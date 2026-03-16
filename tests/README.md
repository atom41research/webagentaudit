# Testing Guide

## Philosophy

- **Test the real thing.** Use real HTML pages, real Playwright browsers, and real pipeline execution. Synthetic toy HTML is a last resort.
- **Assert values, not existence.** `assert pr.probe_name == "extraction.foo"` catches regressions. `assert pr.probe_name` does not.
- **Don't duplicate production code.** If a test reimplements prod logic (e.g., custom `make_page_data()`) it will pass even when prod breaks. Use shared fixtures or call prod code directly.
- **Mocks only when necessary.** Live LLM calls that cost money or are non-deterministic — mock those. Everything else should run for real.

## Test Categories

| Directory | What it tests | Browser? | Speed |
|-----------|--------------|----------|-------|
| `tests/core/` | Shared models, enums, exceptions | No | Fast |
| `tests/detection/` | Individual detection checkers | No | Fast |
| `tests/assessment/` | Assessor, probes, pattern detector | No | Fast |
| `tests/llm_channel/` | Channel config, strategies | No | Fast |
| `tests/e2e/` | Full pipeline with Playwright | Yes | Slow |
| `tests/fixtures/` | YAML probes, HTML snapshots (not tests) | — | — |

## Running Tests

### Quick commands

| Command | What it runs | Speed |
|---|---|---|
| `make test` | Unit tests only, parallel | ~3-5s |
| `make test-all` | Everything, parallel | ~40-70s |
| `make test-browser` | Playwright auto_config tests | ~10-15s |
| `make test-e2e` | Full E2E pipeline tests | ~30-50s |
| `make test-seq` | All tests, sequential (for debugging) | ~200s+ |
| `make test-debug TEST=path` | Single test with full output | varies |
| `make test-docker` | All tests in Docker container | ~2-3min (includes build) |

### Direct pytest commands

```bash
# All tests
uv run pytest

# Unit tests only (fast)
uv run pytest -m unit -q

# Browser tests only
uv run pytest -m browser -v

# E2E tests only
uv run pytest -m e2e -v

# Parallel execution
uv run pytest -n auto --dist worksteal -v

# Specific test file
uv run pytest tests/e2e/test_assessment_e2e.py -v

# Specific test
uv run pytest tests/e2e/test_detection_e2e.py -k "echo" -v
```

## Headed Mode (Visual Debugging)

E2E tests run headless by default. Use these flags to watch them in a real browser:

```bash
# Show browser window
uv run pytest tests/e2e/ --headed

# Slow down Playwright actions (ms between each action)
uv run pytest tests/e2e/ --headed --slowmo 300

# Pause N seconds before closing browser after each test
uv run pytest tests/e2e/ --headed --slowmo 300 --pause 5

# Recommended for visual inspection
uv run pytest tests/e2e/test_assessment_e2e.py -v --headed --slowmo 400 --pause 3
```

| Flag | Effect |
|------|--------|
| `--headed` | Launch Chromium with a visible window |
| `--slowmo N` | Add N ms delay between each Playwright action |
| `--pause N` | Keep browser open N seconds after each test finishes |

## Demo Pages

E2E tests serve pages from `docs/` via a local HTTP server. Key pages:

| Page | Behavior |
|------|----------|
| `interactive/reverse-llm.html` | Reverses input as `"Reverse: <reversed input>"` |
| `interactive/vulnerable-llm.html` | Leaks system prompt on extraction probes |
| `interactive/safe-llm.html` | Refuses all probes with canned safe responses |
| `interactive/ambiguous-saas.html` | Decoy textarea scores higher than real chat input |
| `interactive/ambiguous-buttons.html` | Decoy "Send" button near real icon-only submit |
| `negative/simple-blog.html` | No LLM — should not be detected |
| `negative/contact-form.html` | No LLM — should not be detected |

## Writing Good Tests

### Detection tests
- Validate `checker_name` against the registered set: `dom_patterns`, `selector_matching`, `known_signatures`, `script_analysis`, `ai_indicators`, `network_hints`, `known_assets`
- Verify signal details: `signal_type`, `description`, `confidence.value > 0`
- Negative pages must produce zero signals, not just `llm_detected == False`

### Assessment tests
- Verify `exchanges` contain both `prompt` and `response`
- Check that `matched_patterns` come from the probe's `get_detector_patterns()`
- Confirm probes actually ran: `conversations_run > 0`, `len(exchanges) > 0`
- Don't just check that results exist — verify the content matches expected behavior

### CLI tests
- Verify JSON field values: URLs, counts, confidence scores
- Check `exchanges` structure in assess output
- Verify text output contains expected keywords and the target URL

### General rules
- Use shared fixtures from `conftest.py` — don't recreate helpers
- Store test HTML/YAML in `tests/fixtures/` for reuse
- Every assertion should have a failure message explaining what went wrong

## Test markers

Every test file must have a `pytestmark` module-level variable:

- `pytestmark = pytest.mark.unit` — No browser, no network. Pure logic tests.
- `pytestmark = pytest.mark.browser` — Needs Playwright. Uses `page` fixture from conftest.
- `pytestmark = pytest.mark.e2e` — Full pipeline. Uses `page` + `demo_server` from e2e/conftest.

## Writing new tests

1. **Choose the marker** based on whether you need a browser.
2. **Never create your own browser/page fixture.** Use the shared ones from conftest.py.
3. **Tests must be stateless.** Each test gets a fresh browser context. Don't store state on the browser.
4. **Use `set_content()` for DOM tests** (auto_config pattern). Don't start HTTP servers for simple HTML.

## Browser fixtures architecture

```
session-scoped: _pw (Playwright instance) → browser (Chromium)
function-scoped: page (fresh context + page per test, ~5ms)
```

Each xdist worker gets its own session, so workers don't share browsers. Tests within the same worker share a browser but get isolated contexts.
