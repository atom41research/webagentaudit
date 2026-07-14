"""Narrow handling of modal, consent, and onboarding blockers."""

from __future__ import annotations

import asyncio
import logging

from playwright.async_api import ElementHandle, Frame, Page

from . import consts
from ._dom_utils import is_element_interactable
from ._selector_builder import SelectorBuilder

logger = logging.getLogger(__name__)


class PreflightDismissal:
    """Find and click only recognised blocker controls."""

    def __init__(self, selector_builder: SelectorBuilder | None = None) -> None:
        self._selector_builder = selector_builder or SelectorBuilder()

    async def dismiss_one(self, page: Page | Frame) -> str | None:
        """Dismiss one top-most blocker and return its stable selector."""
        control = await self._find_dismiss_control(page)
        if control is None:
            return None
        selector = await self._selector_builder.build(control, page)
        await control.click()
        await asyncio.sleep(consts.PREFLIGHT_SETTLE_MS / 1000)
        return selector

    async def dismiss(self, page: Page | Frame) -> int:
        """Compatibility helper used by focused preflight tests."""
        dismissed = 0
        for _ in range(consts.PREFLIGHT_MAX_DISMISSALS):
            if await self.dismiss_one(page) is None:
                break
            dismissed += 1
        if dismissed:
            logger.info("Preflight dismissed %d blocking window(s)", dismissed)
        return dismissed

    async def _find_dismiss_control(
        self, page: Page | Frame
    ) -> ElementHandle | None:
        controls = page.locator("button, [role='button']")
        match = await controls.evaluate_all(
            r"""(elements, options) => {
                const matches = [];
                elements.forEach((el, index) => {
                    const rect = el.getBoundingClientRect();
                    const style = getComputedStyle(el);
                    if (el.disabled || rect.width <= 0 || rect.height <= 0
                        || style.display === 'none' || style.visibility === 'hidden') return;
                    const centerX = rect.left + rect.width / 2;
                    const centerY = rect.top + rect.height / 2;
                    if (centerX >= 0 && centerX <= window.innerWidth
                        && centerY >= 0 && centerY <= window.innerHeight) {
                        const top = document.elementFromPoint(centerX, centerY);
                        if (!top || (top !== el && !el.contains(top))) return;
                    }
                    const label = [el.textContent, el.getAttribute('aria-label'), el.title]
                        .filter(value => typeof value === 'string')
                        .join(' ').replace(/\s+/g, ' ').trim().toLowerCase();
                    let parent = el;
                    let blocker = false;
                    let zIndex = 0;
                    for (let depth = 0; depth < 8 && parent; depth++, parent = parent.parentElement) {
                        const identity = `${parent.id} ${parent.className || ''}`.toLowerCase();
                        const role = parent.getAttribute('role');
                        if (role === 'dialog' || parent.getAttribute('aria-modal') === 'true'
                            || /modal|dialog|overlay|onboarding|setup|welcome|tour|cookie|consent|banner/.test(identity)) {
                            blocker = true;
                            zIndex = Math.max(zIndex, Number.parseInt(getComputedStyle(parent).zIndex, 10) || 0);
                        }
                    }
                    const explicitSetup = options.explicit.some(
                        phrase => label.includes(phrase)
                    );
                    const safeLabel = options.dismiss.some(
                        phrase => label === phrase || label.startsWith(`${phrase} `)
                    );
                    if (safeLabel && (blocker || explicitSetup)) {
                        matches.push({index, zIndex});
                    }
                });
                matches.sort((a, b) => b.zIndex - a.zIndex);
                return matches[0] || null;
            }""",
            {
                "dismiss": consts.PREFLIGHT_DISMISS_KEYWORDS,
                "explicit": consts.PREFLIGHT_EXPLICIT_SETUP_KEYWORDS,
            },
        )
        if match is None:
            return None
        element = await controls.nth(match["index"]).element_handle()
        if element is None or not await is_element_interactable(element):
            return None
        return element
