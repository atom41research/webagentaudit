"""Main LLM assessor — orchestrates probes against a target."""

import asyncio
import logging
from collections.abc import Callable

from webagentaudit.llm_channel.base import BaseLlmChannel
from webagentaudit.llm_channel.models import ChannelMessage

from .config import AssessmentConfig
from .detectors.pattern_detector import PatternDetector
from .models import AssessmentResult, AssessmentSummary, ProbeExchange, ProbeResult
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
    ) -> None:
        self._config = config
        self._channel_factory = channel_factory
        self._registry = registry
        self._progress_callback = progress_callback
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

        async def _run_probe(probe: BaseProbe) -> ProbeResult | None:
            async with semaphore:
                if self._config.stop_on_first and vulnerability_found.is_set():
                    return None

                channel = self._channel_factory()
                try:
                    await channel.connect(url)
                    probe_result = await self._execute_probe(probe, channel)
                finally:
                    try:
                        await channel.disconnect()
                    except Exception:
                        pass

                async with results_lock:
                    results.append(probe_result)
                    if self._progress_callback:
                        self._progress_callback(list(results))

                if probe_result.vulnerability_detected:
                    vulnerability_found.set()

                if self._config.inter_probe_delay_ms > 0:
                    await asyncio.sleep(self._config.inter_probe_delay_ms / 1000.0)

                return probe_result

        tasks = [asyncio.create_task(_run_probe(probe)) for probe in probes]

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
        self, probe: BaseProbe, channel: BaseLlmChannel
    ) -> ProbeResult:
        """Execute a single probe's conversations against the channel."""
        conversations = probe.get_conversations()
        patterns = probe.get_detector_patterns()
        all_matched: list[str] = []
        all_exchanges: list[ProbeExchange] = []
        conversations_run = 0

        for conversation in conversations:
            conversations_run += 1
            for turn in conversation.turns:
                try:
                    response = await channel.send(ChannelMessage(text=turn.prompt))
                    turn_matched: list[str] = []
                    if turn.detect_after:
                        turn_matched = self._detector.detect(response.text, patterns)
                        all_matched.extend(turn_matched)
                    all_exchanges.append(ProbeExchange(
                        prompt=turn.prompt,
                        response=response.text,
                        matched_patterns=turn_matched,
                    ))
                except Exception:
                    logger.warning(
                        "Error during probe '%s' conversation turn",
                        probe.name,
                        exc_info=True,
                    )

        return ProbeResult(
            probe_name=probe.name,
            conversations_run=conversations_run,
            vulnerability_detected=len(all_matched) > 0,
            matched_patterns=list(set(all_matched)),
            exchanges=all_exchanges,
        )
