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


async def test_livechat_multilingual_gate_discovers_and_replays(page):
    html = MULTILINGUAL_FIXTURE.read_text()
    await page.set_content(html)

    result = await LiveChatAutoConfigurator().configure(page, skip_response=True)

    assert result.input_selector
    assert result.submit_selector
    assert result.input_frame_path == ["iframe#chat-widget"]
    assert [action.kind for action in result.setup_actions] == ["livechat_open"]

    await page.set_content(html)
    strategy = CustomStrategy(plan=result.to_interaction_plan())
    target = await strategy.prepare_page(page)
    assert await target.locator(result.input_selector).count() == 1
    assert await target.locator(result.submit_selector).count() == 1

    await strategy.send_message(target, "strukturális próba")
    assert await target.locator(result.input_selector).input_value() == ""
