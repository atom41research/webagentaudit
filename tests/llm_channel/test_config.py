"""Tests for LLM channel configuration."""

import pytest

from webagentaudit.llm_channel.config import ChannelConfig
from webagentaudit.llm_channel.browser import (
    effective_user_agent,
    window_position_launch_args,
)


def test_fullscreen_implies_headed_browser():
    config = ChannelConfig(headless=True, fullscreen=True)

    assert config.headless is False


def test_window_position_implies_headed_browser():
    config = ChannelConfig(headless=True, window_position=(0, 0))

    assert config.headless is False


def test_window_position_rejects_non_chromium_browser():
    with pytest.raises(ValueError, match="requires Chromium"):
        ChannelConfig(browser="firefox", window_position=(0, 0))


def test_window_position_uses_xwayland_when_wayland_is_active(monkeypatch):
    monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-0")
    monkeypatch.setattr(
        "webagentaudit.llm_channel.browser.sys.platform", "linux"
    )

    assert window_position_launch_args((0, 0)) == [
        "--ozone-platform=x11",
        "--window-position=0,0",
    ]


def test_headless_chromium_user_agent_does_not_advertise_headless_mode():
    user_agent = effective_user_agent(
        "chromium", headless=True, browser_version="145.0.1.2"
    )

    assert "Chrome/145.0.1.2" in user_agent
    assert "HeadlessChrome" not in user_agent


def test_explicit_user_agent_is_preserved():
    assert effective_user_agent(
        "chromium", headless=True, configured="custom-agent"
    ) == "custom-agent"
