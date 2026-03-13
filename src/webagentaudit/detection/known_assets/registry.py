"""Registry for known LLM assets. Provides lookup and matching."""

from typing import Optional

from .models import AssetCategory, KnownAsset


class KnownAssetsRegistry:
    """Registry of known LLM/chatbot assets.

    Provides methods to look up assets by URL, script signature,
    or API pattern. The registry is populated from curated data
    modules.
    """

    def __init__(self) -> None:
        self._assets: list[KnownAsset] = []
        self._by_name: dict[str, KnownAsset] = {}

    def register(self, asset: KnownAsset) -> None:
        """Register a known asset."""
        self._assets.append(asset)
        self._by_name[asset.name.lower()] = asset

    def register_many(self, assets: list[KnownAsset]) -> None:
        """Register multiple assets."""
        for asset in assets:
            self.register(asset)

    def get_all(self) -> list[KnownAsset]:
        return list(self._assets)

    def get_by_name(self, name: str) -> Optional[KnownAsset]:
        return self._by_name.get(name.lower())

    def get_by_category(self, category: AssetCategory) -> list[KnownAsset]:
        return [a for a in self._assets if a.category == category]

    def match_url(self, url: str) -> list[KnownAsset]:
        """Find assets whose known URLs match the given URL."""
        import re

        url_lower = url.lower()
        matches = []
        for asset in self._assets:
            # Exact URL prefix match
            for known_url in asset.urls:
                if url_lower.startswith(known_url.lower()):
                    matches.append(asset)
                    break
            else:
                # Regex pattern match
                for pattern in asset.url_patterns:
                    if re.search(pattern, url_lower):
                        matches.append(asset)
                        break
        return matches

    def match_script_url(self, script_url: str) -> list[KnownAsset]:
        """Find assets whose script signatures match a script URL."""
        script_lower = script_url.lower()
        matches = []
        for asset in self._assets:
            for sig in asset.script_signatures:
                if sig.url_fragment.lower() in script_lower:
                    matches.append(asset)
                    break
        return matches

    def match_inline_script(self, script_content: str) -> list[KnownAsset]:
        """Find assets whose inline script patterns match script content."""
        import re

        matches = []
        for asset in self._assets:
            for pattern in asset.inline_script_patterns:
                if re.search(pattern, script_content, re.IGNORECASE):
                    matches.append(asset)
                    break
        return matches

    def match_api_endpoint(self, url: str) -> list[KnownAsset]:
        """Find assets whose API signatures match an endpoint URL."""
        import re

        matches = []
        for asset in self._assets:
            for sig in asset.api_signatures:
                if re.search(sig.pattern, url, re.IGNORECASE):
                    matches.append(asset)
                    break
        return matches

    @classmethod
    def default(cls) -> "KnownAssetsRegistry":
        """Create a registry populated with all built-in known assets."""
        from .data import direct_llm_apps, embeddable_sdks, chatbot_platforms

        registry = cls()
        registry.register_many(direct_llm_apps.ASSETS)
        registry.register_many(embeddable_sdks.ASSETS)
        registry.register_many(chatbot_platforms.ASSETS)
        return registry
