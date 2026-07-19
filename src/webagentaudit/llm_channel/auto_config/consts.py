"""Constants for auto-configuration scoring."""

# ---------------------------------------------------------------------------
# Input Finding
# ---------------------------------------------------------------------------

INPUT_POSITIVE_KEYWORDS = [
    "ask",
    "message",
    "chat",
    "type",
    "question",
    "prompt",
    "write",
    "send",
    "tell",
    "say",
    "query",
]

INPUT_NEGATIVE_KEYWORDS = [
    "search",
    "find",
    "filter",
    "subscribe",
    "email",
    "login",
    "password",
    "username",
    "phone",
    "url",
    "coupon",
    "code",
]

INPUT_CHAT_SIGNAL_KEYWORDS = [
    "ask",
    "assistant",
    "chat",
    "compose",
    "conversation",
    "message",
    "prompt",
    "question",
    "query",
    "rcw-input",
    "tell me",
    "type here",
    "frage",
]

INPUT_STRONG_NEGATIVE_KEYWORDS = [
    "captcha",
    "checkout",
    "coupon",
    "email",
    "first name",
    "first_name",
    "last name",
    "last_name",
    "login",
    "newsletter",
    "password",
    "phone",
    "search",
    "subscribe",
    "terminal",
    "username",
]

# Traditional web forms often label a large textarea "Message". Restrict
# these negatives to the enclosing form so real chat composers may still use
# the same words in their own labels and placeholders.
INPUT_FORM_STRONG_NEGATIVE_KEYWORDS = [
    "contact",
    "gform",
    "gravity",
    "lead-form",
    "lead_form",
]

INPUT_PARENT_KEYWORDS = [
    "chat",
    "assistant",
    "ai",
    "message",
    "conversation",
    "rcw",
    "widget",
    "prompt",
    "copilot",
]

# Scoring weights for input candidates (sum ≈ 1.0)
INPUT_WEIGHT_ELEMENT_TYPE = 0.15
INPUT_WEIGHT_PLACEHOLDER = 0.25
INPUT_WEIGHT_ARIA_LABEL = 0.15
INPUT_WEIGHT_POSITION = 0.10
INPUT_WEIGHT_SIZE = 0.05
INPUT_WEIGHT_PARENT_CONTEXT = 0.15
INPUT_WEIGHT_DATA_TESTID = 0.10
INPUT_WEIGHT_NO_NEGATIVE = 0.05
INPUT_WEIGHT_CHAT_SIGNAL = 0.20

# Minimum score threshold to accept an input candidate
INPUT_MIN_SCORE = 0.30

# ---------------------------------------------------------------------------
# Submit Finding
# ---------------------------------------------------------------------------

SUBMIT_POSITIVE_KEYWORDS = [
    "send",
    "submit",
    "go",
    "ask",
]

SUBMIT_WEIGHT_PROXIMITY = 0.30
SUBMIT_WEIGHT_LABEL = 0.25
SUBMIT_WEIGHT_TYPE = 0.15
SUBMIT_WEIGHT_CLASS = 0.15
SUBMIT_WEIGHT_ICON = 0.15

SUBMIT_MAX_DISTANCE_PX = 200
# Do not click a weak, unrelated icon button (for example, "close sidebar").
# When no control clears this bar, pressing Enter is safer.
SUBMIT_MIN_SCORE = 0.24

# ---------------------------------------------------------------------------
# Response Finding
# ---------------------------------------------------------------------------

RESPONSE_PROBE_MESSAGE = "Hello, this is a test message."
RESPONSE_PROBE_TIMEOUT_MS = 15_000
RESPONSE_DOM_SETTLE_MS = 500
RESPONSE_POLL_INTERVAL_MS = 500
# Valid assistants sometimes answer capability checks with only "No"/"Yes".
RESPONSE_MIN_TEXT_LENGTH = 1
RESPONSE_TRANSIENT_PATTERN = (
    r"^\s*(thinking|loading|generating)(?:\s+(response|answer))?[.\u2026]*\s*$"
)
RESPONSE_METADATA_PATTERN = (
    r"^(today|yesterday|\d{1,2}:\d{2}(?:\s?[ap]m)?|"
    r"\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?)$"
)
RESPONSE_SYSTEM_PATTERN = (
    r"^(we (?:have )?received your message|.*\bwill (?:get|be) back\b|"
    r"give (?:the )?team a way to reach you)"
)
RESPONSE_GREETING_PATTERN = (
    r"^(?:(?:hi|hello|good morning|good afternoon|good evening)\b.*"
    r"(?:how can i help|what would you like|ask me|please select|select which|"
    r"speaking with|ready to assist).*|how can i help\??)$"
)

