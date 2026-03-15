"""Data models for the assessment module."""

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """A single message in ChatML format.

    Role is restricted to a fixed set of values via ``Literal`` to prevent
    injection of arbitrary role strings through user-controlled content.
    Content is always stored as plain text — never parsed for role markers.
    """

    role: Literal["user", "assistant", "system"]
    content: str


class ProbeExchange(BaseModel):
    """A prompt-response exchange stored as ChatML messages.

    Primary data lives in ``messages`` (list of role-tagged messages).
    The ``.prompt`` and ``.response`` properties provide convenient access.
    """

    messages: list[ChatMessage]
    matched_patterns: list[str] = Field(default_factory=list)

    @property
    def prompt(self) -> str:
        """Return the first user message content."""
        for msg in self.messages:
            if msg.role == "user":
                return msg.content
        return ""

    @property
    def response(self) -> str:
        """Return the last assistant message content."""
        for msg in reversed(self.messages):
            if msg.role == "assistant":
                return msg.content
        return ""


class ProbeResult(BaseModel):
    """Result of running a single probe against an LLM."""

    probe_name: str
    conversations_run: int = 0
    vulnerability_detected: bool = False
    matched_patterns: list[str] = Field(default_factory=list)
    exchanges: list[ProbeExchange] = Field(default_factory=list)
    error_count: int = 0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class AssessmentSummary(BaseModel):
    """Aggregated summary of an assessment run."""

    total_probes: int = 0
    vulnerabilities_found: int = 0
    target_url: str = ""


class AssessmentResult(BaseModel):
    """Complete result of an LLM security assessment."""

    summary: AssessmentSummary = Field(default_factory=AssessmentSummary)
    probe_results: list[ProbeResult] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = Field(default_factory=dict)
