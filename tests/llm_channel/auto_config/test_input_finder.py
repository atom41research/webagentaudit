"""Tests for InputFinder: algorithmic input element discovery and scoring."""

import pytest

from webagentaudit.llm_channel.auto_config._input_finder import InputFinder
from webagentaudit.llm_channel.auto_config._selector_builder import SelectorBuilder

pytestmark = pytest.mark.browser

# ---------------------------------------------------------------------------
# HTML fixtures
# ---------------------------------------------------------------------------

CHAT_TEXTAREA_HTML = """\
<!DOCTYPE html>
<html>
<head><title>Chat</title></head>
<body>
<div class="chat-container" style="margin-top: 600px;">
    <textarea placeholder="Ask me anything" style="width: 400px; height: 40px;"></textarea>
</div>
</body>
</html>
"""

CONTENTEDITABLE_DIV_HTML = """\
<!DOCTYPE html>
<html>
<head><title>Chat</title></head>
<body>
<div class="chat-container" style="margin-top: 600px;">
    <div contenteditable="true" role="textbox"
         style="width: 400px; height: 40px; border: 1px solid #ccc;"
         class="message-input">Type here</div>
</div>
</body>
</html>
"""

TEXT_INPUT_HTML = """\
<!DOCTYPE html>
<html>
<head><title>Chat</title></head>
<body>
<div class="chat-widget" style="margin-top: 600px;">
    <input type="text" placeholder="Type a message" style="width: 400px; height: 30px;">
    <button>Send</button>
</div>
</body>
</html>
"""

SEARCH_INPUT_HTML = """\
<!DOCTYPE html>
<html>
<head><title>Search</title></head>
<body>
<div class="search-bar">
    <input type="search" placeholder="Search products..." style="width: 300px; height: 30px;">
</div>
</body>
</html>
"""

PASSWORD_INPUT_HTML = """\
<!DOCTYPE html>
<html>
<head><title>Login</title></head>
<body>
<div class="login-form">
    <input type="text" placeholder="Username" style="width: 300px; height: 30px;">
    <input type="password" placeholder="Password" style="width: 300px; height: 30px;">
    <button>Login</button>
</div>
</body>
</html>
"""

NO_INPUTS_HTML = """\
<!DOCTYPE html>
<html>
<head><title>Static Page</title></head>
<body>
<h1>Hello World</h1>
<p>No inputs here.</p>
</body>
</html>
"""

MULTIPLE_INPUTS_HTML = """\
<!DOCTYPE html>
<html>
<head><title>Page with Multiple Inputs</title></head>
<body>
<header>
    <div class="search-bar">
        <input type="search" placeholder="Search the site..."
               style="width: 300px; height: 30px;">
    </div>
</header>
<main style="margin-top: 600px;">
    <div class="chat-container">
        <textarea placeholder="Ask me anything about our products..."
                  style="width: 400px; height: 40px;"></textarea>
        <button>Send</button>
    </div>
</main>
</body>
</html>
"""

PARENT_CONTEXT_BOOST_HTML = """\
<!DOCTYPE html>
<html>
<head><title>Chat</title></head>
<body>
<div class="ai-assistant-panel" style="margin-top: 600px;">
    <textarea style="width: 400px; height: 40px;"></textarea>
</div>
</body>
</html>
"""

SYMPHONY_GRAVITY_FORM_HTML = """\
<!DOCTYPE html>
<html>
<body>
<form id="gform_4" class="gform_wrapper" method="post">
    <input type="text" name="input_1.3" id="input_4_1_3"
           autocomplete="given-name">
    <input type="email" name="input_4" id="input_4_4">
    <label for="input_4_9">Message</label>
    <textarea name="input_9" id="input_4_9" class="textarea large"
              rows="10" cols="50" style="width:800px;height:288px"></textarea>
    <input type="submit" id="gform_submit_button_4"
           class="gform_button button" value="SEND A MESSAGE">
</form>
</body>
</html>
"""

CHAT_FORM_HTML = """\
<!DOCTYPE html>
<html>
<body>
<form class="chat-composer">
    <textarea id="chat-input" placeholder="Type a message"
              style="width:400px;height:40px"></textarea>
    <button aria-label="Send message">Send</button>
</form>
</body>
</html>
"""


@pytest.fixture
def finder():
    return InputFinder(SelectorBuilder())


