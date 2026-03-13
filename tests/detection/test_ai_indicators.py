"""Tests for the AiIndicatorChecker — data-driven AI/LLM UI detection.

Test HTML patterns are derived from real pages in our corpus:
- Mintlify docs (sparkle polygon, chat-assistant classes, "Ask a question..." placeholder)
- Vercel docs ("Ask AI" button, aria-label="Ask AI")
- Supabase docs (lucide-sparkles class, "Start with Supabase AI prompts")
- QuillBot (data-testid="ai-chat-input", MUI-based)
- Phind Chat (textarea#phind-input, placeholder="Ask me anything...")
- Stripe docs (StripeAssistantContainer, --assistant-width CSS var)
- Tidio (#tidio-chat container with fixed position)
"""

import pytest

from webagentaudit.detection.deterministic.ai_indicators import AiIndicatorChecker
from webagentaudit.detection.models import PageData


def make_page(html: str, url: str = "https://example.com") -> PageData:
    return PageData(url=url, html=html, scripts=[], inline_scripts=[])


class TestSparkleIconDetection:
    def test_detects_lucide_sparkles_class(self):
        """Real pattern: Supabase docs uses lucide-sparkles on AI prompt link."""
        html = """<!DOCTYPE html><html><body>
        <a class="group w-fit rounded-full border px-3 py-1">
            <svg class="lucide lucide-sparkles" viewBox="0 0 24 24">
                <path d="M11.017 2.814a1 1 0 0 1 1.966 0l1.051 5.558"/>
            </svg>
            Start with Supabase AI prompts
        </a>
        </body></html>"""
        checker = AiIndicatorChecker()
        signals = checker.check(make_page(html))
        assert any(s.signal_type == "ai_sparkle_icon" for s in signals)

    def test_detects_heroicon_sparkles(self):
        html = """<!DOCTYPE html><html><body>
        <button>
            <svg class="heroicon-sparkles" viewBox="0 0 24 24">
                <path d="M9.813 15.904"/>
            </svg>
        </button>
        </body></html>"""
        checker = AiIndicatorChecker()
        signals = checker.check(make_page(html))
        assert any(s.signal_type == "ai_sparkle_icon" for s in signals)

    def test_detects_polygon_sparkle_in_button(self):
        """Real pattern: Mintlify uses polygon SVG for sparkle icon."""
        html = """<!DOCTYPE html><html><body>
        <button aria-label="Toggle assistant panel">
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 18 18">
                <g fill="currentColor">
                    <path d="M5.658,2.99l-1.263-.421"/>
                    <polygon points="9.5 2.75 11.412 7.587 16.25 9.5 11.412 11.413 9.5 16.25 7.587 11.413 2.75 9.5 7.587 7.587 9.5 2.75"/>
                </g>
            </svg>
        </button>
        </body></html>"""
        checker = AiIndicatorChecker()
        signals = checker.check(make_page(html))
        assert any(s.signal_type == "ai_sparkle_icon" for s in signals)

    def test_no_sparkle_on_plain_page(self):
        html = """<!DOCTYPE html><html><body>
        <h1>Hello World</h1>
        <svg viewBox="0 0 24 24"><path d="M0 0h24v24H0z"/></svg>
        </body></html>"""
        checker = AiIndicatorChecker()
        signals = checker.check(make_page(html))
        assert not any(s.signal_type == "ai_sparkle_icon" for s in signals)

    def test_polygon_in_non_interactive_element_ignored(self):
        """Polygon SVGs in non-interactive parents shouldn't trigger."""
        html = """<!DOCTYPE html><html><body>
        <svg viewBox="0 0 18 18">
            <polygon points="9 1 11 7 17 9 11 11 9 17 7 11 1 9 7 7 9 1"/>
        </svg>
        </body></html>"""
        checker = AiIndicatorChecker()
        signals = checker.check(make_page(html))
        # SVG is a direct child of body, not in a button/link
        sparkle_signals = [s for s in signals if s.signal_type == "ai_sparkle_icon"]
        assert len(sparkle_signals) == 0


