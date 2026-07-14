"""Regression tests for the bounded input-first discovery controller."""

import pytest

from webagentaudit.llm_channel.auto_config import AlgorithmicAutoConfigurator

pytestmark = pytest.mark.browser


async def test_existing_chat_input_wins_without_clicking_page_controls(page):
    await page.set_content(
        '<button id="unrelated" onclick="window.clicked = true">Support</button>'
        '<textarea id="prompt" placeholder="Ask the assistant"></textarea>'
    )

    result = await AlgorithmicAutoConfigurator().configure(
        page, skip_response=True
    )

    assert result.input_selector == "#prompt"
    assert result.setup_actions == []
    assert not await page.evaluate("window.clicked || false")


async def test_search_box_does_not_prevent_chat_launcher_attempt(page):
    await page.set_content(
        '<input id="search" type="text" placeholder="Search products">'
        '<button id="chat-launcher" aria-label="Open chat" '
        'onclick="chat.hidden = false">Chat</button>'
        '<section id="chat" hidden>'
        '<textarea id="message" placeholder="Type your message"></textarea>'
        '</section>'
    )

    result = await AlgorithmicAutoConfigurator().configure(
        page, skip_response=True
    )

    assert result.input_selector == "#message"
    assert [action.selector for action in result.setup_actions] == [
        "#chat-launcher"
    ]


async def test_modal_blocker_is_dismissed_before_input_search(page):
    await page.set_content(
        '<textarea id="prompt" placeholder="Ask a question"></textarea>'
        '<div id="consent-modal" role="dialog" style="position:fixed;inset:0;'
        'background:white;z-index:20">'
        '<button id="accept" onclick="this.parentElement.remove()">Accept</button>'
        '</div>'
    )

    result = await AlgorithmicAutoConfigurator().configure(
        page, skip_response=True
    )

    assert result.input_selector == "#prompt"
    assert len(result.setup_actions) == 1
    assert result.setup_actions[0].kind == "dismiss"
    assert result.setup_actions[0].selector == "#accept"


async def test_unknown_iframe_with_real_chat_input_is_discovered(page):
    await page.set_content(
        '<iframe name="vendor-widget" srcdoc="'
        '<textarea id=&quot;message&quot; placeholder=&quot;Message us&quot;>'
        '</textarea>"></iframe>'
    )

    result = await AlgorithmicAutoConfigurator().configure(
        page, skip_response=True
    )

    assert result.input_selector == "#message"
    assert result.input_frame_path == ['iframe[name="vendor-widget"]']
