"""LLM channel that communicates via browser automation."""

import asyncio
import logging
from datetime import UTC, datetime
from pathlib import Path

from playwright.async_api import Browser, BrowserContext, Frame, Page, async_playwright

from webagentaudit.core.exceptions import (
    ChannelError,
    ChannelNotReadyError,
    ChannelResponseError,
    ChannelSubmissionError,
    ChannelTimeoutError,
)
from .base import BaseLlmChannel
from .browser import (
    apply_window_geometry,
    browser_launch_options,
    effective_user_agent,
    goto_and_inspect,
    wait_for_domcontentloaded_and_inspect,
    window_position_launch_args,
)
from .config import ChannelConfig
from .consts import (
    PAGE_SETTLE_MS,
    TEXT_OBSERVATION_TIMEOUT_MS,
)
from .models import ChannelMessage, ChannelResponse
from .strategies.base import BaseStrategy

logger = logging.getLogger(__name__)


class PlaywrightChannel(BaseLlmChannel):
    """Channel that interacts with web-based LLMs through browser automation."""

    def __init__(
        self,
        config: ChannelConfig,
        strategy: BaseStrategy,
        browser: Browser | None = None,
        page: Page | None = None,
        context: BrowserContext | None = None,
        close_external_page: bool = True,
    ) -> None:
        super().__init__(config=config)
        self._strategy = strategy
        self._external_browser = browser
        self._external_page = page
        self._external_context = context
        self._close_external_page = close_external_page
        self._playwright = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None
        self._interaction_target: Page | Frame | None = None

    async def connect(self, url: str) -> None:
        viewport = None if self._config.fullscreen else {
            "width": self._config.viewport_width,
            "height": self._config.viewport_height,
        }
        launch_args = []
        if self._config.browser_profile:
            launch_args.append(
                f"--profile-directory={self._config.browser_profile}"
            )
        if self._config.fullscreen:
            launch_args.append("--start-fullscreen")
        launch_args.extend(
            window_position_launch_args(self._config.window_position)
        )
        launch_options = browser_launch_options(
            self._config.browser,
            self._config.executable_path,
            launch_args,
        )

        if self._external_page:
            self._page = self._external_page
            self._context = self._page.context
        elif self._external_context:
            self._context = self._external_context
            self._page = await self._context.new_page()
        elif self._config.user_data_dir:
            # Persistent context requires its own playwright/browser
            self._playwright = await async_playwright().start()
            launcher = getattr(self._playwright, self._config.browser)
            user_agent = effective_user_agent(
                self._config.browser,
                headless=self._config.headless,
                configured=self._config.user_agent,
            )
            self._context = await launcher.launch_persistent_context(
                self._config.user_data_dir,
                headless=self._config.headless,
                viewport=viewport,
                user_agent=user_agent,
                extra_http_headers=self._config.extra_headers or {},
                executable_path=self._config.executable_path,
                ignore_https_errors=self._config.ignore_https_errors,
                **launch_options,
            )
            self._page = await self._context.new_page()
        elif self._external_browser:
            # Reuse external browser — only create context+page (cheap)
            user_agent = effective_user_agent(
                self._config.browser,
                headless=self._config.headless,
                configured=self._config.user_agent,
                browser_version=self._external_browser.version,
            )
            self._context = await self._external_browser.new_context(
                viewport=viewport,
                user_agent=user_agent,
                extra_http_headers=self._config.extra_headers or {},
                ignore_https_errors=self._config.ignore_https_errors,
            )
            self._page = await self._context.new_page()
        else:
            # No external browser — full launch (original behavior)
            self._playwright = await async_playwright().start()
            launcher = getattr(self._playwright, self._config.browser)
            self._browser = await launcher.launch(
                headless=self._config.headless,
                executable_path=self._config.executable_path,
                **launch_options,
            )
            user_agent = effective_user_agent(
                self._config.browser,
                headless=self._config.headless,
                configured=self._config.user_agent,
                browser_version=self._browser.version,
            )
            self._context = await self._browser.new_context(
                viewport=viewport,
                user_agent=user_agent,
                extra_http_headers=self._config.extra_headers or {},
                ignore_https_errors=self._config.ignore_https_errors,
            )
            self._page = await self._context.new_page()

        await apply_window_geometry(
            self._page,
            browser=self._config.browser,
            fullscreen=self._config.fullscreen,
            position=self._config.window_position,
        )
        await self._page.bring_to_front()

        if not self._external_page:
            await goto_and_inspect(self._page, url, self._config.timeout_ms)
            await self._page.wait_for_timeout(PAGE_SETTLE_MS)

        prepared_target = await self._strategy.prepare_page(self._page)
        if prepared_target is not None:
            self._interaction_target = prepared_target
            return

        trigger_selector = getattr(self._strategy, "trigger_selector", None)
        if trigger_selector:
            try:
                await self._strategy.activate_trigger(self._page)
            except Exception as exc:
                raise ChannelError(
                    f"Could not activate discovered trigger '{trigger_selector}': {exc}"
                ) from exc

        # Resolve iframe if strategy specifies one
        iframe_sel = getattr(self._strategy, "iframe_selector", None)
        if iframe_sel:
            try:
                iframe_el = self._page.locator(iframe_sel)
                await iframe_el.wait_for(timeout=self._config.timeout_ms)
                frame = await iframe_el.element_handle()
                content_frame = await frame.content_frame()
                if content_frame is None:
                    raise ChannelError(
                        f"Could not access content frame of '{iframe_sel}'"
                    )
                self._interaction_target = content_frame
            except ChannelError:
                raise
            except Exception as exc:
                raise ChannelError(
                    f"Failed to resolve iframe '{iframe_sel}': {exc}"
                ) from exc
        else:
            self._interaction_target = self._page

    @property
    def _target(self) -> Page | Frame:
        """The page or frame to interact with."""
        if self._interaction_target is None:
            raise ChannelNotReadyError("Channel not connected")
        return self._interaction_target

    async def send(self, message: ChannelMessage) -> ChannelResponse:
        target = self._target
        try:
            await self._strategy.prepare_response(target)
        except Exception as exc:
            raise ChannelResponseError(
                f"Could not prepare response reader: {exc}"
            ) from exc
        started_at = asyncio.get_running_loop().time()
        existing_pages = set(self._context.pages) if self._context else set()
        new_page: asyncio.Future[Page] | None = None
        page_listener = None
        if self._context:
            new_page = asyncio.get_running_loop().create_future()

            def page_listener(page: Page) -> None:
                if page not in existing_pages and not new_page.done():
                    new_page.set_result(page)

            self._context.on("page", page_listener)
        try:
            try:
                await self._strategy.send_message(target, message.text)
            except ChannelSubmissionError:
                raise
            except Exception as exc:
                raise ChannelSubmissionError(
                    f"Could not type or submit prompt: {exc}"
                ) from exc
            if self._config.post_send_wait_ms:
                await asyncio.sleep(self._config.post_send_wait_ms / 1000)
            if new_page and new_page.done():
                target = await self._activate_page(
                    new_page.result(), self._config.timeout_ms
                )
                if self._context and page_listener:
                    self._context.remove_listener("page", page_listener)
                    page_listener = None
                new_page = None
            if self._config.post_send_screenshot_dir and self._page:
                screenshot_dir = Path(self._config.post_send_screenshot_dir)
                screenshot_dir.mkdir(parents=True, exist_ok=True)
                filename = datetime.now(UTC).strftime(
                    "after_send_%Y%m%dT%H%M%S%fZ.png"
                )
                try:
                    await self._page.screenshot(
                        path=str(screenshot_dir / filename), full_page=True
                    )
                except Exception as exc:
                    logger.warning("Could not save post-send screenshot: %s", exc)
            text, target = await self._get_response_following_page(
                target, new_page
            )
            if text is None:
                raise ChannelTimeoutError("No response received within timeout")
            metadata = await self._strategy.get_response_metadata(target)
            response_time_ms = (
                asyncio.get_running_loop().time() - started_at
            ) * 1000
            if self._config.post_success_wait_ms:
                await asyncio.sleep(self._config.post_success_wait_ms / 1000)
            return ChannelResponse(
                text=text,
                response_time_ms=response_time_ms,
                timestamp=datetime.now(UTC),
                metadata=metadata,
            )
        except (ChannelSubmissionError, ChannelResponseError):
            raise
        except Exception as exc:
            raise ChannelResponseError(
                f"Could not read response: {exc}"
            ) from exc
        finally:
            if self._context and page_listener:
                self._context.remove_listener("page", page_listener)
            if new_page and not new_page.done():
                new_page.cancel()

    async def _activate_page(self, page: Page, timeout_ms: int) -> Page:
        self._page = page
        self._interaction_target = page
        await wait_for_domcontentloaded_and_inspect(page, timeout_ms)
        return page

    async def _get_response_following_page(
        self,
        target: Page | Frame,
        new_page: asyncio.Future[Page] | None,
    ) -> tuple[str | None, Page | Frame]:
        """Read the response, switching if submission opens a delayed page."""
        if new_page is None:
            return (
                await self._strategy.get_response(
                    target, self._config.timeout_ms
                ),
                target,
            )

        loop = asyncio.get_running_loop()
        deadline = loop.time() + self._config.timeout_ms / 1000
        response = asyncio.create_task(
            self._strategy.get_response(target, self._config.timeout_ms)
        )
        done, _ = await asyncio.wait(
            {response, new_page}, return_when=asyncio.FIRST_COMPLETED
        )
        if response in done:
            try:
                return response.result(), target
            except ChannelResponseError:
                if new_page not in done:
                    raise

        if not response.done():
            response.cancel()
            await asyncio.gather(response, return_exceptions=True)
        remaining_ms = int((deadline - loop.time()) * 1000)
        if remaining_ms <= 0:
            raise ChannelTimeoutError("No response received within timeout")
        target = await self._activate_page(new_page.result(), remaining_ms)
        remaining_ms = int((deadline - loop.time()) * 1000)
        if remaining_ms <= 0:
            raise ChannelTimeoutError("No response received within timeout")
        return (
            await self._strategy.get_response(target, remaining_ms),
            target,
        )

    async def write(self, text: str) -> None:
        target = self._target
        input_sel = await self._strategy.find_input(target)
        if not input_sel:
            raise ChannelNotReadyError("Input element not found")
        await target.fill(input_sel, text)

    async def read(self, timeout_ms: int | None = None) -> ChannelResponse:
        target = self._target
        timeout = timeout_ms or self._config.timeout_ms
        text = await self._strategy.get_response(target, timeout)
        if text is None:
            raise ChannelTimeoutError("No response received within timeout")
        return ChannelResponse(text=text, timestamp=datetime.now(UTC))

    async def observe_text(self) -> str | None:
        """Return accessible rendered text across the active page's frames."""
        if self._page is None or self._page.is_closed():
            return None
        rendered = []
        for frame in self._page.frames:
            try:
                text = await frame.locator("body").inner_text(
                    timeout=TEXT_OBSERVATION_TIMEOUT_MS
                )
            except Exception:
                logger.debug("Could not observe rendered text in frame")
                continue
            if text:
                rendered.append(text)
        return "\n".join(rendered)

    async def disconnect(self) -> None:
        if self._external_context and self._page:
            if self._close_external_page:
                await self._page.close()
            self._context = None
        elif self._context:
            await self._context.close()
            self._context = None
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        self._page = None
        self._interaction_target = None

    async def is_ready(self) -> bool:
        return self._page is not None
