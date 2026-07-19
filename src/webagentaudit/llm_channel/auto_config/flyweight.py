"""Focused auto-configuration for Flyweight AI widgets."""

from __future__ import annotations

import asyncio
from collections.abc import Callable

from playwright.async_api import Frame, Page

from webagentaudit.core.exceptions import ChannelNotReadyError
from webagentaudit.core.models import ConfidenceScore
from webagentaudit.llm_channel.models import InteractionAction

from . import consts
from .base import BaseAutoConfigurator
from .models import AutoConfigResult, ElementHint


async def _current_frame(page: Page) -> Frame | None:
    iframe = page.locator(consts.FLYWEIGHT_FRAME_SELECTOR).first
    if await iframe.count() == 0:
        return None
    handle = await iframe.element_handle()
    return await handle.content_frame() if handle else None


async def open_flyweight_widget(page: Page) -> Frame:
    """Open Flyweight when necessary and return its stable chat frame."""
    elapsed = 0
    frame = None
    while elapsed < consts.FLYWEIGHT_WAIT_MS:
        frame = await _current_frame(page)
        if frame is not None:
            break
        await asyncio.sleep(consts.DISCOVERY_INPUT_POLL_MS / 1000)
        elapsed += consts.DISCOVERY_INPUT_POLL_MS
    if frame is None:
        raise ChannelNotReadyError("Flyweight chat frame did not render")

    input_element = frame.locator(consts.FLYWEIGHT_INPUT_SELECTOR).first
    if not await input_element.is_visible():
        launcher = frame.locator(consts.FLYWEIGHT_LAUNCHER_SELECTOR).first
        try:
            await launcher.wait_for(
                state="visible", timeout=consts.FLYWEIGHT_WAIT_MS
            )
            await launcher.click(timeout=consts.FLYWEIGHT_WAIT_MS)
        except Exception as exc:
            raise ChannelNotReadyError(
                "Flyweight launcher did not become available"
            ) from exc

    try:
        await input_element.wait_for(
            state="visible", timeout=consts.FLYWEIGHT_WAIT_MS
        )
    except Exception as exc:
        raise ChannelNotReadyError(
            "Flyweight opened, but its composer did not render"
        ) from exc
    return frame


class FlyweightAutoConfigurator(BaseAutoConfigurator):
    """Bind Flyweight's stable iframe, composer, and send control."""

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

        frame = await open_flyweight_widget(page)
        self._emit("TRIGGER", "opened Flyweight widget")
        result = AutoConfigResult(
            input_selector=consts.FLYWEIGHT_INPUT_SELECTOR,
            input_confidence=ConfidenceScore(value=1.0),
            submit_selector=consts.FLYWEIGHT_SUBMIT_SELECTOR,
            submit_confidence=ConfidenceScore(value=1.0),
            response_selector=consts.FLYWEIGHT_RESPONSE_SELECTOR,
            response_confidence=ConfidenceScore(value=1.0),
            discovery_frame=frame,
            iframe_selector=consts.FLYWEIGHT_FRAME_SELECTOR,
            input_frame_path=[consts.FLYWEIGHT_FRAME_SELECTOR],
            setup_actions=[InteractionAction(
                kind="flyweight_open",
                selector=consts.FLYWEIGHT_LAUNCHER_SELECTOR,
            )],
        )
        self._emit("CHAT FOUND", result.input_selector)
        return result

    def _emit(self, phase: str, detail: str) -> None:
        if self._progress_callback:
            self._progress_callback(phase, detail)
