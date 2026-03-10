# LLM Detection Techniques

## Overview

Techniques for detecting interactive LLM interfaces on webpages, used by the `detection` module.

## 1. DOM Pattern Matching

Look for HTML elements characteristic of chat/LLM interfaces:

### Input Elements
- `textarea[placeholder*="ask"]`, `textarea[placeholder*="message"]`
- `input[placeholder*="chat"]`, `input[placeholder*="question"]`
- `[data-testid*="prompt"]`, `[contenteditable="true"]` in chat contexts
- `[role="textbox"]` with chat-related parent containers

### Container Elements
- `[class*="chatbot"]`, `[id*="chatbot"]`
- `[class*="ai-chat"]`, `[class*="llm"]`
- `[aria-label*="chat"]`, `[aria-label*="assistant"]`
- `[data-testid="chat-widget"]`
- `.chat-bot-container`, `.ai-assistant`

### Response Elements
- `[class*="message"]` with streaming/typing indicators
- `[class*="response"]`, `[class*="answer"]`
- Markdown-rendered content blocks within chat containers

## 2. Known Provider Signatures

Script URLs and DOM markers for known chat/LLM providers:

| Provider | Script Signatures | DOM Markers |
|----------|------------------|-------------|
| Intercom | `widget.intercom.io`, `js.intercomcdn.com` | `#intercom-container` |
| Drift | `js.driftt.com` | `.drift-widget` |
| Tidio | `code.tidio.co` | `#tidio-chat` |
| Zendesk | `static.zdassets.com` | `[data-garden-id]` with chat |
| Freshdesk | `wchat.freshchat.com` | `#freshdesk-widget` |
| Crisp | `client.crisp.chat` | `.crisp-client` |
| LiveChat | `cdn.livechatinc.com` | `#chat-widget-container` |
| HubSpot | `js.usemessages.com` | `#hubspot-messages-iframe-container` |

Note: Not all chat widgets are LLM-powered. Provider detection is a signal, not proof.

## 3. Script Analysis

Analyze JavaScript for LLM-related code:
- Imports of LLM SDKs (OpenAI, Anthropic, etc.)
- WebSocket connections to known LLM API endpoints
- Streaming response handling patterns (SSE, ReadableStream)
- Chat/completion API calls in bundled code

## 4. Network/API Endpoint Patterns

URL patterns suggesting LLM backend:
- `/api/v*/chat`, `/api/chat/completions`
- `/v*/messages` (Anthropic-style)
- `/api/assistant`, `/api/ai/`
- `/completion`, `/generate`
- WebSocket URLs with chat/llm keywords

## 5. AI-Assisted Detection

When deterministic methods are inconclusive:
1. Take page screenshot
2. Extract DOM summary (structure, visible text, interactive elements)
3. Send to AI model with prompt: "Does this page contain an interactive LLM/chatbot interface? Identify the input area and response area."
4. Parse AI response for confirmation and selector suggestions
