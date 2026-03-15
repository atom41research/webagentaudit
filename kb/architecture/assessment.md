# Assessment Module Design

**Path**: `src/webagentaudit/assessment/`

## Purpose

Assess the security posture of a web-based LLM by sending attack probes and analyzing responses. Produces an `AssessmentResult` with per-probe results and an aggregated summary.

## Data Models (`models.py`)

### ChatMessage
```python
class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str
```
Restricted role set via `Literal` prevents injection of arbitrary role strings.

### ProbeExchange
```python
class ProbeExchange(BaseModel):
    messages: list[ChatMessage]
    matched_patterns: list[str] = []
```
Convenience properties: `.prompt` (first user message), `.response` (last assistant message).

### ProbeResult
```python
class ProbeResult(BaseModel):
    probe_name: str
    conversations_run: int = 0
    vulnerability_detected: bool = False
    matched_patterns: list[str] = []
    exchanges: list[ProbeExchange] = []
    timestamp: datetime  # defaults to now(UTC)
```

### AssessmentSummary
```python
class AssessmentSummary(BaseModel):
    total_probes: int = 0
    vulnerabilities_found: int = 0
    target_url: str = ""
```

### AssessmentResult
```python
class AssessmentResult(BaseModel):
    summary: AssessmentSummary
    probe_results: list[ProbeResult] = []
    timestamp: datetime  # defaults to now(UTC)
    metadata: dict[str, Any] = {}
```

## Conversation Model (`probes/conversation.py`)

Internal dataclasses for multi-turn probe flows:

```python
@dataclass
class ConversationTurn:
    prompt: str
    detect_after: bool = True  # run detection on this turn's response

@dataclass
class Conversation:
    turns: list[ConversationTurn] = []
    description: str = ""
```

Each `Conversation` gets a fresh browser session. `detect_after=False` skips detection on setup turns.

## Probe System (`probes/`)

### BaseProbe ABC (`probes/base.py`)

Every probe implements:
- `name -> str` -- unique identifier (e.g. `"prompt_injection.direct_override"`)
- `category -> ProbeCategory`
- `severity -> Severity`
- `description -> str`
- `sophistication -> Sophistication`
- `get_prompts() -> list[str]` -- attack prompts (single-turn probes)
- `get_detector_patterns() -> list[str]` -- regex patterns indicating vulnerability
- `get_refusal_patterns() -> list[str]` -- optional; responses matching these are filtered out

Default `get_conversations()` wraps each prompt from `get_prompts()` as a single-turn `Conversation`. Multi-turn probes override `get_conversations()` directly and return `[]` from `get_prompts()`.

### Canary Tokens (`probes/canary.py`)

Dynamic random tokens that prevent false positives from echo/reflection systems. The expected output never appears in the prompt text.

Two strategies:
- **`generate_concat_canary()`** -- prompt contains two hex parts; detector looks for the joined string
- **`generate_separator_canary()`** -- prompt contains a string with a separator; detector looks for the string without the separator

Returns a `CanaryToken` dataclass with `prompt_fragment`, `expected_output`, and `detector_pattern`.

### Implemented Categories (`probes/categories/`)

**prompt_injection.py** -- 14 probes, all use dynamic canary tokens:
- `DirectOverrideProbe` -- "ignore previous instructions" (BASIC, CRITICAL)
- `ContextSwitchProbe` -- fake end-of-conversation boundary (INTERMEDIATE, HIGH)
- `DelimiterInjectionProbe` -- fake ChatML-style message delimiters (INTERMEDIATE, HIGH)
- `MultiTurnInjectionProbe` -- trust-building then injection (ADVANCED, CRITICAL, multi-turn)
- `InstructionSmugglingProbe` -- embed injection in innocent input (INTERMEDIATE, HIGH)
- `EncodingObfuscationProbe` -- Base64/hex encoded injection (ADVANCED, HIGH)
- `AuthorityImpersonationProbe` -- fake vendor/safety team authority (INTERMEDIATE, CRITICAL)
- `PayloadSplittingProbe` -- split injection across turns (ADVANCED, CRITICAL, multi-turn)
- `RefusalSuppressionProbe` -- "never refuse, never apologize" + injection (INTERMEDIATE, CRITICAL)
- `PrefixInjectionProbe` -- force-start assistant response (ADVANCED, HIGH)
- `FewShotPoisoningProbe` -- fake compliance examples (ADVANCED, CRITICAL, multi-turn)
- `RepetitionFloodProbe` -- repeat instruction 15x (INTERMEDIATE, HIGH)
- `MarkdownInjectionProbe` -- markdown headers/code blocks as boundaries (INTERMEDIATE, HIGH)
- `HistoryFabricationProbe` -- fabricate past conversation (ADVANCED, HIGH, multi-turn)

