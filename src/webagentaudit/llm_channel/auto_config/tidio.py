"""Focused auto-configuration for Tidio chat widgets."""

from __future__ import annotations

import asyncio
from collections.abc import Callable

from playwright.async_api import Frame, Page

from webagentaudit.core.exceptions import ChannelNotReadyError
from webagentaudit.core.models import ConfidenceScore
from webagentaudit.llm_channel.models import InteractionAction

from . import consts
from ._frame_finder import FrameFinder
from ._input_finder import InputFinder
from ._selector_builder import SelectorBuilder
from ._submit_finder import SubmitFinder
from .base import BaseAutoConfigurator
from .models import AutoConfigResult, ElementHint, FrameCandidate, ScoredElement


async def open_tidio_widget(
    page: Page, *, timeout_ms: int | None = None
) -> None:
    """Wait for Tidio's public SDK, then display and open the widget."""
    timeout_ms = timeout_ms or consts.TIDIO_WAIT_MS
    try:
        await page.wait_for_function(
            "window.tidioChatApi && "
            "typeof window.tidioChatApi.display === 'function' && "
            "typeof window.tidioChatApi.on === 'function'",
            timeout=timeout_ms,
        )
    except Exception as exc:
        raise ChannelNotReadyError(
            "Tidio was identified, but its widget API did not become available"
        ) from exc

    await page.evaluate("window.tidioChatApi.display(true)")
    try:
        await page.evaluate(
            """timeout => new Promise((resolve, reject) => {
                const timer = setTimeout(
                    () => reject(new Error('Tidio ready timeout')), timeout
                );
                window.tidioChatApi.on('ready', () => {
                    clearTimeout(timer);
                    resolve();
                });
            })""",
            timeout_ms,
        )
    except Exception as exc:
        raise ChannelNotReadyError(
            "Tidio's widget API loaded, but the widget never became ready"
        ) from exc

    await page.evaluate(
        "window.tidioChatApi.show(); window.tidioChatApi.open()"
    )


class TidioAutoConfigurator(BaseAutoConfigurator):
    """Open Tidio through its SDK and bind its rendered composer."""

    def __init__(
        self,
        progress_callback: Callable[[str, str], None] | None = None,
    ) -> None:
        selector_builder = SelectorBuilder()
        self._frame_finder = FrameFinder()
        self._input_finder = InputFinder(selector_builder)
        self._submit_finder = SubmitFinder(selector_builder)
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

        await open_tidio_widget(page)
        self._emit("TRIGGER", "opened Tidio widget")

        candidate, scored = await self._wait_for_composer(page, input_hint)
        if candidate is None or scored is None:
            raise ChannelNotReadyError(
                await self._missing_composer_reason(page)
            )

        result = AutoConfigResult(
            input_selector=scored.candidate.selector,
            input_confidence=ConfidenceScore(value=min(scored.score / 0.8, 1.0)),
            discovery_frame=candidate.frame,
            iframe_selector=candidate.iframe_selector,
            input_frame_path=candidate.frame_path,
            setup_actions=[InteractionAction(
                kind="tidio_open", selector="window.tidioChatApi"
            )],
        )
        submit = await self._submit_finder.find(
            candidate.frame, scored.candidate, hint=submit_hint
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

    async def _wait_for_composer(
        self, page: Page, hint: ElementHint | None
    ) -> tuple[FrameCandidate | None, ScoredElement | None]:
        elapsed = 0
        while elapsed < consts.TIDIO_WAIT_MS:
            for candidate in await self._tidio_frames(page):
                scored = await self._input_finder.find(
                    candidate.frame, hint=hint
                )
                if scored is not None:
                    return candidate, scored
            await asyncio.sleep(consts.DISCOVERY_INPUT_POLL_MS / 1000)
            elapsed += consts.DISCOVERY_INPUT_POLL_MS
        return None, None

    async def _tidio_frames(self, page: Page) -> list[FrameCandidate]:
        candidates = await self._frame_finder.find_chat_frames(page)
        return [
            candidate
            for candidate in candidates
            if "tidio" in " ".join([
                candidate.iframe_selector,
                candidate.src,
                candidate.title,
                *candidate.frame_path,
            ]).lower()
        ]

    async def _missing_composer_reason(self, page: Page) -> str:
        frames = await self._tidio_frames(page)
        for candidate in frames:
            if await candidate.frame.locator(
                'input[type="email"]:visible, input[autocomplete="email"]:visible'
            ).count():
                return "Tidio requires a pre-chat email form before messaging"
        if frames:
            return "Tidio rendered a widget, but exposed no usable chat composer"
        return "Tidio became ready, but did not render a chat frame"

    def _emit(self, phase: str, detail: str) -> None:
        if self._progress_callback:
            self._progress_callback(phase, detail)
