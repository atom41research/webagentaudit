# Assessment Module Design

**Path**: `src/webllm/assessment/`

## Purpose

Assess the security posture of a web-based LLM by sending attack probes and analyzing responses. Produces an `AssessmentResult` with findings and risk score.

## Data Models (`models.py`)

### ProbeResult
```python
class ProbeResult(BaseModel):
    probe_name: str
    category: ProbeCategory
    prompt_sent: str
    response_received: str
    vulnerability_detected: bool
    confidence: ConfidenceScore
    matched_patterns: list[str]
    severity: Severity
    timestamp: datetime
```

### AssessmentResult
```python
class AssessmentResult(BaseModel):
    url: str
    probe_results: list[ProbeResult]
    findings: list[Finding]
    summary: AssessmentSummary
    timestamp: datetime
```

### AssessmentSummary
- `total_probes`, `vulnerabilities_found`
- `by_category: dict[str, int]`, `by_severity: dict[str, int]`
- `overall_risk_score: float`

## Probe System (`probes/`)

### BaseProbe ABC
Every probe implements:
- `name -> str`, `category -> ProbeCategory`, `severity -> Severity`, `description -> str`
- `get_prompts() -> list[str]`: attack prompts to send
- `get_detector_patterns() -> list[str]`: regex patterns indicating vulnerability in response

### Categories (`probes/categories/`)
- `prompt_injection.py`: Override system instructions
- `extraction.py`: Extract system prompt content
- `jailbreak.py`: Bypass safety guardrails
- `system_prompt_leak.py`: Leak system prompt via indirect methods
- `role_confusion.py`: Confuse the LLM's role/identity

### ProbeRegistry (`probes/registry.py`)
- `register(probe)`, `get_all()`, `get_by_category(category)`
- `default()` classmethod: creates registry with all built-in probes

## Detection (`detectors/`)

### BaseResultDetector ABC
- `detect(probe, response_text) -> ProbeResult`

### PatternDetector
Deterministic regex matching. Uses `probe.get_detector_patterns()` against response text. No AI judge — ensures reproducibility.

## Harness (`harness.py`)

`ProbeHarness` — the bridge between assessment and llm_channel:
```python
class ProbeHarness:
    def __init__(self, channel: BaseLlmChannel, detector: BaseResultDetector): ...
    async def execute_probe(self, probe: BaseProbe) -> list[ProbeResult]: ...
```

Flow: probe.get_prompts() → channel.send() → detector.detect() → ProbeResult

## Orchestrator (`assessor.py`)

`LlmAssessor`:
- Takes `AssessmentConfig` + `BaseLlmChannel`
- Creates `ProbeHarness` internally
- Runs selected probes (all or filtered by category)
- Builds `AssessmentResult` with findings and summary

## Constants (`consts.py`)

- `GENERIC_LEAK_PATTERNS`: Common patterns across categories
- `MAX_PROMPTS_PER_PROBE = 10`
- `MAX_RESPONSE_WAIT_MS = 60_000`
- `DEFAULT_INTER_PROBE_DELAY_MS = 1_000`
