"""Focused auto-configuration for Featurebase Messenger."""

from __future__ import annotations

from collections.abc import Callable

from playwright.async_api import Frame, Page

from webagentaudit.core.exceptions import ChannelNotReadyError
from webagentaudit.core.models import ConfidenceScore
from webagentaudit.llm_channel.models import InteractionAction

from . import consts
from .base import BaseAutoConfigurator
from .models import AutoConfigResult, ElementHint


async def open_featurebase_composer(page: Page) -> Frame:
    """Open a new Featurebase conversation through its public SDK."""
    try:
        await page.wait_for_function(
            "typeof window.Featurebase === 'function'",
            timeout=consts.FEATUREBASE_WAIT_MS,
        )
        await page.evaluate(
            "draft => window.Featurebase('showNewMessage', draft)",
            consts.FEATUREBASE_DISCOVERY_DRAFT,
        )
        frame_locator = page.locator(consts.FEATUREBASE_FRAME_SELECTOR).first
        await frame_locator.wait_for(
            state="attached", timeout=consts.FEATUREBASE_WAIT_MS
        )
        handle = await frame_locator.element_handle()
        frame = await handle.content_frame() if handle else None
        if frame is None:
            raise RuntimeError("Featurebase frame was inaccessible")
        await frame.locator(
            f"{consts.FEATUREBASE_INPUT_SELECTOR}:visible"
        ).first.wait_for(state="visible", timeout=consts.FEATUREBASE_WAIT_MS)
        return frame
    except Exception as exc:
        raise ChannelNotReadyError(
            "Featurebase was identified, but its messenger was not booted"
        ) from exc


class FeaturebaseAutoConfigurator(BaseAutoConfigurator):
    """Open Featurebase and bind its stable Messenger controls."""

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

        self._emit("INTERACTION", consts.FEATUREBASE_INTERACTION_DESCRIPTION)
        frame = await open_featurebase_composer(page)
        self._emit("TRIGGER", "opened Featurebase new-message composer")
        result = AutoConfigResult(
            input_selector=consts.FEATUREBASE_INPUT_SELECTOR,
            input_confidence=ConfidenceScore(value=1.0),
            submit_selector=consts.FEATUREBASE_SUBMIT_SELECTOR,
            submit_confidence=ConfidenceScore(value=1.0),
            response_selector=consts.FEATUREBASE_RESPONSE_SELECTOR,
            response_confidence=ConfidenceScore(value=1.0),
            discovery_frame=frame,
            iframe_selector=consts.FEATUREBASE_FRAME_SELECTOR,
            input_frame_path=[consts.FEATUREBASE_FRAME_SELECTOR],
            setup_actions=[InteractionAction(
                kind="featurebase_new_message", selector="window.Featurebase"
            )],
        )
        self._emit("CHAT FOUND", result.input_selector)
        return result

    def _emit(self, phase: str, detail: str) -> None:
        if self._progress_callback:
            self._progress_callback(phase, detail)
