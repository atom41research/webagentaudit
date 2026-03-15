"""Probe registry for discovering and filtering probes."""

from pathlib import Path

from webagentaudit.core.enums import ProbeCategory, Severity, Sophistication

from .base import BaseProbe


class ProbeRegistry:
    """Registry for managing and querying assessment probes.

    Probes are registered explicitly (no import-time magic) for
    debuggability and control.
    """

    def __init__(self) -> None:
        self._probes: dict[str, BaseProbe] = {}

    def register(self, probe: BaseProbe) -> None:
        """Register a probe instance. Overwrites if name already exists."""
        self._probes[probe.name] = probe

    def get_all(self) -> list[BaseProbe]:
        """Return all registered probes."""
        return list(self._probes.values())

    def get_by_category(self, category: ProbeCategory) -> list[BaseProbe]:
        """Return probes matching the given category."""
        return [p for p in self._probes.values() if p.category == category]

    def get_by_name(self, name: str) -> BaseProbe | None:
        """Return a probe by name, or None if not found."""
        return self._probes.get(name)

    def get_by_severity(self, severity: Severity) -> list[BaseProbe]:
        """Return probes matching the given severity."""
        return [p for p in self._probes.values() if p.severity == severity]

    def get_by_sophistication(
        self, sophistication: Sophistication
    ) -> list[BaseProbe]:
        """Return probes matching the given sophistication level."""
        return [
            p for p in self._probes.values()
            if p.sophistication == sophistication
        ]

    def load_yaml_dir(self, directory: Path) -> int:
        """Load all YAML probes from a directory and register them.

        Returns:
            Number of probes loaded.
        """
        from .yaml_loader import load_yaml_probes

        probes = load_yaml_probes(directory)
        for probe in probes:
            self.register(probe)
        return len(probes)

    def load_yaml_file(self, path: Path) -> None:
        """Load a single YAML probe file and register it.

        Raises:
            YamlProbeLoadError: If the file cannot be loaded.
        """
        from .yaml_loader import load_yaml_probe

        probe = load_yaml_probe(path)
        self.register(probe)

    def filter(
        self,
        *,
        categories: list[ProbeCategory] | None = None,
        severities: list[Severity] | None = None,
        sophistication_levels: list[Sophistication] | None = None,
        names: list[str] | None = None,
    ) -> list[BaseProbe]:
        """Return probes matching all provided filters (AND logic)."""
        probes = list(self._probes.values())
        if names:
            probes = [p for p in probes if p.name in names]
        if categories:
            probes = [p for p in probes if p.category in categories]
        if severities:
            probes = [p for p in probes if p.severity in severities]
        if sophistication_levels:
            probes = [p for p in probes if p.sophistication in sophistication_levels]
        return probes

    @classmethod
    def default(cls) -> "ProbeRegistry":
        """Create a registry pre-loaded with all built-in probes.

        Each call creates fresh probe instances — canary-based probes
        generate new random tokens per instantiation.
        """
        from .categories import (
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

        registry = cls()
        for probe_cls in [
            # Prompt Injection
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
            # Extraction
            DirectAskExtractionProbe,
            RolePlayExtractionProbe,
            TrustBuildingExtractionProbe,
            EncodingExtractionProbe,
            RepeatEchoProbe,
            TranslationExtractionProbe,
            HypotheticalExtractionProbe,
            CompletionExtractionProbe,
            MultiLanguageExtractionProbe,
            # Jailbreak
            DanPersonaProbe,
            SudoModeProbe,
            ResearchExemptionProbe,
            CreativeWritingProbe,
            SimulationProbe,
            MultiTurnJailbreakProbe,
            MultiLanguageJailbreakProbe,
            ObfuscationJailbreakProbe,
            # Output Safety
            XssPayloadProbe,
            EventHandlerInjectionProbe,
            ProtocolHandlerProbe,
            IframeInjectionProbe,
            CodeExecutionElicitationProbe,
            # System Prompt Leak
            DirectRestrictionProbe,
            NegativeSpaceProbe,
            CapabilityEnumerationProbe,
            ErrorProbingProbe,
            CompetingObjectivesProbe,
            MultiLanguageLeakProbe,
            # Role Confusion
            IdentityOverrideProbe,
            AuthorityClaimProbe,
            SystemMessageInjectionProbe,
            PersonaStackingProbe,
            TemporalConfusionProbe,
        ]:
            registry.register(probe_cls())
        return registry
