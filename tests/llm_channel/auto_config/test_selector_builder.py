"""Tests for SelectorBuilder: CSS selector construction from DOM elements."""

import pytest
from playwright.async_api import async_playwright

from webagentaudit.llm_channel.auto_config._selector_builder import SelectorBuilder
from webagentaudit.llm_channel.auto_config.models import ElementCandidate

# ---------------------------------------------------------------------------
# HTML fixtures
# ---------------------------------------------------------------------------

ELEMENT_WITH_ID_HTML = """\
<!DOCTYPE html>
<html>
<head><title>ID Test</title></head>
<body>
<div>
    <textarea id="the-chat-input" placeholder="Type here"
              style="width: 400px; height: 40px;"></textarea>
</div>
</body>
</html>
"""

ELEMENT_WITH_TESTID_HTML = """\
<!DOCTYPE html>
<html>
<head><title>TestID Test</title></head>
<body>
<div>
    <textarea data-testid="prompt-textarea" placeholder="Type here"
              style="width: 400px; height: 40px;"></textarea>
</div>
</body>
</html>
"""

ELEMENT_WITH_UNIQUE_CLASS_HTML = """\
<!DOCTYPE html>
<html>
<head><title>Class Test</title></head>
<body>
<div>
    <textarea class="chat-message-input" placeholder="Type here"
              style="width: 400px; height: 40px;"></textarea>
</div>
</body>
</html>
"""

ELEMENT_WITH_PLACEHOLDER_HTML = """\
<!DOCTYPE html>
<html>
<head><title>Placeholder Test</title></head>
<body>
<div>
    <textarea placeholder="Ask me anything" style="width: 400px; height: 40px;"></textarea>
    <textarea placeholder="Leave a comment" style="width: 400px; height: 40px;"></textarea>
</div>
</body>
</html>
"""

ELEMENT_NEEDING_ANCESTOR_HTML = """\
<!DOCTYPE html>
<html>
<head><title>Ancestor Test</title></head>
<body>
<div class="page-content">
    <div id="chat-panel">
        <textarea style="width: 400px; height: 40px;"></textarea>
    </div>
    <div id="notes-panel">
        <textarea style="width: 400px; height: 40px;"></textarea>
    </div>
</div>
</body>
</html>
"""

RESPONSE_CONTAINER_HTML = """\
<!DOCTYPE html>
<html>
<head><title>Response Container</title></head>
<body>
<div id="chat">
    <div id="messages">
        <div class="message bot-msg">First message</div>
        <div class="message bot-msg">Second message</div>
        <div class="message bot-msg">Latest reply from the bot</div>
    </div>
</div>
</body>
</html>
"""

RESPONSE_NO_CONTAINER_HTML = """\
<!DOCTYPE html>
<html>
<head><title>Response No Container</title></head>
<body>
<div id="chat">
    <div class="reply-bubble">Only one reply here</div>
</div>
</body>
</html>
"""


@pytest.fixture
async def browser():
    pw = await async_playwright().start()
    browser = await pw.chromium.launch(headless=True)
    yield browser
    await browser.close()
    await pw.stop()


@pytest.fixture
async def page(browser):
    context = await browser.new_context()
    pg = await context.new_page()
    yield pg
    await context.close()


@pytest.fixture
def builder():
    return SelectorBuilder()


