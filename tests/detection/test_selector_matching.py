"""Tests for the SelectorMatchingChecker.

The SelectorMatchingChecker scans the DOM for known chat widget container
selectors such as #intercom-container, .drift-widget, [class*="chatbot"],
[aria-label*="chat"], etc.
"""

import pytest

from webagentaudit.detection.deterministic.selector_matching import SelectorMatchingChecker
from webagentaudit.detection.models import PageData

from tests.conftest import (
    ARIA_LABEL_CHAT_HTML,
    CHATBOT_WRAPPER_HTML,
    DRIFT_WIDGET_HTML,
    INTERCOM_CHAT_HTML,
    SIMPLE_BLOG_HTML,
)


@pytest.fixture
def checker():
    return SelectorMatchingChecker()


def _page(html: str, url: str = "https://example.com") -> PageData:
    return PageData(url=url, html=html)


class TestSelectorMatchingIntercom:
    """Test detection of Intercom-style chat widget containers."""

    def test_intercom_container_detected(self, checker):
        """A page with <div id='intercom-container'> should be detected."""
        page = _page(INTERCOM_CHAT_HTML)
        signals = checker.check(page)

        assert len(signals) >= 1

        widget_selectors = {s.metadata.get("widget_selector") for s in signals}
        assert "#intercom-container" in widget_selectors

    def test_intercom_signals_are_chat_widget_type(self, checker):
        page = _page(INTERCOM_CHAT_HTML)
        signals = checker.check(page)

        for sig in signals:
            assert sig.signal_type == "chat_widget"


class TestSelectorMatchingChatbotClass:
    """Test detection via [class*='chatbot'] pattern."""

    def test_chatbot_wrapper_class_detected(self, checker):
        """A page with class='chatbot-wrapper' should match [class*='chatbot']."""
        page = _page(CHATBOT_WRAPPER_HTML)
        signals = checker.check(page)

        assert len(signals) >= 1

        widget_selectors = {s.metadata.get("widget_selector") for s in signals}
        assert any("chatbot" in sel for sel in widget_selectors if sel)

    def test_chatbot_id_detected(self, checker):
        """A page with id containing 'chatbot' should match [id*='chatbot']."""
        html = """\
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Banking Portal - First National Bank</title>
    <link rel="stylesheet" href="/css/bank.css">
</head>
<body>
    <header class="bank-header">
        <a href="/" class="bank-logo">First National Bank</a>
        <nav>
            <a href="/accounts">Accounts</a>
            <a href="/transfers">Transfers</a>
            <a href="/help">Help</a>
        </nav>
    </header>
    <main class="dashboard">
        <h1>Welcome back, Alex</h1>
        <div class="account-summary">
            <div class="account-card">
                <h3>Checking Account</h3>
                <p class="balance">$4,521.87</p>
            </div>
            <div class="account-card">
                <h3>Savings Account</h3>
                <p class="balance">$12,340.00</p>
            </div>
        </div>
    </main>
    <div id="chatbot-assistant" class="floating-widget">
        <div class="widget-toggle">
            <button aria-label="Open chatbot">Chat with us</button>
        </div>
    </div>
    <script src="/js/dashboard.js"></script>
</body>
</html>"""
        page = _page(html)
        signals = checker.check(page)

        assert len(signals) >= 1
        widget_selectors = {s.metadata.get("widget_selector") for s in signals}
        assert any("chatbot" in sel for sel in widget_selectors if sel)


class TestSelectorMatchingAriaLabel:
    """Test detection via aria-label containing 'chat' or 'assistant'."""

    def test_aria_label_chat_assistant_detected(self, checker):
        """A div with aria-label='chat assistant' should be detected."""
        page = _page(ARIA_LABEL_CHAT_HTML)
        signals = checker.check(page)

        assert len(signals) >= 1

        widget_selectors = {s.metadata.get("widget_selector") for s in signals}
        assert any(
            "aria-label" in sel
            for sel in widget_selectors
            if sel
        )

    def test_aria_label_chat_in_nested_elements(self, checker):
        """Aria-label 'chat' attributes on nested elements should also be found."""
        html = """\
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Product Page - TechShop</title>
</head>
<body>
    <header>
        <a href="/">TechShop</a>
    </header>
    <main>
        <div class="product-detail">
            <h1>Wireless Keyboard Pro</h1>
            <p class="price">$79.99</p>
            <p>Premium mechanical keyboard with wireless connectivity.</p>
            <button class="btn-buy">Buy Now</button>
        </div>
    </main>
    <aside class="support-panel" aria-label="chat support">
        <div class="support-body">
            <p>Need help deciding? Chat with our team.</p>
            <button class="start-chat-btn">Start Chat</button>
        </div>
    </aside>
    <script src="/js/product.js"></script>
</body>
</html>"""
        page = _page(html)
        signals = checker.check(page)

        assert len(signals) >= 1


