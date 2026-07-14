"""Chatbase-specific discovery, replay, and delayed-bootstrap regressions."""

from pathlib import Path

import pytest
from playwright.async_api import Frame

from webagentaudit.llm_channel.auto_config.chatbase import (
    ChatbaseAutoConfigurator,
)
from webagentaudit.llm_channel.strategies.custom import CustomStrategy

pytestmark = pytest.mark.browser

FIXTURE = (
    Path(__file__).parents[2] / "fixtures" / "chatbase_widget.html"
).read_text(encoding="utf-8")


async def test_chatbase_configurator_opens_replays_and_reads_response(page):
    await page.set_content(FIXTURE)

    result = await ChatbaseAutoConfigurator().configure(
        page, skip_response=True
    )

    assert result.input_selector == "#message"
    assert result.submit_selector is None
    assert result.response_selector == (
        '[role="log"] [data-loading-assistant] .prose'
    )
    assert result.input_frame_path == ["#chatbase-bubble-window iframe"]
    assert [action.kind for action in result.setup_actions] == [
        "chatbase_open"
    ]

    await page.set_content(FIXTURE)
    strategy = CustomStrategy(plan=result.to_interaction_plan())
    target = await strategy.prepare_page(page)
    assert isinstance(target, Frame)

    await strategy.prepare_response(target)
    await strategy.send_message(target, "image capability prompt")
    assert await strategy.wait_for_response(target, timeout_ms=5_000) == "No"


async def test_chatbase_configurator_recovers_load_event_stranded_embed(page):
    await page.route(
        "https://www.chatbase.co/embed.min.js",
        lambda route: route.fulfill(
            content_type="application/javascript",
            body="""window.addEventListener('load', () => {
              if (document.querySelector('#chatbase-bubble-button')) return;
              window.openChatbase = () => {
                document.querySelector('#chatbase-bubble-window iframe').srcdoc =
                  '<textarea id="message"></textarea>';
              };
              document.body.insertAdjacentHTML('beforeend',
                '<button id="chatbase-bubble-button" ' +
                  'onclick="openChatbase()">Open</button>' +
                '<div id="chatbase-bubble-window"><iframe></iframe></div>'
              );
            });""",
        ),
    )
    await page.set_content(
        """<!doctype html><script>
        window.chatbase = () => undefined;
        window.addEventListener('load', () => {
          if (document.querySelector('script[src*="chatbase.co/embed"]')) return;
          const script = document.createElement('script');
          script.src = 'https://www.chatbase.co/embed.min.js';
          document.body.appendChild(script);
        });
        </script>"""
    )

    result = await ChatbaseAutoConfigurator().configure(
        page, skip_response=True
    )

    assert result.input_selector == "#message"
    assert await page.locator("#chatbase-bubble-button").is_visible()