class TestAiButtonDetection:
    def test_detects_ask_ai_button(self):
        """Real pattern: Vercel docs has 'Ask AI' button."""
        html = """<!DOCTYPE html><html><body>
        <header>
            <button class="outline-none" aria-label="Ask AI">
                <span class="truncate inline-block px-1.5">Ask AI</span>
            </button>
        </header>
        </body></html>"""
        checker = AiIndicatorChecker()
        signals = checker.check(make_page(html))
        assert any(s.signal_type == "ai_button" for s in signals)

    def test_detects_ask_ai_about_page_link(self):
        """Real pattern: Vercel docs bottom link."""
        html = """<!DOCTYPE html><html><body>
        <button class="text-gray-900">
            <span>Ask AI about this page</span>
        </button>
        </body></html>"""
        checker = AiIndicatorChecker()
        signals = checker.check(make_page(html))
        assert any(s.signal_type == "ai_button" for s in signals)

    def test_detects_ai_chat_link(self):
        """Real pattern: QuillBot nav link 'AI Chat'."""
        html = """<!DOCTYPE html><html><body>
        <a href="/ai-chat">AI Chat</a>
        </body></html>"""
        checker = AiIndicatorChecker()
        signals = checker.check(make_page(html))
        assert any(s.signal_type == "ai_button" for s in signals)

    def test_no_false_positive_on_regular_buttons(self):
        html = """<!DOCTYPE html><html><body>
        <button>Submit</button>
        <a href="/about">About Us</a>
        <button>Contact Sales</button>
        </body></html>"""
        checker = AiIndicatorChecker()
        signals = checker.check(make_page(html))
        assert not any(s.signal_type == "ai_button" for s in signals)

    def test_article_mentioning_ai_not_detected_as_button(self):
        """Wikipedia-style article text shouldn't trigger AI button detection."""
        html = """<!DOCTYPE html><html><body>
        <article>
            <p>AI chatbots have revolutionized customer service.</p>
            <p>The best AI chatbot platforms include many options.</p>
        </article>
        </body></html>"""
        checker = AiIndicatorChecker()
        signals = checker.check(make_page(html))
        assert not any(s.signal_type == "ai_button" for s in signals)


class TestAiAriaLabelDetection:
    def test_detects_ask_ai_aria_label(self):
        """Real pattern: Vercel docs button."""
        html = """<!DOCTYPE html><html><body>
        <button aria-label="Ask AI" class="some-class">
            <svg viewBox="0 0 16 16"><path d="M0 0"/></svg>
        </button>
        </body></html>"""
        checker = AiIndicatorChecker()
        signals = checker.check(make_page(html))
        assert any(s.signal_type == "ai_aria_label" for s in signals)

    def test_detects_toggle_assistant_aria_label(self):
        """Real pattern: Mintlify docs button."""
        html = """<!DOCTYPE html><html><body>
        <button aria-label="Toggle assistant panel" class="group/ai">
            <svg viewBox="0 0 18 18"><path d="M5.658"/></svg>
        </button>
        </body></html>"""
        checker = AiIndicatorChecker()
        signals = checker.check(make_page(html))
        assert any(s.signal_type == "ai_aria_label" for s in signals)

    def test_no_false_positive_on_close_chat(self):
        html = """<!DOCTYPE html><html><body>
        <button aria-label="Close chat">X</button>
        </body></html>"""
        checker = AiIndicatorChecker()
        signals = checker.check(make_page(html))
        assert not any(s.signal_type == "ai_aria_label" for s in signals)


class TestAiCssClassDetection:
    def test_detects_chat_assistant_class(self):
        """Real pattern: Mintlify uses chat-assistant-* classes."""
        html = """<!DOCTYPE html><html><body>
        <div class="chat-assistant-floating-input w-full">
            <textarea class="chat-assistant-input" placeholder="Ask a question..."></textarea>
            <button class="chat-assistant-send-button" aria-label="Send message"></button>
        </div>
        </body></html>"""
        checker = AiIndicatorChecker()
        signals = checker.check(make_page(html))
        assert any(s.signal_type == "ai_class" for s in signals)

    def test_detects_stripe_assistant_class(self):
        """Real pattern: Stripe docs uses StripeAssistantContainer."""
        html = """<!DOCTYPE html><html><body>
        <div class="StripeAssistantContainer">
            <div class="Shell">
                <div class="Header">Stripe Docs</div>
            </div>
        </div>
        </body></html>"""
        checker = AiIndicatorChecker()
        signals = checker.check(make_page(html))
        assert any(s.signal_type == "ai_class" for s in signals)

    def test_no_false_positive_on_ai_center_class(self):
        """Real negative: StackOverflow's ai-center is align-items:center, not AI."""
        html = """<!DOCTYPE html><html><body>
        <div class="d-flex ai-center">
            <span>Some text</span>
        </div>
        </body></html>"""
        checker = AiIndicatorChecker()
        signals = checker.check(make_page(html))
        assert not any(s.signal_type == "ai_class" for s in signals)


class TestAiCssVariableDetection:
    def test_detects_assistant_width_variable(self):
        """Real pattern: Stripe docs has --assistant-width: 0px."""
        html = """<!DOCTYPE html><html style="--assistant-width: 0px!important"><body>
        <div class="Shell">Content</div>
        </body></html>"""
        checker = AiIndicatorChecker()
        signals = checker.check(make_page(html))
        assert any(s.signal_type == "ai_css_variable" for s in signals)

    def test_detects_assistant_sheet_width_variable(self):
        """Real pattern: Mintlify has --assistant-sheet-width."""
        html = """<!DOCTYPE html><html style="--assistant-sheet-width: 0px"><body>
        <div>Content</div>
        </body></html>"""
        checker = AiIndicatorChecker()
        signals = checker.check(make_page(html))
        assert any(s.signal_type == "ai_css_variable" for s in signals)


