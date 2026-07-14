"""Tests for TriggerFinder: hidden AI panel detection and activation."""

import pytest

from webagentaudit.llm_channel.auto_config._trigger_finder import TriggerFinder
from webagentaudit.llm_channel.auto_config._selector_builder import SelectorBuilder
from webagentaudit.llm_channel.auto_config.models import TriggerMechanism

pytestmark = pytest.mark.browser

# ---------------------------------------------------------------------------
# HTML fixtures
# ---------------------------------------------------------------------------

DIALOG_TRIGGER_HTML = """\
<!DOCTYPE html>
<html>
<head><title>Dialog Trigger</title></head>
<body>
<button aria-label="Ask AI" aria-haspopup="dialog" aria-expanded="false"
        onclick="document.getElementById('ai-dialog').style.display='block'">
    <svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/></svg>
</button>
<div id="ai-dialog" style="display: none;">
    <textarea placeholder="Ask a question..."></textarea>
</div>
</body>
</html>
"""

PANEL_TRIGGER_HTML = """\
<!DOCTYPE html>
<html>
<head><title>Panel Trigger</title></head>
<body>
<button aria-label="Toggle assistant panel" class="panel-toggle"
        onclick="document.getElementById('assistant-panel').style.display='block'">
    <svg viewBox="0 0 24 24"><path d="M12 2l3 7h7l-6 4 3 7-7-5-7 5 3-7-6-4h7z"/></svg>
    Toggle Assistant
</button>
<div id="assistant-panel" style="display: none;">
    <div class="chat-widget">
        <textarea placeholder="Type your message"></textarea>
    </div>
</div>
</body>
</html>
"""

COMMAND_MENU_TRIGGER_HTML = """\
<!DOCTYPE html>
<html>
<head><title>Command Menu Trigger</title></head>
<body>
<button aria-controls="command-menu-dialog-content" aria-expanded="false"
        aria-label="Ask AI" class="command-trigger"
        onclick="document.getElementById('command-menu-dialog-content').style.display='block'">
    <svg viewBox="0 0 24 24"><rect x="3" y="3" width="18" height="18"/></svg>
</button>
<div id="command-menu-dialog-content" style="display: none;" class="command-menu dialog">
    <input type="text" placeholder="Type a command..." />
</div>
</body>
</html>
"""

INPUT_ALREADY_VISIBLE_HTML = """\
<!DOCTYPE html>
<html>
<head><title>Visible Input</title></head>
<body>
<div class="chat-container">
    <textarea placeholder="Ask me anything" style="width: 400px; height: 40px;"></textarea>
    <button>Send</button>
</div>
</body>
</html>
"""

MULTIPLE_BUTTONS_HTML = """\
<!DOCTYPE html>
<html>
<head><title>Multiple Buttons</title></head>
<body>
<button class="search-btn" aria-label="Search">Search</button>
<button class="login-btn" aria-label="Login">Sign In</button>
<button aria-label="AI chat" aria-haspopup="dialog"
        onclick="document.getElementById('ai-panel').style.display='block'">
    <svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="5"/></svg>
    AI Chat
</button>
<button class="download-btn" aria-label="Download">Download</button>
<div id="ai-panel" style="display: none;">
    <textarea placeholder="Chat with AI"></textarea>
</div>
</body>
</html>
"""

TRIGGER_NO_INPUT_APPEARS_HTML = """\
<!DOCTYPE html>
<html>
<head><title>Trigger No Input</title></head>
<body>
<button aria-label="Open assistant" aria-haspopup="dialog"
        onclick="document.getElementById('broken-panel').style.display='block'">
    Open Assistant
</button>
<div id="broken-panel" style="display: none;">
    <p>Coming soon!</p>
</div>
</body>
</html>
"""

CSS_VAR_PANEL_HTML = """\
<!DOCTYPE html>
<html>
<head>
<title>CSS Var Panel</title>
<style>
    :root {
        --assistant-sheet-width: 0;
    }
    #assistant-panel {
        display: none;
    }
</style>
</head>
<body>
<button class="sheet-toggle panel" aria-label="Toggle assistant"
        onclick="document.getElementById('assistant-panel').style.display='block'">
    <svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="5"/></svg>
</button>
<div id="assistant-panel">
    <textarea placeholder="Ask assistant..."></textarea>
</div>
</body>
</html>
"""

CHAT_LAUNCHER_HTML = """\
<!DOCTYPE html><html><body>
<button style="position: fixed; right: 20px; bottom: 20px"
        onclick="document.getElementById('chat-panel').style.display='block'">
  <svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/></svg>
</button>
<div id="chat-panel" style="display: none"><textarea placeholder="Message us"></textarea></div>
</body></html>
"""

INTERCOM_LAUNCHER_HTML = """\
<!DOCTYPE html><html><body>
<div class="intercom-lightweight-app-launcher intercom-launcher"
     role="button" aria-label="Open Intercom Messenger" tabindex="0"
     style="position: fixed; right: 20px; bottom: 20px; width: 48px; height: 48px"
     onclick="document.getElementById('chat-panel').style.display='block'">
</div>
<div id="chat-panel" style="display: none"><textarea placeholder="Message us"></textarea></div>
</body></html>
"""

