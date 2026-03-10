"""Known embeddable LLM/AI SDK vendors — their scripts get embedded on third-party pages."""

from ..models import ApiSignature, AssetCategory, DomSignature, KnownAsset, ScriptSignature

ASSETS: list[KnownAsset] = [
    KnownAsset(
        name="whtvr.ai",
        category=AssetCategory.EMBEDDABLE_SDK,
        description="whtvr.ai embeddable AI chat SDK",
        script_signatures=[
            ScriptSignature(url_fragment="whtvr.ai", description="whtvr.ai SDK script"),
        ],
        api_signatures=[
            ApiSignature(pattern=r"api\.whtvr\.ai/api/sdk/chat", description="whtvr.ai chat API"),
            ApiSignature(pattern=r"whtvr\.ai/api/", description="whtvr.ai API endpoints"),
        ],
        inline_script_patterns=[r"whtvr\.ai", r"whtvr"],
        vendor_url="https://whtvr.ai",
    ),
    KnownAsset(
        name="Voiceflow Widget",
        category=AssetCategory.EMBEDDABLE_SDK,
        description="Voiceflow embeddable chat widget",
        script_signatures=[
            ScriptSignature(url_fragment="cdn.voiceflow.com", description="Voiceflow CDN"),
        ],
        inline_script_patterns=[r"voiceflow", r"vf_project"],
        vendor_url="https://voiceflow.com",
    ),
    KnownAsset(
        name="Botpress Webchat",
        category=AssetCategory.EMBEDDABLE_SDK,
        description="Botpress embeddable webchat widget",
        script_signatures=[
            ScriptSignature(url_fragment="cdn.botpress.cloud", description="Botpress CDN"),
            ScriptSignature(url_fragment="webchat.botpress.cloud", description="Botpress webchat"),
        ],
        api_signatures=[
            ApiSignature(pattern=r"api\.botpress\.cloud", description="Botpress API"),
        ],
        inline_script_patterns=[r"botpress", r"window\.botpressWebChat"],
        vendor_url="https://botpress.com",
    ),
    KnownAsset(
        name="Ada",
        category=AssetCategory.EMBEDDABLE_SDK,
        description="Ada AI-powered customer service chatbot",
        script_signatures=[
            ScriptSignature(url_fragment="static.ada.support", description="Ada SDK"),
        ],
        inline_script_patterns=[r"adaEmbed", r"ada\.support"],
        vendor_url="https://ada.cx",
    ),
    KnownAsset(
        name="Chatbase",
        category=AssetCategory.EMBEDDABLE_SDK,
        description="Chatbase custom GPT chatbot for websites",
        script_signatures=[
            ScriptSignature(url_fragment="chatbase.co", description="Chatbase embed"),
            ScriptSignature(url_fragment="www.chatbase.co/embed", description="Chatbase embed widget"),
        ],
        api_signatures=[
            ApiSignature(pattern=r"chatbase\.co/api", description="Chatbase API"),
        ],
        inline_script_patterns=[r"chatbase", r"chatbotId"],
        vendor_url="https://www.chatbase.co",
    ),
    KnownAsset(
        name="CustomGPT",
        category=AssetCategory.EMBEDDABLE_SDK,
        description="CustomGPT embeddable AI agent",
        script_signatures=[
            ScriptSignature(url_fragment="customgpt.ai", description="CustomGPT SDK"),
        ],
        inline_script_patterns=[r"customgpt", r"CustomGPT"],
        vendor_url="https://customgpt.ai",
    ),
    KnownAsset(
        name="Dante AI",
        category=AssetCategory.EMBEDDABLE_SDK,
        description="Dante AI embeddable chatbot",
        script_signatures=[
            ScriptSignature(url_fragment="dante-ai", description="Dante AI script"),
            ScriptSignature(url_fragment="danteai", description="Dante AI CDN"),
        ],
        inline_script_patterns=[r"dante-ai", r"danteai"],
        vendor_url="https://dante-ai.com",
    ),
    KnownAsset(
        name="Chaindesk",
        category=AssetCategory.EMBEDDABLE_SDK,
        description="Chaindesk AI chatbot platform",
        script_signatures=[
            ScriptSignature(url_fragment="chaindesk.ai", description="Chaindesk script"),
        ],
        api_signatures=[
            ApiSignature(pattern=r"api\.chaindesk\.ai", description="Chaindesk API"),
        ],
        inline_script_patterns=[r"chaindesk"],
        vendor_url="https://chaindesk.ai",
    ),
    KnownAsset(
        name="DocsBot",
        category=AssetCategory.EMBEDDABLE_SDK,
        description="DocsBot AI documentation chatbot",
        script_signatures=[
            ScriptSignature(url_fragment="docsbot.ai", description="DocsBot script"),
        ],
        inline_script_patterns=[r"docsbot", r"DocsBotAI"],
        vendor_url="https://docsbot.ai",
    ),
    KnownAsset(
        name="SiteGPT",
        category=AssetCategory.EMBEDDABLE_SDK,
        description="SiteGPT AI chatbot trained on website content",
        script_signatures=[
            ScriptSignature(url_fragment="sitegpt.ai", description="SiteGPT script"),
        ],
        inline_script_patterns=[r"sitegpt", r"SiteGPT"],
        vendor_url="https://sitegpt.ai",
    ),
    KnownAsset(
        name="Kommunicate",
        category=AssetCategory.EMBEDDABLE_SDK,
        description="Kommunicate AI chatbot and live chat",
        script_signatures=[
            ScriptSignature(url_fragment="widget.kommunicate.io", description="Kommunicate widget"),
        ],
        inline_script_patterns=[r"kommunicate", r"Kommunicate"],
        vendor_url="https://kommunicate.io",
    ),
    KnownAsset(
        name="Dialogflow CX Messenger",
        category=AssetCategory.EMBEDDABLE_SDK,
        description="Google Dialogflow CX embedded messenger",
        script_signatures=[
            ScriptSignature(url_fragment="dialogflow.cloud.google.com", description="Dialogflow messenger"),
        ],
        dom_signatures=[
            DomSignature(selector="df-messenger", description="Dialogflow messenger custom element"),
        ],
        inline_script_patterns=[r"dialogflow", r"df-messenger"],
        vendor_url="https://cloud.google.com/dialogflow",
    ),
    KnownAsset(
        name="Amazon Lex Web UI",
        category=AssetCategory.EMBEDDABLE_SDK,
        description="Amazon Lex embedded chatbot",
        script_signatures=[
            ScriptSignature(url_fragment="lex-web-ui", description="Amazon Lex Web UI"),
        ],
        inline_script_patterns=[r"aws-lex", r"lex-web-ui", r"LexWebUi"],
        vendor_url="https://aws.amazon.com/lex/",
    ),
    KnownAsset(
        name="IBM watsonx Assistant",
        category=AssetCategory.EMBEDDABLE_SDK,
        description="IBM watsonx (formerly Watson) Assistant web chat",
        script_signatures=[
            ScriptSignature(url_fragment="watson-virtual-agent", description="Watson VA"),
            ScriptSignature(url_fragment="web-chat.global.assistant.watson", description="Watson web chat"),
            ScriptSignature(url_fragment="webchat.assistant.watson.cloud.ibm.com", description="Watson webchat CDN"),
        ],
        inline_script_patterns=[
            r"watsonAssistant",
            r"WatsonAssistantChat",
            r"watson-virtual-agent",
            r"integrationID",
        ],
        vendor_url="https://www.ibm.com/products/watsonx-assistant",
    ),
    KnownAsset(
        name="LivePerson",
        category=AssetCategory.EMBEDDABLE_SDK,
        description="LivePerson conversational AI platform",
        script_signatures=[
            ScriptSignature(url_fragment="liveperson.net", description="LivePerson script"),
            ScriptSignature(url_fragment="lptag.liveperson.net", description="LivePerson tag"),
        ],
        inline_script_patterns=[r"lpTag", r"liveperson"],
        vendor_url="https://liveperson.com",
    ),
    KnownAsset(
        name="Landbot",
        category=AssetCategory.EMBEDDABLE_SDK,
        description="Landbot no-code chatbot builder",
        script_signatures=[
            ScriptSignature(url_fragment="landbot.io", description="Landbot script"),
            ScriptSignature(url_fragment="cdn.landbot.io", description="Landbot CDN"),
        ],
        inline_script_patterns=[r"landbot", r"Landbot"],
        vendor_url="https://landbot.io",
        is_llm_powered=False,
    ),
    KnownAsset(
        name="ManyChat",
        category=AssetCategory.EMBEDDABLE_SDK,
        description="ManyChat chat marketing platform",
        script_signatures=[
            ScriptSignature(url_fragment="manychat.com", description="ManyChat script"),
        ],
        inline_script_patterns=[r"ManyChat", r"mcWidgetJsonUrl"],
        vendor_url="https://manychat.com",
        is_llm_powered=False,
    ),
    KnownAsset(
        name="Chatfuel",
        category=AssetCategory.EMBEDDABLE_SDK,
        description="Chatfuel chatbot platform",
        script_signatures=[
            ScriptSignature(url_fragment="chatfuel.com", description="Chatfuel script"),
        ],
        inline_script_patterns=[r"chatfuel"],
        vendor_url="https://chatfuel.com",
        is_llm_powered=False,
    ),
    KnownAsset(
        name="ChatBot.com",
        category=AssetCategory.EMBEDDABLE_SDK,
        description="ChatBot.com AI chatbot builder",
        script_signatures=[
            ScriptSignature(url_fragment="widget.chatbot.com", description="ChatBot.com widget"),
            ScriptSignature(url_fragment="cdn.chatbot.com", description="ChatBot.com CDN"),
        ],
        inline_script_patterns=[r"ChatBotKit", r"chatbot\.com"],
        vendor_url="https://chatbot.com",
    ),
]
