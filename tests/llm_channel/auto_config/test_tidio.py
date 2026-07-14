"""Tidio-specific discovery and replay regressions."""

import pytest
from playwright.async_api import Frame

from webagentaudit.core.exceptions import ChannelNotReadyError
from webagentaudit.llm_channel.auto_config import consts
from webagentaudit.llm_channel.auto_config.tidio import (
    TidioAutoConfigurator,
    open_tidio_widget,
)
from webagentaudit.llm_channel.strategies.custom import CustomStrategy

pytestmark = pytest.mark.browser


TIDIO_WIDGET_HTML = """<!doctype html><script>
window.tidioChatApi = {
  readyEventWasFired: false,
  on(event, callback) {
    if (event !== 'ready') return;
    if (this.readyEventWasFired) callback();
    else this.readyCallback = callback;
  },
  display(visible) {
    if (visible) setTimeout(() => {
      this.readyEventWasFired = true;
      this.readyCallback?.();
    }, 10);
  },
  show() {},
  open() {
    if (document.querySelector('#tidio-chat-iframe')) return;
    const frame = document.createElement('iframe');
    frame.id = 'tidio-chat-iframe';
    frame.title = 'Tidio Chat';
    frame.style = 'width: 360px; height: 500px';
    frame.srcdoc = `<div id="messages"><div class="message">Welcome</div></div>
      <textarea class="chat-input" placeholder="Type your message..."></textarea>
      <button aria-label="Send message" onclick="
        const input = document.querySelector('textarea');
        input.value = '';
        setTimeout(() => messages.insertAdjacentHTML(
          'beforeend', '<div class=message>No</div>'
        ), 10);
      ">Send</button>`;
    document.body.append(frame);
  },
};
</script>"""


async def test_tidio_configurator_discovers_replays_and_reads_response(page):
    await page.set_content(TIDIO_WIDGET_HTML)

    result = await TidioAutoConfigurator().configure(page, skip_response=True)

    assert result.input_selector == "textarea.chat-input"
    assert result.submit_selector == 'button[aria-label="Send message"]'
    assert result.input_frame_path == ['iframe[id="tidio-chat-iframe"]']
    assert [action.kind for action in result.setup_actions] == ["tidio_open"]

    await page.set_content(TIDIO_WIDGET_HTML)
    strategy = CustomStrategy(plan=result.to_interaction_plan())
    target = await strategy.prepare_page(page)
    assert isinstance(target, Frame)

    await strategy.prepare_response(target)
    await strategy.send_message(target, "image capability prompt")
    assert await strategy.wait_for_response(target, timeout_ms=5_000) == "No"


async def test_tidio_api_unavailable_is_explicit(page):
    await page.set_content("<div>page with a delayed or broken Tidio embed</div>")

    with pytest.raises(ChannelNotReadyError, match="API did not become available"):
        await open_tidio_widget(page, timeout_ms=50)


async def test_tidio_api_never_ready_is_explicit(page):
    await page.set_content("""<script>
      window.tidioChatApi = {
        display() {},
        on(event, callback) {},
      };
    </script>""")

    with pytest.raises(ChannelNotReadyError, match="never became ready"):
        await open_tidio_widget(page, timeout_ms=500)


async def test_tidio_pre_chat_email_form_is_not_fabricated(page, monkeypatch):
    monkeypatch.setattr(consts, "TIDIO_WAIT_MS", 100)
    await page.set_content("""<script>
      window.tidioChatApi = {
        readyEventWasFired: true,
        on(event, callback) { if (event === 'ready') callback(); },
        display() {}, show() {},
        open() {
          const frame = document.createElement('iframe');
          frame.id = 'tidio-chat-iframe';
          frame.title = 'Tidio Chat';
          frame.style = 'width: 360px; height: 500px';
          frame.srcdoc = '<input type="email" placeholder="Email">';
          document.body.append(frame);
        },
      };
    </script>""")

    with pytest.raises(ChannelNotReadyError, match="pre-chat email form"):
        await TidioAutoConfigurator().configure(page, skip_response=True)
