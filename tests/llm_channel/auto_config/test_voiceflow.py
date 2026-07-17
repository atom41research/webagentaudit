"""Voiceflow-specific discovery, replay, and response regressions."""

import json

import pytest

from webagentaudit.core.exceptions import ChannelNotReadyError
from webagentaudit.llm_channel.auto_config import consts
from webagentaudit.llm_channel.auto_config.voiceflow import (
    VoiceflowAutoConfigurator,
    open_voiceflow_widget,
)
from webagentaudit.llm_channel.strategies.custom import CustomStrategy

pytestmark = pytest.mark.browser


def _widget_html(*, legacy: bool, responses: list[str] | None = None) -> str:
    greeting = (
        '<div class="vfrc-system-response vfrc-system-response--message">Hello</div>'
        if legacy else ""
    )
    placeholder = "Message…" if legacy else "Type a message..."
    responses_json = json.dumps(responses or ["No"])
    return f"""<!doctype html><script>
      window.voiceflow = {{chat: {{open() {{
        if (document.querySelector('#voiceflow-chat')) return;
        const host = document.createElement('div');
        host.id = 'voiceflow-chat';
        document.body.append(host);
        const root = host.attachShadow({{mode: 'open'}});
        root.innerHTML = `<div class="messages">{greeting}</div>
          <textarea placeholder="{placeholder}"></textarea>`;
        const input = root.querySelector('textarea');
        input.onkeydown = event => {{
          if (event.key !== 'Enter') return;
          input.value = '';
          for (const text of {responses_json}) {{
            const response = document.createElement('div');
            response.className = 'vfrc-system-response';
            response.textContent = text;
            root.querySelector('.messages').append(response);
          }}
        }};
      }}}}}};
    </script>"""


@pytest.mark.parametrize("legacy", [False, True])
async def test_voiceflow_configurator_replays_and_reads_response(page, legacy):
    fixture = _widget_html(legacy=legacy)
    await page.set_content(fixture)

    result = await VoiceflowAutoConfigurator().configure(
        page, skip_response=True
    )

    assert result.input_selector == "#voiceflow-chat textarea"
    assert result.response_selector == ".vfrc-system-response"
    assert result.submit_selector is None
    assert [action.kind for action in result.setup_actions] == [
        "voiceflow_open"
    ]

    await page.set_content(fixture)
    strategy = CustomStrategy(plan=result.to_interaction_plan())
    target = await strategy.prepare_page(page)
    await strategy.prepare_response(target)
    await strategy.send_message(target, "image capability prompt")

    assert await strategy.wait_for_response(target, timeout_ms=5_000) == "No"


async def test_voiceflow_reads_every_new_assistant_part(page):
    responses = ["def my_fibonacci(n): return n", "Did that help?"]
    fixture = _widget_html(legacy=True, responses=responses)
    await page.set_content(fixture)
    result = await VoiceflowAutoConfigurator().configure(page, skip_response=True)

    strategy = CustomStrategy(plan=result.to_interaction_plan())
    target = await strategy.prepare_page(page)
    await strategy.prepare_response(target)
    await strategy.send_message(target, "write Fibonacci")

    assert await strategy.wait_for_response(target, timeout_ms=5_000) == (
        "\n\n".join(responses)
    )
    metadata = await strategy.get_response_metadata(target)
    assert metadata["response_parts"] == "2"
    assert metadata["response_mode"] == "explicit"


async def test_voiceflow_api_unavailable_is_explicit(page, monkeypatch):
    monkeypatch.setattr(consts, "VOICEFLOW_WAIT_MS", 50)
    await page.set_content("<div>page with a broken Voiceflow embed</div>")

    with pytest.raises(ChannelNotReadyError, match="API did not become available"):
        await open_voiceflow_widget(page)
