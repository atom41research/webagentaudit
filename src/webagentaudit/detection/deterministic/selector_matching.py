"""Selector matching checker for chat widget containers."""

from __future__ import annotations

import logging

from ...core.enums import DetectionMethod
from ...core.models import ConfidenceScore
from ..consts import CHAT_WIDGET_SELECTORS, SIGNAL_WEIGHT_CHAT_WIDGET
from ..models import DetectionSignal, PageData
from .base import BaseSignalChecker

logger = logging.getLogger(__name__)


class SelectorMatchingChecker(BaseSignalChecker):
    """Check DOM for known chat widget container selectors."""

    @property
    def name(self) -> str:
        return "selector_matching"

    def check(self, page_data: PageData) -> list[DetectionSignal]:
        signals: list[DetectionSignal] = []

        if not page_data.html:
            return signals

        try:
            soup = page_data.get_soup()
        except Exception:
            logger.debug("Failed to parse HTML for selector matching")
            return signals

        for selector in CHAT_WIDGET_SELECTORS:
            try:
                elements = soup.select(selector)
            except Exception:
                logger.debug("Invalid CSS selector skipped: %s", selector)
                continue
            for element in elements:
                snippet = str(element)[:200]
                signals.append(
                    DetectionSignal(
                        checker_name=self.name,
                        signal_type="chat_widget",
                        description=f"Found chat widget matching '{selector}'",
                        confidence=ConfidenceScore(value=SIGNAL_WEIGHT_CHAT_WIDGET),
                        evidence=f"{selector} -> {snippet}",
                        method=DetectionMethod.DETERMINISTIC,
                        metadata={"widget_selector": selector},
                    )
                )

        return signals
