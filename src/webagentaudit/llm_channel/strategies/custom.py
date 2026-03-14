"""Custom interaction strategy using user-provided CSS selectors."""

import asyncio
import logging

from playwright.async_api import Frame, Page

from webagentaudit.core.exceptions import ChannelError, ChannelTimeoutError

from ..consts import RESPONSE_POLL_INTERVAL_MS, RESPONSE_STABLE_INTERVAL_MS
from .base import BaseInteractionStrategy

logger = logging.getLogger(__name__)


class CustomStrategy(BaseInteractionStrategy):
    """Strategy that uses explicit, user-provided CSS selectors.

    Unlike ChatWidgetStrategy, this strategy does not attempt to auto-detect
    elements. All selectors must be provided by the caller.
    """

    def __init__(
        self,
        input_selector: str,
        response_selector: str,
        submit_selector: str | None = None,
        iframe_selector: str | None = None,
    ) -> None:
        if not input_selector:
            raise ValueError("input_selector is required for CustomStrategy")
        if not response_selector:
            raise ValueError("response_selector is required for CustomStrategy")

        self._input_selector = input_selector
        self._submit_selector = submit_selector
        self._response_selector = response_selector
        self._iframe_selector = iframe_selector

    @property
    def iframe_selector(self) -> str | None:
        return self._iframe_selector

    async def find_input(self, page: Page | Frame) -> bool:
        """Check that the user-provided input selector matches a visible element."""
        try:
            count = await self._visible(page, self._input_selector).count()
            logger.debug("find_input: '%s' matched %d visible element(s)", self._input_selector, count)
            return count > 0
        except Exception:
            return False

    async def send_message(self, page: Page | Frame, text: str) -> None:
        """Type text into the input and submit using user-provided selectors."""
        input_el = self._visible(page, self._input_selector).first
        logger.debug("send_message: focusing input '%s'", self._input_selector)

        try:
            await self._focus_element(input_el)
        except Exception as exc:
            raise ChannelError(
                f"Could not focus input element '{self._input_selector}': {exc}"
            ) from exc

        logger.debug("send_message: filling text (%d chars)", len(text))
        await input_el.fill(text)

        if self._submit_selector:
            submit_el = self._visible(page, self._submit_selector).first
            logger.debug("send_message: clicking submit '%s'", self._submit_selector)
            try:
                await self._focus_element(submit_el)
            except Exception as exc:
                raise ChannelError(
                    f"Could not focus submit button '{self._submit_selector}': {exc}"
                ) from exc
        else:
            logger.debug("send_message: pressing Enter")
            await input_el.press("Enter")

    async def wait_for_response(self, page: Page | Frame, timeout_ms: int) -> str:
        """Wait for response text to stabilise.

        Captures the baseline text before waiting so we can detect
        actual changes (not just pre-existing content).
        """
        logger.debug("wait_for_response: selector='%s', timeout=%dms", self._response_selector, timeout_ms)
        poll_interval_s = RESPONSE_POLL_INTERVAL_MS / 1000
        stable_threshold_s = RESPONSE_STABLE_INTERVAL_MS / 1000
        timeout_s = timeout_ms / 1000

        # Capture baseline: text that was already visible before our message
        baseline_text = await self._get_response_text(page)
        if baseline_text:
            logger.debug("wait_for_response: baseline text (%d chars): '%s...'",
                         len(baseline_text), baseline_text[:80].replace("\n", " "))

        previous_text = ""
        stable_elapsed = 0.0
        total_elapsed = 0.0

        while total_elapsed < timeout_s:
            await asyncio.sleep(poll_interval_s)
            total_elapsed += poll_interval_s

            current_text = await self._get_response_text(page)

            # Skip if text hasn't changed from baseline
            if current_text == baseline_text:
                continue

            if current_text and current_text != previous_text:
                preview = current_text[:80].replace("\n", " ")
                logger.debug("wait_for_response: text changed (%.1fs) '%s...'", total_elapsed, preview)
                previous_text = current_text
                stable_elapsed = 0.0
            elif current_text:
                stable_elapsed += poll_interval_s
                if stable_elapsed >= stable_threshold_s:
                    logger.debug("wait_for_response: stable after %.1fs (%d chars)", total_elapsed, len(current_text))
                    return current_text

        if previous_text:
            logger.debug("wait_for_response: timeout but have text (%d chars)", len(previous_text))
            return previous_text

        raise ChannelTimeoutError(
            f"No response received within {timeout_ms}ms"
        )

    async def get_response_html(self, page: Page | Frame) -> str | None:
        """Get the inner HTML of the response element."""
        try:
            elements = page.locator(self._response_selector)
            count = await elements.count()
            if count == 0:
                return None
            return await elements.last.inner_html()
        except Exception:
            return None

    async def _get_response_text(self, page: Page | Frame) -> str:
        """Extract text from the response element."""
        try:
            elements = page.locator(self._response_selector)
            count = await elements.count()
            if count == 0:
                return ""
            return (await elements.last.inner_text()).strip()
        except Exception:
            return ""
