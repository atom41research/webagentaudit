# Rendered DOM Analysis Notes: LLM/AI Chat Input Elements

## 1. QuillBot AI Chat (`quillbot_ai_chat/rendered_dom.html`)

**Has LLM box: YES**

### Input Element

- **Tag:** `<textarea>`
- **Selector:** `textarea[data-testid="ai-chat-input"]`
- **CSS classes:** `MuiInputBase-input MuiInputBase-inputMultiline css-1j9el04`
- **Placeholder:** `"Ask me anything"`
- **data-testid:** `ai-chat-input`
- **Parent wrapper class:** `MuiInputBase-root MuiInputBase-multiline css-1dld18n` (has Mui-focused variant)
- **Note:** There is a secondary hidden `<textarea>` (aria-hidden, readonly, tabindex=-1) used by MUI for auto-sizing. Only the first textarea is the real input.

### Submit Mechanism

- **Tag:** `<button>`
- **Selector:** `button[data-testid="quill-chat-send-button"]`
- **CSS classes:** `MuiButtonBase-root MuiIconButton-root MuiIconButton-sizeMedium css-hvk3mx`
- **type:** `button`
- **role:** `button`
- **Style:** `background-color: rgb(0, 136, 71); max-height: 40px;`
- **Contains:** An SVG arrow icon (right-pointing arrow path)

### Additional Buttons

- **Attach file:** `button[data-testid="ai-chat-attach-file"]` with `aria-label="Upload files"`
- **Chat tools trigger:** `button[data-testid="quill-chat-tools-trigger"]` (MUI text button with icon)
- **New chat:** `button[data-testid="ai-chat-new-chat-button"]`
- **Chat history:** `button[data-testid="ai-chat-open-chat-history-button"]`

### Container Type

- **Regular DOM** (no iframe, no shadow DOM for the chat input)
- The only iframe is a reCAPTCHA and a GTM noscript iframe -- neither contains chat UI
- Root container: `div#root-client`

### Position

- **Full-page / inline** -- The AI Chat is the primary page content, not a floating widget
- The page URL is `/ai-chat` and the entire page is dedicated to the chat interface
- Component tree (from CMS config): `AIChatContext > AIChatHistory + AIChatInput`
- Max width container: 720px, centered

### AI Icon SVGs Found

- **Sparkle/star icon** used as the AI Chat nav icon in both sidebar and mobile nav
  - SVG viewBox: `0 0 24 24`, fill: `#2c3e5d`
  - Key path: `M11.259 7.505c.265-.673 1.217-.673 1.482 0l.68 1.725a2.393...` (4-pointed sparkle shape)
  - Wrapped in a circle/rounded-square border (second path draws the container)
  - Used on: `a[href="/ai-chat"]` sidebar links, `a[href="/ai-chat?referrer=side_navbar"]`
  - Container class: `div.icon.MuiBox-root`
