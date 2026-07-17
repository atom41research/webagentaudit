"""Partial validation of the good-probe authoring contract.

Regex overlap with a complete sent prompt is mechanically detectable here.
Authors must still ensure the expected output itself is absent, distinctive,
and absent from the target's pre-submit rendered page.
"""

from dataclasses import dataclass

from .detectors.pattern_detector import PatternDetector
from .probes.base import BaseProbe


@dataclass(frozen=True)
class PromptPatternOverlap:
    """Detector patterns already present in a detection-active prompt."""

    conversation_index: int
    turn_index: int
    patterns: tuple[str, ...]


def find_prompt_pattern_overlaps(
    probe: BaseProbe,
    detector: PatternDetector | None = None,
) -> list[PromptPatternOverlap]:
    """Return detection-active turns whose prompt matches probe patterns."""
    pattern_detector = detector or PatternDetector()
    patterns = probe.get_detector_patterns()
    overlaps = []
    for conversation_index, conversation in enumerate(
        probe.get_conversations(), start=1
    ):
        for turn_index, turn in enumerate(conversation.turns, start=1):
            if not turn.detect_after:
                continue
            matched = pattern_detector.detect(turn.prompt, patterns)
            if matched:
                overlaps.append(PromptPatternOverlap(
                    conversation_index=conversation_index,
                    turn_index=turn_index,
                    patterns=tuple(matched),
                ))
    return overlaps
