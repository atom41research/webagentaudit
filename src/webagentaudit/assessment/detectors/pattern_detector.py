"""Regex-based pattern detector."""

import logging
import re

from .base import BaseDetector

logger = logging.getLogger(__name__)


class PatternDetector(BaseDetector):
    """Detects vulnerability patterns in LLM responses.

    Pure pattern matching — each probe defines its own patterns that
    unambiguously indicate a successful attack (unique markers, leaked
    content, canary strings).  No generic refusal filtering; probes are
    designed so that only real vulnerabilities trigger their patterns.
    """

    def detect(
        self,
        response_text: str,
        patterns: list[str],
        refusal_patterns: list[str] | None = None,
    ) -> list[str]:
        # If probe provides explicit refusal patterns, filter those out
        if refusal_patterns:
            is_refusal = any(
                re.search(rp, response_text, re.IGNORECASE)
                for rp in refusal_patterns
            )
            if is_refusal:
                return []

        matched = []
        for pattern in patterns:
            try:
                if re.search(pattern, response_text, re.IGNORECASE):
                    matched.append(pattern)
            except re.error as exc:
                logger.warning("Invalid regex pattern %r: %s", pattern, exc)
                continue
        return matched
