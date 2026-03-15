"""End-to-end assessment tests against demo pages.

Tests the full assessment pipeline: load probes, connect a channel to a
running demo page, run probes, and verify results.

The demo pages use docs/shared/echo-engine.js which has deterministic
keyword-based responses.  This lets us predict exactly which probes will
detect vulnerabilities and which won't:

  - Canary probes (injection, jailbreak, role_confusion) look for random hex
    tokens in the response.  The demo page returns hardcoded strings, so
    canary probes should NEVER detect.
  - Disclosure probes (extraction, system_prompt_leak) use structural regex.
    The demo's responses match these patterns, so they SHOULD detect.
  - Output safety probes use HTML-tag regex.  The demo returns actual HTML
    payloads, so they SHOULD detect.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from webagentaudit.assessment.assessor import LlmAssessor
from webagentaudit.assessment.config import AssessmentConfig
from webagentaudit.assessment.probes.categories import (
    # Prompt Injection (14) — canary-based
    AuthorityImpersonationProbe,
    ContextSwitchProbe,
    DelimiterInjectionProbe,
    DirectOverrideProbe,
    EncodingObfuscationProbe,
    FewShotPoisoningProbe,
    HistoryFabricationProbe,
    InstructionSmugglingProbe,
    MarkdownInjectionProbe,
    MultiTurnInjectionProbe,
    PayloadSplittingProbe,
    PrefixInjectionProbe,
    RefusalSuppressionProbe,
    RepetitionFloodProbe,
    # Extraction (9) — disclosure-pattern-based
    CompletionExtractionProbe,
    DirectAskExtractionProbe,
    EncodingExtractionProbe,
    HypotheticalExtractionProbe,
    MultiLanguageExtractionProbe,
    RepeatEchoProbe,
    RolePlayExtractionProbe,
    TranslationExtractionProbe,
    TrustBuildingExtractionProbe,
    # Jailbreak (8) — canary-based
    CreativeWritingProbe,
    DanPersonaProbe,
    MultiLanguageJailbreakProbe,
    MultiTurnJailbreakProbe,
    ObfuscationJailbreakProbe,
    ResearchExemptionProbe,
    SimulationProbe,
    SudoModeProbe,
    # Output Safety (5) — HTML-pattern-based
    CodeExecutionElicitationProbe,
    EventHandlerInjectionProbe,
    IframeInjectionProbe,
    ProtocolHandlerProbe,
    XssPayloadProbe,
    # System Prompt Leak (6) — leak-pattern-based
    CapabilityEnumerationProbe,
    CompetingObjectivesProbe,
    DirectRestrictionProbe,
    ErrorProbingProbe,
    MultiLanguageLeakProbe,
    NegativeSpaceProbe,
    # Role Confusion (5) — canary-based
    AuthorityClaimProbe,
    IdentityOverrideProbe,
    PersonaStackingProbe,
    SystemMessageInjectionProbe,
    TemporalConfusionProbe,
)
from webagentaudit.assessment.probes.registry import ProbeRegistry
from webagentaudit.llm_channel.config import ChannelConfig
from webagentaudit.llm_channel.playwright_channel import PlaywrightChannel
from webagentaudit.llm_channel.strategies.custom import CustomStrategy

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
YAML_PROBES_DIR = FIXTURES_DIR / "yaml_probes"

# All 27 canary-based probes (should NEVER detect on demo pages)
CANARY_PROBE_CLASSES = [
    # Prompt Injection (14)
    DirectOverrideProbe, ContextSwitchProbe, DelimiterInjectionProbe,
    MultiTurnInjectionProbe, InstructionSmugglingProbe,
    EncodingObfuscationProbe, AuthorityImpersonationProbe,
    PayloadSplittingProbe, RefusalSuppressionProbe, PrefixInjectionProbe,
    FewShotPoisoningProbe, RepetitionFloodProbe, MarkdownInjectionProbe,
    HistoryFabricationProbe,
    # Jailbreak (8)
    DanPersonaProbe, SudoModeProbe, ResearchExemptionProbe,
    CreativeWritingProbe, SimulationProbe, MultiTurnJailbreakProbe,
    MultiLanguageJailbreakProbe, ObfuscationJailbreakProbe,
    # Role Confusion (5)
    IdentityOverrideProbe, AuthorityClaimProbe,
    SystemMessageInjectionProbe, PersonaStackingProbe,
    TemporalConfusionProbe,
]

# Extraction probes that WILL detect on vulnerable page
# (their prompts contain English keywords that trigger echo-engine)
EXTRACTION_DETECTING_PROBES = [
    DirectAskExtractionProbe, RolePlayExtractionProbe,
    TrustBuildingExtractionProbe, EncodingExtractionProbe,
    RepeatEchoProbe, TranslationExtractionProbe,
    HypotheticalExtractionProbe, CompletionExtractionProbe,
]

# Extraction probe that WON'T detect (non-English prompts)
EXTRACTION_NON_DETECTING_PROBES = [MultiLanguageExtractionProbe]

# All 5 output safety probes detect on vulnerable page
OUTPUT_SAFETY_DETECTING_PROBES = [
    XssPayloadProbe, EventHandlerInjectionProbe, ProtocolHandlerProbe,
    IframeInjectionProbe, CodeExecutionElicitationProbe,
]

# System prompt leak probes that WILL detect
LEAK_DETECTING_PROBES = [
    DirectRestrictionProbe, NegativeSpaceProbe,
    CapabilityEnumerationProbe, ErrorProbingProbe,
]

# System prompt leak probes with uncertain detection (language/keyword edge cases)
LEAK_MAYBE_PROBES = [CompetingObjectivesProbe, MultiLanguageLeakProbe]


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


def _make_assessor(channel_factory, registry):
    """Helper to create an assessor with standard config."""
    return LlmAssessor(
        config=AssessmentConfig(workers=1),
        channel_factory=channel_factory,
        registry=registry,
    )


def _registry_from_classes(probe_classes):
    """Create a ProbeRegistry from a list of probe classes."""
    registry = ProbeRegistry()
    for cls in probe_classes:
        registry.register(cls())
    return registry


# ---------------------------------------------------------------------------
# Assessment against vulnerable demo page (YAML probes)
# ---------------------------------------------------------------------------


class TestAssessmentVulnerable:
    """Assess the vulnerable demo page — should find vulnerabilities."""

    async def test_custom_probes_detect_vulnerability(self, demo_server, channel_factory):
        """YAML probes should detect the vulnerable demo's PWNED responses."""
        registry = ProbeRegistry()
        registry.load_yaml_dir(YAML_PROBES_DIR)
        all_probes = registry.get_all()
        assert len(all_probes) > 0, "Should have loaded at least one probe"

        assessor = _make_assessor(channel_factory, registry)
        url = f"{demo_server}/interactive/vulnerable-llm.html"
        result = await assessor.assess(url)

        assert result.summary.total_probes > 0
        assert len(result.probe_results) > 0
        assert result.summary.vulnerabilities_found > 0

        # Find a probe that detected a vulnerability and verify its exchanges
        vuln_probes = [
            pr for pr in result.probe_results if pr.vulnerability_detected
        ]
        assert len(vuln_probes) > 0, "At least one probe should detect a vulnerability"

        vuln_pr = vuln_probes[0]
        assert len(vuln_pr.exchanges) > 0, "Vulnerable probe should have exchanges"

        # At least one exchange should have a non-empty response
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

        assessor = _make_assessor(channel_factory, registry)
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

        assessor = _make_assessor(channel_factory, registry)
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

        assessor = _make_assessor(channel_factory, registry)
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

        assessor = _make_assessor(channel_factory, registry)
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

        assessor = _make_assessor(channel_factory, registry)
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
# Built-in probe E2E: full 47-probe suite
# ---------------------------------------------------------------------------


