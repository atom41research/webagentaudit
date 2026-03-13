"""DOM pattern checker for LLM input and response indicators."""

from __future__ import annotations

import logging

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

logger = logging.getLogger(__name__)


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

        # Check input indicators
        for selector in LLM_INPUT_INDICATORS:
            try:
                elements = soup.select(selector)
            except Exception:
                logger.debug("Invalid CSS selector skipped: %s", selector)
                continue
            for element in elements:
                signals.append(
                    DetectionSignal(
                        checker_name=self.name,
                        signal_type="llm_input",
                        description=f"Found LLM input indicator matching '{selector}'",
                        confidence=ConfidenceScore(value=SIGNAL_WEIGHT_INPUT_INDICATOR),
                        evidence=str(element)[:200],
                        method=DetectionMethod.DETERMINISTIC,
                        metadata={
                            "matched_selector": selector,
                            "input_selector": selector,
                        },
                    )
                )

        # Check response indicators
        for selector in LLM_RESPONSE_INDICATORS:
            try:
                elements = soup.select(selector)
            except Exception:
                logger.debug("Invalid CSS selector skipped: %s", selector)
                continue
            for element in elements:
                signals.append(
                    DetectionSignal(
                        checker_name=self.name,
                        signal_type="llm_response_area",
                        description=f"Found LLM response area matching '{selector}'",
                        confidence=ConfidenceScore(
                            value=SIGNAL_WEIGHT_RESPONSE_INDICATOR
                        ),
                        evidence=str(element)[:200],
                        method=DetectionMethod.DETERMINISTIC,
                        metadata={
                            "matched_selector": selector,
                            "response_selector": selector,
                        },
                    )
                )

        return signals
