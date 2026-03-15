"""Configuration for LLM channels."""

from dataclasses import dataclass, field

from .consts import (
    API_PROVIDER_OPENAI,
    DEFAULT_API_MAX_TOKENS,
    DEFAULT_API_TEMPERATURE,
    DEFAULT_MODEL_OPENAI,
)


@dataclass
class ChannelConfig:
    """Configuration for an LLM channel."""

    timeout_ms: int = 30_000
    headless: bool = True
    browser: str = "chromium"
    viewport_width: int = 1280
    viewport_height: int = 720
    user_agent: str | None = None
    extra_headers: dict[str, str] = field(default_factory=dict)
    user_data_dir: str | None = None


@dataclass
class ApiChannelConfig(ChannelConfig):
    """Configuration for API-based LLM channels.

    Extends ChannelConfig with provider-specific settings for HTTP API
    communication (OpenAI, Anthropic).
    """

    provider: str = API_PROVIDER_OPENAI
    api_key: str | None = None
    base_url: str | None = None
    model: str = DEFAULT_MODEL_OPENAI
    system_prompt: str | None = None
    temperature: float = DEFAULT_API_TEMPERATURE
    max_tokens: int = DEFAULT_API_MAX_TOKENS
    response_timeout_ms: int = 60_000
    max_response_length: int = 50_000
