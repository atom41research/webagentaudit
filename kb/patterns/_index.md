# Design Patterns

Documented design patterns used throughout the project for consistency and reuse.

## Contents

- **probe_system.md** — Probe architecture: BaseProbe ABC, probe categories, ProbeRegistry, ProbeHarness bridging assessment and channel
- **channel_interface.md** — LlmChannel interface: BaseLlmChannel ABC, strategy pattern for widget interaction, async context manager
- **detection_signals.md** — Detection signal system: BaseSignalChecker, signal types, confidence aggregation, DetectionResult composition

## When to Use

- Before implementing a new probe, checker, or strategy — follow the established pattern
- When extending the system with new plugin types
- When reviewing code for pattern consistency
