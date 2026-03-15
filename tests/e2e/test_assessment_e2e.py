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


@pytest.fixture
def channel_factory(request):
    """Channel factory that respects --headed from conftest."""
    headed = request.config.getoption("--headed", default=False)

    def _factory() -> PlaywrightChannel:
        strategy = CustomStrategy(
            input_selector="#prompt-input",
            response_selector=".bot-message:last-child",
            submit_selector="#send-btn",
        )
        return PlaywrightChannel(
            config=ChannelConfig(headless=not headed, timeout_ms=10_000),
            strategy=strategy,
        )

    return _factory


# ---------------------------------------------------------------------------
# Assessment against vulnerable demo page
# ---------------------------------------------------------------------------


class TestAssessmentVulnerable:
    """Assess the vulnerable demo page — should find vulnerabilities."""

    async def test_custom_probes_detect_vulnerability(self, demo_server, channel_factory):
        """YAML probes should detect the vulnerable demo's PWNED responses."""
        registry = ProbeRegistry()
        registry.load_yaml_dir(YAML_PROBES_DIR)
        all_probes = registry.get_all()
        assert len(all_probes) > 0, "Should have loaded at least one probe"

        config = AssessmentConfig(workers=1)
        assessor = LlmAssessor(
            config=config,
            channel_factory=channel_factory,
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

    async def test_assessment_result_structure(self, demo_server, channel_factory):
        """AssessmentResult should be well-formed with correct field values."""
        registry = ProbeRegistry()
        registry.load_yaml_file(YAML_PROBES_DIR / "single_turn.yaml")

        config = AssessmentConfig(workers=1)
        assessor = LlmAssessor(
            config=config,
            channel_factory=channel_factory,
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

    async def test_vulnerable_matched_patterns_are_from_probe(self, demo_server, channel_factory):
        """matched_patterns should be actual regexes from the probe definition."""
        registry = ProbeRegistry()
        registry.load_yaml_dir(YAML_PROBES_DIR)

        config = AssessmentConfig(workers=1)
        assessor = LlmAssessor(
            config=config,
            channel_factory=channel_factory,
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

    async def test_safe_page_no_vulnerabilities(self, demo_server, channel_factory):
        """Safe page refuses all probes — no vulnerability should be detected."""
        registry = ProbeRegistry()
        registry.load_yaml_dir(YAML_PROBES_DIR)

        config = AssessmentConfig(workers=1)
        assessor = LlmAssessor(
            config=config,
            channel_factory=channel_factory,
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
# Assessment against reverse demo page
# ---------------------------------------------------------------------------


class TestAssessmentReverse:
    """Assess the reverse demo page — responses reverse the input.

    The reverse page returns 'Reverse: <reversed input>', making it trivial
    to verify that input and output are correctly captured and distinct.
    """

    async def test_reverse_page_runs_multiple_probes(self, demo_server, channel_factory):
        """All probes should run and produce distinct input/output pairs."""
        registry = ProbeRegistry()
        registry.load_yaml_dir(YAML_PROBES_DIR)
        all_probes = registry.get_all()
        assert len(all_probes) >= 2, "Should have multiple probes for this test"

        config = AssessmentConfig(workers=1)
        assessor = LlmAssessor(
            config=config,
            channel_factory=channel_factory,
            registry=registry,
        )

        url = f"{demo_server}/interactive/reverse-llm.html"
        result = await assessor.assess(url)

        assert result.summary.total_probes == len(all_probes)
        assert len(result.probe_results) == len(all_probes)

        for pr in result.probe_results:
            assert len(pr.exchanges) > 0, (
                f"Probe '{pr.probe_name}' should have exchanges"
            )
            for exchange in pr.exchanges:
                assert exchange.prompt, "Every exchange must have a non-empty prompt"
                assert exchange.response.startswith("Reverse: "), (
                    f"Reverse page response should start with 'Reverse: ', "
                    f"got: {exchange.response!r}"
                )
                # The response must differ from the prompt (reversed text)
                reversed_text = exchange.response.removeprefix("Reverse: ")
                assert reversed_text != exchange.prompt, (
                    "Reversed output must differ from input"
                )
                # Verify the response is actually the prompt reversed
                expected_reversed = exchange.prompt.strip().split("\n")
                # Just check first line reversed (multi-line prompts get joined)
                first_line = expected_reversed[0].strip()
                assert reversed_text.endswith(first_line[0]), (
                    f"Reversed text should end with first char of prompt. "
                    f"Prompt starts with: {first_line[:10]!r}, "
                    f"reversed ends with: {reversed_text[-10:]!r}"
                )

    async def test_multi_turn_probe_captures_all_turns(self, demo_server, channel_factory):
        """Multi-turn probe should capture all conversation turns with reversed output."""
        registry = ProbeRegistry()
        registry.load_yaml_file(YAML_PROBES_DIR / "multi_turn.yaml")
        # multi_turn.yaml has 2 conversations x 2 turns = 4 total turns

        config = AssessmentConfig(workers=1)
        assessor = LlmAssessor(
            config=config,
            channel_factory=channel_factory,
            registry=registry,
        )

        url = f"{demo_server}/interactive/reverse-llm.html"
        result = await assessor.assess(url)

        assert result.summary.total_probes == 1
        pr = result.probe_results[0]
        assert pr.conversations_run == 2
        assert len(pr.exchanges) == 4  # 2 conversations x 2 turns
        for exchange in pr.exchanges:
            assert exchange.prompt, "Every turn should have a prompt"
            assert exchange.response, "Every turn should have a response"
            assert exchange.response.startswith("Reverse: ")
            # Input and output are provably different
            assert exchange.response != exchange.prompt


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


# ---------------------------------------------------------------------------
# Assessment with built-in Python probes (canary-based)
# ---------------------------------------------------------------------------


class TestAssessmentBuiltinProbes:
    """Assess demo pages using built-in Python probes from ProbeRegistry.default().

    These probes use dynamic canary tokens for injection and disclosure-structure
    patterns for extraction — validating the full pipeline end-to-end.
    """

    async def test_builtin_probes_detect_vulnerable_page(self, demo_server, channel_factory):
        """Built-in probes should detect vulnerabilities on the vulnerable demo page."""
        registry = ProbeRegistry.default()

        config = AssessmentConfig(workers=1)
        assessor = LlmAssessor(
            config=config,
            channel_factory=channel_factory,
            registry=registry,
        )

        url = f"{demo_server}/interactive/vulnerable-llm.html"
        result = await assessor.assess(url)

        assert result.summary.total_probes == 47, (
            "Should run all 47 built-in probes"
        )
        assert result.summary.vulnerabilities_found > 0, (
            "Vulnerable page should trigger at least one built-in probe"
        )

        # At least one extraction probe should detect a system prompt leak
        extraction_results = [
            pr for pr in result.probe_results
            if pr.probe_name.startswith("extraction.")
        ]
        extraction_vulns = [pr for pr in extraction_results if pr.vulnerability_detected]
        assert len(extraction_vulns) > 0, (
            "At least one extraction probe should detect system prompt disclosure"
        )

        # At least one system_prompt_leak probe should detect behavioral leakage
        leak_results = [
            pr for pr in result.probe_results
            if pr.probe_name.startswith("system_prompt_leak.")
        ]
        leak_vulns = [pr for pr in leak_results if pr.vulnerability_detected]
        assert len(leak_vulns) > 0, (
            "At least one system_prompt_leak probe should detect behavioral leakage"
        )

        # At least one output_safety probe should detect dangerous output
        output_results = [
            pr for pr in result.probe_results
            if pr.probe_name.startswith("output_safety.")
        ]
        output_vulns = [pr for pr in output_results if pr.vulnerability_detected]
        assert len(output_vulns) > 0, (
            "At least one output_safety probe should detect dangerous web output"
        )

        # Verify exchange structure for detected vulnerabilities
        for pr in extraction_vulns + leak_vulns + output_vulns:
            assert pr.conversations_run > 0
            assert len(pr.exchanges) > 0
            assert len(pr.matched_patterns) > 0

    async def test_builtin_probes_safe_page_clean(self, demo_server, channel_factory):
        """Built-in probes should find no vulnerabilities on the safe demo page."""
        registry = ProbeRegistry.default()

        config = AssessmentConfig(workers=1)
        assessor = LlmAssessor(
            config=config,
            channel_factory=channel_factory,
            registry=registry,
        )

        url = f"{demo_server}/interactive/safe-llm.html"
        result = await assessor.assess(url)

        assert result.summary.total_probes == 47
        assert result.summary.vulnerabilities_found == 0, (
            "Safe page should not trigger any built-in probes"
        )
        # All probes should have actually executed
        for pr in result.probe_results:
            assert pr.conversations_run > 0, (
                f"Probe '{pr.probe_name}' should have run conversations"
            )

    async def test_canary_probes_no_false_positive_on_reverse(
        self, demo_server, channel_factory
    ):
        """Canary-based probes should NOT false-positive on the reverse page.

        The reverse page echoes reversed input — canary anti-echo design ensures
        that the reversed canary parts don't match the detector pattern.
        Tests injection, jailbreak, and role confusion probes.
        """
        from webagentaudit.assessment.probes.categories import (
            ContextSwitchProbe,
            DanPersonaProbe,
            DelimiterInjectionProbe,
            DirectOverrideProbe,
            IdentityOverrideProbe,
            SudoModeProbe,
        )

        registry = ProbeRegistry()
        for probe_cls in [
            DirectOverrideProbe, ContextSwitchProbe, DelimiterInjectionProbe,
            DanPersonaProbe, SudoModeProbe, IdentityOverrideProbe,
        ]:
            registry.register(probe_cls())

        config = AssessmentConfig(workers=1)
        assessor = LlmAssessor(
            config=config,
            channel_factory=channel_factory,
            registry=registry,
        )

        url = f"{demo_server}/interactive/reverse-llm.html"
        result = await assessor.assess(url)

        assert result.summary.vulnerabilities_found == 0, (
            "Canary-based probes should not false-positive on reverse/echo pages"
        )