class TestAiPlaceholderDetection:
    def test_detects_ask_me_anything_placeholder(self):
        """Real pattern: QuillBot and Phind use 'Ask me anything'."""
        html = """<!DOCTYPE html><html><body>
        <textarea placeholder="Ask me anything" data-testid="ai-chat-input"></textarea>
        </body></html>"""
        checker = AiIndicatorChecker()
        signals = checker.check(make_page(html))
        assert any(s.signal_type == "ai_placeholder" for s in signals)

    def test_detects_ask_a_question_placeholder(self):
        """Real pattern: Mintlify uses 'Ask a question...'."""
        html = """<!DOCTYPE html><html><body>
        <textarea class="chat-assistant-input" placeholder="Ask a question..."></textarea>
        </body></html>"""
        checker = AiIndicatorChecker()
        signals = checker.check(make_page(html))
        assert any(s.signal_type == "ai_placeholder" for s in signals)

    def test_contenteditable_with_ask_placeholder(self):
        """Real pattern: Andi Search uses contenteditable with placeholder."""
        html = """<!DOCTYPE html><html><body>
        <div contenteditable="true" class="rcw-input" role="textbox"
             placeholder="Ask Andi..." spellcheck="true"></div>
        </body></html>"""
        checker = AiIndicatorChecker()
        signals = checker.check(make_page(html))
        assert any(s.signal_type == "ai_placeholder" for s in signals)

    def test_no_false_positive_on_search_input(self):
        """Real negative: Wikipedia search input with 'Search Wikipedia'."""
        html = """<!DOCTYPE html><html><body>
        <input type="search" placeholder="Search Wikipedia" aria-label="Search Wikipedia">
        </body></html>"""
        checker = AiIndicatorChecker()
        signals = checker.check(make_page(html))
        assert not any(s.signal_type == "ai_placeholder" for s in signals)

    def test_no_false_positive_on_contact_form(self):
        """Contact form textarea with 'Tell us about...' shouldn't trigger."""
        html = """<!DOCTYPE html><html><body>
        <textarea placeholder="Tell us about your project..."></textarea>
        </body></html>"""
        checker = AiIndicatorChecker()
        signals = checker.check(make_page(html))
        assert not any(s.signal_type == "ai_placeholder" for s in signals)


class TestAiDisclaimerDetection:
    def test_detects_generated_using_ai_text(self):
        """Real pattern: Mintlify disclaimer."""
        html = """<!DOCTYPE html><html><body>
        <div class="chat-assistant-disclaimer">
            Responses are generated using AI and may contain mistakes.
        </div>
        </body></html>"""
        checker = AiIndicatorChecker()
        signals = checker.check(make_page(html))
        assert any(s.signal_type == "ai_disclaimer" for s in signals)

    def test_no_false_positive_on_article_text(self):
        html = """<!DOCTYPE html><html><body>
        <article>
            <p>This article discusses how neural networks work.</p>
        </article>
        </body></html>"""
        checker = AiIndicatorChecker()
        signals = checker.check(make_page(html))
        assert not any(s.signal_type == "ai_disclaimer" for s in signals)


class TestChatContainerDetection:
    def test_detects_tidio_chat_container(self):
        """Real pattern: Tidio uses #tidio-chat."""
        html = """<!DOCTYPE html><html><body>
        <div id="tidio-chat" style="z-index: 999999999 !important; position: fixed;">
            <iframe id="tidio-chat-code" title="Tidio Chat code"></iframe>
        </div>
        </body></html>"""
        checker = AiIndicatorChecker()
        signals = checker.check(make_page(html))
        assert any(s.signal_type == "chat_container" for s in signals)

    def test_detects_intercom_container(self):
        html = """<!DOCTYPE html><html><body>
        <div id="intercom-container">
            <div class="intercom-launcher-frame"></div>
        </div>
        </body></html>"""
        checker = AiIndicatorChecker()
        signals = checker.check(make_page(html))
        assert any(s.signal_type == "chat_container" for s in signals)

    def test_detects_chat_iframe_by_title(self):
        """Real pattern: Drift uses iframe with title containing 'chat'."""
        html = """<!DOCTYPE html><html><body>
        <iframe title="Drift Widget Chat" src="about:blank"></iframe>
        </body></html>"""
        checker = AiIndicatorChecker()
        signals = checker.check(make_page(html))
        assert any(s.signal_type == "chat_container" for s in signals)


