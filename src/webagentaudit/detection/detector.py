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
        """Combine signal confidences using decay-sum.

        Sorts signals by confidence descending, takes the strongest as the base,
        then adds diminishing contributions from remaining signals (0.3^i decay).
        This ensures multiple signals boost confidence beyond the single strongest,
        while capping at 1.0.
        """
        if not signals:
            return ConfidenceScore(value=0.0)
        values = sorted(
            (s.confidence.value for s in signals), reverse=True
        )
        base = values[0]
        remaining = values[1:]
        boost = sum(val * (0.3 ** (i + 1)) for i, val in enumerate(remaining))
        return ConfidenceScore(value=min(base + boost, 1.0))

    def _extract_provider_hint(
        self, signals: list[DetectionSignal]
    ) -> Optional[str]:
        """Extract provider hint from the highest-confidence known_provider signal."""
        provider_signals = [
            s for s in signals
            if s.signal_type == "known_provider" and "provider" in s.metadata
        ]
        if not provider_signals:
            return None
        best = max(provider_signals, key=lambda s: s.confidence.value)
        return best.metadata["provider"]

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
