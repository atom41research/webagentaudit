"""Data models for LLM channel communication."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ChannelMessage(BaseModel):
    """A message to send to the LLM."""
    text: str
    metadata: dict[str, str] = {}


class ChannelResponse(BaseModel):
    """A response received from the LLM."""
    text: str
    response_time_ms: float = 0.0
    truncated: bool = False
    timestamp: datetime | None = None
    metadata: dict[str, str] = {}


class ProxyConfig(BaseModel):
    """Proxy server configuration."""
    server: str
    username: str | None = None
    password: str | None = None


class InteractionAction(BaseModel):
    """One deterministic setup action needed to expose a chat input."""

    kind: Literal[
        "dismiss", "trigger", "botpress_open", "chatbase_open",
        "denser_open", "featurebase_new_message", "intercom_show",
        "chatbot_open", "flyweight_open", "livechat_open", "tidio_open",
        "voiceflow_open"
    ]
    selector: str
    frame_path: list[str] = Field(default_factory=list)
    optional: bool = False


class InteractionPlan(BaseModel):
    """Stable selectors and setup actions discovered for a browser channel."""

    input_selector: str
    submit_selector: str | None = None
    response_selector: str | None = None
    input_frame_path: list[str] = Field(default_factory=list)
    setup_actions: list[InteractionAction] = Field(default_factory=list)
