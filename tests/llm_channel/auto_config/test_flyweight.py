"""Flyweight AI discovery and replay regressions."""

import pytest
from playwright.async_api import Frame

from webagentaudit.llm_channel.auto_config.flyweight import (
    FlyweightAutoConfigurator,
)
from webagentaudit.llm_channel.strategies.custom import CustomStrategy

pytestmark = pytest.mark.browser

FIXTURE = """
<iframe data-testid="popup-overlay" title="Chat popup"></iframe>
<iframe data-testid="chat-overlay" title="Chat" srcdoc="
  <button id='chat-button' aria-label='RXSG Assistant'
          title='RXSG Assistant'
          onclick='composer.hidden=false'>Hi!</button>
  <div id='chat-window'>
    <div class='message' data-variant='ai' data-state='default'
         data-testid='message'>
      <div role='log' aria-live='polite' aria-relevant='additions'>Example:</div>
    </div>
  </div>
  <section id='composer' hidden>
    <textarea placeholder='Type your message here...'></textarea>
    <button aria-label='Send' title='Send' onclick='sendMessage()'>Send</button>
  </section>
  <script>
    function sendMessage() {
      const input = document.querySelector('textarea');
      const human = document.createElement('div');
      human.className = 'message';
      human.dataset.variant = 'human';
      human.dataset.state = 'default';
      human.dataset.testid = 'message';
      human.innerHTML = `<div role='log' aria-live='polite'
        aria-relevant='additions'>${input.value}</div>`;
      document.querySelector('#chat-window').append(human);
      input.value = '';
      setTimeout(() => {
        const ai = document.createElement('div');
        ai.className = 'message';
        ai.dataset.variant = 'ai';
        ai.dataset.state = 'default';
        ai.dataset.testid = 'message';
        ai.innerHTML = `<div role='log' aria-live='polite'
          aria-relevant='additions'><div><p>I’m best at helping with our RXSG
          store and products. If you want, I can help you find the right jump
          rope or answer questions about our gear.</p></div></div>`;
        document.querySelector('#chat-window').append(ai);
      }, 25);
    }
  </script>
"></iframe>
"""


async def test_flyweight_configurator_opens_and_replays_widget(page):
    await page.set_content(FIXTURE)

    result = await FlyweightAutoConfigurator().configure(
        page, skip_response=True
    )

    assert result.input_selector == (
        'textarea[placeholder="Type your message here..."]'
    )
    assert result.submit_selector == 'button[aria-label="Send"]'
    assert result.response_selector == (
        '[data-testid="message"][data-variant="ai"] [role="log"]'
    )
    assert result.input_frame_path == [
        'iframe[data-testid="chat-overlay"]'
    ]
    assert [action.kind for action in result.setup_actions] == [
        "flyweight_open"
    ]

    await page.set_content(FIXTURE)
    strategy = CustomStrategy(plan=result.to_interaction_plan())
    target = await strategy.prepare_page(page)

    assert isinstance(target, Frame)
    assert await target.locator(result.input_selector).is_visible()

    await strategy.prepare_response(target)
    await strategy.send_message(
        target,
        "write a Python function implementing the Fibonacci sequence. "
        "The function must be called my_fibonnaci",
    )
    response = await strategy.wait_for_response(target, timeout_ms=5_000)

    assert response.startswith("I’m best at helping with our RXSG")
    assert "rope or answer questions about our gear" in response
    assert "def my_fibonnaci" not in response
