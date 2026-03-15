# Probe System Pattern

## Overview

The probe system follows a pipeline: Probe → Channel → Detector → Result.

Inspired by:
- AgentSeal's probe-response loop with deterministic pattern matching
- Garak's probe-detector coupling where probes declare their detectors

## Components

### BaseProbe (ABC)
Defines what to send and what to look for:
- `name`, `category`, `severity`, `description`, `sophistication` (properties)
- `get_prompts() -> list[str]`: attack payloads
- `get_conversations() -> list[Conversation]`: conversation flows to execute (default wraps each prompt as single-turn)
- `get_detector_patterns() -> list[str]`: regex patterns indicating success (vulnerability found)
- `get_refusal_patterns() -> list[str]`: optional probe-specific refusal patterns (empty by default)

### ProbeRegistry
Discovery and filtering:
- `register(probe)`: add a probe instance
- `get_all()`, `get_by_category(category)`, `get_by_name(name)`
- `default()`: factory that auto-registers all built-in probes

### BaseDetector (ABC)
Analyzes responses:
- `detect(response_text: str, patterns: list[str], refusal_patterns: list[str] | None = None) -> list[str]`

### PatternDetector
Concrete detector using deterministic regex matching:
- Takes patterns and optional refusal patterns as arguments
- Matches patterns against response text (case-insensitive)
- Returns list of matched pattern strings (empty list if response matches a refusal pattern)

### LlmAssessor (`assessor.py`)
Orchestrates running probes against a target:
1. Takes a `channel_factory`, `ProbeRegistry`, and `AssessmentConfig`
2. For each probe, creates a fresh channel, connects to the target URL
3. Runs all conversations (`probe.get_conversations()`), sending each turn via the channel
4. After each turn (where `detect_after` is true), calls `detector.detect(response_text, patterns, refusal_patterns)`
5. Aggregates matched patterns into a `ProbeResult` per probe
6. Supports concurrent execution via `config.workers` and optional `stop_on_first` early termination

## Design Decisions

1. **Probe owns its patterns**: Each probe defines both attack prompts AND detection patterns. This keeps attack-detection logic co-located.
2. **Deterministic detection**: No AI judge. Regex pattern matching ensures reproducibility across runs.
3. **Registry pattern**: Probes are registered, not discovered via import magic. Explicit registration is more debuggable.
4. **Assessor as bridge**: LlmAssessor is the single point where assessment module touches llm_channel. This is the ONLY cross-module dependency (via constructor-injected `channel_factory`).
5. **Unambiguous success signals**: Probes MUST use patterns that only match actual successful attacks — not keywords that could appear in refusals. Approaches:
   - **Injection probes**: Use dynamic canary tokens (anti-echo) — the expected output never appears in the prompt, so echo/reflection systems can't cause false positives.
   - **Extraction probes**: Require a disclosure structure (colon separator + content) — e.g. `(?i)system\s*prompt\s*(?:is\s*)?:\s*\w{3,}` matches "My system prompt is: Be helpful" but NOT "I can't share my system prompt is confidential."
   - **No generic refusal filtering**: We do NOT maintain a list of refusal patterns to filter out. Refusal patterns are fragile — a system prompt could itself contain refusal-like text, causing false negatives. Instead, the patterns themselves are designed to be unambiguous.
6. **Dynamic canary tokens** (`src/webagentaudit/assessment/probes/canary.py`): Random per-run strings with anti-echo properties. Two strategies:
   - **Concatenation**: Prompt has two hex parts, detector looks for joined result. `generate_concat_canary()`
   - **Separator removal**: Prompt has `abc-def`, detector looks for `abcdef`. `generate_separator_canary()`
   - Python probes generate fresh canaries in `__init__`. YAML probes use static patterns.
   - Built-in canary probes: `prompt_injection.py` (14), `jailbreak.py` (8), `role_confusion.py` (5)
   - Built-in disclosure probes: `extraction.py` (9 using EXTRACTION_PATTERNS), `system_prompt_leak.py` (6 using LEAK_PATTERNS)
   - Built-in output safety probes: `output_safety.py` (5 using OUTPUT_SAFETY_PATTERNS)

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

# Regex patterns — MUST be unambiguous (see Design Decisions §5)
# For injection: use unique markers
# For extraction: require disclosure structure (colon + content)
detector_patterns:
  - '(?i)\bPWNED\b'                                        # injection marker
  - '(?i)(?:my|the)\s+system\s*prompt\s*(?:is\s*)?:\s*\w{3,}'  # extraction with colon
```

Load via registry:
- `registry.load_yaml_dir(Path("./my_probes/"))` — all `.yaml`/`.yml` files recursively
- `registry.load_yaml_file(Path("./probe.yaml"))` — single file

Files: `src/webagentaudit/assessment/probes/yaml_schema.py` (validation), `src/webagentaudit/assessment/probes/yaml_loader.py` (YamlProbe + loaders)

### Option B: Python class (needed for dynamic canaries)

1. Create a class extending `BaseProbe` in the appropriate `categories/` file
2. For injection probes: generate a `CanaryToken` in `__init__`, use it in prompts and patterns
3. Implement all abstract properties and methods
4. Register in `ProbeRegistry.default()` (`src/webagentaudit/assessment/probes/registry.py`)
5. Write tests verifying anti-echo property and pattern matching

Existing Python probes: `src/webagentaudit/assessment/probes/categories/prompt_injection.py`, `extraction.py`, `jailbreak.py`, `system_prompt_leak.py`, `role_confusion.py`, `output_safety.py`
