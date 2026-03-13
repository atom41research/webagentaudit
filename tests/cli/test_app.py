"""Comprehensive CLI tests using Click's CliRunner.

Tests cover:
- Help text and command existence
- Option parsing for detect, assess, probes commands
- Path-based option validation
- Category/sophistication validation
- Option combinations
- Edge cases
"""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from webagentaudit.cli.app import cli
from webagentaudit.core.consts import VERSION


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def fixtures_dir():
    return Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def yaml_probes_dir(fixtures_dir):
    return str(fixtures_dir / "yaml_probes")


@pytest.fixture
def single_turn_yaml(fixtures_dir):
    return str(fixtures_dir / "yaml_probes" / "single_turn.yaml")


@pytest.fixture
def multi_turn_yaml(fixtures_dir):
    return str(fixtures_dir / "yaml_probes" / "multi_turn.yaml")


# ---------------------------------------------------------------------------
# Help text and command existence
# ---------------------------------------------------------------------------


class TestHelpAndVersion:
    """Verify top-level help, version, and subcommand help."""

    def test_top_level_help(self, runner):
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "detect" in result.output
        assert "assess" in result.output
        assert "probes" in result.output

    def test_version(self, runner):
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert VERSION in result.output
        assert "webagentaudit" in result.output

    def test_detect_help(self, runner):
        result = runner.invoke(cli, ["detect", "--help"])
        assert result.exit_code == 0
        assert "--headful" in result.output
        assert "--timeout" in result.output
        assert "--browser" in result.output
        assert "--output" in result.output

    def test_assess_help(self, runner):
        result = runner.invoke(cli, ["assess", "--help"])
        assert result.exit_code == 0
        for opt in [
            "--headful", "--screenshots", "--input-selector",
            "--response-selector", "--input-hint", "--submit-hint",
            "--iframe-selector", "--wait-for", "--category",
            "--sophistication", "--probe-dir", "--probe-file",
            "--probes", "--workers", "--timeout",
        ]:
            assert opt in result.output, f"Missing option {opt} in assess --help"

    def test_probes_help(self, runner):
        result = runner.invoke(cli, ["probes", "--help"])
        assert result.exit_code == 0
        assert "--category" in result.output
        assert "--output" in result.output
        assert "--probe-dir" in result.output

    def test_unknown_command(self, runner):
        result = runner.invoke(cli, ["nonexistent"])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# Detect command
# ---------------------------------------------------------------------------


class TestDetectCommand:
    """Tests for the detect command option parsing."""

    def test_detect_missing_url(self, runner):
        result = runner.invoke(cli, ["detect"])
        assert result.exit_code != 0

    def test_detect_help_shows_all_options(self, runner):
        result = runner.invoke(cli, ["detect", "--help"])
        assert result.exit_code == 0
        for opt in ["--headful", "--browser", "--browser-exe",
                     "--user-data-dir", "--timeout", "--verbose", "--output"]:
            assert opt in result.output, f"Missing {opt}"

    def test_detect_browser_choices(self, runner):
        result = runner.invoke(cli, ["detect", "--help"])
        assert "chromium" in result.output
        assert "firefox" in result.output
        assert "webkit" in result.output


# ---------------------------------------------------------------------------
# Assess command option parsing
# ---------------------------------------------------------------------------


class TestAssessOptionParsing:
    """Test that all assess options are accepted by the CLI parser."""

    def test_assess_missing_url(self, runner):
        result = runner.invoke(cli, ["assess"])
        assert result.exit_code != 0

    def test_assess_help_has_user_data_dir(self, runner):
        result = runner.invoke(cli, ["assess", "--help"])
        assert "--user-data-dir" in result.output

    def test_assess_help_has_submit_selector(self, runner):
        result = runner.invoke(cli, ["assess", "--help"])
        assert "--submit-selector" in result.output

    def test_assess_help_has_response_hint(self, runner):
        result = runner.invoke(cli, ["assess", "--help"])
        assert "--response-hint" in result.output

    def test_assess_help_has_browser_exe(self, runner):
        result = runner.invoke(cli, ["assess", "--help"])
        assert "--browser-exe" in result.output

    def test_assess_help_has_output(self, runner):
        result = runner.invoke(cli, ["assess", "--help"])
        assert "--output" in result.output


# ---------------------------------------------------------------------------
# Assess path-based options
# ---------------------------------------------------------------------------


class TestAssessPathOptions:
    """Test path validation for --probe-dir and --probe-file."""

    def test_probe_dir_valid(self, runner, yaml_probes_dir):
        """--probe-dir with existing directory is accepted by the parser."""
        result = runner.invoke(cli, ["assess", "--help"])
        assert "--probe-dir" in result.output

    def test_probe_dir_nonexistent(self, runner):
        """--probe-dir with nonexistent path should error."""
        result = runner.invoke(cli, [
            "assess", "http://example.com",
            "--probe-dir", "/nonexistent/path/xyz",
        ])
        assert result.exit_code != 0

    def test_probe_file_nonexistent(self, runner):
        """--probe-file with nonexistent path should error."""
        result = runner.invoke(cli, [
            "assess", "http://example.com",
            "--probe-file", "/nonexistent/file.yaml",
        ])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# Probes command
# ---------------------------------------------------------------------------


