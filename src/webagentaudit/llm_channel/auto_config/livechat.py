"""Focused auto-configuration for standalone LiveChat widgets."""

from __future__ import annotations

import asyncio
from collections.abc import Callable

from playwright.async_api import Frame, Page

from webagentaudit.core.exceptions import ChannelNotReadyError
from webagentaudit.core.models import ConfidenceScore
from webagentaudit.llm_channel.models import InteractionAction

from . import consts
from ._input_finder import InputFinder
from ._preflight import PreflightDismissal
from ._selector_builder import SelectorBuilder
from ._submit_finder import SubmitFinder
from .base import BaseAutoConfigurator
from .models import AutoConfigResult, ElementHint


async def _current_frame(page: Page, selector: str) -> Frame | None:
    iframe = page.locator(selector).first
    if await iframe.count() == 0:
        return None
    handle = await iframe.element_handle()
    return await handle.content_frame() if handle else None


async def _wait_for_frame(page: Page, selector: str) -> Frame | None:
    elapsed = 0
    while elapsed < consts.LIVECHAT_WAIT_MS:
        frame = await _current_frame(page, selector)
        if frame is not None:
            return frame
        await asyncio.sleep(consts.DISCOVERY_INPUT_POLL_MS / 1000)
        elapsed += consts.DISCOVERY_INPUT_POLL_MS
    return None


async def _open_start_gate(frame: Frame) -> None:
    """Advance LiveChat's language-independent pre-conversation gate."""
    controls = frame.locator(
        f"{consts.LIVECHAT_START_SELECTOR}, {consts.LIVECHAT_INPUT_SELECTOR}"
    ).first
    try:
        await controls.wait_for(state="visible", timeout=consts.LIVECHAT_WAIT_MS)
    except Exception as exc:
        raise ChannelNotReadyError("LiveChat controls did not render") from exc
    start = frame.locator(consts.LIVECHAT_START_SELECTOR).first
    if await start.count() == 0 or not await start.is_visible():
        return
    await start.click(timeout=consts.LIVECHAT_WAIT_MS)
    await frame.locator(consts.LIVECHAT_INPUT_SELECTOR).first.wait_for(
        state="visible", timeout=consts.LIVECHAT_WAIT_MS
    )


async def _has_visible_controls(frame: Frame) -> bool:
    controls = frame.locator(
        f"{consts.LIVECHAT_START_SELECTOR}, {consts.LIVECHAT_INPUT_SELECTOR}"
    ).first
    try:
        return await controls.count() > 0 and await controls.is_visible()
    except Exception:
        return False


async def open_livechat_widget(page: Page) -> Frame:
    """Open the minimized widget when needed and return its main frame."""
    expanded = await _current_frame(page, consts.LIVECHAT_FRAME_SELECTOR)
    if expanded is not None and await _has_visible_controls(expanded):
        await _open_start_gate(expanded)
        return expanded

    minimized = await _wait_for_frame(
        page, consts.LIVECHAT_MINIMIZED_FRAME_SELECTOR
    )
    if minimized is None:
        if expanded is not None:
            await _open_start_gate(expanded)
            return expanded
        raise ChannelNotReadyError("LiveChat launcher did not render")
    launcher = minimized.locator("button").first
    await launcher.wait_for(state="visible", timeout=consts.LIVECHAT_WAIT_MS)
    await launcher.click(timeout=consts.LIVECHAT_WAIT_MS)

    expanded = await _wait_for_frame(page, consts.LIVECHAT_FRAME_SELECTOR)
    if expanded is None:
        raise ChannelNotReadyError("LiveChat composer frame did not render")
    await _open_start_gate(expanded)
    return expanded


class LiveChatAutoConfigurator(BaseAutoConfigurator):
    """Open standalone LiveChat and discover its current composer controls."""

    def __init__(
        self,
        progress_callback: Callable[[str, str], None] | None = None,
    ) -> None:
        selector_builder = SelectorBuilder()
        self._input_finder = InputFinder(selector_builder)
        self._preflight = PreflightDismissal(selector_builder)
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

        setup_actions: list[InteractionAction] = []
        for _ in range(consts.PREFLIGHT_MAX_DISMISSALS):
            dismissed = await self._preflight.dismiss_one(page)
            if dismissed is None:
                break
            setup_actions.append(InteractionAction(
                kind="dismiss", selector=dismissed, optional=True
            ))
            self._emit("BLOCKER", f"dismissed {dismissed}")

        frame = await open_livechat_widget(page)
        self._emit("TRIGGER", "opened LiveChat widget")
        scored = await self._poll_for_input(frame, input_hint)
        if scored is None:
            raise ChannelNotReadyError("LiveChat composer did not render")

        result = AutoConfigResult(
            input_selector=scored.candidate.selector,
            input_confidence=ConfidenceScore(value=1.0),
            discovery_frame=frame,
            iframe_selector=consts.LIVECHAT_FRAME_SELECTOR,
            input_frame_path=[consts.LIVECHAT_FRAME_SELECTOR],
            setup_actions=[*setup_actions, InteractionAction(
                kind="livechat_open",
                selector=consts.LIVECHAT_MINIMIZED_FRAME_SELECTOR,
            )],
        )
        submit = await self._submit_finder.find(
            frame,
            scored.candidate,
            hint=submit_hint,
            trusted_context=True,
        )
        if submit is not None:
            result.submit_selector = submit.candidate.selector
            result.submit_confidence = ConfidenceScore(value=1.0)
        else:
            result.use_enter_to_submit = True
            result.submit_confidence = ConfidenceScore(value=0.5)
        self._emit("CHAT FOUND", result.input_selector)
        return result

    async def _poll_for_input(
        self, frame: Frame, hint: ElementHint | None
    ):
        elapsed = 0
        while elapsed < consts.LIVECHAT_WAIT_MS:
            scored = await self._input_finder.find(
                frame, hint=hint, trusted_context=True
            )
            if scored is not None:
                return scored
            await asyncio.sleep(consts.DISCOVERY_INPUT_POLL_MS / 1000)
            elapsed += consts.DISCOVERY_INPUT_POLL_MS
        return None

    def _emit(self, phase: str, detail: str) -> None:
        if self._progress_callback:
            self._progress_callback(phase, detail)
