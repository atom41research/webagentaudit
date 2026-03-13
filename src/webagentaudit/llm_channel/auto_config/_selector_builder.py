"""CSS selector construction from DOM elements.

Builds stable, minimal CSS selectors by preferring (in order):
1. ID
2. ``data-testid``
3. Unique class name
4. Attribute-based selector (placeholder, aria-label)
5. Ancestor chain with ``>``
"""

from __future__ import annotations

import logging

from playwright.async_api import ElementHandle, Frame, Page

from . import consts
from .models import ElementCandidate

logger = logging.getLogger(__name__)


class SelectorBuilder:
    """Construct CSS selectors for discovered DOM elements."""

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def build(self, el: ElementHandle, page: Page | Frame) -> str:
        """Build a minimal CSS selector that uniquely identifies *el*."""

        props: dict = await el.evaluate(
            """el => {
                const tag = el.tagName.toLowerCase();
                const id = el.id || '';
                const testId = el.getAttribute('data-testid') || '';
                const classes = el.className && typeof el.className === 'string'
                    ? el.className.split(/\\s+/).filter(Boolean)
                    : [];
                const placeholder = el.getAttribute('placeholder') || '';
                const ariaLabel = el.getAttribute('aria-label') || '';

                // Ancestor info (up to 3 levels)
                const ancestors = [];
                let p = el.parentElement;
                for (let i = 0; i < 3 && p && p !== document.body; i++) {
                    ancestors.push({
                        tag: p.tagName.toLowerCase(),
                        id: p.id || '',
                        classes: p.className && typeof p.className === 'string'
                            ? p.className.split(/\\s+/).filter(Boolean)
                            : [],
                    });
                    p = p.parentElement;
                }
                return { tag, id, testId, classes, placeholder, ariaLabel, ancestors };
            }"""
        )

        tag = props["tag"]
        el_id = props["id"]
        test_id = props["testId"]
        classes = props["classes"]
        placeholder = props["placeholder"]
        aria_label = props["ariaLabel"]

        # 1. Stable ID
        if el_id and not self._is_dynamic_id(el_id):
            selector = f"#{el_id}"
            if await self._is_unique(selector, page):
                return selector

        # 2. data-testid
        if test_id:
            selector = f'[data-testid="{test_id}"]'
            if await self._is_unique(selector, page):
                return selector

        # 3. Unique class name
        stable_classes = self._filter_classes(classes)
        for cls in stable_classes:
            selector = f"{tag}.{cls}"
            if await self._is_unique(selector, page):
                return selector

        # 4. Placeholder attribute
        if placeholder:
            selector = f'{tag}[placeholder="{placeholder}"]'
            if await self._is_unique(selector, page):
                return selector

        # 5. aria-label
        if aria_label:
            selector = f'{tag}[aria-label="{aria_label}"]'
            if await self._is_unique(selector, page):
                return selector

        # 6. Ancestor chain
        ancestors = props.get("ancestors", [])
        return await self._build_ancestor_chain(tag, stable_classes, ancestors, page)

    async def build_response_selector(
        self, candidate: ElementCandidate, page: Page | Frame
    ) -> str:
        """Build a ``container > tag:last-of-type`` selector for response elements.

        Looks for a parent container that has multiple children of the same
        tag as *candidate*, then returns ``container > tag:last-of-type``.
        """
        tag = candidate.tag_name
        original_selector = candidate.selector

        # Try to find the parent container via the candidate's selector.
        # We use querySelectorAll and pick the last match (response elements
        # are typically the last sibling), then walk up until we find a
        # parent with an ID or stable classes.
        container_info: dict | None = await page.evaluate(
            """(args) => {
                const sel = args.sel;
                const candTag = args.tag;
                const candClasses = args.classes;

                // Find the element — prefer class-based match (more precise),
                // then fall back to generic selector
                let el = null;
                if (candClasses.length > 0) {
                    const classSel = candTag + '.' + candClasses.join('.');
                    const all = document.querySelectorAll(classSel);
                    if (all.length > 0) el = all[all.length - 1];
                }
                if (!el) {
                    try { el = document.querySelector(sel); } catch(e) {}
                }
                if (!el) return null;

                // Walk up to find the best parent container
                let parent = el.parentElement;
                const tag = el.tagName.toLowerCase();
                // Walk up at most 3 levels to find a parent with an ID
                let bestParent = parent;
                let p = parent;
                for (let i = 0; i < 3 && p && p !== document.body; i++) {
                    if (p.id) { bestParent = p; break; }
                    p = p.parentElement;
                }
                if (!bestParent || bestParent === document.body) {
                    bestParent = parent;
                }

                // Build a selector for the parent
                let parentSel = '';
                if (bestParent.id) {
                    parentSel = '#' + bestParent.id;
                } else {
                    const pTag = bestParent.tagName.toLowerCase();
                    const pClasses = bestParent.className && typeof bestParent.className === 'string'
                        ? bestParent.className.split(/\\s+/).filter(Boolean) : [];
                    if (pClasses.length > 0) {
                        parentSel = pTag + '.' + pClasses.join('.');
                    } else {
                        parentSel = pTag;
                    }
                }
                return {
                    parentSelector: parentSel,
                    childTag: tag,
                    siblingCount: bestParent.querySelectorAll(':scope > ' + tag).length,
                };
            }""",
            {"sel": original_selector, "tag": tag, "classes": candidate.classes},
        )

        if not container_info:
            return original_selector

        parent_sel = container_info["parentSelector"]
        child_tag = container_info["childTag"]

        # Build the :last-of-type selector
        response_sel = f"{parent_sel} > {child_tag}:last-of-type"

        # Verify it resolves to an element
        if await self._is_valid(response_sel, page):
            return response_sel

        return original_selector

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _is_dynamic_id(el_id: str) -> bool:
        """Return True if the ID looks auto-generated / session-dependent."""
        for prefix in consts.SELECTOR_DYNAMIC_ID_PATTERNS:
            if el_id.startswith(prefix) or prefix in el_id:
                return True
        return False

    @staticmethod
    def _filter_classes(classes: list[str]) -> list[str]:
        """Remove auto-generated and overly long class names."""
        result: list[str] = []
        for cls in classes:
            if len(cls) > consts.SELECTOR_MAX_CLASS_LENGTH:
                continue
            if any(cls.startswith(p) for p in consts.SELECTOR_AUTO_GENERATED_PREFIXES):
                continue
            result.append(cls)
        return result

    async def _build_ancestor_chain(
        self,
        tag: str,
        classes: list[str],
        ancestors: list[dict],
        page: Page | Frame,
    ) -> str:
        """Construct a ``parent > child`` selector using ancestor context."""
        for ancestor in ancestors:
            anc_id = ancestor.get("id", "")
            if anc_id and not self._is_dynamic_id(anc_id):
                selector = f"#{anc_id} > {tag}"
                if await self._is_unique(selector, page):
                    return selector

        for ancestor in ancestors:
            anc_tag = ancestor.get("tag", "div")
            anc_classes = self._filter_classes(ancestor.get("classes", []))
            for cls in anc_classes:
                selector = f"{anc_tag}.{cls} > {tag}"
                if await self._is_unique(selector, page):
                    return selector

        # Fallback: just tag (may not be unique)
        return tag

    @staticmethod
    async def _is_unique(selector: str, page: Page | Frame) -> bool:
        """Check whether exactly one element matches *selector*."""
        try:
            count = await page.evaluate(
                "(sel) => document.querySelectorAll(sel).length", selector
            )
            return count == 1
        except Exception:
            return False

    @staticmethod
    async def _is_valid(selector: str, page: Page | Frame) -> bool:
        """Check whether at least one element matches *selector*."""
        try:
            count = await page.evaluate(
                "(sel) => document.querySelectorAll(sel).length", selector
            )
            return count >= 1
        except Exception:
            return False
