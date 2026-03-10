"""Tests for the DomPatternChecker.

The DomPatternChecker scans the DOM for LLM input areas (textareas with
chat-related placeholders, data-testid attributes, etc.) and response
containers (message lists, conversation logs, etc.).
"""

import pytest

from webllm.detection.deterministic.dom_patterns import DomPatternChecker
from webllm.detection.models import PageData

from tests.conftest import (
    CHATBOT_WRAPPER_HTML,
    CONTACT_FORM_HTML,
    DATA_TESTID_PROMPT_HTML,
    INTERCOM_CHAT_HTML,
    SIMPLE_BLOG_HTML,
)


@pytest.fixture
def checker():
    return DomPatternChecker()


def _page(html: str, url: str = "https://example.com") -> PageData:
    return PageData(url=url, html=html)


class TestDomPatternInputDetection:
    """Test detection of LLM input areas in the DOM."""

    def test_intercom_style_chat_textarea(self, checker):
        """An Intercom-style page with a textarea asking the user to type should
        be detected as containing an LLM input."""
        page = _page(INTERCOM_CHAT_HTML)
        signals = checker.check(page)

        input_signals = [s for s in signals if s.signal_type == "llm_input"]
        assert len(input_signals) >= 1

        # The textarea has placeholder="Ask us anything..." which should match
        matched_selectors = {s.metadata.get("matched_selector") for s in input_signals}
        assert any("ask" in sel.lower() or "Ask" in sel for sel in matched_selectors if sel)

    def test_data_testid_prompt_input(self, checker):
        """A page with data-testid='prompt-input' should be detected."""
        page = _page(DATA_TESTID_PROMPT_HTML)
        signals = checker.check(page)

        input_signals = [s for s in signals if s.signal_type == "llm_input"]
        assert len(input_signals) >= 1

        matched_selectors = {s.metadata.get("matched_selector") for s in input_signals}
        assert any("prompt" in sel for sel in matched_selectors if sel)

    def test_ask_me_anything_textarea(self, checker):
        """A standalone textarea with placeholder 'Ask me anything' should match."""
        html = """\
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Support Bot - QuickHelp</title>
    <link rel="stylesheet" href="/css/main.css">
</head>
<body>
    <header class="site-header">
        <nav>
            <a href="/" class="logo">QuickHelp</a>
            <a href="/faq">FAQ</a>
            <a href="/contact">Contact</a>
        </nav>
    </header>
    <main class="support-chat">
        <div class="chat-panel">
            <div class="chat-history">
                <div class="bot-greeting">
                    <p>Welcome! How can I assist you today?</p>
                </div>
            </div>
            <div class="chat-input-area">
                <textarea placeholder="Ask me anything" class="chat-textarea"
                          rows="2"></textarea>
                <button class="send-btn">Send</button>
            </div>
        </div>
    </main>
    <footer>
        <p>&copy; 2025 QuickHelp Inc.</p>
    </footer>
</body>
</html>"""
        page = _page(html)
        signals = checker.check(page)

        input_signals = [s for s in signals if s.signal_type == "llm_input"]
        assert len(input_signals) >= 1

    def test_message_placeholder_textarea(self, checker):
        """A textarea with placeholder containing 'message' should match."""
        html = """\
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Live Chat - RetailStore</title>
</head>
<body>
    <header>
        <h1>RetailStore Live Chat</h1>
    </header>
    <main>
        <div class="chat-container">
            <div class="messages-area">
                <div class="agent-msg">
                    <p>Hello! How may I help you?</p>
                </div>
            </div>
            <div class="input-bar">
                <textarea placeholder="Type your message here..."
                          class="msg-input" rows="2"></textarea>
                <button class="btn-send">Send</button>
            </div>
        </div>
    </main>
    <script src="/js/chat.js"></script>
</body>
</html>"""
        page = _page(html)
        signals = checker.check(page)

        input_signals = [s for s in signals if s.signal_type == "llm_input"]
        assert len(input_signals) >= 1

    def test_chatbot_wrapper_textarea_detected(self, checker):
        """The chatbot-wrapper HTML with 'Ask me anything about our products...'
        placeholder should trigger input detection."""
        page = _page(CHATBOT_WRAPPER_HTML)
        signals = checker.check(page)

        input_signals = [s for s in signals if s.signal_type == "llm_input"]
        assert len(input_signals) >= 1


