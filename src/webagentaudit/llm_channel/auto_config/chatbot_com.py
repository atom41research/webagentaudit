"""Focused auto-configuration for ChatBot.com widgets and handoffs."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from urllib.parse import urlparse

from playwright.async_api import Frame, Page

from webagentaudit.core.models import ConfidenceScore
from webagentaudit.llm_channel.models import InteractionAction

from . import consts
from ._input_finder import InputFinder
from ._preflight import PreflightDismissal
from ._selector_builder import SelectorBuilder
from .base import BaseAutoConfigurator
from .models import AutoConfigResult, ElementHint


class ChatbotComAutoConfigurator(BaseAutoConfigurator):
    """Open ChatBot.com UI variants and return a replayable interaction plan."""

    def __init__(self, progress_callback: Callable[[str, str], None] | None = None) -> None:
        self._input_finder = InputFinder(SelectorBuilder())
        self._preflight = PreflightDismissal(SelectorBuilder())
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
        del skip_response, submit_hint, response_hint
        if not isinstance(page, Page):
            return AutoConfigResult()

        setup_actions: list[InteractionAction] = []
        for _ in range(consts.CHATBOT_COM_MAX_BLOCKERS):
            dismissed = await self._preflight.dismiss_one(page)
            if dismissed is None:
                break
            setup_actions.append(InteractionAction(
                kind="dismiss", selector=dismissed, optional=True
            ))
            self._emit("BLOCKER", f"dismissed {dismissed}")

        host = (urlparse(page.url).hostname or "").removeprefix("www.")
        frame = await self._open_direct_widget(page, setup_actions)
        if frame is not None:
            await self._open_direct_conversation(frame, host, setup_actions)
            result = await self._result_for_direct(frame, setup_actions, input_hint)
            if result.input_selector:
                return result

        result = await self._open_livechat_handoff(page, host, setup_actions)
        if result.input_selector:
            return result
        self._emit("DISCOVER", "ChatBot.com widget exposed no usable input")
        return AutoConfigResult()

    async def _open_direct_widget(
        self, page: Page, actions: list[InteractionAction]
    ) -> Frame | None:
        try:
            elapsed = 0
            while elapsed < consts.CHATBOT_COM_WAIT_MS:
                try:
                    await page.wait_for_function(
                        "window.BE_API && typeof window.BE_API.openChatWindow === 'function'",
                        timeout=consts.DISCOVERY_INPUT_POLL_MS,
                    )
                    self._emit(
                        "INTERACTION",
                        consts.PROGRAMMATIC_INTERACTION_DESCRIPTIONS[
                            "chatbot_open"
                        ],
                    )
                    await page.evaluate("window.BE_API.openChatWindow()")
                    break
                except Exception:
                    await asyncio.sleep(consts.DISCOVERY_INPUT_POLL_MS / 1000)
                    elapsed += consts.DISCOVERY_INPUT_POLL_MS
            else:
                return None
            actions.append(InteractionAction(
                kind="chatbot_open", selector="window.BE_API.openChatWindow"
            ))
            self._emit("TRIGGER", "opened ChatBot.com widget")
        except Exception:
            return None
        return await self._wait_for_frame(page, consts.CHATBOT_COM_FRAME_SELECTOR)

    async def _open_direct_conversation(
        self, frame: Frame, host: str, actions: list[InteractionAction]
    ) -> None:
        start = frame.locator(consts.CHATBOT_COM_START_SELECTOR).first
        try:
            await start.wait_for(state="visible", timeout=consts.CHATBOT_COM_WAIT_MS)
        except Exception:
            return
        if await start.count():
            await start.click(timeout=consts.CHATBOT_COM_WAIT_MS)
            actions.append(InteractionAction(
                kind="trigger", selector=consts.CHATBOT_COM_START_SELECTOR,
                frame_path=[consts.CHATBOT_COM_FRAME_SELECTOR],
            ))
            self._emit("TRIGGER", "started ChatBot.com conversation")

        option = consts.CHATBOT_COM_ONBOARDING_SELECTORS.get(host)
        if option:
            control = frame.locator(option).first
            if await control.count():
                await control.click(timeout=consts.CHATBOT_COM_WAIT_MS)
                actions.append(InteractionAction(
                    kind="trigger", selector=option,
                    frame_path=[consts.CHATBOT_COM_FRAME_SELECTOR],
                ))
                await asyncio.sleep(consts.CHATBOT_COM_SETUP_SETTLE_MS / 1000)
                self._emit("TRIGGER", f"completed {host} onboarding")

    async def _result_for_direct(
        self,
        frame: Frame,
        actions: list[InteractionAction],
        hint: ElementHint | None,
    ) -> AutoConfigResult:
        scored = None
        elapsed = 0
        while scored is None and elapsed < consts.CHATBOT_COM_WAIT_MS:
            scored = await self._input_finder.find(frame, hint=hint)
            if scored is None:
                await asyncio.sleep(consts.DISCOVERY_INPUT_POLL_MS / 1000)
                elapsed += consts.DISCOVERY_INPUT_POLL_MS
        if scored is None:
            return AutoConfigResult()
        result = AutoConfigResult(
            input_selector=scored.candidate.selector,
            input_confidence=ConfidenceScore(value=1.0),
            submit_selector=consts.CHATBOT_COM_SUBMIT_SELECTOR,
            submit_confidence=ConfidenceScore(value=1.0),
            discovery_frame=frame,
            iframe_selector=consts.CHATBOT_COM_FRAME_SELECTOR,
            input_frame_path=[consts.CHATBOT_COM_FRAME_SELECTOR],
            setup_actions=actions,
        )
        self._emit("CHAT FOUND", result.input_selector)
        return result

    async def _open_livechat_handoff(
        self, page: Page, host: str, actions: list[InteractionAction]
    ) -> AutoConfigResult:
        start_frame = await self._wait_for_frame(
            page, consts.CHATBOT_COM_LIVECHAT_MINIMIZED_SELECTOR
        )
        if start_frame is None:
            return AutoConfigResult()
        await start_frame.locator("button").first.click(timeout=consts.CHATBOT_COM_WAIT_MS)
        actions.append(InteractionAction(
            kind="trigger", selector="button",
            frame_path=[consts.CHATBOT_COM_LIVECHAT_MINIMIZED_SELECTOR],
        ))

        livechat = await self._wait_for_frame(page, consts.CHATBOT_COM_LIVECHAT_SELECTOR)
        handoff_selector = consts.CHATBOT_COM_LIVECHAT_START_SELECTORS.get(host)
        if livechat is None or handoff_selector is None:
            return AutoConfigResult()
        handoff = livechat.locator(handoff_selector).first
        await handoff.click(timeout=consts.CHATBOT_COM_WAIT_MS)
        actions.append(InteractionAction(
            kind="trigger", selector=handoff_selector,
            frame_path=[consts.CHATBOT_COM_LIVECHAT_SELECTOR],
        ))
        moment = livechat.locator(consts.CHATBOT_COM_MOMENT_SELECTOR).first
        await moment.wait_for(state="visible", timeout=consts.CHATBOT_COM_WAIT_MS)
        await moment.click()
        actions.append(InteractionAction(
            kind="trigger", selector=consts.CHATBOT_COM_MOMENT_SELECTOR,
            frame_path=[consts.CHATBOT_COM_LIVECHAT_SELECTOR],
        ))

        frame_path = [
            consts.CHATBOT_COM_LIVECHAT_SELECTOR,
            consts.CHATBOT_COM_MOMENT_FRAME_SELECTOR,
        ]
        frame = await self._wait_for_nested_frame(page, frame_path)
        if frame is None:
            return AutoConfigResult()
        result = AutoConfigResult(
            input_selector=consts.CHATBOT_COM_HANDOFF_INPUT_SELECTOR,
            input_confidence=ConfidenceScore(value=1.0),
            submit_selector=consts.CHATBOT_COM_HANDOFF_SUBMIT_SELECTOR,
            submit_confidence=ConfidenceScore(value=1.0),
            discovery_frame=frame,
            iframe_selector=consts.CHATBOT_COM_MOMENT_FRAME_SELECTOR,
            input_frame_path=frame_path,
            setup_actions=actions,
        )
        self._emit("CHAT FOUND", result.input_selector)
        return result

    async def _wait_for_frame(self, page: Page, selector: str) -> Frame | None:
        return await self._wait_for_nested_frame(page, [selector])

    async def _wait_for_nested_frame(
        self, page: Page, path: list[str]
    ) -> Frame | None:
        elapsed = 0
        while elapsed < consts.CHATBOT_COM_WAIT_MS:
            target: Page | Frame = page
            try:
                for selector in path:
                    iframe = target.locator(selector).first
                    if await iframe.count() == 0:
                        raise RuntimeError("frame element not found")
                    handle = await iframe.element_handle(timeout=500)
                    frame = await handle.content_frame() if handle else None
                    if frame is None:
                        raise RuntimeError("frame unavailable")
                    target = frame
                return target if isinstance(target, Frame) else None
            except Exception:
                await asyncio.sleep(consts.DISCOVERY_INPUT_POLL_MS / 1000)
                elapsed += consts.DISCOVERY_INPUT_POLL_MS
        return None

    def _emit(self, phase: str, detail: str) -> None:
        if self._progress_callback:
            self._progress_callback(phase, detail)
