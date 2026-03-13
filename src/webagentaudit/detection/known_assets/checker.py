"""Detection checker that uses the known assets registry."""

from ...core.enums import DetectionMethod
from ...core.models import ConfidenceScore
from ..deterministic.base import BaseSignalChecker
from ..models import DetectionSignal, PageData
from .models import AssetCategory, KnownAsset
from .registry import KnownAssetsRegistry

# Confidence weights by asset category
CONFIDENCE_WEIGHT_DIRECT_APP = 0.95
CONFIDENCE_WEIGHT_EMBEDDABLE_SDK = 0.80
CONFIDENCE_WEIGHT_CHATBOT_PLATFORM = 0.75
CONFIDENCE_WEIGHT_API_PROVIDER = 0.70


def _weight_for_category(category: AssetCategory) -> float:
    return {
        AssetCategory.DIRECT_LLM_APP: CONFIDENCE_WEIGHT_DIRECT_APP,
        AssetCategory.EMBEDDABLE_SDK: CONFIDENCE_WEIGHT_EMBEDDABLE_SDK,
        AssetCategory.CHATBOT_PLATFORM: CONFIDENCE_WEIGHT_CHATBOT_PLATFORM,
        AssetCategory.API_PROVIDER: CONFIDENCE_WEIGHT_API_PROVIDER,
    }.get(category, 0.5)


class KnownAssetsChecker(BaseSignalChecker):
    """Checks a page against the known assets registry.

    Detects known LLM apps (by URL), embedded SDKs (by script signatures),
    chatbot platforms (by script/DOM signatures), and API patterns.
    """

    def __init__(self, registry: KnownAssetsRegistry | None = None) -> None:
        self._registry = registry or KnownAssetsRegistry.default()

    @property
    def name(self) -> str:
        return "known_assets"

    def check(self, page_data: PageData) -> list[DetectionSignal]:
        signals: list[DetectionSignal] = []
        seen_assets: set[str] = set()

        # 1. Check if the page URL itself is a known LLM app
        url_matches = self._registry.match_url(page_data.url)
        for asset in url_matches:
            if asset.name not in seen_assets:
                seen_assets.add(asset.name)
                signals.append(self._make_signal(
                    asset, "known_url", f"Page URL matches known LLM: {asset.name}",
                    evidence=page_data.url,
                ))

        # 2. Check script src URLs against registry
        all_script_urls = list(page_data.scripts)
        soup = page_data.get_soup()
        for tag in soup.find_all("script", src=True):
            src = tag.get("src", "")
            if src and src not in all_script_urls:
                all_script_urls.append(src)

        for script_url in all_script_urls:
            for asset in self._registry.match_script_url(script_url):
                if asset.name not in seen_assets:
                    seen_assets.add(asset.name)
                    signals.append(self._make_signal(
                        asset, "known_script", f"Script matches {asset.name} SDK",
                        evidence=script_url,
                    ))

        # 3. Check inline scripts against registry
        all_inline = list(page_data.inline_scripts)
        for tag in soup.find_all("script"):
            if not tag.get("src") and tag.string:
                content = tag.string.strip()
                if content and content not in all_inline:
                    all_inline.append(content)

        for content in all_inline:
            for asset in self._registry.match_inline_script(content):
                if asset.name not in seen_assets:
                    seen_assets.add(asset.name)
                    signals.append(self._make_signal(
                        asset, "known_inline_script",
                        f"Inline script matches {asset.name}",
                        evidence=content[:200],
                    ))

        # 4. Check DOM signatures
        for asset in self._registry.get_all():
            if asset.name in seen_assets:
                continue
            for dom_sig in asset.dom_signatures:
                try:
                    if soup.select_one(dom_sig.selector):
                        seen_assets.add(asset.name)
                        signals.append(self._make_signal(
                            asset, "known_dom",
                            f"DOM element matches {asset.name}: {dom_sig.description}",
                            evidence=dom_sig.selector,
                        ))
                        break
                except Exception:
                    continue

        return signals

    def _make_signal(
        self,
        asset: KnownAsset,
        signal_type: str,
        description: str,
        evidence: str,
    ) -> DetectionSignal:
        return DetectionSignal(
            checker_name=self.name,
            signal_type=signal_type,
            description=description,
            confidence=ConfidenceScore(value=_weight_for_category(asset.category)),
            evidence=evidence,
            method=DetectionMethod.DETERMINISTIC,
            metadata={
                "asset_name": asset.name,
                "asset_category": asset.category.value,
                "is_llm_powered": asset.is_llm_powered,
                "vendor_url": asset.vendor_url or "",
            },
        )
