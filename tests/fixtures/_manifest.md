# Test Fixtures Manifest

HTML page fixtures collected from real websites for chat widget / LLM interface detection testing.

Fetched on: 2026-03-10

---

## First-party LLM prompt composers

### `gemini_prompt_composer.html`
- **Source URL:** https://gemini.google.com/app
- **Captured:** 2026-07-14
- **Description:** Sanitized live DOM fragment for Gemini's contenteditable prompt composer.

### `openai_prompt_composer.html`
- **Source URL:** https://openai.com/
- **Captured:** 2026-07-14
- **Description:** Sanitized live DOM fragment for OpenAI's homepage ChatGPT prompt form.

---

## Fixtures with confirmed chat widget embed scripts

### `chatbase_widget.html`
- **Source URLs:** https://billhuscher.com/, https://ruggedrestore.com/,
  https://registocriminal.justica.gov.pt/, https://safespacebuildings.com/
- **Captured:** 2026-07-14
- **Description:** Sanitized current Chatbase launcher, iframe, composer, and
  assistant-message structure.
- **Provider:** Chatbase

### `chatbase_delayed_bootstrap.html`
- **Derived from:** `chatbase_widget.html`
- **Description:** Replayable cold-load variant that withholds all provider
  evidence until after the initial page-settle window, then renders Rugged
  Restore's runtime Chatbase launcher DOM without relying on an embed-script
  signature, followed by the iframe, composer, and assistant-message structure.
- **Provider:** Chatbase

### `denser_embed_widget.html`
- **Source URLs:** https://denser.ai/, https://www.eos.com.au/, https://premiere-concierge.com/
- **Captured:** 2026-07-14
- **Description:** Sanitized, replayable Denser embed structure preserving the live shadow-root launcher, iframe, composer, assistant bubble, transient scroll control, and competing lead-form submit control.
- **Detection signals:**
  - `<denser-chatbot>` custom element
  - `button[part="button"]` launcher
  - `iframe[title="Denser Chatbot"]`
  - `textarea#message`
- **Provider:** Denser

### `crisp_crisp.html`
- **Source URL:** https://crisp.chat/en/
- **Description:** Crisp's own homepage. Contains the Crisp chat widget embedded in static HTML.
- **Detection signals:**
  - `crisp.chat` domain references
  - `$crisp` JavaScript global
  - `CRISP_WEBSITE_ID` configuration variable
- **Provider:** Crisp

### `custom_chatbot_tawk.html`
- **Source URL:** https://www.tawk.to
- **Description:** tawk.to's own homepage. Contains the tawk.to chat widget embed script in static HTML.
- **Detection signals:**
  - `Tawk_API` JavaScript global
  - `embed.tawk.to` script source (e.g., `https://embed.tawk.to/521727297ca1334016000005/18nms7gql`)
  - `tawkto-signup-form` plugin references
- **Provider:** tawk.to

### `custom_chatbot_livechat.html`
- **Source URL:** https://www.livechat.com
- **Description:** LiveChat's own homepage. Contains both the LiveChat widget and a HubSpot tracking script.
- **Detection signals:**
  - `cdn.livechatinc.com/tracking.js` script source
  - `window.__lc.license = 19196658` configuration
  - `LiveChatWidget` JavaScript API (`LiveChatWidget.on`, `LiveChatWidget.get`, `LiveChatWidget.call`)
  - Also contains: `hs-script-loader` (HubSpot tracking, `//js-eu1.hs-scripts.com/26269451.js`)
- **Provider:** LiveChat (+ HubSpot tracking)

### `livechat_delayed_widget.html`
- **Derived from:** A saved 2026-07-19 standalone LiveChat runtime diagnostic;
  it is not treated as evidence that Rugged Restore changed providers.
- **Description:** Replayable delayed standalone LiveChat lifecycle. It renders
  the minimized launcher iframe after the initial provider-detection window
  begins and the conversation
  iframe after the launcher click. The `history=1` variant starts with an old
  detector match and returns a safe new answer, proving response collection
  excludes persisted transcript content.
- **Detection signals:**
  - `iframe#chat-widget-minimized`
  - `iframe#chat-widget`
  - `textarea#message`
- **Provider:** LiveChat

