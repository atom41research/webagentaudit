"""Tests for the LlmDetector orchestrator."""

from unittest.mock import MagicMock

import pytest

from webagentaudit.core.enums import ConfidenceLevel, DetectionMethod
from webagentaudit.core.models import ConfidenceScore
from webagentaudit.detection.config import DetectionConfig
from webagentaudit.detection.deterministic.base import BaseSignalChecker
from webagentaudit.detection.detector import LlmDetector
from webagentaudit.detection.models import DetectionSignal, PageData

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_signal(
    signal_type: str = "test_signal",
    confidence: float = 0.5,
    checker_name: str = "mock_checker",
    metadata: dict | None = None,
) -> DetectionSignal:
    """Create a DetectionSignal with sensible defaults for testing."""
    return DetectionSignal(
        checker_name=checker_name,
        signal_type=signal_type,
        description=f"Mock signal of type {signal_type}",
        confidence=ConfidenceScore(value=confidence),
        evidence="test evidence",
        method=DetectionMethod.DETERMINISTIC,
        metadata=metadata or {},
    )


def _make_page_data(html: str = "<html><body>test</body></html>") -> PageData:
    return PageData(url="https://example.com", html=html)


class StubChecker(BaseSignalChecker):
    """Concrete checker that returns preconfigured signals."""

    def __init__(self, signals: list[DetectionSignal], checker_name: str = "stub"):
        self._signals = signals
        self._name = checker_name

    @property
    def name(self) -> str:
        return self._name

    def check(self, page_data: PageData) -> list[DetectionSignal]:
        return self._signals


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestLlmDetectorNoCheckers:
    """Test detector behaviour with no registered checkers."""

    def test_no_checkers_returns_empty_result(self):
        detector = LlmDetector()
        result = detector.detect(_make_page_data())

        assert result.llm_detected is False
        assert result.signals == []
        assert result.overall_confidence.value == 0.0
        assert result.provider_hint is None
        assert result.interaction_hint is None

    def test_no_checkers_preserves_url(self):
        detector = LlmDetector()
        page = PageData(url="https://target-site.com/page", html="<html></html>")
        result = detector.detect(page)

        assert result.url == "https://target-site.com/page"


class TestLlmDetectorSignalAggregation:
    """Test that signals from registered checkers are properly aggregated."""

    def test_single_checker_signals_are_collected(self):
        signals = [
            _make_signal(signal_type="chat_widget", confidence=0.6),
            _make_signal(signal_type="llm_input", confidence=0.5),
        ]
        checker = StubChecker(signals, "widget_checker")
        detector = LlmDetector()
        detector.register_checker(checker)

        result = detector.detect(_make_page_data())

        assert len(result.signals) == 2
        signal_types = {s.signal_type for s in result.signals}
        assert "chat_widget" in signal_types
        assert "llm_input" in signal_types

    def test_multiple_checkers_signals_combined(self):
        checker_a = StubChecker(
            [_make_signal(signal_type="dom_match", confidence=0.4)],
            "checker_a",
        )
        checker_b = StubChecker(
            [_make_signal(signal_type="known_provider", confidence=0.85,
                          metadata={"provider": "intercom"})],
            "checker_b",
        )
        detector = LlmDetector()
        detector.register_checker(checker_a)
        detector.register_checker(checker_b)

        result = detector.detect(_make_page_data())

        assert len(result.signals) == 2

    def test_checker_returning_no_signals_is_fine(self):
        empty_checker = StubChecker([], "empty")
        signal_checker = StubChecker(
            [_make_signal(confidence=0.7)], "has_signals",
        )
        detector = LlmDetector()
        detector.register_checker(empty_checker)
        detector.register_checker(signal_checker)

        result = detector.detect(_make_page_data())

        assert len(result.signals) == 1


