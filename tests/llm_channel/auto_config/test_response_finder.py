"""Tests for ResponseFinder: interactive response element discovery via DOM diffing."""

from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from webagentaudit.core.exceptions import ChannelResponseError
from webagentaudit.llm_channel.auto_config._response_finder import ResponseFinder
from webagentaudit.llm_channel.auto_config._selector_builder import SelectorBuilder
from webagentaudit.llm_channel.auto_config import consts

pytestmark = pytest.mark.browser

# ---------------------------------------------------------------------------
# HTML fixtures
# ---------------------------------------------------------------------------

ECHO_CHAT_HTML = """\
<!DOCTYPE html>
<html>
<head><title>Echo Chat</title></head>
<body>
<div id="chat" style="position: relative;">
    <div id="messages">
        <div class="message bot-response">Welcome! How can I help?</div>
    </div>
    <textarea id="input" placeholder="Type a message"
              style="width: 400px; height: 40px;"></textarea>
    <button id="send" style="width: 60px; height: 30px;">Send</button>
</div>
<script>
document.getElementById('send').addEventListener('click', function() {
    var input = document.getElementById('input');
    var text = input.value;
    input.value = '';
    setTimeout(function() {
        var div = document.createElement('div');
        div.className = 'message bot-response';
        div.textContent = 'Bot: ' + text;
        document.getElementById('messages').appendChild(div);
    }, 300);
});
</script>
</body>
</html>
"""

NO_RESPONSE_HTML = """\
<!DOCTYPE html>
<html>
<head><title>No Response</title></head>
<body>
<div id="chat">
    <textarea id="input" placeholder="Type a message"
              style="width: 400px; height: 40px;"></textarea>
    <button id="send" style="width: 60px; height: 30px;">Send</button>
</div>
<script>
document.getElementById('send').addEventListener('click', function() {
    // Does nothing - no response is generated
    var input = document.getElementById('input');
    input.value = '';
});
</script>
</body>
</html>
"""

NURBANK_CHAT_HTML = """\
<!DOCTYPE html>
<html><body>
<div class="description"><p>All rights reserved.</p></div>
<section class="nurbank-chat-agent__panel">
  <div class="nurbank-chat-agent__messages">
    <div class="nurbank-chat-agent__row">
      <div class="nurbank-chat-agent__bubble nurbank-chat-agent__bubble--assistant">
        Welcome to Nurbank AI.
      </div>
    </div>
  </div>
  <textarea class="nurbank-chat-agent__input"></textarea>
  <button class="nurbank-chat-agent__send">Send</button>
</section>
<script>
document.querySelector('.nurbank-chat-agent__send').addEventListener('click', () => {
    const messages = document.querySelector('.nurbank-chat-agent__messages');
    const customer = document.createElement('div');
    customer.className = 'nurbank-chat-agent__row nurbank-chat-agent__row--customer';
    customer.textContent = document.querySelector('.nurbank-chat-agent__input').value;
    messages.appendChild(customer);
    setTimeout(() => {
        const row = document.createElement('div');
        row.className = 'nurbank-chat-agent__row';
        const reply = document.createElement('div');
        reply.className = 'nurbank-chat-agent__bubble nurbank-chat-agent__bubble--assistant';
        reply.textContent = 'I can only help with Nurbank banking products.';
        row.appendChild(reply);
        messages.appendChild(row);
    }, 300);
});
</script>
</body></html>
"""

NESTED_ASSISTANT_CHAT_HTML = """\
<!DOCTYPE html><html><body>
<main class="grid app-shell"><div class="messages"><div class="assistant-response">Welcome</div></div></main>
<textarea id="input"></textarea><button id="send">Send</button>
<script>
send.addEventListener('click', () => {
  const customer = document.createElement('div');
  customer.className = 'customer-message'; customer.textContent = input.value;
  document.querySelector('.messages').append(customer);
  setTimeout(() => {
    const reply = document.createElement('div');
    reply.className = 'assistant-response'; reply.textContent = 'yes';
    document.querySelector('.messages').append(reply);
  }, 300);
});
</script></body></html>
"""

