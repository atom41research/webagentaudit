"""Abstract base for response detectors."""

from abc import ABC, abstractmethod


class BaseDetector(ABC):
    @abstractmethod
    def detect(
        self,
        response_text: str,
        patterns: list[str],
        refusal_patterns: list[str] | None = None,
    ) -> list[str]:
        """Check response text against patterns. Return matched patterns.

        If *refusal_patterns* is provided by the probe, responses matching
        any refusal pattern are filtered out.  By default no refusal
        filtering is applied — probes should use unambiguous success
        patterns instead.
        """
