"""End-to-end CLI tests.

Tests the CLI commands against live demo pages using Click's CliRunner.

Note: detect/assess commands use asyncio.run() internally, so these tests
must be regular (non-async) functions to avoid nested event loop issues.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from webagentaudit.cli.app import cli

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
YAML_PROBES_DIR = str(FIXTURES_DIR / "yaml_probes")


@pytest.fixture
def runner():
    return CliRunner()


# ---------------------------------------------------------------------------
# detect command e2e
# ---------------------------------------------------------------------------


class TestDetectE2E:
    """End-to-end tests for the detect command."""

    def test_detect_text_output(self, runner, demo_server):
        """detect against an interactive demo page should find an LLM."""
        url = f"{demo_server}/interactive/echo-llm.html"
        result = runner.invoke(cli, ["detect", url, "--output", "text"])
        assert result.exit_code == 0, f"Failed: {result.output}"
        assert "Detection Result" in result.output

    def test_detect_json_output(self, runner, demo_server):
        """detect --output json should produce valid JSON."""
        url = f"{demo_server}/interactive/echo-llm.html"
        result = runner.invoke(cli, ["detect", url, "--output", "json"])
        assert result.exit_code == 0, f"Failed: {result.output}"
        # Find JSON in output (skip any non-JSON prefix)
        lines = result.output.strip().split("\n")
        json_start = None
        for i, line in enumerate(lines):
            if line.strip().startswith("{"):
                json_start = i
                break
        assert json_start is not None, "No JSON object in output"
        json_str = "\n".join(lines[json_start:])
        data = json.loads(json_str)
        assert "url" in data
        assert "llm_detected" in data

    def test_detect_negative_page(self, runner, demo_server):
        """detect against a negative page should not find an LLM."""
        url = f"{demo_server}/negative/simple-blog.html"
        result = runner.invoke(cli, ["detect", url, "--output", "json"])
        assert result.exit_code == 0, f"Failed: {result.output}"
        lines = result.output.strip().split("\n")
        json_start = None
        for i, line in enumerate(lines):
            if line.strip().startswith("{"):
                json_start = i
                break
        assert json_start is not None
        json_str = "\n".join(lines[json_start:])
        data = json.loads(json_str)
        assert data["llm_detected"] is False

    def test_detect_with_timeout(self, runner, demo_server):
        url = f"{demo_server}/interactive/echo-llm.html"
        result = runner.invoke(cli, [
            "detect", url, "--timeout", "60000",
        ])
        assert result.exit_code == 0, f"Failed: {result.output}"

    def test_detect_positive_has_signals(self, runner, demo_server):
        """detect JSON output for a positive page should include signals."""
        url = f"{demo_server}/interactive/echo-llm.html"
        result = runner.invoke(cli, ["detect", url, "--output", "json"])
        assert result.exit_code == 0
        lines = result.output.strip().split("\n")
        json_start = next(
            i for i, line in enumerate(lines) if line.strip().startswith("{")
        )
        data = json.loads("\n".join(lines[json_start:]))
        assert data["llm_detected"] is True
        assert len(data["signals"]) > 0


# ---------------------------------------------------------------------------
# probes command e2e with custom probe dir
# ---------------------------------------------------------------------------


class TestProbesE2E:
    """End-to-end tests for the probes command with real fixtures."""

    def test_probes_lists_custom_probes(self, runner):
        result = runner.invoke(cli, [
            "probes", "--probe-dir", YAML_PROBES_DIR, "--output", "json",
        ])
        assert result.exit_code == 0
        lines = result.output.strip().split("\n")
        json_start = next(
            i for i, line in enumerate(lines) if line.strip().startswith("[")
        )
        json_str = "\n".join(lines[json_start:])
        data = json.loads(json_str)
        assert len(data) > 0
        names = [p["name"] for p in data]
        assert "extraction.custom_direct_ask" in names

    def test_probes_text_output_structured(self, runner):
        result = runner.invoke(cli, [
            "probes", "--probe-dir", YAML_PROBES_DIR, "--output", "text",
        ])
        assert result.exit_code == 0
        assert "Available Probes" in result.output

    def test_probes_filter_category(self, runner):
        result = runner.invoke(cli, [
            "probes", "--probe-dir", YAML_PROBES_DIR,
            "--category", "extraction", "--output", "json",
        ])
        assert result.exit_code == 0
        lines = result.output.strip().split("\n")
        json_start = next(
            i for i, line in enumerate(lines) if line.strip().startswith("[")
        )
        data = json.loads("\n".join(lines[json_start:]))
        for probe in data:
            assert probe["category"] == "extraction"

    def test_probes_filter_sophistication(self, runner):
        result = runner.invoke(cli, [
            "probes", "--probe-dir", YAML_PROBES_DIR,
            "--sophistication", "basic", "--output", "json",
        ])
        assert result.exit_code == 0
        lines = result.output.strip().split("\n")
        json_start = next(
            i for i, line in enumerate(lines) if line.strip().startswith("[")
        )
        data = json.loads("\n".join(lines[json_start:]))
        for probe in data:
            assert probe["sophistication"] == "basic"
