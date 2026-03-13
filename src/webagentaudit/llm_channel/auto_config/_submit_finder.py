"""Algorithmic submit button discovery and scoring."""

from __future__ import annotations

import logging
import math

from playwright.async_api import ElementHandle, Frame, Page

from . import consts
from ._dom_utils import extract_element_props, is_element_visible
from ._hint_matcher import compute_hint_match
from ._selector_builder import SelectorBuilder
from .models import ElementCandidate, ElementHint, ScoredElement

logger = logging.getLogger(__name__)


class SubmitFinder:
    """Find the best submit/send button relative to a known input element.

    Scoring factors:
    - proximity: Euclidean distance from the input element
    - label: text content or aria-label matching send/submit keywords
    - type: input[type=submit] or button[type=submit]
    - class: class name containing send/submit keywords
    - icon: presence of SVG child (common for icon-only send buttons)
    """

    def __init__(self, selector_builder: SelectorBuilder | None = None) -> None:
        self._selector_builder = selector_builder or SelectorBuilder()

    async def find(
        self,
        page: Page | Frame,
        input_candidate: ElementCandidate,
        *,
        hint: ElementHint | None = None,
    ) -> ScoredElement | None:
        """Find the best submit button near *input_candidate*."""
        buttons = await self._gather_candidates(page, input_candidate)
        if not buttons:
            logger.debug("No submit button candidates found")
            return None

        scored = [self._score(c, input_candidate) for c in buttons]

        if hint:
            for se in scored:
                match = compute_hint_match(se.candidate, hint)
                boost = match * consts.HINT_BOOST_MAX
                se.score += boost
                se.score_breakdown["hint_match"] = boost

        scored.sort(key=lambda s: s.score, reverse=True)

        best = scored[0]
        logger.debug(
            "Best submit candidate: %s (score=%.3f, breakdown=%s)",
            best.candidate.selector,
            best.score,
            best.score_breakdown,
        )
        return best if best.score > consts.SUBMIT_MIN_SCORE else None

    async def _gather_candidates(
        self, page: Page | Frame, input_candidate: ElementCandidate
    ) -> list[ElementCandidate]:
        """Collect all visible button/submit elements on the page."""
        selectors = [
            "button",
            "input[type='submit']",
            "[role='button']",
        ]
        seen: set[str] = set()
        candidates: list[ElementCandidate] = []

        for selector in selectors:
            elements: list[ElementHandle] = await page.locator(selector).element_handles()
            for el in elements:
                if not await is_element_visible(el):
                    continue
                identity = await el.evaluate("el => el.outerHTML.substring(0, 100)")
                if identity in seen:
                    continue
                seen.add(identity)

                candidate = await extract_element_props(el, page)
                candidate.selector = await self._selector_builder.build(el, page)
                candidates.append(candidate)

        return candidates

    def _score(
        self, candidate: ElementCandidate, input_candidate: ElementCandidate
    ) -> ScoredElement:
        """Score a button candidate relative to the input element."""
        breakdown: dict[str, float] = {}

        breakdown["proximity"] = (
            self._score_proximity(candidate, input_candidate) * consts.SUBMIT_WEIGHT_PROXIMITY
        )
        breakdown["label"] = (
            self._score_label(candidate) * consts.SUBMIT_WEIGHT_LABEL
        )
        breakdown["type"] = (
            self._score_type(candidate) * consts.SUBMIT_WEIGHT_TYPE
        )
        breakdown["class"] = (
            self._score_class(candidate) * consts.SUBMIT_WEIGHT_CLASS
        )
        breakdown["icon"] = (
            self._score_icon(candidate) * consts.SUBMIT_WEIGHT_ICON
        )

        total = sum(breakdown.values())
        return ScoredElement(candidate=candidate, score=total, score_breakdown=breakdown)

    # ------------------------------------------------------------------
    # Individual scoring helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _score_proximity(
        candidate: ElementCandidate, input_candidate: ElementCandidate
    ) -> float:
        """Score based on pixel distance from the input element."""
        if not candidate.bounding_box or not input_candidate.bounding_box:
            return 0.0

        cb = candidate.bounding_box
        ib = input_candidate.bounding_box

        # Centre-to-centre Euclidean distance
        cx = cb["x"] + cb["width"] / 2
        cy = cb["y"] + cb["height"] / 2
        ix = ib["x"] + ib["width"] / 2
        iy = ib["y"] + ib["height"] / 2

        distance = math.sqrt((cx - ix) ** 2 + (cy - iy) ** 2)

        if distance > consts.SUBMIT_MAX_DISTANCE_PX:
            return 0.0

        return max(0.0, 1.0 - distance / consts.SUBMIT_MAX_DISTANCE_PX)

    @staticmethod
    def _score_label(candidate: ElementCandidate) -> float:
        """Score based on text content or aria-label matching keywords."""
        text = (candidate.text_content + " " + candidate.aria_label).lower()
        for kw in consts.SUBMIT_POSITIVE_KEYWORDS:
            if kw in text:
                return 1.0
        return 0.0

    @staticmethod
    def _score_type(candidate: ElementCandidate) -> float:
        """Score based on element type (submit button)."""
        if candidate.element_type == "submit":
            return 1.0
        if candidate.tag_name == "button":
            return 0.3
        return 0.0

    @staticmethod
    def _score_class(candidate: ElementCandidate) -> float:
        """Score based on class names containing send/submit keywords."""
        class_str = " ".join(candidate.classes).lower()
        for kw in consts.SUBMIT_POSITIVE_KEYWORDS:
            if kw in class_str:
                return 1.0
        return 0.0

    @staticmethod
    def _score_icon(candidate: ElementCandidate) -> float:
        """Score based on SVG child (icon-only send button)."""
        return 1.0 if candidate.has_svg_child else 0.0
