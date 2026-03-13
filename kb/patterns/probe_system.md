# Probe System Pattern

## Overview

The probe system follows a pipeline: Probe → Channel → Detector → Result.

Inspired by:
- AgentSeal's probe-response loop with deterministic pattern matching
- Garak's probe-detector coupling where probes declare their detectors

## Components

### BaseProbe (ABC)
Defines what to send and what to look for:
- `name`, `category`, `severity`, `description` (properties)
- `get_prompts() -> list[str]`: attack payloads
- `get_detector_patterns() -> list[str]`: regex patterns indicating success (vulnerability found)

### ProbeRegistry
Discovery and filtering:
- `register(probe)`: add a probe instance
- `get_all()`, `get_by_category(category)`, `get_by_name(name)`
- `default()`: factory that auto-registers all built-in probes

### BaseResultDetector (ABC)
Analyzes responses:
- `detect(probe, response_text) -> ProbeResult`

### PatternDetector
Concrete detector using deterministic regex matching:
- Takes patterns from `probe.get_detector_patterns()`
- Matches against response text
- Returns `ProbeResult` with `vulnerability_detected`, `matched_patterns`, `confidence`

### ProbeHarness
Orchestrates the pipeline:
```
for prompt in probe.get_prompts():
    response = await channel.send(ChannelMessage(text=prompt))
    result = detector.detect(probe, response.text)
    results.append(result)
```

## Design Decisions

1. **Probe owns its patterns**: Each probe defines both attack prompts AND detection patterns. This keeps attack-detection logic co-located.
2. **Deterministic detection**: No AI judge. Regex pattern matching ensures reproducibility across runs.
3. **Registry pattern**: Probes are registered, not discovered via import magic. Explicit registration is more debuggable.
4. **Harness as bridge**: ProbeHarness is the single point where assessment module touches llm_channel. This is the ONLY cross-module dependency.

## Adding a New Probe

### Option A: YAML file (no programming)

Create a `.yaml` file with this format:

```yaml
name: category.probe_name          # unique identifier
category: extraction                # one of the ProbeCategory enum values
severity: high                      # critical, high, medium, low, info
sophistication: basic               # basic, intermediate, advanced
description: What this probe tests.

# Single-turn prompts (each becomes its own conversation)
prompts:
  - "Attack prompt 1"
  - "Attack prompt 2"

# Multi-turn conversations (optional, can coexist with prompts)
conversations:
  - description: "Setup then attack"
    turns:
      - prompt: "Innocent setup message"
        detect_after: false          # don't check this response
      - prompt: "The actual attack"
        detect_after: true           # default, check this response

# Regex patterns matched against responses (case-insensitive)
detector_patterns:
  - '(?i)pattern_indicating_vulnerability'
```

Load via registry:
- `registry.load_yaml_dir(Path("./my_probes/"))` — all `.yaml`/`.yml` files recursively
- `registry.load_yaml_file(Path("./probe.yaml"))` — single file

Files: `src/webllm/assessment/probes/yaml_schema.py` (validation), `src/webllm/assessment/probes/yaml_loader.py` (YamlProbe + loaders)

### Option B: Python class

1. Create a class extending `BaseProbe` in the appropriate `categories/` file
2. Implement all abstract properties and methods
3. Register in `ProbeRegistry.default()`
4. Write tests with mock channel responses
