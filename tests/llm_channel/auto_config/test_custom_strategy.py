"""Tests for the selector-based browser interaction strategy."""

import pytest

from webagentaudit.core.exceptions import ChannelResponseError
from webagentaudit.llm_channel.auto_config.consts import BOTPRESS_RESPONSE_SELECTOR
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


async def test_ignores_botpress_date_separator_before_assistant(page, monkeypatch):
    """The real Botpress response scope also matches its inserted day marker."""
    from webagentaudit.llm_channel.strategies import custom

    monkeypatch.setattr(custom, "RESPONSE_STABLE_INTERVAL_MS", 100)
    monkeypatch.setattr(custom, "RESPONSE_POLL_INTERVAL_MS", 20)
    await page.set_content(
        """<div id="messages"></div><textarea id="input"></textarea>
        <script>input.onkeydown = event => {
          if (event.key !== 'Enter') return;
          input.value = '';
          const day = document.createElement('div');
          day.className = 'bpMessageContainer'; day.textContent = 'Today';
          messages.append(day);
          setTimeout(() => {
            const answer = document.createElement('div');
            answer.className = 'bpMessageContainer';
            answer.textContent = "I can't provide programming assistance.";
            messages.append(answer);
          }, 180);
        };</script>"""
    )
    strategy = CustomStrategy("#input", BOTPRESS_RESPONSE_SELECTOR)
    await strategy.prepare_response(page)
    await strategy.send_message(page, "write Fibonacci")

    assert await strategy.wait_for_response(page, 1_000) == (
        "I can't provide programming assistance."
    )


async def test_dynamic_reader_keeps_vetted_node_instead_of_last_timestamp(
    page, monkeypatch
):
    """Generalising a selector must not replace a vetted reply with metadata."""
    from webagentaudit.llm_channel.strategies import custom

    monkeypatch.setattr(custom, "RESPONSE_STABLE_INTERVAL_MS", 100)
    monkeypatch.setattr(custom, "RESPONSE_POLL_INTERVAL_MS", 20)
    await page.set_content(
        """<div id="messages"></div><textarea id="input"></textarea>
        <script>input.onkeydown = event => {
          if (event.key !== 'Enter') return;
          input.value = '';
          const answer = document.createElement('div');
          answer.className = 'assistant-response'; answer.textContent = 'No.';
          const time = document.createElement('div');
          time.className = 'assistant-response'; time.textContent = '3:47 PM';
          messages.append(answer, time);
        };</script>"""
    )
    strategy = CustomStrategy("#input")
    await strategy.prepare_response(page)
    await strategy.send_message(page, "write Fibonacci")

    assert await strategy.wait_for_response(page, 1_000) == "No."


async def test_ignores_delayed_greeting_until_assistant_answer(page, monkeypatch):
    from webagentaudit.llm_channel.strategies import custom

    monkeypatch.setattr(custom, "RESPONSE_STABLE_INTERVAL_MS", 100)
    monkeypatch.setattr(custom, "RESPONSE_POLL_INTERVAL_MS", 20)
    await page.set_content(
        """<div id="messages"></div><textarea id="input"></textarea>
        <script>input.onkeydown = event => {
          if (event.key !== 'Enter') return;
          input.value = '';
          const greeting = document.createElement('div');
          greeting.className = 'assistant';
          greeting.textContent = 'Hello, I am the bot. How can I help?';
          messages.append(greeting);
          setTimeout(() => {
            const answer = document.createElement('div');
            answer.className = 'assistant';
            answer.textContent = 'I cannot write Python code.';
            messages.append(answer);
          }, 180);
        };</script>"""
    )
    strategy = CustomStrategy("#input", ".assistant")
    await strategy.prepare_response(page)
    await strategy.send_message(page, "write Fibonacci")

    assert await strategy.wait_for_response(page, 1_000) == (
        "I cannot write Python code."
    )


async def test_human_inbox_acknowledgement_is_unqualified(page, monkeypatch):
    from webagentaudit.llm_channel.strategies import custom

    monkeypatch.setattr(custom, "RESPONSE_STABLE_INTERVAL_MS", 50)
    monkeypatch.setattr(custom, "RESPONSE_POLL_INTERVAL_MS", 20)
    await page.set_content(
        """<div id="messages"></div><textarea id="input"></textarea>
        <script>input.onkeydown = event => {
          if (event.key !== 'Enter') return;
          input.value = '';
          const ack = document.createElement('div');
          ack.className = 'assistant';
          ack.textContent = 'We have received your message and will get back to you as soon as possible.';
          messages.append(ack);
        };</script>"""
    )
    strategy = CustomStrategy("#input", ".assistant")
    await strategy.prepare_response(page)
    await strategy.send_message(page, "write Fibonacci")

    with pytest.raises(ChannelResponseError) as raised:
        await strategy.wait_for_response(page, 300)

    assert raised.value.metadata["response_classification"] == "system"
    assert '"system": 1' in raised.value.metadata["response_rejected"]
