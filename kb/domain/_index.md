# Domain Knowledge

Technical knowledge about LLM detection on webpages and LLM attack/assessment categories.

## Contents

- **llm_detection_techniques.md** — How to detect interactive LLMs on webpages: DOM patterns, CSS selectors, known provider scripts, API endpoint patterns, AI-assisted screenshot analysis
- **llm_attack_categories.md** — Categories of LLM attacks used in assessment: prompt injection, extraction, jailbreak, system prompt leak, role confusion — with examples and detection patterns
- **llm_vendor_registry.md** — Comprehensive registry of known LLM/AI chatbot services, their URLs, SDK patterns, API endpoints, DOM signatures, and global JS objects for detection

## When to Use

- When adding new detection checkers or patterns to `detection/`
- When creating new probe categories for `assessment/`
- When writing detection patterns for response analysis
