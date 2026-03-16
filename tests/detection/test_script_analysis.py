"""Tests for the ScriptAnalysisChecker.

The ScriptAnalysisChecker scans inline scripts, script URLs, and embedded
<script> tags for patterns suggesting LLM SDK usage, WebSocket chat
connections, streaming response handling, and chat/completion API calls.
"""

import pytest

from webagentaudit.detection.consts import SIGNAL_WEIGHT_SCRIPT_ANALYSIS
from webagentaudit.detection.deterministic.script_analysis import ScriptAnalysisChecker
from webagentaudit.detection.models import PageData

from tests.conftest import SIMPLE_BLOG_HTML

pytestmark = pytest.mark.unit


@pytest.fixture
def checker():
    return ScriptAnalysisChecker()


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
# Realistic HTML fixtures with embedded scripts
# ---------------------------------------------------------------------------

OPENAI_SDK_PAGE_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DocuSearch - AI-Powered Documentation</title>
    <link rel="stylesheet" href="/css/docs.css">
</head>
<body>
    <header class="docs-header">
        <a href="/" class="brand">DocuSearch</a>
        <nav>
            <a href="/guides">Guides</a>
            <a href="/api-ref">API Reference</a>
        </nav>
    </header>
    <main class="docs-content">
        <h1>Search our documentation</h1>
        <div class="search-container">
            <input type="text" placeholder="What are you looking for?"
                   class="doc-search-input" id="doc-search">
            <div id="search-results" class="results-panel"></div>
        </div>
    </main>
    <script>
        import OpenAI from 'openai';

        const client = new OpenAI({
            apiKey: window.__OPENAI_KEY__,
            dangerouslyAllowBrowser: true,
        });

        async function searchDocs(query) {
            const chatCompletion = await client.chat.completions.create({
                model: 'gpt-4o-mini',
                messages: [
                    { role: 'system', content: 'You are a documentation assistant.' },
                    { role: 'user', content: query },
                ],
            });
            return chatCompletion.choices[0].message.content;
        }
    </script>
    <script src="/js/docs-ui.js"></script>
</body>
</html>
"""

ANTHROPIC_SDK_PAGE_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Claude Chat - Demo App</title>
    <link rel="stylesheet" href="/css/chat.css">
</head>
<body>
    <header class="app-bar">
        <h1 class="app-title">Claude Chat Demo</h1>
    </header>
    <main class="chat-layout">
        <div id="messages" class="message-feed"></div>
        <div class="compose-bar">
            <textarea id="user-input" placeholder="Type a message..."
                      rows="2"></textarea>
            <button id="send-btn" class="btn-send">Send</button>
        </div>
    </main>
    <script>
        import Anthropic from 'anthropic';

        const anthropic = new Anthropic({
            apiKey: window.__ANTHROPIC_KEY__,
        });

        async function sendMessage(text) {
            const message = await anthropic.messages.create({
                model: 'claude-sonnet-4-20250514',
                max_tokens: 1024,
                messages: [{ role: 'user', content: text }],
            });
            const outputEl = document.getElementById('messages');
            const div = document.createElement('div');
            div.className = 'msg assistant';
            div.textContent = message.content[0].text;
            outputEl.appendChild(div);
        }
    </script>
</body>
</html>
"""

LANGCHAIN_CHATBOT_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Support Bot - Powered by LangChain</title>
    <link rel="stylesheet" href="/css/support.css">
</head>
<body>
    <header class="site-header">
        <a href="/" class="brand">SupportHub</a>
        <nav>
            <a href="/faq">FAQ</a>
            <a href="/tickets">Tickets</a>
        </nav>
    </header>
    <main class="support-main">
        <h1>Ask our AI Support Agent</h1>
        <div class="chat-window">
            <div id="chat-log" class="chat-log"></div>
            <div class="input-area">
                <textarea placeholder="Describe your issue..."
                          id="support-input" rows="2"></textarea>
                <button id="ask-btn">Ask</button>
            </div>
        </div>
    </main>
    <script>
        import { ChatOpenAI } from 'langchain/chat_models/openai';
        import { HumanMessage } from 'langchain/schema';

        const chatbot = new ChatOpenAI({
            openAIApiKey: window.__LLM_KEY__,
            modelName: 'gpt-4',
            temperature: 0.3,
        });

        async function askAgent(question) {
            const response = await chatbot.call([
                new HumanMessage(question),
            ]);
            return response.content;
        }
    </script>
