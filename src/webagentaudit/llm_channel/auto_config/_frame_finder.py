"""Discovery of accessible frames that contain, or can expose, chat UI."""

from __future__ import annotations

import logging

from playwright.async_api import Frame, Page

from . import consts
from .models import FrameCandidate

logger = logging.getLogger(__name__)


class FrameFinder:
    """Rank chat frames without filtering out unknown vendors with real inputs."""

    async def find_chat_frames(self, page: Page) -> list[FrameCandidate]:
        candidates: list[FrameCandidate] = []
        for frame in page.frames:
            if frame is page.main_frame:
                continue
            try:
                element = await frame.frame_element()
                src = await element.get_attribute("src") or frame.url
                title = await element.get_attribute("title") or ""
                selector = await self._selector_for(element, frame.parent_frame)
                frame_path = await self.frame_path(frame)
                has_input = await self._frame_has_input(frame)
                score = 0.3 if has_input else 0.0

                if any(pattern in src.lower() for pattern in consts.FRAME_URL_PATTERNS):
                    score += 0.3
                if any(word in title.lower() for word in ("chat", "widget", "messenger")):
                    score += 0.2
                if await element.evaluate(
                    "(el, selectors) => selectors.some(selector => { "
                    "try { return el.matches(selector); } catch (_) { return false; } })",
                    consts.FRAME_CHAT_SELECTORS,
                ):
                    score += 0.5

                # An unknown frame with a usable input is more valuable than a
                # vendor signature with no rendered interface.
                if not has_input and score < consts.FRAME_MIN_SCORE:
                    continue
                candidates.append(FrameCandidate(
                    frame=frame,
                    score=score,
                    iframe_selector=selector,
                    src=src,
                    title=title,
                    has_input=has_input,
                    frame_path=frame_path,
                ))
            except Exception:
                logger.debug("Could not inspect frame %s", frame.url, exc_info=True)

        candidates.sort(key=lambda candidate: candidate.score, reverse=True)
        return candidates

    async def frame_path(self, frame: Frame) -> list[str]:
        """Build stable selectors from the main page to ``frame``."""
        path: list[str] = []
        current: Frame | None = frame
        while current is not None and current.parent_frame is not None:
            element = await current.frame_element()
            path.insert(0, await self._selector_for(element, current.parent_frame))
            current = current.parent_frame
        return path

    @staticmethod
    async def _selector_for(element, parent: Frame | None) -> str:
        """Prefer stable iframe attributes over positional selectors."""
        attributes = await element.evaluate(
            "el => ({id: el.id, name: el.name, title: el.title, "
            "testid: el.getAttribute('data-testid'), src: el.getAttribute('src')})"
        )
        choices = [
            ("id", attributes.get("id")),
            ("name", attributes.get("name")),
            ("data-testid", attributes.get("testid")),
            ("title", attributes.get("title")),
        ]
        for attribute, value in choices:
            if not value:
                continue
            escaped = value.replace("\\", "\\\\").replace('"', '\\"')
            selector = f'iframe[{attribute}="{escaped}"]'
            try:
                if parent is not None and await parent.locator(selector).count() == 1:
                    return selector
            except Exception:
                pass

        src = attributes.get("src") or ""
        if src and parent is not None:
            escaped = src.replace("\\", "\\\\").replace('"', '\\"')
            selector = f'iframe[src="{escaped}"]'
            try:
                if await parent.locator(selector).count() == 1:
                    return selector
            except Exception:
                pass

        if parent is None:
            return "iframe"
        return await element.evaluate(
            """node => {
                const parts = [];
                for (let current = node; current && current !== document.body;
                     current = current.parentElement) {
                    const tag = current.tagName.toLowerCase();
                    const siblings = current.parentElement
                        ? [...current.parentElement.children]
                            .filter(item => item.tagName === current.tagName)
                        : [];
                    const position = siblings.indexOf(current) + 1;
                    parts.unshift(
                        siblings.length > 1
                            ? `${tag}:nth-of-type(${position})`
                            : tag
                    );
                }
                return parts.join(' > ');
            }"""
        )

    @staticmethod
    async def _frame_has_input(frame: Frame) -> bool:
        try:
            for selector in consts.FRAME_INPUT_CHECK_SELECTORS:
                locator = frame.locator(selector)
                for index in range(await locator.count()):
                    if await locator.nth(index).is_visible():
                        return True
        except Exception:
            pass
        return False
