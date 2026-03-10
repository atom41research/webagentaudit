# LLM & AI Chatbot Vendor Registry

Comprehensive registry of known LLM/AI chatbot services, their URLs, SDK patterns, and API endpoints.
Used by the detection module to identify LLM-powered interfaces on webpages.

---

## Category 1: Direct LLM Applications

These are websites where the URL IS the LLM chat interface. Detection means recognizing
you're on one of these sites.

### ChatGPT (OpenAI)

- **Category**: direct_llm_app
- **URLs**: `chatgpt.com`, `chat.openai.com`
- **API base**: `https://api.openai.com/v1`
- **API patterns**: `/v1/chat/completions`, `/v1/responses`
- **Identifiers**: OpenAI branding, `oai-` prefixed cookies

### Claude (Anthropic)

- **Category**: direct_llm_app
- **URLs**: `claude.ai`
- **API base**: `https://api.anthropic.com`
- **API patterns**: `/v1/messages`
- **Identifiers**: Anthropic branding

### Google Gemini

- **Category**: direct_llm_app
- **URLs**: `gemini.google.com`
- **API base**: `https://geminiweb-pa.clients6.google.com`
- **Internal UI class**: `BardChatUi`
- **API patterns**: `generativelanguage.googleapis.com/v1beta/models`
- **Identifiers**: `WIZ_global_data` config object, references to `gemini-2.0-flash`, `gemini-2.5-flash`

### Microsoft Copilot

- **Category**: direct_llm_app
- **URLs**: `copilot.microsoft.com`
- **Identifiers**: "Message Copilot" input placeholder, `$_TSR.router` routing system, 10240 char limit on input
- **Modes**: "Quick response", "Real talk", "Think deeper", search, task

### Perplexity

- **Category**: direct_llm_app
- **URLs**: `perplexity.ai`, `www.perplexity.ai`
- **Identifiers**: Search/chat hybrid interface

### HuggingChat

- **Category**: direct_llm_app
- **URLs**: `huggingface.co/chat`, `huggingface.co/chat/`
- **Sub-paths**: `/chat/models`, `/chat/settings/application`, `/chat/settings/omni`
- **Identifiers**: `window.plausible` analytics, `dark` class on `document.documentElement`, 126+ model references
- **Meta**: `<meta name="theme-color" content="#07090d">`

### Poe

- **Category**: direct_llm_app
- **URLs**: `poe.com`
- **Identifiers**: Multi-model chat aggregator by Quora

### You.com

- **Category**: direct_llm_app
- **URLs**: `you.com`, `you.com/?chatMode=default`
- **API**: `https://you.com/apis` (search API for RAG)
- **Developer docs**: `docs.you.com`
- **DOM selectors**: `.nav2_component`, `[data-dropdown='wrap']`, `[data-shader="canvas"]`

### Groq

- **Category**: direct_llm_app
- **URLs**: `groq.com` (marketing), `console.groq.com` (playground)
- **Chat playground**: `console.groq.com/playground`
- **API base**: `https://api.groq.com/openai/v1` (OpenAI-compatible)
- **API key management**: `console.groq.com/keys`
- **Identifiers**: HubSpot form portal `44341333`

### Mistral (Le Chat)

- **Category**: direct_llm_app
- **URLs**: `chat.mistral.ai`
- **API base**: `https://api.mistral.ai/v1`
- **API patterns**: `/v1/chat/completions`

### DeepSeek

- **Category**: direct_llm_app
- **URLs**: `chat.deepseek.com`
- **API base**: `https://api.deepseek.com`
- **API patterns**: `/v1/chat/completions` (OpenAI-compatible)

### xAI Grok

- **Category**: direct_llm_app
- **URLs**: `grok.com` (primary chat UI), `x.ai` (company site)
- **Note**: `grok.x.ai` redirects to `x.ai`
- **WebSocket**: `wss://grok-v2.x.ai/ws/app_chat/stream_audio` (voice mode)
- **Model references**: `grok-3`, `grok-4-mini-thinking-tahoe`
- **Config**: `short_id_to_model_id_map` in server config object
- **Framework**: Next.js SSR

