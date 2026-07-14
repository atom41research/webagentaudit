"""Tests for LLM channel configuration."""

from webagentaudit.llm_channel.config import ChannelConfig
from webagentaudit.llm_channel.browser import effective_user_agent


def test_fullscreen_implies_headed_browser():
    config = ChannelConfig(headless=True, fullscreen=True)

    assert config.headless is False


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
