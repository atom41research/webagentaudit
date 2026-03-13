"""Data models for the assessment module."""

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class ProbeResult(BaseModel):
    """Result of running a single probe against an LLM."""

    probe_name: str
    conversations_run: int = 0
    vulnerability_detected: bool = False
    matched_patterns: list[str] = Field(default_factory=list)
    responses: list[str] = Field(default_factory=list)
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
