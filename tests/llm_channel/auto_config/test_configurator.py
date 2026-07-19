"""Regression tests for the bounded input-first discovery controller."""

import asyncio
from pathlib import Path

import pytest

from webagentaudit.llm_channel.auto_config import AlgorithmicAutoConfigurator
from webagentaudit.llm_channel.auto_config import consts

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


async def test_delayed_chat_frame_is_polled_without_clicking_send_or_reloading(
    page, monkeypatch,
):
    html = (
        Path(__file__).parents[2] / "fixtures" / "insait_delayed_widget.html"
    ).read_text()
    await page.set_content(html)
    reloads = 0

    async def record_reload(*args, **kwargs):
        nonlocal reloads
        reloads += 1

    monkeypatch.setattr(page, "reload", record_reload)

    result = await AlgorithmicAutoConfigurator().configure(
        page, skip_response=True
    )
    frame = await page.locator("#insait-chat-frame").element_handle()
    content = await frame.content_frame()

    assert result.input_selector == "#composer"
    assert result.setup_actions == []
    assert reloads == 0
    assert await content.evaluate("window.sendClicks") == 0


async def test_flyweight_chat_frame_is_ranked_before_main_page(page, monkeypatch):
    await page.set_content("""
        <main>
          <button>Shop products</button>
          <button>View cart</button>
        </main>
        <iframe data-testid="chat-overlay" title="Chat" srcdoc="
          <button id='chat-button' aria-label='RXSG Assistant'
                  title='RXSG Assistant'
                  style='position:fixed;right:1rem;bottom:1rem'
                  onclick='message.hidden=false'>Hi!</button>
          <textarea id='message' placeholder='Type your message here...'
                    hidden></textarea>
          <button aria-label='Send' title='Send'>Send</button>
        "></iframe>
    """)
    configurator = AlgorithmicAutoConfigurator()
    original_rank = configurator._trigger_finder.ranked_candidates
    original_find_input = configurator._input_finder.find
    original_dismiss = configurator._preflight.dismiss_one
    ranked_main_page = False
    scanned_main_page_for_input = False
    scanned_main_page_for_blockers = False

    async def record_context(context):
        nonlocal ranked_main_page
        if context is page:
            ranked_main_page = True
        return await original_rank(context)

    async def record_input_context(context, *args, **kwargs):
        nonlocal scanned_main_page_for_input
        if context is page:
            scanned_main_page_for_input = True
        return await original_find_input(context, *args, **kwargs)

    async def record_blocker_context(context):
        nonlocal scanned_main_page_for_blockers
        if context is page:
            scanned_main_page_for_blockers = True
        return await original_dismiss(context)

    monkeypatch.setattr(
        configurator._trigger_finder, "ranked_candidates", record_context
    )
    monkeypatch.setattr(configurator._input_finder, "find", record_input_context)
    monkeypatch.setattr(
        configurator._preflight, "dismiss_one", record_blocker_context
    )

    result = await configurator.configure(page, skip_response=True)

    assert result.input_selector == "#message"
    assert result.input_frame_path == ['iframe[data-testid="chat-overlay"]']
    assert result.setup_actions[0].selector == "#chat-button"
    assert not scanned_main_page_for_input
    assert not scanned_main_page_for_blockers
    assert not ranked_main_page


async def test_timed_out_discovery_result_is_consumed(page, monkeypatch):
    events: list[tuple[str, str]] = []
    configurator = AlgorithmicAutoConfigurator(
        progress_callback=lambda phase, detail: events.append((phase, detail))
    )
    release = asyncio.Event()

    async def finish_after_timeout(*args, **kwargs):
        await release.wait()
        configurator._emit("DISCOVER", "late cleanup event")
        raise RuntimeError("page closed after discovery timeout")

    monkeypatch.setattr(configurator, "_configure_page", finish_after_timeout)
    monkeypatch.setattr(consts, "DISCOVERY_TIMEOUT_MS", 1)

    result = await configurator.configure(page, skip_response=True)
    assert result.input_selector is None
    assert len(configurator._background_tasks) == 1

    release.set()
    await asyncio.sleep(0)
    await asyncio.sleep(0)
    assert not configurator._background_tasks
    assert events == [("DISCOVER", "time budget exhausted")]


async def test_no_chat_page_does_not_reload_without_a_trigger(
    page, monkeypatch,
):
    html = (
        Path(__file__).parents[2] / "fixtures" / "no_chatbot_example.html"
    ).read_text()
    await page.set_content(html)
    events: list[tuple[str, str]] = []
    reloads = 0

    async def record_reload(*args, **kwargs):
        nonlocal reloads
        reloads += 1

    monkeypatch.setattr(page, "reload", record_reload)

    result = await AlgorithmicAutoConfigurator(
        progress_callback=lambda phase, detail: events.append((phase, detail))
    ).configure(page, skip_response=True)

    assert result.input_selector is None
    assert reloads == 0
    assert events == [
        ("DISCOVER", "scanning page and frames for an input"),
        ("DISCOVER", "no usable chat input found"),
    ]