### Pi (Inflection AI)

- **Category**: direct_llm_app
- **URLs**: `pi.ai`
- **Identifiers**: Conversational personal AI

---

## Category 2: Embeddable AI/LLM SDK Vendors

These provide chat widgets that websites embed. Detection means finding their scripts,
DOM elements, or API patterns on third-party pages.

### whtvr.ai

- **Category**: embeddable_sdk
- **Company URL**: `whtvr.ai`
- **SDK/API endpoint**: `api.whtvr.ai/api/sdk/chat`
- **Description**: AI-powered conversational layers for websites
- **Script patterns**: Unknown (dashboard-generated)
- **DOM signatures**: Unknown (needs further investigation)

### Voiceflow

- **Category**: embeddable_sdk
- **Company URL**: `voiceflow.com`
- **Docs**: `docs.voiceflow.com`
- **Script patterns**: Widget likely loaded from `cdn.voiceflow.com` or dynamically generated
- **DOM signatures**: Unknown (documentation not fully public)
- **Notes**: Provides visual conversation design platform; widget details in authenticated docs

### Botpress

- **Category**: embeddable_sdk
- **Company URL**: `botpress.com`
- **Docs**: `botpress.com/docs`
- **Script URL**: `https://cdn.botpress.cloud/webchat/v2.3/inject.js` (version may change: `v2.x`)
- **CDN pattern**: `cdn.botpress.cloud/webchat/v*`
- **Global object**: `window.botpress`
- **Initialization**:
  ```javascript
  window.botpress.init({
    botId: "<BOT_ID>",
    clientId: "<CLIENT_ID>",
    selector: "body"
  });
  ```
- **DOM elements**:
  - `iframe#webchat-root` — main chat iframe
  - `iframe#fab-root` — floating action button iframe
- **CSS classes**: `.bpOpen`, `.bpClose` (visibility toggle)
- **Events**: `webchat:initialized`
- **Methods**: `open()`, `close()`, `toggle()`, `sendMessage()`, `sendEvent()`, `updateUser()`, `getUser()`
- **State tracking**: `window.botpress.state` = `"opened"` | `"closed"` | `"initial"`

### Ada

- **Category**: embeddable_sdk
- **Company URL**: `ada.cx`
- **Docs**: `docs.ada.cx`
- **Script URL**: `https://static.ada.support/embed2.js`
- **Script attributes**:
  - `id="__ada"`
  - `data-handle="<BOT_HANDLE>"`
  - `data-lazy` (optional, delays init)
- **Global objects**:
  - `window.adaSettings` (config: `handle`, `cluster`, `metaFields`, `chatterTokenCallback`, `adaReadyCallback`)
  - `window.adaEmbed` (runtime: `start()`, `toggle()`)
- **Regional domains**:
  - Default: `<bot>.ada.support`
  - US2: `<bot>.us2.ada.support`
  - Canada: `<bot>.maple.ada.support`
  - EU: `<bot>.eu.ada.support`
- **DOM signatures**: Script element with `id="__ada"`, `data-handle` attribute
- **Security**: Bot only launches on authorized domains

### Dialogflow Messenger (Google)

- **Category**: embeddable_sdk
- **Company**: Google Cloud
- **Docs**: `cloud.google.com/dialogflow/cx/docs/concept/integration/dialogflow-messenger`
- **Script URL**: `https://www.gstatic.com/dialogflow-console/fast/df-messenger/prod/v1/df-messenger.js`
- **Custom elements**:
  - `<df-messenger>` — main widget container
  - `<df-messenger-chat>` — chat interface
  - `<df-external-custom-feedback>` — feedback component
- **Key attributes**:
  - `location` — agent region
  - `project-id` — GCP project
  - `agent-id` — Dialogflow agent
  - `language-code` — conversation language
  - `chat-title` — display title
  - `oauth-client-id` — for auth