</body>
</html>
"""

WEBSOCKET_CHAT_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LiveChat - Real-time AI Assistant</title>
    <link rel="stylesheet" href="/css/livechat.css">
</head>
<body>
    <header class="chat-header">
        <span class="chat-title">LiveChat AI</span>
        <button class="close-btn">Close</button>
    </header>
    <main class="chat-body">
        <div id="messages" class="message-list"></div>
        <div class="input-row">
            <input type="text" id="msg-input" placeholder="Type here..."
                   class="chat-input">
            <button id="send" class="send-btn">Send</button>
        </div>
    </main>
    <script>
        const ws = new WebSocket('wss://api.livechat.io/ws/chat/v2');
        ws.onopen = function() {
            ws.send(JSON.stringify({ type: 'init', session: sessionId }));
        };
        ws.onmessage = function(event) {
            const data = JSON.parse(event.data);
            if (data.type === 'assistant_message') {
                appendMessage(data.content, 'assistant');
            }
        };

        function sendMessage(text) {
            ws.send(JSON.stringify({ type: 'user_message', content: text }));
        }
    </script>
</body>
</html>
"""

STREAMING_SSE_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>StreamChat - AI with Streaming Responses</title>
    <link rel="stylesheet" href="/css/streamchat.css">
</head>
<body>
    <header>
        <h1>StreamChat</h1>
    </header>
    <main class="chat-interface">
        <div id="response-area" class="response-container"></div>
        <div class="prompt-bar">
            <textarea id="prompt" placeholder="Ask anything..."
                      rows="2"></textarea>
            <button id="send">Generate</button>
        </div>
    </main>
    <script>
        async function streamResponse(prompt) {
            const response = await fetch('/api/v1/chat/completions', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'text/event-stream',
                },
                body: JSON.stringify({
                    model: 'gpt-4',
                    messages: [{ role: 'user', content: prompt }],
                    stream: true,
                }),
            });

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let done = false;

            while (!done) {
                const { value, done: readerDone } = await reader.read();
                done = readerDone;
                const chunk = decoder.decode(value, { stream: true });
                if (chunk.includes('data: [DONE]')) break;
                appendToResponse(chunk);
            }
        }
    </script>
</body>
</html>
"""

READABLE_STREAM_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FlowAI - Streaming Demo</title>
    <link rel="stylesheet" href="/css/flow.css">
</head>
<body>
    <header><h1>FlowAI</h1></header>
    <main>
        <div id="output" class="output-area"></div>
        <div class="controls">
            <input type="text" id="query" placeholder="Enter prompt">
            <button id="go">Go</button>
        </div>
    </main>
    <script>
        async function generate(query) {
            const resp = await fetch('/api/generate', {
                method: 'POST',
                body: JSON.stringify({ prompt: query }),
            });

            const stream = new ReadableStream({
                start(controller) {
                    const reader = resp.body.getReader();
                    function push() {
                        reader.read().then(function(result) {
                            if (result.done) { controller.close(); return; }
                            controller.enqueue(result.value);
                            push();
                        });
                    }
                    push();
                }
            });
            return stream;
        }
    </script>
</body>
</html>
"""

EVENTSOURCE_CHAT_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EventChat - Server-Sent Events Demo</title>
    <link rel="stylesheet" href="/css/eventchat.css">
</head>
<body>
    <header><h1>EventChat</h1></header>
    <main>
        <div id="chat-output" class="chat-window"></div>
        <div class="compose">
            <textarea id="input" placeholder="Your message..."
                      rows="2"></textarea>
            <button id="submit">Send</button>
        </div>
    </main>
    <script>
        function startStream(prompt) {
            var url = '/api/chat/stream?prompt=' + encodeURIComponent(prompt);
            var source = new EventSource(url);
            source.onmessage = function(event) {
                var data = JSON.parse(event.data);
                appendToken(data.token);
            };
            source.onerror = function() {
                source.close();
            };
        }
    </script>
