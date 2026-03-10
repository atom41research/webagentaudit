# LlmChannel Module Design

**Path**: `src/webllm/llm_channel/`

## Purpose

Provide an abstract interface for sending prompts to and receiving responses from web-based LLM interfaces. The Playwright-based implementation handles browser automation.

## Interface (`base.py`)

### BaseLlmChannel ABC
```python
class BaseLlmChannel(ABC):
    def __init__(self, config: ChannelConfig): ...

    async def connect(self, url: str) -> None: ...
    async def send(self, message: ChannelMessage) -> ChannelResponse: ...
    async def disconnect(self) -> None: ...
    async def is_ready(self) -> bool: ...

    # Async context manager support
    async def __aenter__(self): return self
    async def __aexit__(self, *args): await self.disconnect()
```

## Data Models (`models.py`)

### ChannelMessage
- `text: str`
- `metadata: dict`

### ChannelResponse
- `text: str`
- `raw_html: Optional[str]`
- `response_time_ms: float`
- `truncated: bool`
- `error: Optional[str]`
- `timestamp: datetime`

## Configuration (`config.py`)

### ChannelConfig (dataclass)
- `response_timeout_ms: int = 30_000`
- `max_response_length: int = 50_000`
- `retry_count: int = 2`

### PlaywrightChannelConfig(ChannelConfig)
- `headless: bool = True`
- `browser_type: str = "chromium"`
- `input_selector: Optional[str]`
- `submit_selector: Optional[str]`
- `response_selector: Optional[str]`
- `wait_for_selector: Optional[str]`
- `viewport_width: int = 1280`
- `viewport_height: int = 720`

## Interaction Strategies (`strategies/`)

### BaseInteractionStrategy ABC
```python
async def find_input(self, page: Page) -> bool: ...
async def send_message(self, page: Page, text: str) -> None: ...
async def wait_for_response(self, page: Page, timeout_ms: int) -> str: ...
async def is_response_complete(self, page: Page) -> bool: ...
```

### ChatWidgetStrategy
Generic strategy for standard chat widgets. Uses configurable selectors.

### CustomStrategy
User-provided CSS selectors for non-standard UIs.

## Playwright Implementation (`playwright_channel.py`)

`PlaywrightChannel(BaseLlmChannel)`:
- Manages browser lifecycle (launch, context, page)
- Delegates DOM interaction to a strategy
- Handles response waiting with stability detection
- Supports both auto-detected and explicit selectors

## Constants (`consts.py`)

- `DEFAULT_VIEWPORT = (1280, 720)`
- `DEFAULT_NAVIGATION_TIMEOUT_MS = 30_000`
- `TYPING_INDICATOR_SELECTORS`: list of known typing indicator selectors
- `RESPONSE_STABLE_INTERVAL_MS = 2_000`: no DOM change threshold
