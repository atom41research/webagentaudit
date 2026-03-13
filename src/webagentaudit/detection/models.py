"""Detection data models."""

from typing import Any, Optional

from bs4 import BeautifulSoup
from pydantic import BaseModel, Field

from ..core.enums import DetectionMethod
from ..core.models import ConfidenceScore, Finding


class PageData(BaseModel):
    """Parsed page data used by detection checkers."""

    url: str
    html: str
    scripts: list[str] = Field(default_factory=list)
    inline_scripts: list[str] = Field(default_factory=list)
    stylesheets: list[str] = Field(default_factory=list)
    meta_tags: dict[str, str] = Field(default_factory=dict)
    iframes: list[str] = Field(default_factory=list)
    screenshot_path: Optional[str] = None

    model_config = {"arbitrary_types_allowed": True}

    def get_soup(self) -> BeautifulSoup:
        """Parse HTML into BeautifulSoup. Cached on first call."""
        if not hasattr(self, "_soup"):
            object.__setattr__(self, "_soup", BeautifulSoup(self.html, "lxml"))
        return self._soup


class DetectionSignal(BaseModel):
    """A single signal suggesting LLM presence on a page."""

    checker_name: str
    signal_type: str
    description: str
    confidence: ConfidenceScore
    evidence: str
    method: DetectionMethod
    metadata: dict[str, Any] = Field(default_factory=dict)


class DetectionResult(BaseModel):
    """Complete result of LLM detection on a page."""

    url: str
    llm_detected: bool
    overall_confidence: ConfidenceScore
    signals: list[DetectionSignal] = Field(default_factory=list)
    provider_hint: Optional[str] = None
    interaction_hint: Optional[dict[str, str]] = None
    findings: list[Finding] = Field(default_factory=list)
