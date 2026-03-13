"""Regex-based pattern detector."""

import re

from .base import BaseDetector


class PatternDetector(BaseDetector):
    def detect(self, response_text: str, patterns: list[str]) -> list[str]:
        matched = []
        for pattern in patterns:
            try:
                if re.search(pattern, response_text, re.IGNORECASE):
                    matched.append(pattern)
            except re.error:
                continue
        return matched
