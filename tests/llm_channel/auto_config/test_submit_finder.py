"""Tests for SubmitFinder: algorithmic submit button discovery and scoring."""

import pytest
from playwright.async_api import Page, async_playwright

from webagentaudit.llm_channel.auto_config._dom_utils import extract_element_props
from webagentaudit.llm_channel.auto_config._selector_builder import SelectorBuilder
from webagentaudit.llm_channel.auto_config._submit_finder import SubmitFinder
from webagentaudit.llm_channel.auto_config.models import ElementCandidate

# ---------------------------------------------------------------------------
# HTML fixtures — input and button are laid out inline (no absolute positioning)
# so that Playwright renders them close together naturally.
# ---------------------------------------------------------------------------

SEND_BUTTON_HTML = """\
<!DOCTYPE html>
<html>
<head><title>Chat</title></head>
<body>
<div class="chat-container" style="display: flex; align-items: center; gap: 4px; margin-top: 500px;">
    <textarea id="chat-input" placeholder="Type a message"
              style="width: 200px; height: 40px;"></textarea>
    <button id="send-btn" style="width: 60px; height: 30px;">Send</button>
</div>
</body>
</html>
"""

SVG_ICON_BUTTON_HTML = """\
<!DOCTYPE html>
<html>
<head><title>Chat</title></head>
<body>
<div class="chat-container" style="display: flex; align-items: center; gap: 4px; margin-top: 500px;">
    <textarea id="chat-input" placeholder="Type a message"
              style="width: 200px; height: 40px;"></textarea>
    <button id="icon-btn" aria-label="Send message" style="width: 40px; height: 40px;">
        <svg viewBox="0 0 24 24"><path d="M2 21l21-9L2 3v7l15 2-15 2z"/></svg>
    </button>
</div>
</body>
</html>
"""

SUBMIT_TYPE_BUTTON_HTML = """\
<!DOCTYPE html>
<html>
<head><title>Chat</title></head>
<body>
<div class="chat-container" style="display: flex; align-items: center; gap: 4px; margin-top: 500px;">
    <textarea id="chat-input" placeholder="Type a message"
              style="width: 200px; height: 40px;"></textarea>
    <input type="submit" value="Go" style="width: 60px; height: 30px;">
</div>
</body>
</html>
"""

SEND_CLASS_BUTTON_HTML = """\
<!DOCTYPE html>
<html>
<head><title>Chat</title></head>
<body>
<div class="chat-container" style="display: flex; align-items: center; gap: 4px; margin-top: 500px;">
    <textarea id="chat-input" placeholder="Type a message"
              style="width: 200px; height: 40px;"></textarea>
    <button class="send-btn" style="width: 60px; height: 30px;">Submit</button>
</div>
</body>
</html>
"""

FAR_BUTTON_HTML = """\
<!DOCTYPE html>
<html>
<head><title>Chat</title></head>
<body>
<div style="position: relative; height: 800px;">
    <button id="far-btn"
            style="position: absolute; top: 20px; left: 20px; width: 60px; height: 30px;">
        Send
    </button>
    <textarea id="chat-input" placeholder="Type a message"
              style="position: absolute; top: 600px; left: 100px; width: 400px; height: 40px;"></textarea>
</div>
</body>
</html>
"""

NO_BUTTONS_HTML = """\
<!DOCTYPE html>
<html>
<head><title>Chat</title></head>
<body>
<div class="chat-container">
    <textarea id="chat-input" placeholder="Type a message"
              style="width: 400px; height: 40px;"></textarea>
</div>
</body>
</html>
"""

MULTIPLE_BUTTONS_HTML = """\
<!DOCTYPE html>
<html>
<head><title>Chat</title></head>
<body>
<div style="position: relative; height: 800px;">
    <!-- Login button far away at the top -->
    <button id="login-btn"
            style="position: absolute; top: 20px; left: 50px; width: 80px; height: 30px;">
        Login
    </button>
    <!-- Chat input + Send button in a flex row near the bottom -->
    <div style="display: flex; align-items: center; gap: 4px;
                position: absolute; top: 600px; left: 100px;">
        <textarea id="chat-input" placeholder="Type a message"
                  style="width: 200px; height: 40px;"></textarea>
        <button id="send-btn" class="send-btn" style="width: 60px; height: 30px;">Send</button>
    </div>
</div>
</body>
</html>
"""


async def _get_input_candidate(pg: Page) -> ElementCandidate:
    """Extract a real ElementCandidate from the #chat-input element on the page."""
    el = await pg.query_selector("#chat-input")
    assert el is not None, "Expected #chat-input to exist on the page"
    candidate = await extract_element_props(el, pg)
    builder = SelectorBuilder()
    candidate.selector = await builder.build(el, pg)
    return candidate


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
    return SubmitFinder(SelectorBuilder())