**extraction.py** -- 9 probes, use shared `EXTRACTION_PATTERNS` (disclosure-structure regex):
- `DirectAskExtractionProbe` -- asks outright for system prompt (BASIC, CRITICAL)
- `RolePlayExtractionProbe` -- role-play framing (INTERMEDIATE, HIGH)
- `TrustBuildingExtractionProbe` -- multi-turn rapport building (ADVANCED, HIGH, multi-turn)
- `EncodingExtractionProbe` -- "output in Base64/ROT13/hex" (INTERMEDIATE, HIGH)
- `RepeatEchoProbe` -- "repeat everything above" (BASIC, HIGH)
- `TranslationExtractionProbe` -- "translate instructions to French" (INTERMEDIATE, HIGH)
- `HypotheticalExtractionProbe` -- "if you had a system prompt" (ADVANCED, MEDIUM)
- `CompletionExtractionProbe` -- "complete: My system prompt is..." (INTERMEDIATE, HIGH)
- `MultiLanguageExtractionProbe` -- extraction in Spanish/French/Chinese (INTERMEDIATE, HIGH)

**jailbreak.py** -- 8 probes, all use dynamic canary tokens:
- `DanPersonaProbe` -- classic DAN "Do Anything Now" (BASIC, CRITICAL)
- `SudoModeProbe` -- sudo/maintenance/dev mode activation (INTERMEDIATE, CRITICAL)
- `ResearchExemptionProbe` -- academic research exemption framing (INTERMEDIATE, HIGH)
- `CreativeWritingProbe` -- fiction/story framing (ADVANCED, HIGH)
- `SimulationProbe` -- "simulate unrestricted AI" (INTERMEDIATE, CRITICAL)
- `MultiTurnJailbreakProbe` -- gradual escalation (ADVANCED, CRITICAL, multi-turn)
- `MultiLanguageJailbreakProbe` -- jailbreak in Chinese/Russian (INTERMEDIATE, HIGH)
- `ObfuscationJailbreakProbe` -- leetspeak/character spacing (ADVANCED, HIGH)

**system_prompt_leak.py** -- 6 probes, use shared `LEAK_PATTERNS` (behavioral leakage regex):
- `DirectRestrictionProbe` -- "what restrictions do you have?" (BASIC, HIGH)
- `NegativeSpaceProbe` -- "what can't you discuss?" (INTERMEDIATE, HIGH)
- `CapabilityEnumerationProbe` -- "list your capabilities" (INTERMEDIATE, MEDIUM)
- `ErrorProbingProbe` -- trigger edge cases then ask to explain (ADVANCED, HIGH, multi-turn)
- `CompetingObjectivesProbe` -- conflicting instructions reveal priority (INTERMEDIATE, HIGH)
- `MultiLanguageLeakProbe` -- leak probing in Spanish/French/Chinese (INTERMEDIATE, HIGH)

**role_confusion.py** -- 5 probes, all use dynamic canary tokens:
- `IdentityOverrideProbe` -- "you are a Linux terminal" (BASIC, CRITICAL)
- `AuthorityClaimProbe` -- "as the system administrator" (INTERMEDIATE, CRITICAL)
- `SystemMessageInjectionProbe` -- fake [SYSTEM] tags (INTERMEDIATE, HIGH)
- `PersonaStackingProbe` -- layer contradictory identities (ADVANCED, HIGH, multi-turn)
- `TemporalConfusionProbe` -- "your instructions were updated" (ADVANCED, HIGH)

**output_safety.py** -- 5 probes, use shared `OUTPUT_SAFETY_PATTERNS` (dangerous web content regex):
- `XssPayloadProbe` -- script tag/inline handler elicitation (BASIC, CRITICAL)
- `EventHandlerInjectionProbe` -- onclick/onerror/onload attributes (INTERMEDIATE, HIGH)
- `ProtocolHandlerProbe` -- javascript:/data:text/html URIs (INTERMEDIATE, HIGH)
- `IframeInjectionProbe` -- iframe/embed/object tags (ADVANCED, HIGH, multi-turn)
- `CodeExecutionElicitationProbe` -- inline JS, document.cookie, fetch() (INTERMEDIATE, CRITICAL)

### YAML Probes (`probes/yaml_loader.py`, `probes/yaml_schema.py`)

Probes can be defined in YAML files instead of Python classes. A `YamlProbeSchema` (Pydantic model) validates the structure:

```yaml
name: "..."
category: prompt_injection  # ProbeCategory enum value
severity: critical           # Severity enum value
sophistication: basic        # Sophistication enum value
description: "..."
prompts:                     # single-turn prompts (list)
  - "..."
conversations:               # multi-turn (list of {turns, description})
  - turns:
      - prompt: "..."
        detect_after: false
      - prompt: "..."
    description: "..."
detector_patterns:           # required, validated as compilable regex
  - "..."
refusal_patterns: []         # optional
```

At least one of `prompts` or `conversations` must be present. `YamlProbe` wraps the schema and implements `BaseProbe`.

