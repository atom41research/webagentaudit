# Knowledgebase

Central repository of research, design decisions, and domain knowledge for the webllm project.

## Contents

- **reference_projects/** — Research on existing tools that inspired this project (AgentSeal, Garak, promptfoo)
- **architecture/** — Module design documents, interfaces, data models, dependency graph
- **patterns/** — Design patterns used across the project (probe system, channel interface, detection signals)
- **domain/** — Domain knowledge about LLM detection techniques and attack categories

## When to Use

Check this knowledgebase BEFORE starting any new work:
- Before designing a new module or feature, check `architecture/` for existing design decisions
- Before implementing probes or detection, check `domain/` for known techniques
- Before creating abstractions, check `patterns/` for established patterns
- Before studying a reference project, check `reference_projects/` for existing research

## Maintenance Rules

### When to Update

| Trigger | Action |
|---------|--------|
| You discover something not already in the KB | Write it down immediately — don't wait until the task is done |
| A design decision deviates from what's documented | Update the architecture doc with the new decision and reasoning |
| A module's interface, model, or structure changes in code | Update the corresponding `kb/architecture/<module>.md` to match |
| You add a new probe category or attack type | Update `kb/domain/llm_attack_categories.md` |
| You add a new detection technique or selector set | Update `kb/domain/llm_detection_techniques.md` |
| You add a new design pattern or change an existing one | Update the relevant `kb/patterns/` doc |
| You research a new external tool/project | Add a new file in `kb/reference_projects/` |

### Staleness Prevention

- If you read a KB doc and it contradicts the actual code — **fix the doc right then**. Don't leave it for later.
- Architecture docs must include file paths. If a file moves, update the doc.
- The KB is only useful if it's accurate. Stale docs are worse than no docs.

### Structure Rules

- Every folder MUST have an `_index.md` explaining its contents.
- When adding a new file or subfolder to `kb/`, update the parent `_index.md` to list it.
- One topic per file. If a file grows beyond its scope, split it.
