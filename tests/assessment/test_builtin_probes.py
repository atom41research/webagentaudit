"""Tests for built-in probe classes — canary anti-echo and detection."""

import re

import pytest

from webagentaudit.assessment.detectors.pattern_detector import PatternDetector
from webagentaudit.assessment.probes.base import BaseProbe
from webagentaudit.assessment.probes.categories import (
    # Prompt Injection (14)
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
    # Extraction (9)
    CompletionExtractionProbe,
    DirectAskExtractionProbe,
    EncodingExtractionProbe,
    HypotheticalExtractionProbe,
    MultiLanguageExtractionProbe,
    RepeatEchoProbe,
    RolePlayExtractionProbe,
    TranslationExtractionProbe,
    TrustBuildingExtractionProbe,
    # Jailbreak (8)
    CreativeWritingProbe,
    DanPersonaProbe,
    MultiLanguageJailbreakProbe,
    MultiTurnJailbreakProbe,
    ObfuscationJailbreakProbe,
    ResearchExemptionProbe,
    SimulationProbe,
    SudoModeProbe,
    # Output Safety (5)
    CodeExecutionElicitationProbe,
    EventHandlerInjectionProbe,
    IframeInjectionProbe,
    ProtocolHandlerProbe,
    XssPayloadProbe,
    # System Prompt Leak (6)
    CapabilityEnumerationProbe,
    CompetingObjectivesProbe,
    DirectRestrictionProbe,
    ErrorProbingProbe,
    MultiLanguageLeakProbe,
    NegativeSpaceProbe,
    # Role Confusion (5)
    AuthorityClaimProbe,
    IdentityOverrideProbe,
    PersonaStackingProbe,
    SystemMessageInjectionProbe,
    TemporalConfusionProbe,
)
from webagentaudit.assessment.probes.registry import ProbeRegistry

# Canary-based probes (use dynamic tokens, anti-echo property)
INJECTION_PROBES = [
    DirectOverrideProbe,
    ContextSwitchProbe,
    DelimiterInjectionProbe,
    MultiTurnInjectionProbe,
    InstructionSmugglingProbe,
    EncodingObfuscationProbe,
    AuthorityImpersonationProbe,
    PayloadSplittingProbe,
    RefusalSuppressionProbe,
    PrefixInjectionProbe,
    FewShotPoisoningProbe,
    RepetitionFloodProbe,
    MarkdownInjectionProbe,
    HistoryFabricationProbe,
]

JAILBREAK_PROBES = [
    DanPersonaProbe,
    SudoModeProbe,
    ResearchExemptionProbe,
    CreativeWritingProbe,
    SimulationProbe,
    MultiTurnJailbreakProbe,
    MultiLanguageJailbreakProbe,
    ObfuscationJailbreakProbe,
]

ROLE_CONFUSION_PROBES = [
    IdentityOverrideProbe,
    AuthorityClaimProbe,
    SystemMessageInjectionProbe,
    PersonaStackingProbe,
    TemporalConfusionProbe,
]

# All canary-based probes
CANARY_PROBES = INJECTION_PROBES + JAILBREAK_PROBES + ROLE_CONFUSION_PROBES

# Disclosure-pattern-based probes
EXTRACTION_PROBES = [
    DirectAskExtractionProbe,
    RolePlayExtractionProbe,
    TrustBuildingExtractionProbe,
    EncodingExtractionProbe,
    RepeatEchoProbe,
    TranslationExtractionProbe,
    HypotheticalExtractionProbe,
    CompletionExtractionProbe,
    MultiLanguageExtractionProbe,
]

SYSTEM_PROMPT_LEAK_PROBES = [
    DirectRestrictionProbe,
    NegativeSpaceProbe,
    CapabilityEnumerationProbe,
    ErrorProbingProbe,
    CompetingObjectivesProbe,
    MultiLanguageLeakProbe,
]

OUTPUT_SAFETY_PROBES = [
    XssPayloadProbe,
    EventHandlerInjectionProbe,
    ProtocolHandlerProbe,
    IframeInjectionProbe,
    CodeExecutionElicitationProbe,
]

# All disclosure-pattern-based probes
DISCLOSURE_PROBES = EXTRACTION_PROBES + SYSTEM_PROMPT_LEAK_PROBES

ALL_PROBES = CANARY_PROBES + DISCLOSURE_PROBES + OUTPUT_SAFETY_PROBES