CLASSLESS_REPLY_CHAT_HTML = """\
<!DOCTYPE html><html><body>
<div id="messages"><div>Welcome</div></div>
<textarea id="input"></textarea><button id="send">Send</button>
<script>
send.addEventListener('click', () => {
  const customer = document.createElement('div'); customer.textContent = input.value;
  messages.append(customer);
  setTimeout(() => { const reply = document.createElement('span'); reply.textContent = 'yes'; messages.append(reply); }, 300);
});
</script></body></html>
"""

TIMESTAMPED_REPLY_CHAT_HTML = """\
<!DOCTYPE html><html><body>
<div id="messages"><div>Welcome</div></div>
<textarea id="input"></textarea><button id="send">Send</button>
<script>
send.addEventListener('click', () => {
  const customer = document.createElement('div'); customer.textContent = input.value;
  messages.append(customer);
  const time = document.createElement('span'); time.textContent = '11:44 PM'; messages.append(time);
  setTimeout(() => { const reply = document.createElement('span'); reply.textContent = 'yes'; messages.append(reply); }, 300);
});
</script></body></html>
"""

REPLY_WITH_ACTION_HTML = """\
<!DOCTYPE html><html><body>
<div id="messages"><div>Welcome</div></div>
<textarea id="input"></textarea><button id="send">Send</button>
<script>
send.addEventListener('click', () => {
  const customer = document.createElement('div'); customer.textContent = input.value;
  messages.append(customer);
  setTimeout(() => {
    const reply = document.createElement('div');
    const text = document.createElement('span'); text.textContent = 'yes';
    const copy = document.createElement('button'); copy.textContent = 'Copy';
    reply.append(text, copy); messages.append(reply);
  }, 300);
});
</script></body></html>
"""

MARKDOWN_REPLY_CHAT_HTML = """\
<!DOCTYPE html><html><body>
<div class="messages"><div class="assistant-response">Welcome</div></div>
<textarea id="input"></textarea><button id="send">Send</button>
<script>
send.addEventListener('click', () => {
  const customer = document.createElement('div');
  customer.className = 'customer-message'; customer.textContent = input.value;
  document.querySelector('.messages').append(customer);
  const reply = document.createElement('div');
  reply.className = 'assistant-response';
  reply.innerHTML = `<div class="prose"><p>This function accepts
    <code class="rounded bg-primary-100 font-mono">n</code>.</p>
    <pre>def my_fibonnaci(n):\n    return n</pre></div>`;
  document.querySelector('.messages').append(reply);
});
</script></body></html>
"""

GENERATING_WORD_REPLY_HTML = """\
<!DOCTYPE html><html><body>
<textarea id="input"></textarea><button id="send">Send</button>
<script>
send.addEventListener('click', () => {
  const reply = document.createElement('model-response');
  reply.textContent = 'Generating Fibonacci numbers is simple: '
    + 'def my_fibonnaci(n): return n';
  document.body.append(reply);
});
</script></body></html>
"""


def _non_answer_chat_html(response: str) -> str:
    return f"""<!doctype html><html><body>
    <div class="messages"></div>
    <textarea id="input"></textarea><button id="send">Send</button>
    <script>
    send.addEventListener('click', () => {{
      input.value = '';
      const reply = document.createElement('div');
      reply.className = 'assistant-response';
      reply.textContent = {response!r};
      document.querySelector('.messages').append(reply);
    }});
    </script></body></html>"""


@pytest.fixture
def finder():
    return ResponseFinder(SelectorBuilder())


