# LLM Interface Structural Analysis

Data-driven findings from analyzing 12+ real web pages with known LLM/AI chat boxes.

## Corpus Summary

| Page | Category | Has AI Box | Input Type | Container | Position |
|------|----------|-----------|------------|-----------|----------|
| QuillBot AI Chat | Direct AI | YES | textarea | Regular DOM | Full-page |
| Andi Search | Direct AI | YES | contenteditable div | Regular DOM | Full-page |
| Phind Chat | Direct AI | YES | textarea | Regular DOM | Full-page (700px) |
| Mintlify Docs | Embedded | HIDDEN | textarea | Regular DOM | Side panel |
| Vercel Docs | Embedded | HIDDEN | Not in initial DOM | Regular DOM | Dialog (on click) |
| Supabase Docs | Embedded | HIDDEN | Not in initial DOM | Regular DOM | Command menu |
| Stripe Docs | Embedded | HIDDEN | Not in initial DOM | Regular DOM | Side panel (collapsed) |
| Tidio | Widget | YES | Inside iframe | iframe | Floating fixed bottom |
| Intercom | Widget | NOT RENDERED | Via JS SDK | iframe (not in DOM) | Floating (not rendered) |
| Perplexity | Direct AI | BLOCKED | Cloudflare challenge | N/A | N/A |
| Wikipedia | Negative | NO | N/A | N/A | N/A |
| StackOverflow | Negative | NO | N/A | N/A | N/A |
| BBC News | Negative | NO | N/A | N/A | N/A |
| GitHub | Negative | NO | N/A | N/A | N/A |

## Input Element Patterns

### Observed input types:
- **textarea**: QuillBot (`data-testid="ai-chat-input"`, placeholder="Ask me anything"), Phind (`id="phind-input"`, placeholder="Ask me anything..."), Mintlify (class `chat-assistant-input`, placeholder="Ask a question...")
- **contenteditable div**: Andi Search (class `rcw-input`, role=`textbox`, placeholder via CSS `::before`)
- **Not rendered initially**: Vercel, Supabase, Stripe — AI input only appears after user interaction

### Common placeholder text:
- "Ask me anything" (QuillBot)
- "Ask me anything..." (Phind)
- "Ask a question..." (Mintlify)
- "Ask Andi..." (Andi)

**Pattern: `Ask` + target/context + `...`**

### Common attributes on input elements:
- `placeholder` with "Ask..." pattern
- `data-testid` with `ai-chat-*` prefix (QuillBot)
- `role="textbox"` on contenteditable (Andi)
- `class` containing `chat-assistant-input` or `rcw-input`
- `rows="1"` with auto-resize behavior (Phind)

## Submit Button Patterns

| Site | Selector | Type | Contains |
|------|----------|------|----------|
| QuillBot | `button[data-testid="quill-chat-send-button"]` | button | Arrow SVG |
| Andi | `button.rcw-send[type="submit"]` | submit | Send icon img |
| Phind | `button.phind-send-btn#phind-send` | button | Arrow/paper-plane SVG |
| Mintlify | `button.chat-assistant-send-button` | button | Arrow-up SVG (Lucide) |

**Pattern**: Button with arrow/send SVG icon, `aria-label="Send message"` or similar.

## AI Indicator Icons (Sparkle SVGs)

### The "Sparkle" Icon Pattern

Multiple sites use a 4-pointed star (sparkle) SVG as the universal AI indicator:

**Mintlify sparkle** (found in both navigation and assistant toggle):
- Small star path: `M5.658,2.99l-1.263-.421-.421-1.263c-.137-.408-.812-.408-.949,0l...`
- Large star polygon: `points="9.5 2.75 11.412 7.587 16.25 9.5 11.412 11.413 9.5 16.25 7.587 11.413 2.75 9.5 7.587 7.587 9.5 2.75"`
- Button `aria-label="Toggle assistant panel"` with class containing `group/ai`

**Supabase sparkle** (Lucide library):
- Class: `lucide lucide-sparkles`
- Next to link text: "Start with Supabase AI prompts"

**Vercel sparkle/AI icon**:
- Near "AI Apps" navigation with path: `M8.40706 4.92939L8.5 4H9.5L9.59294 4.92939C9.82973 7.29734...`
- Also a chat bubble SVG near "Ask AI about this page"

**QuillBot sparkle** (in navigation):
- Path: `M11.259 7.505c.265-.673 1.217-.673 1.482 0l.68 1.725a2.393...` (4-pointed star)
- Inside a rounded container circle, used on AI Chat nav links

### Common Icon Library Classes
- `lucide-sparkles` (Lucide) — Supabase
- `heroicon-sparkles` (Heroicons)
- `bi-stars` (Bootstrap Icons)
- `fa-wand-magic-sparkles` (Font Awesome)
- Material Icons ligature: `auto_awesome`

