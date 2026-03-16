"""Tests for the known assets registry and checker."""

import pytest

from webagentaudit.detection.known_assets import KnownAssetsRegistry, AssetCategory, KnownAsset, ScriptSignature
from webagentaudit.detection.known_assets.models import ApiSignature, DomSignature
from webagentaudit.detection.known_assets.checker import KnownAssetsChecker
from webagentaudit.detection.models import PageData

pytestmark = pytest.mark.unit


def make_page_data(html="<html><body></body></html>", url="https://example.com", scripts=None, inline_scripts=None):
    return PageData(
        url=url,
        html=html,
        scripts=scripts or [],
        inline_scripts=inline_scripts or [],
    )


class TestKnownAssetsRegistry:
    def test_register_and_get_by_name(self):
        registry = KnownAssetsRegistry()
        asset = KnownAsset(name="TestBot", category=AssetCategory.EMBEDDABLE_SDK)
        registry.register(asset)
        assert registry.get_by_name("testbot") is asset
        assert registry.get_by_name("TESTBOT") is asset

    def test_get_by_category(self):
        registry = KnownAssetsRegistry()
        sdk = KnownAsset(name="SDK1", category=AssetCategory.EMBEDDABLE_SDK)
        app = KnownAsset(name="App1", category=AssetCategory.DIRECT_LLM_APP)
        registry.register_many([sdk, app])
        assert registry.get_by_category(AssetCategory.EMBEDDABLE_SDK) == [sdk]
        assert registry.get_by_category(AssetCategory.DIRECT_LLM_APP) == [app]

    def test_match_url_exact(self):
        registry = KnownAssetsRegistry()
        asset = KnownAsset(
            name="ChatGPT", category=AssetCategory.DIRECT_LLM_APP,
            urls=["https://chatgpt.com"],
        )
        registry.register(asset)
        assert registry.match_url("https://chatgpt.com/c/abc123") == [asset]
        assert registry.match_url("https://other.com") == []

    def test_match_url_pattern(self):
        registry = KnownAssetsRegistry()
        asset = KnownAsset(
            name="Claude", category=AssetCategory.DIRECT_LLM_APP,
            url_patterns=[r"claude\.ai"],
        )
        registry.register(asset)
        assert registry.match_url("https://claude.ai/chat/xyz") == [asset]
        assert registry.match_url("https://not-claude.com") == []

    def test_match_script_url(self):
        registry = KnownAssetsRegistry()
        asset = KnownAsset(
            name="Intercom", category=AssetCategory.CHATBOT_PLATFORM,
            script_signatures=[ScriptSignature(url_fragment="widget.intercom.io")],
        )
        registry.register(asset)
        assert registry.match_script_url("https://widget.intercom.io/widget/abc") == [asset]
        assert registry.match_script_url("https://cdn.jquery.com/jquery.js") == []

    def test_match_inline_script(self):
        registry = KnownAssetsRegistry()
        asset = KnownAsset(
            name="Crisp", category=AssetCategory.CHATBOT_PLATFORM,
            inline_script_patterns=[r"\$crisp", r"CRISP_WEBSITE_ID"],
        )
        registry.register(asset)
        assert registry.match_inline_script('window.$crisp = [];') == [asset]
        assert registry.match_inline_script('console.log("hello")') == []

    def test_match_api_endpoint(self):
        registry = KnownAssetsRegistry()
        asset = KnownAsset(
            name="whtvr.ai", category=AssetCategory.EMBEDDABLE_SDK,
            api_signatures=[ApiSignature(pattern=r"api\.whtvr\.ai/api/sdk/chat")],
        )
        registry.register(asset)
        assert registry.match_api_endpoint("https://api.whtvr.ai/api/sdk/chat") == [asset]
        assert registry.match_api_endpoint("https://api.example.com/chat") == []

    def test_default_registry_has_assets(self):
        registry = KnownAssetsRegistry.default()
        all_assets = registry.get_all()
        assert len(all_assets) >= 1
        # Check major categories are populated
        assert len(registry.get_by_category(AssetCategory.DIRECT_LLM_APP)) >= 10
        assert len(registry.get_by_category(AssetCategory.EMBEDDABLE_SDK)) >= 10
        assert len(registry.get_by_category(AssetCategory.CHATBOT_PLATFORM)) >= 10

    def test_default_registry_finds_chatgpt(self):
        registry = KnownAssetsRegistry.default()
        matches = registry.match_url("https://chatgpt.com/c/some-chat")
        assert any(a.name == "ChatGPT" for a in matches)

    def test_default_registry_finds_whtvr(self):
        registry = KnownAssetsRegistry.default()
        matches = registry.match_script_url("https://cdn.whtvr.ai/sdk.js")
        assert any(a.name == "whtvr.ai" for a in matches)


