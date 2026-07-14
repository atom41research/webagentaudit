"""Tests for LLM channel configuration."""

from webagentaudit.llm_channel.config import ChannelConfig


def test_fullscreen_implies_headed_browser():
    config = ChannelConfig(headless=True, fullscreen=True)

    assert config.headless is False
