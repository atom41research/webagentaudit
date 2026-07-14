"""Denser-specific discovery regressions."""

from pathlib import Path

import pytest
from playwright.async_api import Frame

from webagentaudit.llm_channel.auto_config.denser import DenserAutoConfigurator
from webagentaudit.llm_channel.strategies.custom import CustomStrategy

pytestmark = pytest.mark.browser

FIXTURE = (
    Path(__file__).parents[2] / "fixtures" / "denser_embed_widget.html"
).read_text(encoding="utf-8")


async def test_denser_configurator_opens_and_replays_real_embed_structure(page):
    await page.set_content(FIXTURE)

    result = await DenserAutoConfigurator().configure(page, skip_response=True)

    assert result.input_selector == "#message"
    assert result.submit_selector is None
    assert result.response_selector == (
        ".bg-incomingchat .text-incomingchat-foreground"
    )
    assert result.input_frame_path == ['iframe[title="Denser Chatbot"]']
    assert [action.kind for action in result.setup_actions] == ["trigger"]
    assert result.setup_actions[0].selector == (
        'denser-chatbot button[part="button"]'
    )

    await page.set_content(FIXTURE)
    target = await CustomStrategy(
        plan=result.to_interaction_plan()
    ).prepare_page(page)

    assert isinstance(target, Frame)
    assert await target.locator("#message").is_visible()

    strategy = CustomStrategy(plan=result.to_interaction_plan())
    await strategy.prepare_response(target)
    await strategy.send_message(target, "test prompt")

    assert await target.locator("#message").input_value() == ""
    assert await strategy.wait_for_response(target, timeout_ms=5_000) == "No"
