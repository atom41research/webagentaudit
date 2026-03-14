"""End-to-end assessment tests against demo pages.

Tests the full assessment pipeline: load probes, connect a channel to a
running demo page, run probes, and verify results.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from webagentaudit.assessment.assessor import LlmAssessor
from webagentaudit.assessment.config import AssessmentConfig
from webagentaudit.assessment.models import ProbeExchange
from webagentaudit.assessment.probes.registry import ProbeRegistry
from webagentaudit.llm_channel.config import ChannelConfig
from webagentaudit.llm_channel.playwright_channel import PlaywrightChannel
from webagentaudit.llm_channel.strategies.custom import CustomStrategy

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
YAML_PROBES_DIR = FIXTURES_DIR / "yaml_probes"


def _channel_factory(headless: bool = True) -> PlaywrightChannel:
    strategy = CustomStrategy(
        input_selector="#prompt-input",
        response_selector=".bot-message:last-child",
        submit_selector="#send-btn",
    )
    return PlaywrightChannel(
        config=ChannelConfig(headless=headless, timeout_ms=10_000),
        strategy=strategy,
    )


# ---------------------------------------------------------------------------
# Assessment against vulnerable demo page
# ---------------------------------------------------------------------------


class TestAssessmentVulnerable:
    """Assess the vulnerable demo page — should find vulnerabilities."""

    async def test_custom_probes_detect_vulnerability(self, demo_server):
        """YAML probes should detect the vulnerable demo's PWNED responses."""
        registry = ProbeRegistry()
        registry.load_yaml_dir(YAML_PROBES_DIR)
        all_probes = registry.get_all()
        assert len(all_probes) > 0, "Should have loaded at least one probe"

        config = AssessmentConfig(workers=1)
        assessor = LlmAssessor(
            config=config,
            channel_factory=_channel_factory,
            registry=registry,
        )

        url = f"{demo_server}/interactive/vulnerable-llm.html"
        result = await assessor.assess(url)

        assert result.summary.total_probes > 0
        # The vulnerable page responds to extraction probes
        assert len(result.probe_results) > 0
        assert result.summary.vulnerabilities_found > 0

        # Find a probe that detected a vulnerability and verify its exchanges
        vuln_probes = [
            pr for pr in result.probe_results if pr.vulnerability_detected
        ]
        assert len(vuln_probes) > 0, "At least one probe should detect a vulnerability"

        vuln_pr = vuln_probes[0]
        assert len(vuln_pr.exchanges) > 0, "Vulnerable probe should have exchanges"

        # At least one exchange should have a non-empty response matching
        # the vulnerable page's behavior (system prompt leak)
        responses_with_content = [
            ex for ex in vuln_pr.exchanges if ex.response
        ]
        assert len(responses_with_content) > 0, (
            "At least one exchange should have a non-empty response"
        )

        # matched_patterns must be non-empty for the vulnerable probe
        assert len(vuln_pr.matched_patterns) > 0, (
            "Vulnerable probe must have matched_patterns"
        )

    async def test_assessment_result_structure(self, demo_server):
        """AssessmentResult should be well-formed with correct field values."""
        registry = ProbeRegistry()
        registry.load_yaml_file(YAML_PROBES_DIR / "single_turn.yaml")

        config = AssessmentConfig(workers=1)
        assessor = LlmAssessor(
            config=config,
            channel_factory=_channel_factory,
            registry=registry,
        )

        url = f"{demo_server}/interactive/vulnerable-llm.html"
        result = await assessor.assess(url)

        assert result.summary.target_url == url
        assert result.summary.total_probes == 1
        for pr in result.probe_results:
            assert pr.probe_name == "extraction.custom_direct_ask"
            assert pr.conversations_run > 0
            assert len(pr.exchanges) > 0
            for exchange in pr.exchanges:
                assert exchange.prompt, "Every exchange must have a non-empty prompt"
                assert exchange.response, "Every exchange must have a non-empty response"

    async def test_vulnerable_matched_patterns_are_from_probe(self, demo_server):
        """matched_patterns should be actual regexes from the probe definition."""
        registry = ProbeRegistry()
        registry.load_yaml_dir(YAML_PROBES_DIR)

        config = AssessmentConfig(workers=1)
        assessor = LlmAssessor(
            config=config,
            channel_factory=_channel_factory,
            registry=registry,
        )

        url = f"{demo_server}/interactive/vulnerable-llm.html"
        result = await assessor.assess(url)

        # Collect all known patterns from loaded probes
        all_probe_patterns = set()
        for probe in registry.get_all():
            all_probe_patterns.update(probe.get_detector_patterns())

        # Every matched pattern must come from a loaded probe
        for pr in result.probe_results:
            for pattern in pr.matched_patterns:
                assert pattern in all_probe_patterns, (
                    f"Matched pattern '{pattern}' not found in any probe's detector_patterns"
                )


# ---------------------------------------------------------------------------
# Assessment against safe demo page
# ---------------------------------------------------------------------------


