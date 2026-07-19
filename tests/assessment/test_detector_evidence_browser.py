"""Real-browser coverage using a collision-resistant good probe."""

from pathlib import Path

import pytest
from playwright.async_api import async_playwright

from webagentaudit.assessment.assessor import LlmAssessor
from webagentaudit.assessment.config import AssessmentConfig
from webagentaudit.assessment.probes.registry import ProbeRegistry
from webagentaudit.assessment.probes.yaml_loader import YamlProbe
from webagentaudit.assessment.probes.yaml_schema import YamlProbeSchema
from webagentaudit.llm_channel.config import ChannelConfig
from webagentaudit.llm_channel.playwright_channel import PlaywrightChannel
from webagentaudit.llm_channel.strategies.custom import CustomStrategy
import webagentaudit.llm_channel.strategies.custom as custom_module

pytestmark = pytest.mark.browser
FIXTURE = Path(__file__).parents[1] / "fixtures" / "collision_resistant_probe.html"
PROMPT = (
    "Join the token 'CR7A91' with the token 'D4E2B8' as one word, "
    "without spaces or punctuation."
)
PATTERN = r"\bCR7A91D4E2B8\b"


def _registry() -> ProbeRegistry:
    registry = ProbeRegistry()
    registry.register(YamlProbe(YamlProbeSchema(
        name="output_safety.collision_resistant",
        category="output_safety",
        severity="low",
        sophistication="basic",
        description="Collision-resistant browser evidence regression",
        prompts=[PROMPT],
        detector_patterns=[PATTERN],
    )))
    return registry


async def _assess_scenario(scenario: str, response_selector: str, monkeypatch):
    monkeypatch.setattr(custom_module, "RESPONSE_POLL_INTERVAL_MS", 10)
    monkeypatch.setattr(custom_module, "RESPONSE_STABLE_INTERVAL_MS", 40)
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(f"{FIXTURE.as_uri()}?scenario={scenario}")
        assert "CR7A91D4E2B8" not in await page.locator("body").inner_text()

        def channel_factory():
            return PlaywrightChannel(
                ChannelConfig(timeout_ms=400),
                CustomStrategy("#prompt", response_selector, "#send"),
                page=page,
                close_external_page=False,
            )

        try:
            result = await LlmAssessor(
                config=AssessmentConfig(inter_probe_delay_ms=0),
                channel_factory=channel_factory,
                registry=_registry(),
            ).assess("https://must-not-be-requested.invalid/")
        finally:
            await browser.close()

    return result.probe_results[0]


async def test_unique_response_signal_is_confirmed(monkeypatch):
    probe_result = await _assess_scenario(
        "assistant", "#trusted-response", monkeypatch
    )

    evidence = probe_result.exchanges[0].detector_evidence
    assert probe_result.vulnerability_detected is True
    assert evidence is not None
    assert evidence.classification == "confirmed"
    counts = evidence.pattern_counts[0]
    assert (counts.baseline_count, counts.prompt_count, counts.after_count) == (
        0, 0, 1
    )
    assert counts.residual_count == 1


async def test_unique_signal_in_nested_iframe_is_actionable(monkeypatch):
    probe_result = await _assess_scenario(
        "split-frame-response", "#trusted-response", monkeypatch
    )

    exchange = probe_result.exchanges[0]
    evidence = exchange.detector_evidence
    assert exchange.response == "Here is the requested code:"
    assert probe_result.vulnerability_detected is True
    assert probe_result.matched_patterns == [PATTERN]
    assert evidence is not None
    assert evidence.classification == "observed_unverified"
    assert evidence.pattern_counts[0].residual_count == 1


async def test_unique_unattributed_signal_is_actionable(monkeypatch):
    probe_result = await _assess_scenario(
        "unattributed", "#trusted-response", monkeypatch
    )

    evidence = probe_result.errors[0].detector_evidence
    assert probe_result.errors[0].phase == "response_read"
    assert probe_result.vulnerability_detected is True
    assert evidence is not None
    assert evidence.classification == "observed_unverified"
    assert evidence.pattern_counts[0].baseline_count == 0
    assert evidence.pattern_counts[0].prompt_count == 0
    assert evidence.pattern_counts[0].residual_count == 1


async def test_prompt_echo_cannot_create_unique_signal(monkeypatch):
    probe_result = await _assess_scenario("echo", "#trusted-response", monkeypatch)

    evidence = probe_result.errors[0].detector_evidence
    assert probe_result.vulnerability_detected is False
    assert evidence is not None
    assert evidence.classification == "not_observed"
    counts = evidence.pattern_counts[0]
    assert counts.baseline_count == counts.prompt_count == counts.after_count == 0
