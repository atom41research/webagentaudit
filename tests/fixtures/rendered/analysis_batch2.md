# Analysis Batch 2 - LLM/AI Chat Input Elements

## perplexity
- Has LLM/AI box: no (blocked by Cloudflare challenge)
- Input: N/A - page is a Cloudflare "Just a moment..." verification page, not the actual Perplexity UI
- Submit: N/A
- Container: regular DOM
- Position: N/A
- AI Icons: none (only Cloudflare spinner/verification icons)
- AI-related text: none
- Notable: The rendered DOM captured a Cloudflare Turnstile challenge page instead of the actual Perplexity search interface. The page title is "Just a moment..." with text "Performing security verification". Contains a hidden `cf-turnstile-response` input. The actual Perplexity AI search UI was not captured.

## vercel_docs
- Has LLM/AI box: hidden (Ask AI button triggers dialog)
- Input: not rendered in DOM (dialog opens on click, likely client-side rendered)
- Submit: N/A (not rendered until dialog opens)
- Trigger Button: tag=button, type="submit", aria-label="Ask AI", class contains "data-geist-button", text="Ask AI"
- Container: regular DOM
- Position: hidden (header button, requires click to open AI dialog)
- AI Icons: SVG sparkle/4-pointed-star icon found near "AI Apps" navigation link. The sparkle SVG path: `M8.40706 4.92939L8.5 4H9.5L9.59294 4.92939C9.82973 7.29734...` - a classic 4-pointed star shape (2 occurrences on page). This is used as a navigation menu icon for "AI Apps" section.
- AI-related text:
  - Button: "Ask AI" (aria-label="Ask AI") - appears twice (mobile + desktop header)
  - Link: "Ask AI about this page" (with chat bubble SVG icon)
  - Navigation: "AI Apps" menu item with sparkle SVG
  - Content: "AI SDK", "AI Gateway", "AI bot filtering", "AI-powered development assistant"
  - Search button: "Search Documentation" with keyboard shortcut Cmd+K
- Notable: Two separate "Ask AI" buttons exist (one for mobile `#docs-header-mobile`, one for desktop `#docs-header-desktop`). There is also an inline "Ask AI about this page" link below the page title. The search button is a separate element from the AI button. The AI dialog content is not present in the static DOM -- it is rendered client-side when the button is clicked. The sparkle SVG icon appears in the navigation menu under "AI Apps" solution link.

## supabase_docs
- Has LLM/AI box: hidden (search button opens command menu with AI)
- Input: not rendered in static DOM (command menu dialog opened via JS)
- Submit: N/A
- Trigger Button: tag=button, type="button", aria-haspopup="dialog", aria-expanded="false", aria-controls="command-menu-dialog-content", text="Search docs..."
- Container: regular DOM
- Position: hidden (header search button opens command menu dialog)
- AI Icons: Search icon (lucide-search SVG), Command key icon (lucide-command SVG). No explicit sparkle icon found in the rendered DOM.
- AI-related text:
  - Search button placeholder: "Search docs..."
  - The `aria-controls="command-menu-dialog-content"` ID suggests a command palette (cmdk-style)
  - No "Ask Supabase AI" text visible in the static rendered DOM (likely rendered client-side when command menu opens)
  - Content references to AI: Supabase has AI/Vector docs but no AI assistant text found in the homepage DOM
- Notable: The search button appears in both the desktop and mobile header navbars. It uses `aria-haspopup="dialog"` and `aria-controls="command-menu-dialog-content"`, indicating a dialog-based command menu. The AI assistant ("Ask Supabase AI") is likely a tab/mode within this command menu that is only rendered after opening. The command menu shortcut is Cmd+K displayed via a `<kbd>` element. Two identical search buttons exist (desktop nav + mobile nav).

## mintlify_docs
- Has LLM/AI box: hidden (dual: search dialog + assistant side panel)
- Input: placeholder="Ask a question..." (rendered as part of assistant panel, 4 occurrences found)
- Submit: N/A (not explicitly found as a standalone button)
- Trigger Buttons:
  - Search: tag=button, aria-label="Open search" (2 occurrences, mobile + desktop)
  - Assistant panel: tag=button, aria-label="Toggle assistant panel"
- Container: regular DOM
- Position: hidden (search opens modal dialog; assistant opens as a side sheet panel)
- AI Icons: Not explicitly sparkle icons found in search results, but the assistant panel is a distinct AI feature
- AI-related text:
  - "Toggle assistant panel" (aria-label on button)
  - "Ask a question..." (placeholder text, 4 occurrences)
  - "chat-assistant-sheet-open" / "chat-assistant-sheet-width" (localStorage keys for assistant state)
  - "--assistant-sheet-width" CSS variable (set to 0px when closed, 368px when open)
  - "data-page-mode" = "frame"
  - HTML root has: `data-banner-state="hidden"`, style `--assistant-sheet-width: 0px`
  - CSS class references: "chat-assistant" (16 occurrences), "assistant-sheet" (5 occurrences)
  - "AI-native" mentioned in meta description
