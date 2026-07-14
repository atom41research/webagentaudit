"""Focused auto-configuration for Denser embed-chat widgets."""

from __future__ import annotations

import asyncio
from collections.abc import Callable

from playwright.async_api import Frame, Page

from webagentaudit.core.models import ConfidenceScore
from webagentaudit.llm_channel.models import InteractionAction

from . import consts
from .base import BaseAutoConfigurator
from .models import AutoConfigResult, ElementHint


class DenserAutoConfigurator(BaseAutoConfigurator):
    """Open Denser's shadow-DOM launcher and bind its stable composer."""

    def __init__(
        self,
        progress_callback: Callable[[str, str], None] | None = None,
    ) -> None:
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
        del skip_response, input_hint, submit_hint, response_hint
        if not isinstance(page, Page):
            return AutoConfigResult()

        frame = await self._find_ready_frame(page, timeout_ms=1_000)
        setup_actions: list[InteractionAction] = []
        if frame is None:
            launcher = page.locator(consts.DENSER_LAUNCHER_SELECTOR).first
            try:
                await launcher.wait_for(
                    state="visible", timeout=consts.DENSER_WAIT_MS
                )
                await launcher.click(timeout=consts.DENSER_WAIT_MS)
            except Exception:
                frame = await self._find_ready_frame(page, timeout_ms=1_000)
                if frame is None:
                    self._emit("DISCOVER", "Denser launcher did not render")
                    return AutoConfigResult()
            else:
                setup_actions.append(InteractionAction(
                    kind="trigger", selector=consts.DENSER_LAUNCHER_SELECTOR
                ))
                self._emit("TRIGGER", "opened Denser chatbot")
                frame = await self._find_ready_frame(
                    page, timeout_ms=consts.DENSER_WAIT_MS
                )

        if frame is None:
            self._emit("DISCOVER", "Denser composer did not render")
            return AutoConfigResult()

        result = AutoConfigResult(
            input_selector=consts.DENSER_INPUT_SELECTOR,
            input_confidence=ConfidenceScore(value=1.0),
            response_selector=consts.DENSER_RESPONSE_SELECTOR,
            response_confidence=ConfidenceScore(value=1.0),
            discovery_frame=frame,
            iframe_selector=consts.DENSER_FRAME_SELECTOR,
            input_frame_path=[consts.DENSER_FRAME_SELECTOR],
            setup_actions=setup_actions,
        )
        self._emit("CHAT FOUND", result.input_selector)
        return result

    async def _find_ready_frame(
        self, page: Page, *, timeout_ms: int
    ) -> Frame | None:
        elapsed = 0
        while elapsed < timeout_ms:
            for frame in page.frames:
                if frame is page.main_frame:
                    continue
                try:
                    owner = await frame.frame_element()
                    if (
                        await owner.get_attribute("title") == "Denser Chatbot"
                        and await frame.locator(
                            consts.DENSER_INPUT_SELECTOR
                        ).is_visible()
                    ):
                        return frame
                except Exception:
                    continue
            await asyncio.sleep(consts.DISCOVERY_INPUT_POLL_MS / 1000)
            elapsed += consts.DISCOVERY_INPUT_POLL_MS
        return None

    def _emit(self, phase: str, detail: str) -> None:
        if self._progress_callback:
            self._progress_callback(phase, detail)
