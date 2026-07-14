"""Featurebase-specific discovery, replay, and response regressions."""

import pytest
from playwright.async_api import Frame

from webagentaudit.core.exceptions import ChannelNotReadyError
from webagentaudit.llm_channel.auto_config import consts
from webagentaudit.llm_channel.auto_config.featurebase import (
    FeaturebaseAutoConfigurator,
    open_featurebase_composer,
)
from webagentaudit.llm_channel.strategies.custom import CustomStrategy

pytestmark = pytest.mark.browser


WIDGET = """<!doctype html><script>
window.Featurebase = (action, draft) => {
  if (action !== 'showNewMessage' || !draft || document.querySelector('iframe')) {
    return;
  }
  const frame = document.createElement('iframe');
  frame.name = 'fb-messenger-frame';
  frame.srcdoc = `<div data-fb-conversation-parts-wrapper></div>
    <div contenteditable="true" role="textbox"
      aria-label="Send us a message...">${draft}</div>
    <button aria-label="Submit message" onclick="
      const input = document.querySelector('[contenteditable]');
      input.innerHTML = '<p><br></p>';
      document.querySelector('[data-fb-conversation-parts-wrapper]')
        .insertAdjacentHTML('beforeend',
          '<div data-conversation-part-id=customer><div class=float-right>' +
          '<div class=installation-content>image capability prompt</div>' +
          '</div></div>' +
          '<div data-conversation-part-id=answer><div class=float-left>' +
          '<div class=installation-content><p>No</p></div></div></div>' +
          '<div data-conversation-part-id=followup><div class=float-left>' +
          '<div class=installation-content><p>Anything else?</p></div>' +
          '</div></div>');
    ">Send</button>`;
  document.body.append(frame);
};
</script>"""


async def test_featurebase_configurator_replays_and_reads_first_answer(page):
    await page.set_content(WIDGET)
    progress = []

    result = await FeaturebaseAutoConfigurator(
        lambda phase, detail: progress.append((phase, detail))
    ).configure(
        page, skip_response=True
    )

    assert result.input_selector == consts.FEATUREBASE_INPUT_SELECTOR
    assert result.submit_selector == consts.FEATUREBASE_SUBMIT_SELECTOR
    assert result.response_selector == consts.FEATUREBASE_RESPONSE_SELECTOR
    assert result.input_frame_path == [consts.FEATUREBASE_FRAME_SELECTOR]
    assert [action.kind for action in result.setup_actions] == [
        "featurebase_new_message"
    ]
    assert (
        "INTERACTION",
        consts.FEATUREBASE_INTERACTION_DESCRIPTION,
    ) in progress

    await page.set_content(WIDGET)
    strategy = CustomStrategy(plan=result.to_interaction_plan())
    target = await strategy.prepare_page(page)
    assert isinstance(target, Frame)

    await strategy.prepare_response(target)
    await strategy.send_message(target, "image capability prompt")

    assert await strategy.wait_for_response(target, timeout_ms=5_000) == "No"


async def test_featurebase_unbooted_messenger_is_explicit(page, monkeypatch):
    monkeypatch.setattr(consts, "FEATUREBASE_WAIT_MS", 50)
    await page.set_content("<script>window.Featurebase = () => undefined</script>")

    with pytest.raises(ChannelNotReadyError, match="messenger was not booted"):
        await open_featurebase_composer(page)