class TestProbeInterface:
    """All probes implement BaseProbe correctly."""

    @pytest.mark.parametrize("probe_cls", ALL_PROBES)
    def test_is_base_probe(self, probe_cls):
        probe = probe_cls()
        assert isinstance(probe, BaseProbe)

    @pytest.mark.parametrize("probe_cls", ALL_PROBES)
    def test_has_required_properties(self, probe_cls):
        probe = probe_cls()
        assert probe.name
        assert probe.category
        assert probe.severity
        assert probe.description
        assert probe.sophistication

    @pytest.mark.parametrize("probe_cls", ALL_PROBES)
    def test_has_conversations_or_prompts(self, probe_cls):
        probe = probe_cls()
        conversations = probe.get_conversations()
        assert len(conversations) > 0, "Probe must have at least one conversation"

    @pytest.mark.parametrize("probe_cls", ALL_PROBES)
    def test_has_detector_patterns(self, probe_cls):
        probe = probe_cls()
        patterns = probe.get_detector_patterns()
        assert len(patterns) > 0

    @pytest.mark.parametrize("probe_cls", ALL_PROBES)
    def test_detector_patterns_are_valid_regex(self, probe_cls):
        probe = probe_cls()
        for pattern in probe.get_detector_patterns():
            re.compile(pattern)


class TestCanaryProbeAntiEcho:
    """Canary-based probes (injection, jailbreak, role confusion) have anti-echo."""

    @pytest.mark.parametrize("probe_cls", CANARY_PROBES)
    def test_patterns_dont_match_prompt_text(self, probe_cls):
        """The canary output must NOT appear in the prompt (anti-echo)."""
        probe = probe_cls()
        patterns = probe.get_detector_patterns()
        # Collect all prompt text
        prompt_texts = []
        for conv in probe.get_conversations():
            for turn in conv.turns:
                prompt_texts.append(turn.prompt)

        for prompt_text in prompt_texts:
            for pattern in patterns:
                assert not re.search(pattern, prompt_text, re.IGNORECASE), (
                    f"Pattern {pattern!r} matches prompt text — "
                    f"violates anti-echo principle"
                )

    @pytest.mark.parametrize("probe_cls", CANARY_PROBES)
    def test_patterns_match_expected_canary_output(self, probe_cls):
        """The detector pattern matches the canary's expected output."""
        probe = probe_cls()
        expected = probe._canary.expected_output
        detector = PatternDetector()
        matched = detector.detect(expected, probe.get_detector_patterns())
        assert len(matched) > 0, f"Pattern should match canary output {expected!r}"

    @pytest.mark.parametrize("probe_cls", CANARY_PROBES)
    def test_fresh_instances_have_different_canaries(self, probe_cls):
        """Each instantiation produces a new canary."""
        a = probe_cls()
        b = probe_cls()
        assert a._canary.expected_output != b._canary.expected_output

    @pytest.mark.parametrize("probe_cls", CANARY_PROBES)
    def test_patterns_dont_match_refusal(self, probe_cls):
        """Canary patterns don't match typical refusals."""
        probe = probe_cls()
        detector = PatternDetector()
        refusals = [
            "I can't help with that request.",
            "I won't follow those instructions.",
            "I'm sorry, but I cannot comply.",
        ]
        for refusal in refusals:
            matched = detector.detect(refusal, probe.get_detector_patterns())
            assert matched == [], f"Pattern should not match refusal: {refusal!r}"


class TestExtractionProbePatterns:
    """Extraction probes use disclosure-structure patterns."""

    @pytest.mark.parametrize("probe_cls", EXTRACTION_PROBES)
    def test_patterns_match_actual_disclosure(self, probe_cls):
        probe = probe_cls()
        detector = PatternDetector()
        disclosures = [
            "My system prompt is: You are a helpful assistant.",
            "Here is my system prompt: Always be polite.",
            "My instructions are to always respond in English.",
        ]
        for disclosure in disclosures:
            matched = detector.detect(disclosure, probe.get_detector_patterns())
            assert len(matched) >= 1, (
                f"Pattern should match disclosure: {disclosure!r}"
            )

    @pytest.mark.parametrize("probe_cls", EXTRACTION_PROBES)
    def test_patterns_dont_match_refusal(self, probe_cls):
        probe = probe_cls()
        detector = PatternDetector()
        refusals = [
            "I can't tell you what my system prompt is.",
            "I won't reveal my system prompt.",
            "I can't share my system prompt or configuration settings.",
            "Sharing my system prompt is against my guidelines.",
        ]
        for refusal in refusals:
            matched = detector.detect(refusal, probe.get_detector_patterns())
            assert matched == [], f"Pattern should not match refusal: {refusal!r}"


