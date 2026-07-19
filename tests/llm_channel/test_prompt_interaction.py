"""Browser tests based on sanitized Gemini and OpenAI DOM captures."""

from pathlib import Path

import pytest
from playwright.async_api import async_playwright

from webagentaudit.llm_channel.auto_config import AlgorithmicAutoConfigurator
from webagentaudit.core.exceptions import ChannelSubmissionError
from webagentaudit.llm_channel.config import ChannelConfig
from webagentaudit.llm_channel.models import ChannelMessage
from webagentaudit.llm_channel.playwright_channel import PlaywrightChannel
from webagentaudit.llm_channel.strategies.custom import CustomStrategy
import webagentaudit.llm_channel.playwright_channel as channel_module
import webagentaudit.llm_channel.strategies.custom as custom_module

pytestmark = pytest.mark.browser

FIXTURES = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
async def page():
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        page = await browser.new_page()
        yield page
        await browser.close()


@pytest.mark.parametrize(
    ("fixture", "expected_input", "expected_submit"),
    [
        ("gemini_prompt_composer.html", "div.ql-editor", None),
        (
            "openai_prompt_composer.html",
            "textarea.text-p2",
            'button[aria-label="Send prompt to ChatGPT"]',
        ),
    ],
)
async def test_auto_discovers_live_prompt_composer_shapes(
    page, fixture, expected_input, expected_submit
):
    await page.set_content((FIXTURES / fixture).read_text())

    result = await AlgorithmicAutoConfigurator().configure(page, skip_response=True)

    assert result.input_selector == expected_input
    assert result.submit_selector == expected_submit


async def test_response_snapshot_detects_fast_text_and_new_image(page, monkeypatch):
    await page.set_content((FIXTURES / "openai_prompt_composer.html").read_text())
    await page.evaluate(
        """() => {
            const form = document.querySelector('form');
            const input = document.querySelector('textarea');
            const submit = document.querySelector('button[type="submit"]');
            input.addEventListener('input', () => { submit.disabled = false; });
            form.addEventListener('submit', event => {
                event.preventDefault();
                const response = document.createElement('div');
                response.dataset.messageAuthorRole = 'assistant';
                response.innerHTML = `Image created<img alt="generated test image"
                    src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=">`;
                document.body.append(response);
            });
        }"""
    )
    monkeypatch.setattr(custom_module, "RESPONSE_POLL_INTERVAL_MS", 20)
    monkeypatch.setattr(custom_module, "RESPONSE_STABLE_INTERVAL_MS", 100)
    strategy = CustomStrategy(
        "textarea.text-p2",
        '[data-message-author-role="assistant"]',
        'button[aria-label="Send prompt to ChatGPT"]',
    )

    await strategy.prepare_response(page)
    await strategy.send_message(page, "Generate an image")
    response = await strategy.wait_for_response(page, 2_000)
    metadata = await strategy.get_response_metadata(page)

    assert response == "Image created"
    assert metadata["image_count"] == "1"


async def test_noop_submit_click_falls_back_to_enter(page, monkeypatch):
    await page.set_content((FIXTURES / "openai_prompt_composer.html").read_text())
    await page.evaluate(
        """() => {
            const input = document.querySelector('textarea');
            const submit = document.querySelector('button');
            submit.type = 'button';
            input.addEventListener('input', () => { submit.disabled = false; });
            input.addEventListener('keydown', event => {
                if (event.key !== 'Enter') return;
                event.preventDefault();
                input.value = '';
            });
        }"""
    )
    monkeypatch.setattr(custom_module, "SUBMISSION_CONFIRM_TIMEOUT_MS", 100)
    monkeypatch.setattr(custom_module, "SUBMISSION_CONFIRM_POLL_INTERVAL_MS", 20)
    strategy = CustomStrategy(
        "textarea.text-p2",
        '[data-message-author-role="assistant"]',
        'button[aria-label="Send prompt to ChatGPT"]',
    )

    await strategy.prepare_response(page)
    await strategy.send_message(page, "Generate an image")

    assert await page.locator("textarea").input_value() == ""


