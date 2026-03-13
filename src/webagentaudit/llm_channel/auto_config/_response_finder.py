"""Interactive response element discovery via DOM diffing.

Sends a probe message, waits for DOM changes, and identifies the element
that contains the bot's response.
"""

from __future__ import annotations

import asyncio
import logging

from playwright.async_api import Frame, Page

from . import consts
from ._selector_builder import SelectorBuilder
from .models import ElementCandidate, ScoredElement

logger = logging.getLogger(__name__)

# Keywords in class/id that suggest the element is a response container
_RESPONSE_CONTEXT_KEYWORDS = [
    "response",
    "reply",
    "answer",
    "bot",
    "assistant",
    "message",
    "output",
    "result",
]


class ResponseFinder:
    """Discover the response element by sending a probe and diffing the DOM.

    Algorithm:
    1. Take a text snapshot of the page.
    2. Type the probe message into *input_selector* and submit.
    3. Poll for new text nodes that were not in the snapshot.
    4. Identify the deepest element containing the new text.
    5. Build a generalised ``:last-of-type`` selector for it.
    """

    def __init__(self, selector_builder: SelectorBuilder | None = None) -> None:
        self._selector_builder = selector_builder or SelectorBuilder()

    async def find(
        self,
        page: Page | Frame,
        *,
        input_selector: str,
        submit_selector: str | None,
    ) -> tuple[ScoredElement | None, str | None]:
        """Send a probe message and discover the response element.

        Returns:
            A tuple of (ScoredElement, response_text) or (None, None).
        """
        # 1. Snapshot existing text
        before_texts = await self._snapshot_texts(page)

        # 2. Type probe and submit
        await self._send_probe(page, input_selector, submit_selector)

        # 3. Wait and poll for new text
        new_element_info = await self._poll_for_response(page, before_texts)
        if not new_element_info:
            logger.debug("No new text appeared after probe message")
            return None, None

        response_text = new_element_info["text"]
        element_selector = new_element_info["selector"]

        # 4. Build a ScoredElement
        candidate = ElementCandidate(
            tag_name=new_element_info.get("tag", "div"),
            selector=element_selector,
            classes=new_element_info.get("classes", []),
        )

        # Build a generalised response selector
        response_selector = await self._selector_builder.build_response_selector(
            candidate, page
        )
        candidate.selector = response_selector

        # Score the response candidate
        breakdown = self._score_response(candidate)
        total = sum(breakdown.values())

        scored = ScoredElement(
            candidate=candidate, score=total, score_breakdown=breakdown
        )
        return scored, response_text

    async def _snapshot_texts(self, page: Page | Frame) -> set[str]:
        """Collect all visible text content from the page."""
        texts: list[str] = await page.evaluate(
            """() => {
                const ignore = new Set(%s);
                const texts = [];
                const walker = document.createTreeWalker(
                    document.body,
                    NodeFilter.SHOW_ELEMENT,
                    { acceptNode: (node) =>
                        ignore.has(node.tagName.toLowerCase())
                            ? NodeFilter.FILTER_REJECT
                            : NodeFilter.FILTER_ACCEPT
                    }
                );
                while (walker.nextNode()) {
                    const t = walker.currentNode.textContent.trim();
                    if (t.length >= %d) texts.push(t);
                }
                return texts;
            }"""
            % (
                str(list(consts.RESPONSE_IGNORE_TAGS)),
                consts.RESPONSE_MIN_TEXT_LENGTH,
            )
        )
        return set(texts)

    async def _send_probe(
        self,
        page: Page | Frame,
        input_selector: str,
        submit_selector: str | None,
    ) -> None:
        """Type the probe message and submit."""
        await page.fill(input_selector, consts.RESPONSE_PROBE_MESSAGE)
        if submit_selector:
            await page.click(submit_selector)
        else:
            await page.press(input_selector, "Enter")

    async def _poll_for_response(
        self, page: Page | Frame, before_texts: set[str]
    ) -> dict | None:
        """Poll the DOM for new text that wasn't in *before_texts*."""
        timeout_ms = consts.RESPONSE_PROBE_TIMEOUT_MS
        interval_ms = consts.RESPONSE_POLL_INTERVAL_MS
        settle_ms = consts.RESPONSE_DOM_SETTLE_MS
        elapsed = 0

        # Wait a bit for DOM to settle
        await asyncio.sleep(settle_ms / 1000)
        elapsed += settle_ms

        while elapsed < timeout_ms:
            result = await page.evaluate(
                """(beforeTexts) => {
                    const ignore = new Set(%s);
                    const walker = document.createTreeWalker(
                        document.body,
                        NodeFilter.SHOW_ELEMENT,
                        { acceptNode: (node) =>
                            ignore.has(node.tagName.toLowerCase())
                                ? NodeFilter.FILTER_REJECT
                                : NodeFilter.FILTER_ACCEPT
                        }
                    );
                    const beforeSet = new Set(beforeTexts);
                    while (walker.nextNode()) {
                        const el = walker.currentNode;
                        const t = el.textContent.trim();
                        if (t.length >= %d && !beforeSet.has(t)) {
                            // Find the deepest element whose text is new
                            let deepest = el;
                            function findDeepest(node) {
                                for (const child of node.children) {
                                    const ct = child.textContent.trim();
                                    if (ct.length >= %d && !beforeSet.has(ct)) {
                                        deepest = child;
                                        findDeepest(child);
                                        return;
                                    }
                                }
                            }
                            findDeepest(el);
                            const tag = deepest.tagName.toLowerCase();
                            const classes = deepest.className && typeof deepest.className === 'string'
                                ? deepest.className.split(/\\s+/).filter(Boolean)
                                : [];
                            // Build a basic selector
                            let sel = tag;
                            if (deepest.id) sel = '#' + deepest.id;
                            else if (classes.length > 0) sel = tag + '.' + classes.join('.');
                            return { text: t, selector: sel, tag: tag, classes: classes };
                        }
                    }
                    return null;
                }"""
                % (
                    str(list(consts.RESPONSE_IGNORE_TAGS)),
                    consts.RESPONSE_MIN_TEXT_LENGTH,
                    consts.RESPONSE_MIN_TEXT_LENGTH,
                ),
                list(before_texts),
            )
            if result:
                return result

            await asyncio.sleep(interval_ms / 1000)
            elapsed += interval_ms

        return None

    @staticmethod
    def _score_response(candidate: ElementCandidate) -> dict[str, float]:
        """Score the response candidate based on context keywords."""
        breakdown: dict[str, float] = {}
        class_str = " ".join(candidate.classes).lower()
        context_score = 0.0
        for kw in _RESPONSE_CONTEXT_KEYWORDS:
            if kw in class_str:
                context_score = 1.0
                break
        breakdown["context"] = context_score * 0.5
        breakdown["found"] = 0.5  # baseline score for finding a response
        return breakdown
