"""DOM pattern checker for LLM input and response indicators."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from ...core.enums import DetectionMethod
from ...core.models import ConfidenceScore
from ..consts import (
    LLM_INPUT_INDICATORS,
    LLM_RESPONSE_INDICATORS,
    SIGNAL_WEIGHT_INPUT_INDICATOR,
    SIGNAL_WEIGHT_RESPONSE_INDICATOR,
)
from ..models import DetectionSignal, PageData
from .base import BaseSignalChecker

if TYPE_CHECKING:
    from bs4 import Tag

logger = logging.getLogger(__name__)


def _element_evidence(element: Tag, max_len: int = 200) -> str:
    """Extract readable evidence text from a DOM element.

    Uses get_text() for clean readable content. Falls back to the opening
    tag with attributes when the element has no text (e.g. empty textarea).
    """
    text = element.get_text(strip=True)
    if text:
        return text[:max_len]
    # Build a readable opening-tag representation (no children, no closing)
    attrs = " ".join(f'{k}="{v}"' for k, v in element.attrs.items() if isinstance(v, str))
    tag_repr = f"<{element.name} {attrs}>" if attrs else f"<{element.name}>"
    return tag_repr[:max_len]


class DomPatternChecker(BaseSignalChecker):
    """Check DOM for LLM input areas and response containers."""

    @property
    def name(self) -> str:
        return "dom_patterns"

    def check(self, page_data: PageData) -> list[DetectionSignal]:
        signals: list[DetectionSignal] = []

        if not page_data.html:
            return signals

        try:
            soup = page_data.get_soup()
        except Exception:
            logger.debug("Failed to parse HTML for DOM pattern checking")
            return signals

        # Check input indicators (one signal per selector pattern)
        for selector in LLM_INPUT_INDICATORS:
            try:
                elements = soup.select(selector)
            except Exception:
                logger.debug("Invalid CSS selector skipped: %s", selector)
                continue
            if elements:
                signals.append(
                    DetectionSignal(
                        checker_name=self.name,
                        signal_type="llm_input",
                        description=f"Found LLM input indicator matching '{selector}'",
                        confidence=ConfidenceScore(value=SIGNAL_WEIGHT_INPUT_INDICATOR),
                        evidence=_element_evidence(elements[0]),
                        method=DetectionMethod.DETERMINISTIC,
                        metadata={
                            "matched_selector": selector,
                            "input_selector": selector,
                            "match_count": len(elements),
                        },
                    )
                )

        # Check response indicators (one signal per selector pattern)
        for selector in LLM_RESPONSE_INDICATORS:
            try:
                elements = soup.select(selector)
            except Exception:
                logger.debug("Invalid CSS selector skipped: %s", selector)
                continue
            if elements:
                signals.append(
                    DetectionSignal(
                        checker_name=self.name,
                        signal_type="llm_response_area",
                        description=f"Found LLM response area matching '{selector}'",
                        confidence=ConfidenceScore(
                            value=SIGNAL_WEIGHT_RESPONSE_INDICATOR
                        ),
                        evidence=_element_evidence(elements[0]),
                        method=DetectionMethod.DETERMINISTIC,
                        metadata={
                            "matched_selector": selector,
                            "response_selector": selector,
                            "match_count": len(elements),
                        },
                    )
                )

        return signals
