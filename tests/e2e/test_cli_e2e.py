"""End-to-end CLI tests.

Tests the CLI commands against live demo pages using Click's CliRunner.

Note: detect/assess commands use asyncio.run() internally, so these tests
must be regular (non-async) functions to avoid nested event loop issues.
"""

from __future__ import annotations

import glob
import json
import socket
from pathlib import Path

import pytest
from click.testing import CliRunner

from webagentaudit.cli.app import cli

pytestmark = pytest.mark.e2e

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
YAML_PROBES_DIR = str(FIXTURES_DIR / "yaml_probes")


def _find_free_port() -> int:
    """Return a TCP port that is not listening."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


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
        url = f"{demo_server}/interactive/reverse-llm.html"
        result = runner.invoke(cli, ["detect", url, "--output", "text"])
        assert result.exit_code == 0, f"Failed: {result.output}"
        assert "Detection Result" in result.output

    def test_detect_json_output(self, runner, demo_server):
        """detect --output json should produce valid JSON."""
        url = f"{demo_server}/interactive/reverse-llm.html"
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
        assert data["url"] == url
        assert data["llm_detected"] is True
        assert data["overall_confidence"]["value"] > 0

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
        assert len(data.get("signals", [])) == 0

    def test_detect_with_timeout(self, runner, demo_server):
        url = f"{demo_server}/interactive/reverse-llm.html"
        result = runner.invoke(cli, [
            "detect", url, "--timeout", "60000",
        ])
        assert result.exit_code == 0, f"Failed: {result.output}"

    def test_detect_positive_has_signals(self, runner, demo_server):
        """detect JSON output for a positive page should include signals."""
        url = f"{demo_server}/interactive/reverse-llm.html"
        result = runner.invoke(cli, ["detect", url, "--output", "json"])
        assert result.exit_code == 0
        lines = result.output.strip().split("\n")
        json_start = next(
            i for i, line in enumerate(lines) if line.strip().startswith("{")
        )
        data = json.loads("\n".join(lines[json_start:]))
        assert data["llm_detected"] is True
        assert len(data["signals"]) > 0
        for signal in data["signals"]:
            assert "checker_name" in signal
            assert "signal_type" in signal
            assert signal["confidence"]["value"] > 0


# ---------------------------------------------------------------------------
# assess command e2e
# ---------------------------------------------------------------------------


SINGLE_PROBE_YAML = str(FIXTURES_DIR / "yaml_probes" / "single_turn.yaml")
SINGLE_PROBE_NAME = "extraction.custom_direct_ask"


class TestAssessE2E:
    """End-to-end tests for the assess command.

    Tests that verify CLI output format use a single probe to keep execution
    fast. Tests that verify detection behavior use the full probe dir with
    concurrent workers.
    """

    def test_assess_explicit_selectors(self, runner, demo_server):
        """assess with explicit selectors against echo page should succeed."""
        url = f"{demo_server}/interactive/reverse-llm.html"
        result = runner.invoke(cli, [
            "assess", url,
            "--input-selector", "#prompt-input",
            "--response-selector", ".bot-message:last-child",
            "--submit-selector", "#send-btn",
            "--probe-file", SINGLE_PROBE_YAML,
            "--probes", SINGLE_PROBE_NAME,
            "--output", "text",
        ])
        assert result.exit_code == 0, f"Failed: {result.output}"
        assert "Results" in result.output

    def test_assess_with_probe_file(self, runner, demo_server):
        """assess with --probe-file should succeed."""
        url = f"{demo_server}/interactive/reverse-llm.html"
        result = runner.invoke(cli, [
            "assess", url,
            "--input-selector", "#prompt-input",
            "--response-selector", ".bot-message:last-child",
            "--submit-selector", "#send-btn",
            "--probe-file", SINGLE_PROBE_YAML,
            "--probes", SINGLE_PROBE_NAME,
            "--output", "text",
        ])
        assert result.exit_code == 0, f"Failed: {result.output}"

    def test_assess_json_output(self, runner, demo_server):
        """assess --output json should produce valid JSON."""
        url = f"{demo_server}/interactive/reverse-llm.html"
        result = runner.invoke(cli, [
            "assess", url,
            "--input-selector", "#prompt-input",
            "--response-selector", ".bot-message:last-child",
            "--submit-selector", "#send-btn",
            "--probe-file", SINGLE_PROBE_YAML,
            "--probes", SINGLE_PROBE_NAME,
            "--output", "json",
        ])
        assert result.exit_code == 0, f"Failed: {result.output}"
        # Find JSON in output
        lines = result.output.strip().split("\n")
        json_start = None
        for i, line in enumerate(lines):
            if line.strip().startswith("{"):
                json_start = i
                break
        assert json_start is not None, f"No JSON in output: {result.output}"
        data = json.loads("\n".join(lines[json_start:]))
        assert "summary" in data
        assert "probe_results" in data
        assert data["summary"]["target_url"] == url
        assert data["summary"]["total_probes"] > 0
        assert len(data["probe_results"]) > 0
        pr = data["probe_results"][0]
        assert "exchanges" in pr
        assert len(pr["exchanges"]) > 0
        for ex in pr["exchanges"]:
            assert "messages" in ex and len(ex["messages"]) >= 2
            roles = [m["role"] for m in ex["messages"]]
            assert "user" in roles, "Exchange must have a user message"
            assert "assistant" in roles, "Exchange must have an assistant message"
            for m in ex["messages"]:
                assert m["content"], "Message content must be non-empty"

    def test_assess_text_output(self, runner, demo_server):
        """assess --output text should show results."""
        url = f"{demo_server}/interactive/reverse-llm.html"
        result = runner.invoke(cli, [
            "assess", url,
            "--input-selector", "#prompt-input",
            "--response-selector", ".bot-message:last-child",
            "--submit-selector", "#send-btn",
            "--probe-file", SINGLE_PROBE_YAML,
            "--probes", SINGLE_PROBE_NAME,
            "--output", "text",
        ])
        assert result.exit_code == 0, f"Failed: {result.output}"
        assert "Results" in result.output
        assert "Total Probes" in result.output

    def test_assess_vulnerable_finds_vuln(self, runner, demo_server):
        """assess against vulnerable page should find vulnerabilities."""
        url = f"{demo_server}/interactive/vulnerable-llm.html"
        result = runner.invoke(cli, [
            "assess", url,
            "--input-selector", "#prompt-input",
            "--response-selector", ".bot-message:last-child",
            "--submit-selector", "#send-btn",
            "--probe-dir", YAML_PROBES_DIR,
            "--category", "extraction",
            "--workers", "4",
            "--output", "json",
        ])
        assert result.exit_code == 0, f"Failed: {result.output}"
        lines = result.output.strip().split("\n")
        json_start = next(
            i for i, line in enumerate(lines) if line.strip().startswith("{")
        )
        data = json.loads("\n".join(lines[json_start:]))
        assert data["summary"]["vulnerabilities_found"] > 0
        # Find a vulnerable probe result and verify its exchanges
        vuln_probes = [pr for pr in data["probe_results"] if pr["vulnerability_detected"]]
        assert len(vuln_probes) > 0, "Should have at least one vulnerable probe"
        vp = vuln_probes[0]
        assert len(vp["matched_patterns"]) > 0
        assert len(vp["exchanges"]) > 0
        # Verify exchanges have assistant responses with actual content
        assert any(
            m["content"]
            for ex in vp["exchanges"]
            for m in ex["messages"]
            if m["role"] == "assistant"
        )

    def test_assess_multiple_probe_files(self, runner, demo_server):
        """assess with multiple --probe-file flags should run all probes."""
        url = f"{demo_server}/interactive/reverse-llm.html"
        probe_file_1 = SINGLE_PROBE_YAML
        yaml_files = sorted(glob.glob(str(FIXTURES_DIR / "yaml_probes" / "*.yaml")))
        if len(yaml_files) < 2:
            pytest.skip("Need at least 2 YAML probe files")
        probe_file_2 = yaml_files[1] if yaml_files[0] == probe_file_1 else yaml_files[0]

        result = runner.invoke(cli, [
            "assess", url,
            "--input-selector", "#prompt-input",
            "--response-selector", ".bot-message:last-child",
            "--submit-selector", "#send-btn",
            "--probe-file", probe_file_1,
            "--probe-file", probe_file_2,
            "--probes", f"{SINGLE_PROBE_NAME},extraction.trust_building_custom",
            "--workers", "4",
            "--output", "json",
        ])
        assert result.exit_code == 0, f"Failed: {result.output}"

    def test_assess_iframe_chat(self, runner, demo_server):
        """assess with --iframe-selector should work against iframe page."""
        url = f"{demo_server}/interactive/iframe-chat.html"
        result = runner.invoke(cli, [
            "assess", url,
            "--iframe-selector", "#chat-widget-frame",
            "--input-selector", "#prompt-input",
            "--response-selector", ".bot-message:last-child",
            "--submit-selector", "#send-btn",
            "--probe-file", SINGLE_PROBE_YAML,
            "--probes", SINGLE_PROBE_NAME,
            "--output", "text",
        ])
        assert result.exit_code == 0, f"Failed: {result.output}"


# ---------------------------------------------------------------------------
# URL loading failure tests
# ---------------------------------------------------------------------------


class TestDetectUrlFailures:
    """Detect command should show user-friendly errors for unreachable URLs."""

    def test_detect_dns_resolution_failure(self, runner):
        """Nonexistent domain should produce a clear error, not a traceback."""
        result = runner.invoke(cli, [
            "detect", "https://this-domain-does-not-exist-12345.invalid",
            "--timeout", "5000",
        ])
        assert result.exit_code != 0
        assert "Error: Could not load" in result.output
        assert "Traceback" not in result.output

    def test_detect_connection_refused(self, runner):
        """Connection to a port with nothing listening should error cleanly."""
        port = _find_free_port()
        result = runner.invoke(cli, [
            "detect", f"http://127.0.0.1:{port}",
            "--timeout", "5000",
        ])
        assert result.exit_code != 0
        assert "Error: Could not load" in result.output
        assert "Traceback" not in result.output

    def test_detect_timeout(self, runner):
        """Very short timeout should error cleanly, not crash."""
        # 1ms timeout — navigation can't complete in time
        result = runner.invoke(cli, [
            "detect", "https://example.com",
            "--timeout", "1",
        ])
        assert result.exit_code != 0
        assert "Error: Could not load" in result.output
        assert "Traceback" not in result.output

    def test_detect_invalid_url_scheme(self, runner):
        """Non-HTTP URL should error cleanly."""
        result = runner.invoke(cli, [
            "detect", "ftp://example.com",
            "--timeout", "5000",
        ])
        assert result.exit_code != 0
        assert "Traceback" not in result.output

    def test_detect_dns_failure_json_output(self, runner):
        """JSON mode should also handle URL failures without traceback."""
        result = runner.invoke(cli, [
            "detect", "https://this-domain-does-not-exist-12345.invalid",
            "--timeout", "5000", "--output", "json",
        ])
        assert result.exit_code != 0
        assert "Traceback" not in (result.output + (result.stderr or ""))


class TestAssessUrlFailures:
    """Assess command should show user-friendly errors for unreachable URLs."""

    def test_assess_dns_resolution_failure(self, runner):
        """Nonexistent domain should produce a clear error, not a traceback."""
        result = runner.invoke(cli, [
            "assess", "https://this-domain-does-not-exist-12345.invalid",
            "--timeout", "5000",
        ])
        assert result.exit_code != 0
        assert "Error: Could not load" in result.output
        assert "Traceback" not in result.output

    def test_assess_connection_refused(self, runner):
        """Connection to a closed port should error cleanly."""
        port = _find_free_port()
        result = runner.invoke(cli, [
            "assess", f"http://127.0.0.1:{port}",
            "--timeout", "5000",
        ])
        assert result.exit_code != 0
        assert "Error: Could not load" in result.output
        assert "Traceback" not in result.output

    def test_assess_timeout(self, runner):
        """Very short timeout should error cleanly, not crash."""
        result = runner.invoke(cli, [
            "assess", "https://example.com",
            "--timeout", "1",
        ])
        assert result.exit_code != 0
        assert "Error: Could not load" in result.output
        assert "Traceback" not in result.output