- **Events**: `df-url-suggested`, `df-custom-submit-feedback-clicked`

### Amazon Lex

- **Category**: embeddable_sdk
- **Company**: AWS
- **GitHub**: `github.com/aws-samples/aws-lex-web-ui`
- **Script patterns**: Self-hosted or via CloudFormation-deployed S3 bucket
- **Key module**: `aws-lex-web-ui` (npm)
- **DOM signatures**: Configurable, typically custom elements
- **Notes**: No fixed CDN URL; deployed per-customer via CloudFormation

### IBM watsonx Assistant (formerly Watson Assistant)

- **Category**: embeddable_sdk
- **Company**: IBM
- **Script URL**: `https://web-chat.global.assistant.watson.appdomain.cloud/versions/{version}/WatsonAssistantChatEntry.js`
- **CDN pattern**: `web-chat.global.assistant.watson.appdomain.cloud`
- **Initialization**:
  ```javascript
  window.watsonAssistantChatOptions = {
    integrationID: "<INTEGRATION_ID>",
    region: "<REGION>",
    serviceInstanceID: "<SERVICE_INSTANCE_ID>",
    onLoad: async (instance) => { await instance.render(); }
  };
  ```
- **DOM signatures**: Watson-branded chat widget container
- **Key parameters**: `integrationID`, `region`, `serviceInstanceID`

### Rasa

- **Category**: embeddable_sdk / chatbot_platform
- **Company URL**: `rasa.com`
- **Widget**: `rasa-webchat` (community widget)
- **Script pattern**: Self-hosted or via npm `rasa-webchat`
- **Custom element**: `<rasa-chat-widget>` (Rasa Chat channel connector)
- **API endpoint**: `/webhooks/rest/webhook` (Rasa server)
- **Notes**: Open-source framework; widget is self-hosted, no fixed CDN

### Tidio

- **Category**: embeddable_sdk
- **Company URL**: `tidio.com`
- **Developer docs**: `developers.tidio.com`
- **Script URL**: `https://code.tidio.co/<PUBLIC_KEY>/external.js`
- **CDN pattern**: `code.tidio.co`
- **DOM signatures**: `#tidio-chat`, `#tidio-chat-iframe`
- **Global object**: `window.tidioChatApi`
- **Methods**: `tidioChatApi.open()`, `tidioChatApi.close()`, etc.
- **API headers**: `X-Tidio-Openapi-Client-Id`, `X-Tidio-Openapi-Client-Secret`
- **Integrations**: WordPress plugin `tidio-live-chat`, Shopify app, Chrome extension

### Intercom (Fin AI)

- **Category**: embeddable_sdk
- **Company URL**: `intercom.com`
- **Script URL**: `https://widget.intercom.io/widget/<APP_ID>`
- **CDN pattern**: `widget.intercom.io`
- **Global object**: `window.Intercom`
- **Initialization**:
  ```javascript
  window.Intercom('boot', {
    app_id: '<APP_ID>',
    user_id: '<USER_ID>',
    email: '<EMAIL>'
  });
  ```
- **Key methods**:
  - `Intercom('boot', {...})` — initialize
  - `Intercom('update', {...})` — update user data
  - `Intercom('shutdown')` — end session
- **DOM signatures**: `#intercom-container`, `#intercom-frame`
- **Rate limits**: 20 update calls per user per page (resets every 30 min)
- **Cookies**: Expire after 1 week

### Drift (now Salesloft)

- **Category**: embeddable_sdk
- **Company URL**: `drift.com` (redirects to `salesloft.com/platform/drift`)
- **Script URL**: `https://js.driftt.com/include/<VERSION>/<ACCOUNT_ID>.js`
- **CDN pattern**: `js.driftt.com`
- **Global object**: `window.drift`
- **API methods**: `drift.api.toggleChat()`, `drift.api.openChat()`, etc.
- **DOM signatures**: `.drift-widget`, `#drift-widget`, `#drift-frame-controller`
- **Ketch integration**: `global.ketchcdn.com/web/v3/config/drift/`

