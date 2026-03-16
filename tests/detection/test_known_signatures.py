"""Tests for the KnownSignatureChecker.

The KnownSignatureChecker scans external script URLs, inline scripts, and raw
HTML for known LLM provider script fragments (Intercom, Drift, Tidio, etc.).
"""

import pytest

from webagentaudit.detection.consts import SIGNAL_WEIGHT_KNOWN_PROVIDER
from webagentaudit.detection.deterministic.known_signatures import KnownSignatureChecker
from webagentaudit.detection.models import PageData

from tests.conftest import (
    DRIFT_WIDGET_HTML,
    INTERCOM_CHAT_HTML,
    MULTI_PROVIDER_HTML,
    SIMPLE_BLOG_HTML,
    TIDIO_EMBED_HTML,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def checker():
    return KnownSignatureChecker()


def _page(
    html: str = "<html><body></body></html>",
    url: str = "https://example.com",
    scripts: list[str] | None = None,
    inline_scripts: list[str] | None = None,
) -> PageData:
    return PageData(
        url=url,
        html=html,
        scripts=scripts or [],
        inline_scripts=inline_scripts or [],
    )


class TestKnownSignatureIntercom:
    """Test Intercom provider detection."""

    def test_intercom_script_url_detected(self, checker):
        """A page with a script from widget.intercom.io should detect Intercom."""
        page = _page(
            scripts=["https://widget.intercom.io/widget/abc123"],
        )
        signals = checker.check(page)

        assert len(signals) >= 1
        providers = {s.metadata.get("provider") for s in signals}
        assert "intercom" in providers

    def test_intercom_cdn_script_detected(self, checker):
        """A script from js.intercomcdn.com should also detect Intercom."""
        page = _page(
            scripts=["https://js.intercomcdn.com/vendor-bundle.js"],
        )
        signals = checker.check(page)

        providers = {s.metadata.get("provider") for s in signals}
        assert "intercom" in providers

    def test_intercom_in_html_source(self, checker):
        """Intercom script tag embedded in HTML should be detected."""
        page = _page(html=INTERCOM_CHAT_HTML)
        signals = checker.check(page)

        providers = {s.metadata.get("provider") for s in signals}
        assert "intercom" in providers


class TestKnownSignatureDrift:
    """Test Drift provider detection."""

    def test_drift_script_url_detected(self, checker):
        """A page with a script from js.driftt.com should detect Drift."""
        page = _page(
            scripts=["https://js.driftt.com/include/abc.js"],
        )
        signals = checker.check(page)

        assert len(signals) >= 1
        providers = {s.metadata.get("provider") for s in signals}
        assert "drift" in providers

    def test_drift_alternate_domain_detected(self, checker):
        """A script from js.drift.com should also detect Drift."""
        page = _page(
            scripts=["https://js.drift.com/widget.js"],
        )
        signals = checker.check(page)

        providers = {s.metadata.get("provider") for s in signals}
        assert "drift" in providers

    def test_drift_in_html_source(self, checker):
        """Drift script embedded in the HTML fixture should be detected."""
        page = _page(html=DRIFT_WIDGET_HTML)
        signals = checker.check(page)

        providers = {s.metadata.get("provider") for s in signals}
        assert "drift" in providers


class TestKnownSignatureTidio:
    """Test Tidio provider detection."""

    def test_tidio_script_in_html(self, checker):
        """A <script src='https://code.tidio.co/xyz.js'> embedded in HTML
        should detect Tidio."""
        page = _page(html=TIDIO_EMBED_HTML)
        signals = checker.check(page)

        providers = {s.metadata.get("provider") for s in signals}
        assert "tidio" in providers

    def test_tidio_script_url_detected(self, checker):
        """Tidio script URL in the scripts list should be detected."""
        page = _page(
            scripts=["https://code.tidio.co/abc123def.js"],
        )
        signals = checker.check(page)

        providers = {s.metadata.get("provider") for s in signals}
        assert "tidio" in providers


class TestKnownSignatureNoDetection:
    """Test that unrelated scripts do not trigger false positives."""

    def test_jquery_script_no_detection(self, checker):
        """A page loading only jQuery should produce no signals."""
        page = _page(
            scripts=["https://cdn.jquery.com/jquery.min.js"],
        )
        signals = checker.check(page)

        assert signals == []

    def test_generic_analytics_no_detection(self, checker):
        """Common analytics scripts should not trigger detection."""
        page = _page(
            scripts=[
                "https://www.google-analytics.com/analytics.js",
                "https://cdn.segment.com/analytics.js/v1/abc/analytics.min.js",
                "https://www.googletagmanager.com/gtag/js?id=G-ABC123",
            ],
        )
        signals = checker.check(page)

        assert signals == []

    def test_simple_blog_no_detection(self, checker):
        """A plain blog page HTML should not trigger any provider detection."""
        page = _page(html=SIMPLE_BLOG_HTML)
        signals = checker.check(page)

        assert signals == []

    def test_empty_scripts_no_detection(self, checker):
        """No scripts at all should produce no signals."""
        page = _page(scripts=[], html="<html><body>Nothing here</body></html>")
        signals = checker.check(page)

        assert signals == []


class TestKnownSignatureMultipleProviders:
    """Test detection of multiple providers on a single page."""

    def test_two_providers_both_detected(self, checker):
        """A page loading both Intercom and Drift scripts should detect both."""
        page = _page(
            scripts=[
                "https://widget.intercom.io/widget/agency123",
                "https://js.driftt.com/include/xyz456/drift.min.js",
            ],
        )
        signals = checker.check(page)

        providers = {s.metadata.get("provider") for s in signals}
        assert "intercom" in providers
        assert "drift" in providers

    def test_multi_provider_html_fixture(self, checker):
        """The multi-provider HTML fixture should detect both Intercom and Drift."""
        page = _page(html=MULTI_PROVIDER_HTML)
        signals = checker.check(page)

        providers = {s.metadata.get("provider") for s in signals}
        assert "intercom" in providers
        assert "drift" in providers

    def test_three_providers_on_one_page(self, checker):
        """A page with Intercom, Tidio, and Zendesk should detect all three."""
        page = _page(
            scripts=[
                "https://widget.intercom.io/widget/abc",
                "https://code.tidio.co/xyz.js",
                "https://static.zdassets.com/ekr/snippet.js",
            ],
        )
        signals = checker.check(page)

        providers = {s.metadata.get("provider") for s in signals}
        assert "intercom" in providers
        assert "tidio" in providers
        assert "zendesk" in providers


class TestKnownSignatureDeduplication:
    """Test that duplicate fragments don't produce duplicate signals."""

    def test_same_fragment_in_scripts_and_html_deduped(self, checker):
        """If the same script URL appears in both the scripts list and the
        HTML source, only one signal per (provider, fragment) should be emitted."""
        intercom_url = "https://widget.intercom.io/widget/abc123"
        html = f"""\
<!DOCTYPE html>
<html>
<head><title>Test</title></head>
<body>
    <p>Content</p>
    <script src="{intercom_url}"></script>
</body>
</html>"""
        page = _page(html=html, scripts=[intercom_url])
        signals = checker.check(page)

        # Should have exactly one signal for intercom/widget.intercom.io
        intercom_signals = [
            s for s in signals
            if s.metadata.get("provider") == "intercom"
            and "widget.intercom.io" in s.evidence
        ]
        assert len(intercom_signals) == 1


class TestKnownSignatureSignalProperties:
    """Test that returned signals carry correct properties."""

    def test_signal_type_is_known_provider(self, checker):
        page = _page(scripts=["https://widget.intercom.io/widget/abc"])
        signals = checker.check(page)

        for sig in signals:
            assert sig.signal_type == "known_provider"

    def test_checker_name_is_known_signatures(self, checker):
        page = _page(scripts=["https://js.driftt.com/include/x.js"])
        signals = checker.check(page)

        for sig in signals:
            assert sig.checker_name == "known_signatures"

    def test_confidence_uses_known_provider_weight(self, checker):
        page = _page(scripts=["https://code.tidio.co/abc.js"])
        signals = checker.check(page)

        for sig in signals:
            assert sig.confidence.value == SIGNAL_WEIGHT_KNOWN_PROVIDER

    def test_provider_in_metadata(self, checker):
        page = _page(scripts=["https://widget.intercom.io/widget/abc"])
        signals = checker.check(page)

        for sig in signals:
            assert "provider" in sig.metadata
            assert isinstance(sig.metadata["provider"], str)

    def test_evidence_contains_fragment(self, checker):
        page = _page(scripts=["https://widget.intercom.io/widget/abc"])
        signals = checker.check(page)

        for sig in signals:
            assert sig.evidence  # non-empty
            assert "intercom" in sig.evidence or "widget" in sig.evidence


class TestKnownSignatureAdditionalProviders:
    """Test a broader set of known providers beyond Intercom/Drift/Tidio."""

    @pytest.mark.parametrize(
        "script_url,expected_provider",
        [
            ("https://static.zdassets.com/ekr/snippet.js", "zendesk"),
            ("https://wchat.freshchat.com/js/widget.js", "freshdesk"),
            ("https://client.crisp.chat/l.js", "crisp"),
            ("https://cdn.livechatinc.com/tracking.js", "livechat"),
            ("https://js.usemessages.com/conversations-embed.js", "hubspot"),
            ("https://embed.tawk.to/abc123/default", "tawk"),
            ("https://static.olark.com/jsclient/loader.js", "olark"),
            ("https://app.chatwoot.com/packs/js/sdk.js", "chatwoot"),
            ("https://cdn.botpress.cloud/webchat/v1/inject.js", "botpress"),
            ("https://cdn.voiceflow.com/widget/bundle.mjs", "voiceflow"),
            ("https://widget.kommunicate.io/v2/kommunicate.app", "kommunicate"),
            ("https://static.ada.support/embed.js", "ada"),
        ],
    )
    def test_provider_detected(self, checker, script_url, expected_provider):
        page = _page(scripts=[script_url])
        signals = checker.check(page)

        providers = {s.metadata.get("provider") for s in signals}
        assert expected_provider in providers
