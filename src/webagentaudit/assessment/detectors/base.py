"""Abstract base for response detectors."""

from abc import ABC, abstractmethod


class BaseDetector(ABC):
    @abstractmethod
    def detect(self, response_text: str, patterns: list[str]) -> list[str]:
        """Check response text against patterns. Return matched patterns."""