class TestDomPatternResponseDetection:
    """Test detection of LLM response/conversation areas in the DOM."""

    def test_intercom_chat_message_list(self, checker):
        """Intercom-style page with chat-messages class should be detected as a
        response area."""
        page = _page(INTERCOM_CHAT_HTML)
        signals = checker.check(page)

        response_signals = [s for s in signals if s.signal_type == "llm_response_area"]
        assert len(response_signals) >= 1

    def test_data_testid_message_list(self, checker):
        """A page with data-testid='message-list' should detect a response area."""
        page = _page(DATA_TESTID_PROMPT_HTML)
        signals = checker.check(page)

        response_signals = [s for s in signals if s.signal_type == "llm_response_area"]
        assert len(response_signals) >= 1

    def test_conversation_class_detected(self, checker):
        """A div with a class containing 'conversation' should be detected."""
        html = """\
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>AI Chat - HelpBot</title>
</head>
<body>
    <header><h1>HelpBot</h1></header>
    <main class="app-layout">
        <div class="conversation-container" id="chat-log">
            <div class="message-row assistant">
                <p>Hi! I'm HelpBot. What can I do for you?</p>
            </div>
            <div class="message-row user">
                <p>How do I reset my password?</p>
            </div>
            <div class="message-row assistant">
                <p>Go to Settings > Security > Reset Password.</p>
            </div>
        </div>
        <div class="compose-area">
            <input type="text" placeholder="ask a question..." class="compose-input">
            <button>Send</button>
        </div>
    </main>
    <script src="/js/helpbot.js"></script>
</body>
</html>"""
        page = _page(html)
        signals = checker.check(page)

        response_signals = [s for s in signals if s.signal_type == "llm_response_area"]
        assert len(response_signals) >= 1

    def test_role_log_detected(self, checker):
        """An element with role='log' should be detected as a response area."""
        html = """\
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Chat App</title></head>
<body>
    <header><h1>ChatApp</h1></header>
    <main>
        <div class="chat-view">
            <div role="log" class="transcript">
                <div class="entry bot">Welcome to ChatApp!</div>
            </div>
            <div class="input-row">
                <input type="text" placeholder="chat with us">
                <button>Send</button>
            </div>
        </div>
    </main>
</body>
</html>"""
        page = _page(html)
        signals = checker.check(page)

        response_signals = [s for s in signals if s.signal_type == "llm_response_area"]
        assert len(response_signals) >= 1


class TestDomPatternNoDetection:
    """Test that non-chat pages produce no signals."""

    def test_simple_blog_no_signals(self, checker):
        """A plain blog page with no chat elements should produce no signals."""
        page = _page(SIMPLE_BLOG_HTML)
        signals = checker.check(page)

        assert signals == []

    def test_contact_form_no_input_signals(self, checker):
        """A standard contact form should NOT produce llm_input signals.
        The placeholder 'Tell us about your project...' does not match
        any of the LLM input indicators."""
        page = _page(CONTACT_FORM_HTML)
        signals = checker.check(page)

        input_signals = [s for s in signals if s.signal_type == "llm_input"]
        assert len(input_signals) == 0

    def test_empty_html_no_signals(self, checker):
        """An empty HTML string should produce no signals."""
        page = _page("")
        signals = checker.check(page)

        assert signals == []

    def test_static_marketing_page_no_signals(self, checker):
        """A static marketing page with no interactive chat elements."""
        html = """\
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Acme Solutions - Enterprise Software</title>
    <link rel="stylesheet" href="/css/marketing.css">
</head>
<body>
    <header class="hero-header">
        <nav class="navbar">
            <a href="/" class="brand">Acme Solutions</a>
            <ul>
                <li><a href="/features">Features</a></li>
                <li><a href="/pricing">Pricing</a></li>
                <li><a href="/about">About</a></li>
                <li><a href="/login" class="btn-login">Log In</a></li>
            </ul>
        </nav>
    </header>
    <section class="hero">
        <h1>Transform Your Business with AI-Powered Analytics</h1>
        <p>Get actionable insights from your data in minutes, not months.</p>
        <a href="/signup" class="cta-btn">Start Free Trial</a>
    </section>
    <section class="features-grid">
        <div class="feature-card">
            <h3>Real-time Dashboards</h3>
            <p>Monitor your KPIs as they happen.</p>
        </div>
        <div class="feature-card">
            <h3>Automated Reports</h3>
            <p>Schedule reports delivered to your inbox.</p>
        </div>
    </section>
    <footer>
        <p>&copy; 2025 Acme Solutions Inc.</p>
    </footer>
    <script src="/js/analytics.js"></script>
</body>
</html>"""
        page = _page(html)
        signals = checker.check(page)

        assert signals == []


class TestDomPatternSignalMetadata:
    """Test that signals carry correct metadata."""

    def test_input_signal_has_input_selector_metadata(self, checker):
        page = _page(INTERCOM_CHAT_HTML)
        signals = checker.check(page)

        input_signals = [s for s in signals if s.signal_type == "llm_input"]
        assert len(input_signals) >= 1

        for sig in input_signals:
            assert "input_selector" in sig.metadata
            assert "matched_selector" in sig.metadata

    def test_response_signal_has_response_selector_metadata(self, checker):
        page = _page(INTERCOM_CHAT_HTML)
        signals = checker.check(page)

        response_signals = [s for s in signals if s.signal_type == "llm_response_area"]
        assert len(response_signals) >= 1

        for sig in response_signals:
            assert "response_selector" in sig.metadata
            assert "matched_selector" in sig.metadata

    def test_signal_checker_name_is_dom_patterns(self, checker):
        page = _page(INTERCOM_CHAT_HTML)
        signals = checker.check(page)

        assert len(signals) >= 1
        for sig in signals:
            assert sig.checker_name == "dom_patterns"

    def test_signal_evidence_is_not_empty(self, checker):
        page = _page(INTERCOM_CHAT_HTML)
        signals = checker.check(page)

        for sig in signals:
            assert sig.evidence  # non-empty string
