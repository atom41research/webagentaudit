"""Interactive response element discovery via DOM diffing.

Sends a probe message, waits for DOM changes, and identifies the element
that contains the bot's response.
"""

from __future__ import annotations

import asyncio
import logging

from playwright.async_api import Frame, Page

from webagentaudit.core.exceptions import (
    ChannelResponseError,
    ChannelSubmissionError,
)

from . import consts
from ._dom_utils import click_enabled_submit_after_fill
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

_RESPONSE_ELEMENT_KEYWORDS = [
    "response",
    "reply",
    "answer",
    "bot",
    "assistant",
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
        before_texts = await self.snapshot(page)

        # 2. Type probe and submit
        try:
            await self._send_probe(page, input_selector, submit_selector)
        except Exception as exc:
            raise ChannelSubmissionError(
                f"Could not type or submit discovery prompt: {exc}"
            ) from exc

        # 3. Wait and poll for new text
        try:
            return await self.wait(
                page,
                before_texts,
                submitted_text=consts.RESPONSE_PROBE_MESSAGE,
            )
        except ChannelResponseError:
            input_text = await page.locator(input_selector).first.evaluate(
                "el => 'value' in el ? el.value : "
                "(el.innerText || el.textContent || '')"
            )
            if input_text.strip() == consts.RESPONSE_PROBE_MESSAGE.strip():
                raise ChannelSubmissionError(
                    "Discovery prompt remained in the input after submission"
                )
            raise

    async def snapshot(self, page: Page | Frame) -> set[str]:
        """Capture response-relevant text before the real prompt is sent."""
        return await self._snapshot_texts(page)

    async def wait(
        self,
        page: Page | Frame,
        before_texts: set[str],
        timeout_ms: int | None = None,
        submitted_text: str | None = None,
    ) -> tuple[ScoredElement | None, str | None]:
        """Discover the assistant response without sending another prompt."""
        new_element_info = await self._poll_for_response(
            page,
            before_texts,
            timeout_ms=timeout_ms,
            submitted_text=submitted_text,
        )
        if not new_element_info:
            raise ChannelResponseError(
                "Prompt was submitted, but no response could be read"
            )

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
        elif not await click_enabled_submit_after_fill(page, input_selector):
            await page.press(input_selector, "Enter")

    async def _poll_for_response(
        self,
        page: Page | Frame,
        before_texts: set[str],
        *,
        timeout_ms: int | None = None,
        submitted_text: str | None = None,
    ) -> dict | None:
        """Poll the DOM for new text that wasn't in *before_texts*."""
        timeout_ms = timeout_ms or consts.RESPONSE_PROBE_TIMEOUT_MS
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
                    const matches = [];
                    while (walker.nextNode()) {
                        const el = walker.currentNode;
                        if (["button", "a", "input", "textarea", "select", "option", "svg", "path"].includes(
                            el.tagName.toLowerCase()
                        ) || el.closest("button, a, [role='button']")) continue;
                        const t = el.textContent.trim();
                        if (t.length < %d || beforeSet.has(t)) continue;

                        const classes = el.className && typeof el.className === 'string'
                            ? el.className.split(/\\s+/).filter(Boolean)
                            : [];
                        const context = `${el.id} ${classes.join(' ')}`.toLowerCase();
                        if (/\\b(thinking|loading|generating)\\b/.test(t.toLowerCase())) continue;
                        if (/^\\d{1,2}:\\d{2}(?:\\s?[AP]M)?$/i.test(t)) continue;

                        let depth = 0;
                        for (let parent = el.parentElement; parent; parent = parent.parentElement) depth++;
                        const semantic = %s.some(keyword => context.includes(keyword));
                        // The submitted probe is often rendered as a customer echo.
                        // Preserve it only when it is explicitly marked as a reply
                        // (some test/chat backends intentionally echo as the bot).
                        if (t.includes(%s) && !semantic) continue;
                        matches.push({ el, text: t, classes, depth, semantic });
                    }
                    // A page shell can also contain the new response text.  Keep the
                    // deepest semantic element rather than the last ancestor visited.
                    const leaves = matches.filter(match => !matches.some(other =>
                        other.el !== match.el && match.el.contains(other.el)
                    ));
                    leaves.sort((a, b) => Number(b.semantic) - Number(a.semantic)
                        || b.depth - a.depth || a.text.length - b.text.length);
                    const response = leaves[0];
                    if (!response) return null;

                    const el = response.el;
                    const tag = el.tagName.toLowerCase();
                    const path = (node) => {
                        const parts = [];
                        for (let current = node; current && current.nodeType === Node.ELEMENT_NODE; current = current.parentElement) {
                            if (current.id) { parts.unshift('#' + CSS.escape(current.id)); break; }
                            const tagName = current.tagName.toLowerCase();
                            const children = current.parentElement
                                ? [...current.parentElement.children] : [];
                            const siblings = children
                                .filter(sibling => sibling.tagName === current.tagName);
                            const position = siblings.indexOf(current) + 1;
                            parts.unshift(siblings.length > 1 ? `${tagName}:nth-of-type(${position})` : tagName);
                            if (current.tagName === 'BODY') break;
                        }
                        return parts.join(' > ');
                    };
                    let sel = path(el);
                    if (el.id) sel = '#' + CSS.escape(el.id);
                    else if (response.semantic && response.classes.length > 0) {
                        sel = tag + '.' + response.classes.join('.');
                    }
                    return { text: response.text, selector: sel, tag, classes: response.classes };
                }"""
                % (
                    str(list(consts.RESPONSE_IGNORE_TAGS)),
                    consts.RESPONSE_MIN_TEXT_LENGTH,
                    str(_RESPONSE_ELEMENT_KEYWORDS),
                    repr(submitted_text or consts.RESPONSE_PROBE_MESSAGE),
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