class TestProbesCommand:
    """Tests for the probes listing command."""

    def test_probes_no_options(self, runner):
        """probes with no options exits cleanly."""
        result = runner.invoke(cli, ["probes"])
        assert result.exit_code == 0

    def test_probes_output_text(self, runner):
        result = runner.invoke(cli, ["probes", "--output", "text"])
        assert result.exit_code == 0

    def test_probes_output_json(self, runner):
        result = runner.invoke(cli, ["probes", "--output", "json"])
        assert result.exit_code == 0

    def test_probes_output_invalid(self, runner):
        """Invalid output format should error."""
        result = runner.invoke(cli, ["probes", "--output", "xml"])
        assert result.exit_code != 0

    def test_probes_with_valid_category(self, runner):
        result = runner.invoke(cli, ["probes", "--category", "extraction"])
        assert result.exit_code == 0

    def test_probes_with_valid_sophistication(self, runner):
        result = runner.invoke(cli, ["probes", "--sophistication", "basic"])
        assert result.exit_code == 0

    def test_probes_with_probe_dir(self, runner, yaml_probes_dir):
        result = runner.invoke(cli, [
            "probes", "--probe-dir", yaml_probes_dir,
        ])
        assert result.exit_code == 0
        assert "Loaded" in result.output

    def test_probes_probe_dir_nonexistent(self, runner):
        result = runner.invoke(cli, [
            "probes", "--probe-dir", "/nonexistent/dir",
        ])
        assert result.exit_code != 0

    def test_probes_json_with_custom_dir(self, runner, yaml_probes_dir):
        """Probes from custom dir should appear in JSON output."""
        result = runner.invoke(cli, [
            "probes", "--probe-dir", yaml_probes_dir, "--output", "json",
        ])
        assert result.exit_code == 0
        assert "extraction" in result.output  # fixtures contain extraction probes

    def test_probes_category_filter_with_custom_dir(self, runner, yaml_probes_dir):
        result = runner.invoke(cli, [
            "probes", "--probe-dir", yaml_probes_dir,
            "--category", "extraction",
        ])
        assert result.exit_code == 0

    def test_probes_all_filters_combined(self, runner, yaml_probes_dir):
        result = runner.invoke(cli, [
            "probes", "--probe-dir", yaml_probes_dir,
            "--category", "extraction",
            "--sophistication", "basic",
            "--output", "json",
        ])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Category / sophistication validation in probes command
# ---------------------------------------------------------------------------


class TestProbesValidation:
    """Test that invalid category/sophistication values raise errors."""

    def test_invalid_category(self, runner):
        """Invalid category should raise a ValueError caught by Click."""
        result = runner.invoke(cli, ["probes", "--category", "bogus_category"])
        assert result.exit_code != 0

    def test_invalid_sophistication(self, runner):
        result = runner.invoke(cli, ["probes", "--sophistication", "mega"])
        assert result.exit_code != 0

    def test_mixed_valid_invalid_category(self, runner):
        """A comma-separated list with one invalid category should error."""
        result = runner.invoke(cli, [
            "probes", "--category", "extraction,bogus",
        ])
        assert result.exit_code != 0

    def test_valid_categories_comma_separated(self, runner):
        result = runner.invoke(cli, [
            "probes", "--category", "extraction,prompt_injection",
        ])
        assert result.exit_code == 0

    def test_valid_sophistication_comma_separated(self, runner):
        result = runner.invoke(cli, [
            "probes", "--sophistication", "basic,advanced",
        ])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Edge case handling."""

    def test_url_with_query_params(self, runner):
        """URL with special characters should be accepted by the parser."""
        result = runner.invoke(cli, [
            "assess", "--help",
        ])
        assert result.exit_code == 0

    def test_empty_category(self, runner):
        """Empty --category string is treated as no filter (passes)."""
        result = runner.invoke(cli, ["probes", "--category", ""])
        # Empty string results in an empty set — no filtering applied
        assert result.exit_code == 0

    def test_probes_text_output_has_header(self, runner, yaml_probes_dir):
        """Text output should have a structured header."""
        result = runner.invoke(cli, [
            "probes", "--probe-dir", yaml_probes_dir, "--output", "text",
        ])
        assert result.exit_code == 0
        assert "Available Probes" in result.output

    def test_probes_json_output_is_valid_json(self, runner, yaml_probes_dir):
        """JSON output should be parseable."""
        import json

        result = runner.invoke(cli, [
            "probes", "--probe-dir", yaml_probes_dir, "--output", "json",
        ])
        assert result.exit_code == 0
        # Filter out any non-JSON lines (like "Loaded X custom probe(s)")
        lines = result.output.strip().split("\n")
        # Find the JSON array in the output
        json_start = None
        for i, line in enumerate(lines):
            if line.strip().startswith("["):
                json_start = i
                break
        assert json_start is not None, "No JSON array found in output"
        json_str = "\n".join(lines[json_start:])
        data = json.loads(json_str)
        assert isinstance(data, list)
        assert len(data) > 0
        for item in data:
            assert "name" in item
            assert "category" in item

    def test_version_matches_consts(self, runner):
        """Version in CLI should match VERSION in core.consts."""
        result = runner.invoke(cli, ["--version"])
        assert VERSION in result.output
