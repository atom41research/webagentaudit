"""Chat widget iframe discovery.

Scans a page for iframes that contain chat widget interfaces, scoring
them by vendor-specific selectors, URL patterns, title matching, and
the presence of input elements inside the frame.
"""

from __future__ import annotations

import logging

from playwright.async_api import Frame, Page

from . import consts
from .models import FrameCandidate

logger = logging.getLogger(__name__)


class FrameFinder:
    """Find chat widget iframes on a page.

    Scoring:
    - Vendor selector match: 0.5
    - URL pattern match: 0.3
    - Title keyword match: 0.2
    - Has input element inside frame: +0.3
    """

    async def find_chat_frames(self, page: Page) -> list[FrameCandidate]:
        """Discover and rank iframes likely to contain chat widgets.

        Returns:
            A list of ``FrameCandidate`` sorted by score (highest first).
            Empty list if no chat frames are found.
        """
        iframes = await page.query_selector_all("iframe")
        if not iframes:
            return []

        candidates: list[FrameCandidate] = []

        for iframe in iframes:
            score = 0.0
            matched_selector = ""

            # 1. Check vendor-specific selectors
            for selector in consts.FRAME_CHAT_SELECTORS:
                try:
                    match = await page.query_selector(selector)
                    if match:
                        is_same = await page.evaluate(
                            "(args) => args[0] === args[1]",
                            [iframe, match],
                        )
                        if is_same:
                            score += 0.5
                            matched_selector = selector
                            break
                except Exception:
                    continue

            # 2. Check URL patterns in src attribute
            src = await iframe.get_attribute("src") or ""
            for pattern in consts.FRAME_URL_PATTERNS:
                if pattern in src.lower():
                    score += 0.3
                    if not matched_selector:
                        matched_selector = f'iframe[src*="{pattern}"]'
                    break

            # 3. Check title attribute
            title = await iframe.get_attribute("title") or ""
            title_lower = title.lower()
            if any(kw in title_lower for kw in ("chat", "widget", "messenger")):
                score += 0.2
                if not matched_selector:
                    matched_selector = f'iframe[title="{title}"]'

            if score < consts.FRAME_MIN_SCORE:
                continue

            # Build a selector for this iframe
            if not matched_selector:
                iframe_id = await iframe.get_attribute("id")
                if iframe_id:
                    matched_selector = f"iframe#{iframe_id}"
                else:
                    iframe_name = await iframe.get_attribute("name")
                    if iframe_name:
                        matched_selector = f'iframe[name="{iframe_name}"]'
                    else:
                        matched_selector = "iframe"

            # 4. Get the content frame and check for input elements
            content_frame = await iframe.content_frame()
            has_input = await self._frame_has_input(iframe, page)
            if has_input:
                score += 0.3

            candidates.append(
                FrameCandidate(
                    frame=content_frame,
                    iframe_selector=matched_selector,
                    score=score,
                    src=src,
                    title=title,
                    has_input=has_input,
                )
            )

        candidates.sort(key=lambda c: c.score, reverse=True)
        return candidates

    @staticmethod
    async def _frame_has_input(iframe_handle, page: Page) -> bool:
        """Check if the iframe contains any input elements."""
        try:
            # Get the frame object from the iframe element
            frame = await iframe_handle.content_frame()
            if not frame:
                return False

            for selector in consts.FRAME_INPUT_CHECK_SELECTORS:
                try:
                    el = await frame.query_selector(selector)
                    if el:
                        return True
                except Exception:
                    continue
        except Exception:
            pass
        return False