class TestSelectorMatchingDrift:
    """Test detection of Drift-style chat widget containers."""

    def test_drift_widget_class_detected(self, checker):
        """A page with class='drift-widget' should be detected."""
        page = _page(DRIFT_WIDGET_HTML)
        signals = checker.check(page)

        assert len(signals) >= 1

        widget_selectors = {s.metadata.get("widget_selector") for s in signals}
        assert ".drift-widget" in widget_selectors


class TestSelectorMatchingNoDetection:
    """Test that clean pages with no chat widgets produce no signals."""

    def test_plain_blog_no_widgets(self, checker):
        """A simple blog page with no chat elements should return empty."""
        page = _page(SIMPLE_BLOG_HTML)
        signals = checker.check(page)

        assert signals == []

    def test_empty_html_no_detection(self, checker):
        page = _page("")
        signals = checker.check(page)

        assert signals == []

    def test_standard_saas_page_no_chat_widgets(self, checker):
        """A SaaS landing page without any chat widget elements."""
        html = """\
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Analytics Dashboard - DataViz Pro</title>
    <link rel="stylesheet" href="/css/dashboard.css">
</head>
<body>
    <header class="app-bar">
        <a href="/" class="app-logo">DataViz Pro</a>
        <nav class="app-nav">
            <a href="/dashboard">Dashboard</a>
            <a href="/reports">Reports</a>
            <a href="/settings">Settings</a>
        </nav>
        <div class="user-info">
            <img src="/img/avatar.png" alt="User avatar" class="avatar-sm">
            <span class="user-name">Sarah</span>
        </div>
    </header>
    <main class="dashboard-content">
        <h1>Dashboard Overview</h1>
        <div class="metrics-row">
            <div class="metric-card">
                <h3>Page Views</h3>
                <p class="metric-value">142,857</p>
            </div>
            <div class="metric-card">
                <h3>Unique Visitors</h3>
                <p class="metric-value">54,321</p>
            </div>
            <div class="metric-card">
                <h3>Bounce Rate</h3>
                <p class="metric-value">32.4%</p>
            </div>
        </div>
        <div class="chart-container">
            <canvas id="traffic-chart"></canvas>
        </div>
    </main>
    <footer class="app-footer">
        <p>&copy; 2025 DataViz Pro</p>
    </footer>
    <script src="/js/chart.js"></script>
    <script src="/js/dashboard.js"></script>
</body>
</html>"""
        page = _page(html)
        signals = checker.check(page)

        assert signals == []


class TestSelectorMatchingSignalProperties:
    """Test that returned signals have correct properties."""

    def test_checker_name_is_selector_matching(self, checker):
        page = _page(INTERCOM_CHAT_HTML)
        signals = checker.check(page)

        assert len(signals) >= 1
        for sig in signals:
            assert sig.checker_name == "selector_matching"

    def test_signal_type_is_chat_widget(self, checker):
        page = _page(DRIFT_WIDGET_HTML)
        signals = checker.check(page)

        for sig in signals:
            assert sig.signal_type == "chat_widget"

    def test_evidence_contains_selector_and_snippet(self, checker):
        page = _page(INTERCOM_CHAT_HTML)
        signals = checker.check(page)

        for sig in signals:
            assert sig.evidence  # non-empty

    def test_confidence_uses_chat_widget_weight(self, checker):
        from webagentaudit.detection.consts import SIGNAL_WEIGHT_CHAT_WIDGET

        page = _page(INTERCOM_CHAT_HTML)
        signals = checker.check(page)

        for sig in signals:
            assert sig.confidence.value == SIGNAL_WEIGHT_CHAT_WIDGET

    def test_widget_selector_in_metadata(self, checker):
        page = _page(DRIFT_WIDGET_HTML)
        signals = checker.check(page)

        for sig in signals:
            assert "widget_selector" in sig.metadata