async def test_email_gated_chat_reports_requirement_without_waiting(page):
    await page.set_content(
        '<input type="email" placeholder="email@example.com">'
        '<textarea id="prompt"></textarea>'
        '<button id="send" disabled>Send</button>'
    )
    strategy = CustomStrategy("#prompt", ".response", "#send")

    with pytest.raises(ChannelSubmissionError, match="requires an email"):
        await strategy.send_message(page, "Can you generate an image?")


async def test_dynamic_response_reader_ignores_submitted_prompt_echo(
    page, monkeypatch
):
    await page.set_content(
        '<form><textarea id="prompt" placeholder="Ask the assistant"></textarea>'
        '<button id="send" type="submit">Send</button></form>'
        '<div id="messages"></div>'
    )
    await page.evaluate(
        """() => document.querySelector('form').addEventListener('submit', event => {
            event.preventDefault();
            const input = document.querySelector('#prompt');
            const messages = document.querySelector('#messages');
            messages.insertAdjacentHTML(
                'beforeend',
                `<div class="user-message">${input.value}</div>`
            );
            input.value = '';
            setTimeout(() => {
                messages.insertAdjacentHTML(
                    'beforeend',
                    '<div class="assistant-message">No</div>'
                );
                setTimeout(() => {
                    messages.lastElementChild.textContent =
                        'No — I can only answer questions in this chat.';
                }, 700);
            }, 50);
        })"""
    )
    monkeypatch.setattr(custom_module, "RESPONSE_POLL_INTERVAL_MS", 20)
    # Keep the test's stability contract longer than the delayed second chunk.
    monkeypatch.setattr(custom_module, "RESPONSE_STABLE_INTERVAL_MS", 900)
    strategy = CustomStrategy("#prompt", None, "#send")

    await strategy.prepare_response(page)
    await strategy.send_message(page, "Can you generate an image?")
    response = await strategy.wait_for_response(page, 2_000)

    assert response == "No — I can only answer questions in this chat."


async def test_explicit_response_reader_ignores_submitted_prompt_echo(
    page, monkeypatch
):
    await page.set_content(
        '<textarea id="prompt"></textarea><button id="send">Send</button>'
        '<div id="messages"><div class="intercom-comment">Welcome</div></div>'
    )
    await page.evaluate(
        """() => document.querySelector('#send').addEventListener('click', () => {
            const input = document.querySelector('#prompt');
            const messages = document.querySelector('#messages');
            messages.insertAdjacentHTML(
                'beforeend', `<div class="intercom-comment">${input.value}</div>`
            );
            input.value = '';
            messages.insertAdjacentHTML(
                'beforeend', '<div class="delivery-status">Seen • Just now</div>'
            );
            setTimeout(() => messages.insertAdjacentHTML(
                'beforeend', '<div class="intercom-comment">No</div>'
            ), 300);
        })"""
    )
    monkeypatch.setattr(custom_module, "RESPONSE_POLL_INTERVAL_MS", 20)
    monkeypatch.setattr(custom_module, "RESPONSE_STABLE_INTERVAL_MS", 100)
    strategy = CustomStrategy("#prompt", ".intercom-comment", "#send")

    await strategy.prepare_response(page)
    await strategy.send_message(page, "Can you generate an image?")
    response = await strategy.wait_for_response(page, 1_000)

    assert response == "No"