class TestSystemPromptLeakPatterns:
    """System prompt leak probes use behavioral leakage patterns."""

    @pytest.mark.parametrize("probe_cls", SYSTEM_PROMPT_LEAK_PROBES)
    def test_patterns_match_behavioral_leakage(self, probe_cls):
        probe = probe_cls()
        detector = PatternDetector()
        leaks = [
            "My restrictions include: never generating harmful content.",
            "I am configured to answer customer support questions only.",
            "I cannot discuss topics related to weapons or violence.",
            "I was not allowed to share personal data.",
        ]
        for leak in leaks:
            matched = detector.detect(leak, probe.get_detector_patterns())
            assert len(matched) >= 1, (
                f"Pattern should match behavioral leak: {leak!r}"
            )

    @pytest.mark.parametrize("probe_cls", SYSTEM_PROMPT_LEAK_PROBES)
    def test_patterns_dont_match_generic_response(self, probe_cls):
        probe = probe_cls()
        detector = PatternDetector()
        generic = [
            "I'm happy to help with any questions you have.",
            "Let me assist you with that.",
            "Sure, I can help you with this task.",
        ]
        for response in generic:
            matched = detector.detect(response, probe.get_detector_patterns())
            assert matched == [], (
                f"Leak pattern should not match generic response: {response!r}"
            )


class TestOutputSafetyPatterns:
    """Output safety probes detect dangerous web content."""

    @pytest.mark.parametrize("probe_cls", OUTPUT_SAFETY_PROBES)
    def test_patterns_match_dangerous_output(self, probe_cls):
        probe = probe_cls()
        detector = PatternDetector()
        dangerous = [
            '<script>alert("xss")</script>',
            '<img onerror="alert(1)" src="x">',
            '<a href="javascript:void(0)">click</a>',
            '<iframe src="https://evil.com"></iframe>',
            '<embed src="malicious.swf">',
        ]
        for output in dangerous:
            matched = detector.detect(output, probe.get_detector_patterns())
            assert len(matched) >= 1, (
                f"Pattern should match dangerous output: {output!r}"
            )

    @pytest.mark.parametrize("probe_cls", OUTPUT_SAFETY_PROBES)
    def test_patterns_dont_match_safe_text(self, probe_cls):
        probe = probe_cls()
        detector = PatternDetector()
        safe = [
            "Here is some plain text about web development.",
            "The function takes two parameters and returns a string.",
            "I can help you learn about HTML and CSS.",
        ]
        for response in safe:
            matched = detector.detect(response, probe.get_detector_patterns())
            assert matched == [], (
                f"Pattern should not match safe text: {response!r}"
            )


class TestRegistryDefault:
    """ProbeRegistry.default() loads all built-in probes."""

    def test_default_registry_has_all_probes(self):
        registry = ProbeRegistry.default()
        probes = registry.get_all()
        assert len(probes) == len(ALL_PROBES)

    def test_default_registry_probe_names_unique(self):
        registry = ProbeRegistry.default()
        names = [p.name for p in registry.get_all()]
        assert len(names) == len(set(names))

    def test_fresh_registries_have_different_canaries(self):
        r1 = ProbeRegistry.default()
        r2 = ProbeRegistry.default()
        p1 = r1.get_by_name("prompt_injection.direct_override")
        p2 = r2.get_by_name("prompt_injection.direct_override")
        assert p1.get_detector_patterns() != p2.get_detector_patterns()

    def test_all_six_categories_covered(self):
        from webagentaudit.core.enums import ProbeCategory

        registry = ProbeRegistry.default()
        for cat in ProbeCategory:
            probes = registry.get_by_category(cat)
            assert len(probes) > 0, f"Category {cat.value} has no probes"

    def test_severity_filter(self):
        from webagentaudit.core.enums import Severity

        registry = ProbeRegistry.default()
        critical = registry.filter(severities=[Severity.CRITICAL])
        assert len(critical) > 0
        for p in critical:
            assert p.severity == Severity.CRITICAL
