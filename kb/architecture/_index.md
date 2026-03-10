# Architecture

Design documents for each module, interfaces, data models, and the dependency graph.

## Contents

- **overview.md** — High-level architecture: module responsibilities, dependency graph, key design decisions
- **core.md** — Core module: shared models (ConfidenceScore, Finding), enums (Severity, ProbeCategory), exceptions, constants strategy
- **detection.md** — Detection module: deterministic signal checkers, AI-assisted detection, signal aggregation, DetectionResult model
- **assessment.md** — Assessment module: probe system, result detectors, harness, assessor orchestrator, report builder
- **llm_channel.md** — LlmChannel module: BaseLlmChannel interface, interaction strategies, Playwright implementation

## When to Use

- Before implementing any module, read its architecture doc first
- When adding new interfaces or modifying existing ones
- When making decisions about data flow between modules