# Elements to skip when building text snapshots
RESPONSE_IGNORE_TAGS = frozenset(
    ["script", "style", "noscript", "meta", "link"]
)

# ---------------------------------------------------------------------------
# Trigger Finding
# ---------------------------------------------------------------------------

TRIGGER_AI_LABEL_KEYWORDS = [
    "ask ai",
    "assistant",
    "chat",
    "toggle assistant",
    "ai chat",
    "open assistant",
    "chat panel",
    "ai assistant",
    "ask question",
    "ask a question",
    "message us",
    "support",
    "messenger",
    "start a conversation",
    "send us a message",
]

TRIGGER_NEGATIVE_LABEL_KEYWORDS = [
    "close",
    "minimize",
]

TRIGGER_CONVERSATION_LABEL_KEYWORDS = [
    "ask a question",
    "start a conversation",
    "send us a message",
]

TRIGGER_DIALOG_SELECTORS = [
    'button[aria-haspopup="dialog"][aria-expanded="false"]',
    'button[aria-haspopup="dialog"]',
]

TRIGGER_MENU_SELECTORS = [
    'button[aria-controls*="dialog" i]',
    'button[aria-controls*="menu" i]',
    'button[aria-controls*="command" i]',
]

TRIGGER_CHAT_LAUNCHER_SELECTORS = [
    '[role="button"][aria-label*="chat" i]',
    '[role="button"][aria-label*="messenger" i]',
    '[id*="chat" i][id*="activator" i]',
    '[class*="chat" i][class*="launcher" i]',
]

TRIGGER_CSS_VAR_PATTERNS = [
    r"--assistant[_-](?:sheet[_-])?width:\s*0",
    r"--ai[_-]panel[_-](?:width|visible):\s*0",
]

TRIGGER_MIN_SCORE = 0.3
TRIGGER_DECISIVE_SCORE = 0.5
TRIGGER_WAIT_FOR_INPUT_MS = 3000

DISCOVERY_TIMEOUT_MS = 20_000
DISCOVERY_INPUT_POLL_MS = 250
DISCOVERY_ACTION_WAIT_MS = 2_000
DISCOVERY_MAX_BLOCKERS = 3
DISCOVERY_MAX_TRIGGERS = 5
DISCOVERY_MAX_TRIGGER_DEPTH = 2

# Scoring weights for trigger candidates
TRIGGER_WEIGHT_AI_LABEL = 0.30
TRIGGER_WEIGHT_DIALOG_ATTR = 0.25
TRIGGER_WEIGHT_ARIA_CONTROLS = 0.20
TRIGGER_WEIGHT_CSS_VAR = 0.15
TRIGGER_WEIGHT_ICON = 0.10
TRIGGER_WEIGHT_FLOATING_POSITION = 0.20

# ---------------------------------------------------------------------------
# Page preflight
# ---------------------------------------------------------------------------

# Only these controls are clicked, and only when nested in a modal-like UI.
PREFLIGHT_DISMISS_KEYWORDS = [
    "skip",
    "skip setup",
    "skip onboarding",
    "skip tour",
    "accept",
    "accept all",
    "agree",
    "allow all",
    "continue",
    "not now",
    "maybe later",
    "got it",
    "dismiss",
    "close",
    # Common localized consent labels (EasyTrack/Cookiebot).
    "elfogadom",
    "hozzájárulok",
    "engedélyezem",
]
# These labels are unambiguously setup/onboarding actions, even where a site
# does not provide a dialog/overlay semantic wrapper.
PREFLIGHT_EXPLICIT_SETUP_KEYWORDS = [
    "skip setup",
    "skip onboarding",
    "skip tour",
]
PREFLIGHT_MAX_DISMISSALS = 5
PREFLIGHT_SETTLE_MS = 150

# Input selectors to wait for after clicking a trigger
TRIGGER_INPUT_WAIT_SELECTORS = [
    "textarea",
    "input[type='text']",
    "[contenteditable='true']",
    "[role='textbox']",
]

# ---------------------------------------------------------------------------
# Hint Matching
# ---------------------------------------------------------------------------

# Weights for computing similarity between a hint and a candidate (sum = 1.0)
HINT_WEIGHT_TAG = 0.20
HINT_WEIGHT_CLASSES = 0.35
HINT_WEIGHT_LABEL = 0.20
HINT_WEIGHT_ATTRIBUTES = 0.15
HINT_WEIGHT_SVG = 0.10

# Maximum additive boost to a finder score from a matching hint
HINT_BOOST_MAX = 0.40

# Attributes compared in the "attributes" scoring bucket
HINT_MATCHABLE_ATTRIBUTES = ("dir", "type", "role", "placeholder")

