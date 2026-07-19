"""Standalone LiveChat discovery regressions."""

from pathlib import Path

import pytest

from webagentaudit.llm_channel.auto_config.livechat import (
    LiveChatAutoConfigurator,
)
from webagentaudit.llm_channel.strategies.custom import CustomStrategy

pytestmark = pytest.mark.browser

FIXTURE = (
    Path(__file__).parents[2] / "fixtures" / "livechat_delayed_widget.html"
)
MULTILINGUAL_FIXTURE = (
    Path(__file__).parents[2] / "fixtures" / "livechat_multilingual_gate.html"
)


async def test_livechat_delayed_launcher_discovers_and_replays(page):
    html = FIXTURE.read_text().replace("9000", "25").replace("2500", "25")
    await page.set_content(html)

    result = await LiveChatAutoConfigurator().configure(page, skip_response=True)

    assert result.input_selector == "#message"
    assert result.submit_selector == 'button[aria-label="Send a message"]'
    assert result.input_frame_path == ["iframe#chat-widget"]
    assert [action.kind for action in result.setup_actions] == ["livechat_open"]

    await page.set_content(html)
    target = await CustomStrategy(
        plan=result.to_interaction_plan()
    ).prepare_page(page)
    assert await target.locator(result.input_selector).count() == 1


async def test_livechat_multilingual_gate_discovers_and_replays(
    page, monkeypatch
):
    html = MULTILINGUAL_FIXTURE.read_text()
    await page.set_content(html)
    monkeypatch.setattr(
        "webagentaudit.llm_channel.auto_config.consts.LIVECHAT_WAIT_MS", 3_000
    )
    monkeypatch.setattr(
        "webagentaudit.llm_channel.auto_config.consts.DISCOVERY_INPUT_POLL_MS", 10
    )

    assert await page.locator("iframe#chat-widget").count() == 1
    assert await page.frame_locator(
        "iframe#chat-widget"
    ).locator("#start-chat-button, textarea").count() == 0
    assert await page.frame_locator(
        "iframe#chat-widget-minimized"
    ).locator("button").count() == 1

    result = await LiveChatAutoConfigurator().configure(page, skip_response=True)

    assert result.input_selector
    assert result.submit_selector
    assert result.input_frame_path == ["iframe#chat-widget"]
    assert [action.kind for action in result.setup_actions] == [
        "dismiss",
        "livechat_open",
    ]
    assert result.setup_actions[0].selector == "button.mQxxMq"

    replay_page = await page.context.new_page()
    await replay_page.set_content(html)
    assert await replay_page.locator("button.mQxxMq").is_visible()
    strategy = CustomStrategy(plan=result.to_interaction_plan())
    target = await strategy.prepare_page(replay_page)
    assert await target.locator(result.input_selector).count() == 1
    assert await target.locator(result.submit_selector).count() == 1

    await strategy.send_message(target, "strukturális próba")
    assert await target.locator(result.input_selector).input_value() == ""
