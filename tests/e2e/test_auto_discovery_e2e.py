"""End-to-end tests for the auto-discovery hint system.

These tests run AlgorithmicAutoConfigurator.configure() against HTML fixture
pages served by a local HTTP server (docs/interactive/).  They verify that
hint options (input_hint, submit_hint) correctly override auto-discovery when
decoy elements score higher than the real chat controls.

Fixture pages
-------------
- ambiguous-saas.html:
    Decoy: feedback textarea (.feedback-input-field) scores ~0.63.
    Real:  chat input (.xk-prompt-field) scores ~0.34.
    With input_hint the real one wins.

- ambiguous-buttons.html:
    Decoy: newsletter "Send" button (.newsletter-send-btn) with keyword text.
    Real:  icon-only SVG button (.xk-action-trigger) with no text label.
    With submit_hint the real one wins.
"""

from __future__ import annotations

import pytest
from playwright.async_api import Page

from webagentaudit.llm_channel.auto_config import AlgorithmicAutoConfigurator
from webagentaudit.llm_channel.auto_config._hint_matcher import parse_hint

pytestmark = pytest.mark.e2e


# ---------------------------------------------------------------------------
# Input hint tests (ambiguous-saas.html)
# ---------------------------------------------------------------------------


class TestInputHintDiscovery:
    """Tests that --input-hint overcomes decoy elements on ambiguous pages."""

    async def test_without_hint_picks_decoy(self, page, demo_server):
        """Without hint, auto-discovery picks the feedback textarea (decoy)."""
        url = f"{demo_server}/interactive/ambiguous-saas.html"
        await page.goto(url, wait_until="domcontentloaded")
        await page.wait_for_timeout(500)

        configurator = AlgorithmicAutoConfigurator()
        result = await configurator.configure(page, skip_response=True)

        # Without hint, the feedback textarea should win (higher score)
        assert result.input_selector is not None
        assert "xk-prompt-field" not in result.input_selector, (
            "Without hint, should NOT pick the real chat input"
        )

    async def test_with_hint_picks_real_input(self, page, demo_server):
        """With matching hint, auto-discovery picks the real chat input."""
        url = f"{demo_server}/interactive/ambiguous-saas.html"
        await page.goto(url, wait_until="domcontentloaded")
        await page.wait_for_timeout(500)

        hint = parse_hint('<input class="xk-prompt-field" type="text">')
        configurator = AlgorithmicAutoConfigurator()
        result = await configurator.configure(page, skip_response=True, input_hint=hint)

        assert result.input_selector is not None
        assert "xk-prompt-field" in result.input_selector, (
            f"With hint, should pick the real chat input. Got: {result.input_selector}"
        )

    async def test_hint_boost_is_significant(self, page, demo_server):
        """The hint-boosted score should be significantly higher than baseline."""
        # This is tested implicitly by the above tests passing,
        # but we verify the selector difference explicitly
        url = f"{demo_server}/interactive/ambiguous-saas.html"
        await page.goto(url, wait_until="domcontentloaded")
        await page.wait_for_timeout(500)

        configurator = AlgorithmicAutoConfigurator()

        # Without hint
        result_no_hint = await configurator.configure(page, skip_response=True)

        # With hint
        hint = parse_hint('<input class="xk-prompt-field" type="text">')
        result_with_hint = await configurator.configure(page, skip_response=True, input_hint=hint)

        # They should pick DIFFERENT elements
        assert result_no_hint.input_selector != result_with_hint.input_selector, (
            "Hint should change which element is selected"
        )


# ---------------------------------------------------------------------------
# Submit hint tests (ambiguous-buttons.html)
# ---------------------------------------------------------------------------


class TestSubmitHintDiscovery:
    """Tests that --submit-hint overcomes decoy buttons on ambiguous pages."""

    async def test_without_hint_picks_decoy_button(self, page, demo_server):
        """Without hint, auto-discovery picks the newsletter Send button (decoy)."""
        url = f"{demo_server}/interactive/ambiguous-buttons.html"
        await page.goto(url, wait_until="domcontentloaded")
        await page.wait_for_timeout(500)

        configurator = AlgorithmicAutoConfigurator()
        result = await configurator.configure(page, skip_response=True)

        assert result.submit_selector is not None
        assert "xk-action-trigger" not in result.submit_selector, (
            "Without hint, should NOT pick the real send button"
        )

    async def test_with_hint_picks_real_button(self, page, demo_server):
        """With matching hint, auto-discovery picks the real send button."""
        url = f"{demo_server}/interactive/ambiguous-buttons.html"
        await page.goto(url, wait_until="domcontentloaded")
        await page.wait_for_timeout(500)

        hint = parse_hint('<button class="xk-action-trigger"><svg></svg></button>')
        configurator = AlgorithmicAutoConfigurator()
        result = await configurator.configure(page, skip_response=True, submit_hint=hint)

        assert result.submit_selector is not None
        assert "xk-action-trigger" in result.submit_selector, (
            f"With hint, should pick the real send button. Got: {result.submit_selector}"
        )