### `livechat_multilingual_gate.html`
- **Derived from:** The 2026-07-19 EasyTrack LiveChat iframe DOM supplied by
  the operator.
- **Description:** Hungarian pre-conversation state with LiveChat's stable
  `#start-chat-button`, hashed styling classes, structural transcript roles,
  and composer/send controls whose visible and accessible text is not English.
  It verifies that discovery and replay advance the gate and use provider-frame
  structure instead of translated keywords.
- **Detection signals:**
  - `iframe#chat-widget`
  - `#start-chat-button`
  - `[role="grid"][aria-live="polite"]`
- **Provider:** LiveChat

### `insait_delayed_widget.html`
- **Derived from:** A headed 2026-07-19 cold-load inspection of
  https://reducemypayment.com/.
- **Description:** An unknown-provider chat iframe whose shell and lower-right
  SVG send button render before its textarea. The composer appears after a
  bounded delay. Discovery must poll the recognized frame without treating the
  submit control as a launcher or reloading the host page.
- **Detection signals:**
  - `iframe#insait-chat-frame[title="Chatbot Assistant"]`
  - `[data-testid="widget-send-button"]`
  - delayed `textarea#composer`
- **Provider:** Insait (generic discovery; no canonical provider route)

### `custom_chatbot_hubspot.html`
- **Source URL:** https://www.hubspot.com
- **Description:** HubSpot's own homepage. Contains the HubSpot script loader which powers their chat widget.
- **Detection signals:**
  - `<script defer id="hs-script-loader" src="/hs/scriptloader/53.js?businessUnitId=0">`
  - References to chatbot builder and live chat in footer links
- **Provider:** HubSpot

### `custom_chatbot_zendesk.html`
- **Source URL:** https://www.zendesk.com
- **Description:** Zendesk's own homepage. Contains the Zendesk Web Widget (Classic) loader.
- **Detection signals:**
  - `static.zdassets.com` script source references
  - `zendesk_hostname` JavaScript configuration
  - Zendesk domain pattern matching in scripts
- **Provider:** Zendesk

### `custom_chatbot_olark.html`
- **Source URL:** https://www.olark.com
- **Description:** Olark's own homepage. Contains a complete Olark chat widget embed with initialization code.
- **Detection signals:**
  - `static.olark.com/jsclient/loader.js` script source
  - `olark.identify('9353-431-10-4341')` initialization call
  - `window.olark` JavaScript global
  - `olark.com/js/analytics-free.min.js` analytics script
- **Provider:** Olark

### `custom_chatbot_helpscout.html`
- **Source URL:** https://www.helpscout.com
- **Description:** Help Scout's own homepage. Contains the Help Scout Beacon widget.
- **Detection signals:**
  - `beacon-2.helpscout.net` domain references
  - `Beacon()` JavaScript API calls
  - `hs-beacon` related identifiers
  - `helpscout` brand references throughout
- **Provider:** Help Scout (Beacon)

### `custom_chatbot_chatwoot.html`
- **Source URL:** https://www.chatwoot.com
- **Description:** Chatwoot's own homepage. Contains the Chatwoot SDK widget embed.
- **Detection signals:**
  - `chatwootSDK` JavaScript reference
  - `app.chatwoot.com` domain
  - `websiteToken` configuration parameter
- **Provider:** Chatwoot

---

## Product pages (widget loads dynamically, not in static HTML)

### `intercom_intercom.html`
- **Source URL:** https://www.intercom.com
- **Description:** Intercom's own homepage. The page is a Next.js SPA rendered as a single line of HTML. Contains extensive references to Intercom products (Fin AI agent, Intercom Suite, etc.) but the Intercom Messenger widget itself is loaded dynamically via JavaScript and is NOT present in the static HTML.
- **Detection signals (content-based, not embed scripts):**
  - `intercom` brand name throughout page content and metadata
  - References to "Fin" AI agent product
  - `/intercom-marketing-site/` asset paths
- **Note:** Useful for testing content-based heuristics rather than script-based detection.
- **Provider:** Intercom (product page, no widget embed in static HTML)

