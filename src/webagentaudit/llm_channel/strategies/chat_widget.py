"""Generic chat widget interaction strategy using configurable CSS selectors."""

import asyncio

from playwright.async_api import Frame, Page

from webagentaudit.core.exceptions import ChannelError, ChannelTimeoutError

from ..consts import RESPONSE_POLL_INTERVAL_MS, RESPONSE_STABLE_INTERVAL_MS
from .base import BaseInteractionStrategy

# Default selectors for common chat widget patterns
_DEFAULT_INPUT_SELECTORS = [
    "textarea[placeholder*='message' i]",
    "textarea[placeholder*='ask' i]",
    "textarea[placeholder*='type' i]",
    "textarea[aria-label*='message' i]",
    "textarea[aria-label*='chat' i]",
    "input[placeholder*='message' i]",
    "input[placeholder*='ask' i]",
    "[contenteditable='true'][role='textbox']",
    ".chat-input textarea",
    ".chat-input input",
]

_DEFAULT_SUBMIT_SELECTORS = [
    "button[type='submit']",
    "button[aria-label*='send' i]",
    "button[class*='send' i]",
    "button[data-testid*='send' i]",
    ".send-btn",
    ".chat-send",
]

_DEFAULT_RESPONSE_SELECTORS = [
    ".chat-message:last-child",
    "[data-testid='message-content']:last-child",
    ".bot-message:last-child",
    ".assistant-message:last-child",
    ".message.bot:last-child",
    ".chatbot-message.bot:last-child",
    "[class*='response']:last-child",
]


class ChatWidgetStrategy(BaseInteractionStrategy):
    """Generic strategy for interacting with standard chat widgets.

    Uses a configurable set of CSS selectors to find input fields,
    submit buttons, and response containers. Falls back to default
    selectors if none are provided.
    """

    def __init__(
        self,
        input_selector: str | None = None,
        submit_selector: str | None = None,
        response_selector: str | None = None,
    ) -> None:
        self._input_selector = input_selector
        self._submit_selector = submit_selector
        self._response_selector = response_selector
        self._resolved_input_selector: str | None = None
        self._resolved_submit_selector: str | None = None
        self._resolved_response_selector: str | None = None

    async def find_input(self, page: Page | Frame) -> bool:
        """Locate input, submit, and response elements on the page."""
        self._resolved_input_selector = await self._resolve_selector(
            page, self._input_selector, _DEFAULT_INPUT_SELECTORS
        )
        if not self._resolved_input_selector:
            return False

        self._resolved_submit_selector = await self._resolve_selector(
            page, self._submit_selector, _DEFAULT_SUBMIT_SELECTORS
        )
        self._resolved_response_selector = await self._resolve_selector(
            page, self._response_selector, _DEFAULT_RESPONSE_SELECTORS
        )

        return True

    async def send_message(self, page: Page | Frame, text: str) -> None:
        """Type text into the input and submit."""
        if not self._resolved_input_selector:
            raise ChannelError("Input element not found. Call find_input() first.")

        input_el = page.locator(self._resolved_input_selector).first
        await self._focus_element(input_el)
        await input_el.fill(text)

        if self._resolved_submit_selector:
            submit_el = page.locator(self._resolved_submit_selector).first
            await self._focus_element(submit_el)
        else:
            # Fall back to pressing Enter
            await input_el.press("Enter")

    async def wait_for_response(self, page: Page | Frame, timeout_ms: int) -> str:
        """Wait for the response text to stabilise within the timeout."""
        if not self._resolved_response_selector:
            # Try to find a response element now
            self._resolved_response_selector = await self._resolve_selector(
                page, self._response_selector, _DEFAULT_RESPONSE_SELECTORS
            )
            if not self._resolved_response_selector:
                raise ChannelError(
                    "Response element not found. Cannot wait for response."
                )

        poll_interval_s = RESPONSE_POLL_INTERVAL_MS / 1000
        stable_threshold_s = RESPONSE_STABLE_INTERVAL_MS / 1000
        timeout_s = timeout_ms / 1000

        previous_text = ""
        stable_elapsed = 0.0
        total_elapsed = 0.0

        while total_elapsed < timeout_s:
            await asyncio.sleep(poll_interval_s)
            total_elapsed += poll_interval_s

            current_text = await self._get_last_response_text(page)

            if current_text and current_text != previous_text:
                previous_text = current_text
                stable_elapsed = 0.0
            elif current_text:
                stable_elapsed += poll_interval_s
                if stable_elapsed >= stable_threshold_s:
                    return current_text

        if previous_text:
            return previous_text

        raise ChannelTimeoutError(
            f"No response received within {timeout_ms}ms"
        )

    async def get_response_html(self, page: Page | Frame) -> str | None:
        """Get the inner HTML of the last response element."""
        if not self._resolved_response_selector:
            return None
        try:
            elements = page.locator(self._resolved_response_selector)
            count = await elements.count()
            if count == 0:
                return None
            return await elements.last.inner_html()
        except Exception:
            return None

    async def _get_last_response_text(self, page: Page | Frame) -> str:
        """Extract text from the last response element."""
        if not self._resolved_response_selector:
            return ""
        try:
            elements = page.locator(self._resolved_response_selector)
            count = await elements.count()
            if count == 0:
                return ""
            return (await elements.last.inner_text()).strip()
        except Exception:
            return ""

    @staticmethod
    async def _resolve_selector(
        page: Page | Frame,
        explicit: str | None,
        defaults: list[str],
    ) -> str | None:
        """Resolve a selector: use the explicit one if provided, otherwise
        try each default selector until one matches an element on the page."""
        if explicit:
            try:
                count = await page.locator(explicit).count()
                if count > 0:
                    return explicit
            except Exception:
                pass
            return None  # Explicit selector didn't match; let caller fall back

        for selector in defaults:
            try:
                count = await page.locator(selector).count()
                if count > 0:
                    return selector
            except Exception:
                continue
        return None
