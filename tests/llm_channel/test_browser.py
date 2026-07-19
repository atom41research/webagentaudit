from unittest.mock import AsyncMock

import pytest
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from webagentaudit.llm_channel.browser import (
    browser_launch_options,
    goto_and_inspect,
    wait_for_domcontentloaded_and_inspect,
)


@pytest.mark.asyncio
async def test_navigation_timeout_returns_control_for_dom_inspection():
    page = AsyncMock()
    page.goto.side_effect = PlaywrightTimeoutError("still loading")

    assert await goto_and_inspect(page, "https://example.test", 20_000) is None
    page.goto.assert_awaited_once_with(
        "https://example.test",
        wait_until="domcontentloaded",
        timeout=20_000,
    )


@pytest.mark.asyncio
async def test_response_timeout_does_not_extend_navigation_budget():
    page = AsyncMock()
    page.goto.side_effect = PlaywrightTimeoutError("still loading")

    assert await goto_and_inspect(page, "https://example.test", 120_000) is None

    page.goto.assert_awaited_once_with(
        "https://example.test",
        wait_until="domcontentloaded",
        timeout=20_000,
    )


@pytest.mark.asyncio
async def test_page_handoff_uses_bounded_navigation_budget():
    page = AsyncMock()
    page.wait_for_load_state.side_effect = PlaywrightTimeoutError("still loading")

    await wait_for_domcontentloaded_and_inspect(page, 120_000)

    page.wait_for_load_state.assert_awaited_once_with(
        "domcontentloaded", timeout=20_000
    )


def test_chrome_launch_options_are_shared():
    options = browser_launch_options(
        "chromium", extra_args=["--start-fullscreen"]
    )

    assert options == {
        "channel": "chrome",
        "args": [
            "--disable-blink-features=AutomationControlled",
            "--start-fullscreen",
        ],
    }