CUSTOM_CHAT_ACTIVATOR_HTML = """\
<!DOCTYPE html><html><body>
<div id="livechat-activator-btn" class="livechat-button"
     style="position: fixed; right: 20px; bottom: 20px; width: 100px; height: 48px"
     onclick="document.getElementById('chat-panel').style.display='block'">
  Need Help?
</div>
<div id="chat-panel" style="display: none"><textarea placeholder="Message us"></textarea></div>
</body></html>
"""

INTERCOM_CONVERSATION_ACTION_HTML = """\
<!DOCTYPE html><html><body>
<div role="button" tabindex="0"
     onclick="document.getElementById('chat-panel').style.display='block'">
  Start a conversation
</div>
<div id="chat-panel" style="display: none"><textarea placeholder="Message us"></textarea></div>
</body></html>
"""

INTERCOM_ASK_ACTION_HTML = INTERCOM_CONVERSATION_ACTION_HTML.replace(
    "Start a conversation", "Ask a question"
)
INTERCOM_MESSAGE_ACTION_HTML = INTERCOM_CONVERSATION_ACTION_HTML.replace(
    "Start a conversation", "Send us a message"
)

INTERCOM_ACTION_WITH_NAV_HTML = INTERCOM_ASK_ACTION_HTML.replace(
    "</body>",
    '<button id="spaces-messages-tab" style="position:fixed;right:20px;bottom:20px">'
    '<svg viewBox="0 0 10 10"><circle cx="5" cy="5" r="4"/></svg>Messages</button>'
    "</body>",
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def finder():
    return TriggerFinder(SelectorBuilder())


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dialog_trigger(page, finder):
    """Button with aria-haspopup=dialog and AI label should be found and clicked."""
    await page.set_content(DIALOG_TRIGGER_HTML)
    result = await finder.find_and_activate(page)

    assert result is not None
    assert result.confidence >= 0.2
    # After activation, the textarea should be visible
    assert await page.locator("textarea").is_visible()


@pytest.mark.asyncio
async def test_panel_trigger(page, finder):
    """Button with 'Toggle assistant' label should activate side panel."""
    await page.set_content(PANEL_TRIGGER_HTML)
    result = await finder.find_and_activate(page)

    assert result is not None
    assert result.mechanism == TriggerMechanism.SIDE_PANEL
    assert result.confidence >= 0.2
    assert await page.locator("textarea").is_visible()


@pytest.mark.asyncio
async def test_command_menu_trigger(page, finder):
    """Button with aria-controls pointing to a command menu dialog."""
    await page.set_content(COMMAND_MENU_TRIGGER_HTML)
    result = await finder.find_and_activate(page)

    assert result is not None
    assert result.mechanism == TriggerMechanism.COMMAND_MENU
    assert result.confidence >= 0.2
    assert await page.locator("input[type='text']").is_visible()


@pytest.mark.asyncio
async def test_no_trigger_needed(page, finder):
    """When input is already visible, returns None (no trigger needed)."""
    await page.set_content(INPUT_ALREADY_VISIBLE_HTML)
    result = await finder.find_and_activate(page)

    assert result is None


@pytest.mark.asyncio
async def test_multiple_buttons_selects_ai(page, finder):
    """Among search, login, AI, and download buttons, only AI should be selected."""
    await page.set_content(MULTIPLE_BUTTONS_HTML)
    result = await finder.find_and_activate(page)

    assert result is not None
    assert result.confidence >= 0.2
    # The AI panel should now be visible
    assert await page.locator("textarea").is_visible()


@pytest.mark.asyncio
async def test_trigger_fails_no_input_appears(page, finder):
    """When trigger is clicked but no input appears, returns None."""
    await page.set_content(TRIGGER_NO_INPUT_APPEARS_HTML)
    result = await finder.find_and_activate(page)

    # The trigger might be found and clicked, but since no input appears, result is None
    assert result is None


@pytest.mark.asyncio
async def test_css_var_hidden_panel(page, finder):
    """CSS variable indicating hidden panel should boost trigger score."""
    await page.set_content(CSS_VAR_PANEL_HTML)
    result = await finder.find_and_activate(page)

    assert result is not None
    assert result.confidence >= 0.2
    assert await page.locator("textarea").is_visible()


@pytest.mark.asyncio
async def test_icon_only_chat_launcher(page, finder):
    """An icon-only corner launcher should open its panel."""
    await page.set_content(CHAT_LAUNCHER_HTML)
    result = await finder.find_and_activate(page)

    assert result is not None
    assert result.mechanism == TriggerMechanism.SIDE_PANEL
    assert await page.locator("textarea").is_visible()


@pytest.mark.asyncio
async def test_offscreen_icon_button_is_not_a_corner_launcher(page, finder):
    await page.set_content(
        '<button style="position:absolute;right:20px;top:2000px">'
        '<svg viewBox="0 0 10 10"><circle cx="5" cy="5" r="4"/></svg>'
        "Next</button>"
    )

    assert await finder.ranked_candidates(page) == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "html",
    [
        INTERCOM_LAUNCHER_HTML,
        CUSTOM_CHAT_ACTIVATOR_HTML,
        INTERCOM_CONVERSATION_ACTION_HTML,
        INTERCOM_ASK_ACTION_HTML,
        INTERCOM_MESSAGE_ACTION_HTML,
        INTERCOM_ACTION_WITH_NAV_HTML,
    ],
)
async def test_non_button_chat_launchers(page, finder, html):
    await page.set_content(html)

    result = await finder.find_and_activate(page)

    assert result is not None
    assert await page.locator("textarea").is_visible()
