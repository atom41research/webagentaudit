# webagentaudit

Python project for detecting and assessing interactive LLMs on webpages.

## Modules

Three independent modules + shared core:

- `src/webagentaudit/core/` — Shared models, enums, exceptions, constants (no external deps except pydantic)
- `src/webagentaudit/detection/` — Detect interactive LLMs on webpages (deterministic + AI-assisted)
- `src/webagentaudit/assessment/` — Assess LLM security via probes (like AgentSeal/Garak)
- `src/webagentaudit/llm_channel/` — Interface for sending/receiving messages to web-based LLMs

Dependency graph: `core` ← `detection`, `llm_channel`, `assessment`. Assessment takes `BaseLlmChannel` via constructor injection (Dependency Inversion).

## Git & Commits

- NEVER mention yourself (Claude/AI) as a contributor in commits — no Co-Authored-By, no AI references
- Don't mention yourself when committing or pushing

## Tooling & Environment

- Use `uv` for ALL module/dependency operations
- Dev deps go in `[dependency-groups].dev` so plain `uv sync` works
- NEVER ignore import errors or dependency failures — they indicate broken environment
- Web interaction via Playwright

## Architecture Principles

- Modular architecture — NO code/logic duplication
- OOP + SOLID principles throughout
- Break modules into self-contained submodules that can be developed independently
- Use constants (`consts.py` per module) — ALWAYS check existing consts before creating new ones
- Parts must be independent of each other (dependency inversion at module boundaries)
- Pydantic `BaseModel` for data models that cross module boundaries
- `dataclass` for internal configuration objects
- ABC for abstract interfaces

## Development Workflow

See `workflow-rules.md` for the full workflow rules. Key highlights:

### Subagents & Parallelism
- Use subagents with git worktree for parallel work on independent modules
- Each worktree agent works on one module at a time
- Core module must be stable before parallel work on other modules
- Always try to "break" modules into submodules that are self-contained
- Use subagents liberally to keep main context window clean — one task per subagent

### Planning & Verification
- Enter plan mode for ANY non-trivial task (3+ steps or architectural decisions)
- If something goes sideways, STOP and re-plan immediately
- Never mark a task complete without proving it works (run tests, check logs, demonstrate correctness)
- Ask yourself: "Would a staff engineer approve this?"

### Quality Standards
- Simplicity first — make every change as simple as possible, impact minimal code
- No laziness — find root causes, no temporary fixes, senior developer standards
- For non-trivial changes: pause and ask "is there a more elegant way?"
- Minimal impact — changes should only touch what's necessary

### Testing
- Tests must be based on real pages and real interactions whenever possible — as close to reality as we can get
- Prefer real HTML snapshots / saved pages over synthetic toy HTML
- When testing detection or channel interaction, use actual page structures from known LLM-powered sites
- Store test fixtures (HTML snapshots, DOM dumps) in `tests/fixtures/` for reuse
- Mocks are acceptable only when real interaction is impractical (e.g., live LLM responses that cost money or are non-deterministic)

### Lessons & Self-Improvement
- After ANY correction from the user: update `tasks/lessons.md` with the pattern
- Review lessons at session start for relevant project

### Task Tracking
- Write plan to `tasks/todo.md` with checkable items
- Track progress, mark items complete as you go
- Document results and capture lessons after corrections

## Knowledgebase

All research, design decisions, and reference material lives in `kb/`. See `kb/_index.md` for full structure.

### Rules — MUST follow

**Before work:**
- Read the relevant `kb/` docs BEFORE starting any task. If the task touches detection, read `kb/architecture/detection.md` and `kb/domain/llm_detection_techniques.md`. Same principle for assessment, llm_channel, patterns, etc.
- Check `kb/reference_projects/` before designing anything new — the answer may already be there.

**During work:**
- If you discover something not in the KB (new pattern, gotcha, external tool insight, design decision), write it down immediately — don't wait until the end.
- If you make a design decision that deviates from what's documented, update the KB doc to reflect the new decision and the reasoning.

**After work:**
- When a module's interface, model, or structure changes: update the corresponding `kb/architecture/<module>.md` to match the actual code. KB must never be stale.
- When adding a new file/subfolder to `kb/`, update the parent `_index.md` to list it.
- When adding a new probe category, detection technique, or attack type: update the relevant `kb/domain/` doc.

**What goes where:**
- `reference_projects/` — Research on external tools/projects. One file per project.
- `architecture/` — How our modules work. Interfaces, models, configs, orchestration. Must match actual code.
- `patterns/` — Reusable design patterns. How to add new probes, checkers, strategies, etc.
- `domain/` — Domain knowledge independent of our code. Detection techniques, attack taxonomies, selector lists.

**Staleness prevention:**
- If you read a KB doc and find it contradicts the actual code, fix the KB doc right then — don't leave it for later.
- Architecture docs must include file paths. If a file moves, update the doc.

## Project Structure

```
webagentaudit/
├── CLAUDE.md
├── pyproject.toml
├── kb/                          # Knowledgebase (research, design, domain knowledge)
│   ├── _index.md
│   ├── reference_projects/      # Studied reference projects
│   ├── architecture/            # Architecture and design docs
│   ├── patterns/                # Design patterns used
│   └── domain/                  # Domain knowledge
├── src/webagentaudit/
│   ├── core/                    # Shared models, enums, exceptions, constants
│   ├── detection/               # LLM detection on webpages
│   │   ├── deterministic/       # DOM patterns, selectors, signatures
│   │   └── ai_assisted/         # Screenshot + DOM AI analysis
│   ├── assessment/              # LLM security assessment
│   │   ├── probes/              # Attack probes by category
│   │   │   └── categories/      # prompt_injection, extraction, jailbreak, etc.
│   │   └── detectors/           # Response analysis (pattern matching)
│   └── llm_channel/             # Web-based LLM interaction
│       └── strategies/          # Interaction strategies (chat widget, custom)
└── tests/
```
