"""Data models for LLM channel communication."""

from datetime import datetime

from pydantic import BaseModel


class ChannelMessage(BaseModel):
    """A message to send to the LLM."""
    text: str
    metadata: dict[str, str] = {}


class ChannelResponse(BaseModel):
    """A response received from the LLM."""
    text: str
    raw_html: str | None = None
    response_time_ms: float = 0.0
    truncated: bool = False
    timestamp: datetime | None = None
    metadata: dict[str, str] = {}


class ProxyConfig(BaseModel):
    """Proxy server configuration."""
    server: str
    username: str | None = None
    password: str | None = None
