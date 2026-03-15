"""Probe category implementations."""

from .extraction import (
    CompletionExtractionProbe,
    DirectAskExtractionProbe,
    EncodingExtractionProbe,
    HypotheticalExtractionProbe,
    MultiLanguageExtractionProbe,
    RepeatEchoProbe,
    RolePlayExtractionProbe,
    TranslationExtractionProbe,
    TrustBuildingExtractionProbe,
)
from .jailbreak import (
    CreativeWritingProbe,
    DanPersonaProbe,
    MultiLanguageJailbreakProbe,
    MultiTurnJailbreakProbe,
    ObfuscationJailbreakProbe,
    ResearchExemptionProbe,
    SimulationProbe,
    SudoModeProbe,
)
from .output_safety import (
    CodeExecutionElicitationProbe,
    EventHandlerInjectionProbe,
    IframeInjectionProbe,
    ProtocolHandlerProbe,
    XssPayloadProbe,
)
from .prompt_injection import (
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
)
from .role_confusion import (
    AuthorityClaimProbe,
    IdentityOverrideProbe,
    PersonaStackingProbe,
    SystemMessageInjectionProbe,
    TemporalConfusionProbe,
)
from .system_prompt_leak import (
    CapabilityEnumerationProbe,
    CompetingObjectivesProbe,
    DirectRestrictionProbe,
    ErrorProbingProbe,
    MultiLanguageLeakProbe,
    NegativeSpaceProbe,
)

__all__ = [
    # Prompt Injection (14)
    "AuthorityImpersonationProbe",
    "ContextSwitchProbe",
    "DelimiterInjectionProbe",
    "DirectOverrideProbe",
    "EncodingObfuscationProbe",
    "FewShotPoisoningProbe",
    "HistoryFabricationProbe",
    "InstructionSmugglingProbe",
    "MarkdownInjectionProbe",
    "MultiTurnInjectionProbe",
    "PayloadSplittingProbe",
    "PrefixInjectionProbe",
    "RefusalSuppressionProbe",
    "RepetitionFloodProbe",
    # Extraction (9)
    "CompletionExtractionProbe",
    "DirectAskExtractionProbe",
    "EncodingExtractionProbe",
    "HypotheticalExtractionProbe",
    "MultiLanguageExtractionProbe",
    "RepeatEchoProbe",
    "RolePlayExtractionProbe",
    "TranslationExtractionProbe",
    "TrustBuildingExtractionProbe",
    # Jailbreak (8)
    "CreativeWritingProbe",
    "DanPersonaProbe",
    "MultiLanguageJailbreakProbe",
    "MultiTurnJailbreakProbe",
    "ObfuscationJailbreakProbe",
    "ResearchExemptionProbe",
    "SimulationProbe",
    "SudoModeProbe",
    # Output Safety (5)
    "CodeExecutionElicitationProbe",
    "EventHandlerInjectionProbe",
    "IframeInjectionProbe",
    "ProtocolHandlerProbe",
    "XssPayloadProbe",
    # System Prompt Leak (6)
    "CapabilityEnumerationProbe",
    "CompetingObjectivesProbe",
    "DirectRestrictionProbe",
    "ErrorProbingProbe",
    "MultiLanguageLeakProbe",
    "NegativeSpaceProbe",
    # Role Confusion (5)
    "AuthorityClaimProbe",
    "IdentityOverrideProbe",
    "PersonaStackingProbe",
    "SystemMessageInjectionProbe",
    "TemporalConfusionProbe",
]