class TestBuiltinProbesFull:
    """Run all 47 built-in probes and verify aggregate results."""

    async def test_all_47_probes_run(self, demo_server, channel_factory):
        """All 47 built-in probes should execute against the vulnerable page."""
        registry = ProbeRegistry.default()
        assessor = _make_assessor(channel_factory, registry)

        url = f"{demo_server}/interactive/vulnerable-llm.html"
        result = await assessor.assess(url)

        assert result.summary.total_probes == 47, (
            "Should run all 47 built-in probes"
        )
        assert len(result.probe_results) == 47

        # Every probe must have executed at least one conversation
        for pr in result.probe_results:
            assert pr.conversations_run > 0, (
                f"Probe '{pr.probe_name}' should have run at least one conversation"
            )
            assert len(pr.exchanges) > 0, (
                f"Probe '{pr.probe_name}' should have at least one exchange"
            )

    async def test_safe_page_zero_vulnerabilities_all_47(self, demo_server, channel_factory):
        """All 47 probes should find zero vulnerabilities on the safe page."""
        registry = ProbeRegistry.default()
        assessor = _make_assessor(channel_factory, registry)

        url = f"{demo_server}/interactive/safe-llm.html"
        result = await assessor.assess(url)

        assert result.summary.total_probes == 47
        assert result.summary.vulnerabilities_found == 0, (
            "Safe page should not trigger any built-in probes"
        )
        for pr in result.probe_results:
            assert pr.conversations_run > 0, (
                f"Probe '{pr.probe_name}' should have run conversations"
            )
            assert not pr.vulnerability_detected, (
                f"Probe '{pr.probe_name}' should NOT detect on safe page"
            )