class TestSubmitFinderBasic:
    """Test SubmitFinder.find() with various HTML fixtures."""

    async def test_send_button_found_with_high_score(self, page, finder):
        """A button with 'Send' text near the input should be found with a high score."""
        await page.set_content(SEND_BUTTON_HTML, wait_until="domcontentloaded")
        input_candidate = await _get_input_candidate(page)
        result = await finder.find(page, input_candidate)
        assert result is not None
        assert result.score > 0.3
        assert "send" in result.candidate.text_content.lower()

    async def test_svg_icon_button_found(self, page, finder):
        """A button with an SVG icon and aria-label near input should be found."""
        await page.set_content(SVG_ICON_BUTTON_HTML, wait_until="domcontentloaded")
        input_candidate = await _get_input_candidate(page)
        result = await finder.find(page, input_candidate)
        assert result is not None
        assert result.candidate.has_svg_child is True

    async def test_submit_type_button_found(self, page, finder):
        """An input[type=submit] near the input should be found."""
        await page.set_content(SUBMIT_TYPE_BUTTON_HTML, wait_until="domcontentloaded")
        input_candidate = await _get_input_candidate(page)
        result = await finder.find(page, input_candidate)
        assert result is not None
        assert result.score_breakdown["type"] > 0.0

    async def test_send_class_button_found(self, page, finder):
        """A button with class 'send-btn' should be found and score on class name."""
        await page.set_content(SEND_CLASS_BUTTON_HTML, wait_until="domcontentloaded")
        input_candidate = await _get_input_candidate(page)
        result = await finder.find(page, input_candidate)
        assert result is not None
        assert result.score_breakdown["class"] > 0.0

    async def test_far_button_scores_low_proximity(self, page, finder):
        """A button far from the input (>200px) should score 0 on proximity."""
        await page.set_content(FAR_BUTTON_HTML, wait_until="domcontentloaded")
        input_candidate = await _get_input_candidate(page)
        result = await finder.find(page, input_candidate)
        # The button is very far away; proximity should be 0
        if result is not None:
            assert result.score_breakdown["proximity"] == 0.0

    async def test_no_buttons_returns_none(self, page, finder):
        """Page with no buttons should return None."""
        await page.set_content(NO_BUTTONS_HTML, wait_until="domcontentloaded")
        input_candidate = await _get_input_candidate(page)
        result = await finder.find(page, input_candidate)
        assert result is None

    async def test_multiple_buttons_selects_send(self, page, finder):
        """With 'Login' far away and 'Send' near input, 'Send' should win."""
        await page.set_content(MULTIPLE_BUTTONS_HTML, wait_until="domcontentloaded")
        input_candidate = await _get_input_candidate(page)
        result = await finder.find(page, input_candidate)
        assert result is not None
        assert "send" in result.candidate.text_content.lower()


class TestSubmitFinderScoring:
    """Verify specific scoring factors of SubmitFinder."""

    async def test_proximity_score_decreases_with_distance(self, page, finder):
        """Nearby button should score higher on proximity than a far-away one."""
        # Near button
        await page.set_content(SEND_BUTTON_HTML, wait_until="domcontentloaded")
        input_candidate = await _get_input_candidate(page)
        near_result = await finder.find(page, input_candidate)

        # Far button (re-read input candidate for this page layout too)
        await page.set_content(FAR_BUTTON_HTML, wait_until="domcontentloaded")
        far_input_candidate = await _get_input_candidate(page)
        far_result = await finder.find(page, far_input_candidate)

        assert near_result is not None
        assert near_result.score_breakdown["proximity"] > 0.0

        if far_result is not None:
            assert near_result.score_breakdown["proximity"] > far_result.score_breakdown["proximity"]

    async def test_label_score_for_send_keyword(self, page, finder):
        """Button with 'Send' text should score high on the label factor."""
        await page.set_content(SEND_BUTTON_HTML, wait_until="domcontentloaded")
        input_candidate = await _get_input_candidate(page)
        result = await finder.find(page, input_candidate)
        assert result is not None
        assert result.score_breakdown["label"] > 0.0

    async def test_icon_score_for_svg_button(self, page, finder):
        """Button with an SVG child should score on the icon factor."""
        await page.set_content(SVG_ICON_BUTTON_HTML, wait_until="domcontentloaded")
        input_candidate = await _get_input_candidate(page)
        result = await finder.find(page, input_candidate)
        assert result is not None
        assert result.score_breakdown["icon"] > 0.0