class TestSelectorBuilderBuild:
    """Test SelectorBuilder.build() selector construction."""

    async def test_element_with_id(self, page, builder):
        """Element with an ID should return '#the-id' selector."""
        await page.set_content(ELEMENT_WITH_ID_HTML, wait_until="domcontentloaded")
        el = await page.query_selector("textarea")
        selector = await builder.build(el, page)
        assert selector == "#the-chat-input"

    async def test_element_with_data_testid(self, page, builder):
        """Element with data-testid should return '[data-testid=\"...\"]' selector."""
        await page.set_content(ELEMENT_WITH_TESTID_HTML, wait_until="domcontentloaded")
        el = await page.query_selector("textarea")
        selector = await builder.build(el, page)
        assert selector == '[data-testid="prompt-textarea"]'

    async def test_element_with_unique_class(self, page, builder):
        """Element with a unique class should return 'tag.classname' selector."""
        await page.set_content(ELEMENT_WITH_UNIQUE_CLASS_HTML, wait_until="domcontentloaded")
        el = await page.query_selector("textarea")
        selector = await builder.build(el, page)
        assert "chat-message-input" in selector
        assert selector.startswith("textarea")

    async def test_element_with_placeholder_attr(self, page, builder):
        """Element with placeholder should use it when other selectors aren't unique enough."""
        await page.set_content(ELEMENT_WITH_PLACEHOLDER_HTML, wait_until="domcontentloaded")
        el = await page.query_selector('textarea[placeholder="Ask me anything"]')
        selector = await builder.build(el, page)
        # Should use placeholder since there's no id, testid, or unique class
        assert "placeholder" in selector or "Ask me anything" in selector

    async def test_element_needing_ancestor_chain(self, page, builder):
        """When no unique attribute exists, should use ancestor chain with '>' format."""
        await page.set_content(ELEMENT_NEEDING_ANCESTOR_HTML, wait_until="domcontentloaded")
        el = await page.query_selector("#chat-panel textarea")
        selector = await builder.build(el, page)
        # Should include parent context since the textarea alone isn't unique
        assert ">" in selector or "#chat-panel" in selector

    async def test_built_selector_actually_matches(self, page, builder):
        """The built selector should actually find the element when queried."""
        await page.set_content(ELEMENT_WITH_ID_HTML, wait_until="domcontentloaded")
        el = await page.query_selector("textarea")
        selector = await builder.build(el, page)
        found = await page.query_selector(selector)
        assert found is not None


class TestSelectorBuilderResponseSelector:
    """Test SelectorBuilder.build_response_selector() for response elements."""

    async def test_response_with_multiple_siblings(self, page, builder):
        """Response element inside container with siblings should produce :last-of-type."""
        await page.set_content(RESPONSE_CONTAINER_HTML, wait_until="domcontentloaded")
        # Get the last .bot-msg element
        elements = await page.query_selector_all(".message.bot-msg")
        last_el = elements[-1]

        # First build a precise selector for this element
        precise_selector = await builder.build(last_el, page)

        # Build the response selector using a candidate
        candidate = ElementCandidate(
            tag_name="div",
            selector=precise_selector,
            classes=["message", "bot-msg"],
        )
        response_selector = await builder.build_response_selector(candidate, page)
        assert "last-of-type" in response_selector

    async def test_response_selector_matches_latest(self, page, builder):
        """The response selector should match the latest (last) message element."""
        await page.set_content(RESPONSE_CONTAINER_HTML, wait_until="domcontentloaded")
        elements = await page.query_selector_all(".message.bot-msg")
        last_el = elements[-1]

        precise_selector = await builder.build(last_el, page)
        candidate = ElementCandidate(
            tag_name="div",
            selector=precise_selector,
            classes=["message", "bot-msg"],
        )
        response_selector = await builder.build_response_selector(candidate, page)

        # Query the page with the built selector and verify it gets the latest
        matched = await page.query_selector(response_selector)
        assert matched is not None
        text = await matched.inner_text()
        assert "Latest reply" in text

    async def test_response_selector_uses_container_id(self, page, builder):
        """When container has an ID, the response selector should reference it."""
        await page.set_content(RESPONSE_CONTAINER_HTML, wait_until="domcontentloaded")
        elements = await page.query_selector_all(".message.bot-msg")
        last_el = elements[-1]

        precise_selector = await builder.build(last_el, page)
        candidate = ElementCandidate(
            tag_name="div",
            selector=precise_selector,
            classes=["message", "bot-msg"],
        )
        response_selector = await builder.build_response_selector(candidate, page)
        # #messages is the parent with multiple same-tag children
        assert "#messages" in response_selector

    async def test_single_child_fallback(self, page, builder):
        """When only one child exists (no siblings), should fallback gracefully."""
        await page.set_content(RESPONSE_NO_CONTAINER_HTML, wait_until="domcontentloaded")
        el = await page.query_selector(".reply-bubble")
        precise_selector = await builder.build(el, page)

        candidate = ElementCandidate(
            tag_name="div",
            selector=precise_selector,
            classes=["reply-bubble"],
        )
        response_selector = await builder.build_response_selector(candidate, page)
        # With only one child, it may fall back to class-based :last-of-type or the precise selector
        assert response_selector is not None
        assert len(response_selector) > 0
