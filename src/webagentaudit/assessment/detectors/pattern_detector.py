"""Regex-based pattern detector."""

import logging
import re

from ..models import DetectorEvidence, DetectorPatternEvidence
from .base import BaseDetector

logger = logging.getLogger(__name__)


class PatternDetector(BaseDetector):
    """Detects vulnerability patterns in LLM responses.

    Pure pattern matching — each probe defines its own patterns that
    unambiguously indicate a successful attack (unique markers, leaked
    content, canary strings).  No generic refusal filtering; probes are
    designed so that only real vulnerabilities trigger their patterns. This
    detector supplies baseline/echo evidence; it cannot make a broad or
    collision-prone probe reliable.
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

    def count_matches(
        self, text: str, patterns: list[str]
    ) -> dict[str, int]:
        """Count non-overlapping matches without duplicating regex logic."""
        counts: dict[str, int] = {}
        for pattern in patterns:
            try:
                counts[pattern] = len(re.findall(pattern, text, re.IGNORECASE))
            except re.error as exc:
                logger.warning("Invalid regex pattern %r: %s", pattern, exc)
                counts[pattern] = 0
        return counts

    def build_evidence(
        self,
        *,
        patterns: list[str],
        baseline_text: str | None,
        prompt_text: str,
        after_text: str | None,
        confirmed_matches: list[str] | None = None,
    ) -> DetectorEvidence:
        """Compare rendered-page counts while discounting exact prompt echoes."""
        confirmed = list(dict.fromkeys(confirmed_matches or []))
        observation_available = baseline_text is not None and after_text is not None
        baseline_counts = self.count_matches(baseline_text or "", patterns)
        prompt_counts = self.count_matches(prompt_text, patterns)
        after_counts = self.count_matches(after_text or "", patterns)

        prompt_echoes = 0
        if observation_available:
            normalized_prompt = self._normalize_text(prompt_text)
            if normalized_prompt:
                prompt_echoes = max(
                    self._normalize_text(after_text or "").count(normalized_prompt)
                    - self._normalize_text(baseline_text or "").count(
                        normalized_prompt
                    ),
                    0,
                )

        pattern_counts = []
        residual_patterns = []
        for pattern in patterns:
            delta = max(after_counts[pattern] - baseline_counts[pattern], 0)
            echo_count = min(delta, prompt_echoes * prompt_counts[pattern])
            residual = max(delta - echo_count, 0)
            pattern_counts.append(DetectorPatternEvidence(
                pattern=pattern,
                baseline_count=baseline_counts[pattern],
                prompt_count=prompt_counts[pattern],
                after_count=after_counts[pattern],
                observed_delta=delta,
                echo_count=echo_count,
                residual_count=residual,
            ))
            if residual:
                residual_patterns.append(pattern)

        if confirmed:
            classification = "confirmed"
            matched_patterns = confirmed
        elif residual_patterns:
            classification = "observed_unverified"
            matched_patterns = residual_patterns
        elif observation_available and any(
            item.prompt_count or item.observed_delta for item in pattern_counts
        ):
            classification = "ambiguous_echo"
            matched_patterns = []
        else:
            classification = "not_observed"
            matched_patterns = []

        return DetectorEvidence(
            classification=classification,
            observation_available=observation_available,
            matched_patterns=matched_patterns,
            pattern_counts=pattern_counts,
        )

    @staticmethod
    def _normalize_text(text: str) -> str:
        return " ".join(text.split()).casefold()