class TestAssessmentSafe:
    """Assess the safe demo page — should find no vulnerabilities."""

    async def test_safe_page_no_vulnerabilities(self, demo_server):
        """Safe page refuses all probes — no vulnerability should be detected."""
        registry = ProbeRegistry()
        registry.load_yaml_dir(YAML_PROBES_DIR)

        config = AssessmentConfig(workers=1)
        assessor = LlmAssessor(
            config=config,
            channel_factory=_channel_factory,
            registry=registry,
        )

        url = f"{demo_server}/interactive/safe-llm.html"
        result = await assessor.assess(url)

        assert result.summary.total_probes > 0
        assert result.summary.vulnerabilities_found == 0, (
            "Safe page should not trigger any vulnerability detections"
        )
        # Verify probes actually executed (not just skipped)
        assert all(pr.conversations_run > 0 for pr in result.probe_results), (
            "Every probe should have run at least one conversation"
        )
        assert all(len(pr.exchanges) > 0 for pr in result.probe_results), (
            "Every probe should have exchanges — probes ran but found no vulnerability"
        )


# ---------------------------------------------------------------------------
# Assessment against echo demo page
# ---------------------------------------------------------------------------


class TestAssessmentEcho:
    """Assess the echo demo page — responses echo back input."""

    async def test_echo_page_runs_probes(self, demo_server):
        """Echo page should run probes and return echo responses."""
        registry = ProbeRegistry()
        registry.load_yaml_file(YAML_PROBES_DIR / "single_turn.yaml")

        config = AssessmentConfig(workers=1)
        assessor = LlmAssessor(
            config=config,
            channel_factory=_channel_factory,
            registry=registry,
        )

        url = f"{demo_server}/interactive/echo-llm.html"
        result = await assessor.assess(url)

        assert result.summary.total_probes == 1
        # Echo page echoes everything — check we got responses back
        for pr in result.probe_results:
            assert len(pr.exchanges) > 0, "Should have exchanges"
            for exchange in pr.exchanges:
                assert exchange.prompt, "Every exchange must have a non-empty prompt"
                assert exchange.response.startswith("Echo: "), (
                    f"Echo page response should start with 'Echo: ', got: {exchange.response!r}"
                )
                # The echoed text should contain a substring of the prompt
                prompt_fragment = exchange.prompt[:30]
                assert prompt_fragment in exchange.response, (
                    f"Echoed response should contain the prompt text. "
                    f"Prompt fragment: {prompt_fragment!r}, response: {exchange.response!r}"
                )

    async def test_multi_turn_probe_captures_all_turns(self, demo_server):
        """Multi-turn probe should capture all conversation turns."""
        registry = ProbeRegistry()
        registry.load_yaml_file(YAML_PROBES_DIR / "multi_turn.yaml")
        # multi_turn.yaml has 2 conversations x 2 turns = 4 total turns

        config = AssessmentConfig(workers=1)
        assessor = LlmAssessor(
            config=config,
            channel_factory=_channel_factory,
            registry=registry,
        )

        url = f"{demo_server}/interactive/echo-llm.html"
        result = await assessor.assess(url)

        assert result.summary.total_probes == 1
        pr = result.probe_results[0]
        assert pr.conversations_run == 2
        assert len(pr.exchanges) == 4  # 2 conversations x 2 turns
        for exchange in pr.exchanges:
            assert exchange.prompt, "Every turn should have a prompt"
            assert exchange.response, "Every turn should have a response"
            assert exchange.response.startswith("Echo: ")


# ---------------------------------------------------------------------------
# ProbeRegistry loading and filtering
# ---------------------------------------------------------------------------


class TestProbeRegistry:
    """Test probe registry loading from YAML fixtures."""

    def test_load_yaml_dir(self):
        registry = ProbeRegistry()
        loaded = registry.load_yaml_dir(YAML_PROBES_DIR)
        assert loaded > 0
        all_probes = registry.get_all()
        assert len(all_probes) == loaded

    def test_load_single_file(self):
        registry = ProbeRegistry()
        registry.load_yaml_file(YAML_PROBES_DIR / "single_turn.yaml")
        all_probes = registry.get_all()
        assert len(all_probes) == 1
        assert all_probes[0].name == "extraction.custom_direct_ask"

    def test_filter_by_category(self):
        from webagentaudit.core.enums import ProbeCategory

        registry = ProbeRegistry()
        registry.load_yaml_dir(YAML_PROBES_DIR)
        filtered = registry.filter(categories=[ProbeCategory.EXTRACTION])
        assert len(filtered) > 0
        for probe in filtered:
            assert probe.category == ProbeCategory.EXTRACTION

    def test_filter_by_sophistication(self):
        from webagentaudit.core.enums import Sophistication

        registry = ProbeRegistry()
        registry.load_yaml_dir(YAML_PROBES_DIR)
        filtered = registry.filter(sophistication_levels=[Sophistication.BASIC])
        for probe in filtered:
            assert probe.sophistication == Sophistication.BASIC

    def test_probe_has_required_fields(self):
        registry = ProbeRegistry()
        registry.load_yaml_file(YAML_PROBES_DIR / "single_turn.yaml")
        probe = registry.get_all()[0]
        assert probe.name
        assert probe.category
        assert probe.severity
        assert probe.sophistication
        assert probe.description
        assert len(probe.get_detector_patterns()) > 0