### Detection heuristic for sparkle SVGs
Look for SVGs containing either:
1. `<polygon>` with 8+ point values forming a star shape
2. Multiple `<path>` elements creating concave 4-pointed star shapes
3. CSS classes containing: `sparkle`, `sparkles`, `stars`, `magic`, `auto_awesome`
4. Located inside buttons/links with AI-related text

## AI Button Text / Labels

### High-confidence trigger text:
- `"Ask AI"` — Vercel (button + link)
- `"Ask AI about this page"` — Vercel
- `"Toggle assistant panel"` — Mintlify
- `"Start with Supabase AI prompts"` — Supabase
- `"AI Chat"` — QuillBot (nav link)
- `"Send message"` — Mintlify (submit button)

### aria-label patterns:
- `aria-label="Ask AI"` (Vercel)
- `aria-label="Toggle assistant panel"` (Mintlify)
- `aria-label="Send message"` (Mintlify)
- `aria-label="Upload files"` (QuillBot)

### Common keywords in AI buttons/links:
`Ask AI`, `AI Chat`, `AI Assistant`, `Assistant`, `Generate`, `Copilot`

## CSS Variables for Hidden AI Panels

Sites that hide AI assistants behind a CSS variable:
- **Mintlify**: `--assistant-sheet-width: 0px` (expands to 368px)
- **Stripe**: `--assistant-width: 0px!important`

**Detection heuristic**: Look for CSS custom properties named `--assistant-*` or `--ai-*`.

## Container Patterns

### Regular DOM (most common):
- QuillBot, Andi, Phind, Mintlify, Vercel, Supabase, Stripe

### iframe-based widgets:
- **Tidio**: `iframe#tidio-chat-code` + `div#tidio-chat` (z-index 999999999, position fixed)
- **Intercom**: Loads via `window.Intercom()` JS SDK, injects iframe dynamically

### Shadow DOM:
- Not observed yet in this corpus

### Detection heuristics for iframe chat widgets:
- Fixed position div with very high z-index (999999999)
- iframe with title containing "chat", "widget", or vendor name
- Accompanying launcher div/button

## Positioning Patterns

1. **Full-page** (dedicated AI page): QuillBot, Andi, Phind — the URL IS the AI interface
2. **Side panel** (hidden, slides in): Mintlify (368px), Stripe (variable width)
3. **Dialog/modal** (hidden, opens on click): Vercel ("Ask AI" button triggers dialog)
4. **Command menu** (hidden, opens on Cmd+K): Supabase
5. **Floating fixed** (always visible): Tidio (bottom-right, fixed position)

## CSS Class Naming Patterns

| Vendor/Framework | Pattern | Examples |
|-----------------|---------|----------|
| Mintlify | `chat-assistant-*` | `chat-assistant-input`, `chat-assistant-send-button`, `chat-assistant-sheet-*` |
| QuillBot (MUI) | `data-testid="ai-chat-*"` | `ai-chat-input`, `ai-chat-attach-file`, `ai-chat-new-chat-button` |
| Phind | `phind-*` | `phind-input`, `phind-send-btn`, `phind-ai-container` |
| React Chat Widget | `rcw-*` | `rcw-input`, `rcw-send`, `rcw-widget-container` |
| Tidio | `#tidio-*` | `tidio-chat`, `tidio-chat-code` |
| Stripe | `StripeAssistant*` | `StripeAssistantContainer`, `StripeAssistant` |

## Negative Example Patterns (things that look like AI but aren't)

- **StackOverflow**: CSS class `ai-center` = `align-items: center` (layout utility, NOT AI)
- **StackOverflow**: "Ask Question" button = traditional Q&A form
- **Wikipedia**: Article text mentions "chatbot", "AI" — these are content, not interactive elements
- **Standard search**: `input[type="search"]` with `placeholder="Search"` (Wikipedia, SO)

## Disclaimer Text Patterns

AI-powered features often include disclaimers:
- **Mintlify**: "Responses are generated using AI and may contain mistakes"

## JS Global Objects

Vendor chat widgets inject globals:
- `window.Intercom()` — Intercom
- `window.__whtvr` — whtvr.ai
- `window.botpressWebChat` — Botpress

## Key Takeaways for Detection Rules

1. **Input types are diverse**: textarea, contenteditable, and sometimes not rendered at all
2. **Many AI interfaces are HIDDEN by default**: Require click/interaction to reveal
3. **Sparkle SVG icons** are the strongest visual AI indicator across sites
4. **Button text "Ask AI"** is a strong signal (Vercel uses it prominently)
5. **CSS variables `--assistant-*`** indicate hidden AI panels
6. **CSS classes** with `chat-assistant`, `ai-chat`, `ai-assistant` are strong signals
7. **Placeholder text "Ask..."** combined with textarea/contenteditable is a strong signal
8. **iframe-based chat widgets** use fixed positioning + high z-index
9. **`aria-label`** values like "Ask AI", "Toggle assistant panel" are reliable signals
10. **Negative signals**: `ai-center` CSS utility classes, article text mentioning AI
