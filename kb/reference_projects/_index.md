# Reference Projects

Research on existing LLM security and evaluation tools that inform webllm's design.

## Contents

- **agentseal.md** — AgentSeal: AI agent security validation toolkit. Probe-response architecture, deterministic pattern matching, trust scoring
- **garak.md** — NVIDIA Garak: LLM vulnerability scanner. Plugin architecture with probes, detectors, generators, harnesses, evaluators
- **promptfoo.md** — Promptfoo: LLM evaluation framework. Provider abstraction, declarative config, assertion-based evaluation
- **gap_analysis_garak_promptfoo.md** — Comprehensive gap analysis: every Garak probe module (38) and Promptfoo plugin (134) mapped against our 47 probes, with feasibility assessment for deterministic detection

## When to Use

- When designing new probe categories or detection patterns
- When deciding on architectural patterns for plugin/extensibility systems
- When comparing our approach to industry standards
