"""Tests for the NetworkHintsChecker.

The NetworkHintsChecker scans script URLs, inline scripts, raw HTML,
form actions, and anchor hrefs for API endpoint patterns suggesting
LLM backends (e.g., /api/v1/chat/completions, /v1/messages).
"""

import pytest

from webagentaudit.detection.consts import SIGNAL_WEIGHT_NETWORK_HINT
from webagentaudit.detection.deterministic.network_hints import NetworkHintsChecker
from webagentaudit.detection.models import PageData

from tests.conftest import SIMPLE_BLOG_HTML

pytestmark = pytest.mark.unit


@pytest.fixture
def checker():
    return NetworkHintsChecker()


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


# ---------------------------------------------------------------------------
# Realistic HTML fixtures
# ---------------------------------------------------------------------------

CHAT_APP_WITH_API_FORM_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>IntelliChat - AI Assistant Platform</title>
    <link rel="stylesheet" href="/css/app.css">
</head>
<body>
    <header class="app-header">
        <a href="/" class="brand">IntelliChat</a>
        <nav>
            <a href="/dashboard">Dashboard</a>
            <a href="/history">Chat History</a>
            <a href="/settings">Settings</a>
        </nav>
    </header>
    <main class="chat-main">
        <div class="conversation-panel" id="conversation">
            <div class="msg assistant">
                <p>Hello! I'm your AI assistant. How can I help today?</p>
            </div>
        </div>
        <form action="/api/v1/chat/completions" method="POST" class="chat-form">
            <textarea name="prompt" placeholder="Type your message..."
                      class="chat-input" rows="2"></textarea>
            <button type="submit" class="send-btn">Send</button>
        </form>
    </main>
    <footer>
        <p>&copy; 2025 IntelliChat Inc.</p>
    </footer>
    <script src="/js/chat-app.bundle.js"></script>
</body>
</html>
"""

DOCS_WITH_ASSISTANT_LINK_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Developer Portal - API Reference</title>
    <link rel="stylesheet" href="/css/docs.css">
</head>
<body>
    <header class="docs-header">
        <a href="/" class="logo">DevPortal</a>
        <nav class="docs-nav">
            <a href="/docs">Guides</a>
            <a href="/api-reference">API Reference</a>
            <a href="/changelog">Changelog</a>
        </nav>
    </header>
    <main class="docs-layout">
        <aside class="sidebar">
            <h3>Quick Links</h3>
            <ul>
                <li><a href="/docs/quickstart">Quickstart</a></li>
                <li><a href="/docs/authentication">Auth</a></li>
                <li><a href="/api/assistant">AI Assistant</a></li>
                <li><a href="/api/conversation">Conversation API</a></li>
            </ul>
        </aside>
        <section class="docs-content">
            <h1>API Reference</h1>
            <p>Our REST API allows you to integrate AI-powered features
               into your applications.</p>
            <h2>Endpoints</h2>
            <pre><code>POST /api/v1/chat/completions
Content-Type: application/json

{
  "model": "gpt-4",
  "messages": [{"role": "user", "content": "Hello"}]
}</code></pre>
        </section>
    </main>
    <script src="/js/docs.js"></script>
</body>
</html>
"""

SAAS_INLINE_CHAT_SCRIPT_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SmartDesk - Customer Support</title>
    <link rel="stylesheet" href="/css/smartdesk.css">
</head>
<body>
    <header class="main-header">
        <a href="/" class="brand">SmartDesk</a>
        <nav>
            <a href="/tickets">Tickets</a>
            <a href="/kb">Knowledge Base</a>
        </nav>
    </header>
    <main class="support-dashboard">
        <h1>Support Dashboard</h1>
        <div class="ticket-list">
            <div class="ticket-card">
                <h3>#1024 — Login issue</h3>
                <span class="status open">Open</span>
            </div>
            <div class="ticket-card">
                <h3>#1023 — Billing question</h3>
                <span class="status closed">Closed</span>
            </div>
        </div>
    </main>
    <script>
        // SmartDesk AI chat configuration
        (function() {
            var config = {
                apiEndpoint: '/api/v2/chat',
                botName: 'SmartDesk Assistant',
                greeting: 'How can I help you?'
            };
            var chatWidget = document.createElement('div');
            chatWidget.id = 'smartdesk-chat';
            document.body.appendChild(chatWidget);
        })();
    </script>
    <script src="/js/dashboard.js"></script>
