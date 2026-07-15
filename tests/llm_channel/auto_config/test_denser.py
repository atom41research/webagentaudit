"""Denser-specific discovery regressions."""

from pathlib import Path
from urllib.parse import quote

import pytest
from playwright.async_api import Frame

from webagentaudit.llm_channel.auto_config.denser import DenserAutoConfigurator
from webagentaudit.llm_channel.config import ChannelConfig
from webagentaudit.llm_channel.playwright_channel import PlaywrightChannel
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
    assert [action.kind for action in result.setup_actions] == ["denser_open"]
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


async def test_denser_already_open_discovery_replays_on_fresh_page(page):
    await page.set_content(FIXTURE)
    await page.locator('denser-chatbot button[part="button"]').click()

    result = await DenserAutoConfigurator().configure(page, skip_response=True)

    assert [action.kind for action in result.setup_actions] == ["denser_open"]

    fresh_page = await page.context.new_page()
    try:
        await fresh_page.set_content(FIXTURE)
        target = await CustomStrategy(
            plan=result.to_interaction_plan()
        ).prepare_page(fresh_page)

        assert isinstance(target, Frame)
        assert await target.locator("#message").is_visible()
    finally:
        await fresh_page.close()


async def test_denser_sequential_probes_reuse_live_page_without_refresh(page):
    url = f"data:text/html,{quote(FIXTURE)}"
    await page.goto(url)
    await page.locator('denser-chatbot button[part="button"]').click()
    result = await DenserAutoConfigurator().configure(page, skip_response=True)
    plan = result.to_interaction_plan()

    context = page.context
    navigations = 0

    def count_navigation(frame):
        nonlocal navigations
        if frame is page.main_frame:
            navigations += 1

    page.on("framenavigated", count_navigation)
    for _ in range(2):
        channel = PlaywrightChannel(
            config=ChannelConfig(headless=False),
            strategy=CustomStrategy(plan=plan),
            page=page,
            context=context,
            close_external_page=False,
        )
        await channel.connect(url)
        assert await channel.is_ready()
        await channel.disconnect()
        assert not page.is_closed()
        assert context.pages == [page]

    assert navigations == 0
