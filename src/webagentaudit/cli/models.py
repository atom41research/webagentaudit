"""Structured output models for CLI batch assessment."""

from typing import Literal

from pydantic import BaseModel, Field

from webagentaudit.assessment.models import AssessmentResult


BatchFailurePhase = Literal[
    "navigation",
    "chat_detection",
    "connection",
    "prompt_submission",
    "response_read",
    "assessment",
]


class BatchTargetResult(BaseModel):
    """Operational result for one URL in a batch assessment."""

    url: str
    status: Literal["success", "failed"]
    failure_phase: BatchFailurePhase | None = None
    error: str | None = None
    error_type: str | None = None
    duration_ms: float
    probes_run: int = 0
    vulnerabilities_found: int = 0
    provider_hint: str | None = None
    interaction: str | None = None
    assessment: AssessmentResult | None = None


class BatchAssessmentSummary(BaseModel):
    """Aggregate operational counts for a URL batch."""

    total: int
    succeeded: int
    failed: int


class BatchAssessmentResult(BaseModel):
    """Complete structured result for a URL-file assessment."""

    summary: BatchAssessmentSummary
    targets: list[BatchTargetResult] = Field(default_factory=list)
    output_file: str | None = None