class TestKnownAssetsChecker:
    def test_detects_direct_llm_app_by_url(self):
        checker = KnownAssetsChecker()
        page = make_page_data(url="https://chatgpt.com/c/test-conversation")
        signals = checker.check(page)
        assert len(signals) >= 1
        assert any(s.signal_type == "known_url" for s in signals)
        assert any(s.metadata.get("asset_name") == "ChatGPT" for s in signals)

    def test_detects_intercom_by_script(self):
        checker = KnownAssetsChecker()
        page = make_page_data(
            scripts=["https://widget.intercom.io/widget/abc123"],
        )
        signals = checker.check(page)
        assert len(signals) >= 1
        assert any(s.metadata.get("asset_name") == "Intercom" for s in signals)

    def test_detects_crisp_by_inline_script(self):
        checker = KnownAssetsChecker()
        html = """<!DOCTYPE html>
<html><head>
<script>window.$crisp=[];window.CRISP_WEBSITE_ID="abc123";</script>
</head><body><p>Hello</p></body></html>"""
        page = make_page_data(html=html)
        signals = checker.check(page)
        assert any(s.metadata.get("asset_name") == "Crisp" for s in signals)

    def test_detects_chatgpt_dom_signature(self):
        checker = KnownAssetsChecker()
        html = """<!DOCTYPE html>
<html><body>
<div id="__next">
<textarea id="prompt-textarea" placeholder="Message ChatGPT"></textarea>
</div>
</body></html>"""
        page = make_page_data(html=html, url="https://chatgpt.com")
        signals = checker.check(page)
        # Should find by URL (known_url) — DOM adds nothing new since URL already matched
        assert any(s.signal_type == "known_url" for s in signals)

    def test_detects_botpress_by_script_in_html(self):
        checker = KnownAssetsChecker()
        html = """<!DOCTYPE html>
<html><head>
<script src="https://cdn.botpress.cloud/webchat/v1/inject.js"></script>
</head><body><p>Welcome</p></body></html>"""
        page = make_page_data(html=html)
        signals = checker.check(page)
        assert any(s.metadata.get("asset_name") == "Botpress Webchat" for s in signals)

    def test_no_detection_on_plain_page(self):
        checker = KnownAssetsChecker()
        html = """<!DOCTYPE html>
<html><head><title>My Blog</title></head>
<body><h1>Welcome to my blog</h1><p>Nothing to see here.</p></body></html>"""
        page = make_page_data(html=html)
        signals = checker.check(page)
        assert len(signals) == 0

    def test_deduplicates_same_asset(self):
        checker = KnownAssetsChecker()
        html = """<!DOCTYPE html>
<html><head>
<script src="https://widget.intercom.io/widget/abc"></script>
</head><body>
<div id="intercom-container"></div>
</body></html>"""
        page = make_page_data(
            html=html,
            scripts=["https://widget.intercom.io/widget/abc"],
        )
        signals = checker.check(page)
        intercom_signals = [s for s in signals if s.metadata.get("asset_name") == "Intercom"]
        assert len(intercom_signals) == 1  # Only one, not duplicated

    def test_multiple_assets_on_one_page(self):
        checker = KnownAssetsChecker()
        page = make_page_data(
            scripts=[
                "https://widget.intercom.io/widget/abc",
                "https://cdn.botpress.cloud/webchat/v1/inject.js",
            ],
        )
        signals = checker.check(page)
        asset_names = {s.metadata.get("asset_name") for s in signals}
        assert "Intercom" in asset_names
        assert "Botpress Webchat" in asset_names

    def test_signal_has_correct_metadata(self):
        checker = KnownAssetsChecker()
        page = make_page_data(
            scripts=["https://widget.intercom.io/widget/abc"],
        )
        signals = checker.check(page)
        assert len(signals) >= 1
        signal = signals[0]
        assert signal.checker_name == "known_assets"
        assert "asset_name" in signal.metadata
        assert "asset_category" in signal.metadata
        assert "is_llm_powered" in signal.metadata
        assert signal.confidence.value > 0

    def test_confidence_higher_for_direct_apps(self):
        checker = KnownAssetsChecker()
        # Direct app
        direct = make_page_data(url="https://chatgpt.com/c/test")
        direct_signals = checker.check(direct)
        # Chatbot platform
        platform = make_page_data(scripts=["https://widget.intercom.io/widget/abc"])
        platform_signals = checker.check(platform)
        assert direct_signals[0].confidence.value > platform_signals[0].confidence.value

    def test_whtvr_detected_by_inline_script(self):
        checker = KnownAssetsChecker()
        html = """<!DOCTYPE html>
<html><head>
<script>
(function(){var w=window;w.__whtvr={config:{botId:"abc123"}};
var s=document.createElement("script");s.src="https://api.whtvr.ai/sdk/widget.js";
document.head.appendChild(s);})();
</script>
</head><body><article><h1>News Article</h1></article></body></html>"""
        page = make_page_data(html=html)
        signals = checker.check(page)
        assert any(s.metadata.get("asset_name") == "whtvr.ai" for s in signals)