</body>
</html>
"""

PLAIN_MARKETING_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NovaTech - Cloud Infrastructure</title>
    <link rel="stylesheet" href="/css/marketing.css">
    <link rel="preconnect" href="https://fonts.googleapis.com">
</head>
<body>
    <header class="hero-nav">
        <a href="/" class="brand-logo">NovaTech</a>
        <nav>
            <a href="/platform">Platform</a>
            <a href="/solutions">Solutions</a>
            <a href="/pricing">Pricing</a>
            <a href="/docs">Docs</a>
            <a href="/login" class="btn-outline">Log In</a>
        </nav>
    </header>
    <section class="hero-section">
        <h1>Deploy at Scale. Effortlessly.</h1>
        <p>NovaTech's cloud platform handles millions of requests with
           zero config. Focus on building, not infrastructure.</p>
        <a href="/signup" class="cta-primary">Start Free</a>
    </section>
    <section class="features">
        <div class="feature-card">
            <h3>Auto-Scaling</h3>
            <p>Scale from zero to millions without touching a config file.</p>
        </div>
        <div class="feature-card">
            <h3>Edge Network</h3>
            <p>200+ PoPs worldwide for sub-50ms latency everywhere.</p>
        </div>
        <div class="feature-card">
            <h3>CI/CD Built In</h3>
            <p>Push to deploy. Rollback in one click.</p>
        </div>
    </section>
    <footer>
        <p>Copyright 2025 NovaTech Inc.</p>
    </footer>
    <script src="https://www.googletagmanager.com/gtag/js?id=G-XXXXXX"></script>
    <script>
        window.dataLayer = window.dataLayer || [];
        function gtag(){dataLayer.push(arguments);}
        gtag('js', new Date());
        gtag('config', 'G-XXXXXX');
    </script>
</body>
</html>
"""

JQUERY_GALLERY_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Photo Gallery - Memories</title>
    <link rel="stylesheet" href="/css/gallery.css">
</head>
<body>
    <header>
        <h1>My Photo Gallery</h1>
        <nav>
            <a href="/albums">Albums</a>
            <a href="/favorites">Favorites</a>
        </nav>
    </header>
    <main class="gallery-grid">
        <div class="photo-card">
            <img src="/photos/sunset.jpg" alt="Sunset at the beach">
            <p>Summer 2025</p>
        </div>
        <div class="photo-card">
            <img src="/photos/mountain.jpg" alt="Mountain trail">
            <p>Hiking trip</p>
        </div>
    </main>
    <script src="https://code.jquery.com/jquery-3.7.1.min.js"></script>
    <script>
        $(document).ready(function() {
            $('.photo-card img').on('click', function() {
                var src = $(this).attr('src');
                var lightbox = document.getElementById('lightbox');
                document.getElementById('lightbox-img').setAttribute('src', src);
                $(lightbox).fadeIn(300);
            });
            $('#lightbox').on('click', function() {
                $(this).fadeOut(300);
            });
        });
    </script>
