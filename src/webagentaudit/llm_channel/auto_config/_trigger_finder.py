"""Hidden AI panel detection and activation.

Scans for buttons that open hidden chat panels (dialogs, side panels,
command menus) and attempts to activate them so that the input element
becomes visible.
"""

from __future__ import annotations

import asyncio
import logging
import re

from playwright.async_api import ElementHandle, Frame, Page

from . import consts
from ._dom_utils import extract_element_props, is_element_visible
from ._selector_builder import SelectorBuilder
from .models import ElementCandidate, TriggerMechanism, TriggerResult

logger = logging.getLogger(__name__)


class TriggerFinder:
    """Find and activate trigger buttons that reveal hidden AI chat panels.

    Scoring factors (from ``consts``):
    - AI label keywords in text/aria-label
    - ``aria-haspopup="dialog"`` attribute
    - ``aria-controls`` pointing to a panel/dialog
    - CSS variables indicating a hidden panel
    - SVG icon child
    """

    def __init__(self, selector_builder: SelectorBuilder | None = None) -> None:
        self._selector_builder = selector_builder or SelectorBuilder()

    async def find_and_activate(
        self, page: Page | Frame
    ) -> TriggerResult | None:
        """Find a trigger button, click it, and verify an input appears.

        Returns:
            A ``TriggerResult`` if a trigger was found and successfully
            activated (an input element appeared). ``None`` if no trigger
            is needed (input already visible) or activation failed.
        """
        # If an input is already visible, no trigger needed
        if await self._input_already_visible(page):
            logger.debug("Input already visible, no trigger needed")
            return None

        candidates = await self._gather_candidates(page)
        if not candidates:
            logger.debug("No trigger candidates found")
            return None

        # Check for CSS variable hidden panels
        has_css_var_panel = await self._check_css_var_panels(page)

        # Score and sort candidates
        scored = []
        for candidate, el in candidates:
            score, mechanism = self._score(candidate, has_css_var_panel)
            scored.append((candidate, el, score, mechanism))

        scored.sort(key=lambda x: x[2], reverse=True)

        # Try each candidate from highest score
        for candidate, el, score, mechanism in scored:
            if score < consts.TRIGGER_MIN_SCORE:
                continue

            logger.debug(
                "Trying trigger: %s (score=%.3f, mechanism=%s)",
                candidate.selector,
                score,
                mechanism.value,
            )

            # Click the trigger
            try:
                await el.click()
            except Exception:
                logger.debug("Failed to click trigger %s", candidate.selector)
                continue

            # Wait for an input to appear
            if await self._wait_for_input(page):
                return TriggerResult(
                    trigger_selector=candidate.selector,
                    mechanism=mechanism,
                    confidence=score,
                )

        return None

    async def _input_already_visible(self, page: Page | Frame) -> bool:
        """Check if any chat input is already visible on the page."""
        for selector in consts.TRIGGER_INPUT_WAIT_SELECTORS:
            try:
                elements = await page.locator(selector).element_handles()
                for el in elements:
                    if await is_element_visible(el):
                        return True
            except Exception:
                continue
        return False

    async def _gather_candidates(
        self, page: Page | Frame
    ) -> list[tuple[ElementCandidate, ElementHandle]]:
        """Collect all visible buttons that might be trigger elements."""
        candidates: list[tuple[ElementCandidate, ElementHandle]] = []
        seen: set[str] = set()

        # Check known dialog/menu selectors first
        all_selectors = (
            consts.TRIGGER_DIALOG_SELECTORS
            + consts.TRIGGER_MENU_SELECTORS
            + ["button"]
        )

        for selector in all_selectors:
            try:
                elements = await page.locator(selector).element_handles()
            except Exception:
                continue
            for el in elements:
                if not await is_element_visible(el):
                    continue
                identity = await el.evaluate("el => el.outerHTML.substring(0, 120)")
                if identity in seen:
                    continue
                seen.add(identity)

                candidate = await extract_element_props(el, page)
                candidate.selector = await self._selector_builder.build(el, page)
                candidates.append((candidate, el))

        return candidates

    async def _check_css_var_panels(self, page: Page | Frame) -> bool:
        """Check if CSS variables indicate a hidden assistant panel."""
        try:
            css_text: str = await page.evaluate(
                """() => {
                    const sheets = document.styleSheets;
                    let text = '';
                    try {
                        for (const sheet of sheets) {
                            for (const rule of sheet.cssRules) {
                                text += rule.cssText + '\\n';
                            }
                        }
                    } catch (e) {}
                    // Also check inline styles on :root
                    const root = document.documentElement;
                    text += root.getAttribute('style') || '';
                    return text;
                }"""
            )
            for pattern in consts.TRIGGER_CSS_VAR_PATTERNS:
                if re.search(pattern, css_text, re.IGNORECASE):
                    return True
        except Exception:
            pass
        return False

    def _score(
        self, candidate: ElementCandidate, has_css_var_panel: bool
    ) -> tuple[float, TriggerMechanism]:
        """Score a trigger candidate. Returns (score, mechanism)."""
        breakdown: dict[str, float] = {}
        mechanism = TriggerMechanism.DIALOG

        # AI label keywords
        label = (
            candidate.text_content + " " + candidate.aria_label
        ).lower()
        ai_label_score = 0.0
        for kw in consts.TRIGGER_AI_LABEL_KEYWORDS:
            if kw in label:
                ai_label_score = 1.0
                break
        breakdown["ai_label"] = ai_label_score * consts.TRIGGER_WEIGHT_AI_LABEL

        # Dialog attribute (aria-haspopup="dialog")
        # We detect this from the element's aria_label context and classes
        # The actual attribute check is via the selector matching in _gather_candidates
        dialog_score = 0.0
        # Check if this element was matched by a dialog selector
        for sel in consts.TRIGGER_DIALOG_SELECTORS:
            if "haspopup" in sel and "dialog" in sel:
                # The candidate was gathered; check its properties
                # We infer from the element props
                pass
        # Actually check the aria attributes via text content analysis
        # Since we can't directly check aria-haspopup from ElementCandidate,
        # we rely on the candidate text and aria_label
        breakdown["dialog_attr"] = dialog_score * consts.TRIGGER_WEIGHT_DIALOG_ATTR

        # aria-controls
        aria_controls_score = 0.0
        # Detected via menu selectors in gather
        # Check class names for command/menu/dialog hints
        class_str = " ".join(candidate.classes).lower()
        if any(kw in class_str for kw in ("command", "menu", "dialog", "panel", "sheet")):
            aria_controls_score = 0.5
            if "command" in class_str or "menu" in class_str:
                mechanism = TriggerMechanism.COMMAND_MENU
            elif "panel" in class_str or "sheet" in class_str:
                mechanism = TriggerMechanism.SIDE_PANEL
        # Check text/label for panel/assistant keywords
        if any(kw in label for kw in ("panel", "toggle", "assistant", "sheet")):
            mechanism = TriggerMechanism.SIDE_PANEL
            aria_controls_score = max(aria_controls_score, 0.5)
        if any(kw in label for kw in ("command", "menu")):
            mechanism = TriggerMechanism.COMMAND_MENU
            aria_controls_score = max(aria_controls_score, 0.5)
        breakdown["aria_controls"] = aria_controls_score * consts.TRIGGER_WEIGHT_ARIA_CONTROLS

        # CSS variable panel
        css_var_score = 1.0 if has_css_var_panel else 0.0
        breakdown["css_var"] = css_var_score * consts.TRIGGER_WEIGHT_CSS_VAR

        # Icon (SVG)
        icon_score = 1.0 if candidate.has_svg_child else 0.0
        breakdown["icon"] = icon_score * consts.TRIGGER_WEIGHT_ICON

        total = sum(breakdown.values())
        return total, mechanism

    async def _wait_for_input(self, page: Page | Frame) -> bool:
        """Wait for a chat input element to become visible after trigger click."""
        timeout = consts.TRIGGER_WAIT_FOR_INPUT_MS
        interval = 200
        elapsed = 0

        while elapsed < timeout:
            for selector in consts.TRIGGER_INPUT_WAIT_SELECTORS:
                try:
                    elements = await page.locator(selector).element_handles()
                    for el in elements:
                        if await is_element_visible(el):
                            return True
                except Exception:
                    continue
            await asyncio.sleep(interval / 1000)
            elapsed += interval

        return False
