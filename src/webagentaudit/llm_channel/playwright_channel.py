"""LLM channel that communicates via browser automation."""

from playwright.async_api import Browser, BrowserContext, Frame, Page, async_playwright

from webagentaudit.core.exceptions import (
    ChannelError,
    ChannelNotReadyError,
    ChannelTimeoutError,
)
from .base import BaseLlmChannel
from .config import ChannelConfig
from .models import ChannelMessage, ChannelResponse
from .strategies.base import BaseStrategy


class PlaywrightChannel(BaseLlmChannel):
    """Channel that interacts with web-based LLMs through browser automation."""

    def __init__(
        self,
        config: ChannelConfig,
        strategy: BaseStrategy,
        browser: Browser | None = None,
    ) -> None:
        super().__init__(config=config)
        self._strategy = strategy
        self._external_browser = browser
        self._playwright = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None
        self._interaction_target: Page | Frame | None = None

    async def connect(self, url: str) -> None:
        viewport = {
            "width": self._config.viewport_width,
            "height": self._config.viewport_height,
        }

        if self._config.user_data_dir:
            # Persistent context requires its own playwright/browser
            self._playwright = await async_playwright().start()
            launcher = getattr(self._playwright, self._config.browser)
            self._context = await launcher.launch_persistent_context(
                self._config.user_data_dir,
                headless=self._config.headless,
                viewport=viewport,
                user_agent=self._config.user_agent,
                extra_http_headers=self._config.extra_headers or {},
            )
            self._page = await self._context.new_page()
        elif self._external_browser:
            # Reuse external browser — only create context+page (cheap)
            self._context = await self._external_browser.new_context(
                viewport=viewport,
                user_agent=self._config.user_agent,
                extra_http_headers=self._config.extra_headers or {},
            )
            self._page = await self._context.new_page()
        else:
            # No external browser — full launch (original behavior)
            self._playwright = await async_playwright().start()
            launcher = getattr(self._playwright, self._config.browser)
            self._browser = await launcher.launch(
                headless=self._config.headless,
            )
            self._context = await self._browser.new_context(
                viewport=viewport,
                user_agent=self._config.user_agent,
                extra_http_headers=self._config.extra_headers or {},
            )
            self._page = await self._context.new_page()

        await self._page.goto(url, wait_until="domcontentloaded")

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
        await self._strategy.send_message(target, message.text)
        text = await self._strategy.get_response(
            target, self._config.timeout_ms
        )
        if text is None:
            raise ChannelTimeoutError("No response received within timeout")
        return ChannelResponse(text=text)

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
        return ChannelResponse(text=text)

    async def disconnect(self) -> None:
        if self._context:
            await self._context.close()
            self._context = None
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        self._page = None

    async def is_ready(self) -> bool:
        return self._page is not None