### Zendesk (Answer Bot / Messaging)

- **Category**: embeddable_sdk
- **Company URL**: `zendesk.com`
- **Script URL**: `https://static.zdassets.com/ekr/snippet.js?key=<KEY>`
- **CDN pattern**: `static.zdassets.com`
- **Staging CDN**: `static-staging.zdassets.com`
- **Global function**: `zE()` (Zendesk Embed)
- **Key commands**:
  - `zE('messenger', 'show')` / `zE('messenger', 'hide')`
  - `zE('messenger', 'open')` / `zE('messenger', 'close')`
  - `zE('messenger:set', 'locale', code)`
  - `zE('messenger:on', 'open', callback)`
- **DOM signatures**: `[data-garden-id]` with chat context, Zendesk iframe
- **Features**: Custom launchers, embedded mode, voice call buttons, CTA buttons, metadata

### Freshchat (Freshdesk / Freddy AI)

- **Category**: embeddable_sdk
- **Company URL**: `freshworks.com`
- **Script URL**: `https://wchat.freshchat.com/js/widget.js`
- **CDN patterns**: `wchat.freshchat.com`, `assetscdn-web.freshchat.com`
- **Initialization**:
  ```javascript
  window.fcWidget.init({
    token: "<TOKEN>",
    host: "https://wchat.freshchat.com"
  });
  ```
- **Global object**: `window.fcWidget`
- **DOM signatures**: `#freshdesk-widget`, `#fc_frame`, `#fc_push_frame`
- **Internal module**: `hotline-frontend/app`
- **Loader IDs**: `#app-loader-360`, `#app-loader`

### Crisp

- **Category**: embeddable_sdk
- **Company URL**: `crisp.chat`
- **Docs**: `docs.crisp.chat/guides/chatbox-sdks/web-sdk/`
- **Script URL**: `https://client.crisp.chat/l.js`
- **CDN pattern**: `client.crisp.chat`
- **Initialization**:
  ```javascript
  window.CRISP_WEBSITE_ID = "<WEBSITE_ID>";
  ```
- **Global object**: `$crisp`
- **DOM signatures**: `.crisp-client`, `#crisp-chatbox`, `.crisp-client #crisp-chatbox-button`, `.crisp-client #crisp-chatbox-chat`
- **CSS positioning**: Fixed bottom positioning with responsive media queries at `max-width: 880px`
- **Mobile SDKs**: iOS, Android, React Native

### LivePerson

- **Category**: embeddable_sdk
- **Company URL**: `liveperson.com`
- **Knowledge base**: `community.liveperson.com`
- **Script pattern**: `lpTag` (LivePerson tag)
- **CDN pattern**: `lptag.liveperson.net` or account-specific CDN
- **Global object**: `window.lpTag`
- **Initialization**: Tag-based embed with account ID
- **DOM signatures**: LivePerson-branded widget container
- **Notes**: Enterprise-focused; implementation varies by deployment

### Kommunicate

- **Category**: embeddable_sdk
- **Company URL**: `kommunicate.io`
- **Docs**: `docs.kommunicate.io/docs/web-installation`
- **Script URL**: `https://widget.kommunicate.io/kommunicate-widget-3.0.min.js`
- **CDN pattern**: `widget.kommunicate.io`
- **Initialization**:
  ```javascript
  var kommunicateSettings = {
    "appId": "<APP_ID>",
    "automaticChatOpenOnNavigation": true,
    "popupWidget": true
  };
  window.kommunicate = m;
  m._globals = kommunicateSettings;
  ```
- **Global object**: `window.kommunicate`
- **DOM signatures**: `#kommunicate-widget-iframe`
- **CSS**: `.chat-popup-widget-container` (hidden on mobile <=425px)
- **iFrame embed**: `widget.kommunicate.io/chat?appId=<APP_ID>`
- **NPM**: `@kommunicate/kommunicate-chatbot-plugin`
- **Config options**: `voiceInput`, `voiceOutput`, `attachment`, `emojilibrary`, `quickReplies`
- **Framework support**: React, Angular, Vue, iFrame

