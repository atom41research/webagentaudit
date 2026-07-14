"""Custom interaction strategy using user-provided CSS selectors."""

import asyncio
import json
import logging
from collections.abc import Callable

from playwright.async_api import ElementHandle, Frame, Page

from webagentaudit.core.exceptions import (
    ChannelError,
    ChannelNotReadyError,
    ChannelSubmissionError,
    ChannelTimeoutError,
)
from webagentaudit.llm_channel.models import InteractionAction, InteractionPlan

from ..auto_config._dom_utils import click_enabled_submit_after_fill
from ..auto_config._response_finder import ResponseFinder
from ..auto_config.chatbase import open_chatbase_widget
from ..auto_config.tidio import open_tidio_widget
from ..consts import (
    RESPONSE_POLL_INTERVAL_MS,
    RESPONSE_STABLE_INTERVAL_MS,
    SUBMISSION_CONFIRM_POLL_INTERVAL_MS,
    SUBMISSION_CONFIRM_TIMEOUT_MS,
    TYPING_INDICATOR_SELECTORS,
)
from .base import BaseInteractionStrategy

logger = logging.getLogger(__name__)


class CustomStrategy(BaseInteractionStrategy):
    """Strategy that uses explicit, user-provided CSS selectors.

    Unlike ChatWidgetStrategy, this strategy does not attempt to auto-detect
    elements. All selectors must be provided by the caller.
    """

    def __init__(
        self,
        input_selector: str | None = None,
        response_selector: str | None = None,
        submit_selector: str | None = None,
        iframe_selector: str | None = None,
        trigger_selector: str | None = None,
        plan: InteractionPlan | None = None,
        progress_callback: Callable[[str, str], None] | None = None,
    ) -> None:
        if plan is None and not input_selector:
            raise ValueError("input_selector is required for CustomStrategy")

        self._plan = plan or InteractionPlan(
            input_selector=input_selector or "",
            submit_selector=submit_selector,
            response_selector=response_selector,
            input_frame_path=[iframe_selector] if iframe_selector else [],
            setup_actions=(
                [InteractionAction(kind="trigger", selector=trigger_selector)]
                if trigger_selector else []
            ),
        )

        self._input_selector = self._plan.input_selector
        self._submit_selector = self._plan.submit_selector
        self._response_selector = self._plan.response_selector
        self._iframe_selector = (
            self._plan.input_frame_path[-1]
            if self._plan.input_frame_path else iframe_selector
        )
        self._trigger_selector = trigger_selector
        self._baseline_text = ""
        self._baseline_html = ""
        self._baseline_images: set[str] = set()
        self._baseline_element: ElementHandle | None = None
        self._response_prepared = False
        self._response_snapshot: set[str] | None = None
        self._submitted_text: str | None = None
        self._response_finder = ResponseFinder()
        self._progress_callback = progress_callback

    async def prepare_page(self, page: Page) -> Page | Frame:
        """Replay the successful discovery path in a fresh browser context."""
        for action in self._plan.setup_actions:
            try:
                if action.kind == "chatbase_open":
                    await open_chatbase_widget(page)
                    continue
                if action.kind == "intercom_show":
                    await page.wait_for_function(
                        "typeof window.Intercom === 'function'",
                        timeout=8_000,
                    )
                    await page.evaluate("window.Intercom('show')")
                    continue
                if action.kind == "chatbot_open":
                    await page.wait_for_function(
                "window.BE_API && typeof window.BE_API.openChatWindow === 'function'",
                        timeout=8_000,
                    )
                    await page.evaluate("window.BE_API.openChatWindow()")
                    continue
                if action.kind == "tidio_open":
                    await open_tidio_widget(page)
                    continue
                target = await self._resolve_frame_path(page, action.frame_path)
                control = target.locator(action.selector).locator("visible=true").first
                await control.wait_for(state="visible", timeout=3_000)
                await control.click(timeout=3_000)
            except Exception as exc:
                if action.optional:
                    continue
                if isinstance(exc, ChannelNotReadyError):
                    raise
                raise ChannelNotReadyError(
                    f"Could not replay {action.kind} action '{action.selector}'"
                ) from exc
        target = await self._resolve_frame_path(page, self._plan.input_frame_path)
        if not await self.find_input(target):
            raise ChannelNotReadyError(
                f"Discovered input '{self._input_selector}' was not available after setup"
            )
        self._emit("CHAT FOUND", self._input_selector)
        return target

    @staticmethod
    async def _resolve_frame_path(page: Page, frame_path: list[str]) -> Page | Frame:
        target: Page | Frame = page
        for selector in frame_path:
            iframe = target.locator(selector).first
            await iframe.wait_for(state="attached", timeout=3_000)
            handle = await iframe.element_handle()
            frame = await handle.content_frame() if handle else None
            if frame is None:
                raise ChannelNotReadyError(f"Could not access frame '{selector}'")
            target = frame
        return target

    @property
    def iframe_selector(self) -> str | None:
        return self._iframe_selector

    @property
    def trigger_selector(self) -> str | None:
        return self._trigger_selector

    async def activate_trigger(self, page: Page | Frame) -> None:
        """Open a chat panel discovered before the assessment channel starts."""
        if self._trigger_selector:
            await self._visible(page, self._trigger_selector).first.click()

    async def find_input(self, page: Page | Frame) -> bool:
        """Check that the user-provided input selector matches a visible element."""
        try:
            count = await self._visible(page, self._input_selector).count()
            logger.debug("find_input: '%s' matched %d visible element(s)", self._input_selector, count)
            return count > 0
        except Exception:
            return False

    async def prepare_response(self, page: Page | Frame) -> None:
        """Snapshot response content before sending the next message."""
        if not self._response_selector:
            self._response_snapshot = await self._response_finder.snapshot(page)
            self._baseline_images = set(await self._get_page_images(page))
            self._response_prepared = True
            return
        if self._baseline_element:
            try:
                await self._baseline_element.dispose()
            except Exception:
                pass
        self._baseline_text = await self._get_response_text(page)
        self._baseline_html = await self.get_response_html(page) or ""
        self._baseline_images = set(await self._get_response_images(page))
        elements = page.locator(self._response_selector)
        self._baseline_element = (
            await elements.last.element_handle()
            if await elements.count()
            else None
        )
        self._response_prepared = True

    async def send_message(self, page: Page | Frame, text: str) -> None:
        """Type text into the input and submit using user-provided selectors."""
        input_el = self._visible(page, self._input_selector).first
        # ``fill`` handles focus itself.  An explicit click here can block on
        # decorative overlays even when the input is otherwise fillable.
        logger.debug("send_message: filling input '%s' (%d chars)", self._input_selector, len(text))
        await input_el.fill(text)
        typed_text = await input_el.evaluate(
            "el => 'value' in el ? el.value : (el.innerText || el.textContent || '')"
        )
        if typed_text.strip() != text.strip():
            raise ChannelSubmissionError(
                "The selected chat input did not contain the intended prompt after filling"
            )
        self._submitted_text = text
        self._emit("TYPED", "prompt text verified in chat input")
        initial_url = page.url if isinstance(page, Page) else page.page.url
        initial_page_count = len(page.context.pages) if isinstance(page, Page) else 0

        if self._submit_selector:
            submit_el = self._visible(page, self._submit_selector).first
            logger.debug("send_message: clicking submit '%s'", self._submit_selector)
            if not await submit_el.is_enabled():
                email_fields = page.locator('input[type="email"]:visible')
                for index in range(await email_fields.count()):
                    if not (await email_fields.nth(index).input_value()).strip():
                        raise ChannelSubmissionError(
                            "Chat requires an email address before a message can be sent"
                        )
            try:
                await submit_el.wait_for(state="visible")
                await self._focus_element(submit_el)
            except Exception as exc:
                raise ChannelError(
                    f"Could not focus submit button '{self._submit_selector}': {exc}"
                ) from exc
        else:
            if await click_enabled_submit_after_fill(page, self._input_selector):
                logger.debug("send_message: clicked enabled submit discovered after fill")
            else:
                logger.debug("send_message: pressing Enter")
                await input_el.press("Enter")

        if not self._response_prepared:
            return

        if await self._wait_for_submission(
            page, text, initial_url, initial_page_count
        ):
            self._emit("SUBMITTED", "prompt left the chat input")
            return

        logger.debug("send_message: click had no effect; pressing Enter")
        await input_el.press("Enter")
        if not await self._wait_for_submission(
            page, text, initial_url, initial_page_count
        ):
            raise ChannelError("Prompt remained in the input after submit and Enter")
        self._emit("SUBMITTED", "prompt left the chat input after Enter fallback")

    async def _wait_for_submission(
        self,
        page: Page | Frame,
        submitted_text: str,
        initial_url: str,
        initial_page_count: int,
    ) -> bool:
        """Confirm that a click or keypress actually submitted the prompt."""
        elapsed_ms = 0
        while elapsed_ms < SUBMISSION_CONFIRM_TIMEOUT_MS:
            if isinstance(page, Page):
                if page.url != initial_url or len(page.context.pages) > initial_page_count:
                    return True
            elif page.page.url != initial_url:
                return True

            try:
                input_el = self._visible(page, self._input_selector).first
                if await input_el.count() == 0:
                    return True
                current_text = await input_el.evaluate(
                    "el => 'value' in el ? el.value : (el.innerText || el.textContent || '')"
                )
                if current_text.strip() != submitted_text.strip():
                    return True
            except Exception:
                return True

            current_text = await self._get_response_text(page)
            current_html = await self.get_response_html(page) or ""
            if (current_text, current_html) != (
                self._baseline_text,
                self._baseline_html,
            ):
                return True

            await asyncio.sleep(SUBMISSION_CONFIRM_POLL_INTERVAL_MS / 1000)
            elapsed_ms += SUBMISSION_CONFIRM_POLL_INTERVAL_MS
        return False

    async def wait_for_response(self, page: Page | Frame, timeout_ms: int) -> str:
        """Wait for response text to stabilise.

        Captures the baseline text before waiting so we can detect
        actual changes (not just pre-existing content).
        """
        logger.debug("wait_for_response: selector='%s', timeout=%dms", self._response_selector, timeout_ms)
        if not self._response_selector:
            if self._response_snapshot is None:
                raise ChannelTimeoutError("Response reader was not prepared")
            scored, response_text = await self._response_finder.wait(
                page,
                self._response_snapshot,
                timeout_ms=timeout_ms,
                submitted_text=self._submitted_text,
            )
            if scored is None:
                raise ChannelTimeoutError(f"No response received within {timeout_ms}ms")
            self._response_selector = scored.candidate.selector
            logger.debug(
                "wait_for_response: discovered selector '%s' from initial text '%s'",
                self._response_selector,
                (response_text or "")[:80],
            )
            # The discovered text may be only the first streamed token. Fall
            # through to the same stability loop used by explicit selectors.
            self._baseline_text = ""
            self._baseline_html = ""
            self._baseline_element = None
        poll_interval_s = RESPONSE_POLL_INTERVAL_MS / 1000
        stable_threshold_s = RESPONSE_STABLE_INTERVAL_MS / 1000
        timeout_s = timeout_ms / 1000

        if self._baseline_text:
            logger.debug("wait_for_response: baseline text (%d chars): '%s...'",
                         len(self._baseline_text), self._baseline_text[:80].replace("\n", " "))

        previous_signature: tuple[str, str, bool] | None = None
        previous_text = ""
        stable_elapsed = 0.0
        total_elapsed = 0.0

        while total_elapsed < timeout_s:
            await asyncio.sleep(poll_interval_s)
            total_elapsed += poll_interval_s

            current_text = await self._get_response_text(page)
            current_html = await self.get_response_html(page) or ""
            if not current_text.strip():
                stable_elapsed = 0.0
                continue
            if (
                self._submitted_text
                and current_text.strip() == self._submitted_text.strip()
            ):
                stable_elapsed = 0.0
                continue
            current_signature = (
                current_text,
                current_html,
                await self._is_baseline_element(page),
            )

            if current_signature == (
                self._baseline_text,
                self._baseline_html,
                True,
            ):
                continue

            if current_signature != previous_signature:
                preview = current_text[:80].replace("\n", " ")
                logger.debug("wait_for_response: content changed (%.1fs) '%s...'", total_elapsed, preview)
                previous_signature = current_signature
                previous_text = current_text
                stable_elapsed = 0.0
            else:
                if await self._is_generating(page):
                    stable_elapsed = 0.0
                    continue
                stable_elapsed += poll_interval_s
                if stable_elapsed >= stable_threshold_s:
                    logger.debug("wait_for_response: stable after %.1fs (%d chars)", total_elapsed, len(current_text))
                    self._emit("RESPONSE READ", "assistant output became stable")
                    return current_text

        if previous_signature is not None:
            logger.debug("wait_for_response: timeout but have text (%d chars)", len(previous_text))
            self._emit("RESPONSE READ", "assistant output read at timeout")
            return previous_text

        raise ChannelTimeoutError(
            f"No response received within {timeout_ms}ms"
        )

    @staticmethod
    async def _is_generating(page: Page | Frame) -> bool:
        """Whether a visible known typing indicator is still present."""
        for selector in TYPING_INDICATOR_SELECTORS:
            try:
                if await page.locator(selector).locator("visible=true").count():
                    return True
            except Exception:
                continue
        return False

    async def _is_baseline_element(self, page: Page | Frame) -> bool:
        """Whether the current response locator still points to the old node."""
        try:
            elements = page.locator(self._response_selector)
            if await elements.count() == 0:
                return self._baseline_element is None
            if self._baseline_element is None:
                return False
            current = await elements.last.element_handle()
            if current is None:
                return False
            try:
                return await current.evaluate(
                    "(element, baseline) => element === baseline",
                    self._baseline_element,
                )
            finally:
                await current.dispose()
        except Exception:
            return False

    async def get_response_html(self, page: Page | Frame) -> str | None:
        """Get the inner HTML of the response element."""
        if not self._response_selector:
            return None
        try:
            elements = page.locator(self._response_selector)
            count = await elements.count()
            if count == 0:
                return None
            return await elements.last.inner_html()
        except Exception:
            return None

    async def _get_response_text(self, page: Page | Frame) -> str:
        """Extract text from the response element."""
        if not self._response_selector:
            return ""
        try:
            elements = page.locator(self._response_selector)
            count = await elements.count()
            if count == 0:
                return ""
            return (await elements.last.inner_text()).strip()
        except Exception:
            return ""

    async def get_response_metadata(self, page: Page | Frame) -> dict[str, str]:
        """Report images added to the response after the prompt was sent."""
        current_images = set(await self._get_response_images(page))
        new_images = sorted(current_images - self._baseline_images)
        return {
            "image_count": str(len(new_images)),
            "image_urls": json.dumps(new_images),
        }

    async def _get_response_images(self, page: Page | Frame) -> list[str]:
        """Return loaded image URLs within the latest response element."""
        try:
            elements = page.locator(self._response_selector)
            if await elements.count() == 0:
                return []
            return await elements.last.locator("img").evaluate_all(
                """images => images
                    .filter(image => image.complete && image.naturalWidth > 0)
                    .map(image => image.currentSrc || image.src)
                    .filter(Boolean)"""
            )
        except Exception:
            return []

    @staticmethod
    async def _get_page_images(page: Page | Frame) -> list[str]:
        try:
            return await page.locator("img").evaluate_all(
                "images => images.filter(image => image.complete && image.naturalWidth > 0)"
                ".map(image => image.currentSrc || image.src).filter(Boolean)"
            )
        except Exception:
            return []

    def _emit(self, phase: str, detail: str) -> None:
        logger.info("%s: %s", phase, detail)
        if self._progress_callback:
            self._progress_callback(phase, detail)