</body>
</html>
"""


class TestScriptAnalysisLlmSdkImports:
    """Test detection of LLM SDK imports and references."""

    def test_openai_sdk_import_detected(self, checker):
        """A page importing the OpenAI SDK should be detected."""
        page = _page(html=OPENAI_SDK_PAGE_HTML)
        signals = checker.check(page)

        assert len(signals) >= 1
        patterns = {s.metadata.get("matched_pattern") for s in signals}
        assert any("openai" in p.lower() for p in patterns if p)

    def test_anthropic_sdk_import_detected(self, checker):
        """A page importing the Anthropic SDK should be detected."""
        page = _page(html=ANTHROPIC_SDK_PAGE_HTML)
        signals = checker.check(page)

        assert len(signals) >= 1
        patterns = {s.metadata.get("matched_pattern") for s in signals}
        assert any("anthropic" in p.lower() for p in patterns if p)

    def test_langchain_import_detected(self, checker):
        """A page using LangChain should be detected."""
        page = _page(html=LANGCHAIN_CHATBOT_HTML)
        signals = checker.check(page)

        assert len(signals) >= 1
        patterns = {s.metadata.get("matched_pattern") for s in signals}
        assert any("langchain" in p.lower() for p in patterns if p)

    def test_google_generative_ai_in_script_url(self, checker):
        """A script URL referencing @google/generative-ai should be detected."""
        page = _page(
            scripts=[
                "https://cdn.example.com/node_modules/@google/generative-ai/dist/index.js",
            ],
        )
        signals = checker.check(page)

        assert len(signals) >= 1

    def test_cohere_sdk_in_inline_script(self, checker):
        """An inline script importing cohere-ai should be detected."""
        code = """
        import { CohereClient } from 'cohere-ai';
        const cohere = new CohereClient({ token: apiKey });
        const response = await cohere.chat({ message: userInput });
        """
        page = _page(inline_scripts=[code])
        signals = checker.check(page)

        assert len(signals) >= 1


class TestScriptAnalysisWebSocket:
    """Test detection of WebSocket connections to chat endpoints."""

    def test_websocket_chat_connection_detected(self, checker):
        """A page opening a WebSocket to a /ws/chat endpoint should be detected."""
        page = _page(html=WEBSOCKET_CHAT_HTML)
        signals = checker.check(page)

        assert len(signals) >= 1
        # Should find WebSocket pattern
        patterns = {s.metadata.get("matched_pattern") for s in signals}
        assert any("WebSocket" in p or "wss?" in p for p in patterns if p)

    def test_websocket_assistant_endpoint_in_inline(self, checker):
        """An inline script with WebSocket to an assistant endpoint should be detected."""
        code = """
        const socket = new WebSocket('wss://backend.myapp.com/ws/assistant');
        socket.onmessage = function(event) {
            var msg = JSON.parse(event.data);
            renderMessage(msg);
        };
        """
        page = _page(inline_scripts=[code])
        signals = checker.check(page)

        assert len(signals) >= 1

    def test_websocket_to_non_chat_endpoint_no_detection(self, checker):
        """A WebSocket to a non-chat endpoint (e.g., stock ticker) should not trigger."""
        code = """
        var ws = new WebSocket('wss://stream.stockdata.com/ws/ticker');
        ws.onmessage = function(e) {
            updatePrice(JSON.parse(e.data));
        };
        """
        page = _page(inline_scripts=[code])
        signals = checker.check(page)

        # The WebSocket pattern requires chat/llm/ai/gpt/assistant keywords
        ws_signals = [
            s for s in signals
            if "WebSocket" in (s.metadata.get("matched_pattern") or "")
            or "wss?" in (s.metadata.get("matched_pattern") or "")
        ]
        assert len(ws_signals) == 0


class TestScriptAnalysisStreaming:
    """Test detection of streaming response patterns."""

    def test_eventsource_detected(self, checker):
        """A page using EventSource for SSE should be detected."""
        page = _page(html=EVENTSOURCE_CHAT_HTML)
        signals = checker.check(page)

        assert len(signals) >= 1
        patterns = {s.metadata.get("matched_pattern") for s in signals}
        assert any("EventSource" in p for p in patterns if p)

    def test_readable_stream_detected(self, checker):
        """A page using ReadableStream for streaming responses should be detected."""
        page = _page(html=READABLE_STREAM_HTML)
        signals = checker.check(page)

        assert len(signals) >= 1
        patterns = {s.metadata.get("matched_pattern") for s in signals}
        assert any("ReadableStream" in p for p in patterns if p)

    def test_getreader_detected(self, checker):
        """A page calling .getReader() for stream processing should be detected."""
        page = _page(html=STREAMING_SSE_HTML)
        signals = checker.check(page)

        patterns = {s.metadata.get("matched_pattern") for s in signals}
        assert any("getReader" in p for p in patterns if p)

    def test_text_event_stream_header_detected(self, checker):
        """A script referencing text/event-stream content type should be detected."""
        page = _page(html=STREAMING_SSE_HTML)
        signals = checker.check(page)

        patterns = {s.metadata.get("matched_pattern") for s in signals}
        assert any("event-stream" in p for p in patterns if p)

    def test_data_done_marker_detected(self, checker):
        """A script checking for 'data: [DONE]' (OpenAI SSE terminator) should be detected."""
        page = _page(html=STREAMING_SSE_HTML)
        signals = checker.check(page)

        patterns = {s.metadata.get("matched_pattern") for s in signals}
        assert any("DONE" in p for p in patterns if p)


class TestScriptAnalysisChatApiCalls:
    """Test detection of chat/completion API calls in scripts."""

    def test_fetch_chat_completions_detected(self, checker):
        """A fetch() call to /chat/completions should be detected."""
        page = _page(html=STREAMING_SSE_HTML)
        signals = checker.check(page)

        assert len(signals) >= 1
        patterns = {s.metadata.get("matched_pattern") for s in signals}
        assert any("chat/completions" in p or "chat" in p for p in patterns if p)

    def test_create_chat_completion_method_detected(self, checker):
        """A .chat.completions.create() call should be detected."""
        page = _page(html=OPENAI_SDK_PAGE_HTML)
        signals = checker.check(page)

        patterns = {s.metadata.get("matched_pattern") for s in signals}
        assert any("completions" in p for p in patterns if p)

    def test_messages_create_method_detected(self, checker):
        """An anthropic .messages.create() call should be detected."""
        page = _page(html=ANTHROPIC_SDK_PAGE_HTML)
        signals = checker.check(page)

        patterns = {s.metadata.get("matched_pattern") for s in signals}
        assert any("messages" in p for p in patterns if p)

    def test_axios_chat_completions_in_inline(self, checker):
        """An axios call to /v1/messages should be detected."""
        code = """
        var response = await axios.post('https://api.anthropic.com/v1/messages', {
            model: 'claude-sonnet-4-20250514',
            max_tokens: 1024,
            messages: [{ role: 'user', content: userPrompt }],
        }, {
            headers: { 'x-api-key': apiKey },
        });
        """
        page = _page(inline_scripts=[code])
        signals = checker.check(page)

        assert len(signals) >= 1


class TestScriptAnalysisVariableNames:
    """Test detection of LLM-related variable/identifier names."""

    def test_chatbot_variable_detected(self, checker):
        """A script with a 'chatbot' variable should be detected."""
        page = _page(html=LANGCHAIN_CHATBOT_HTML)
        signals = checker.check(page)

        patterns = {s.metadata.get("matched_pattern") for s in signals}
        assert any("chatbot" in p.lower() for p in patterns if p)

    def test_ai_assistant_identifier_detected(self, checker):
        """A script with an 'aiAssistant' identifier should be detected."""
        code = """
        var aiAssistant = new AIChatClient({
            endpoint: '/api/chat',
            model: 'custom-model',
        });
        aiAssistant.sendMessage(userInput);
        """
        page = _page(inline_scripts=[code])
        signals = checker.check(page)

        patterns = {s.metadata.get("matched_pattern") for s in signals}
        assert any("aiAssistant" in p for p in patterns if p)

    def test_llm_client_identifier_detected(self, checker):
        """A script with an 'llmClient' identifier should be detected."""
        code = """
        function ChatApp() {
            this.llmClient = new LLMService('/api/v2/chat');
        }
        ChatApp.prototype.ask = function(question) {
            return this.llmClient.complete(question);
        };
        """
        page = _page(inline_scripts=[code])
        signals = checker.check(page)

        patterns = {s.metadata.get("matched_pattern") for s in signals}
        assert any("llmClient" in p for p in patterns if p)


class TestScriptAnalysisNoDetection:
    """Test that non-LLM pages produce no signals."""

    def test_simple_blog_no_signals(self, checker):
        """A plain blog page should produce no signals."""
        page = _page(html=SIMPLE_BLOG_HTML)
        signals = checker.check(page)

        assert signals == []

    def test_marketing_page_no_signals(self, checker):
        """A marketing page with only analytics scripts should produce no signals."""
        page = _page(html=PLAIN_MARKETING_HTML)
        signals = checker.check(page)

        assert signals == []

    def test_jquery_gallery_no_signals(self, checker):
        """A jQuery-powered photo gallery should produce no signals."""
        page = _page(html=JQUERY_GALLERY_HTML)
        signals = checker.check(page)

        assert signals == []

    def test_empty_page_no_signals(self, checker):
        """An empty page should produce no signals."""
        page = _page(html="", scripts=[], inline_scripts=[])
        signals = checker.check(page)

        assert signals == []

    def test_vanilla_js_app_no_signals(self, checker):
        """A vanilla JS app with no LLM patterns should produce no signals."""
        html = """\
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Todo App</title></head>
<body>
    <h1>My Todos</h1>
    <ul id="todo-list"></ul>
    <input type="text" id="new-todo" placeholder="Add a task...">
    <button id="add-btn">Add</button>
    <script>
        var todoList = document.getElementById('todo-list');
        var input = document.getElementById('new-todo');
        document.getElementById('add-btn').addEventListener('click', function() {
            var li = document.createElement('li');
            li.textContent = input.value;
            todoList.appendChild(li);
            input.value = '';
        });
    </script>
