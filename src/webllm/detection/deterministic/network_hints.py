"""Network hints checker for LLM API endpoint patterns."""

from __future__ import annotations

import logging
import re

from ...core.enums import DetectionMethod
from ...core.models import ConfidenceScore
from ..consts import LLM_API_PATTERNS, SIGNAL_WEIGHT_NETWORK_HINT
from ..models import DetectionSignal, PageData
from .base import BaseSignalChecker

logger = logging.getLogger(__name__)


class NetworkHintsChecker(BaseSignalChecker):
    """Check for API endpoint patterns suggesting LLM backends."""

    @property
    def name(self) -> str:
        return "network_hints"

    def check(self, page_data: PageData) -> list[DetectionSignal]:
        signals: list[DetectionSignal] = []

        # Pre-compile the API patterns once per check call
        compiled: list[tuple[str, re.Pattern[str]]] = []
        for raw in LLM_API_PATTERNS:
            try:
                compiled.append((raw, re.compile(raw, re.IGNORECASE)))
            except re.error:
                logger.debug("Invalid API regex pattern skipped: %s", raw)

        if not compiled:
            return signals

        # Track (pattern, matched_text) to avoid duplicates
        seen: set[tuple[str, str]] = set()

        def _scan(text: str, source: str) -> None:
            """Scan *text* against all API patterns and append signals."""
            if not text:
                return
            for raw_pattern, regex in compiled:
                try:
                    match = regex.search(text)
                except Exception:
                    continue
                if not match:
                    continue
                matched_text = match.group()
                key = (raw_pattern, matched_text)
                if key in seen:
                    continue
                seen.add(key)

                signals.append(
                    DetectionSignal(
                        checker_name=self.name,
                        signal_type="llm_api_endpoint",
                        description=f"Found LLM API endpoint pattern: {raw_pattern}",
                        confidence=ConfidenceScore(value=SIGNAL_WEIGHT_NETWORK_HINT),
                        evidence=matched_text,
                        method=DetectionMethod.DETERMINISTIC,
                        metadata={
                            "matched_pattern": raw_pattern,
                            "source": source,
                        },
                    )
                )

        # 1. Script src URLs
        for src in page_data.scripts:
            _scan(src, "script_url")

        # 2. Inline script code
        for code in page_data.inline_scripts:
            _scan(code, "inline_script")

        # 3. Raw HTML (catches hardcoded URLs outside <script> tags)
        if page_data.html:
            _scan(page_data.html, "raw_html")

        # 4. <form> actions and <a> hrefs from the DOM
        if page_data.html:
            try:
                soup = page_data.get_soup()
            except Exception:
                logger.debug("Failed to parse HTML for network hints")
                return signals

            for form in soup.find_all("form"):
                action = form.get("action")
                if action:
                    _scan(str(action), "form_action")

            for anchor in soup.find_all("a"):
                href = anchor.get("href")
                if href:
                    _scan(str(href), "anchor_href")

        return signals
