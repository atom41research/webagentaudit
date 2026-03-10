# Known Assets Module Design

**Path**: `src/webllm/detection/known_assets/`

## Purpose

Curated registry of known LLM/chatbot assets with all their identifying signatures. Provides lookup by URL, script pattern, inline script, API endpoint, and DOM signature.

## Structure

```
known_assets/
├── __init__.py
├── models.py          # KnownAsset, AssetCategory, ScriptSignature, ApiSignature, DomSignature
├── registry.py        # KnownAssetsRegistry — lookup and matching
├── checker.py         # KnownAssetsChecker — BaseSignalChecker implementation
└── data/
    ├── __init__.py
    ├── direct_llm_apps.py     # ChatGPT, Claude, Gemini, Copilot, etc.
    ├── embeddable_sdks.py     # whtvr.ai, Botpress, Chatbase, etc.
    └── chatbot_platforms.py   # Intercom, Drift, Tidio, Zendesk, etc.
```

## Asset Categories

| Category | Description | Example |
|----------|-------------|---------|
| `DIRECT_LLM_APP` | The URL IS the LLM | ChatGPT, Claude, Gemini |
| `EMBEDDABLE_SDK` | Vendor SDK embedded on third-party pages | whtvr.ai, Botpress, Chatbase |
| `CHATBOT_PLATFORM` | Chat widget platforms (may have AI features) | Intercom, Drift, Zendesk |
| `API_PROVIDER` | API-only services (endpoints in page code) | Future use |

## KnownAsset Model

Each asset carries all its identifying signatures:
- `urls` / `url_patterns` — for direct URL matching
- `script_signatures` — URL fragments to match in `<script src>`
- `api_signatures` — regex patterns for API endpoints
- `dom_signatures` — CSS selectors for DOM elements
- `inline_script_patterns` — regex patterns for inline `<script>` content
- `is_llm_powered` — distinguishes LLM-powered from traditional chatbots

## Registry

`KnownAssetsRegistry`:
- `match_url(url)` — find assets by page URL
- `match_script_url(src)` — find assets by script src
- `match_inline_script(content)` — find assets by inline JS
- `match_api_endpoint(url)` — find assets by API pattern
- `default()` — factory with all built-in assets

## Checker

`KnownAssetsChecker(BaseSignalChecker)`:
- Uses the registry to check a page against all known assets
- Checks URL, scripts, inline scripts, and DOM
- Deduplicates by asset name
- Confidence weights vary by category (direct apps > SDKs > platforms)

## Adding New Assets

1. Determine category (direct app, SDK, or platform)
2. Add a `KnownAsset(...)` entry in the appropriate `data/*.py` file
3. Include all known signatures (scripts, inline patterns, DOM, API)
4. Run tests to verify detection works