</body>
</html>"""
        page = _page(html=html)
        signals = checker.check(page)

        assert signals == []

    def test_regular_websocket_no_detection(self, checker):
        """A WebSocket to a non-LLM endpoint should not trigger."""
        html = """\
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Live Scores</title></head>
<body>
    <h1>Live Scores</h1>
    <div id="scores"></div>
    <script>
        var ws = new WebSocket('wss://scores.sportsapi.com/live');
        ws.onmessage = function(e) {
            var data = JSON.parse(e.data);
            document.getElementById('scores').textContent = renderScores(data);
        };
    </script>
</body>
</html>"""
        page = _page(html=html)
        signals = checker.check(page)

        # Generic WebSocket without chat/llm/ai keywords should not match
        ws_signals = [
            s for s in signals
            if "WebSocket" in (s.metadata.get("matched_pattern") or "")
            or "wss?" in (s.metadata.get("matched_pattern") or "")
        ]
        assert len(ws_signals) == 0


class TestScriptAnalysisSignalProperties:
    """Test that returned signals carry correct properties."""

    def test_signal_type_is_llm_script_pattern(self, checker):
        page = _page(inline_scripts=["import OpenAI from 'openai';"])
        signals = checker.check(page)

        for sig in signals:
            assert sig.signal_type == "llm_script_pattern"

    def test_checker_name_is_script_analysis(self, checker):
        page = _page(inline_scripts=["var anthropic = require('anthropic');"])
        signals = checker.check(page)

        for sig in signals:
            assert sig.checker_name == "script_analysis"

    def test_confidence_uses_script_analysis_weight(self, checker):
        page = _page(inline_scripts=["import { langchain } from 'langchain';"])
        signals = checker.check(page)

        for sig in signals:
            assert sig.confidence.value == SIGNAL_WEIGHT_SCRIPT_ANALYSIS

    def test_metadata_contains_matched_pattern(self, checker):
        page = _page(inline_scripts=["var client = new OpenAI({ apiKey: key });"])
        signals = checker.check(page)

        for sig in signals:
            assert "matched_pattern" in sig.metadata
            assert isinstance(sig.metadata["matched_pattern"], str)

    def test_evidence_is_context_snippet(self, checker):
        """Evidence should be a snippet of the surrounding code, not just the match."""
        code = "var chatCompletion = await client.chat.completions.create({ model: 'gpt-4' });"
        page = _page(inline_scripts=[code])
        signals = checker.check(page)

        for sig in signals:
            assert sig.evidence  # non-empty
            # Evidence should contain more than just the matched keyword
            assert len(sig.evidence) > 5


class TestScriptAnalysisMultiplePatterns:
    """Test detection of multiple LLM patterns on a single page."""

    def test_openai_page_produces_multiple_signals(self, checker):
        """The OpenAI SDK page should detect multiple patterns
        (SDK import, .chat.completions.create, chatCompletion variable)."""
        page = _page(html=OPENAI_SDK_PAGE_HTML)
        signals = checker.check(page)

        patterns = {s.metadata.get("matched_pattern") for s in signals}
        # Should find at least OpenAI reference + .chat.completions.create
        assert len(patterns) >= 2

    def test_streaming_page_produces_multiple_signals(self, checker):
        """The streaming SSE page should detect multiple patterns
        (fetch to chat/completions, getReader, text/event-stream, data: [DONE])."""
        page = _page(html=STREAMING_SSE_HTML)
        signals = checker.check(page)

        patterns = {s.metadata.get("matched_pattern") for s in signals}
        # Should find at least 3 distinct patterns
        assert len(patterns) >= 3

    def test_mixed_sdk_and_api_patterns(self, checker):
        """A page combining SDK import with API fetch should detect both."""
        code = """
        import OpenAI from 'openai';

        // Fallback: direct API call when SDK fails
        async function fallbackChat(msg) {
            var resp = await fetch('/api/v1/chat/completions', {
                method: 'POST',
                body: JSON.stringify({ messages: [{ role: 'user', content: msg }] }),
            });
            var reader = resp.body.getReader();
            // stream the response
        }
        """
        page = _page(inline_scripts=[code])
        signals = checker.check(page)

        patterns = {s.metadata.get("matched_pattern") for s in signals}
        # Should find openai pattern + fetch pattern + getReader
        assert len(patterns) >= 2


class TestScriptAnalysisDeduplication:
    """Test that duplicate matches do not produce duplicate signals."""

    def test_same_pattern_in_inline_scripts_and_html_tag_deduped(self, checker):
        """If the same script appears in both inline_scripts field and
        embedded in HTML <script> tags, it should be deduplicated."""
        code = "var aiAssistant = new AIChatService();"
        html = f"""\
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Dedup Test</title></head>
<body>
    <main>Content</main>
    <script>{code}</script>
</body>
</html>"""
        page = _page(html=html, inline_scripts=[code])
        signals = checker.check(page)

        # The pattern "aiAssistant" matched in the same snippet should appear once
        assistant_signals = [
            s for s in signals
            if "aiAssistant" in (s.metadata.get("matched_pattern") or "")
        ]
        assert len(assistant_signals) == 1
