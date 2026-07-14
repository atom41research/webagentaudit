"""ChatBot.com-specific discovery regressions."""

import pytest

from webagentaudit.llm_channel.auto_config.chatbot_com import (
    ChatbotComAutoConfigurator,
)

pytestmark = pytest.mark.browser


@pytest.mark.asyncio
async def test_direct_chatbot_widget_replays_api_and_start_chat(page):
    await page.set_content(
        """<!doctype html>
        <section id="cookies"><a href="#" id="accept" onclick="this.remove()">Accept</a></section>
        <script>
        window.BE_API = {openChatWindow() {
          const frame = document.createElement('iframe');
          frame.id = 'chatbot-chat-frame';
          frame.srcdoc = `<div class="button" onclick="this.hidden=true; document.querySelector('input').hidden=false">Start chat</div>
            <input hidden placeholder="Type your message here">
            <div class="send-icon"></div>`;
          document.body.append(frame);
        }};
        </script>"""
    )

    result = await ChatbotComAutoConfigurator().configure(
        page, skip_response=True
    )

    assert result.input_selector == 'input[placeholder="Type your message here"]'
    assert result.submit_selector == ".send-icon"
    assert result.input_frame_path == ["iframe#chatbot-chat-frame"]
    assert [action.kind for action in result.setup_actions] == [
        "dismiss", "chatbot_open", "trigger"
    ]
