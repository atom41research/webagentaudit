"""Tests for ResponseFinder: interactive response element discovery via DOM diffing."""

import pytest
from playwright.async_api import async_playwright

from webagentaudit.llm_channel.auto_config._response_finder import ResponseFinder
from webagentaudit.llm_channel.auto_config._selector_builder import SelectorBuilder
from webagentaudit.llm_channel.auto_config import consts

# ---------------------------------------------------------------------------
# HTML fixtures
# ---------------------------------------------------------------------------

ECHO_CHAT_HTML = """\
<!DOCTYPE html>
<html>
<head><title>Echo Chat</title></head>
<body>
<div id="chat" style="position: relative;">
    <div id="messages">
        <div class="message bot-response">Welcome! How can I help?</div>
    </div>
    <textarea id="input" placeholder="Type a message"
              style="width: 400px; height: 40px;"></textarea>
    <button id="send" style="width: 60px; height: 30px;">Send</button>
</div>
<script>
document.getElementById('send').addEventListener('click', function() {
    var input = document.getElementById('input');
    var text = input.value;
    input.value = '';
    setTimeout(function() {
        var div = document.createElement('div');
        div.className = 'message bot-response';
        div.textContent = 'Bot: ' + text;
        document.getElementById('messages').appendChild(div);
    }, 300);
});
</script>
</body>
</html>
"""

NO_RESPONSE_HTML = """\
<!DOCTYPE html>
<html>
<head><title>No Response</title></head>
<body>
<div id="chat">
    <textarea id="input" placeholder="Type a message"
              style="width: 400px; height: 40px;"></textarea>
    <button id="send" style="width: 60px; height: 30px;">Send</button>
</div>
<script>
document.getElementById('send').addEventListener('click', function() {
    // Does nothing - no response is generated
    var input = document.getElementById('input');
    input.value = '';
});
</script>
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
def finder():
    return ResponseFinder(SelectorBuilder())


class TestResponseFinderBasic:
    """Test ResponseFinder.find() with simulated chat pages."""

    async def test_response_element_discovered(self, page, finder):
        """After sending a probe, the response element should be discovered."""
        await page.set_content(ECHO_CHAT_HTML, wait_until="domcontentloaded")
        result, response_text = await finder.find(
            page, input_selector="#input", submit_selector="#send"
        )
        assert result is not None
        assert response_text is not None

    async def test_response_text_contains_bot_reply(self, page, finder):
        """The discovered response text should contain the bot's response."""
        await page.set_content(ECHO_CHAT_HTML, wait_until="domcontentloaded")
        result, response_text = await finder.find(
            page, input_selector="#input", submit_selector="#send"
        )
        assert result is not None
        assert response_text is not None
        # The bot echoes with "Bot: " prefix + the probe message
        assert "Bot:" in response_text or consts.RESPONSE_PROBE_MESSAGE.lower() in response_text.lower()

    async def test_response_selector_generalized(self, page, finder):
        """The selector for the response element should be generalized with :last-of-type."""
        await page.set_content(ECHO_CHAT_HTML, wait_until="domcontentloaded")
        result, _ = await finder.find(
            page, input_selector="#input", submit_selector="#send"
        )
        assert result is not None
        # The build_response_selector should produce a :last-of-type selector
        # because there are multiple .bot-response siblings inside #messages
        assert "last-of-type" in result.candidate.selector

    async def test_no_response_returns_none(self, page, finder):
        """When no DOM changes occur after submitting, should return (None, None)."""
        await page.set_content(NO_RESPONSE_HTML, wait_until="domcontentloaded")
        result, response_text = await finder.find(
            page, input_selector="#input", submit_selector="#send"
        )
        assert result is None
        assert response_text is None

    async def test_response_candidate_has_context_score(self, page, finder):
        """The response element should score on context due to 'bot-response' class."""
        await page.set_content(ECHO_CHAT_HTML, wait_until="domcontentloaded")
        result, _ = await finder.find(
            page, input_selector="#input", submit_selector="#send"
        )
        assert result is not None
        # "bot" and "response" are in the context keywords
        assert result.score_breakdown.get("context", 0) > 0.0

    async def test_response_with_enter_key_submit(self, page, finder):
        """ResponseFinder should work when submit_selector is None (Enter key)."""
        enter_chat_html = """\
<!DOCTYPE html>
<html>
<head><title>Enter Chat</title></head>
<body>
<div id="chat">
    <div id="messages">
        <div class="message bot-msg">Hello!</div>
    </div>
    <textarea id="input" placeholder="Type here"
              style="width: 400px; height: 40px;"></textarea>
</div>
<script>
document.getElementById('input').addEventListener('keydown', function(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        var text = this.value;
        this.value = '';
        setTimeout(function() {
            var div = document.createElement('div');
            div.className = 'message bot-msg';
            div.textContent = 'Reply: ' + text;
            document.getElementById('messages').appendChild(div);
        }, 300);
    }
});
</script>
</body>
</html>
"""
        await page.set_content(enter_chat_html, wait_until="domcontentloaded")
        result, response_text = await finder.find(
            page, input_selector="#input", submit_selector=None
        )
        assert result is not None
        assert response_text is not None
        assert "Reply:" in response_text
