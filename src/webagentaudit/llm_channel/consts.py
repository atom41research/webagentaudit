"""Constants for the llm_channel module."""

from webagentaudit.core.consts import DEFAULT_TIMEOUT_MS, MAX_RESPONSE_LENGTH

# Re-export core constants used by this module
CHANNEL_DEFAULT_TIMEOUT_MS = DEFAULT_TIMEOUT_MS
CHANNEL_MAX_RESPONSE_LENGTH = MAX_RESPONSE_LENGTH

# Viewport defaults
DEFAULT_VIEWPORT_WIDTH = 1280
DEFAULT_VIEWPORT_HEIGHT = 720

# Default retry count for send operations
DEFAULT_RETRY_COUNT = 2

# Response stability detection: if the response text doesn't change
# for this many milliseconds, consider the response complete.
RESPONSE_STABLE_INTERVAL_MS = 2_000

# Polling interval for checking response stability (ms)
RESPONSE_POLL_INTERVAL_MS = 200

# Default navigation timeout (ms)
DEFAULT_NAVIGATION_TIMEOUT_MS = 30_000

# Wait time after navigation for JS frameworks to render (ms)
PAGE_SETTLE_MS = 3_000

# Supported browser types
SUPPORTED_BROWSER_TYPES = ("chromium", "firefox", "webkit")

# Default browser type
DEFAULT_BROWSER_TYPE = "chromium"

# Known typing indicator selectors that signal the LLM is still generating
TYPING_INDICATOR_SELECTORS = [
    ".typing-indicator",
    "[data-testid='typing-indicator']",
    ".is-typing",
    ".chat-typing",
    ".message-typing",
    ".bot-typing",
    ".assistant-typing",
    ".loading-dots",
    ".response-loading",
    "[aria-label='typing']",
    "[aria-label='Loading']",
    ".pulse-animation",
    ".thinking-indicator",
]

# ---------- API Channel constants ----------

# Supported API providers
API_PROVIDER_OPENAI = "openai"
API_PROVIDER_ANTHROPIC = "anthropic"
SUPPORTED_API_PROVIDERS = (API_PROVIDER_OPENAI, API_PROVIDER_ANTHROPIC)

# Default models per provider
DEFAULT_MODEL_OPENAI = "gpt-4o-mini"
DEFAULT_MODEL_ANTHROPIC = "claude-sonnet-4-20250514"

# Default API base URLs
DEFAULT_BASE_URL_OPENAI = "https://api.openai.com/v1"
DEFAULT_BASE_URL_ANTHROPIC = "https://api.anthropic.com/v1"

# Environment variable names for API keys
ENV_API_KEY_OPENAI = "OPENAI_API_KEY"
ENV_API_KEY_ANTHROPIC = "ANTHROPIC_API_KEY"

# Default API parameters
DEFAULT_API_TEMPERATURE = 0.0
DEFAULT_API_MAX_TOKENS = 4096

# Anthropic API version header
ANTHROPIC_API_VERSION = "2023-06-01"
