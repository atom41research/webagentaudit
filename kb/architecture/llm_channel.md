# LlmChannel Module Design

**Path**: `src/webagentaudit/llm_channel/`

## Purpose

Provide an abstract interface for sending prompts to and receiving responses from web-based LLM interfaces. Two implementations exist: `PlaywrightChannel` for browser automation and `ApiChannel` for direct HTTP API calls (OpenAI, Anthropic).

## Interface (`base.py`)

### BaseLlmChannel ABC
```python
class BaseLlmChannel(ABC):
    def __init__(self, config: ChannelConfig) -> None: ...

    @property
    def config(self) -> ChannelConfig: ...

    async def connect(self, url: str) -> None: ...
    async def send(self, message: ChannelMessage) -> ChannelResponse: ...
    async def write(self, text: str) -> None: ...
    async def read(self, timeout_ms: int | None = None) -> ChannelResponse: ...
    async def disconnect(self) -> None: ...
    async def is_ready(self) -> bool: ...
```

No async context manager support (`__aenter__`/`__aexit__` are not implemented).

## Data Models (`models.py`)

### ChannelMessage (Pydantic BaseModel)
- `text: str`
- `metadata: dict[str, str] = {}`

### ChannelResponse (Pydantic BaseModel)
- `text: str`
- `response_time_ms: float = 0.0`
- `truncated: bool = False`
- `timestamp: datetime | None = None`
- `metadata: dict[str, str] = {}`

### ProxyConfig (Pydantic BaseModel)
- `server: str`
- `username: str | None = None`
- `password: str | None = None`

## Configuration (`config.py`)

### ChannelConfig (dataclass)
- `timeout_ms: int = 30_000`
- `headless: bool = True`
- `browser: str = "chromium"`
- `viewport_width: int = 1280`
- `viewport_height: int = 720`
- `user_agent: str | None = None`
- `extra_headers: dict[str, str] = field(default_factory=dict)`
- `user_data_dir: str | None = None`

### ApiChannelConfig(ChannelConfig)
- `provider: str = API_PROVIDER_OPENAI`
- `api_key: str | None = None`
- `base_url: str | None = None`
- `model: str = DEFAULT_MODEL_OPENAI`
- `system_prompt: str | None = None`
- `temperature: float = DEFAULT_API_TEMPERATURE`
- `max_tokens: int = DEFAULT_API_MAX_TOKENS`
- `response_timeout_ms: int = 60_000`
- `max_response_length: int = 50_000`

Note: `PlaywrightChannelConfig` no longer exists as a separate class. Browser-related fields (`headless`, `browser`, `viewport_*`, `user_agent`, `extra_headers`, `user_data_dir`) are part of the base `ChannelConfig`.

## Interaction Strategies (`strategies/`)

### BaseStrategy ABC (`strategies/base.py`)
```python
class BaseStrategy(ABC):
    async def find_input(self, page) -> bool: ...
    async def send_message(self, page, text: str) -> None: ...
    async def wait_for_response(self, page, timeout_ms: int) -> str: ...
    async def get_response(self, page, timeout_ms: int) -> str | None: ...
```

`BaseInteractionStrategy` is kept as an alias for backward compatibility.

### ChatWidgetStrategy (`strategies/chat_widget.py`)
Generic strategy for standard chat widgets. Uses configurable selectors.

### CustomStrategy (`strategies/custom.py`)
User-provided CSS selectors for non-standard UIs.

## Playwright Implementation (`playwright_channel.py`)

`PlaywrightChannel(BaseLlmChannel)`:
- Accepts `config`, `strategy` (BaseStrategy), and optional external `browser` instance
- Manages browser lifecycle (launch, context, page)
- Supports persistent browser contexts via `user_data_dir`
- Supports reusing an external `Browser` instance (avoids redundant launches)
- Resolves iframe targets via `strategy.iframe_selector` if present
- Delegates DOM interaction to a strategy
- Implements `write()` (fill input) and `read()` (get response) as separate operations

## API Implementation (`api_channel.py`)

`ApiChannel(BaseLlmChannel)`:
- Sends prompts to LLM APIs (OpenAI, Anthropic) via HTTP using `httpx`
- No browser needed — uses `ApiChannelConfig`
- Maintains conversation history for multi-turn probes within a single channel instance
- `write()` buffers text; `read()` sends the buffered prompt and returns the response
- `send()` bypasses the buffer for single-call convenience
- Resolves API keys from config or environment variables (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`)

## Auto-Configuration (`auto_config/`)

**Path**: `src/webagentaudit/llm_channel/auto_config/`

Algorithmic discovery of LLM chat elements on a live page. No LLM/vision required.

### BaseAutoConfigurator ABC (`auto_config/base.py`)
```python
class BaseAutoConfigurator(ABC):
    async def configure(
        self, page: Page | Frame, *,
        skip_response: bool = False,
        input_hint: ElementHint | None = None,
        submit_hint: ElementHint | None = None,
        response_hint: ElementHint | None = None,
    ) -> AutoConfigResult: ...
```

### AlgorithmicAutoConfigurator (`auto_config/configurator.py`)
Orchestrates a multi-phase discovery pipeline:
1. **TriggerFinder**: detect and click hidden panel buttons (dialogs, side panels, command menus)
2. **FrameFinder**: discover iframes containing chat widgets
3. **InputFinder**: heuristic scoring of candidate input elements (searches main page + iframes)
4. **SubmitFinder**: spatial proximity + label scoring of submit buttons
5. **ResponseFinder**: interactive DOM diffing after sending a probe message
6. **SelectorBuilder**: constructs reusable CSS selectors for discovered elements

### Key Models (`auto_config/models.py`)
- `AutoConfigResult`: discovered selectors (`input_selector`, `submit_selector`, `response_selector`) with `ConfidenceScore` values, plus iframe info and trigger info
- `ElementCandidate`: raw DOM properties for scoring
- `ElementHint`: parsed attributes from user-provided HTML snippets for fuzzy matching
- `ScoredElement`: candidate + computed score + breakdown
- `FrameCandidate`: iframe that may contain a chat widget
- `TriggerResult`: which element was clicked and the trigger mechanism type

## Proxy Support (`proxy.py`)

- `ProxyRotator`: rotates through a list of `ProxyConfig` instances (round-robin or random)
- `parse_proxy_url(url) -> ProxyConfig`: parses proxy URLs (supports auth, socks5)
- `load_proxy_file(path) -> list[ProxyConfig]`: loads proxy list from a text file

## Constants (`consts.py`)

- `DEFAULT_VIEWPORT_WIDTH = 1280` / `DEFAULT_VIEWPORT_HEIGHT = 720`
- `DEFAULT_NAVIGATION_TIMEOUT_MS = 30_000`
- `RESPONSE_STABLE_INTERVAL_MS = 2_000`: no DOM change threshold
- `RESPONSE_POLL_INTERVAL_MS = 200`
- `PAGE_SETTLE_MS = 3_000`: wait after navigation for JS frameworks
- `TYPING_INDICATOR_SELECTORS`: list of known typing indicator CSS selectors
- `SUPPORTED_BROWSER_TYPES`: `("chromium", "firefox", "webkit")`
- API constants: `API_PROVIDER_OPENAI`, `API_PROVIDER_ANTHROPIC`, default models/URLs, env var names