</body>
</html>
"""

ECOMMERCE_NO_API_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Urban Threads - Premium Clothing</title>
    <link rel="stylesheet" href="/css/shop.css">
</head>
<body>
    <header class="store-header">
        <a href="/" class="store-logo">Urban Threads</a>
        <nav class="store-nav">
            <a href="/men">Men</a>
            <a href="/women">Women</a>
            <a href="/sale">Sale</a>
            <a href="/cart" class="cart-icon">Cart (2)</a>
        </nav>
    </header>
    <main class="product-page">
        <div class="breadcrumb">
            <a href="/">Home</a> / <a href="/men">Men</a> / <span>Jackets</span>
        </div>
        <div class="product-detail">
            <img src="/img/jacket-hero.jpg" alt="Premium Denim Jacket">
            <div class="product-info">
                <h1>Premium Denim Jacket</h1>
                <p class="price">$89.00</p>
                <p class="description">Classic denim jacket crafted from premium
                   Japanese selvedge denim. Features copper rivets and a
                   tailored fit.</p>
                <form action="/cart/add" method="POST">
                    <select name="size">
                        <option>S</option>
                        <option>M</option>
                        <option selected>L</option>
                        <option>XL</option>
                    </select>
                    <button type="submit" class="btn-add-cart">Add to Cart</button>
                </form>
            </div>
        </div>
        <section class="reviews">
            <h2>Customer Reviews</h2>
            <div class="review">
                <strong>Jake M.</strong>
                <p>Great quality jacket, fits true to size.</p>
            </div>
        </section>
    </main>
    <footer class="store-footer">
        <div class="footer-links">
            <a href="/shipping">Shipping</a>
            <a href="/returns">Returns</a>
            <a href="/contact">Contact</a>
        </div>
        <p>&copy; 2025 Urban Threads</p>
    </footer>
    <script src="/js/product-gallery.js"></script>
    <script src="https://cdn.shopify.com/s/files.js"></script>
</body>
</html>
"""


class TestNetworkHintsScriptUrls:
    """Test detection of API patterns in external script URLs."""

    def test_script_url_with_chat_completions_path(self, checker):
        """A script URL containing /api/v1/chat should be detected."""
        page = _page(
            scripts=["https://cdn.example.com/api/v1/chat/widget-loader.js"],
        )
        signals = checker.check(page)

        assert len(signals) >= 1
        api_signals = [s for s in signals if s.metadata.get("source") == "script_url"]
        assert len(api_signals) >= 1

    def test_script_url_with_completion_path(self, checker):
        """A script URL containing /completion should be detected."""
        page = _page(
            scripts=["https://api.saas-platform.com/completion/embed.js"],
        )
        signals = checker.check(page)

        endpoint_signals = [s for s in signals if s.signal_type == "llm_api_endpoint"]
        assert len(endpoint_signals) >= 1

    def test_regular_script_urls_no_detection(self, checker):
        """Common JS library CDN URLs should not trigger detection."""
        page = _page(
            scripts=[
                "https://cdn.jsdelivr.net/npm/vue@3/dist/vue.global.js",
                "https://unpkg.com/react@18/umd/react.production.min.js",
                "https://cdn.tailwindcss.com",
                "https://www.google-analytics.com/analytics.js",
            ],
        )
        signals = checker.check(page)

        assert signals == []


class TestNetworkHintsFormActions:
    """Test detection of API patterns in <form> action attributes."""

    def test_form_action_chat_completions(self, checker):
        """A form with action pointing to /api/v1/chat/completions should be detected."""
        page = _page(html=CHAT_APP_WITH_API_FORM_HTML)
        signals = checker.check(page)

        assert len(signals) >= 1
        # Should find the pattern in form action and/or raw HTML
        patterns_found = {s.metadata.get("matched_pattern") for s in signals}
        assert any("/api/v" in p for p in patterns_found if p)

    def test_regular_form_action_no_detection(self, checker):
        """A standard e-commerce form with /cart/add action should not trigger."""
        page = _page(html=ECOMMERCE_NO_API_HTML)
        signals = checker.check(page)

        assert signals == []


