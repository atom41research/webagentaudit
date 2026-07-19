"""Data models for the assessment module."""

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, computed_field


AssessmentFailurePhase = Literal[
    "chat_detection",
    "connection",
    "prompt_submission",
    "response_read",
    "assessment",
]

DetectorEvidenceClassification = Literal[
    "confirmed",
    "observed_unverified",
    "ambiguous_echo",
    "not_observed",
]

AssessmentSecurityVerdict = Literal[
    "vulnerable",
    "pass",
    "probably_not_vulnerable",
    "failed",
]


class DetectorPatternEvidence(BaseModel):
    """Before/after counts for one detector pattern."""

    pattern: str
    baseline_count: int = 0
    prompt_count: int = 0
    after_count: int = 0
    observed_delta: int = 0
    echo_count: int = 0
    residual_count: int = 0


class DetectorEvidence(BaseModel):
    """Detector evidence with explicit attribution confidence."""

    classification: DetectorEvidenceClassification
    observation_available: bool = False
    matched_patterns: list[str] = Field(default_factory=list)
    pattern_counts: list[DetectorPatternEvidence] = Field(default_factory=list)


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
    detector_evidence: DetectorEvidence | None = None
    metadata: dict[str, str] = Field(default_factory=dict)

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


class ProbeError(BaseModel):
    """Operational failure encountered while running a probe."""

    phase: AssessmentFailurePhase
    message: str
    prompt: str | None = None
    detector_evidence: DetectorEvidence | None = None
    metadata: dict[str, str] = Field(default_factory=dict)


class ProbeResult(BaseModel):
    """Result of running a single probe against an LLM."""

    probe_name: str
    conversations_run: int = 0
    vulnerability_detected: bool = False
    matched_patterns: list[str] = Field(default_factory=list)
    echo_safe: bool = True
    prompt_matched_patterns: list[str] = Field(default_factory=list)
    exchanges: list[ProbeExchange] = Field(default_factory=list)
    error_count: int = 0
    errors: list[ProbeError] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @computed_field
    @property
    def security_verdict(self) -> AssessmentSecurityVerdict:
        """Classify security evidence independently of operational success."""
        if self.vulnerability_detected:
            return "vulnerable"
        if not self.errors:
            return "pass" if self.error_count == 0 else "failed"
        if all(
            error.phase == "response_read"
            and error.detector_evidence is not None
            and error.detector_evidence.observation_available
            and error.detector_evidence.classification == "not_observed"
            for error in self.errors
        ):
            return "probably_not_vulnerable"
        return "failed"


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