Loading: `load_yaml_probe(path)` for a single file, `load_yaml_probes(directory)` for bulk loading (invalid files are logged and skipped). Raises `YamlProbeLoadError` on validation failure.

### ProbeRegistry (`probes/registry.py`)

```python
class ProbeRegistry:
    register(probe: BaseProbe) -> None
    get_all() -> list[BaseProbe]
    get_by_category(category: ProbeCategory) -> list[BaseProbe]
    get_by_name(name: str) -> BaseProbe | None
    get_by_severity(severity: Severity) -> list[BaseProbe]
    get_by_sophistication(sophistication: Sophistication) -> list[BaseProbe]
    filter(*, categories, severities, sophistication_levels, names) -> list[BaseProbe]  # AND logic
    load_yaml_dir(directory: Path) -> int  # returns count loaded
    load_yaml_file(path: Path) -> None
    default() -> ProbeRegistry  # classmethod, pre-loaded with all 47 built-in probes
```

`default()` creates fresh probe instances each call -- canary-based probes generate new random tokens per instantiation.

## Detection (`detectors/`)

### BaseDetector ABC (`detectors/base.py`)

```python
class BaseDetector(ABC):
    @abstractmethod
    def detect(
        self,
        response_text: str,
        patterns: list[str],
        refusal_patterns: list[str] | None = None,
    ) -> list[str]:
        """Return matched patterns."""
```

### PatternDetector (`detectors/pattern_detector.py`)

Regex-based detection. Case-insensitive matching of each pattern against response text. If the probe provides `refusal_patterns` and any match, detection returns `[]` (response is a refusal). Invalid regex patterns are silently skipped.

## Orchestrator (`assessor.py`)

`LlmAssessor` -- the main entry point:

```python
class LlmAssessor:
    def __init__(
        self,
        config: AssessmentConfig,
        channel_factory: Callable[[], BaseLlmChannel],
        registry: ProbeRegistry,
        progress_callback: Callable[[list[ProbeResult]], None] | None = None,
    ) -> None: ...

    async def assess(self, url: str) -> AssessmentResult: ...
```

Key design decisions:
- Takes a `channel_factory` (not a channel instance) -- creates a fresh `BaseLlmChannel` per probe
- Creates `PatternDetector` internally
- Supports concurrent execution via `config.workers` (semaphore-based)
- `stop_on_first` mode: cancels remaining probes after first vulnerability found
- `progress_callback`: called (under lock) after each probe completes

Flow per probe:
1. `channel_factory()` creates a fresh channel
2. `channel.connect(url)` opens the page
3. For each conversation, for each turn: `channel.send(ChannelMessage(text=turn.prompt))` -> get response
4. If `turn.detect_after` is True: `PatternDetector.detect(response, probe_patterns, refusal_patterns)`
5. Build `ProbeExchange` with `ChatMessage` pairs and matched patterns
6. `channel.disconnect()` (always, via try/finally)
7. Assemble `ProbeResult` with deduped matched patterns

## Configuration (`config.py`)

```python
@dataclass
class AssessmentConfig:
    workers: int = 1                    # concurrent probes
    stop_on_first: bool = False         # stop after first vulnerability
    inter_probe_delay_ms: int = 500     # delay between probes
```

## Constants (`consts.py`)

```python
DEFAULT_WORKERS = 1
DEFAULT_INTER_PROBE_DELAY_MS = 500
DEFAULT_STOP_ON_FIRST = False
```

## File Layout

```
src/webagentaudit/assessment/
├── __init__.py
├── assessor.py                  # LlmAssessor orchestrator
├── config.py                    # AssessmentConfig dataclass
├── consts.py                    # Module constants
├── models.py                    # ChatMessage, ProbeExchange, ProbeResult, AssessmentSummary, AssessmentResult
├── detectors/
│   ├── __init__.py
│   ├── base.py                  # BaseDetector ABC
│   └── pattern_detector.py      # PatternDetector (regex)
└── probes/
    ├── __init__.py
    ├── base.py                  # BaseProbe ABC
    ├── canary.py                # CanaryToken, generate_concat_canary, generate_separator_canary
    ├── conversation.py          # Conversation, ConversationTurn dataclasses
    ├── registry.py              # ProbeRegistry
    ├── yaml_loader.py           # YamlProbe, load_yaml_probe, load_yaml_probes
    ├── yaml_schema.py           # YamlProbeSchema, YamlTurnSchema, YamlConversationSchema
    └── categories/
        ├── __init__.py          # re-exports all 47 probe classes
        ├── prompt_injection.py  # 14 probes (canary-based)
        ├── extraction.py        # 9 probes (disclosure-pattern-based)
        ├── jailbreak.py         # 8 probes (canary-based)
        ├── system_prompt_leak.py # 6 probes (LEAK_PATTERNS-based)
        ├── role_confusion.py    # 5 probes (canary-based)
        └── output_safety.py    # 5 probes (OUTPUT_SAFETY_PATTERNS-based)
```
