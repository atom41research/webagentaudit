"""API-based LLM channel implementation.

Sends prompts to LLM APIs (OpenAI, Anthropic) via HTTP and returns
responses as ``ChannelResponse`` objects. No browser needed.
"""

import logging
import os
import time
from datetime import UTC, datetime
from typing import Any

import httpx

from webagentaudit.core.exceptions import (
    ChannelError,
    ChannelNotReadyError,
    ChannelTimeoutError,
)

from .base import BaseLlmChannel
from .config import ApiChannelConfig
from .consts import (
    ANTHROPIC_API_VERSION,
    API_PROVIDER_ANTHROPIC,
    API_PROVIDER_OPENAI,
    DEFAULT_BASE_URL_ANTHROPIC,
    DEFAULT_BASE_URL_OPENAI,
    ENV_API_KEY_ANTHROPIC,
    ENV_API_KEY_OPENAI,
    SUPPORTED_API_PROVIDERS,
)
from .models import ChannelMessage, ChannelResponse

logger = logging.getLogger(__name__)


class ApiChannel(BaseLlmChannel):
    """LLM channel that communicates via HTTP API calls.

    Supports OpenAI and Anthropic chat completion endpoints.
    Each channel instance maintains conversation history for multi-turn
    probes within a single conversation. The harness creates a fresh
    channel per conversation.
    """

    def __init__(self, config: ApiChannelConfig | None = None) -> None:
        resolved_config = config or ApiChannelConfig()
        super().__init__(resolved_config)
        self._api_config: ApiChannelConfig = resolved_config
        self._client: httpx.AsyncClient | None = None
        self._api_key: str | None = None
        self._base_url: str = ""
        self._connected = False
        self._message_history: list[dict[str, str]] = []
        self._pending_text: str | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def connect(self, url: str) -> None:
        """Validate config and initialise the HTTP client.

        Args:
            url: For API channels this can be the API base URL or an
                arbitrary URL (ignored when base_url is set in config).
        """
        provider = self._api_config.provider
        if provider not in SUPPORTED_API_PROVIDERS:
            raise ChannelError(
                f"Unsupported API provider: {provider!r}. "
                f"Supported: {', '.join(SUPPORTED_API_PROVIDERS)}"
            )

        # Resolve API key
        self._api_key = self._api_config.api_key or self._resolve_api_key(provider)
        if not self._api_key:
            env_var = self._env_var_for_provider(provider)
            raise ChannelError(
                f"No API key for provider {provider!r}. "
                f"Set {env_var} or pass api_key in config."
            )

        # Resolve base URL: explicit config > url parameter > provider default
        self._base_url = (
            self._api_config.base_url
            or (url if url and self._looks_like_api_url(url) else None)
            or self._default_base_url(provider)
        )

        timeout_s = self._api_config.response_timeout_ms / 1000.0
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(timeout_s))
        self._message_history = []
        self._pending_text = None
        self._connected = True

        logger.info(
            "ApiChannel connected: provider=%s, model=%s, base_url=%s",
            provider,
            self._api_config.model,
            self._base_url,
        )

    async def disconnect(self) -> None:
        """Close the HTTP client and reset state."""
        self._connected = False
        self._message_history = []
        self._pending_text = None
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def is_ready(self) -> bool:
        """Return True if the client is initialised and API key is set."""
        return (
            self._connected
            and self._client is not None
            and self._api_key is not None
        )

    # ------------------------------------------------------------------
    # Message sending
    # ------------------------------------------------------------------

    async def write(self, text: str) -> None:
        """Buffer text for the next read() call.

        API channels cannot send and receive independently — a single
        HTTP call does both. ``write()`` buffers the prompt so that
        ``read()`` can include it in the API request.
        """
        if not self._connected:
            raise ChannelNotReadyError(
                "Channel is not connected. Call connect() first."
            )
        self._pending_text = text

    async def read(self, timeout_ms: int | None = None) -> ChannelResponse:
        """Send the buffered prompt to the API and return the response.

        Raises:
            ChannelNotReadyError: If no text has been buffered via write().
            ChannelTimeoutError: On HTTP timeout.
            ChannelError: On API errors.
        """
        if not self._connected or self._client is None:
            raise ChannelNotReadyError(
                "Channel is not connected. Call connect() first."
            )
        if self._pending_text is None:
            raise ChannelNotReadyError(
                "No message buffered. Call write() before read()."
            )

        text = self._pending_text
        self._pending_text = None

        return await self._call_api(text, timeout_ms)

    async def send(self, message: ChannelMessage) -> ChannelResponse:
        """Write and read in a single operation (optimised path).

        Bypasses the buffer and calls the API directly.
        """
        if not self._connected or self._client is None:
            raise ChannelNotReadyError(
                "Channel is not connected. Call connect() first."
            )
        return await self._call_api(message.text)

    # ------------------------------------------------------------------
    # API call internals
    # ------------------------------------------------------------------

    async def _call_api(
        self, text: str, timeout_ms: int | None = None,
    ) -> ChannelResponse:
        """Make the HTTP call to the provider's chat completion endpoint."""
        assert self._client is not None  # noqa: S101

        self._message_history.append({"role": "user", "content": text})

        provider = self._api_config.provider
        start_ms = time.monotonic() * 1000

        try:
            if provider == API_PROVIDER_OPENAI:
                response_text = await self._call_openai(timeout_ms)
            elif provider == API_PROVIDER_ANTHROPIC:
                response_text = await self._call_anthropic(timeout_ms)
            else:
                raise ChannelError(f"Unsupported provider: {provider!r}")
        except httpx.TimeoutException as exc:
            effective_timeout = timeout_ms or self._api_config.response_timeout_ms
            raise ChannelTimeoutError(
                f"API request timed out after {effective_timeout}ms"
            ) from exc
        except httpx.HTTPError as exc:
            raise ChannelError(f"HTTP error: {exc}") from exc

        elapsed_ms = (time.monotonic() * 1000) - start_ms

        # Store assistant response in history for multi-turn conversations
        self._message_history.append(
            {"role": "assistant", "content": response_text}
        )

        # Truncate if needed
        truncated = False
        if len(response_text) > self._api_config.max_response_length:
            response_text = response_text[: self._api_config.max_response_length]
            truncated = True

        return ChannelResponse(
            text=response_text,
            response_time_ms=elapsed_ms,
            truncated=truncated,
            timestamp=datetime.now(UTC),
        )

    async def _call_openai(self, timeout_ms: int | None = None) -> str:
        """Call the OpenAI chat completions endpoint."""
        assert self._client is not None  # noqa: S101

        url = f"{self._base_url}/chat/completions"
        messages = self._build_openai_messages()

        payload: dict[str, Any] = {
            "model": self._api_config.model,
            "messages": messages,
            "temperature": self._api_config.temperature,
            "max_tokens": self._api_config.max_tokens,
        }

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        timeout = self._build_timeout(timeout_ms)

        response = await self._client.post(
            url, json=payload, headers=headers, timeout=timeout,
        )

        if response.status_code != 200:
            error_body = response.text
            raise ChannelError(
                f"OpenAI API error {response.status_code}: {error_body}"
            )

        data = response.json()
        return self._extract_openai_response(data)

    async def _call_anthropic(self, timeout_ms: int | None = None) -> str:
        """Call the Anthropic messages endpoint."""
        assert self._client is not None  # noqa: S101

        url = f"{self._base_url}/messages"
        messages = self._build_anthropic_messages()

        payload: dict[str, Any] = {
            "model": self._api_config.model,
            "messages": messages,
            "temperature": self._api_config.temperature,
            "max_tokens": self._api_config.max_tokens,
        }

        if self._api_config.system_prompt:
            payload["system"] = self._api_config.system_prompt

        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": ANTHROPIC_API_VERSION,
            "Content-Type": "application/json",
        }

        timeout = self._build_timeout(timeout_ms)

        response = await self._client.post(
            url, json=payload, headers=headers, timeout=timeout,
        )

        if response.status_code != 200:
            error_body = response.text
            raise ChannelError(
                f"Anthropic API error {response.status_code}: {error_body}"
            )

        data = response.json()
        return self._extract_anthropic_response(data)

    # ------------------------------------------------------------------
    # Message formatting helpers
    # ------------------------------------------------------------------

    def _build_openai_messages(self) -> list[dict[str, str]]:
        """Build the messages array for OpenAI's chat completions API."""
        messages: list[dict[str, str]] = []
        if self._api_config.system_prompt:
            messages.append(
                {"role": "system", "content": self._api_config.system_prompt}
            )
        messages.extend(self._message_history)
        return messages

    def _build_anthropic_messages(self) -> list[dict[str, str]]:
        """Build the messages array for Anthropic's messages API.

        Anthropic uses a top-level ``system`` parameter instead of a
        system message in the messages array.
        """
        return list(self._message_history)

    @staticmethod
    def _extract_openai_response(data: dict[str, Any]) -> str:
        """Extract the assistant message from an OpenAI response."""
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ChannelError(
                f"Unexpected OpenAI response structure: {data}"
            ) from exc

    @staticmethod
    def _extract_anthropic_response(data: dict[str, Any]) -> str:
        """Extract the assistant message from an Anthropic response."""
        try:
            content_blocks = data["content"]
            text_parts = [
                block["text"]
                for block in content_blocks
                if block.get("type") == "text"
            ]
            return "".join(text_parts)
        except (KeyError, IndexError, TypeError) as exc:
            raise ChannelError(
                f"Unexpected Anthropic response structure: {data}"
            ) from exc

    # ------------------------------------------------------------------
    # Configuration helpers
    # ------------------------------------------------------------------

    def _build_timeout(self, timeout_ms: int | None) -> httpx.Timeout | None:
        """Build an httpx Timeout from an optional override in milliseconds."""
        if timeout_ms is not None:
            return httpx.Timeout(timeout_ms / 1000.0)
        return None  # Use client's default timeout

    @staticmethod
    def _resolve_api_key(provider: str) -> str | None:
        """Read the API key from the environment."""
        env_var = ApiChannel._env_var_for_provider(provider)
        return os.environ.get(env_var)

    @staticmethod
    def _env_var_for_provider(provider: str) -> str:
        """Return the environment variable name for a provider's API key."""
        return {
            API_PROVIDER_OPENAI: ENV_API_KEY_OPENAI,
            API_PROVIDER_ANTHROPIC: ENV_API_KEY_ANTHROPIC,
        }[provider]

    @staticmethod
    def _default_base_url(provider: str) -> str:
        """Return the default base URL for a provider."""
        return {
            API_PROVIDER_OPENAI: DEFAULT_BASE_URL_OPENAI,
            API_PROVIDER_ANTHROPIC: DEFAULT_BASE_URL_ANTHROPIC,
        }[provider]

    @staticmethod
    def _looks_like_api_url(url: str) -> bool:
        """Heuristic: does the URL look like an API base URL?"""
        return "api." in url or "/v1" in url
