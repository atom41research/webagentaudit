"""Focused auto-configuration for Chatbase widgets."""

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


async def open_chatbase_widget(page: Page) -> Frame:
    """Open Chatbase, including embeds stranded before the page load event."""
    frame = await _ready_frame(
        page, timeout_ms=consts.CHATBASE_INITIAL_WAIT_MS
    )
    if frame is not None:
        return frame

    launcher = page.locator(consts.CHATBASE_LAUNCHER_SELECTOR).first
    try:
        await launcher.wait_for(
            state="visible", timeout=consts.CHATBASE_INITIAL_WAIT_MS
        )
    except Exception:
        if not await page.evaluate("typeof window.chatbase === 'function'"):
            raise ChannelNotReadyError(
                "Chatbase was identified, but its bootstrap was unavailable"
            )

        # Some pages never reach their native load event because an unrelated
        # resource remains pending. Let the site's own bootstrap run, then let
        # the loaded Chatbase SDK receive the event it was waiting for.
        await page.evaluate("window.dispatchEvent(new Event('load'))")
        try:
            await page.locator(consts.CHATBASE_EMBED_SELECTOR).last.wait_for(
                state="attached", timeout=consts.CHATBASE_WAIT_MS
            )
            await page.wait_for_function(
                """selector => {
                    const script = document.querySelector(selector);
                    return script && performance.getEntriesByName(script.src).length;
                }""",
                arg=consts.CHATBASE_EMBED_SELECTOR,
                timeout=consts.CHATBASE_WAIT_MS,
            )
        except Exception as exc:
            raise ChannelNotReadyError(
                "Chatbase was identified, but its embed script did not load"
            ) from exc
        await page.evaluate("window.dispatchEvent(new Event('load'))")

    try:
        await launcher.wait_for(
            state="visible", timeout=consts.CHATBASE_WAIT_MS
        )
        await launcher.click(timeout=consts.CHATBASE_WAIT_MS)
    except Exception as exc:
        raise ChannelNotReadyError(
            "Chatbase was identified, but its launcher did not become available"
        ) from exc

    frame = await _ready_frame(page, timeout_ms=consts.CHATBASE_WAIT_MS)
    if frame is None:
        raise ChannelNotReadyError(
            "Chatbase opened, but its composer did not render"
        )
    return frame


async def _ready_frame(page: Page, *, timeout_ms: int) -> Frame | None:
    elapsed = 0
    while elapsed < timeout_ms:
        iframe = page.locator(consts.CHATBASE_FRAME_SELECTOR).first
        try:
            handle = await iframe.element_handle(timeout=250)
            frame = await handle.content_frame() if handle else None
            if frame and await frame.locator(
                consts.CHATBASE_INPUT_SELECTOR
            ).is_visible():
                return frame
        except Exception:
            pass
        await asyncio.sleep(consts.DISCOVERY_INPUT_POLL_MS / 1000)
        elapsed += consts.DISCOVERY_INPUT_POLL_MS
    return None


class ChatbaseAutoConfigurator(BaseAutoConfigurator):
    """Open a Chatbase widget and bind its stable current UI controls."""

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

        frame = await open_chatbase_widget(page)
        self._emit("TRIGGER", "opened Chatbase widget")
        try:
            await frame.locator(consts.CHATBASE_RESPONSE_SELECTOR).first.wait_for(
                state="visible", timeout=consts.CHATBASE_GREETING_WAIT_MS
            )
        except Exception:
            pass

        result = AutoConfigResult(
            input_selector=consts.CHATBASE_INPUT_SELECTOR,
            input_confidence=ConfidenceScore(value=1.0),
            response_selector=consts.CHATBASE_RESPONSE_SELECTOR,
            response_confidence=ConfidenceScore(value=1.0),
            discovery_frame=frame,
            iframe_selector=consts.CHATBASE_FRAME_SELECTOR,
            input_frame_path=[consts.CHATBASE_FRAME_SELECTOR],
            setup_actions=[
                InteractionAction(
                    kind="chatbase_open",
                    selector=consts.CHATBASE_LAUNCHER_SELECTOR,
                )
            ],
        )
        self._emit("CHAT FOUND", result.input_selector)
        return result

    def _emit(self, phase: str, detail: str) -> None:
        if self._progress_callback:
            self._progress_callback(phase, detail)
