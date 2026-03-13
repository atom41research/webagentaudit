"""End-to-end detection tests against demo pages.

These tests launch a local HTTP server, load real demo pages in Playwright,
collect PageData, and run the full detection pipeline.
"""

from __future__ import annotations

import pytest
from playwright.async_api import Page

from webagentaudit.detection.detector import LlmDetector
from webagentaudit.detection.deterministic.ai_indicators import AiIndicatorChecker
from webagentaudit.detection.deterministic.dom_patterns import DomPatternChecker
from webagentaudit.detection.deterministic.known_signatures import KnownSignatureChecker
from webagentaudit.detection.deterministic.network_hints import NetworkHintsChecker
from webagentaudit.detection.deterministic.script_analysis import ScriptAnalysisChecker
from webagentaudit.detection.deterministic.selector_matching import SelectorMatchingChecker
from webagentaudit.detection.known_assets.checker import KnownAssetsChecker
from webagentaudit.detection.models import PageData


def _create_detector() -> LlmDetector:
    detector = LlmDetector()
    detector.register_checker(DomPatternChecker())
    detector.register_checker(SelectorMatchingChecker())
    detector.register_checker(KnownSignatureChecker())
    detector.register_checker(ScriptAnalysisChecker())
    detector.register_checker(AiIndicatorChecker())
    detector.register_checker(NetworkHintsChecker())
    detector.register_checker(KnownAssetsChecker())
    return detector


async def _collect_page_data(page: Page, url: str) -> PageData:
    """Collect PageData from a live Playwright page."""
    html = await page.content()
    scripts = await page.evaluate(
        "() => Array.from(document.querySelectorAll('script[src]')).map(s => s.src)"
    )
    inline_scripts = await page.evaluate(
        "() => Array.from(document.querySelectorAll('script:not([src])'))"
        ".map(s => s.textContent || '').filter(t => t.trim().length > 0)"
    )
    stylesheets = await page.evaluate(
        "() => Array.from(document.querySelectorAll('link[rel=\"stylesheet\"]'))"
        ".map(l => l.href)"
    )
    meta_tags = await page.evaluate("""() => {
        const m = {};
        document.querySelectorAll('meta[name], meta[property]').forEach(el => {
            const key = el.getAttribute('name') || el.getAttribute('property');
            m[key] = el.getAttribute('content') || '';
        });
        return m;
    }""")
    iframes = await page.evaluate(
        "() => Array.from(document.querySelectorAll('iframe'))"
        ".map(f => f.src).filter(s => s)"
    )
    return PageData(
        url=url, html=html, scripts=scripts, inline_scripts=inline_scripts,
        stylesheets=stylesheets, meta_tags=meta_tags, iframes=iframes,
    )


# ---------------------------------------------------------------------------
# Detection: positive cases (pages that should be detected as having LLMs)
# ---------------------------------------------------------------------------


class TestDetectionPositive:
    """Pages with chat widgets / LLM interfaces should be detected."""

    @pytest.mark.parametrize("path,desc", [
        ("interactive/echo-llm.html", "echo chat"),
        ("interactive/vulnerable-llm.html", "vulnerable chat"),
        ("interactive/safe-llm.html", "safe chat"),
    ])
    async def test_interactive_pages_detected(
        self, page, demo_server, path, desc
    ):
        url = f"{demo_server}/{path}"
        await page.goto(url, wait_until="domcontentloaded")
        await page.wait_for_timeout(500)

        page_data = await _collect_page_data(page, url)
        detector = _create_detector()
        result = detector.detect(page_data)

        assert result.llm_detected, f"Should detect LLM on {desc}: {url}"
        assert result.overall_confidence.value > 0, "Should have non-zero confidence"
        assert len(result.signals) > 0, "Should have at least one signal"


# ---------------------------------------------------------------------------
# Detection: negative cases (pages without LLMs)
# ---------------------------------------------------------------------------


class TestDetectionNegative:
    """Pages without chat widgets should NOT be detected as having LLMs."""

    @pytest.mark.parametrize("path,desc", [
        ("negative/simple-blog.html", "blog"),
        ("negative/contact-form.html", "contact form"),
        ("negative/ecommerce.html", "ecommerce"),
        ("negative/search-only.html", "search page"),
    ])
    async def test_negative_pages_not_detected(
        self, page, demo_server, path, desc
    ):
        url = f"{demo_server}/{path}"
        await page.goto(url, wait_until="domcontentloaded")
        await page.wait_for_timeout(500)

        page_data = await _collect_page_data(page, url)
        detector = _create_detector()
        result = detector.detect(page_data)

        assert not result.llm_detected, (
            f"Should NOT detect LLM on {desc}: {url}"
        )


# ---------------------------------------------------------------------------
# Detection result structure
# ---------------------------------------------------------------------------


class TestDetectionResultStructure:
    """Verify the DetectionResult structure is correct."""

    async def test_result_has_url(self, page, demo_server):
        url = f"{demo_server}/interactive/echo-llm.html"
        await page.goto(url, wait_until="domcontentloaded")
        await page.wait_for_timeout(500)

        page_data = await _collect_page_data(page, url)
        detector = _create_detector()
        result = detector.detect(page_data)

        assert result.url == url

    async def test_result_serializes_to_json(self, page, demo_server):
        url = f"{demo_server}/interactive/echo-llm.html"
        await page.goto(url, wait_until="domcontentloaded")
        await page.wait_for_timeout(500)

        page_data = await _collect_page_data(page, url)
        detector = _create_detector()
        result = detector.detect(page_data)

        import json
        data = json.loads(result.model_dump_json())
        assert "url" in data
        assert "llm_detected" in data
        assert "signals" in data
        assert isinstance(data["signals"], list)

    async def test_signals_have_checker_name(self, page, demo_server):
        url = f"{demo_server}/interactive/echo-llm.html"
        await page.goto(url, wait_until="domcontentloaded")
        await page.wait_for_timeout(500)

        page_data = await _collect_page_data(page, url)
        detector = _create_detector()
        result = detector.detect(page_data)

        for signal in result.signals:
            assert signal.checker_name
            assert signal.signal_type
            assert signal.description
