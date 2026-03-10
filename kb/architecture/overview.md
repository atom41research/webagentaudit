# Architecture Overview

## Module Responsibilities

### core (`src/webllm/core/`)
Shared foundation with zero cross-module dependencies. Contains:
- Data models (Pydantic): `ConfidenceScore`, `Finding`
- Enums: `Severity`, `ConfidenceLevel`, `ProbeCategory`, `DetectionMethod`
- Exceptions: hierarchy rooted at `WebLlmError`
- Constants: shared thresholds, version, defaults

### detection (`src/webllm/detection/`)
Detects interactive LLMs on webpages. Two sub-approaches:
- **deterministic/**: Signal checkers (DOM patterns, CSS selectors, known signatures, script analysis, network hints). Each checker implements `BaseSignalChecker` and produces `DetectionSignal` objects.
- **ai_assisted/**: Uses an AI model to analyze screenshots + DOM for LLM presence validation.
- **detector.py**: `LlmDetector` orchestrator aggregates signals into `DetectionResult` with overall confidence score.

### assessment (`src/webllm/assessment/`)
Assesses LLM security via attack probes. Components:
- **probes/**: `BaseProbe` ABC → concrete probe categories. `ProbeRegistry` for discovery.
- **detectors/**: `BaseResultDetector` ABC → `PatternDetector` (deterministic regex matching on responses).
- **harness.py**: `ProbeHarness` bridges probes + channel + detector. The ONLY cross-module import (uses `BaseLlmChannel`).
- **assessor.py**: `LlmAssessor` orchestrator runs probe sets and builds `AssessmentResult`.
- **report.py**: `AssessmentReport` builder.

### llm_channel (`src/webllm/llm_channel/`)
Interface for sending/receiving messages to web-based LLMs:
- **base.py**: `BaseLlmChannel` ABC (connect, send, disconnect, is_ready, async context manager)
- **strategies/**: `BaseInteractionStrategy` ABC → concrete strategies (chat_widget, custom selector)
- **playwright_channel.py**: `PlaywrightChannel` implementation using Playwright + strategies

## Dependency Graph

```
core (no deps)
  ↑
  ├── detection (depends on core only)
  ├── llm_channel (depends on core only)
  └── assessment (depends on core; imports BaseLlmChannel interface from llm_channel)
```

Assessment depends on llm_channel ONLY through the abstract `BaseLlmChannel` interface (Dependency Inversion Principle). It never imports Playwright or browser-specific code.

## Key Design Decisions

1. **Pydantic for data models, dataclass for configs**: Models that cross boundaries or get serialized use Pydantic. Internal config uses dataclasses.
2. **No AI judge for assessment**: Deterministic pattern matching ensures reproducibility (inspired by AgentSeal).
3. **Strategy pattern for channel interactions**: Different LLM widgets need different DOM interaction sequences.
4. **Signal aggregation for detection**: Individual checkers produce independent signals; orchestrator combines them.
5. **Registry pattern for probes**: New probes are added by extending BaseProbe and registering.
6. **Constructor injection**: Assessment receives LlmChannel at construction time, not via import.
