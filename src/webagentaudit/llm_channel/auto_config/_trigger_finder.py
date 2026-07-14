"""Hidden AI panel detection and activation.

Scans for buttons that open hidden chat panels (dialogs, side panels,
command menus) and attempts to activate them so that the input element
becomes visible.
"""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass

from playwright.async_api import ElementHandle, Frame, Page

from . import consts
from ._dom_utils import extract_element_props, is_element_interactable, is_element_visible
from ._selector_builder import SelectorBuilder
from .models import ElementCandidate, TriggerMechanism, TriggerResult

logger = logging.getLogger(__name__)


@dataclass
class TriggerCandidate:
    candidate: ElementCandidate
    element: ElementHandle
    score: float
    mechanism: TriggerMechanism


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

        # Compatibility helper: the configurator uses ``ranked_candidates``
        # and owns retries/reloads; direct callers still get one bounded pass.
        for item in await self.ranked_candidates(page):
            candidate, el, score, mechanism = (
                item.candidate, item.element, item.score, item.mechanism
            )

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

    async def ranked_candidates(
        self, page: Page | Frame
    ) -> list[TriggerCandidate]:
        """Return high-confidence candidates without clicking any of them."""
        candidates = await self._gather_candidates(page)
        has_css_var_panel = await self._check_css_var_panels(page)
        ranked: list[TriggerCandidate] = []
        for candidate, element in candidates:
            score, mechanism = self._score(candidate, has_css_var_panel)
            if score >= consts.TRIGGER_MIN_SCORE:
                ranked.append(TriggerCandidate(
                    candidate=candidate,
                    element=element,
                    score=score,
                    mechanism=mechanism,
                ))
        ranked.sort(key=lambda item: item.score, reverse=True)
        return ranked

    async def _input_already_visible(self, page: Page | Frame) -> bool:
        """Check if any chat input is already visible on the page."""
        for selector in consts.TRIGGER_INPUT_WAIT_SELECTORS:
            try:
                elements = await page.locator(selector).element_handles()
                for el in elements:
                    if await is_element_interactable(el):
                        return True
            except Exception:
                continue
        return False

    async def _gather_candidates(
        self, page: Page | Frame
    ) -> list[tuple[ElementCandidate, ElementHandle]]:
        """Collect all visible buttons that might be trigger elements."""
        candidates: list[tuple[ElementCandidate, ElementHandle]] = []
        seen: set[int] = set()

        # Check known dialog/menu selectors first
        all_selectors = (
            consts.TRIGGER_DIALOG_SELECTORS
            + consts.TRIGGER_MENU_SELECTORS
            + consts.TRIGGER_CHAT_LAUNCHER_SELECTORS
            + ["button", '[role="button"]']
        )

        for selector in all_selectors:
            try:
                elements = await page.locator(selector).element_handles()
            except Exception:
                continue
            for el in elements:
                if not await is_element_visible(el):
                    continue
                identity = await el.evaluate(
                    """el => {
                        const ids = window.__webagentauditElementIds
                            || (window.__webagentauditElementIds = new WeakMap());
                        const next = window.__webagentauditNextElementId || 1;
                        if (!ids.has(el)) {
                            ids.set(el, next);
                            window.__webagentauditNextElementId = next + 1;
                        }
                        return ids.get(el);
                    }"""
                )
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
        label = " ".join([
            candidate.text_content,
            candidate.aria_label,
            candidate.title,
            candidate.data_testid,
        ]).lower()
        if any(keyword in label for keyword in consts.TRIGGER_NEGATIVE_LABEL_KEYWORDS):
            return 0.0, mechanism
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
        if any(
            keyword in label
            for keyword in consts.TRIGGER_CONVERSATION_LABEL_KEYWORDS
        ):
            aria_controls_score = 1.0
        if any(kw in class_str for kw in ("command", "menu", "dialog", "panel", "sheet", "chat")):
            aria_controls_score = 0.5
            if "command" in class_str or "menu" in class_str:
                mechanism = TriggerMechanism.COMMAND_MENU
            elif any(kw in class_str for kw in ("panel", "sheet", "chat")):
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

        # A lower-right SVG control is commonly a floating chat launcher.
        box = candidate.bounding_box or {}
        viewport_width = box.get("viewportWidth", 0)
        viewport_height = box.get("viewportHeight", 0)
        is_corner_launcher = (
            viewport_width > 0
            and viewport_height > 0
            and box.get("x", 0) >= 0
            and box.get("y", 0) >= 0
            and box.get("x", 0) < viewport_width
            and box.get("y", 0) < viewport_height
            and box.get("x", 0) + box.get("width", 0) >= viewport_width * 0.75
            and box.get("y", 0) + box.get("height", 0) >= viewport_height * 0.65
        )
        if is_corner_launcher:
            mechanism = TriggerMechanism.SIDE_PANEL
        breakdown["floating_position"] = (
            consts.TRIGGER_WEIGHT_FLOATING_POSITION if is_corner_launcher else 0.0
        )

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
                        if await is_element_interactable(el):
                            return True
                except Exception:
                    continue
            await asyncio.sleep(interval / 1000)
            elapsed += interval

        return False
