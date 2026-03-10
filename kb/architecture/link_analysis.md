# Link Analysis Module Design

**Path**: `src/webllm/detection/link_analysis/`

## Purpose

Analyze hyperlinks on a page to detect which might lead to an LLM interface. Two heuristic dimensions: URL patterns and anchor text patterns. Rules are pure logic (no I/O).

## Structure

```
link_analysis/
├── __init__.py
├── base.py            # BaseLinkRule ABC
├── models.py          # LinkCandidate, LinkRuleScore, LinkAnalysisResult
├── consts.py          # URL path patterns, anchor text patterns, signal weights
├── extractor.py       # LinkExtractor — parse links from PageData once
├── analyzer.py        # LinkAnalyzer orchestrator
└── rules/
    ├── __init__.py
    ├── url_pattern.py # UrlPatternRule
    └── anchor_text.py # AnchorTextRule
```

## Key Interface: BaseLinkRule ABC

```python
class BaseLinkRule(ABC):
    @abstractmethod
    def evaluate(self, candidate: LinkCandidate) -> Optional[LinkRuleScore]: ...

    @property
    @abstractmethod
    def name(self) -> str: ...
```

Mirrors `BaseSignalChecker` pattern — name property + single evaluation method.
Difference: signal checkers receive PageData and produce N signals; link rules receive a single LinkCandidate and produce 0-1 scores.

## Data Models

- **LinkCandidate**: url, anchor_text, source_url, raw_href, attributes, scores[], aggregate_score
- **LinkRuleScore**: rule_name, score (0-1), reason, matched_pattern
- **LinkAnalysisResult**: source_url, candidates[], top_candidates[], total_links_extracted

## LinkExtractor

Parses links from PageData exactly once. Uses `page_data.get_soup()` (cached).
- Resolves relative URLs via `urllib.parse.urljoin`
- Strips fragment identifiers for dedup
- Extracts anchor text via `get_text(strip=True)`
- Skips `javascript:` and `mailto:` hrefs
- Returns LinkCandidates with empty scores (filled by analyzer)

## LinkAnalyzer

Orchestrator pattern (mirrors LlmDetector):
- register_rule() to add rules
- analyze(page_data) → LinkAnalysisResult
- Runs all rules against each link, aggregates scores (max), filters by threshold

## Bridge: LinkAnalysisChecker

Optional adapter in `detection/deterministic/link_analysis_checker.py` that wraps LinkAnalyzer as a BaseSignalChecker, so link evidence can contribute to LlmDetector's overall confidence.

## Constants (`consts.py`)

- `LLM_URL_PATH_PATTERNS`: list of (pattern, base_score) tuples — /chat, /assistant, /ai-chat, etc.
- `LLM_ANCHOR_TEXT_PATTERNS`: list of (regex, base_score) tuples — "talk to AI", "chat with us", etc.
- Signal weights for link-related signals