async def test_response_reader_waits_for_typing_indicator(page, monkeypatch):
    await page.set_content('<textarea id="prompt"></textarea><div id="messages"></div>')
    monkeypatch.setattr(custom_module, "RESPONSE_POLL_INTERVAL_MS", 20)
    monkeypatch.setattr(custom_module, "RESPONSE_STABLE_INTERVAL_MS", 100)
    strategy = CustomStrategy("#prompt", "#response")
    await strategy.prepare_response(page)
    await page.evaluate(
        """() => {
            document.querySelector('#messages').insertAdjacentHTML(
                'beforeend',
                '<div id="response">No</div><div class="typing-indicator">...</div>'
            );
            setTimeout(() => {
                document.querySelector('#response').textContent =
                    'No — completed response';
                document.querySelector('.typing-indicator').remove();
            }, 250);
        }"""
    )

    response = await strategy.wait_for_response(page, 1_000)

    assert response == "No — completed response"


async def test_response_reader_waits_for_chatgpt_stop_button(page, monkeypatch):
    await page.set_content(
        '<textarea id="prompt"></textarea>'
    )
    monkeypatch.setattr(custom_module, "RESPONSE_POLL_INTERVAL_MS", 20)
    monkeypatch.setattr(custom_module, "RESPONSE_STABLE_INTERVAL_MS", 100)
    strategy = CustomStrategy(
        "#prompt", '[data-message-author-role="assistant"]'
    )
    await strategy.prepare_response(page)
    await page.evaluate(
        """() => {
            document.body.insertAdjacentHTML(
                'beforeend',
                '<div data-message-author-role="assistant">Here is the function:</div>'
                + '<button data-testid="stop-button">Stop generating</button>'
            );
            setTimeout(() => {
                document.querySelector('[data-message-author-role="assistant"]')
                    .textContent = 'Here is the function: def my_fibonnaci(n): return n';
                document.querySelector('[data-testid="stop-button"]').remove();
            }, 1_000);
        }"""
    )

    response = await strategy.wait_for_response(page, 2_000)

    assert "def my_fibonnaci" in response


async def test_channel_waits_for_page_hydration_before_submit(tmp_path, monkeypatch):
    html = tmp_path / "hydrating-chat.html"
    html.write_text(
        """<!doctype html><form><textarea></textarea>
        <button aria-label="Send prompt" type="submit">Send</button></form>
        <script>
        setTimeout(() => document.querySelector('form').addEventListener('submit', event => {
            event.preventDefault();
            document.querySelector('textarea').value = '';
            const response = document.createElement('div');
            response.id = 'response';
            response.textContent = 'Hydrated response';
            document.body.append(response);
        }), 100);
        </script>"""
    )
    monkeypatch.setattr(channel_module, "PAGE_SETTLE_MS", 150)
    monkeypatch.setattr(custom_module, "RESPONSE_POLL_INTERVAL_MS", 20)
    monkeypatch.setattr(custom_module, "RESPONSE_STABLE_INTERVAL_MS", 100)
    strategy = CustomStrategy(
        "textarea", "#response", 'button[aria-label="Send prompt"]'
    )
    channel = PlaywrightChannel(
        ChannelConfig(timeout_ms=2_000), strategy=strategy
    )

    try:
        await channel.connect(html.as_uri())
        response = await channel.send(ChannelMessage(text="Hello"))
    finally:
        await channel.disconnect()

    assert response.text == "Hydrated response"


async def test_channel_reuses_injected_discovery_page_without_navigation(page):
    await page.set_content(
        '<textarea id="prompt" placeholder="Ask the assistant"></textarea>'
    )
    original_url = page.url
    channel = PlaywrightChannel(
        ChannelConfig(timeout_ms=500),
        strategy=CustomStrategy("#prompt", "body"),
        page=page,
    )

    try:
        await channel.connect("https://must-not-be-requested.invalid/")
        assert page.url == original_url
        assert await page.locator("#prompt").count() == 1
    finally:
        await channel.disconnect()


