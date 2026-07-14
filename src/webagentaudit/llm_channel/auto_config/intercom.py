"""Focused auto-configuration for Intercom Messenger."""

from __future__ import annotations

import asyncio
import re
from collections.abc import Callable

from playwright.async_api import Frame, Page

from webagentaudit.core.models import ConfidenceScore
from webagentaudit.llm_channel.models import InteractionAction

from . import consts
from ._input_finder import InputFinder
from ._preflight import PreflightDismissal
from ._selector_builder import SelectorBuilder
from ._submit_finder import SubmitFinder
from .base import BaseAutoConfigurator
from .models import AutoConfigResult, ElementHint


class IntercomAutoConfigurator(BaseAutoConfigurator):
    """Open Intercom directly and discover its current composer controls."""

    def __init__(
        self,
        progress_callback: Callable[[str, str], None] | None = None,
    ) -> None:
        self._selector_builder = SelectorBuilder()
        self._input_finder = InputFinder(self._selector_builder)
        self._submit_finder = SubmitFinder(self._selector_builder)
        self._preflight = PreflightDismissal(self._selector_builder)
        self._progress_callback = progress_callback

    async def configure(
        self,
        page: Page | Frame,
        *,
        skip_response: bool = False,
        input_hint: ElementHint | None = None,
        submit_hint: ElementHint | None = None,
        response_hint: ElementHint | None = None,
    ) -> AutoConfigResult:
        del skip_response, response_hint
        if not isinstance(page, Page):
            return AutoConfigResult()

        setup_actions: list[InteractionAction] = []
        dismissed = await self._preflight.dismiss_one(page)
        if dismissed:
            setup_actions.append(InteractionAction(
                kind="dismiss", selector=dismissed, optional=True
            ))
            self._emit("BLOCKER", f"dismissed {dismissed}")

        try:
            await page.wait_for_function(
                "typeof window.Intercom === 'function'",
                timeout=consts.INTERCOM_FRAME_WAIT_MS,
            )
            await page.evaluate("window.Intercom('show')")
        except Exception:
            self._emit("DISCOVER", "Intercom API was unavailable")
            return AutoConfigResult()
        setup_actions.append(InteractionAction(
            kind="intercom_show", selector="window.Intercom"
        ))
        self._emit("TRIGGER", "opened Intercom Messenger")

        frame = await self._wait_for_messenger_frame(page)
        if frame is None:
            self._emit("DISCOVER", "Intercom Messenger did not render")
            return AutoConfigResult()

        scored = await self._input_finder.find(frame, hint=input_hint)
        if scored is None:
            action = frame.locator('[role="button"]').filter(
                has_text=re.compile(
                    consts.INTERCOM_CONVERSATION_ACTION_PATTERN,
                    re.IGNORECASE,
                )
            ).first
            try:
                await action.wait_for(
                    state="visible", timeout=consts.INTERCOM_FRAME_WAIT_MS
                )
                action_handle = await action.element_handle()
                if action_handle is None:
                    return AutoConfigResult()
                action_selector = await self._selector_builder.build(
                    action_handle, frame
                )
                await action.click()
                setup_actions.append(InteractionAction(
                    kind="trigger",
                    selector=action_selector,
                    frame_path=[consts.INTERCOM_MESSENGER_FRAME_SELECTOR],
                ))
                action_text = " ".join((await action.inner_text()).split())
                self._emit("TRIGGER", f"opened {action_text}")
            except Exception:
                self._emit("DISCOVER", "no Intercom conversation action found")
                return AutoConfigResult()
            scored = await self._poll_for_input(frame, input_hint)

        if scored is None:
            self._emit("DISCOVER", "Intercom composer did not render")
            return AutoConfigResult()

        result = AutoConfigResult(
            input_selector=scored.candidate.selector,
            input_confidence=ConfidenceScore(value=min(scored.score / 0.8, 1.0)),
            discovery_frame=frame,
            iframe_selector=consts.INTERCOM_MESSENGER_FRAME_SELECTOR,
            input_frame_path=[consts.INTERCOM_MESSENGER_FRAME_SELECTOR],
            setup_actions=setup_actions,
        )
        submit = await self._submit_finder.find(
            frame, scored.candidate, hint=submit_hint
        )
        if submit is not None:
            result.submit_selector = submit.candidate.selector
            result.submit_confidence = ConfidenceScore(
                value=min(submit.score / 0.7, 1.0)
            )
        else:
            result.use_enter_to_submit = True
            result.submit_confidence = ConfidenceScore(value=0.5)
        self._emit("CHAT FOUND", result.input_selector)
        return result

    async def _wait_for_messenger_frame(self, page: Page) -> Frame | None:
        elapsed = 0
        while elapsed < consts.INTERCOM_FRAME_WAIT_MS:
            frame = page.frame(name="intercom-messenger-frame")
            if frame is not None:
                return frame
            await asyncio.sleep(consts.DISCOVERY_INPUT_POLL_MS / 1000)
            elapsed += consts.DISCOVERY_INPUT_POLL_MS
        return None

    async def _poll_for_input(
        self, frame: Frame, hint: ElementHint | None
    ):
        elapsed = 0
        while elapsed < consts.INTERCOM_FRAME_WAIT_MS:
            scored = await self._input_finder.find(frame, hint=hint)
            if scored is not None:
                return scored
            await asyncio.sleep(consts.DISCOVERY_INPUT_POLL_MS / 1000)
            elapsed += consts.DISCOVERY_INPUT_POLL_MS
        return None

    def _emit(self, phase: str, detail: str) -> None:
        if self._progress_callback:
            self._progress_callback(phase, detail)