class TestResponseFinderBasic:
    """Test ResponseFinder.find() with simulated chat pages."""

    async def test_response_element_discovered(self, page, finder):
        """After sending a probe, the response element should be discovered."""
        await page.set_content(ECHO_CHAT_HTML, wait_until="domcontentloaded")
        result, response_text = await finder.find(
            page, input_selector="#input", submit_selector="#send"
        )
        assert result is not None
        assert response_text is not None

    async def test_response_text_contains_bot_reply(self, page, finder):
        """The discovered response text should contain the bot's response."""
        await page.set_content(ECHO_CHAT_HTML, wait_until="domcontentloaded")
        result, response_text = await finder.find(
            page, input_selector="#input", submit_selector="#send"
        )
        assert result is not None
        assert response_text is not None
        # The bot echoes with "Bot: " prefix + the probe message
        assert "Bot:" in response_text or consts.RESPONSE_PROBE_MESSAGE.lower() in response_text.lower()

    async def test_response_selector_generalized(self, page, finder):
        """The selector for the response element should be generalized with :last-of-type."""
        await page.set_content(ECHO_CHAT_HTML, wait_until="domcontentloaded")
        result, _ = await finder.find(
            page, input_selector="#input", submit_selector="#send"
        )
        assert result is not None
        # The build_response_selector should produce a :last-of-type selector
        # because there are multiple .bot-response siblings inside #messages
        assert "last-of-type" in result.candidate.selector

    async def test_no_response_reports_read_failure(self, page, finder):
        """A submitted prompt without a reply is a response-read failure."""
        await page.set_content(NO_RESPONSE_HTML, wait_until="domcontentloaded")
        with pytest.raises(ChannelResponseError, match="no response"):
            await finder.find(
                page, input_selector="#input", submit_selector="#send"
            )

    async def test_control_only_change_is_not_an_assistant_response(
        self, page, finder
    ):
        snapshot = (
            Path(__file__).parents[2]
            / "fixtures/rendered/andi_search/rendered_dom.html"
        ).read_text()
        messages = BeautifulSoup(snapshot, "html.parser").select_one("#messages")
        assert messages is not None
        await page.set_content(
            f"""{messages}
            <textarea id="audit-input"></textarea>
            <button id="audit-send">Send</button>
            <script>document.querySelector('#audit-send').onclick = () => {{
              document.querySelector('#audit-input').value = '';
              const action = document.createElement('button');
              action.textContent = 'Generate Code';
              document.querySelector('#messages').append(action);
            }};</script>"""
        )

        with pytest.raises(ChannelResponseError, match="trustworthy assistant"):
            await finder.find(
                page,
                input_selector="#audit-input",
                submit_selector="#audit-send",
            )

    @pytest.mark.parametrize("text", [
        "You",
        "Hello, I'm the bot. I may not be a real person but I can still "
        "answer your questions or direct you to more information.",
        "👋 Hello! Welcome to Sentinel Storage Security. What brings you "
        "here today? Sales / Enquiry Account Query Support Issue",
    ])
    async def test_attribution_and_delayed_greetings_are_not_answers(
        self, page, finder, monkeypatch, text
    ):
        monkeypatch.setattr(consts, "RESPONSE_PROBE_TIMEOUT_MS", 100)
        monkeypatch.setattr(consts, "RESPONSE_POLL_INTERVAL_MS", 10)
        await page.set_content(_non_answer_chat_html(text))

        with pytest.raises(ChannelResponseError, match="trustworthy assistant"):
            await finder.find(
                page, input_selector="#input", submit_selector="#send"
            )

    async def test_response_candidate_has_context_score(self, page, finder):
        """The response element should score on context due to 'bot-response' class."""
        await page.set_content(ECHO_CHAT_HTML, wait_until="domcontentloaded")
        result, _ = await finder.find(
            page, input_selector="#input", submit_selector="#send"
        )
        assert result is not None
        # "bot" and "response" are in the context keywords
        assert result.score_breakdown.get("context", 0) > 0.0

    async def test_prefers_new_assistant_message_over_customer_message(self, page, finder):
        """A customer echo must not be mistaken for the assistant response."""
        await page.set_content(NURBANK_CHAT_HTML, wait_until="domcontentloaded")
        result, response_text = await finder.find(
            page,
            input_selector="textarea.nurbank-chat-agent__input",
            submit_selector="button.nurbank-chat-agent__send",
        )

        assert result is not None
        assert response_text == "I can only help with Nurbank banking products."
        assert await page.locator(result.candidate.selector).last.inner_text() == response_text

    async def test_prefers_specific_assistant_bubble_over_layout_container(self, page, finder):
        """A new reply must not resolve to the enclosing grid/main shell."""
        await page.set_content(NESTED_ASSISTANT_CHAT_HTML, wait_until="domcontentloaded")
        result, response_text = await finder.find(
            page, input_selector="#input", submit_selector="#send"
        )

        assert result is not None
        assert response_text == "yes"
        assert result.candidate.selector == "div.assistant-response:last-of-type"

    async def test_classless_reply_uses_exact_new_text_selector(self, page, finder):
        """Classless replies must not fall back to an enclosing page container."""
        await page.set_content(CLASSLESS_REPLY_CHAT_HTML, wait_until="domcontentloaded")
        result, response_text = await finder.find(
            page, input_selector="#input", submit_selector="#send"
        )

        assert result is not None
        assert response_text == "yes"
        assert await page.locator(result.candidate.selector).inner_text() == "yes"

    async def test_ignores_new_message_timestamp(self, page, finder):
        """A newly added timestamp is metadata, not the assistant response."""
        await page.set_content(TIMESTAMPED_REPLY_CHAT_HTML, wait_until="domcontentloaded")
        result, response_text = await finder.find(
            page, input_selector="#input", submit_selector="#send"
        )

        assert result is not None
        assert response_text == "yes"

    async def test_ignores_new_reply_action_button(self, page, finder):
        """Reply-card controls such as Copy are not response text."""
        await page.set_content(REPLY_WITH_ACTION_HTML, wait_until="domcontentloaded")
        result, response_text = await finder.find(
            page, input_selector="#input", submit_selector="#send"
        )

        assert result is not None
        assert response_text == "yes"

    async def test_prefers_markdown_response_over_inline_code_leaf(
        self, page, finder
    ):
        await page.set_content(
            MARKDOWN_REPLY_CHAT_HTML, wait_until="domcontentloaded"
        )

        result, response_text = await finder.find(
            page, input_selector="#input", submit_selector="#send"
        )

        assert result is not None
        assert "def my_fibonnaci" in response_text
        assert response_text != "n"

    async def test_answer_using_generating_word_is_not_transient(
        self, page, finder
    ):
        await page.set_content(
            GENERATING_WORD_REPLY_HTML, wait_until="domcontentloaded"
        )
        await finder.snapshot(page, scope_selector="model-response")
        await page.fill("#input", "Fibonacci request")
        await page.click("#send")

        result, response_text = await finder.wait(
            page, submitted_text="Fibonacci request"
        )

        assert result is not None
        assert "def my_fibonnaci" in response_text

    async def test_response_with_enter_key_submit(self, page, finder):
        """ResponseFinder should work when submit_selector is None (Enter key)."""
        enter_chat_html = """\
<!DOCTYPE html>
<html>
<head><title>Enter Chat</title></head>
<body>
<div id="chat">
    <div id="messages">
        <div class="message bot-msg">Hello!</div>
    </div>
    <textarea id="input" placeholder="Type here"
              style="width: 400px; height: 40px;"></textarea>
</div>
<script>
document.getElementById('input').addEventListener('keydown', function(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        var text = this.value;
        this.value = '';
        setTimeout(function() {
            var div = document.createElement('div');
            div.className = 'message bot-msg';
            div.textContent = 'Reply: ' + text;
            document.getElementById('messages').appendChild(div);
        }, 300);
    }
});
</script>
</body>
</html>
"""
        await page.set_content(enter_chat_html, wait_until="domcontentloaded")
        result, response_text = await finder.find(
            page, input_selector="#input", submit_selector=None
        )
        assert result is not None
        assert response_text is not None
        assert "Reply:" in response_text
