# Crawl Scope Module Design

**Path**: `src/webllm/detection/crawl_scope/`

## Purpose

Decide whether a URL is within bounds for crawling. Each scope is pure logic — given a URL and seed URL, return bool. Scopes are composable.

## Structure

```
crawl_scope/
├── __init__.py
├── base.py            # BaseCrawlScope ABC
├── models.py          # CrawlScopeConfig dataclass
├── composite.py       # CompositeCrawlScope (AND/OR composition)
└── scopes/
    ├── __init__.py
    ├── same_domain.py  # SameDomainScope
    ├── same_apex.py    # SameApexDomainScope
    ├── url_prefix.py   # UrlPrefixScope
    └── allowlist.py    # AllowlistScope
```

## Key Interface: BaseCrawlScope ABC

```python
class BaseCrawlScope(ABC):
    @abstractmethod
    def is_in_scope(self, url: str, *, seed_url: str) -> bool: ...

    @property
    @abstractmethod
    def name(self) -> str: ...
```

`seed_url` is passed explicitly (not stored at construction) to keep scopes stateless and reusable.

## Scope Implementations

- **SameDomainScope**: same hostname as seed URL
- **SameApexDomainScope**: same registrable domain (support.example.com matches www.example.com). Uses simple suffix extraction with small list of known multi-part TLDs in consts.
- **UrlPrefixScope**: URL starts with given prefix (constructed with prefix string)
- **AllowlistScope**: URL matches explicit list (constructed with URL list)

## CompositeCrawlScope

Implements `BaseCrawlScope`. Composes multiple scopes with AND (require_all=True) or OR logic. Can be nested (Composite pattern).

## Configuration

```python
@dataclass
class CrawlScopeConfig:
    max_depth: int = 2
    max_urls: int = 50
    require_all_scopes: bool = True  # AND vs OR
    custom_allowlist: list[str] = field(default_factory=list)
    custom_denylist: list[str] = field(default_factory=list)
```

## Design Decision: Depth Is Execution, Not Scope

Depth limits are in CrawlScopeConfig for configuration, but depth tracking belongs to the crawl executor (outside detection module). Scopes answer "is this URL valid?" not "have we gone too deep?"

## Crawl Executor (Outside Detection Module)

The detection module provides building blocks. A crawl orchestrator would compose:
1. `LlmDetector.detect(page_data)` — is there an LLM on this page?
2. `LinkAnalyzer.analyze(page_data)` — which links might lead to LLMs?
3. `CompositeCrawlScope.is_in_scope(url)` — should we follow this URL?

The orchestrator does the I/O (page fetching) and depth tracking.
