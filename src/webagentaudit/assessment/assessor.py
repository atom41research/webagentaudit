"""Main LLM assessor — orchestrates probes against a target."""

import asyncio
import logging
from collections.abc import Callable

from webagentaudit.llm_channel.base import BaseLlmChannel
from webagentaudit.llm_channel.models import ChannelMessage
from webagentaudit.core.exceptions import (
    ChannelNotReadyError,
    ChannelResponseError,
    ChannelSubmissionError,
)

from .config import AssessmentConfig
from .detectors.pattern_detector import PatternDetector
from .models import (
    AssessmentResult,
    AssessmentSummary,
    ChatMessage,
    ProbeError,
    ProbeExchange,
    ProbeResult,
)
from .probes.base import BaseProbe
from .probes.registry import ProbeRegistry

logger = logging.getLogger(__name__)


class LlmAssessor:
    """Orchestrates running assessment probes against a web-based LLM.

    Uses a channel factory to create a fresh channel per probe, runs
    conversations, and applies pattern detection to identify vulnerabilities.
    Supports concurrent execution via ``config.workers``.
    """

    def __init__(
        self,
        config: AssessmentConfig,
        channel_factory: Callable[[], BaseLlmChannel],
        registry: ProbeRegistry,
        progress_callback: Callable[[list[ProbeResult]], None] | None = None,
        activity_callback: Callable[[str, str], None] | None = None,
    ) -> None:
        self._config = config
        self._channel_factory = channel_factory
        self._registry = registry
        self._progress_callback = progress_callback
        self._activity_callback = activity_callback
        self._detector = PatternDetector()

    async def assess(self, url: str) -> AssessmentResult:
        """Run all registered probes against the target URL.

        Returns an AssessmentResult with per-probe results and a summary.
        """
        probes = self._registry.get_all()
        if not probes:
            return AssessmentResult(
                summary=AssessmentSummary(total_probes=0, target_url=url),
            )

        semaphore = asyncio.Semaphore(self._config.workers)
        results: list[ProbeResult] = []
        results_lock = asyncio.Lock()
        vulnerability_found = asyncio.Event()

        async def _run_probe(
            probe_number: int, probe: BaseProbe,
        ) -> ProbeResult | None:
            async with semaphore:
                if self._config.stop_on_first and vulnerability_found.is_set():
                    return None

                probe_result = await self._execute_probe(
                    probe,
                    url,
                    probe_number=probe_number,
                    total_probes=len(probes),
                )

                async with results_lock:
                    results.append(probe_result)
                    if self._progress_callback:
                        self._progress_callback(list(results))

                if probe_result.vulnerability_detected:
                    vulnerability_found.set()

                if self._config.inter_probe_delay_ms > 0:
                    await asyncio.sleep(self._config.inter_probe_delay_ms / 1000.0)

                return probe_result

        tasks = [
            asyncio.create_task(_run_probe(number, probe))
            for number, probe in enumerate(probes, start=1)
        ]

        if self._config.stop_on_first:
            # Wait for either all tasks to finish or first vulnerability
            done_event = asyncio.Event()

            async def _watch_completion() -> None:
                await asyncio.gather(*tasks, return_exceptions=True)
                done_event.set()

            watcher = asyncio.create_task(_watch_completion())

            # Wait for first vulnerability or all tasks done
            vuln_waiter = asyncio.create_task(vulnerability_found.wait())
            done_waiter = asyncio.create_task(done_event.wait())

            await asyncio.wait(
                [vuln_waiter, done_waiter],
                return_when=asyncio.FIRST_COMPLETED,
            )

            # Cancel remaining tasks if vulnerability found
            if vulnerability_found.is_set():
                for task in tasks:
                    if not task.done():
                        task.cancel()

            # Wait for cancellation to propagate
            await asyncio.gather(*tasks, return_exceptions=True)
            vuln_waiter.cancel()
            done_waiter.cancel()
            watcher.cancel()
            # Suppress cancellation errors from helper tasks
            for t in [vuln_waiter, done_waiter, watcher]:
                try:
                    await t
                except (asyncio.CancelledError, Exception):
                    pass
        else:
            await asyncio.gather(*tasks, return_exceptions=True)

        vuln_count = sum(1 for r in results if r.vulnerability_detected)

        return AssessmentResult(
            summary=AssessmentSummary(
                total_probes=len(results),
                vulnerabilities_found=vuln_count,
                target_url=url,
            ),
            probe_results=results,
        )

    async def _execute_probe(
        self,
        probe: BaseProbe,
        url: str,
        *,
        probe_number: int,
        total_probes: int,
    ) -> ProbeResult:
        """Execute a single probe's conversations, each with a fresh channel."""
        conversations = probe.get_conversations()
        total_turns = sum(len(item.turns) for item in conversations)
        if self._activity_callback:
            noun = "interaction" if total_turns == 1 else "interactions"
            self._activity_callback(
                "PROBE START",
                f"[{probe_number}/{total_probes}] {probe.name} "
                f"({total_turns} planned {noun})",
            )
        patterns = probe.get_detector_patterns()
        refusal_patterns = probe.get_refusal_patterns() or None
        all_matched: list[str] = []
        all_exchanges: list[ProbeExchange] = []
        conversations_run = 0
        turns_started = 0
        errors: list[ProbeError] = []

        for conversation in conversations:
            conversations_run += 1
            channel = self._channel_factory()
            if conversation.turns:
                turns_started += 1
                self._emit_turn_start(turns_started, total_turns, probe.name)
            try:
                await channel.connect(url)
                for turn_index, turn in enumerate(conversation.turns):
                    if turn_index:
                        turns_started += 1
                        self._emit_turn_start(
                            turns_started, total_turns, probe.name
                        )
                    try:
                        response = await channel.send(ChannelMessage(text=turn.prompt))
                        turn_matched: list[str] = []
                        if turn.detect_after:
                            turn_matched = self._detector.detect(
                                response.text, patterns, refusal_patterns,
                            )
                            all_matched.extend(turn_matched)
                        all_exchanges.append(ProbeExchange(
                            messages=[
                                ChatMessage(role="user", content=turn.prompt),
                                ChatMessage(role="assistant", content=response.text),
                            ],
                            matched_patterns=turn_matched,
                        ))
                    except Exception as exc:
                        phase = self._failure_phase(exc)
                        message = str(exc) or type(exc).__name__
                        errors.append(ProbeError(
                            phase=phase,
                            message=message,
                            prompt=turn.prompt,
                        ))
                        logger.debug(
                            "Probe '%s' turn failed in %s: %s",
                            probe.name,
                            phase,
                            message,
                            exc_info=phase == "assessment",
                        )
            except Exception as exc:
                expected = isinstance(exc, ChannelNotReadyError)
                errors.append(ProbeError(
                    phase="chat_detection" if expected else "connection",
                    message=str(exc) or type(exc).__name__,
                ))
                logger.debug(
                    "Probe '%s' could not connect: %s",
                    probe.name,
                    str(exc) or type(exc).__name__,
                    exc_info=not expected,
                )
            finally:
                try:
                    await channel.disconnect()
                except Exception:
                    pass

        return ProbeResult(
            probe_name=probe.name,
            conversations_run=conversations_run,
            vulnerability_detected=len(all_matched) > 0,
            matched_patterns=list(set(all_matched)),
            exchanges=all_exchanges,
            error_count=len(errors),
            errors=errors,
        )

    def _emit_turn_start(
        self, turn_number: int, total_turns: int, probe_name: str
    ) -> None:
        if self._activity_callback:
            self._activity_callback(
                "PROBE TURN",
                f"[{turn_number}/{total_turns}] {probe_name}",
            )

    @staticmethod
    def _failure_phase(exc: Exception) -> str:
        if isinstance(exc, ChannelNotReadyError):
            return "chat_detection"
        if isinstance(exc, ChannelSubmissionError):
            return "prompt_submission"
        if isinstance(exc, ChannelResponseError):
            return "response_read"
        return "assessment"
