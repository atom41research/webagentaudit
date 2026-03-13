"""Abstract base for interaction strategies."""

from abc import ABC, abstractmethod


class BaseStrategy(ABC):
    """Defines how to interact with a specific type of LLM widget."""

    @abstractmethod
    async def find_input(self, page) -> bool:
        """Check whether the input element exists on the page."""

    @abstractmethod
    async def send_message(self, page, text: str) -> None:
        """Type and submit a message."""

    @abstractmethod
    async def wait_for_response(self, page, timeout_ms: int) -> str:
        """Wait for the LLM response text to stabilise and return it."""

    async def get_response(self, page, timeout_ms: int) -> str | None:
        """Wait for and extract the LLM response text.

        Default implementation delegates to ``wait_for_response``.
        """
        return await self.wait_for_response(page, timeout_ms)

    @staticmethod
    async def _focus_element(element) -> None:
        """Scroll an element into view and click it."""
        await element.scroll_into_view_if_needed()
        await element.click()

    @staticmethod
    def _visible(page, selector: str):
        """Return a Playwright locator filtered to visible elements."""
        return page.locator(selector).locator("visible=true")


# Alias for backward compatibility
BaseInteractionStrategy = BaseStrategy