### `tidio_tidio.html`
- **Source URL:** https://www.tidio.com
- **Description:** Tidio's own homepage. Next.js SPA rendered as a single long line. Contains references to Tidio as a product/brand but the Tidio chat widget code (`code.tidio.co`, `tidioChatCode`) is NOT present in the static HTML -- it is loaded dynamically.
- **Detection signals (content-based, not embed scripts):**
  - `tidio` brand name in metadata and content
- **Note:** Useful for testing content-based heuristics rather than script-based detection.
- **Provider:** Tidio (product page, no widget embed in static HTML)

### `custom_chatbot_freshdesk.html`
- **Source URL:** https://www.freshworks.com
- **Description:** Freshworks homepage. Next.js SPA. Mentions Freshchat/Freshdesk as products but does NOT embed the Freshchat widget (`fcWidget`) in static HTML.
- **Detection signals (content-based, not embed scripts):**
  - `freshworks` brand references
  - Product mentions of Freshchat, Freshdesk
- **Note:** Useful for testing content-based heuristics. No actual chat widget embed code.
- **Provider:** Freshworks (product page, no widget embed in static HTML)

---

## Negative fixtures (no chat widget)

### `no_chatbot_example.html`
- **Source URL:** https://example.com
- **Description:** IANA example domain. Minimal HTML page with no JavaScript, no chat widgets, no third-party scripts. The simplest possible negative test case.
- **Detection signals:** None. Should trigger zero detections.
- **Provider:** None

### `no_chatbot_wikipedia.html`
- **Source URL:** https://en.wikipedia.org/wiki/Main_Page
- **Description:** Wikipedia Main Page. Complex HTML with lots of content but no chat widgets or third-party chat scripts.
- **Detection signals:** None. Should trigger zero detections.
- **Provider:** None

### `no_chatbot_craigslist.html`
- **Source URL:** https://www.craigslist.org
- **Description:** Craigslist homepage. Simple HTML, no chat widgets, no third-party chat scripts.
- **Detection signals:** None. Should trigger zero detections.
- **Provider:** None

---

## Summary table

| File | Provider | Widget in static HTML? | Key detection pattern |
|------|----------|----------------------|----------------------|
| `chatbase_widget.html` | Chatbase | Yes (replayable live structure) | `#chatbase-bubble-button`, `#message` |
| `chatbase_delayed_bootstrap.html` | Chatbase | Delayed after navigation | `#chatbase-bubble-button`, `#chatbase-bubble-window` |
| `livechat_delayed_widget.html` | LiveChat | Delayed after navigation and launcher click | `iframe#chat-widget-minimized`, `iframe#chat-widget` |
| `flyweight_widget.html` | Flyweight AI | Yes (RX Smart Gear runtime structure) | `iframe[data-testid="chat-overlay"]`, `#chat-button` |
| `denser_embed_widget.html` | Denser | Yes (replayable live structure) | `denser-chatbot`, `iframe[title="Denser Chatbot"]` |
| `crisp_crisp.html` | Crisp | Yes | `$crisp`, `CRISP_WEBSITE_ID` |
| `custom_chatbot_tawk.html` | tawk.to | Yes | `Tawk_API`, `embed.tawk.to` |
| `custom_chatbot_livechat.html` | LiveChat (+HubSpot) | Yes | `LiveChatWidget`, `cdn.livechatinc.com`, `__lc.license` |
| `custom_chatbot_hubspot.html` | HubSpot | Yes | `hs-script-loader` |
| `custom_chatbot_zendesk.html` | Zendesk | Yes | `static.zdassets.com` |
| `custom_chatbot_olark.html` | Olark | Yes | `olark.identify`, `static.olark.com/jsclient` |
| `custom_chatbot_helpscout.html` | Help Scout | Yes | `Beacon()`, `beacon-2.helpscout.net` |
| `custom_chatbot_chatwoot.html` | Chatwoot | Yes | `chatwootSDK`, `app.chatwoot.com` |
| `intercom_intercom.html` | Intercom | No (dynamic) | Brand mentions only |
| `tidio_tidio.html` | Tidio | No (dynamic) | Brand mentions only |
| `custom_chatbot_freshdesk.html` | Freshworks | No (dynamic) | Brand mentions only |
| `no_chatbot_example.html` | None | N/A | No signals |
| `no_chatbot_wikipedia.html` | None | N/A | No signals |
| `no_chatbot_craigslist.html` | None | N/A | No signals |