class TestDataTestidDetection:
    def test_detects_ai_chat_testid(self):
        """Real pattern: QuillBot uses data-testid='ai-chat-input'."""
        html = """<!DOCTYPE html><html><body>
        <textarea data-testid="ai-chat-input" placeholder="Ask me anything"></textarea>
        </body></html>"""
        checker = AiIndicatorChecker()
        signals = checker.check(make_page(html))
        assert any(s.signal_type == "ai_data_testid" for s in signals)

    def test_detects_send_button_testid(self):
        html = """<!DOCTYPE html><html><body>
        <button data-testid="send-button">
            <svg viewBox="0 0 24 24"><path d="M2 21l21-9L2 3"/></svg>
        </button>
        </body></html>"""
        checker = AiIndicatorChecker()
        signals = checker.check(make_page(html))
        assert any(s.signal_type == "ai_data_testid" for s in signals)


class TestMaterialIconDetection:
    def test_detects_auto_awesome_ligature(self):
        html = """<!DOCTYPE html><html><body>
        <button>
            <span class="material-icons">auto_awesome</span>
            Generate
        </button>
        </body></html>"""
        checker = AiIndicatorChecker()
        signals = checker.check(make_page(html))
        assert any(s.signal_type == "ai_material_icon" for s in signals)

    def test_detects_smart_toy_ligature(self):
        html = """<!DOCTYPE html><html><body>
        <span class="material-symbols-outlined">smart_toy</span>
        </body></html>"""
        checker = AiIndicatorChecker()
        signals = checker.check(make_page(html))
        assert any(s.signal_type == "ai_material_icon" for s in signals)


class TestNegativeExamples:
    def test_plain_blog_no_signals(self):
        html = """<!DOCTYPE html><html><body>
        <h1>My Blog</h1>
        <p>This is a regular blog post about technology.</p>
        <footer>&copy; 2025</footer>
        </body></html>"""
        checker = AiIndicatorChecker()
        signals = checker.check(make_page(html))
        assert len(signals) == 0

    def test_ecommerce_no_signals(self):
        html = """<!DOCTYPE html><html><body>
        <h1>Featured Products</h1>
        <div class="product-card">
            <h3>Widget Pro</h3>
            <p class="price">$29.99</p>
            <button>Add to Cart</button>
        </div>
        </body></html>"""
        checker = AiIndicatorChecker()
        signals = checker.check(make_page(html))
        assert len(signals) == 0

    def test_regular_search_not_detected(self):
        html = """<!DOCTYPE html><html><body>
        <form>
            <input type="search" placeholder="Search..." aria-label="Search">
            <button type="submit">Search</button>
        </form>
        </body></html>"""
        checker = AiIndicatorChecker()
        signals = checker.check(make_page(html))
        assert len(signals) == 0

    def test_stackoverflow_ai_center_not_detected(self):
        """StackOverflow's ai-center utility class is not AI."""
        html = """<!DOCTYPE html><html><body>
        <div class="d-flex ai-center jc-space-between">
            <span class="fs-body3">Questions</span>
            <a href="/questions/ask" class="s-btn">Ask Question</a>
        </div>
        <div class="d-flex ai-center">
            <input type="text" name="q" placeholder="Search..." class="s-input">
        </div>
        </body></html>"""
        checker = AiIndicatorChecker()
        signals = checker.check(make_page(html))
        assert len(signals) == 0


class TestMultipleSignals:
    def test_mintlify_like_page_multiple_signals(self):
        """Mintlify-like page should trigger multiple signal types."""
        html = """<!DOCTYPE html>
        <html style="--assistant-sheet-width: 0px">
        <body>
        <button aria-label="Toggle assistant panel" class="group/ai">
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18">
                <polygon points="9.5 2.75 11.412 7.587 16.25 9.5 11.412 11.413 9.5 16.25 7.587 11.413 2.75 9.5 7.587 7.587 9.5 2.75"/>
            </svg>
        </button>
        <div class="chat-assistant-floating-input">
            <textarea class="chat-assistant-input" placeholder="Ask a question..."></textarea>
            <button class="chat-assistant-send-button" aria-label="Send message"></button>
        </div>
        <div class="chat-assistant-disclaimer">
            Responses are generated using AI and may contain mistakes.
        </div>
        </body></html>"""
        checker = AiIndicatorChecker()
        signals = checker.check(make_page(html))
        signal_types = {s.signal_type for s in signals}
        # Should detect multiple independent signal types
        assert len(signal_types) >= 3
        assert "ai_sparkle_icon" in signal_types or "ai_aria_label" in signal_types
        assert "ai_class" in signal_types
        assert "ai_placeholder" in signal_types

    def test_empty_html_no_crash(self):
        checker = AiIndicatorChecker()
        signals = checker.check(make_page(""))
        assert signals == []

    def test_checker_name(self):
        checker = AiIndicatorChecker()
        assert checker.name == "ai_indicators"
