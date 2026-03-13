"""Data models for known LLM assets."""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class AssetCategory(str, Enum):
    """Category of a known LLM asset."""

    DIRECT_LLM_APP = "direct_llm_app"  # ChatGPT, Claude, Gemini — the URL IS the LLM
    EMBEDDABLE_SDK = "embeddable_sdk"  # Vendor SDK embedded on third-party pages
    CHATBOT_PLATFORM = "chatbot_platform"  # Chat widget platforms (may or may not be LLM-powered)
    API_PROVIDER = "api_provider"  # API-only services (no UI, but endpoints appear in code)


class ScriptSignature(BaseModel):
    """A script URL pattern that identifies a vendor's SDK on a page."""

    url_fragment: str  # Substring to match in script src URLs
    description: str = ""


class ApiSignature(BaseModel):
    """An API endpoint pattern that identifies a vendor's backend."""

    pattern: str  # Regex pattern to match against URLs in page code
    description: str = ""


class DomSignature(BaseModel):
    """A DOM element pattern that identifies a vendor's widget."""

    selector: str  # CSS selector
    description: str = ""


class KnownAsset(BaseModel):
    """A known LLM/chatbot asset with all its identifying signatures."""

    name: str
    category: AssetCategory
    description: str = ""

    # URLs where this LLM lives (for direct apps)
    urls: list[str] = Field(default_factory=list)
    # URL patterns (regex) for matching
    url_patterns: list[str] = Field(default_factory=list)

    # Script signatures for embedded detection
    script_signatures: list[ScriptSignature] = Field(default_factory=list)

    # API endpoint patterns
    api_signatures: list[ApiSignature] = Field(default_factory=list)

    # DOM element signatures
    dom_signatures: list[DomSignature] = Field(default_factory=list)

    # Inline script content patterns (regex)
    inline_script_patterns: list[str] = Field(default_factory=list)

    # Additional metadata
    vendor_url: Optional[str] = None  # Vendor's main website
    is_llm_powered: bool = True  # False for traditional chatbots
