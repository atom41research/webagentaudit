"""Detection-specific constants."""

# Known LLM chat widget selectors
CHAT_WIDGET_SELECTORS = [
    '[data-testid="chat-widget"]',
    ".chat-bot-container",
    "#intercom-container",
    ".drift-widget",
    "#tidio-chat",
    "#freshdesk-widget",
    ".crisp-client",
    "#chat-widget-container",
    "#hubspot-messages-iframe-container",
    '[class*="chatbot"]',
    '[id*="chatbot"]',
    '[aria-label*="chat"]',
    '[aria-label*="assistant"]',
    '[class*="ai-chat"]',
    '[class*="ai-assistant"]',
]

# DOM patterns indicating LLM input areas
LLM_INPUT_INDICATORS = [
    'textarea[placeholder*="ask"]',
    'textarea[placeholder*="Ask"]',
    'textarea[placeholder*="message"]',
    'textarea[placeholder*="Message"]',
    'textarea[placeholder*="chat"]',
    'textarea[placeholder*="Chat"]',
    'textarea[placeholder*="question"]',
    'textarea[placeholder*="type"]',
    'input[placeholder*="ask"]',
    'input[placeholder*="chat"]',
    'input[placeholder*="message"]',
    '[data-testid*="prompt"]',
    '[data-testid*="chat-input"]',
    '[contenteditable="true"][class*="chat"]',
    '[role="textbox"][aria-label*="chat"]',
    '[role="textbox"][aria-label*="message"]',
]

# DOM patterns indicating LLM response areas
LLM_RESPONSE_INDICATORS = [
    '[class*="message-list"]',
    '[class*="chat-messages"]',
    '[class*="conversation"]',
    '[class*="chat-log"]',
    '[class*="response-container"]',
    '[data-testid*="message"]',
    '[role="log"]',
]

# Known LLM provider script signatures (provider -> list of script URL fragments)
KNOWN_PROVIDER_SCRIPTS: dict[str, list[str]] = {
    "intercom": ["widget.intercom.io", "js.intercomcdn.com"],
    "drift": ["js.driftt.com", "js.drift.com"],
    "tidio": ["code.tidio.co"],
    "zendesk": ["static.zdassets.com", "ekr.zdassets.com"],
    "freshdesk": ["wchat.freshchat.com", "assetscdn-wchat.freshchat.com"],
    "crisp": ["client.crisp.chat"],
    "livechat": ["cdn.livechatinc.com"],
    "hubspot": ["js.usemessages.com", "js.hubspot.com"],
    "tawk": ["embed.tawk.to"],
    "olark": ["static.olark.com"],
    "chatwoot": ["app.chatwoot.com"],
    "botpress": ["cdn.botpress.cloud", "webchat.botpress.cloud"],
    "voiceflow": ["cdn.voiceflow.com"],
    "kommunicate": ["widget.kommunicate.io"],
    "ada": ["static.ada.support"],
}

# API endpoint patterns suggesting LLM backends
LLM_API_PATTERNS = [
    r"/api/v\d+/chat",
    r"/api/chat/completions",
    r"/v\d+/messages",
    r"/api/assistant",
    r"/api/ai/",
    r"/api/bot/",
    r"/completion",
    r"/generate",
    r"/chat/send",
    r"/api/conversation",
]

# Confidence weights for different signal types
SIGNAL_WEIGHT_KNOWN_PROVIDER = 0.85
SIGNAL_WEIGHT_CHAT_WIDGET = 0.6
SIGNAL_WEIGHT_INPUT_INDICATOR = 0.5
SIGNAL_WEIGHT_RESPONSE_INDICATOR = 0.4
SIGNAL_WEIGHT_SCRIPT_ANALYSIS = 0.55
SIGNAL_WEIGHT_NETWORK_HINT = 0.65
