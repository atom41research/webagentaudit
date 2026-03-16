"""Tests for assessment data models."""

from datetime import UTC, datetime

import pytest

from webagentaudit.assessment.models import (
    AssessmentResult,
    AssessmentSummary,
    ChatMessage,
    ProbeExchange,
    ProbeResult,
)

pytestmark = pytest.mark.unit


class TestChatMessage:
    """ChatMessage role validation and construction."""

    def test_valid_roles(self):
        for role in ("user", "assistant", "system"):
            msg = ChatMessage(role=role, content="hello")
            assert msg.role == role

    def test_invalid_role_rejected(self):
        with pytest.raises(Exception):
            ChatMessage(role="admin", content="hello")

    def test_content_preserved(self):
        msg = ChatMessage(role="user", content="test content\nwith newlines")
        assert msg.content == "test content\nwith newlines"


class TestProbeExchange:
    """ProbeExchange properties and defaults."""

    def test_prompt_returns_first_user_message(self):
        exchange = ProbeExchange(
            messages=[
                ChatMessage(role="user", content="hello"),
                ChatMessage(role="assistant", content="hi"),
            ]
        )
        assert exchange.prompt == "hello"

    def test_response_returns_last_assistant_message(self):
        exchange = ProbeExchange(
            messages=[
                ChatMessage(role="user", content="hello"),
                ChatMessage(role="assistant", content="first"),
                ChatMessage(role="user", content="again"),
                ChatMessage(role="assistant", content="second"),
            ]
        )
        assert exchange.response == "second"

    def test_prompt_empty_when_no_user_message(self):
        exchange = ProbeExchange(
            messages=[ChatMessage(role="assistant", content="hi")]
        )
        assert exchange.prompt == ""

    def test_response_empty_when_no_assistant_message(self):
        exchange = ProbeExchange(
            messages=[ChatMessage(role="user", content="hello")]
        )
        assert exchange.response == ""

    def test_matched_patterns_default_empty(self):
        exchange = ProbeExchange(
            messages=[ChatMessage(role="user", content="hi")]
        )
        assert exchange.matched_patterns == []

    def test_matched_patterns_stored(self):
        exchange = ProbeExchange(
            messages=[ChatMessage(role="user", content="hi")],
            matched_patterns=["pattern1", "pattern2"],
        )
        assert exchange.matched_patterns == ["pattern1", "pattern2"]


class TestProbeResult:
    """ProbeResult defaults and computed fields."""

    def test_defaults(self):
        result = ProbeResult(probe_name="test.probe")
        assert result.probe_name == "test.probe"
        assert result.conversations_run == 0
        assert result.vulnerability_detected is False
        assert result.matched_patterns == []
        assert result.exchanges == []
        assert isinstance(result.timestamp, datetime)

    def test_vulnerability_detected_flag(self):
        result = ProbeResult(
            probe_name="test.probe",
            vulnerability_detected=True,
            matched_patterns=["(?i)PWNED"],
        )
        assert result.vulnerability_detected is True
        assert len(result.matched_patterns) == 1

    def test_timestamp_is_utc(self):
        result = ProbeResult(probe_name="test.probe")
        assert result.timestamp.tzinfo is not None


class TestAssessmentSummary:
    """AssessmentSummary defaults."""

    def test_defaults(self):
        summary = AssessmentSummary()
        assert summary.total_probes == 0
        assert summary.vulnerabilities_found == 0
        assert summary.target_url == ""

    def test_with_values(self):
        summary = AssessmentSummary(
            total_probes=5, vulnerabilities_found=2, target_url="https://example.com"
        )
        assert summary.total_probes == 5
        assert summary.vulnerabilities_found == 2
        assert summary.target_url == "https://example.com"


class TestAssessmentResult:
    """AssessmentResult structure and serialization."""

    def test_defaults(self):
        result = AssessmentResult()
        assert result.summary.total_probes == 0
        assert result.probe_results == []
        assert result.metadata == {}

    def test_model_dump_json(self):
        result = AssessmentResult(
            summary=AssessmentSummary(total_probes=1, target_url="http://test"),
            probe_results=[
                ProbeResult(
                    probe_name="test.probe",
                    conversations_run=1,
                    vulnerability_detected=True,
                    matched_patterns=["pattern"],
                    exchanges=[
                        ProbeExchange(
                            messages=[
                                ChatMessage(role="user", content="hello"),
                                ChatMessage(role="assistant", content="PWNED"),
                            ],
                            matched_patterns=["pattern"],
                        )
                    ],
                )
            ],
        )
        json_str = result.model_dump_json()
        assert "test.probe" in json_str
        assert "PWNED" in json_str

    def test_round_trip_serialization(self):
        original = AssessmentResult(
            summary=AssessmentSummary(total_probes=2, vulnerabilities_found=1),
            probe_results=[
                ProbeResult(probe_name="a.b", vulnerability_detected=True),
            ],
        )
        json_str = original.model_dump_json()
        restored = AssessmentResult.model_validate_json(json_str)
        assert restored.summary.total_probes == 2
        assert restored.probe_results[0].probe_name == "a.b"
        assert restored.probe_results[0].vulnerability_detected is True