class TestLlmDetectorConfidence:
    """Test confidence aggregation logic."""

    def test_decay_sum_aggregation(self):
        """Multiple signals boost confidence beyond the single strongest.

        Formula: base + sum(val * 0.3^i for i, val in enumerate(remaining))
        With [0.7, 0.5, 0.3]: 0.7 + 0.5*0.3 + 0.3*0.09 = 0.877
        """
        signals = [
            _make_signal(confidence=0.3),
            _make_signal(confidence=0.7),
            _make_signal(confidence=0.5),
        ]
        checker = StubChecker(signals)
        detector = LlmDetector()
        detector.register_checker(checker)

        result = detector.detect(_make_page_data())

        assert result.overall_confidence.value == pytest.approx(0.877, abs=1e-3)

    def test_multiple_signals_beat_single_signal(self):
        """Three signals at 0.5 should score higher than one signal at 0.5."""
        single_checker = StubChecker([_make_signal(confidence=0.5)])
        multi_checker = StubChecker([
            _make_signal(confidence=0.5),
            _make_signal(confidence=0.5),
            _make_signal(confidence=0.5),
        ])

        detector_single = LlmDetector()
        detector_single.register_checker(single_checker)
        result_single = detector_single.detect(_make_page_data())

        detector_multi = LlmDetector()
        detector_multi.register_checker(multi_checker)
        result_multi = detector_multi.detect(_make_page_data())

        assert result_multi.overall_confidence.value > result_single.overall_confidence.value

    def test_single_signal_confidence(self):
        checker = StubChecker([_make_signal(confidence=0.85)])
        detector = LlmDetector()
        detector.register_checker(checker)

        result = detector.detect(_make_page_data())

        assert result.overall_confidence.value == 0.85

    def test_confidence_capped_at_one(self):
        # Even if somehow a signal has confidence 1.0, overall stays <= 1.0
        checker = StubChecker([_make_signal(confidence=1.0)])
        detector = LlmDetector()
        detector.register_checker(checker)

        result = detector.detect(_make_page_data())

        assert result.overall_confidence.value <= 1.0

    def test_zero_confidence_signals_give_zero_overall(self):
        checker = StubChecker([_make_signal(confidence=0.0)])
        detector = LlmDetector()
        detector.register_checker(checker)

        result = detector.detect(_make_page_data())

        assert result.overall_confidence.value == 0.0


class TestLlmDetectorLlmDetectedThreshold:
    """Test that llm_detected is driven by the config threshold."""

    def test_above_default_threshold_is_detected(self):
        # Default threshold is 0.3
        checker = StubChecker([_make_signal(confidence=0.5)])
        detector = LlmDetector()
        detector.register_checker(checker)

        result = detector.detect(_make_page_data())

        assert result.llm_detected is True

    def test_below_default_threshold_is_not_detected(self):
        checker = StubChecker([_make_signal(confidence=0.2)])
        detector = LlmDetector()
        detector.register_checker(checker)

        result = detector.detect(_make_page_data())

        assert result.llm_detected is False

    def test_at_exact_threshold_is_detected(self):
        checker = StubChecker([_make_signal(confidence=0.3)])
        detector = LlmDetector()
        detector.register_checker(checker)

        result = detector.detect(_make_page_data())

        assert result.llm_detected is True

    def test_custom_high_threshold_filters_detection(self):
        config = DetectionConfig(confidence_threshold=0.8)
        checker = StubChecker([_make_signal(confidence=0.7)])
        detector = LlmDetector(config=config)
        detector.register_checker(checker)

        result = detector.detect(_make_page_data())

        assert result.llm_detected is False

    def test_custom_low_threshold_allows_detection(self):
        config = DetectionConfig(confidence_threshold=0.1)
        checker = StubChecker([_make_signal(confidence=0.15)])
        detector = LlmDetector(config=config)
        detector.register_checker(checker)

        result = detector.detect(_make_page_data())

        assert result.llm_detected is True


class TestLlmDetectorProviderHint:
    """Test provider_hint extraction from known_provider signals."""

    def test_extracts_provider_from_known_provider_signal(self):
        signals = [
            _make_signal(
                signal_type="known_provider",
                confidence=0.85,
                metadata={"provider": "intercom"},
            ),
        ]
        checker = StubChecker(signals)
        detector = LlmDetector()
        detector.register_checker(checker)

        result = detector.detect(_make_page_data())

        assert result.provider_hint == "intercom"

    def test_no_provider_hint_without_known_provider_signal(self):
        signals = [_make_signal(signal_type="chat_widget", confidence=0.6)]
        checker = StubChecker(signals)
        detector = LlmDetector()
        detector.register_checker(checker)

        result = detector.detect(_make_page_data())

        assert result.provider_hint is None

    def test_highest_confidence_provider_wins(self):
        """When multiple providers are detected, the highest-confidence one wins."""
        signals = [
            _make_signal(
                signal_type="known_provider",
                confidence=0.7,
                metadata={"provider": "drift"},
            ),
            _make_signal(
                signal_type="known_provider",
                confidence=0.9,
                metadata={"provider": "intercom"},
            ),
        ]
        checker = StubChecker(signals)
        detector = LlmDetector()
        detector.register_checker(checker)

        result = detector.detect(_make_page_data())

        # The highest-confidence provider should be returned
        assert result.provider_hint == "intercom"

    def test_equal_confidence_providers_returns_one(self):
        """When providers have equal confidence, one is returned (deterministic)."""
        signals = [
            _make_signal(
                signal_type="known_provider",
                confidence=0.85,
                metadata={"provider": "drift"},
            ),
            _make_signal(
                signal_type="known_provider",
                confidence=0.85,
                metadata={"provider": "intercom"},
            ),
        ]
        checker = StubChecker(signals)
        detector = LlmDetector()
        detector.register_checker(checker)

        result = detector.detect(_make_page_data())

        assert result.provider_hint in ("drift", "intercom")

    def test_provider_hint_ignored_if_metadata_missing_key(self):
        signals = [
            _make_signal(
                signal_type="known_provider",
                confidence=0.85,
                metadata={"script_url": "something"},  # no 'provider' key
            ),
        ]
        checker = StubChecker(signals)
        detector = LlmDetector()
        detector.register_checker(checker)

        result = detector.detect(_make_page_data())

        assert result.provider_hint is None