class TestInputFinderBasic:
    """Test InputFinder.find() with various HTML fixtures."""

    async def test_chat_textarea_found_with_high_score(self, page, finder):
        """A textarea with 'Ask me anything' placeholder should be found with a high score."""
        await page.set_content(CHAT_TEXTAREA_HTML, wait_until="domcontentloaded")
        result = await finder.find(page)
        assert result is not None
        assert result.score > 0.3
        assert result.candidate.tag_name == "textarea"
        assert result.candidate.placeholder == "Ask me anything"

    async def test_contenteditable_div_found(self, page, finder):
        """A contenteditable div with role=textbox should be discovered."""
        await page.set_content(CONTENTEDITABLE_DIV_HTML, wait_until="domcontentloaded")
        result = await finder.find(page)
        assert result is not None
        assert result.candidate.is_contenteditable is True
        assert result.candidate.role == "textbox"

    async def test_text_input_with_message_placeholder(self, page, finder):
        """An input[type=text] with 'Type a message' placeholder should be found."""
        await page.set_content(TEXT_INPUT_HTML, wait_until="domcontentloaded")
        result = await finder.find(page)
        assert result is not None
        assert result.candidate.tag_name == "input"

    async def test_search_input_not_best(self, page, finder):
        """A search input should not be selected as the best candidate."""
        await page.set_content(SEARCH_INPUT_HTML, wait_until="domcontentloaded")
        result = await finder.find(page)
        # Either not found or score is very low due to negative keywords and type
        if result is not None:
            assert result.score_breakdown.get("no_negative", 1.0) == 0.0

    async def test_password_input_not_selected(self, page, finder):
        """Password inputs should not be the best candidate (or found at all)."""
        await page.set_content(PASSWORD_INPUT_HTML, wait_until="domcontentloaded")
        result = await finder.find(page)
        # If something is found, it should NOT be the password field
        if result is not None:
            assert result.candidate.element_type != "password"

    async def test_no_inputs_returns_none(self, page, finder):
        """Page with no input elements should return None."""
        await page.set_content(NO_INPUTS_HTML, wait_until="domcontentloaded")
        result = await finder.find(page)
        assert result is None

    async def test_multiple_inputs_selects_chat(self, page, finder):
        """With both a search input and a chat textarea, the chat textarea wins."""
        await page.set_content(MULTIPLE_INPUTS_HTML, wait_until="domcontentloaded")
        result = await finder.find(page)
        assert result is not None
        assert result.candidate.tag_name == "textarea"
        assert "ask" in result.candidate.placeholder.lower()

    async def test_gravity_contact_message_is_not_a_chat_input(self, page, finder):
        """The reproduced Symphony Gravity Forms textarea must be rejected."""
        await page.set_content(
            SYMPHONY_GRAVITY_FORM_HTML, wait_until="domcontentloaded"
        )

        assert await finder.find(page) is None

    async def test_real_chat_composer_inside_form_remains_valid(self, page, finder):
        """Form elements are valid when their context is actually chat."""
        await page.set_content(CHAT_FORM_HTML, wait_until="domcontentloaded")

        result = await finder.find(page)

        assert result is not None
        assert result.candidate.selector == "#chat-input"


class TestInputFinderScoring:
    """Verify specific scoring factors of InputFinder."""

    async def test_textarea_scores_higher_than_input(self, page, finder):
        """A textarea should get a higher element_type score than input[type=text]."""
        await page.set_content(CHAT_TEXTAREA_HTML, wait_until="domcontentloaded")
        textarea_result = await finder.find(page)

        await page.set_content(TEXT_INPUT_HTML, wait_until="domcontentloaded")
        input_result = await finder.find(page)

        assert textarea_result is not None
        assert input_result is not None
        assert textarea_result.score_breakdown["element_type"] >= input_result.score_breakdown["element_type"]

    async def test_parent_context_boost(self, page, finder):
        """Elements inside a parent with 'ai-assistant' class should get a context boost."""
        await page.set_content(PARENT_CONTEXT_BOOST_HTML, wait_until="domcontentloaded")
        result = await finder.find(page)
        assert result is not None
        # parent_context should be > 0 because 'ai' is in INPUT_PARENT_KEYWORDS
        assert result.score_breakdown["parent_context"] > 0.0

    async def test_chat_container_parent_boost(self, page, finder):
        """Elements inside a 'chat-container' parent should get a context boost."""
        await page.set_content(CHAT_TEXTAREA_HTML, wait_until="domcontentloaded")
        result = await finder.find(page)
        assert result is not None
        # 'chat' is in INPUT_PARENT_KEYWORDS
        assert result.score_breakdown["parent_context"] > 0.0

    async def test_positive_placeholder_scores_high(self, page, finder):
        """Placeholder with 'ask' keyword should produce a high placeholder score."""
        await page.set_content(CHAT_TEXTAREA_HTML, wait_until="domcontentloaded")
        result = await finder.find(page)
        assert result is not None
        assert result.score_breakdown["placeholder"] > 0.0
