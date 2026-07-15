"""Browser compatibility helpers for web-based LLM channels."""

from __future__ import annotations

import logging
import os
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.async_api import Page

_CHROMIUM_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/{version} Safari/537.36"
)

logger = logging.getLogger(__name__)


def effective_user_agent(
    browser: str,
    *,
    headless: bool,
    configured: str | None = None,
    browser_version: str | None = None,
) -> str | None:
    """Return a usable UA while preserving explicit and headed settings."""
    if configured:
        return configured
    if browser != "chromium" or not headless:
        return None
    return _CHROMIUM_USER_AGENT.format(version=browser_version or "120.0.0.0")


def window_position_launch_args(position: tuple[int, int] | None) -> list[str]:
    """Return Chromium arguments that make explicit positioning possible."""
    if position is None:
        return []

    args = [f"--window-position={position[0]},{position[1]}"]
    if sys.platform.startswith("linux") and os.environ.get("WAYLAND_DISPLAY"):
        args.insert(0, "--ozone-platform=x11")
    return args


async def apply_window_geometry(
    page: Page,
    *,
    browser: str,
    fullscreen: bool = False,
    position: tuple[int, int] | None = None,
) -> None:
    """Apply headed Chromium window bounds after the target exists."""
    if browser != "chromium" or not (fullscreen or position):
        return

    session = await page.context.new_cdp_session(page)
    try:
        window = await session.send("Browser.getWindowForTarget")
        window_id = window["windowId"]
        if position:
            await session.send("Browser.setWindowBounds", {
                "windowId": window_id,
                "bounds": {
                    "windowState": "normal",
                    "left": position[0],
                    "top": position[1],
                },
            })
            actual = (
                await session.send(
                    "Browser.getWindowBounds", {"windowId": window_id}
                )
            )["bounds"]
            if (
                actual.get("windowState") != "normal"
                or actual.get("left") != position[0]
                or actual.get("top") != position[1]
            ):
                logger.debug(
                    "Window manager adjusted Chromium position from %s to "
                    "(%s, %s) with state %s",
                    position,
                    actual.get("left"),
                    actual.get("top"),
                    actual.get("windowState"),
                )
        if fullscreen:
            await session.send("Browser.setWindowBounds", {
                "windowId": window_id,
                "bounds": {"windowState": "fullscreen"},
            })
            bounds = (
                await session.send(
                    "Browser.getWindowBounds", {"windowId": window_id}
                )
            )["bounds"]
            await session.send("Emulation.setDeviceMetricsOverride", {
                "width": bounds["width"],
                "height": bounds["height"],
                "deviceScaleFactor": 0,
                "mobile": False,
                "screenWidth": bounds["width"],
                "screenHeight": bounds["height"],
            })
    finally:
        await session.detach()
