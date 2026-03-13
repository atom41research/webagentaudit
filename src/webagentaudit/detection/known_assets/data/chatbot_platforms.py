"""Known chatbot/live-chat platforms — may or may not be LLM-powered.

These are the traditional chat widget providers. Many have added AI/LLM features
(e.g., Intercom Fin, Zendesk Answer Bot, Freshdesk Freddy AI), so they're tracked
here with is_llm_powered indicating known AI capability.
"""

from ..models import ApiSignature, AssetCategory, DomSignature, KnownAsset, ScriptSignature

ASSETS: list[KnownAsset] = [
    KnownAsset(
        name="Intercom",
        category=AssetCategory.CHATBOT_PLATFORM,
        description="Intercom customer messaging with Fin AI agent",
        script_signatures=[
            ScriptSignature(url_fragment="widget.intercom.io", description="Intercom widget"),
            ScriptSignature(url_fragment="js.intercomcdn.com", description="Intercom CDN"),
        ],
        dom_signatures=[
            DomSignature(selector="#intercom-container", description="Intercom container"),
            DomSignature(selector=".intercom-lightweight-app", description="Intercom lightweight"),
        ],
        inline_script_patterns=[r"Intercom\(", r"intercomSettings", r"window\.intercomSettings"],
        vendor_url="https://intercom.com",
        is_llm_powered=True,
    ),
    KnownAsset(
        name="Drift",
        category=AssetCategory.CHATBOT_PLATFORM,
        description="Drift (now Salesloft) conversational marketing with AI",
        script_signatures=[
            ScriptSignature(url_fragment="js.driftt.com", description="Drift script"),
            ScriptSignature(url_fragment="js.drift.com", description="Drift CDN"),
        ],
        dom_signatures=[
            DomSignature(selector=".drift-widget", description="Drift widget"),
            DomSignature(selector="#drift-widget", description="Drift widget ID"),
        ],
        inline_script_patterns=[r"drift\.load\(", r"driftt\.com"],
        vendor_url="https://drift.com",
        is_llm_powered=True,
    ),
    KnownAsset(
        name="Tidio",
        category=AssetCategory.CHATBOT_PLATFORM,
        description="Tidio live chat with Lyro AI chatbot",
        script_signatures=[
            ScriptSignature(url_fragment="code.tidio.co", description="Tidio script"),
        ],
        dom_signatures=[
            DomSignature(selector="#tidio-chat", description="Tidio chat container"),
        ],
        inline_script_patterns=[r"tidio", r"tidioChatCode"],
        vendor_url="https://tidio.com",
        is_llm_powered=True,
    ),
    KnownAsset(
        name="Zendesk",
        category=AssetCategory.CHATBOT_PLATFORM,
        description="Zendesk customer support with Answer Bot AI",
        script_signatures=[
            ScriptSignature(url_fragment="static.zdassets.com", description="Zendesk assets"),
            ScriptSignature(url_fragment="ekr.zdassets.com", description="Zendesk EKR"),
        ],
        dom_signatures=[
            DomSignature(selector='[data-garden-id="containers.chrome"]', description="Zendesk Garden"),
        ],
        inline_script_patterns=[r"zdassets", r"zE\(", r"zESettings"],
        vendor_url="https://zendesk.com",
        is_llm_powered=True,
    ),
    KnownAsset(
        name="Freshdesk",
        category=AssetCategory.CHATBOT_PLATFORM,
        description="Freshdesk/Freshchat with Freddy AI",
        script_signatures=[
            ScriptSignature(url_fragment="wchat.freshchat.com", description="Freshchat widget"),
            ScriptSignature(url_fragment="assetscdn-wchat.freshchat.com", description="Freshchat CDN"),
        ],
        dom_signatures=[
            DomSignature(selector="#freshdesk-widget", description="Freshdesk widget"),
        ],
        inline_script_patterns=[r"freshchat", r"Freshchat", r"fcWidget"],
        vendor_url="https://freshworks.com",
        is_llm_powered=True,
    ),
    KnownAsset(
        name="Crisp",
        category=AssetCategory.CHATBOT_PLATFORM,
        description="Crisp business messaging with AI chatbot",
        script_signatures=[
            ScriptSignature(url_fragment="client.crisp.chat", description="Crisp chat script"),
        ],
        dom_signatures=[
            DomSignature(selector=".crisp-client", description="Crisp client container"),
        ],
        inline_script_patterns=[r"\$crisp", r"CRISP_WEBSITE_ID", r"crisp\.chat"],
        vendor_url="https://crisp.chat",
        is_llm_powered=True,
    ),
    KnownAsset(
        name="LiveChat",
        category=AssetCategory.CHATBOT_PLATFORM,
        description="LiveChat with AI assist features",
        script_signatures=[
            ScriptSignature(url_fragment="cdn.livechatinc.com", description="LiveChat CDN"),
        ],
        dom_signatures=[
            DomSignature(selector="#chat-widget-container", description="LiveChat container"),
        ],
        inline_script_patterns=[r"LiveChatWidget", r"__lc\.", r"livechatinc"],
        vendor_url="https://livechat.com",
        is_llm_powered=True,
    ),
    KnownAsset(
        name="HubSpot Chat",
        category=AssetCategory.CHATBOT_PLATFORM,
        description="HubSpot conversations with AI chatbot",
        script_signatures=[
            ScriptSignature(url_fragment="js.usemessages.com", description="HubSpot messages"),
            ScriptSignature(url_fragment="js.hubspot.com", description="HubSpot JS"),
        ],
        dom_signatures=[
            DomSignature(selector="#hubspot-messages-iframe-container", description="HubSpot messages"),
        ],
        inline_script_patterns=[r"hubspot", r"HubSpot", r"hs-script-loader"],
        vendor_url="https://hubspot.com",
        is_llm_powered=True,
    ),
    KnownAsset(
        name="tawk.to",
        category=AssetCategory.CHATBOT_PLATFORM,
        description="tawk.to free live chat with AI Assist",
        script_signatures=[
            ScriptSignature(url_fragment="embed.tawk.to", description="tawk.to embed"),
        ],
        inline_script_patterns=[r"Tawk_API", r"tawk\.to", r"embed\.tawk\.to"],
        vendor_url="https://tawk.to",
        is_llm_powered=True,
    ),
    KnownAsset(
        name="Olark",
        category=AssetCategory.CHATBOT_PLATFORM,
        description="Olark live chat",
        script_signatures=[
            ScriptSignature(url_fragment="static.olark.com", description="Olark script"),
        ],
        inline_script_patterns=[r"olark", r"olark\.identify"],
        vendor_url="https://olark.com",
        is_llm_powered=False,
    ),
    KnownAsset(
        name="Chatwoot",
        category=AssetCategory.CHATBOT_PLATFORM,
        description="Chatwoot open-source customer engagement platform",
        script_signatures=[
            ScriptSignature(url_fragment="app.chatwoot.com", description="Chatwoot script"),
        ],
        inline_script_patterns=[r"chatwootSDK", r"chatwootSettings", r"chatwoot"],
        vendor_url="https://chatwoot.com",
        is_llm_powered=True,
    ),
    KnownAsset(
        name="Help Scout Beacon",
        category=AssetCategory.CHATBOT_PLATFORM,
        description="Help Scout Beacon chat widget with AI Answers",
        script_signatures=[
            ScriptSignature(url_fragment="beacon-2.helpscout.net", description="Help Scout Beacon"),
        ],
        inline_script_patterns=[r"Beacon\(", r"helpscout"],
        vendor_url="https://helpscout.com",
        is_llm_powered=True,
    ),
]
