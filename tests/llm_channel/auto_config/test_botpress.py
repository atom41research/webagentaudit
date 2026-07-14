"""Botpress-specific discovery, replay, and response regressions."""

import pytest
from playwright.async_api import Frame, Page

from webagentaudit.core.exceptions import ChannelNotReadyError
from webagentaudit.llm_channel.auto_config.botpress import (
    BotpressAutoConfigurator,
    open_botpress_widget,
)
from webagentaudit.llm_channel.strategies.custom import CustomStrategy

pytestmark = pytest.mark.browser


def _widget_html(*, embedded: bool) -> str:
    widget = """<div id="messages">
      <div class="bpReset bpMessageContainer">Today</div>
    </div>
    <textarea class="bpComposerInput" aria-label="Message Input"
      onkeydown="if (event.key === 'Enter') {
        this.value = '';
        setTimeout(() => document.getElementById('messages').insertAdjacentHTML(
          'beforeend',
          '&lt;div class=&quot;bpReset bpMessageContainer&quot;&gt;No&lt;/div&gt;'
        ), 10);
      }"></textarea>"""
    render = (
        f"document.body.insertAdjacentHTML('beforeend', {widget!r});"
        if embedded
        else f"""const frame = document.createElement('iframe');
          frame.name = 'webchat';
          frame.title = 'Botpress';
          frame.srcdoc = {widget!r};
          document.body.append(frame);"""
    )
    return f"""<!doctype html><script>
      window.botpress = {{
        state: 'initial',
        open() {{
          this.state = 'opened';
          if (document.querySelector('.bpComposerInput, iframe[name="webchat"]')) return;
          {render}
        }},
      }};
    </script>"""


async def test_botpress_iframe_configurator_replays_and_reads_response(page):
    fixture = _widget_html(embedded=False)
    await page.set_content(fixture)

    result = await BotpressAutoConfigurator().configure(page, skip_response=True)

    assert result.input_selector == "textarea.bpComposerInput"
    assert result.submit_selector is None
    assert result.input_frame_path == ['iframe[name="webchat"]']
    assert [action.kind for action in result.setup_actions] == ["botpress_open"]

    await page.set_content(fixture)
    strategy = CustomStrategy(plan=result.to_interaction_plan())
    target = await strategy.prepare_page(page)
    assert isinstance(target, Frame)

    await strategy.prepare_response(target)
    await strategy.send_message(target, "image capability prompt")
    assert await strategy.wait_for_response(target, timeout_ms=5_000) == "No"


async def test_botpress_embedded_configurator_uses_host_document(page):
    await page.set_content(_widget_html(embedded=True))

    result = await BotpressAutoConfigurator().configure(page, skip_response=True)

    assert result.input_frame_path == []
    assert isinstance(await CustomStrategy(
        plan=result.to_interaction_plan()
    ).prepare_page(page), Page)


async def test_botpress_api_unavailable_is_explicit(page):
    await page.set_content("<div>page with a broken Botpress embed</div>")

    with pytest.raises(ChannelNotReadyError, match="API did not become available"):
        await open_botpress_widget(page, timeout_ms=50)
