"""Bounded input-first auto-configuration for browser chat interfaces."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable

from playwright.async_api import Frame, Page

from webagentaudit.core.models import ConfidenceScore
from webagentaudit.llm_channel.models import InteractionAction

from . import consts
from ._frame_finder import FrameFinder
from ._input_finder import InputFinder
from ._preflight import PreflightDismissal
from ._response_finder import ResponseFinder
from ._selector_builder import SelectorBuilder
from ._submit_finder import SubmitFinder
from ._trigger_finder import TriggerCandidate, TriggerFinder
from .base import BaseAutoConfigurator
from .models import AutoConfigResult, ElementHint, FrameCandidate, ScoredElement

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[str, str], None]


class AlgorithmicAutoConfigurator(BaseAutoConfigurator):
    """Discover a usable input before taking any speculative page action."""

    def __init__(self, progress_callback: ProgressCallback | None = None) -> None:
        self._selector_builder = SelectorBuilder()
        self._frame_finder = FrameFinder()
        self._input_finder = InputFinder(self._selector_builder)
        self._preflight = PreflightDismissal(self._selector_builder)
        self._trigger_finder = TriggerFinder(self._selector_builder)
        self._submit_finder = SubmitFinder(self._selector_builder)
        self._response_finder = ResponseFinder(self._selector_builder)
        self._progress_callback = progress_callback
        self._background_tasks: set[asyncio.Task[AutoConfigResult]] = set()

    async def configure(
        self,
        page: Page | Frame,
        *,
        skip_response: bool = False,
        input_hint: ElementHint | None = None,
        submit_hint: ElementHint | None = None,
        response_hint: ElementHint | None = None,
    ) -> AutoConfigResult:
        del response_hint  # response discovery is DOM-diff based
        if not isinstance(page, Page):
            return await self._configure_frame(
                page,
                skip_response=skip_response,
                input_hint=input_hint,
                submit_hint=submit_hint,
            )
        task = asyncio.create_task(self._configure_page(
            page,
            skip_response=skip_response,
            input_hint=input_hint,
            submit_hint=submit_hint,
        ))
        done, _ = await asyncio.wait(
            {task}, timeout=consts.DISCOVERY_TIMEOUT_MS / 1000
        )
        if done:
            return task.result()

        # Cancelling a pending Playwright protocol call can orphan its response
        # future. Let page cleanup finish it, then consume that result quietly.
        self._background_tasks.add(task)
        task.add_done_callback(self._consume_background_result)
        self._emit("DISCOVER", "time budget exhausted")
        logger.debug("Chat discovery exceeded %dms", consts.DISCOVERY_TIMEOUT_MS)
        return AutoConfigResult()

    def _consume_background_result(
        self, task: asyncio.Task[AutoConfigResult]
    ) -> None:
        self._background_tasks.discard(task)
        try:
            task.result()
        except asyncio.CancelledError:
            logger.debug("Timed-out chat discovery was cancelled")
        except Exception:
            logger.debug("Timed-out chat discovery stopped", exc_info=True)

    async def _configure_page(
        self,
        page: Page,
        *,
        skip_response: bool,
        input_hint: ElementHint | None,
        submit_hint: ElementHint | None,
    ) -> AutoConfigResult:
        self._emit("DISCOVER", "scanning page and frames for an input")
        found = await self._find_input(page, input_hint)
        dismiss_actions: list[InteractionAction] = []

        if found is None:
            dismiss_actions = await self._dismiss_blockers(page, input_hint)
            found = await self._find_input(page, input_hint)

        attempted: set[str] = set()
        trigger_attempts = 0
        while found is None and trigger_attempts < consts.DISCOVERY_MAX_TRIGGERS:
            branch: list[InteractionAction] = []
            allowed_fingerprints: set[str] | None = None
            for depth in range(consts.DISCOVERY_MAX_TRIGGER_DEPTH):
                ranked = await self._rank_triggers(page)
                item = next(
                    (
                        entry
                        for entry in ranked
                        if entry[0] not in attempted
                        and (
                            allowed_fingerprints is None
                            or entry[0] in allowed_fingerprints
                        )
                    ),
                    None,
                )
                if item is None:
                    break
                fingerprint, frame_path, candidate = item
                attempted.add(fingerprint)
                trigger_attempts += 1
                self._emit(
                    "TRIGGER",
                    f"trying {candidate.candidate.selector}"
                    + (f" in {frame_path[-1]}" if frame_path else ""),
                )
                try:
                    await candidate.element.click(timeout=consts.DISCOVERY_ACTION_WAIT_MS)
                except Exception:
                    logger.debug("Trigger click failed: %s", fingerprint, exc_info=True)
                    break
                branch.append(InteractionAction(
                    kind="trigger",
                    selector=candidate.candidate.selector,
                    frame_path=frame_path,
                ))
                found = await self._poll_for_input(page, input_hint)
                if found is not None:
                    return await self._build_result(
                        found,
                        setup_actions=[*dismiss_actions, *branch],
                        skip_response=skip_response,
                        submit_hint=submit_hint,
                    )

                # Only continue a multi-step branch when a new chat control
                # appeared; otherwise isolate the next attempt with a reload.
                after = await self._rank_triggers(page)
                before_fingerprints = {fp for fp, _, _ in ranked}
                allowed_fingerprints = {
                    fp
                    for fp, _, _ in after
                    if fp not in before_fingerprints and fp not in attempted
                }
                if not allowed_fingerprints:
                    break
                if trigger_attempts >= consts.DISCOVERY_MAX_TRIGGERS:
                    break

            if found is not None:
                break
            self._emit("DISCOVER", "reloading after unsuccessful trigger")
            try:
                await page.reload(wait_until="domcontentloaded")
            except Exception:
                logger.debug("Reload after trigger failed", exc_info=True)
                break
            dismiss_actions = await self._dismiss_blockers(page, input_hint)
            found = await self._find_input(page, input_hint)

        if found is None:
            self._emit("DISCOVER", "no usable chat input found")
            return AutoConfigResult()
        return await self._build_result(
            found,
            setup_actions=dismiss_actions,
            skip_response=skip_response,
            submit_hint=submit_hint,
        )

    async def _configure_frame(
        self,
        frame: Frame,
        *,
        skip_response: bool,
        input_hint: ElementHint | None,
        submit_hint: ElementHint | None,
    ) -> AutoConfigResult:
        scored = await self._input_finder.find(frame, hint=input_hint)
        if scored is None:
            return AutoConfigResult()
        return await self._build_result(
            (scored, frame, None),
            setup_actions=[],
            skip_response=skip_response,
            submit_hint=submit_hint,
        )

    async def _dismiss_blockers(
        self, page: Page, input_hint: ElementHint | None
    ) -> list[InteractionAction]:
        actions: list[InteractionAction] = []
        for _ in range(consts.DISCOVERY_MAX_BLOCKERS):
            contexts = await self._contexts(page)
            dismissed = False
            for context, frame_candidate in contexts:
                try:
                    selector = await self._preflight.dismiss_one(context)
                except Exception:
                    logger.debug("Blocker dismissal failed", exc_info=True)
                    continue
                if selector is None:
                    continue
                frame_path = frame_candidate.frame_path if frame_candidate else []
                actions.append(InteractionAction(
                    kind="dismiss",
                    selector=selector,
                    frame_path=frame_path,
                    optional=True,
                ))
                self._emit("BLOCKER", f"dismissed {selector}")
                dismissed = True
                if await self._find_input(page, input_hint) is not None:
                    return actions
                break
            if not dismissed:
                break
        return actions

    async def _poll_for_input(
        self, page: Page, input_hint: ElementHint | None
    ) -> tuple[ScoredElement, Page | Frame, FrameCandidate | None] | None:
        elapsed = 0
        while elapsed < consts.DISCOVERY_ACTION_WAIT_MS:
            found = await self._find_input(page, input_hint)
            if found is not None:
                return found
            await asyncio.sleep(consts.DISCOVERY_INPUT_POLL_MS / 1000)
            elapsed += consts.DISCOVERY_INPUT_POLL_MS
        return None

    async def _find_input(
        self, page: Page, input_hint: ElementHint | None
    ) -> tuple[ScoredElement, Page | Frame, FrameCandidate | None] | None:
        best: tuple[ScoredElement, Page | Frame, FrameCandidate | None] | None = None
        for context, frame_candidate in await self._contexts(page):
            try:
                scored = await self._input_finder.find(context, hint=input_hint)
            except Exception:
                continue
            if scored is not None and (best is None or scored.score > best[0].score):
                best = (scored, context, frame_candidate)
        if best is not None:
            self._emit("CHAT FOUND", best[0].candidate.selector)
        return best

    async def _rank_triggers(
        self, page: Page
    ) -> list[tuple[str, list[str], TriggerCandidate]]:
        ranked: list[tuple[str, list[str], TriggerCandidate]] = []
        for context, frame_candidate in await self._contexts(page):
            frame_path = frame_candidate.frame_path if frame_candidate else []
            try:
                candidates = await self._trigger_finder.ranked_candidates(context)
            except Exception:
                continue
            for candidate in candidates:
                fingerprint = f"{' > '.join(frame_path)}::{candidate.candidate.selector}"
                ranked.append((fingerprint, frame_path, candidate))
            if candidates and candidates[0].score >= consts.TRIGGER_DECISIVE_SCORE:
                break
        ranked.sort(key=lambda item: item[2].score, reverse=True)
        return ranked

    async def _contexts(
        self, page: Page
    ) -> list[tuple[Page | Frame, FrameCandidate | None]]:
        contexts: list[tuple[Page | Frame, FrameCandidate | None]] = []
        for candidate in await self._frame_finder.find_chat_frames(page):
            contexts.append((candidate.frame, candidate))
        contexts.append((page, None))
        return contexts

    async def _build_result(
        self,
        found: tuple[ScoredElement, Page | Frame, FrameCandidate | None],
        *,
        setup_actions: list[InteractionAction],
        skip_response: bool,
        submit_hint: ElementHint | None,
    ) -> AutoConfigResult:
        scored, context, frame_candidate = found
        result = AutoConfigResult(
            input_selector=scored.candidate.selector,
            input_confidence=ConfidenceScore(value=min(scored.score / 0.8, 1.0)),
            input_frame_path=frame_candidate.frame_path if frame_candidate else [],
            iframe_selector=(
                frame_candidate.iframe_selector if frame_candidate else None
            ),
            discovery_frame=frame_candidate.frame if frame_candidate else None,
            setup_actions=setup_actions,
        )
        submit = await self._submit_finder.find(
            context, scored.candidate, hint=submit_hint
        )
        if submit is not None:
            result.submit_selector = submit.candidate.selector
            result.submit_confidence = ConfidenceScore(
                value=min(submit.score / 0.7, 1.0)
            )
        else:
            result.use_enter_to_submit = True
            result.submit_confidence = ConfidenceScore(value=0.5)

        if not skip_response:
            response, text = await self._response_finder.find(
                context,
                input_selector=result.input_selector,
                submit_selector=result.submit_selector,
            )
            if response is not None:
                result.response_selector = response.candidate.selector
                result.response_confidence = ConfidenceScore(
                    value=min(response.score / 0.7, 1.0)
                )
                result.test_message_used = consts.RESPONSE_PROBE_MESSAGE
                result.test_response_received = text
        return result

    def _emit(self, phase: str, detail: str) -> None:
        logger.info("%s: %s", phase, detail)
        if self._progress_callback:
            self._progress_callback(phase, detail)