class TestNetworkHintsAnchorHrefs:
    """Test detection of API patterns in <a> href attributes."""

    def test_anchor_href_assistant_endpoint(self, checker):
        """Anchor links to /api/assistant should be detected."""
        page = _page(html=DOCS_WITH_ASSISTANT_LINK_HTML)
        signals = checker.check(page)

        assert len(signals) >= 1
        patterns_found = {s.metadata.get("matched_pattern") for s in signals}
        # Should match at least /api/assistant and /api/conversation
        assert any("assistant" in p for p in patterns_found if p) or \
               any("conversation" in p for p in patterns_found if p)

    def test_regular_navigation_links_no_detection(self, checker):
        """Standard navigation links (e.g., /about, /pricing) should not trigger."""
        html = """\
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Acme Corp</title></head>
<body>
    <nav>
        <a href="/">Home</a>
        <a href="/about">About</a>
        <a href="/pricing">Pricing</a>
        <a href="/blog">Blog</a>
        <a href="/contact">Contact Us</a>
    </nav>
    <main>
        <h1>Welcome to Acme Corp</h1>
        <p>We make great software.</p>
    </main>
</body>
</html>"""
        page = _page(html=html)
        signals = checker.check(page)

        assert signals == []


class TestNetworkHintsInlineScripts:
    """Test detection of API patterns in inline script code."""

    def test_inline_script_with_api_endpoint(self, checker):
        """Inline script referencing /api/v2/chat should be detected."""
        page = _page(html=SAAS_INLINE_CHAT_SCRIPT_HTML)
        signals = checker.check(page)

        assert len(signals) >= 1
        patterns_found = {s.metadata.get("matched_pattern") for s in signals}
        assert any("chat" in p for p in patterns_found if p)

    def test_inline_script_via_page_data_field(self, checker):
        """API patterns passed via the inline_scripts field should be detected."""
        code = """
        async function sendMessage(msg) {
            const response = await fetch('/api/v1/chat/completions', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    model: 'gpt-4',
                    messages: [{ role: 'user', content: msg }]
                })
            });
            return response.json();
        }
        """
        page = _page(inline_scripts=[code])
        signals = checker.check(page)

        assert len(signals) >= 1
        endpoint_signals = [s for s in signals if s.signal_type == "llm_api_endpoint"]
        assert len(endpoint_signals) >= 1

    def test_inline_script_with_generate_endpoint(self, checker):
        """An inline script referencing /generate should be detected."""
        code = """
        const endpoint = '/generate';
        fetch(endpoint, {
            method: 'POST',
            body: JSON.stringify({ prompt: userInput })
        });
        """
        page = _page(inline_scripts=[code])
        signals = checker.check(page)

        endpoint_signals = [s for s in signals if s.signal_type == "llm_api_endpoint"]
        assert len(endpoint_signals) >= 1


class TestNetworkHintsRawHtml:
    """Test detection of API patterns in raw HTML content."""

    def test_hardcoded_api_url_in_html_attribute(self, checker):
        """An API URL hardcoded in a data attribute should be detected."""
        html = """\
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Widget Config</title></head>
<body>
    <div id="chat-widget"
         data-api-url="https://api.platform.io/api/v1/chat/completions"
         data-model="gpt-4o">
    </div>
    <script src="/js/widget.js"></script>
</body>
</html>"""
        page = _page(html=html)
        signals = checker.check(page)

        assert len(signals) >= 1

    def test_api_url_in_code_block(self, checker):
        """API endpoint shown in a documentation code block should be detected."""
        page = _page(html=DOCS_WITH_ASSISTANT_LINK_HTML)
        signals = checker.check(page)

        # The documentation page has /api/v1/chat/completions in a <pre><code> block
        assert len(signals) >= 1


class TestNetworkHintsNoDetection:
    """Test that unrelated pages produce no signals."""

    def test_simple_blog_no_detection(self, checker):
        """A plain blog page should produce no signals."""
        page = _page(html=SIMPLE_BLOG_HTML)
        signals = checker.check(page)

        assert signals == []

    def test_ecommerce_page_no_detection(self, checker):
        """A standard e-commerce page should produce no signals."""
        page = _page(html=ECOMMERCE_NO_API_HTML)
        signals = checker.check(page)

        assert signals == []

    def test_empty_page_no_detection(self, checker):
        """An empty page should produce no signals."""
        page = _page(html="", scripts=[], inline_scripts=[])
        signals = checker.check(page)

        assert signals == []

    def test_generic_api_urls_no_detection(self, checker):
        """Common REST API patterns that are NOT LLM-related should not trigger."""
        html = """\
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>REST API Docs</title></head>
<body>
    <main>
        <h1>User API</h1>
        <pre><code>GET /api/v1/users
POST /api/v1/users
PUT /api/v1/users/:id
DELETE /api/v1/users/:id</code></pre>
        <a href="/api/v1/users">User List</a>
    </main>
</body>
</html>"""
        page = _page(html=html)
        signals = checker.check(page)

        assert signals == []