### Landbot

- **Category**: embeddable_sdk / chatbot_platform
- **Company URL**: `landbot.io`
- **Script URL**: `https://cdn.landbot.io/landbot-3/landbot-3.0.0.mjs`
- **CDN pattern**: `cdn.landbot.io`
- **Config URL**: `https://storage.googleapis.com/landbot.pro/v3/H-<BOT_ID>/index.json`
- **Module type**: ES Module (`.mjs`)
- **Initialization parameter**: `configUrl` (required)
- **DOM signatures**:
  - `#chatbotPrompt` (input)
  - `#arrowBtn` (submit button)
  - `.embed-prompt`, `.chatbox` (containers)
  - `#charLimitMsg` (character limit)
  - `.input-wrap`
- **CSS classes**: `.shake-once`, `.is-disabled`, `.fade-out` (on submit button)
- **Lazy loading**: Initializes on mouseover/touchstart events
- **Char limit**: 1000 characters

### ManyChat

- **Category**: chatbot_platform
- **Company URL**: `manychat.com`
- **Primary channels**: Facebook Messenger, Instagram, WhatsApp, SMS, Telegram
- **Website widget**: Growth tools with chat widget for website embed
- **Script patterns**: Dashboard-generated embed codes
- **Notes**: Primarily a messaging platform, website widget is secondary feature

### Chatfuel

- **Category**: chatbot_platform
- **Company URL**: `chatfuel.com`
- **Docs**: `docs.chatfuel.com`
- **Primary channels**: WhatsApp, Facebook Messenger, Instagram
- **Website widget**: WhatsApp website button for direct messaging
- **Script patterns**: Dashboard-generated, Next.js-based interface
- **Notes**: Primarily WhatsApp/Messenger automation; website widget is a redirect to WhatsApp

### CustomGPT

- **Category**: embeddable_sdk
- **Company URL**: `customgpt.ai`
- **Docs**: `docs.customgpt.ai`
- **Script pattern**: Likely `cdn.customgpt.ai` or dashboard-generated embed
- **iFrame pattern**: Embeddable chat iframe with project-specific URL
- **API patterns**: REST API for chatbot CRUD and conversation management
- **Notes**: No-code platform; 100+ integrations; embed code generated per-project

### ChatBot.com (by Text/LiveChat)

- **Category**: embeddable_sdk
- **Company URL**: `chatbot.com`
- **Parent company**: Text (also owns LiveChat)
- **Script URL**: Uses LiveChat widget infrastructure: `https://cdn.livechatinc.com/tracking.js`
- **CDN pattern**: `cdn.livechatinc.com`
- **Integration**: `LiveChatWidget` object with session tracking
- **License ID**: Account-specific (e.g., `19196658`)
- **Config**: `manual_channels` integration, `livechat` product name
- **DOM signatures**: LiveChat widget elements

### Dante AI

- **Category**: embeddable_sdk
- **Company URL**: `dante-ai.com`
- **Script URL**: `https://app.dante-ai.com/bubble-embed.js?kb_id=<KB_ID>&token=<TOKEN>&modeltype=<MODEL>&tabs=<true|false>`
- **CDN pattern**: `app.dante-ai.com`
- **Script parameters**:
  - `kb_id` — knowledge base UUID
  - `token` — authentication token UUID
  - `modeltype` — e.g., `gpt-4-omnimodel-mini`
  - `tabs` — boolean for tab display
- **Loading**: Async injection via `document.head.appendChild()`
- **Excluded paths**: `/ai-avatars`, `/guides-iframe`
- **Integrations**: WhatsApp, Slack, Messenger, Teams, Discord, Intercom, Zapier

### Chaindesk