- Notable: Mintlify has TWO distinct AI interaction modes: (1) A search dialog triggered by "Open search" buttons, and (2) A side-panel AI assistant (chat-assistant) that slides in from the right side with a configurable width (default 368px). The assistant state persists via localStorage keys "chat-assistant-sheet-open" and "chat-assistant-sheet-width". The HTML element has a `data-page-mode="frame"` attribute. The assistant panel is closed by default (`--assistant-sheet-width: 0px`). The "SearchBar" component exists in the DOM. This is a Mintlify-powered documentation site (mintlify.com/docs).

## phind_chat
- Has LLM/AI box: yes (full-page AI chat)
- Input: tag=textarea, id="phind-input", class="phind-input", placeholder="Ask me anything...", rows="1"
- Submit: tag=button, class="phind-send-btn", id="phind-send" (contains send/arrow SVG icon)
- Container: regular DOM (embedded within `.phind-ai-container`)
- Position: full-page (embedded chat widget, 700px tall container)
- AI Icons:
  - Logo icon: SVG with layered diamond/prism shape (paths: "M12 2L2 7L12 12L22 7L12 2Z", "M2 17L12 22L22 17", "M2 12L12 17L22 12") - used as bot avatar and header logo
  - Send button: Arrow/paper-plane SVG (path: "M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z")
  - Fullscreen button: Expand arrows SVG
- AI-related text:
  - "Hi! I'm your coding assistant" (bot welcome message)
  - "Ask me anything..." (textarea placeholder)
  - "Phind AI" (logo text)
  - "Phind AI Chat Revolutionizing Developer Search" (heading)
  - "Phind Chat is your AI coding assistant" (meta description)
  - "POPULAR" suggestions section with coding topics
  - Suggestion buttons: "Center a div", "JS promises", "Python list", "React hooks", etc.
- Notable: This is a WordPress site (phindai.org) with an embedded AI chat interface. The chat container is `.phind-ai-container` with `data-ip` attribute containing user IP. The chat has a vibrant purple/blue background (`.phind-bg`). Suggestions have popularity counts. The textarea auto-resizes (style="height: 41px"). Plugin files: `phind-ai-style.css` and `phind-ai-script.js` (v2.5.0). The container is 700px x 100% with `.phind-chat-wrapper` layout.

## intercom_fin
- Has LLM/AI box: no (marketing homepage, no visible chat widget in rendered DOM)
- Input: N/A (no chat input rendered in static DOM)
- Submit: N/A
- Container: regular DOM
- Position: N/A (chat widget not rendered -- Intercom messenger loads via JS)
- AI Icons: No sparkle or AI-specific SVG icons in the rendered DOM for chat purposes
- AI-related text:
  - "The AI customer service company" (page title)
  - "Fin is the leading AI Agent for customer service" (meta description)
  - Intercom messenger hooks in JS: `window.Intercom("onHide"...)`, `window.Intercom("onShow"...)`
  - Events: "intercom-messenger-on-hide", "intercom-messenger-on-show", "intercom-messenger-on-useremailsupplied"
- Notable: This is Intercom's marketing homepage (www.intercom.com). The Intercom Messenger widget is referenced in JavaScript event handlers but its actual DOM (iframe/widget) is NOT present in the rendered HTML. The messenger would typically inject itself via the Intercom JS SDK into an iframe. The page has extensive OneTrust cookie consent SDK styling. No `data-intercom` attributes or Intercom launcher button found in the rendered DOM. The Fin AI agent is marketed on the page but no interactive chat element is rendered. The Intercom messenger integration hooks exist (`window.Intercom("onHide",...)`) suggesting the widget loads dynamically but was not captured in this render.

