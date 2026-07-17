"""Interactive response element discovery via DOM diffing.

Sends a probe message, waits for DOM changes, and identifies the element
that contains the bot's response.
"""

from __future__ import annotations

import asyncio
import json
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
from ..consts import TYPING_INDICATOR_SELECTORS

logger = logging.getLogger(__name__)

_BASELINE_STATE_KEY = "__webagentaudit_response_baseline__"

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
        self.last_html = ""
        self.last_images: list[str] = []
        self.last_part_count = 0
        self.last_rejections: dict[str, int] = {}
        self.last_selector = ""
        self._scope_selector: str | None = None

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
        await self.snapshot(page)

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

    async def snapshot(
        self, page: Page | Frame, *, scope_selector: str | None = None
    ) -> None:
        """Capture response-relevant DOM nodes before the prompt is sent."""
        self.last_html = ""
        self.last_images = []
        self.last_part_count = 0
        self.last_rejections = {}
        self.last_selector = scope_selector or ""
        self._scope_selector = scope_selector
        await self._snapshot_candidates(page, scope_selector=scope_selector)

    async def wait(
        self,
        page: Page | Frame,
        timeout_ms: int | None = None,
        submitted_text: str | None = None,
        *,
        scope_selector: str | None = None,
        stable_interval_ms: int | None = None,
        poll_interval_ms: int | None = None,
    ) -> tuple[ScoredElement | None, str | None]:
        """Discover the assistant response without sending another prompt."""
        has_snapshot = await page.evaluate(
            "key => Boolean(globalThis[key])", _BASELINE_STATE_KEY
        )
        if not has_snapshot:
            self._scope_selector = scope_selector
            await self._snapshot_candidates(
                page,
                scope_selector=scope_selector,
                baseline_existing=False,
            )
        new_element_info = await self._poll_for_response(
            page,
            timeout_ms=timeout_ms,
            submitted_text=submitted_text,
            stable_interval_ms=stable_interval_ms,
            poll_interval_ms=poll_interval_ms,
        )
        if not new_element_info:
            classification = (
                "system"
                if self.last_rejections.get("system")
                or self.last_rejections.get("greeting")
                else "unverified"
            )
            raise ChannelResponseError(
                "Prompt was submitted, but no response with trustworthy "
                "assistant provenance could be identified",
                metadata={
                    "response_classification": classification,
                    "response_rejected": json.dumps(
                        self.last_rejections, sort_keys=True
                    ),
                },
            )

        response_text = new_element_info["text"]
        primary = new_element_info["primary"]
        element_selector = primary["selector"]

        # 4. Build a ScoredElement
        candidate = ElementCandidate(
            tag_name=primary.get("tag", "div"),
            selector=element_selector,
            classes=primary.get("classes", []),
        )

        response_selector = scope_selector or (
            await self._selector_builder.build_response_selector(candidate, page)
        )
        candidate.selector = response_selector
        self.last_html = new_element_info["html"]
        self.last_images = new_element_info["images"]
        self.last_part_count = new_element_info["part_count"]
        self.last_selector = response_selector

        # Score the response candidate
        breakdown = self._score_response(candidate)
        total = sum(breakdown.values())

        scored = ScoredElement(
            candidate=candidate, score=total, score_breakdown=breakdown
        )
        return scored, response_text

    async def has_activity(
        self, page: Page | Frame, *, submitted_text: str | None = None
    ) -> bool:
        """Whether submission changed any response-scoped DOM node."""
        state = await self._response_state(page, submitted_text=submitted_text)
        return bool(state and state["changed"])

    async def _snapshot_candidates(
        self,
        page: Page | Frame,
        *,
        scope_selector: str | None,
        baseline_existing: bool = True,
    ) -> None:
        """Install the single candidate extractor and snapshot node identities."""
        await page.evaluate(
            """config => {
                const ignore = new Set(config.ignoreTags);
                const controls = [
                    "button", "a", "input", "textarea", "select", "option",
                    "form", "label", "svg", "path", "[role='button']"
                ].join(",");
                const contextKeywords = config.contextKeywords;
                const assistantKeywords = config.assistantKeywords;
                const plainText = element => {
                    const clone = element.cloneNode(true);
                    clone.querySelectorAll(controls).forEach(node => node.remove());
                    return (clone.textContent || "").trim();
                };
                const contextFor = element => {
                    const parts = [];
                    for (let node = element; node && node !== document.body;
                         node = node.parentElement) {
                        const classes = typeof node.className === "string"
                            ? node.className : "";
                        parts.push(`${node.id || ""} ${classes}`);
                    }
                    return parts.join(" ").toLowerCase();
                };
                const describe = el => {
                    if (el.matches(controls) || el.closest("form")) return null;
                    const classes = el.className && typeof el.className === "string"
                        ? el.className.split(/\\s+/).filter(Boolean) : [];
                    const context = contextFor(el);
                    const semantic = contextKeywords.some(
                        keyword => context.includes(keyword)
                    );
                    if (!config.scopeSelector && !semantic) return null;
                    const text = plainText(el);
                    if (text.length < config.minTextLength) return null;
                    let depth = 0;
                    for (let parent = el.parentElement; parent;
                         parent = parent.parentElement) depth++;
                    return {
                        el, text, html: el.innerHTML, classes, depth, semantic,
                        assistantSemantic: assistantKeywords.some(
                            keyword => context.includes(keyword)
                        ),
                        customerSemantic: /\\b(user|customer|outgoing|sent)\\b/.test(
                            context
                        ),
                        images: [...el.querySelectorAll("img")]
                            .filter(image => image.complete && image.naturalWidth > 0)
                            .map(image => image.currentSrc || image.src)
                            .filter(Boolean),
                    };
                };
                const candidates = () => {
                    if (config.scopeSelector) {
                        return state.scopedElements
                            .map(describe).filter(Boolean);
                    }
                    const found = [];
                    const walker = document.createTreeWalker(
                        document.body,
                        NodeFilter.SHOW_ELEMENT,
                        { acceptNode: node =>
                            ignore.has(node.tagName.toLowerCase())
                                ? NodeFilter.FILTER_REJECT
                                : NodeFilter.FILTER_ACCEPT
                        }
                    );
                    while (walker.nextNode()) {
                        const candidate = describe(walker.currentNode);
                        if (candidate) found.push(candidate);
                    }
                    return found;
                };
                const baseline = new WeakMap();
                const state = {
                    baseline, candidates, scopeSelector: config.scopeSelector,
                    scopedElements: [], describe,
                };
                globalThis[config.stateKey] = state;
                if (!config.scopeSelector && config.baselineExisting) {
                    for (const candidate of candidates()) {
                        baseline.set(candidate.el, candidate.text);
                    }
                }
            }""",
            {
                "stateKey": _BASELINE_STATE_KEY,
                "ignoreTags": list(consts.RESPONSE_IGNORE_TAGS),
                "minTextLength": consts.RESPONSE_MIN_TEXT_LENGTH,
                "contextKeywords": _RESPONSE_CONTEXT_KEYWORDS,
                "assistantKeywords": _RESPONSE_ELEMENT_KEYWORDS,
                "scopeSelector": scope_selector,
                "baselineExisting": baseline_existing,
            },
        )
        if scope_selector:
            await page.locator(scope_selector).evaluate_all(
                """(elements, config) => {
                    const state = globalThis[config.stateKey];
                    state.scopedElements = elements;
                    if (config.baselineExisting) {
                        for (const candidate of state.candidates()) {
                            state.baseline.set(candidate.el, candidate.text);
                        }
                    }
                }""",
                {
                    "stateKey": _BASELINE_STATE_KEY,
                    "baselineExisting": baseline_existing,
                },
            )

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
        *,
        timeout_ms: int | None = None,
        submitted_text: str | None = None,
        stable_interval_ms: int | None = None,
        poll_interval_ms: int | None = None,
    ) -> dict | None:
        """Poll until the same qualified response parts remain stable."""
        timeout_ms = timeout_ms or consts.RESPONSE_PROBE_TIMEOUT_MS
        interval_ms = poll_interval_ms or consts.RESPONSE_POLL_INTERVAL_MS
        stable_ms = stable_interval_ms or consts.RESPONSE_DOM_SETTLE_MS
        elapsed = 0
        stable_elapsed = 0
        previous_signature: tuple[str, str] | None = None
        previous_result: dict | None = None

        while elapsed < timeout_ms:
            result = await self._response_state(
                page, submitted_text=submitted_text
            )
            if result:
                self.last_rejections = result["rejected"]
                if result["matches"]:
                    text = "\n\n".join(
                        part["text"] for part in result["matches"]
                    )
                    html = "\n".join(
                        part["html"] for part in result["matches"]
                    )
                    signature = (text, html)
                    previous_result = {
                        "text": text,
                        "html": html,
                        "images": list(dict.fromkeys(
                            image
                            for part in result["matches"]
                            for image in part["images"]
                        )),
                        "part_count": len(result["matches"]),
                        "primary": result["matches"][0],
                    }
                    if signature != previous_signature:
                        previous_signature = signature
                        stable_elapsed = 0
                    elif not result["generating"]:
                        stable_elapsed += interval_ms
                        if stable_elapsed >= stable_ms:
                            return previous_result
                else:
                    previous_signature = None
                    previous_result = None
                    stable_elapsed = 0

            await asyncio.sleep(interval_ms / 1000)
            elapsed += interval_ms

        return previous_result

    async def _response_state(
        self, page: Page | Frame, *, submitted_text: str | None
    ) -> dict | None:
        """Return changed qualified parts and rejection evidence."""
        if self._scope_selector:
            await page.locator(self._scope_selector).evaluate_all(
                """(elements, key) => {
                    const state = globalThis[key];
                    if (state) state.scopedElements = elements;
                }""",
                _BASELINE_STATE_KEY,
            )
        return await page.evaluate(
            """config => {
                const state = globalThis[config.stateKey];
                if (!state) return null;
                const rejected = {};
                const reject = reason => rejected[reason] = (rejected[reason] || 0) + 1;
                const normalise = text => text.replace(/\\s+/g, " ").trim();
                const transient = new RegExp(config.transientPattern, "i");
                const metadata = new RegExp(config.metadataPattern, "i");
                const system = new RegExp(config.systemPattern, "i");
                const greeting = new RegExp(config.greetingPattern, "i");
                const submitted = normalise(config.submittedText || "");
                const eligible = [];
                let changed = 0;
                for (const candidate of state.candidates()) {
                    const before = state.baseline.get(candidate.el);
                    if (before === candidate.text) continue;
                    changed++;
                    const text = normalise(candidate.text);
                    let reason = null;
                    if (transient.test(text)) reason = "transient";
                    else if (metadata.test(text)) reason = "metadata";
                    else if (candidate.customerSemantic) reason = "customer";
                    else if (submitted && (
                        text === submitted
                        || (text.includes(submitted) && !candidate.assistantSemantic)
                    )) reason = "echo";
                    else if (system.test(text)) reason = "system";
                    else if (greeting.test(text)) reason = "greeting";
                    if (reason) reject(reason);
                    else eligible.push(candidate);
                }
                const leaves = eligible.filter(match => !eligible.some(other =>
                    other.el !== match.el && match.el.contains(other.el)
                ));
                let matches = leaves;
                if (!state.scopeSelector) {
                    matches = [...leaves].sort((a, b) =>
                        Number(b.assistantSemantic) - Number(a.assistantSemantic)
                        || Number(b.semantic) - Number(a.semantic)
                        || b.depth - a.depth || a.text.length - b.text.length
                    ).slice(0, 1);
                }
                const path = node => {
                    const parts = [];
                    for (let current = node;
                         current && current.nodeType === Node.ELEMENT_NODE;
                         current = current.parentElement) {
                        if (current.id) {
                            parts.unshift('#' + CSS.escape(current.id));
                            break;
                        }
                        const tag = current.tagName.toLowerCase();
                        const siblings = current.parentElement
                            ? [...current.parentElement.children].filter(
                                sibling => sibling.tagName === current.tagName
                            ) : [];
                        const position = siblings.indexOf(current) + 1;
                        parts.unshift(siblings.length > 1
                            ? `${tag}:nth-of-type(${position})` : tag);
                        if (current.tagName === 'BODY') break;
                    }
                    return parts.join(' > ');
                };
                matches = matches.map(candidate => {
                    const tag = candidate.el.tagName.toLowerCase();
                    let selector = path(candidate.el);
                    if (candidate.el.id) selector = '#' + CSS.escape(candidate.el.id);
                    else if (candidate.semantic && candidate.classes.length) {
                        selector = tag + '.' + candidate.classes.join('.');
                    }
                    return {
                        text: candidate.text,
                        html: candidate.html,
                        images: candidate.images,
                        selector, tag, classes: candidate.classes,
                    };
                });
                const generating = config.typingSelectors.some(selector => {
                    try {
                        return [...document.querySelectorAll(selector)]
                            .some(element => element.getClientRects().length);
                    } catch (_) { return false; }
                });
                return {matches, rejected, changed, generating};
            }""",
            {
                "stateKey": _BASELINE_STATE_KEY,
                "submittedText": submitted_text or consts.RESPONSE_PROBE_MESSAGE,
                "transientPattern": consts.RESPONSE_TRANSIENT_PATTERN,
                "metadataPattern": consts.RESPONSE_METADATA_PATTERN,
                "systemPattern": consts.RESPONSE_SYSTEM_PATTERN,
                "greetingPattern": consts.RESPONSE_GREETING_PATTERN,
                "typingSelectors": TYPING_INDICATOR_SELECTORS,
            },
        )

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
