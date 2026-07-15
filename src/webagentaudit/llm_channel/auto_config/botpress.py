"""Focused auto-configuration for Botpress webchat widgets."""

from __future__ import annotations

import asyncio
from collections.abc import Callable

from playwright.async_api import Frame, Page

from webagentaudit.core.exceptions import ChannelNotReadyError
from webagentaudit.core.models import ConfidenceScore
from webagentaudit.llm_channel.models import InteractionAction

from . import consts
from ._frame_finder import FrameFinder
from .base import BaseAutoConfigurator
from .models import AutoConfigResult, ElementHint


async def open_botpress_widget(
    page: Page, *, timeout_ms: int | None = None
) -> None:
    """Open Botpress through its public webchat API."""
    timeout_ms = timeout_ms or consts.BOTPRESS_WAIT_MS
    try:
        await page.wait_for_function(
            "window.botpress && typeof window.botpress.open === 'function'",
            timeout=timeout_ms,
        )
        await page.evaluate("window.botpress.open()")
    except Exception as exc:
        raise ChannelNotReadyError(
            "Botpress was identified, but its widget API did not become available"
        ) from exc


class BotpressAutoConfigurator(BaseAutoConfigurator):
    """Open Botpress and bind its embedded or iframe composer."""

    def __init__(
        self,
        progress_callback: Callable[[str, str], None] | None = None,
    ) -> None:
        self._frame_finder = FrameFinder()
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

        self._emit(
            "INTERACTION",
            consts.PROGRAMMATIC_INTERACTION_DESCRIPTIONS["botpress_open"],
        )
        await open_botpress_widget(page)
        self._emit("TRIGGER", "opened Botpress widget")

        context, frame_path = await self._wait_for_composer(page)
        if context is None:
            raise ChannelNotReadyError(
                "Botpress opened, but did not render a usable chat composer"
            )

        result = AutoConfigResult(
            input_selector=consts.BOTPRESS_INPUT_SELECTOR,
            input_confidence=ConfidenceScore(value=1.0),
            response_selector=consts.BOTPRESS_RESPONSE_SELECTOR,
            response_confidence=ConfidenceScore(value=1.0),
            discovery_frame=context if isinstance(context, Frame) else None,
            iframe_selector=frame_path[-1] if frame_path else None,
            input_frame_path=frame_path,
            setup_actions=[InteractionAction(
                kind="botpress_open", selector="window.botpress"
            )],
            use_enter_to_submit=True,
            submit_confidence=ConfidenceScore(value=0.5),
        )
        self._emit("CHAT FOUND", result.input_selector)
        return result

    async def _wait_for_composer(
        self, page: Page
    ) -> tuple[Page | Frame | None, list[str]]:
        elapsed = 0
        while elapsed < consts.BOTPRESS_WAIT_MS:
            if await page.locator(
                f"{consts.BOTPRESS_INPUT_SELECTOR}:visible"
            ).count():
                return page, []
            for frame in page.frames:
                if frame is page.main_frame:
                    continue
                try:
                    if await frame.locator(
                        f"{consts.BOTPRESS_INPUT_SELECTOR}:visible"
                    ).count():
                        return frame, await self._frame_finder.frame_path(frame)
                except Exception:
                    continue
            await asyncio.sleep(consts.DISCOVERY_INPUT_POLL_MS / 1000)
            elapsed += consts.DISCOVERY_INPUT_POLL_MS
        return None, []

    def _emit(self, phase: str, detail: str) -> None:
        if self._progress_callback:
            self._progress_callback(phase, detail)