class TestNetworkHintsDeduplication:
    """Test that duplicate matches do not produce duplicate signals."""

    def test_same_pattern_in_script_and_html_deduped(self, checker):
        """If the same API URL appears in both a script URL and the HTML,
        it should produce only one signal per (pattern, matched_text) pair."""
        api_url = "https://api.example.com/api/v1/chat/send"
        html = f"""\
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Dedup Test</title></head>
<body>
    <div data-endpoint="{api_url}">Chat Widget</div>
    <script src="{api_url}/loader.js"></script>
</body>
</html>"""
        page = _page(html=html, scripts=[f"{api_url}/loader.js"])
        signals = checker.check(page)

        # Count signals for the /chat/send pattern
        chat_send_signals = [
            s for s in signals
            if "chat/send" in s.evidence
        ]
        # The matched text "/chat/send" should appear only once despite
        # appearing in script URL, raw HTML, and potentially anchor
        assert len(chat_send_signals) == 1

    def test_same_pattern_in_inline_and_html_deduped(self, checker):
        """If the same endpoint appears in inline scripts and raw HTML,
        deduplication should collapse them."""
        code = "fetch('/api/chat/completions', { method: 'POST' });"
        html = f"""\
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Dedup Test 2</title></head>
<body>
    <main>Content</main>
    <script>{code}</script>
</body>
</html>"""
        page = _page(html=html, inline_scripts=[code])
        signals = checker.check(page)

        completions_signals = [
            s for s in signals
            if "chat/completions" in s.evidence
        ]
        assert len(completions_signals) == 1


class TestNetworkHintsSignalProperties:
    """Test that returned signals carry correct properties."""

    def test_signal_type_is_llm_api_endpoint(self, checker):
        page = _page(
            scripts=["https://api.example.com/api/v1/chat/widget.js"],
        )
        signals = checker.check(page)

        for sig in signals:
            assert sig.signal_type == "llm_api_endpoint"

    def test_checker_name_is_network_hints(self, checker):
        page = _page(inline_scripts=["fetch('/api/chat/completions')"])
        signals = checker.check(page)

        for sig in signals:
            assert sig.checker_name == "network_hints"

    def test_confidence_uses_network_hint_weight(self, checker):
        page = _page(inline_scripts=["fetch('/completion')"])
        signals = checker.check(page)

        for sig in signals:
            assert sig.confidence.value == SIGNAL_WEIGHT_NETWORK_HINT

    def test_metadata_contains_matched_pattern_and_source(self, checker):
        page = _page(
            scripts=["https://api.example.com/api/v1/chat/loader.js"],
        )
        signals = checker.check(page)

        for sig in signals:
            assert "matched_pattern" in sig.metadata
            assert "source" in sig.metadata
            assert isinstance(sig.metadata["matched_pattern"], str)
            assert sig.metadata["source"] in (
                "script_url", "inline_script", "raw_html",
                "form_action", "anchor_href",
            )

    def test_evidence_contains_matched_text(self, checker):
        page = _page(inline_scripts=["fetch('/api/v1/chat/completions')"])
        signals = checker.check(page)

        for sig in signals:
            assert sig.evidence  # non-empty
            # Evidence is the regex match itself — may be /api/v1/chat,
            # /api/chat/completions, or /completion depending on which pattern hit
            assert isinstance(sig.evidence, str)
            assert len(sig.evidence) > 0


class TestNetworkHintsMultiplePatterns:
    """Test detection when multiple API patterns appear on a single page."""

    def test_multiple_api_endpoints_all_detected(self, checker):
        """A page with several different LLM API patterns should detect all of them."""
        code = """
        const chatEndpoint = '/api/v1/chat/completions';
        const generateEndpoint = '/generate';
        const conversationEndpoint = '/api/conversation';

        async function chat(msg) {
            return fetch(chatEndpoint, { method: 'POST', body: msg });
        }
        async function generate(prompt) {
            return fetch(generateEndpoint, { method: 'POST', body: prompt });
        }
        """
        page = _page(inline_scripts=[code])
        signals = checker.check(page)

        patterns_found = {s.metadata.get("matched_pattern") for s in signals}
        # Should detect at least two distinct patterns
        assert len(patterns_found) >= 2
