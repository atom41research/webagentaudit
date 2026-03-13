"""LLM channel that communicates via browser automation."""

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

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
    ) -> None:
        super().__init__(config=config)
        self._strategy = strategy
        self._playwright = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None

    async def connect(self, url: str) -> None:
        self._playwright = await async_playwright().start()

        viewport = {
            "width": self._config.viewport_width,
            "height": self._config.viewport_height,
        }

        if self._config.user_data_dir:
            # Persistent context reuses an existing browser profile
            self._context = await self._playwright.chromium.launch_persistent_context(
                self._config.user_data_dir,
                headless=self._config.headless,
                viewport=viewport,
                user_agent=self._config.user_agent,
                extra_http_headers=self._config.extra_headers or {},
            )
            self._page = await self._context.new_page()
        else:
            self._browser = await self._playwright.chromium.launch(
                headless=self._config.headless,
            )
            self._context = await self._browser.new_context(
                viewport=viewport,
                user_agent=self._config.user_agent,
                extra_http_headers=self._config.extra_headers or {},
            )
            self._page = await self._context.new_page()

        await self._page.goto(url, wait_until="domcontentloaded")

    async def send(self, message: ChannelMessage) -> ChannelResponse:
        if not self._page:
            raise ChannelNotReadyError("Channel not connected")
        await self._strategy.send_message(self._page, message.text)
        text = await self._strategy.get_response(
            self._page, self._config.timeout_ms
        )
        if text is None:
            raise ChannelTimeoutError("No response received within timeout")
        return ChannelResponse(text=text)

    async def write(self, text: str) -> None:
        if not self._page:
            raise ChannelNotReadyError("Channel not connected")
        input_sel = await self._strategy.find_input(self._page)
        if not input_sel:
            raise ChannelNotReadyError("Input element not found")
        await self._page.fill(input_sel, text)

    async def read(self, timeout_ms: int | None = None) -> ChannelResponse:
        if not self._page:
            raise ChannelNotReadyError("Channel not connected")
        timeout = timeout_ms or self._config.timeout_ms
        text = await self._strategy.get_response(self._page, timeout)
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
