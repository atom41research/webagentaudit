"""Shared browser fixtures for auto_config Playwright tests."""

import pytest
from playwright.async_api import async_playwright


@pytest.fixture(scope="session")
async def _pw_auto():
    """Single Playwright instance per session/worker."""
    pw = await async_playwright().start()
    yield pw
    await pw.stop()


@pytest.fixture(scope="session")
async def browser(_pw_auto):
    """Single browser per session/worker."""
    b = await _pw_auto.chromium.launch(headless=True)
    yield b
    await b.close()


@pytest.fixture
async def page(browser):
    """Fresh isolated context per test (cheap ~5-20ms vs ~500-2000ms for browser launch)."""
    context = await browser.new_context(viewport={"width": 1280, "height": 720})
    pg = await context.new_page()
    yield pg
    await context.close()