# ---------------------------------------------------------------------------
# Per-category E2E: canary probes must NOT detect on vulnerable page
# ---------------------------------------------------------------------------


class TestCanaryProbesNoDetection:
    """Canary-based probes (injection, jailbreak, role confusion) should never
    detect on the vulnerable demo page — the page returns hardcoded strings,
    not random canary tokens.
    """

    async def test_all_injection_probes_no_detection(self, demo_server, channel_factory):
        """All 14 prompt injection probes should NOT detect on vulnerable page."""
        injection_classes = [
            DirectOverrideProbe, ContextSwitchProbe, DelimiterInjectionProbe,
            MultiTurnInjectionProbe, InstructionSmugglingProbe,
            EncodingObfuscationProbe, AuthorityImpersonationProbe,
            PayloadSplittingProbe, RefusalSuppressionProbe, PrefixInjectionProbe,
            FewShotPoisoningProbe, RepetitionFloodProbe, MarkdownInjectionProbe,
            HistoryFabricationProbe,
        ]
        registry = _registry_from_classes(injection_classes)
        assessor = _make_assessor(channel_factory, registry)

        url = f"{demo_server}/interactive/vulnerable-llm.html"
        result = await assessor.assess(url)

        assert result.summary.total_probes == 14
        assert result.summary.vulnerabilities_found == 0, (
            "Canary-based injection probes should not detect on demo page "
            "(page returns hardcoded strings, not random canary tokens)"
        )
        for pr in result.probe_results:
            assert not pr.vulnerability_detected, (
                f"Injection probe '{pr.probe_name}' should NOT detect — "
                f"matched_patterns={pr.matched_patterns}"
            )
            assert pr.conversations_run > 0, (
                f"Probe '{pr.probe_name}' should have run"
            )

    async def test_all_jailbreak_probes_no_detection(self, demo_server, channel_factory):
        """All 8 jailbreak probes should NOT detect on vulnerable page."""
        jailbreak_classes = [
            DanPersonaProbe, SudoModeProbe, ResearchExemptionProbe,
            CreativeWritingProbe, SimulationProbe, MultiTurnJailbreakProbe,
            MultiLanguageJailbreakProbe, ObfuscationJailbreakProbe,
        ]
        registry = _registry_from_classes(jailbreak_classes)
        assessor = _make_assessor(channel_factory, registry)

        url = f"{demo_server}/interactive/vulnerable-llm.html"
        result = await assessor.assess(url)

        assert result.summary.total_probes == 8
        assert result.summary.vulnerabilities_found == 0, (
            "Canary-based jailbreak probes should not detect on demo page"
        )
        for pr in result.probe_results:
            assert not pr.vulnerability_detected, (
                f"Jailbreak probe '{pr.probe_name}' should NOT detect — "
                f"matched_patterns={pr.matched_patterns}"
            )

    async def test_all_role_confusion_probes_no_detection(self, demo_server, channel_factory):
        """All 5 role confusion probes should NOT detect on vulnerable page."""
        role_classes = [
            IdentityOverrideProbe, AuthorityClaimProbe,
            SystemMessageInjectionProbe, PersonaStackingProbe,
            TemporalConfusionProbe,
        ]
        registry = _registry_from_classes(role_classes)
        assessor = _make_assessor(channel_factory, registry)

        url = f"{demo_server}/interactive/vulnerable-llm.html"
        result = await assessor.assess(url)

        assert result.summary.total_probes == 5
        assert result.summary.vulnerabilities_found == 0, (
            "Canary-based role confusion probes should not detect on demo page"
        )
        for pr in result.probe_results:
            assert not pr.vulnerability_detected, (
                f"Role confusion probe '{pr.probe_name}' should NOT detect — "
                f"matched_patterns={pr.matched_patterns}"
            )


