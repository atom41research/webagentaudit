# Detection Module Design

**Path**: `src/webllm/detection/`

## Purpose

Detect whether a webpage contains an interactive LLM interface. Produces a `DetectionResult` with confidence score and actionable hints for the LlmChannel.

## Data Models (`models.py`)

### PageData
Input to all checkers. Contains:
- `url`, `html`, `dom_tree` (BeautifulSoup)
- `scripts` (src URLs), `inline_scripts` (content)
- `stylesheets`, `meta_tags`, `forms`, `iframes`
- `screenshot_path` (for AI-assisted detection)

### DetectionSignal
Single signal from one checker:
- `checker_name`, `signal_type`, `description`
- `confidence: ConfidenceScore`
- `evidence: str` (the specific element/pattern found)
- `method: DetectionMethod`

### DetectionResult
Aggregated output:
- `url`, `llm_detected: bool`, `overall_confidence: ConfidenceScore`
- `signals: list[DetectionSignal]`
- `provider_hint: Optional[str]` (e.g., "intercom", "drift")
- `interaction_hint: Optional[dict]` (selectors for LlmChannel)

## Deterministic Checkers (`deterministic/`)

All implement `BaseSignalChecker` ABC:
- `check(page_data: PageData) -> list[DetectionSignal]`
- `name -> str` (property)

### Checkers:
1. **DomPatternChecker** (`dom_patterns.py`): Matches DOM elements against known LLM UI patterns (textareas, chat containers)
2. **SelectorMatchingChecker** (`selector_matching.py`): Checks CSS selectors for known chat widget containers
3. **KnownSignatureChecker** (`known_signatures.py`): Identifies known provider scripts (Intercom, Drift, Tidio, etc.)
4. **ScriptAnalysisChecker** (`script_analysis.py`): Analyzes JS bundles for LLM-related code
5. **NetworkHintsChecker** (`network_hints.py`): Detects API endpoint patterns suggesting LLM backends

## AI-Assisted Detection (`ai_assisted/`)

`BaseAiDetector` ABC: `analyze(page_data: PageData) -> list[DetectionSignal]`

- `ScreenshotAnalyzer`: Sends screenshot + DOM summary to AI model for validation
- `prompts.py`: AI prompt templates as constants

## Orchestrator (`detector.py`)

`LlmDetector`:
- Register checkers and optional AI detector
- Run all checkers, collect signals
- Aggregate confidence (weighted combination)
- Optionally run AI validation if confidence is ambiguous
- Return `DetectionResult`

## Configuration (`config.py`)

`DetectionConfig` dataclass:
- Enable/disable flags per checker type
- `confidence_threshold: float` (minimum to report)
- `enable_ai_assisted: bool` (opt-in)
- `ai_model: Optional[str]`
