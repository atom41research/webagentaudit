"""Intercom-specific discovery regressions."""

import pytest

from webagentaudit.llm_channel.auto_config.intercom import IntercomAutoConfigurator

pytestmark = pytest.mark.browser


async def test_intercom_configurator_opens_conversation_and_finds_composer(page):
    await page.set_content(
        """<!doctype html><script>
        window.Intercom = command => {
          if (command !== 'show' || document.querySelector('iframe')) return;
          const frame = document.createElement('iframe');
          frame.name = 'intercom-messenger-frame';
          frame.srcdoc = `<div role="button" id="start"
              onclick="this.hidden=true;composer.hidden=false">Ask a question</div>
            <div id="composer" hidden>
              <textarea placeholder="Message…"></textarea>
              <button aria-label="Send a message…">Send</button>
            </div>`;
          document.body.append(frame);
        };
        </script>"""
    )

    result = await IntercomAutoConfigurator().configure(
        page, skip_response=True
    )

    assert result.input_selector == 'textarea[placeholder="Message…"]'
    assert result.submit_selector == 'button[aria-label="Send a message…"]'
    assert result.input_frame_path == [
        'iframe[name="intercom-messenger-frame"]'
    ]
    assert [action.kind for action in result.setup_actions] == [
        "intercom_show",
        "trigger",
    ]