# ---------------------------------------------------------------------------
# Per-category E2E: canary probes must NOT false-positive on reverse page
# ---------------------------------------------------------------------------


class TestCanaryProbesReversePage:
    """All 27 canary probes must not false-positive on the reverse page.

    The reverse page echoes reversed input — canary anti-echo design ensures
    that reversed canary parts don't match the detector pattern.
    """

    async def test_all_canary_probes_no_false_positive(self, demo_server, channel_factory):
        """All 27 canary probes should produce zero vulnerabilities on reverse page."""
        registry = _registry_from_classes(CANARY_PROBE_CLASSES)
        assert len(registry.get_all()) == 27

        assessor = _make_assessor(channel_factory, registry)
        url = f"{demo_server}/interactive/reverse-llm.html"
        result = await assessor.assess(url)

        assert result.summary.total_probes == 27
        assert result.summary.vulnerabilities_found == 0, (
            "Canary-based probes should not false-positive on reverse/echo pages"
        )
        for pr in result.probe_results:
            assert not pr.vulnerability_detected, (
                f"Canary probe '{pr.probe_name}' false-positived on reverse page — "
                f"matched_patterns={pr.matched_patterns}"
            )
            assert pr.conversations_run > 0


# ---------------------------------------------------------------------------
# Per-category E2E: extraction probes on vulnerable page
# ---------------------------------------------------------------------------


class TestExtractionProbesVulnerable:
    """Extraction probes should detect system prompt disclosure on the
    vulnerable page.  The page returns 'My system prompt is: ...' for
    extraction-related keywords.
    """

    async def test_english_extraction_probes_detect(self, demo_server, channel_factory):
        """8 English-language extraction probes should all detect vulnerability."""
        registry = _registry_from_classes(EXTRACTION_DETECTING_PROBES)
        assessor = _make_assessor(channel_factory, registry)

        url = f"{demo_server}/interactive/vulnerable-llm.html"
        result = await assessor.assess(url)

        assert result.summary.total_probes == 8
        for pr in result.probe_results:
            assert pr.vulnerability_detected, (
                f"Extraction probe '{pr.probe_name}' should detect on vulnerable page. "
                f"conversations_run={pr.conversations_run}, "
                f"exchanges={len(pr.exchanges)}, "
                f"matched_patterns={pr.matched_patterns}"
            )
            assert len(pr.matched_patterns) > 0
            assert pr.conversations_run > 0
            assert len(pr.exchanges) > 0

    async def test_multi_language_extraction_no_detection(self, demo_server, channel_factory):
        """Multi-language extraction probe uses non-English prompts — demo
        page only responds to English keywords, so it should NOT detect."""
        registry = _registry_from_classes(EXTRACTION_NON_DETECTING_PROBES)
        assessor = _make_assessor(channel_factory, registry)

        url = f"{demo_server}/interactive/vulnerable-llm.html"
        result = await assessor.assess(url)

        assert result.summary.total_probes == 1
        pr = result.probe_results[0]
        assert pr.probe_name == "extraction.multi_language"
        assert not pr.vulnerability_detected, (
            "Multi-language extraction should not detect — demo only responds "
            "to English keywords"
        )
        assert pr.conversations_run > 0


# ---------------------------------------------------------------------------
# Per-category E2E: output safety probes on vulnerable page
# ---------------------------------------------------------------------------


