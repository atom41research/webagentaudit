"""Structured output models for CLI batch assessment."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, computed_field

from webagentaudit.assessment.models import (
    AssessmentResult,
    AssessmentSecurityVerdict,
)


BatchFailurePhase = Literal[
    "navigation",
    "chat_detection",
    "connection",
    "prompt_submission",
    "response_read",
    "assessment",
]

BatchOutcome = Literal[
    "vulnerable",
    "passed",
    "probably_not_vulnerable",
    "failed",
    "not_found",
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

    @computed_field
    @property
    def security_verdict(self) -> AssessmentSecurityVerdict | None:
        """Aggregate probe verdicts without changing operational status."""
        if not self.assessment or not self.assessment.probe_results:
            return None
        verdicts = {
            result.security_verdict
            for result in self.assessment.probe_results
        }
        if "vulnerable" in verdicts:
            return "vulnerable"
        if "failed" in verdicts:
            return "failed"
        if "probably_not_vulnerable" in verdicts:
            return "probably_not_vulnerable"
        return "pass"

    @computed_field
    @property
    def outcome(self) -> BatchOutcome:
        """Return the mutually exclusive operator-facing target outcome."""
        if self.status == "not_found":
            return "not_found"
        if self.security_verdict == "vulnerable":
            return "vulnerable"
        if self.status == "success":
            return "passed"
        if self.security_verdict == "probably_not_vulnerable":
            return "probably_not_vulnerable"
        return "failed"


class BatchAssessmentSummary(BaseModel):
    """Mutually exclusive operator-facing outcomes for a URL batch."""

    total: int
    vulnerable: int = 0
    passed: int = 0
    probably_not_vulnerable: int = 0
    failed: int = 0
    not_found: int = 0


class BatchRunMetadata(BaseModel):
    """Reproducibility details for one URL-file assessment."""

    schema_version: Literal[7] = 7
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