## tidio
- Has LLM/AI box: yes (Tidio chat widget, loaded via iframe)
- Input: not rendered in static DOM (lives inside Tidio iframe)
- Submit: N/A (inside iframe)
- Container: iframe (id="tidio-chat-code", title="Tidio Chat code", style="display: none;")
- Position: floating bottom-right (div#tidio-chat, class="needsclick", style="z-index: 999999999 !important; position: fixed;")
- AI Icons: N/A (all UI is inside the iframe, not accessible from main DOM)
- AI-related text:
  - "AI Customer Service Agent, Customer Support Software | Tidio" (page title)
  - Tidio chat script: `//code.tidio.co/w0i4b7fdeerfqqn4w8lwb7ahjasjnrmd.js`
  - AI detection script: sets `is_chatgpt` contact property based on referrer (chatgpt.com or perplexity.ai)
  - Lyro AI references in chunk URLs: "lyro-guidance", "lyro-actions", "ai-agent", "product-recommendations"
  - "ai-agent/playground" page chunk loaded
- Notable: Tidio uses two elements: (1) `iframe#tidio-chat-code` (hidden, title="Tidio Chat code") and (2) `div#tidio-chat` (fixed position, z-index 999999999). The iframe content is not accessible from the main DOM. An interesting tracking script detects if the visitor came from ChatGPT or Perplexity AI and sets a `is_chatgpt` contact property. Tidio's AI agent is called "Lyro" based on script chunk names. There is also an `iframe[owner="archetype"]` element (display:none). The chat widget is loaded via the Tidio JS SDK script.

## stripe_docs
- Has LLM/AI box: hidden (StripeAssistant container present, likely requires interaction)
- Input: placeholder="Search" (search input found)
- Submit: N/A for AI assistant specifically
- Container: regular DOM, plus an iframe for HCaptcha and one for Google Tag Manager
- Position: hidden (StripeAssistant container present but likely collapsed/hidden)
- AI Icons: N/A (no sparkle icons found in search results)
- AI-related text:
  - Class: "StripeAssistantContainer" - a wrapper div in the main app structure
  - Class: "StripeAssistant" - referenced in DOM
  - CSS: `--assistant-width: 0px!important` (assistant panel hidden/collapsed by default)
  - Search input: placeholder="Search"
  - Structure: `.StripeAssistantContainer > .Shell > .Header`
- Notable: The Stripe docs have a `StripeAssistantContainer` class that wraps the entire page shell. The CSS variable `--assistant-width: 0px!important` suggests an AI assistant side panel that can expand (similar to Mintlify). The main search has a simple `placeholder="Search"` input. The page uses obfuscated CSS class names (e.g., `as-3`, `as-7u`, `sn-182o7r0`). An HCaptcha iframe is present. The assistant is integrated at the layout level but collapsed by default.

## stackoverflow
- Has LLM/AI box: no (NEGATIVE example - traditional Q&A site)
- Input: tag=input, name="q", type="text", placeholder="Search...", class="s-input s-input__search js-search-field", aria-label="Search", role="combobox", autocomplete="off"
- Submit: N/A (search form, not AI chat)
- Container: regular DOM
- Position: inline (search bar in top navigation header)
- AI Icons: none
- AI-related text:
  - "ai-center" (Stacks CSS utility class for `align-items: center` -- NOT AI-related, just a layout class)
  - "Ask Question" button (traditional Q&A, not AI)
  - "Policy: Generative AI (e.g., ChatGPT) is banned" (community bulletin link)
  - "AI-driven Design to Print platform" (question title, user content)
  - Chat link: `chat.stackoverflow.com` (traditional chat rooms, not AI)
- Notable: This is a NEGATIVE example. StackOverflow has NO AI chat input or assistant. The `ai-center` CSS classes throughout the page are Stacks design system utility classes for flexbox alignment (`align-items: center`), not AI-related. The search is a standard text search (`input[name="q"]` with `role="combobox"`). The "Ask Question" button links to the traditional Q&A form. There is a prominent community policy link: "Policy: Generative AI (e.g., ChatGPT) is banned". The page uses StackOverflow's Stacks design system.

---

## Summary Table

| Page | Has AI Box | Type | Trigger | Container | Position |
|------|-----------|------|---------|-----------|----------|
| perplexity | no (blocked) | N/A | N/A | N/A | N/A |
| vercel_docs | hidden | AI dialog | "Ask AI" button (aria-label) | regular DOM | header button |
| supabase_docs | hidden | command menu w/ AI | Search button (aria-haspopup="dialog") | regular DOM | header button |
| mintlify_docs | hidden | search dialog + assistant panel | "Open search" + "Toggle assistant panel" buttons | regular DOM | header + side panel |
| phind_chat | yes | embedded chat | always visible | regular DOM | full-page (700px container) |
| intercom_fin | no | messenger (not rendered) | Intercom JS SDK (not in DOM) | iframe (not rendered) | floating (not rendered) |
| tidio | yes | chat widget | always present (div#tidio-chat) | iframe#tidio-chat-code | floating fixed bottom |
| stripe_docs | hidden | assistant container | unknown trigger | regular DOM | side panel (collapsed) |
| stackoverflow | no | NEGATIVE | N/A | N/A | N/A |

## Key Detection Patterns

### Sparkle/Star SVG Icons
- **Vercel**: 4-pointed star path `M8.40706 4.92939L8.5 4H9.5L9.59294 4.92939C9.82973 7.29734...` used near "AI Apps" navigation link

### AI-related Button Labels
- **Vercel**: `aria-label="Ask AI"`, text "Ask AI", "Ask AI about this page"
- **Mintlify**: `aria-label="Toggle assistant panel"`, `aria-label="Open search"`, placeholder="Ask a question..."
- **Supabase**: `aria-controls="command-menu-dialog-content"` with search icon

### CSS Variables for Assistant Panels
- **Mintlify**: `--assistant-sheet-width: 0px` (368px when open)
- **Stripe**: `--assistant-width: 0px!important`

### Chat Widget Iframes
- **Tidio**: `iframe#tidio-chat-code` + `div#tidio-chat` (fixed position, z-index 999999999)
- **Intercom**: Referenced via `window.Intercom()` but not rendered in static DOM

### Search Inputs (non-AI)
- **StackOverflow**: `input[name="q"]`, placeholder="Search...", aria-label="Search", role="combobox"
- **Stripe**: placeholder="Search"

### Negative Indicators
- **StackOverflow**: `ai-center` classes are CSS alignment utilities (align-items: center), NOT AI indicators
- **StackOverflow**: "Ask Question" is traditional Q&A form, not AI chat
