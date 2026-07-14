"""Tests for preflight onboarding/modal dismissal."""

import pytest

from webagentaudit.llm_channel.auto_config._preflight import PreflightDismissal

pytestmark = pytest.mark.browser


SETUP_OVERLAYS_HTML = """\
<!DOCTYPE html><html><body>
<textarea id="chat-input"></textarea>
<div class="setup" style="position: fixed; inset: 0; z-index: 1; background: white;">
  <button onclick="this.parentElement.remove()">Skip setup</button>
</div>
<div class="onboarding-overlay" style="position: fixed; inset: 0; z-index: 2; background: white;">
  <button onclick="this.parentElement.remove()">Skip setup</button>
</div>
</body></html>
"""


async def test_dismisses_stacked_setup_overlays_top_down(page):
    await page.set_content(SETUP_OVERLAYS_HTML)

    assert await PreflightDismissal().dismiss(page) == 2
    assert await page.locator(".setup, .onboarding-overlay").count() == 0


async def test_does_not_click_general_skip_without_modal_markup(page):
    await page.set_content('<button id="skip" onclick="this.remove()">Skip this article</button>')

    assert await PreflightDismissal().dismiss(page) == 0
    assert await page.locator("#skip").count() == 1


async def test_dismisses_explicit_skip_setup_without_modal_markup(page):
    """Some onboarding controls have no dialog/overlay semantic wrapper."""
    await page.set_content(
        '<button class="text-xs" onclick="this.remove()">Skip setup</button>'
    )

    assert await PreflightDismissal().dismiss(page) == 1
    assert await page.locator("button").count() == 0