- **Category**: embeddable_sdk
- **Company URL**: `chaindesk.ai`
- **Script URL**: `https://cdn.jsdelivr.net/npm/@chaindesk/embeds@latest/dist/chatbox/index.js`
- **CDN pattern**: `cdn.jsdelivr.net/npm/@chaindesk/embeds`
- **NPM package**: `@chaindesk/embeds`
- **Module type**: ES Module import
- **Initialization**:
  ```javascript
  import Chatbox from 'https://cdn.jsdelivr.net/npm/@chaindesk/embeds@latest/dist/chatbox/index.js';
  Chatbox.initBubble({ agentId: '<AGENT_ID>' });
  ```
- **DOM attributes**: `id="chaindesk-agent"`, `type="module"`
- **Method**: `Chatbox.initBubble()`
- **Integrations**: WhatsApp, Slack, Telegram, Crisp, Zapier, Messenger

### DocsBot

- **Category**: embeddable_sdk
- **Company URL**: `docsbot.ai`
- **Docs**: `docsbot.ai/documentation`
- **API endpoint**: `https://api.docsbot.ai/teams/<TEAM_ID>/bots/<BOT_ID>/chat`
- **CDN pattern**: Dashboard-generated widget code
- **NPM**: `@docsbot/chat-widget`
- **Notes**: Widget embed code generated per-bot; supports WordPress, Shopify, Squarespace, Wix, Docusaurus

### SiteGPT

- **Category**: embeddable_sdk
- **Company URL**: `sitegpt.ai`
- **API base**: `https://sitegpt.ai/api/v0`
- **API auth**: Bearer token via `Authorization` header
- **API endpoints**: Chatbot CRUD, messages, threads, appearance, settings, quick prompts
- **Rate limits**: 100 req/min (Standard), 500 req/min (Business)
- **Embed**: Per-chatbot unique URL with provided embed code
- **Integrations**: Crisp, Intercom, Zendesk

### Chatbase

- **Category**: embeddable_sdk
- **Company URL**: `chatbase.co`
- **Script URL**: `https://www.chatbase.co/embed.min.js`
- **CDN pattern**: `chatbase.co/embed.min.js`
- **Global object**: `window.chatbase`
- **Initialization**: Script dynamically created with:
  - `src="https://www.chatbase.co/embed.min.js"`
  - `id="<CHATBOT_ID>"` (unique per chatbot, e.g., `z2c2HSfKnCTh5J4650V0I`)
  - `domain="https://www.chatbase.co/"`
- **Queue system**: Proxy-based command queue before script loads
- **State check**: `window.chatbase("getState") !== "initialized"`
- **Channels**: Web, Slack, WhatsApp, Messenger

---

## Category 3: Additional Chat/Support Platforms (may include AI features)

These are primarily support/chat platforms that have added AI capabilities. They may or
may not have LLM-powered features active on any given deployment.

### LiveChat (by Text)

- **Category**: chatbot_platform
- **Script URL**: `https://cdn.livechatinc.com/tracking.js`
- **CDN pattern**: `cdn.livechatinc.com`
- **DOM signatures**: `#chat-widget-container`, LiveChatWidget object

### HubSpot Chat

- **Category**: chatbot_platform
- **Script URL**: `https://js.usemessages.com/conversations-embed.js`
- **CDN pattern**: `js.usemessages.com`
- **DOM signatures**: `#hubspot-messages-iframe-container`

---

## Quick Reference: Script URL Detection Patterns

For use in the detection module's `ScriptChecker`:

