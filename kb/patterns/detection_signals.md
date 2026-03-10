# Detection Signals Pattern

## Overview

Detection uses a signal aggregation pattern: multiple independent checkers each produce zero or more signals, which are combined into an overall detection result with confidence scoring.

## Signal Flow

```
PageData → [Checker1, Checker2, ..., CheckerN] → [Signal, Signal, ...] → Aggregator → DetectionResult
```

## Components

### BaseSignalChecker (ABC)
Each checker examines one aspect of the page:
- `check(page_data) -> list[DetectionSignal]`
- `name -> str` (property)

Checkers are independent — they don't know about each other.

### DetectionSignal
A single piece of evidence:
- `checker_name`: which checker found it
- `signal_type`: classification (e.g., "chat_widget_dom", "api_endpoint")
- `confidence`: how confident this signal is
- `evidence`: the specific element/pattern found
- `method`: DETERMINISTIC or AI_ASSISTED

### Confidence Aggregation

The `LlmDetector` orchestrator aggregates signals into an overall confidence:

Strategy options:
1. **Maximum**: overall = max(signal confidences). Good when any strong signal is sufficient.
2. **Weighted average**: weight by signal type reliability. More nuanced.
3. **Bayesian combination**: treat signals as independent evidence. Most sophisticated.

Start with maximum, add weighted average as option via config.

### DetectionResult Composition

The result includes:
- `llm_detected`: bool (overall_confidence > threshold)
- `overall_confidence`: aggregated score
- `signals`: all individual signals for transparency
- `provider_hint`: if a known provider signature was found
- `interaction_hint`: suggested selectors for LlmChannel to use

## Design Decisions

1. **Checkers are stateless**: Given the same PageData, they produce the same signals. Makes testing trivial.
2. **Signals carry provenance**: Each signal knows which checker produced it. Enables debugging and tuning.
3. **Threshold is configurable**: DetectionConfig.confidence_threshold determines llm_detected cutoff.
4. **interaction_hint bridges detection→channel**: Detection can suggest which selectors to use for LlmChannel, creating a natural pipeline.
