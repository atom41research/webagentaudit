"""Tests for the selector-based browser interaction strategy."""

import pytest

from webagentaudit.llm_channel.strategies.custom import CustomStrategy

pytestmark = pytest.mark.browser


async def test_fill_does_not_make_a_redundant_input_click(page):
    """Typing should not need a separate click that can be blocked by UI chrome."""
    await page.set_content(
        '<textarea id="chat" onclick="window.clicks = (window.clicks || 0) + 1"></textarea>'
    )
    strategy = CustomStrategy("#chat", "body")

    await strategy.send_message(page, "Hello")

    assert (await page.locator("#chat").input_value()).startswith("Hello")
    assert await page.evaluate("window.clicks || 0") == 0


async def test_replays_discovered_trigger(page):
    """A fresh assessment page opens the launcher found during discovery."""
    await page.set_content(
        '<button id="launcher" onclick="chat.hidden = false">Open</button>'
        '<div id="chat" hidden><textarea></textarea></div>'
    )
    strategy = CustomStrategy("textarea", "#chat", trigger_selector="#launcher")

    await strategy.activate_trigger(page)

    assert await page.locator("#chat").is_visible()


async def test_reads_consecutive_identical_response_elements(page, monkeypatch):
    """A new response node counts even when its content matches the previous one."""
    from webagentaudit.llm_channel.strategies import custom

    monkeypatch.setattr(custom, "RESPONSE_STABLE_INTERVAL_MS", 100)
    monkeypatch.setattr(custom, "RESPONSE_POLL_INTERVAL_MS", 20)
    await page.set_content(
        '<div id="responses"><div class="bot">same reply</div></div>'
    )
    strategy = CustomStrategy("body", ".bot:last-child")
    await strategy.prepare_response(page)

    await page.locator("#responses").evaluate(
        "container => {"
        "  const response = document.createElement('div');"
        "  response.className = 'bot';"
        "  response.textContent = 'same reply';"
        "  container.appendChild(response);"
        "}"
    )

    assert await strategy.wait_for_response(page, 1000) == "same reply"
