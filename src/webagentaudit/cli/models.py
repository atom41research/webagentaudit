"""Structured output models for CLI batch assessment."""

from datetime import datetime
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
    status: Literal["success", "failed", "not_found"]
    reason: str | None = None
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
    not_found: int = 0


class BatchRunMetadata(BaseModel):
    """Reproducibility details for one URL-file assessment."""

    schema_version: Literal[3] = 3
    started_at: datetime
    completed_at: datetime
    webagentaudit_version: str
    git_revision: str | None = None
    git_dirty: bool | None = None
    git_diff_sha256: str | None = None
    command: list[str] = Field(default_factory=list)
    url_file_sha256: str
    probe_files_sha256: dict[str, str] = Field(default_factory=dict)
    browser_name: str
    browser_version: str | None = None
    playwright_version: str


class BatchAssessmentResult(BaseModel):
    """Complete structured result for a URL-file assessment."""

    summary: BatchAssessmentSummary
    targets: list[BatchTargetResult] = Field(default_factory=list)
    run: BatchRunMetadata
    output_file: str | None = None
