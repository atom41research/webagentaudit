"""LLM detection orchestrator."""

from typing import Optional

from ..core.models import ConfidenceScore
from .config import DetectionConfig
from .deterministic.base import BaseSignalChecker
from .models import DetectionResult, DetectionSignal, PageData


class LlmDetector:
    """Orchestrates LLM detection using registered checkers.

    Runs all registered signal checkers against page data, aggregates signals,
    and produces a DetectionResult with an overall confidence score.
    """

    def __init__(self, config: Optional[DetectionConfig] = None) -> None:
        self.config = config or DetectionConfig()
        self._checkers: list[BaseSignalChecker] = []

    def register_checker(self, checker: BaseSignalChecker) -> None:
        self._checkers.append(checker)

    def detect(self, page_data: PageData) -> DetectionResult:
        """Run all checkers and aggregate signals into a detection result."""
        all_signals: list[DetectionSignal] = []

        for checker in self._checkers:
            signals = checker.check(page_data)
            all_signals.extend(signals)

        overall_confidence = self._aggregate_confidence(all_signals)
        provider_hint = self._extract_provider_hint(all_signals)
        interaction_hint = self._extract_interaction_hint(all_signals)

        return DetectionResult(
            url=page_data.url,
            llm_detected=overall_confidence.value >= self.config.confidence_threshold,
            overall_confidence=overall_confidence,
            signals=all_signals,
            provider_hint=provider_hint,
            interaction_hint=interaction_hint,
        )

    def _aggregate_confidence(
        self, signals: list[DetectionSignal]
    ) -> ConfidenceScore:
        """Combine signal confidences. Uses max confidence across all signals."""
        if not signals:
            return ConfidenceScore(value=0.0)
        max_value = max(s.confidence.value for s in signals)
        return ConfidenceScore(value=min(max_value, 1.0))

    def _extract_provider_hint(
        self, signals: list[DetectionSignal]
    ) -> Optional[str]:
        """Extract provider hint from known_signature signals."""
        for signal in signals:
            if signal.signal_type == "known_provider" and "provider" in signal.metadata:
                return signal.metadata["provider"]
        return None

    def _extract_interaction_hint(
        self, signals: list[DetectionSignal]
    ) -> Optional[dict[str, str]]:
        """Extract interaction selectors from signals."""
        hint: dict[str, str] = {}
        for signal in signals:
            if "input_selector" in signal.metadata:
                hint["input_selector"] = signal.metadata["input_selector"]
            if "response_selector" in signal.metadata:
                hint["response_selector"] = signal.metadata["response_selector"]
            if "widget_selector" in signal.metadata:
                hint["widget_selector"] = signal.metadata["widget_selector"]
        return hint if hint else None
