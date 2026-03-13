"""Abstract base for auto-configuration strategies."""

from abc import ABC, abstractmethod

from playwright.async_api import Frame, Page

from .models import AutoConfigResult, ElementHint


class BaseAutoConfigurator(ABC):
    """Discovers input/submit/response selectors on a live page.

    Implementations may use algorithmic DOM analysis, LLM vision,
    or hybrid approaches.
    """

    @abstractmethod
    async def configure(
        self,
        page: Page | Frame,
        *,
        skip_response: bool = False,
        input_hint: ElementHint | None = None,
        submit_hint: ElementHint | None = None,
        response_hint: ElementHint | None = None,
    ) -> AutoConfigResult:
        """Analyze the page and return discovered selectors.

        Args:
            page: A Playwright Page already navigated to the target URL.
            skip_response: If True, skip the response element discovery phase.
            input_hint: Optional HTML-parsed hint for the input element.
            submit_hint: Optional HTML-parsed hint for the submit button.
            response_hint: Optional HTML-parsed hint for the response element.

        Returns:
            AutoConfigResult with discovered selectors and confidence scores.

        Raises:
            AutoConfigError: If discovery fails entirely.
        """
