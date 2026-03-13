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

# Minimum score threshold to accept an input candidate
INPUT_MIN_SCORE = 0.1

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
SUBMIT_MIN_SCORE = 0.15

# ---------------------------------------------------------------------------
# Response Finding
# ---------------------------------------------------------------------------

RESPONSE_PROBE_MESSAGE = "Hello, this is a test message."
RESPONSE_PROBE_TIMEOUT_MS = 15_000
RESPONSE_DOM_SETTLE_MS = 500
RESPONSE_POLL_INTERVAL_MS = 500
RESPONSE_MIN_TEXT_LENGTH = 3

# Elements to skip when building text snapshots
RESPONSE_IGNORE_TAGS = frozenset(
    ["script", "style", "noscript", "meta", "link"]
)

# ---------------------------------------------------------------------------
# Trigger Finding
# ---------------------------------------------------------------------------

TRIGGER_AI_LABEL_KEYWORDS = [
    "ask ai",
    "toggle assistant",
    "ai chat",
    "open assistant",
    "chat panel",
    "ai assistant",
    "ask question",
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

TRIGGER_CSS_VAR_PATTERNS = [
    r"--assistant[_-](?:sheet[_-])?width:\s*0",
    r"--ai[_-]panel[_-](?:width|visible):\s*0",
]

TRIGGER_MIN_SCORE = 0.2
TRIGGER_WAIT_FOR_INPUT_MS = 3000

# Scoring weights for trigger candidates
TRIGGER_WEIGHT_AI_LABEL = 0.30
TRIGGER_WEIGHT_DIALOG_ATTR = 0.25
TRIGGER_WEIGHT_ARIA_CONTROLS = 0.20
TRIGGER_WEIGHT_CSS_VAR = 0.15
TRIGGER_WEIGHT_ICON = 0.10

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