# ---------------------------------------------------------------------------
# Selector Building
# ---------------------------------------------------------------------------

# Class prefixes that are auto-generated and should be filtered out
SELECTOR_AUTO_GENERATED_PREFIXES = ("css-", "sc-", "emotion-")

# Maximum class name length to include in selectors
SELECTOR_MAX_CLASS_LENGTH = 40

# Patterns for auto-generated/dynamic IDs that change between sessions
# (Radix UI, React, next.js, etc.)
SELECTOR_DYNAMIC_ID_PATTERNS = (
    "radix-",     # Radix UI: radix-_r_o_, radix-:r1:
    ":r",         # React useId: :r0:, :R1:, :r1m:
    "rc-",        # Ant Design: rc-menu-uuid-1234
    "headlessui-",  # Headless UI: headlessui-menu-1
    "react-aria-",  # React Aria
)

# ---------------------------------------------------------------------------
# Frame / Iframe Discovery
# ---------------------------------------------------------------------------

# CSS selectors for known chat widget iframes (ordered by specificity)
FRAME_CHAT_SELECTORS: list[str] = [
    # Vendor-specific (high confidence)
    "iframe#chat-widget",
    "iframe#chat-widget-minimized",
    "iframe#tidio-chat-iframe",
    "#tidio-chat iframe",
    "iframe#intercom-frame",
    "#intercom-container iframe",
    "iframe#drift-frame-controller",
    "iframe#fc_frame",                          # Freshchat
    "iframe#kommunicate-widget-iframe",
    "#hubspot-messages-iframe-container iframe",
    "iframe#webchat-root",                      # Botpress
    "iframe#fab-root",                          # Botpress FAB
    # Generic attribute-based (medium confidence)
    "iframe[title*='chat' i]",
    "iframe[title*='widget' i]",
    "iframe[title*='messenger' i]",
]

# URL substrings in iframe src that indicate a chat widget
FRAME_URL_PATTERNS: list[str] = [
    "tidio",
    "intercom",
    "drift",
    "freshchat",
    "kommunicate",
    "hubspot",
    "botpress",
    "livechat",
    "zendesk",
    "crisp",
    "tawk",
    "whtvr",
]

# Minimum score threshold for accepting a frame as a chat candidate
FRAME_MIN_SCORE: float = 0.2

# Quick-check selectors to verify a frame has input elements
FRAME_INPUT_CHECK_SELECTORS: list[str] = [
    "textarea",
    "input[type='text']",
    "input:not([type])",
    "[contenteditable='true']",
    "[role='textbox']",
]

# ---------------------------------------------------------------------------
# Chatbase
# ---------------------------------------------------------------------------

CHATBASE_WAIT_MS = 15_000
CHATBASE_INITIAL_WAIT_MS = 1_000
CHATBASE_GREETING_WAIT_MS = 3_000
CHATBASE_LAUNCHER_SELECTOR = "#chatbase-bubble-button"
CHATBASE_EMBED_SELECTOR = 'script[src*="chatbase.co/embed"]'
CHATBASE_FRAME_SELECTOR = "#chatbase-bubble-window iframe"
CHATBASE_INPUT_SELECTOR = "#message"
CHATBASE_RESPONSE_SELECTOR = (
    '[role="log"] [data-loading-assistant] .prose'
)

# ---------------------------------------------------------------------------
# Flyweight AI
# ---------------------------------------------------------------------------

FLYWEIGHT_WAIT_MS = 15_000
FLYWEIGHT_FRAME_SELECTOR = 'iframe[data-testid="chat-overlay"]'
FLYWEIGHT_LAUNCHER_SELECTOR = "#chat-button"
FLYWEIGHT_INPUT_SELECTOR = 'textarea[placeholder="Type your message here..."]'
FLYWEIGHT_SUBMIT_SELECTOR = 'button[aria-label="Send"]'
FLYWEIGHT_RESPONSE_SELECTOR = (
    '[data-testid="message"][data-variant="ai"] [role="log"]'
)

# ---------------------------------------------------------------------------
# Botpress
# ---------------------------------------------------------------------------

BOTPRESS_WAIT_MS = 10_000
BOTPRESS_INPUT_SELECTOR = "textarea.bpComposerInput"
BOTPRESS_RESPONSE_SELECTOR = (
    "div.bpMessageContainer:not(.bpMessageDeliveryStatus)"
    ":not(:has(.bpMessageBlocksButton))"
)

# ---------------------------------------------------------------------------
# Voiceflow
# ---------------------------------------------------------------------------

VOICEFLOW_WAIT_MS = 15_000
VOICEFLOW_INPUT_SELECTOR = "#voiceflow-chat textarea"
VOICEFLOW_RESPONSE_SELECTOR = ".vfrc-system-response"

