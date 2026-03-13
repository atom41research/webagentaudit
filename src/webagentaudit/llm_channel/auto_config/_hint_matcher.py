"""Hint parsing and fuzzy matching for element identification.

Converts raw HTML snippets into ``ElementHint`` objects and computes
similarity scores between hints and discovered ``ElementCandidate`` objects.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser

from . import consts
from .models import ElementCandidate, ElementHint


# ---------------------------------------------------------------------------
# HTML snippet → ElementHint
# ---------------------------------------------------------------------------


class _HintParser(HTMLParser):
    """Minimal HTML parser that extracts the first element's attributes."""

    def __init__(self) -> None:
        super().__init__()
        self.tag_name: str = ""
        self.attrs: dict[str, str] = {}
        self.has_svg: bool = False
        self._done_root = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if not self._done_root:
            self.tag_name = tag
            self.attrs = {k: (v or "") for k, v in attrs}
            self._done_root = True
        elif tag == "svg":
            self.has_svg = True


def parse_hint(html: str) -> ElementHint:
    """Parse an HTML snippet into an ``ElementHint``.

    Only the root element's tag, classes, and selected attributes are
    extracted.  An ``<svg>`` descendant sets ``has_svg_child``.
    """
    if not html or not html.strip():
        return ElementHint(raw_html=html)

    parser = _HintParser()
    try:
        parser.feed(html)
    except Exception:
        return ElementHint(raw_html=html)

    classes_str = parser.attrs.pop("class", "")
    classes = classes_str.split() if classes_str else []

    return ElementHint(
        tag_name=parser.tag_name,
        classes=classes,
        attributes=parser.attrs,
        has_svg_child=parser.has_svg,
        raw_html=html,
    )


# ---------------------------------------------------------------------------
# Fuzzy matching
# ---------------------------------------------------------------------------


def compute_hint_match(candidate: ElementCandidate, hint: ElementHint) -> float:
    """Compute a 0.0–1.0 similarity score between *candidate* and *hint*.

    Scoring buckets (weights from ``consts``):
    - tag name match
    - CSS class overlap (Jaccard)
    - label / title match (from hint attributes)
    - matchable attribute equality
    - SVG child presence
    """
    # Empty hint → no signal
    if not hint.tag_name and not hint.classes and not hint.attributes:
        return 0.0

    scores: dict[str, float] = {}

    # --- tag ---
    if hint.tag_name:
        scores["tag"] = 1.0 if candidate.tag_name == hint.tag_name else 0.0
    else:
        scores["tag"] = 0.0

    # --- classes (Jaccard similarity) ---
    if hint.classes:
        hint_set = set(hint.classes)
        cand_set = set(candidate.classes)
        intersection = hint_set & cand_set
        union = hint_set | cand_set
        scores["classes"] = len(intersection) / len(union) if union else 0.0
    else:
        scores["classes"] = 0.0

    # --- label / title ---
    label_score = 0.0
    for attr in ("title", "aria-label", "placeholder"):
        hint_val = hint.attributes.get(attr, "")
        if not hint_val:
            continue
        cand_val = ""
        if attr == "title":
            cand_val = candidate.title
        elif attr == "aria-label":
            cand_val = candidate.aria_label
        elif attr == "placeholder":
            cand_val = candidate.placeholder

        if cand_val and cand_val == hint_val:
            label_score = 1.0
            break
        elif cand_val and hint_val.lower() in cand_val.lower():
            label_score = 0.7
    scores["label"] = label_score

    # --- matchable attributes ---
    attr_matches = 0
    attr_total = 0
    for attr_name in consts.HINT_MATCHABLE_ATTRIBUTES:
        hint_val = hint.attributes.get(attr_name, "")
        if not hint_val:
            continue
        attr_total += 1
        cand_val = ""
        if attr_name == "dir":
            # dir is not stored on ElementCandidate directly; skip
            continue
        elif attr_name == "type":
            cand_val = candidate.element_type
        elif attr_name == "role":
            cand_val = candidate.role
        elif attr_name == "placeholder":
            cand_val = candidate.placeholder
        if cand_val == hint_val:
            attr_matches += 1
    scores["attributes"] = (attr_matches / attr_total) if attr_total else 0.0

    # --- SVG ---
    if hint.has_svg_child:
        scores["svg"] = 1.0 if candidate.has_svg_child else 0.0
    else:
        # No SVG expected — not penalised
        scores["svg"] = 0.0

    # Weighted sum — normalise by active dimensions only so that
    # a hint with just tag+classes can still reach 1.0.
    weights = {
        "tag": consts.HINT_WEIGHT_TAG if hint.tag_name else 0.0,
        "classes": consts.HINT_WEIGHT_CLASSES if hint.classes else 0.0,
        "label": consts.HINT_WEIGHT_LABEL if label_score > 0 or any(
            hint.attributes.get(a) for a in ("title", "aria-label", "placeholder")
        ) else 0.0,
        "attributes": consts.HINT_WEIGHT_ATTRIBUTES if attr_total > 0 else 0.0,
        "svg": consts.HINT_WEIGHT_SVG if hint.has_svg_child else 0.0,
    }
    total_weight = sum(weights.values())
    if total_weight == 0:
        return 0.0

    raw = sum(scores[k] * weights[k] for k in scores)
    return raw / total_weight