- **Premium diamond icon:** SVG with `type="premiumIcon"` (not AI-related, it's for upgrade)

### Notable Patterns

- Uses **MUI (Material UI)** component library throughout (MuiInputBase, MuiButton, MuiIconButton, MuiSvgIcon)
- CMS-driven layout: Component tree defined in JSON (`AIChatContext`, `AIChatHistory`, `AIChatInput` components with i18nKey props)
- Micro-frontend architecture: Uses SystemJS import maps to load `@quillbot/ai-chat`, `@quillbot/ai-chat-core`, `@quillbot/ai-chat-page`, `@quillbot/ai-chat-view` as separate packages
- All data-testid attributes follow `ai-chat-*` or `quill-chat-*` naming conventions
- The input has `style="height: 23px; overflow: hidden;"` suggesting auto-resize behavior

---

## 2. Andi Search (`andi_search/rendered_dom.html`)

**Has LLM box: YES**

### Input Element

- **Tag:** `<div>` with `contenteditable="true"`
- **Selector:** `div.rcw-input[contenteditable="true"]`
- **CSS class:** `rcw-input`
- **role:** `textbox`
- **Placeholder:** `"Ask Andi..."` (via CSS `content: attr(placeholder)` on `:empty::before`)
- **spellcheck:** `true`
- **Parent wrapper class:** `rcw-new-message`

### Submit Mechanism

- **Tag:** `<button>`
- **Selector:** `button.rcw-send[type="submit"]`
- **CSS class:** `rcw-send`
- **type:** `submit`
- **Contains:** An `<img>` with `class="rcw-send-icon"` and `alt="Send"` (base64-encoded SVG of a send/arrow icon)

### Additional Buttons

- **Emoji picker:** `button.rcw-picker-btn[type="submit"]` with a smiley face SVG icon
- **Close button:** `button.rcw-close-button` with an X icon
- **Launcher button:** `button.rcw-launcher.rcw-hide-sm` with `aria-controls="rcw-chat-container"`
- **Suggestion buttons:** Multiple `button.lw-suggestions-button` elements with predefined queries like "interpret my dreams", "Who is Baby Yoda?", etc.

### Container Type

- **Regular DOM** (no iframe, no shadow DOM)
- Uses **react-chat-widget (rcw)** library -- identifiable by `rcw-*` class prefix
- Container hierarchy: `div.rcw-widget-container > div#rcw-conversation-container.active`
- Root: `div#root`

### Position

- **Full-page / inline** -- The chat is the central UI of the page
- Layout: Three-column grid (`ui grid`) with left nav panel, center chat column (8-wide), and right info column (6-wide)
- The chat column has class `_lwColumnChat_1g1s7_1`
- The conversation container has `aria-live="polite"` for accessibility

### AI Icon SVGs Found

- **No sparkle/star SVG icons found** in the rendered DOM
- All SVGs are base64-encoded inline images (social media icons: LinkedIn, Twitter/X, Discord, TikTok)
- The close/send/picker icons are also base64-encoded SVGs in `<img>` tags, not inline `<svg>` elements
- Robot mascot image: `robot-clouds-C-Y3Og1e.png` (raster, not SVG)

### Notable Patterns

- Uses **react-chat-widget** (`rcw-*` classes) as the chat framework
- Uses **Semantic UI** (`ui grid`, `ui image`, `ui segment`, etc.) for layout
- Uses **styled-components** (v6.3.9) -- `data-styled="active"` attribute present
- Custom CSS variables for chat: `--chat-height`, `--chat-background`, `--chat-font-size`, `--hero-chat-banner-width`
- Custom analytics attributes: `data-andi-event`, `data-andi-action`, `data-andi-channel`
- JSON-LD structured data marks it as a `WebApplication` with `applicationCategory: "SearchApplication"`
- The welcome message uses the Andi brand: "Hello! I'm Andi, your friendly search assistant. What are you looking for?"
- Image preview overlay: `div##rcw-image-preview` (note the double `#` -- likely a bug in the original code)

---

## 3. Wikipedia - Large Language Model Article (`wikipedia_llm/rendered_dom.html`)

**Has LLM box: NO** (negative example -- confirmed)

### Input Elements Present (NOT LLM chat boxes)

1. **Header search input:**
   - Tag: `<input>`
   - Selector: `input#searchInput.cdx-text-input__input.mw-searchInput`
   - type: `search`
   - placeholder: `"Search Wikipedia"`
   - aria-label: `"Search Wikipedia"`
   - accesskey: `f`
   - This is a standard Wikipedia site search, NOT an AI/LLM chat input

2. **Sticky header search input:**
   - Tag: `<input>`
   - Selector: `input.cdx-text-input__input.mw-searchInput` (inside `form#vector-sticky-search-form`)
   - type: `search`
   - placeholder: `"Search Wikipedia"`
   - Duplicate of header search for the sticky navigation bar

### Submit Mechanism (for search only)

- **Tag:** `<button>`
- **Selector:** `button.cdx-button.cdx-search-input__end-button`
- **Text content:** `"Search"`
- Part of the standard Wikipedia search form

### Container Type

- **Regular DOM** (no iframe, no shadow DOM)
- Standard MediaWiki Vector-2022 skin layout

### Position

- Search inputs are in the **header** (standard site navigation), not floating or inline chat
- The page content is an encyclopedic article about Large Language Models

### AI Icon SVGs Found

- **None** -- No sparkle, star, or AI indicator SVGs
- The page references "chatbot" and "prompt" only as article content (text), not as interactive elements

### Notable Patterns

- Standard Wikipedia/MediaWiki page structure with Vector-2022 skin
- Uses Codex Design System components (`cdx-*` classes)
- The article content discusses LLMs, chatbots, prompt engineering -- but these are article text, not interactive AI elements
- All interactive elements are standard Wikipedia functionality (search, edit links, TOC navigation)
- No third-party chat widgets, floating assistants, or AI chat integrations detected

---

## Summary Comparison Table

| Property | QuillBot AI Chat | Andi Search | Wikipedia LLM |
|---|---|---|---|
| Has LLM box | YES | YES | NO |
| Input tag | `<textarea>` | `<div contenteditable>` | `<input type="search">` (not LLM) |
| Input selector | `textarea[data-testid="ai-chat-input"]` | `div.rcw-input[contenteditable="true"]` | `input#searchInput` |
| Placeholder text | "Ask me anything" | "Ask Andi..." | "Search Wikipedia" |
| Submit button | `button[data-testid="quill-chat-send-button"]` | `button.rcw-send[type="submit"]` | N/A |
| Container type | Regular DOM | Regular DOM | Regular DOM |
| Position | Full-page (dedicated chat page) | Full-page (central UI) | Header search only |
| AI sparkle SVGs | Yes (nav icon, 4-pointed star in rounded square) | No (base64 images only) | No |
| UI framework | MUI (Material UI) | react-chat-widget + Semantic UI | MediaWiki Codex |
| Architecture | Micro-frontend (SystemJS) | Monolithic React app | Server-rendered MediaWiki |
