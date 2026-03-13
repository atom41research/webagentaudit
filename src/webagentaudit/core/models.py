"""Shared data models used across all modules."""

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from .consts import (
    CONFIDENCE_CERTAIN_THRESHOLD,
    CONFIDENCE_HIGH_THRESHOLD,
    CONFIDENCE_LOW_THRESHOLD,
    CONFIDENCE_MEDIUM_THRESHOLD,
)
from .enums import ConfidenceLevel, Severity


class ConfidenceScore(BaseModel):
    """A confidence score with a numeric value and derived qualitative level."""

    value: float = Field(ge=0.0, le=1.0)

    @property
    def level(self) -> ConfidenceLevel:
        if self.value >= CONFIDENCE_CERTAIN_THRESHOLD:
            return ConfidenceLevel.CERTAIN
        if self.value >= CONFIDENCE_HIGH_THRESHOLD:
            return ConfidenceLevel.HIGH
        if self.value >= CONFIDENCE_MEDIUM_THRESHOLD:
            return ConfidenceLevel.MEDIUM
        if self.value >= CONFIDENCE_LOW_THRESHOLD:
            return ConfidenceLevel.LOW
        return ConfidenceLevel.NEGLIGIBLE


class Finding(BaseModel):
    """A single finding from detection or assessment."""

    id: str
    title: str
    description: str
    severity: Severity
    confidence: ConfidenceScore
    evidence: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
