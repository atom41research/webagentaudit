"""Regression coverage for page-data collection during navigation."""

import pytest
from playwright.async_api import Error as PlaywrightError

from webagentaudit.cli.app import (
    PageDataCollectionError,
    TargetAssessmentFailure,
    _collect_page_data,
    _open_and_auto_discover,
)
from webagentaudit.core.models import ConfidenceScore
from webagentaudit.detection.models import DetectionResult
from webagentaudit.llm_channel.auto_config.models import AutoConfigResult


pytestmark = pytest.mark.e2e


class _NavigationRacePage:
    """Delegate to a real page after reproducing one transient context loss."""

    def __init__(self, page, *, always_fail: bool = False) -> None:
        self._page = page
        self._always_fail = always_fail
        self._failed = False

    async def content(self):
        self._raise_navigation_error()
        return await self._page.content()

    async def evaluate(self, expression, arg=None):
        self._raise_navigation_error()
        if arg is None:
            return await self._page.evaluate(expression)
        return await self._page.evaluate(expression, arg)

    async def wait_for_load_state(self, *args, **kwargs):
        return await self._page.wait_for_load_state(*args, **kwargs)

    async def wait_for_timeout(self, timeout):
        return await self._page.wait_for_timeout(timeout)

    def _raise_navigation_error(self) -> None:
        if self._always_fail or not self._failed:
            self._failed = True
            raise PlaywrightError(
                "Execution context was destroyed, most likely because of a navigation"
            )


async def test_page_data_collection_retries_navigation_context_loss(
    page, demo_server
):
    url = f"{demo_server}/negative/simple-blog.html"
    await page.goto(url, wait_until="domcontentloaded")

    data = await _collect_page_data(
        _NavigationRacePage(page), url, timeout_ms=1_000
    )

    assert "The Wandering Pixel" in data.html
    assert data.url == url


async def test_page_data_collection_bounds_persistent_navigation(page, demo_server):
    url = f"{demo_server}/negative/simple-blog.html"
    await page.goto(url, wait_until="domcontentloaded")

    with pytest.raises(PageDataCollectionError, match="did not stabilize"):
        await _collect_page_data(
            _NavigationRacePage(page, always_fail=True),
            url,
            timeout_ms=300,
        )


async def test_discovery_classifies_unstable_page_data_as_navigation(
    monkeypatch,
):
    """A bounded collection failure must retain its phase in batch output."""

    class Page:
        async def goto(self, *args, **kwargs):
            return None

        async def wait_for_timeout(self, timeout):
            return None

    class Closeable:
        closed = False

        async def close(self):
            self.closed = True

    closeable = Closeable()

    async def launch(*args, **kwargs):
        return Page(), closeable

    async def collect(*args, **kwargs):
        raise PageDataCollectionError("page kept navigating")

    monkeypatch.setattr("webagentaudit.cli.app._launch_browser", launch)
    monkeypatch.setattr(
        "webagentaudit.cli.app._detection_result_for_page", collect
    )

    with pytest.raises(TargetAssessmentFailure) as raised:
        await _open_and_auto_discover(
            "https://example.test",
            pw=object(),
            browser="chromium",
            headful=False,
            browser_exe=None,
            user_data_dir=None,
            timeout=1_000,
            wait_for_selector=None,
            input_hint=None,
            submit_hint=None,
            response_hint=None,
            screenshots=False,
        )

    assert raised.value.phase == "navigation"
    assert closeable.closed is True


async def test_provider_polling_uses_a_wall_clock_budget(monkeypatch):
    class Page:
        async def goto(self, *args, **kwargs):
            return None

        async def wait_for_timeout(self, timeout):
            return None

    class Closeable:
        async def close(self):
            pass

    calls = 0
    clock = 0.0

    async def launch(*args, **kwargs):
        return Page(), Closeable()

    async def detect(*args, **kwargs):
        nonlocal calls, clock
        calls += 1
        clock += 0.03
        return DetectionResult(
            url="https://example.test",
            llm_detected=False,
            overall_confidence=ConfidenceScore(value=0),
        )

    async def no_input(*args, **kwargs):
        return False

    async def no_plan(*args, **kwargs):
        return AutoConfigResult()

    monkeypatch.setattr("webagentaudit.cli.app._launch_browser", launch)
    monkeypatch.setattr(
        "webagentaudit.cli.app.time.monotonic", lambda: clock
    )
    monkeypatch.setattr("webagentaudit.cli.app._detection_result_for_page", detect)
    monkeypatch.setattr(
        "webagentaudit.llm_channel.auto_config.AlgorithmicAutoConfigurator.has_usable_input",
        no_input,
    )
    monkeypatch.setattr(
        "webagentaudit.llm_channel.auto_config.AlgorithmicAutoConfigurator.configure",
        no_plan,
    )
    monkeypatch.setattr("webagentaudit.cli.app.PROVIDER_DETECTION_MAX_ATTEMPTS", 30)
    monkeypatch.setattr("webagentaudit.cli.app.PROVIDER_DETECTION_TIMEOUT_MS", 50)

    plan, _, _, _ = await _open_and_auto_discover(
        "https://example.test",
        pw=object(),
        browser="chromium",
        headful=False,
        browser_exe=None,
        user_data_dir=None,
        timeout=1_000,
        wait_for_selector=None,
        input_hint=None,
        submit_hint=None,
        response_hint=None,
        screenshots=False,
    )

    assert plan is None
    assert calls == 2