async def test_channel_observes_rendered_text_across_page_frames(page):
    await page.set_content(
        '<main>Outer baseline</main><iframe srcdoc="<p>Inner evidence</p>"></iframe>'
    )
    channel = PlaywrightChannel(
        ChannelConfig(timeout_ms=500),
        strategy=CustomStrategy("main", "body"),
        page=page,
    )

    try:
        await channel.connect("https://must-not-be-requested.invalid/")
        observed = await channel.observe_text()
    finally:
        await channel.disconnect()

    assert observed is not None
    assert "Outer baseline" in observed
    assert "Inner evidence" in observed


async def test_channel_follows_popup_created_after_click(tmp_path, monkeypatch):
    response_page = tmp_path / "response.html"
    response_page.write_text(
        '<div data-message-author-role="assistant">Popup response</div>'
    )
    entry_page = tmp_path / "entry.html"
    entry_page.write_text(
        f"""<!doctype html><form><textarea></textarea>
        <button aria-label="Send prompt" type="submit">Send</button></form>
        <script>
        document.querySelector('form').addEventListener('submit', event => {{
            event.preventDefault();
            document.querySelector('textarea').value = '';
            setTimeout(() => window.open({response_page.as_uri()!r}), 50);
        }});
        </script>"""
    )
    monkeypatch.setattr(channel_module, "PAGE_SETTLE_MS", 0)
    handoff_timeouts = []

    async def bounded_handoff(page, timeout_ms):
        handoff_timeouts.append(timeout_ms)

    monkeypatch.setattr(
        channel_module,
        "wait_for_domcontentloaded_and_inspect",
        bounded_handoff,
    )
    monkeypatch.setattr(custom_module, "RESPONSE_POLL_INTERVAL_MS", 20)
    monkeypatch.setattr(custom_module, "RESPONSE_STABLE_INTERVAL_MS", 100)
    strategy = CustomStrategy(
        "textarea",
        '[data-message-author-role="assistant"]',
        'button[aria-label="Send prompt"]',
    )
    channel = PlaywrightChannel(
        ChannelConfig(timeout_ms=2_000), strategy=strategy
    )

    try:
        await channel.connect(entry_page.as_uri())
        response = await channel.send(ChannelMessage(text="Hello"))
    finally:
        await channel.disconnect()

    assert response.text == "Popup response"
    assert len(handoff_timeouts) == 1
    assert 0 < handoff_timeouts[0] <= 2_000


async def test_channel_follows_delayed_chatgpt_tab(tmp_path, monkeypatch):
    response_page = tmp_path / "chatgpt-response.html"
    response_page.write_text(
        '<div class="flex max-w-full flex-col gap-4 grow">'
        '<div data-message-author-role="assistant" data-message-id="answer">'
        '<div class="markdown prose"><pre><code>'
        '<span>def</span> <span>my_fibonnaci</span><span>(n):</span>'
        '</code></pre></div></div></div>'
    )
    entry_page = tmp_path / "openai-entry.html"
    entry_page.write_text(
        f"""<!doctype html><form><textarea></textarea>
        <button aria-label="Send prompt" type="submit">Send</button></form>
        <script>
        document.querySelector('form').addEventListener('submit', event => {{
            event.preventDefault();
            document.querySelector('textarea').value = '';
            setTimeout(() => window.open({response_page.as_uri()!r}), 800);
        }});
        </script>"""
    )
    monkeypatch.setattr(channel_module, "PAGE_SETTLE_MS", 0)
    monkeypatch.setattr(custom_module, "RESPONSE_POLL_INTERVAL_MS", 20)
    monkeypatch.setattr(custom_module, "RESPONSE_STABLE_INTERVAL_MS", 100)
    strategy = CustomStrategy(
        "textarea",
        '[data-message-author-role="assistant"]',
        'button[aria-label="Send prompt"]',
    )
    channel = PlaywrightChannel(
        ChannelConfig(timeout_ms=2_500), strategy=strategy
    )

    try:
        await channel.connect(entry_page.as_uri())
        response = await channel.send(ChannelMessage(text="Fibonacci"))
    finally:
        await channel.disconnect()

    assert "def my_fibonnaci" in response.text
