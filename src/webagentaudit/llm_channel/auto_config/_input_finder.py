"""Algorithmic input element discovery and scoring."""

from __future__ import annotations

import logging

from playwright.async_api import ElementHandle, Frame, Page

from . import consts
from ._dom_utils import extract_element_props, is_element_visible
from ._hint_matcher import compute_hint_match
from ._selector_builder import SelectorBuilder
from .models import ElementCandidate, ElementHint, ScoredElement

logger = logging.getLogger(__name__)


class InputFinder:
    """Find the best chat input element on a page.

    Algorithm:
    1. Query all textarea, input[type=text], input:not([type]),
       [contenteditable=true], [role=textbox] elements.
    2. Filter to visible elements only.
    3. Score each by multiple heuristics.
    4. Return the highest-scoring candidate above threshold.
    """

    def __init__(self, selector_builder: SelectorBuilder | None = None) -> None:
        self._selector_builder = selector_builder or SelectorBuilder()

    async def find(
        self, page: Page | Frame, *, hint: ElementHint | None = None
    ) -> ScoredElement | None:
        """Find the best input element candidate on the page."""
        candidates = await self._gather_candidates(page)
        if not candidates:
            logger.debug("No input element candidates found on page")
            return None

        scored = [self._score(c) for c in candidates]

        # Apply hint boost
        if hint:
            for se in scored:
                match = compute_hint_match(se.candidate, hint)
                boost = match * consts.HINT_BOOST_MAX
                se.score += boost
                se.score_breakdown["hint_match"] = boost

        scored.sort(key=lambda s: s.score, reverse=True)

        best = scored[0]
        logger.debug(
            "Best input candidate: %s (score=%.3f, breakdown=%s)",
            best.candidate.selector,
            best.score,
            best.score_breakdown,
        )
        return best if best.score > consts.INPUT_MIN_SCORE else None

    async def _gather_candidates(self, page: Page | Frame) -> list[ElementCandidate]:
        """Query the DOM for all potential input elements."""
        selectors = [
            "textarea",
            "input[type='text']",
            "input:not([type])",
            "[contenteditable='true']",
            "[role='textbox']",
        ]
        seen: set[str] = set()
        candidates: list[ElementCandidate] = []

        for selector in selectors:
            elements: list[ElementHandle] = await page.locator(selector).element_handles()
            for el in elements:
                if not await is_element_visible(el):
                    continue

                identity = await el.evaluate(
                    "el => el.outerHTML.substring(0, 100)"
                )
                if identity in seen:
                    continue
                seen.add(identity)

                candidate = await extract_element_props(el, page)
                candidate.selector = await self._selector_builder.build(el, page)
                candidates.append(candidate)

        return candidates

    def _score(self, candidate: ElementCandidate) -> ScoredElement:
        """Score a candidate input element."""
        breakdown: dict[str, float] = {}

        type_score = self._score_element_type(candidate)
        breakdown["element_type"] = type_score * consts.INPUT_WEIGHT_ELEMENT_TYPE

        placeholder_score = _score_keywords(
            candidate.placeholder,
            consts.INPUT_POSITIVE_KEYWORDS,
            consts.INPUT_NEGATIVE_KEYWORDS,
        )
        breakdown["placeholder"] = placeholder_score * consts.INPUT_WEIGHT_PLACEHOLDER

        aria_score = _score_keywords(
            candidate.aria_label,
            consts.INPUT_POSITIVE_KEYWORDS,
            [],
        )
        breakdown["aria_label"] = aria_score * consts.INPUT_WEIGHT_ARIA_LABEL

        breakdown["position"] = (
            self._score_position(candidate) * consts.INPUT_WEIGHT_POSITION
        )
        breakdown["size"] = (
            self._score_size(candidate) * consts.INPUT_WEIGHT_SIZE
        )
        breakdown["parent_context"] = (
            self._score_parent_context(candidate) * consts.INPUT_WEIGHT_PARENT_CONTEXT
        )
        breakdown["data_testid"] = (
            self._score_data_testid(candidate) * consts.INPUT_WEIGHT_DATA_TESTID
        )
        breakdown["no_negative"] = (
            self._score_no_negative(candidate) * consts.INPUT_WEIGHT_NO_NEGATIVE
        )

        total = sum(breakdown.values())
        return ScoredElement(candidate=candidate, score=total, score_breakdown=breakdown)

    # ------------------------------------------------------------------
    # Individual scoring helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _score_element_type(c: ElementCandidate) -> float:
        if c.tag_name == "textarea":
            return 1.0
        if c.is_contenteditable or c.role == "textbox":
            return 0.8
        if c.tag_name == "input" and c.element_type in ("text", ""):
            return 0.6
        return 0.3

    @staticmethod
    def _score_position(c: ElementCandidate) -> float:
        if not c.bounding_box:
            return 0.5
        y = c.bounding_box["y"]
        if y > 500:
            return 1.0
        if y > 300:
            return 0.7
        return 0.3

    @staticmethod
    def _score_size(c: ElementCandidate) -> float:
        if not c.bounding_box:
            return 0.5
        w, h = c.bounding_box["width"], c.bounding_box["height"]
        if w < 100:
            return 0.1
        if h > 200:
            return 0.3
        if 200 < w < 800 and 20 < h < 100:
            return 1.0
        return 0.5

    @staticmethod
    def _score_parent_context(c: ElementCandidate) -> float:
        combined = " ".join(c.parent_classes + c.classes).lower()
        for kw in consts.INPUT_PARENT_KEYWORDS:
            if kw in combined:
                return 1.0
        return 0.0

    @staticmethod
    def _score_data_testid(c: ElementCandidate) -> float:
        if not c.data_testid:
            return 0.0
        testid_lower = c.data_testid.lower()
        for kw in ("chat", "ai", "prompt", "input", "message"):
            if kw in testid_lower:
                return 1.0
        return 0.2

    @staticmethod
    def _score_no_negative(c: ElementCandidate) -> float:
        if c.element_type in ("search", "password", "email", "tel", "url", "number"):
            return 0.0
        placeholder_lower = c.placeholder.lower()
        for neg in consts.INPUT_NEGATIVE_KEYWORDS:
            if neg in placeholder_lower:
                return 0.0
        return 1.0


def _score_keywords(
    text: str, positive: list[str], negative: list[str]
) -> float:
    """Score text based on keyword presence. Returns 0.0-1.0."""
    if not text:
        return 0.0
    text_lower = text.lower()
    for neg in negative:
        if neg in text_lower:
            return 0.0
    for pos in positive:
        if pos in text_lower:
            return 1.0
    return 0.2
