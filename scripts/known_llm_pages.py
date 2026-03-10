"""Curated list of URLs where LLM/chatbot boxes are known to exist.

Used by the collector scripts to build a corpus of rendered pages
for data-driven detection rule development.
"""

from typing import Any

PAGES: dict[str, list[dict[str, Any]]] = {
    # Direct LLM apps — the whole page IS the LLM interface
    "direct_apps": [
        {"name": "chatgpt", "url": "https://chatgpt.com"},
        {"name": "claude", "url": "https://claude.ai"},
        {"name": "gemini", "url": "https://gemini.google.com/app"},
        {"name": "copilot", "url": "https://copilot.microsoft.com"},
        {"name": "poe", "url": "https://poe.com"},
        {"name": "huggingchat", "url": "https://huggingface.co/chat"},
        {"name": "mistral_chat", "url": "https://chat.mistral.ai"},
        {"name": "deepseek", "url": "https://chat.deepseek.com"},
        {"name": "grok", "url": "https://grok.com"},
        {"name": "pi", "url": "https://pi.ai"},
        {"name": "cohere_coral", "url": "https://coral.cohere.com"},
        {"name": "you_com", "url": "https://you.com"},
        {"name": "meta_ai", "url": "https://www.meta.ai"},
    ],
    # Embedded LLM/chatbot widgets on third-party sites
    "embedded_widgets": [
        {"name": "calcalist_whtvr", "url": "https://www.calcalist.co.il/world_news/article/bk4nt66twl"},
        {"name": "intercom_fin_example", "url": "https://www.intercom.com"},
        {"name": "drift_example", "url": "https://www.drift.com"},
        {"name": "tidio_example", "url": "https://www.tidio.com"},
        {"name": "ada_example", "url": "https://www.ada.cx"},
        {"name": "botpress_example", "url": "https://botpress.com"},
        {"name": "crisp_example", "url": "https://crisp.chat/en/"},
        {"name": "zendesk_example", "url": "https://www.zendesk.com"},
        {"name": "hubspot_example", "url": "https://www.hubspot.com"},
        {"name": "freshdesk_example", "url": "https://www.freshworks.com/freshdesk/"},
        {"name": "stripe_docs", "url": "https://docs.stripe.com"},
        # User-provided pages with known LLM boxes (some require interaction to reveal)
        {"name": "vercel_docs", "url": "https://vercel.com/docs", "notes": "Hidden AI box, visible on 'Ask AI' click"},
        {"name": "supabase_docs", "url": "https://supabase.com/docs", "notes": "Requires interaction to reach 'Ask Supabase AI'"},
        {"name": "mintlify_docs", "url": "https://www.mintlify.com/docs", "notes": "AI via search or sparkle icon button"},
    ],
    # Direct LLM/AI chat apps — standalone AI interfaces (not embedded)
    "direct_ai_chat": [
        {"name": "quillbot_ai_chat", "url": "https://quillbot.com/ai-chat"},
        {"name": "perplexity", "url": "https://www.perplexity.ai/"},
        {"name": "andi_search", "url": "https://andisearch.com/"},
        {"name": "phind_chat", "url": "https://phindai.org/phind-chat/"},
    ],
    # Negative examples — pages with NO LLM/chatbot box
    "negative_examples": [
        {"name": "wikipedia_llm", "url": "https://en.wikipedia.org/wiki/Large_language_model"},
        {"name": "github_home", "url": "https://github.com"},
        {"name": "bbc_news", "url": "https://www.bbc.com/news"},
        {"name": "amazon_product", "url": "https://www.amazon.com"},
        {"name": "stackoverflow", "url": "https://stackoverflow.com"},
        {"name": "python_docs", "url": "https://docs.python.org/3/"},
        {"name": "nytimes", "url": "https://www.nytimes.com"},
    ],
}


def get_all_pages() -> list[dict[str, Any]]:
    """Return a flat list of all pages across all categories."""
    all_pages = []
    for pages in PAGES.values():
        all_pages.extend(pages)
    return all_pages


def get_pages_by_category(category: str) -> list[dict[str, Any]]:
    """Return pages for a specific category."""
    return PAGES.get(category, [])