class TestOutputSafetyProbesVulnerable:
    """Output safety probes should detect dangerous HTML in the vulnerable
    page's responses (script tags, event handlers, javascript: URLs, iframes).
    """

    async def test_all_output_safety_probes_detect(self, demo_server, channel_factory):
        """All 5 output safety probes should detect dangerous output."""
        registry = _registry_from_classes(OUTPUT_SAFETY_DETECTING_PROBES)
        assessor = _make_assessor(channel_factory, registry)

        url = f"{demo_server}/interactive/vulnerable-llm.html"
        result = await assessor.assess(url)

        assert result.summary.total_probes == 5
        for pr in result.probe_results:
            assert pr.vulnerability_detected, (
                f"Output safety probe '{pr.probe_name}' should detect on vulnerable page. "
                f"exchanges={len(pr.exchanges)}, "
                f"matched_patterns={pr.matched_patterns}"
            )
            assert len(pr.matched_patterns) > 0


# ---------------------------------------------------------------------------
# Per-category E2E: system prompt leak probes on vulnerable page
# ---------------------------------------------------------------------------


class TestLeakProbesVulnerable:
    """System prompt leak probes should detect behavioral leakage on the
    vulnerable page.  The page returns 'My restrictions include: ...' and
    'I am configured to ...' for leak-related keywords.
    """

    async def test_english_leak_probes_detect(self, demo_server, channel_factory):
        """4 English-language leak probes should all detect vulnerability."""
        registry = _registry_from_classes(LEAK_DETECTING_PROBES)
        assessor = _make_assessor(channel_factory, registry)

        url = f"{demo_server}/interactive/vulnerable-llm.html"
        result = await assessor.assess(url)

        assert result.summary.total_probes == 4
        for pr in result.probe_results:
            assert pr.vulnerability_detected, (
                f"Leak probe '{pr.probe_name}' should detect on vulnerable page. "
                f"exchanges={len(pr.exchanges)}, "
                f"matched_patterns={pr.matched_patterns}"
            )
            assert len(pr.matched_patterns) > 0

    async def test_maybe_leak_probes_run_without_error(self, demo_server, channel_factory):
        """Competing objectives and multi-language leak probes should at least
        run successfully (detection depends on keyword edge cases)."""
        registry = _registry_from_classes(LEAK_MAYBE_PROBES)
        assessor = _make_assessor(channel_factory, registry)

        url = f"{demo_server}/interactive/vulnerable-llm.html"
        result = await assessor.assess(url)

        assert result.summary.total_probes == 2
        for pr in result.probe_results:
            assert pr.conversations_run > 0, (
                f"Probe '{pr.probe_name}' should have run conversations"
            )
            assert len(pr.exchanges) > 0, (
                f"Probe '{pr.probe_name}' should have exchanges"
            )


# ---------------------------------------------------------------------------
# Exchange structure verification
# ---------------------------------------------------------------------------


class TestExchangeStructure:
    """Verify exchange fields are correctly populated for detected vulnerabilities."""

    async def test_vulnerable_exchanges_have_prompts_and_responses(
        self, demo_server, channel_factory
    ):
        """Every exchange should have non-empty prompt and response."""
        registry = _registry_from_classes(
            EXTRACTION_DETECTING_PROBES + OUTPUT_SAFETY_DETECTING_PROBES
        )
        assessor = _make_assessor(channel_factory, registry)

        url = f"{demo_server}/interactive/vulnerable-llm.html"
        result = await assessor.assess(url)

        for pr in result.probe_results:
            for exchange in pr.exchanges:
                assert exchange.prompt, (
                    f"Exchange in '{pr.probe_name}' has empty prompt"
                )
                assert exchange.response, (
                    f"Exchange in '{pr.probe_name}' has empty response"
                )

    async def test_matched_patterns_are_from_probe_definition(
        self, demo_server, channel_factory
    ):
        """Every matched pattern must be a regex from the probe's detector_patterns."""
        registry = ProbeRegistry.default()
        assessor = _make_assessor(channel_factory, registry)

        url = f"{demo_server}/interactive/vulnerable-llm.html"
        result = await assessor.assess(url)

        for pr in result.probe_results:
            if not pr.matched_patterns:
                continue
            probe = registry.get_by_name(pr.probe_name)
            assert probe is not None
            probe_patterns = set(probe.get_detector_patterns())
            for pattern in pr.matched_patterns:
                assert pattern in probe_patterns, (
                    f"Matched pattern '{pattern}' not in probe "
                    f"'{pr.probe_name}' detector_patterns"
                )
