"""Tests for core data models: ConfidenceScore and Finding."""

import pytest

from webagentaudit.core.enums import ConfidenceLevel, Severity
from webagentaudit.core.models import ConfidenceScore, Finding


class TestConfidenceScoreLevel:
    """Test ConfidenceScore.level derivation at each threshold boundary."""

    def test_zero_is_negligible(self):
        score = ConfidenceScore(value=0.0)
        assert score.level == ConfidenceLevel.NEGLIGIBLE

    def test_just_below_low_threshold_is_negligible(self):
        score = ConfidenceScore(value=0.09)
        assert score.level == ConfidenceLevel.NEGLIGIBLE

    def test_at_low_threshold_is_low(self):
        score = ConfidenceScore(value=0.1)
        assert score.level == ConfidenceLevel.LOW

    def test_just_above_low_threshold_is_low(self):
        score = ConfidenceScore(value=0.11)
        assert score.level == ConfidenceLevel.LOW

    def test_just_below_medium_threshold_is_low(self):
        score = ConfidenceScore(value=0.39)
        assert score.level == ConfidenceLevel.LOW

    def test_at_medium_threshold_is_medium(self):
        score = ConfidenceScore(value=0.4)
        assert score.level == ConfidenceLevel.MEDIUM

    def test_just_above_medium_threshold_is_medium(self):
        score = ConfidenceScore(value=0.41)
        assert score.level == ConfidenceLevel.MEDIUM

    def test_just_below_high_threshold_is_medium(self):
        score = ConfidenceScore(value=0.69)
        assert score.level == ConfidenceLevel.MEDIUM

    def test_at_high_threshold_is_high(self):
        score = ConfidenceScore(value=0.7)
        assert score.level == ConfidenceLevel.HIGH

    def test_just_above_high_threshold_is_high(self):
        score = ConfidenceScore(value=0.71)
        assert score.level == ConfidenceLevel.HIGH

    def test_just_below_certain_threshold_is_high(self):
        score = ConfidenceScore(value=0.89)
        assert score.level == ConfidenceLevel.HIGH

    def test_at_certain_threshold_is_certain(self):
        score = ConfidenceScore(value=0.9)
        assert score.level == ConfidenceLevel.CERTAIN

    def test_just_above_certain_threshold_is_certain(self):
        score = ConfidenceScore(value=0.91)
        assert score.level == ConfidenceLevel.CERTAIN

    def test_max_value_is_certain(self):
        score = ConfidenceScore(value=1.0)
        assert score.level == ConfidenceLevel.CERTAIN


class TestConfidenceScoreValidation:
    """Test ConfidenceScore value validation."""

    def test_rejects_negative_value(self):
        with pytest.raises(Exception):
            ConfidenceScore(value=-0.1)

    def test_rejects_value_above_one(self):
        with pytest.raises(Exception):
            ConfidenceScore(value=1.1)

    def test_accepts_boundary_zero(self):
        score = ConfidenceScore(value=0.0)
        assert score.value == 0.0

    def test_accepts_boundary_one(self):
        score = ConfidenceScore(value=1.0)
        assert score.value == 1.0


class TestFinding:
    """Test Finding creation and serialization."""

    def test_finding_creation_with_required_fields(self):
        confidence = ConfidenceScore(value=0.75)
        finding = Finding(
            id="FIND-001",
            title="Detected Intercom Widget",
            description="An Intercom chat widget was found embedded in the page.",
            severity=Severity.MEDIUM,
            confidence=confidence,
        )
        assert finding.id == "FIND-001"
        assert finding.title == "Detected Intercom Widget"
        assert finding.severity == Severity.MEDIUM
        assert finding.confidence.value == 0.75
        assert finding.evidence == []
        assert finding.metadata == {}

    def test_finding_creation_with_all_fields(self):
        confidence = ConfidenceScore(value=0.85)
        finding = Finding(
            id="FIND-002",
            title="Known Provider Script Detected",
            description="Drift chat widget script found in page source.",
            severity=Severity.HIGH,
            confidence=confidence,
            evidence=["js.driftt.com/include/abc.js", "drift-widget element found"],
            metadata={"provider": "drift", "script_url": "https://js.driftt.com/include/abc.js"},
        )
        assert finding.id == "FIND-002"
        assert finding.severity == Severity.HIGH
        assert len(finding.evidence) == 2
        assert finding.metadata["provider"] == "drift"

    def test_finding_serialization_roundtrip(self):
        confidence = ConfidenceScore(value=0.6)
        finding = Finding(
            id="FIND-003",
            title="Chat Input Area Detected",
            description="A textarea with chat-related placeholder text was found.",
            severity=Severity.LOW,
            confidence=confidence,
            evidence=["<textarea placeholder='Ask me anything'>"],
        )
        data = finding.model_dump()
        assert data["id"] == "FIND-003"
        assert data["title"] == "Chat Input Area Detected"
        assert data["severity"] == "low"
        assert data["confidence"]["value"] == 0.6
        assert isinstance(data["evidence"], list)
        assert "timestamp" in data

    def test_finding_json_serialization(self):
        confidence = ConfidenceScore(value=0.5)
        finding = Finding(
            id="FIND-004",
            title="Test Finding",
            description="A test finding for serialization.",
            severity=Severity.INFO,
            confidence=confidence,
        )
        json_str = finding.model_dump_json()
        assert '"id":"FIND-004"' in json_str or '"id": "FIND-004"' in json_str
        assert "info" in json_str

    def test_finding_timestamp_is_set_automatically(self):
        finding = Finding(
            id="FIND-005",
            title="Auto Timestamp",
            description="Should have a timestamp set automatically.",
            severity=Severity.MEDIUM,
            confidence=ConfidenceScore(value=0.5),
        )
        assert finding.timestamp is not None

    def test_finding_severity_enum_values(self):
        """Verify all severity levels can be used in a Finding."""
        for severity in Severity:
            finding = Finding(
                id=f"SEV-{severity.value}",
                title=f"Severity {severity.value}",
                description=f"Test finding with {severity.value} severity.",
                severity=severity,
                confidence=ConfidenceScore(value=0.5),
            )
            assert finding.severity == severity