```python
KNOWN_SDK_PATTERNS = {
    # Vendor: (url_pattern, confidence)
    "botpress": ("cdn.botpress.cloud/webchat", 0.95),
    "ada": ("static.ada.support/embed", 0.95),
    "dialogflow": ("gstatic.com/dialogflow-console/fast/df-messenger", 0.95),
    "tidio": ("code.tidio.co", 0.90),
    "intercom": ("widget.intercom.io/widget", 0.85),
    "drift": ("js.driftt.com", 0.85),
    "zendesk": ("static.zdassets.com/ekr/snippet.js", 0.85),
    "freshchat": ("wchat.freshchat.com", 0.85),
    "crisp": ("client.crisp.chat/l.js", 0.85),
    "liveperson": ("lptag.liveperson.net", 0.80),
    "kommunicate": ("widget.kommunicate.io", 0.90),
    "landbot": ("cdn.landbot.io/landbot", 0.90),
    "chatbase": ("chatbase.co/embed.min.js", 0.90),
    "dante": ("app.dante-ai.com/bubble-embed.js", 0.95),
    "chaindesk": ("@chaindesk/embeds", 0.95),
    "livechat": ("cdn.livechatinc.com/tracking.js", 0.80),
    "hubspot": ("js.usemessages.com", 0.75),
    "chatbot_com": ("cdn.livechatinc.com", 0.80),
    "docsbot": ("api.docsbot.ai", 0.90),
    "whtvr": ("api.whtvr.ai/api/sdk", 0.95),
}
```

## Quick Reference: DOM Signature Detection Patterns

For use in the detection module's `DomChecker`:

```python
KNOWN_DOM_SIGNATURES = {
    # Vendor: (css_selector, confidence)
    "botpress": ("iframe#webchat-root", 0.95),
    "botpress_fab": ("iframe#fab-root", 0.90),
    "ada": ("script#__ada[data-handle]", 0.95),
    "dialogflow": ("df-messenger", 0.95),
    "dialogflow_chat": ("df-messenger-chat", 0.90),
    "tidio": ("#tidio-chat", 0.90),
    "intercom": ("#intercom-container", 0.90),
    "drift": (".drift-widget", 0.85),
    "drift_frame": ("#drift-frame-controller", 0.90),
    "zendesk": ("[data-garden-id]", 0.70),  # Lower confidence, shared selector
    "freshchat": ("#fc_frame", 0.90),
    "crisp": (".crisp-client", 0.90),
    "crisp_chatbox": ("#crisp-chatbox", 0.90),
    "kommunicate": ("#kommunicate-widget-iframe", 0.95),
    "landbot_input": ("#chatbotPrompt", 0.80),
    "chatbase": ("script[src*='chatbase.co/embed.min.js']", 0.95),
    "chaindesk": ("script#chaindesk-agent", 0.95),
    "livechat": ("#chat-widget-container", 0.80),
    "hubspot": ("#hubspot-messages-iframe-container", 0.85),
}
```

## Quick Reference: Global JavaScript Object Detection

For use in runtime detection (checking `window.*` objects):

```python
KNOWN_GLOBAL_OBJECTS = {
    # Vendor: global_object_name
    "botpress": "botpress",
    "ada_settings": "adaSettings",
    "ada_embed": "adaEmbed",
    "intercom": "Intercom",
    "drift": "drift",
    "zendesk": "zE",
    "freshchat": "fcWidget",
    "crisp": "$crisp",
    "crisp_id": "CRISP_WEBSITE_ID",
    "tidio": "tidioChatApi",
    "kommunicate": "kommunicate",
    "chatbase": "chatbase",
    "liveperson": "lpTag",
    "livechat": "LiveChatWidget",
}
```

## Quick Reference: Direct LLM App URL Patterns

For URL-based detection (recognizing the user is on an LLM site):

```python
DIRECT_LLM_URLS = {
    # Vendor: list of hostname patterns
    "chatgpt": ["chatgpt.com", "chat.openai.com"],
    "claude": ["claude.ai"],
    "gemini": ["gemini.google.com"],
    "copilot": ["copilot.microsoft.com"],
    "perplexity": ["perplexity.ai", "www.perplexity.ai"],
    "huggingchat": ["huggingface.co"],  # path must contain /chat
    "poe": ["poe.com"],
    "you": ["you.com"],
    "groq": ["console.groq.com", "groq.com"],
    "mistral": ["chat.mistral.ai"],
    "deepseek": ["chat.deepseek.com"],
    "grok": ["grok.com"],
    "pi": ["pi.ai"],
}
```