# ---------------------------------------------------------------------------
# Featurebase
# ---------------------------------------------------------------------------

FEATUREBASE_WAIT_MS = 15_000
FEATUREBASE_FRAME_SELECTOR = 'iframe[name="fb-messenger-frame"]'
FEATUREBASE_INPUT_SELECTOR = (
    '[contenteditable="true"][role="textbox"][aria-label*="message" i]'
)
FEATUREBASE_SUBMIT_SELECTOR = 'button[aria-label="Submit message"]'
FEATUREBASE_RESPONSE_SELECTOR = (
    "[data-fb-conversation-parts-wrapper] > "
    "[data-conversation-part-id]:has(.float-right) + "
    "[data-conversation-part-id] .installation-content"
)
# The current SDK ignores showNewMessage without truthy initial text. The
# shared strategy replaces this invisible draft before anything is submitted.
FEATUREBASE_DISCOVERY_DRAFT = "\u200b"
FEATUREBASE_INTERACTION_DESCRIPTION = (
    "programmatic Featurebase SDK composer; the visible launcher may not "
    "expose a chat box"
)
PROGRAMMATIC_INTERACTION_DESCRIPTIONS = {
    "botpress_open": (
        "programmatic Botpress widget API opening; prompt and response use "
        "rendered chat controls"
    ),
    "featurebase_new_message": FEATUREBASE_INTERACTION_DESCRIPTION,
    "intercom_show": (
        "programmatic Intercom Messenger API opening; prompt and response use "
        "rendered chat controls"
    ),
    "chatbot_open": (
        "programmatic ChatBot.com widget API opening; prompt and response use "
        "rendered chat controls"
    ),
    "tidio_open": (
        "programmatic Tidio widget API opening; prompt and response use "
        "rendered chat controls"
    ),
    "voiceflow_open": (
        "programmatic Voiceflow widget API opening; prompt and response use "
        "rendered chat controls"
    ),
}

# ---------------------------------------------------------------------------
# Tidio
# ---------------------------------------------------------------------------

TIDIO_WAIT_MS = 15_000

# ---------------------------------------------------------------------------
# Intercom
# ---------------------------------------------------------------------------

INTERCOM_MESSENGER_FRAME_SELECTOR = 'iframe[name="intercom-messenger-frame"]'
INTERCOM_CONVERSATION_ACTION_PATTERN = (
    r"ask a question|start a conversation|send us a message"
)
INTERCOM_FRAME_WAIT_MS = 8_000

# ---------------------------------------------------------------------------
# ChatBot.com
# ---------------------------------------------------------------------------

CHATBOT_COM_WAIT_MS = 15_000
CHATBOT_COM_MAX_BLOCKERS = 3
CHATBOT_COM_SETUP_SETTLE_MS = 3_000
CHATBOT_COM_FRAME_SELECTOR = "iframe#chatbot-chat-frame"
CHATBOT_COM_START_SELECTOR = "div.button"
CHATBOT_COM_SUBMIT_SELECTOR = ".send-icon"
CHATBOT_COM_ONBOARDING_SELECTORS = {
    "royalmailpensionplan.co.uk": (
        '[data-conversation-button-tittle="I don\'t know"]'
    ),
    "sanparks.org": (
        '[data-conversation-button-tittle*="I know what to do"]'
    ),
}
LIVECHAT_WAIT_MS = 15_000
LIVECHAT_MINIMIZED_FRAME_SELECTOR = "iframe#chat-widget-minimized"
LIVECHAT_FRAME_SELECTOR = "iframe#chat-widget"
CHATBOT_COM_LIVECHAT_START_SELECTORS = {
    "easytrack.hu": 'button:has-text("Beszélgessünk")',
}
CHATBOT_COM_MOMENT_SELECTOR = 'button[value^="https://url.chatbot.com/url2"]'
CHATBOT_COM_MOMENT_FRAME_SELECTOR = 'iframe[data-testid="moment-app"]'
CHATBOT_COM_HANDOFF_INPUT_SELECTOR = 'textarea[placeholder*="Ide írva kérdez"]'
CHATBOT_COM_HANDOFF_SUBMIT_SELECTOR = 'button[aria-label="Send"]'

# ---------------------------------------------------------------------------
# Denser
# ---------------------------------------------------------------------------

DENSER_WAIT_MS = 25_000
DENSER_LAUNCHER_SELECTOR = 'denser-chatbot button[part="button"]'
DENSER_FRAME_SELECTOR = 'iframe[title="Denser Chatbot"]'
DENSER_INPUT_SELECTOR = "#message"
DENSER_RESPONSE_SELECTOR = (
    ".bg-incomingchat .text-incomingchat-foreground"
)