class TestLlmDetectorInteractionHint:
    """Test interaction_hint extraction from signal metadata."""

    def test_extracts_input_selector(self):
        signals = [
            _make_signal(
                signal_type="llm_input",
                confidence=0.5,
                metadata={"input_selector": 'textarea[placeholder*="ask"]'},
            ),
        ]
        checker = StubChecker(signals)
        detector = LlmDetector()
        detector.register_checker(checker)

        result = detector.detect(_make_page_data())

        assert result.interaction_hint is not None
        assert result.interaction_hint["input_selector"] == 'textarea[placeholder*="ask"]'

    def test_extracts_response_selector(self):
        signals = [
            _make_signal(
                signal_type="llm_response_area",
                confidence=0.4,
                metadata={"response_selector": '[class*="message-list"]'},
            ),
        ]
        checker = StubChecker(signals)
        detector = LlmDetector()
        detector.register_checker(checker)

        result = detector.detect(_make_page_data())

        assert result.interaction_hint is not None
        assert result.interaction_hint["response_selector"] == '[class*="message-list"]'

    def test_extracts_widget_selector(self):
        signals = [
            _make_signal(
                signal_type="chat_widget",
                confidence=0.6,
                metadata={"widget_selector": "#intercom-container"},
            ),
        ]
        checker = StubChecker(signals)
        detector = LlmDetector()
        detector.register_checker(checker)

        result = detector.detect(_make_page_data())

        assert result.interaction_hint is not None
        assert result.interaction_hint["widget_selector"] == "#intercom-container"

    def test_combines_multiple_selector_hints(self):
        signals = [
            _make_signal(
                signal_type="llm_input",
                confidence=0.5,
                metadata={"input_selector": 'textarea[placeholder*="ask"]'},
            ),
            _make_signal(
                signal_type="chat_widget",
                confidence=0.6,
                metadata={"widget_selector": ".drift-widget"},
            ),
        ]
        checker = StubChecker(signals)
        detector = LlmDetector()
        detector.register_checker(checker)

        result = detector.detect(_make_page_data())

        assert result.interaction_hint is not None
        assert "input_selector" in result.interaction_hint
        assert "widget_selector" in result.interaction_hint

    def test_no_interaction_hint_without_selector_metadata(self):
        signals = [_make_signal(confidence=0.5, metadata={"other_key": "val"})]
        checker = StubChecker(signals)
        detector = LlmDetector()
        detector.register_checker(checker)

        result = detector.detect(_make_page_data())

        assert result.interaction_hint is None


class TestDetectorIntegration:
    """Integration tests using real checkers against fixture HTML."""

    def test_real_checkers_detect_intercom(self):
        """Real checkers should detect Intercom in fixture HTML."""
        from tests.conftest import INTERCOM_CHAT_HTML
        from webagentaudit.detection.deterministic.dom_patterns import DomPatternChecker
        from webagentaudit.detection.deterministic.known_signatures import KnownSignatureChecker
        from webagentaudit.detection.deterministic.selector_matching import SelectorMatchingChecker
        from webagentaudit.detection.models import PageData

        page_data = PageData(
            url="https://example.com",
            html=INTERCOM_CHAT_HTML,
            scripts=["https://widget.intercom.io/widget/abc123"],
        )

        detector = LlmDetector()
        detector.register_checker(DomPatternChecker())
        detector.register_checker(KnownSignatureChecker())
        detector.register_checker(SelectorMatchingChecker())

        result = detector.detect(page_data)

        assert result.llm_detected, "Should detect Intercom chat widget"
        assert result.overall_confidence.value > 0
        assert len(result.signals) > 0

        checker_names = {s.checker_name for s in result.signals}
        # Intercom has a known script signature AND DOM patterns
        assert "known_signatures" in checker_names, (
            f"known_signatures checker should fire for Intercom. Got: {checker_names}"
        )
