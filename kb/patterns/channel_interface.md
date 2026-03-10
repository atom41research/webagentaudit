# Channel Interface Pattern

## Overview

The LlmChannel provides a uniform send/receive interface over different web-based LLM UIs. Uses Strategy pattern for DOM interaction and Template Method for the channel lifecycle.

## Interface: BaseLlmChannel

```python
async def connect(url) -> None      # Navigate and find the LLM
async def send(message) -> response  # Send prompt, wait for response
async def disconnect() -> None       # Clean up browser resources
async def is_ready() -> bool         # Check if connected
```

Supports async context manager (`async with channel as ch:`).

## Strategy Pattern for Interaction

Different LLM widgets require different DOM interaction:
- Chat widgets (Intercom, Drift, Tidio): click to open, find textarea, type, submit
- Custom UIs: user-provided selectors for input, submit, response areas
- Embedded bots: iframe navigation, then interaction

`BaseInteractionStrategy` ABC defines:
- `find_input(page)`: locate the input element
- `send_message(page, text)`: type and submit
- `wait_for_response(page, timeout_ms)`: wait for and extract response
- `is_response_complete(page)`: check if generation finished

`PlaywrightChannel` delegates all DOM interaction to its strategy. Channel handles browser lifecycle; strategy handles page interaction.

## Response Detection

Determining when an LLM has finished generating is non-trivial:
1. **Stability detection**: Monitor response container for DOM changes. If no change for `RESPONSE_STABLE_INTERVAL_MS`, consider it complete.
2. **Typing indicators**: Check for typing indicator elements disappearing.
3. **Content length**: Response stops growing.

## Design Decisions

1. **Interface over implementation**: Assessment module depends on `BaseLlmChannel` ABC, never on `PlaywrightChannel` directly.
2. **Strategy for flexibility**: New widget types are added as strategies, not channel subclasses.
3. **Config-driven selectors**: `PlaywrightChannelConfig` carries selectors that strategies use.
4. **Async throughout**: All channel operations are async for Playwright compatibility.
