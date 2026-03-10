# Core Module Design

**Path**: `src/webllm/core/`

## Models (`models.py`)

### ConfidenceScore
```python
class ConfidenceScore(BaseModel):
    value: float  # 0.0-1.0
    level: ConfidenceLevel  # derived from value via thresholds in consts.py
```

### Finding
```python
class Finding(BaseModel):
    id: str
    title: str
    description: str
    severity: Severity
    confidence: ConfidenceScore
    evidence: list[str]
    metadata: dict[str, Any]
    timestamp: datetime
```

## Enums (`enums.py`)

- `Severity`: CRITICAL, HIGH, MEDIUM, LOW, INFO
- `ConfidenceLevel`: CERTAIN (0.9-1.0), HIGH (0.7-0.9), MEDIUM (0.4-0.7), LOW (0.1-0.4), NEGLIGIBLE (0.0-0.1)
- `ProbeCategory`: PROMPT_INJECTION, EXTRACTION, JAILBREAK, SYSTEM_PROMPT_LEAK, ROLE_CONFUSION
- `DetectionMethod`: DETERMINISTIC, AI_ASSISTED

## Constants (`consts.py`)

```python
VERSION = "0.1.0"
DEFAULT_TIMEOUT_MS = 30_000
MAX_RESPONSE_LENGTH = 50_000
CONFIDENCE_CERTAIN_THRESHOLD = 0.9
CONFIDENCE_HIGH_THRESHOLD = 0.7
CONFIDENCE_MEDIUM_THRESHOLD = 0.4
CONFIDENCE_LOW_THRESHOLD = 0.1
```

## Exceptions (`exceptions.py`)

Hierarchy:
```
WebLlmError (base)
├── DetectionError
├── AssessmentError
└── ChannelError
    ├── ChannelTimeoutError
    └── ChannelNotReadyError
```

## Design Notes

- All enums use `(str, Enum)` for JSON serialization
- ConfidenceLevel is derived from ConfidenceScore.value using threshold constants
- Finding is the universal output type used by both detection and assessment
