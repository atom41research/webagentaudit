"""Known provider signature checker."""

from __future__ import annotations

import logging

from ...core.enums import DetectionMethod
from ...core.models import ConfidenceScore
from ..consts import KNOWN_PROVIDER_SCRIPTS, SIGNAL_WEIGHT_KNOWN_PROVIDER
from ..models import DetectionSignal, PageData
from .base import BaseSignalChecker

logger = logging.getLogger(__name__)


class KnownSignatureChecker(BaseSignalChecker):
    """Check scripts and HTML for known LLM provider signatures."""

    @property
    def name(self) -> str:
        return "known_signatures"

    def check(self, page_data: PageData) -> list[DetectionSignal]:
        signals: list[DetectionSignal] = []

        # Collect all script sources to check: external script URLs and inline
        # script contents, plus raw HTML for any src attributes we might have
        # missed.
        sources_to_check: list[str] = [
            *page_data.scripts,
            *page_data.inline_scripts,
        ]
        if page_data.html:
            sources_to_check.append(page_data.html)

        if not sources_to_check:
            return signals

        # Track which (provider, fragment) pairs we've already reported so we
        # don't emit duplicate signals when the same fragment appears in both
        # the scripts list and the raw HTML.
        seen: set[tuple[str, str]] = set()

        for provider, fragments in KNOWN_PROVIDER_SCRIPTS.items():
            for fragment in fragments:
                for source in sources_to_check:
                    if fragment in source:
                        key = (provider, fragment)
                        if key in seen:
                            continue
                        seen.add(key)

                        signals.append(
                            DetectionSignal(
                                checker_name=self.name,
                                signal_type="known_provider",
                                description=(
                                    f"Detected known provider '{provider}' "
                                    f"via script fragment '{fragment}'"
                                ),
                                confidence=ConfidenceScore(
                                    value=SIGNAL_WEIGHT_KNOWN_PROVIDER
                                ),
                                evidence=fragment,
                                method=DetectionMethod.DETERMINISTIC,
                                metadata={"provider": provider},
                            )
                        )
                        # No need to check remaining sources for this fragment
                        break

        return signals
