"""Focused auto-configuration for Voiceflow web chat widgets."""

from __future__ import annotations

from collections.abc import Callable

from playwright.async_api import Frame, Page

from webagentaudit.core.exceptions import ChannelNotReadyError
from webagentaudit.core.models import ConfidenceScore
from webagentaudit.llm_channel.models import InteractionAction

from . import consts
from .base import BaseAutoConfigurator
from .models import AutoConfigResult, ElementHint


async def open_voiceflow_widget(page: Page) -> None:
    """Open Voiceflow through its public widget API."""
    try:
        await page.wait_for_function(
            "typeof window.voiceflow?.chat?.open === 'function'",
            timeout=consts.VOICEFLOW_WAIT_MS,
        )
        await page.evaluate("window.voiceflow.chat.open()")
    except Exception as exc:
        raise ChannelNotReadyError(
            "Voiceflow was identified, but its widget API did not become available"
        ) from exc


class VoiceflowAutoConfigurator(BaseAutoConfigurator):
    """Open Voiceflow and bind its shadow-root composer."""

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

        await open_voiceflow_widget(page)
        self._emit("TRIGGER", "opened Voiceflow widget")
        try:
            await page.locator(
                f"{consts.VOICEFLOW_INPUT_SELECTOR}:visible"
            ).first.wait_for(state="visible", timeout=consts.VOICEFLOW_WAIT_MS)
        except Exception as exc:
            raise ChannelNotReadyError(
                "Voiceflow opened, but did not render a usable chat composer"
            ) from exc

        result = AutoConfigResult(
            input_selector=consts.VOICEFLOW_INPUT_SELECTOR,
            input_confidence=ConfidenceScore(value=1.0),
            response_selector=consts.VOICEFLOW_RESPONSE_SELECTOR,
            response_confidence=ConfidenceScore(value=1.0),
            setup_actions=[InteractionAction(
                kind="voiceflow_open", selector="window.voiceflow.chat"
            )],
            use_enter_to_submit=True,
            submit_confidence=ConfidenceScore(value=0.5),
        )
        self._emit("CHAT FOUND", result.input_selector)
        return result

    def _emit(self, phase: str, detail: str) -> None:
        if self._progress_callback:
            self._progress_callback(phase, detail)
