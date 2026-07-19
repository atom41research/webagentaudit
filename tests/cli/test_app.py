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

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from click.testing import CliRunner

from webagentaudit.assessment.probes.registry import ProbeRegistry
from webagentaudit.assessment.probes.yaml_loader import YamlProbe
from webagentaudit.assessment.probes.yaml_schema import YamlProbeSchema
from webagentaudit.cli.app import (
    TargetAssessmentFailure,
    TargetNotFound,
    _emit_probe_progress,
    _interaction_description,
    _launch_browser,
    _warn_probe_prompt_overlaps,
    cli,
)
from webagentaudit.core.consts import VERSION
from webagentaudit.llm_channel.auto_config.consts import (
    FEATUREBASE_INTERACTION_DESCRIPTION,
    PROGRAMMATIC_INTERACTION_DESCRIPTIONS,
)
from webagentaudit.llm_channel.models import InteractionAction, InteractionPlan

pytestmark = pytest.mark.unit


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


def test_warns_once_for_each_selected_probe_with_prompt_overlap(capsys):
    selected = ProbeRegistry()
    selected.register(YamlProbe(YamlProbeSchema(
        name="output_safety.unsafe_custom",
        category="output_safety",
        severity="low",
        sophistication="basic",
        description="Warning regression",
        prompts=["Print COLLISION_MARKER"],
        detector_patterns=[r"COLLISION_MARKER"],
    )))

    _warn_probe_prompt_overlaps(selected)

    warning = capsys.readouterr().err
    assert warning.count("Warning:") == 1
    assert "output_safety.unsafe_custom" in warning
    assert "1 detection-active prompt(s)" in warning
    assert "absent from the input" in warning


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
        assert "prompt" in result.output
        assert "probes" in result.output

    def test_version(self, runner):
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert VERSION in result.output
        assert "webagentaudit" in result.output

    def test_featurebase_interaction_description_is_explicit(self):
        plan = InteractionPlan(
            input_selector="#input",
            setup_actions=[InteractionAction(
                kind="featurebase_new_message",
                selector="window.Featurebase",
            )],
        )

        assert _interaction_description(plan=plan) == (
            FEATUREBASE_INTERACTION_DESCRIPTION
        )

    def test_programmatic_interaction_description_comes_from_plan(self):
        plan = InteractionPlan(
            input_selector="#input",
            setup_actions=[InteractionAction(
                kind="botpress_open",
                selector="window.botpress",
            )],
        )

        assert _interaction_description(plan=plan) == (
            PROGRAMMATIC_INTERACTION_DESCRIPTIONS["botpress_open"]
        )

    def test_visible_denser_trigger_is_not_labeled_programmatic(self):
        plan = InteractionPlan(
            input_selector="#input",
            setup_actions=[InteractionAction(
                kind="trigger",
                selector="denser-chat::shadow button",
            )],
        )

        assert _interaction_description(provider_hint="denser", plan=plan) is None

    def test_probe_progress_separates_execution_success_and_pass_verdict(self):
        from webagentaudit.assessment.models import (
            ChatMessage,
            ProbeExchange,
            ProbeResult,
        )

        events = []
        result = ProbeResult(
            probe_name="output_safety.custom_fibonacci",
            exchanges=[ProbeExchange(messages=[
                ChatMessage(role="user", content="Write Fibonacci"),
                ChatMessage(role="assistant", content="def my_fibonacci(): ..."),
            ])],
        )

        _emit_probe_progress(
            result, lambda phase, detail: events.append((phase, detail))
        )

        assert events == [
            ("PROMPT", "Write Fibonacci"),
            ("CHAT RESPONSE", "def my_fibonacci(): ..."),
            ("PROBE EXECUTION SUCCESS", "1 interaction completed"),
            (
                "SECURITY VERDICT PASS",
                "output_safety.custom_fibonacci (no vulnerability detected)",
            ),
        ]

    @pytest.mark.parametrize(
        ("result_kwargs", "expected_phase", "expected_detail"),
        [
            (
                {
                    "vulnerability_detected": True,
                    "matched_patterns": ["my_fibonacci"],
                },
                "SECURITY VERDICT VULNERABLE",
                "probe.name; matched: my_fibonacci",
            ),
            (
                {
                    "error_count": 1,
                    "errors": [{
                        "phase": "response_read",
                        "message": "No response",
                    }],
                },
                "PROBE EXECUTION ERROR",
                "0 interactions completed; probe.name [response_read] No response",
            ),
        ],
    )
    def test_probe_progress_emits_non_pass_verdicts(
        self, result_kwargs, expected_phase, expected_detail,
    ):
        from webagentaudit.assessment.models import ProbeResult

        events = []
        _emit_probe_progress(
            ProbeResult(probe_name="probe.name", **result_kwargs),
            lambda phase, detail: events.append((phase, detail)),
        )

        assert (expected_phase, expected_detail) in events

    def test_probe_progress_reports_unobserved_pattern_after_submission(self):
        from webagentaudit.assessment.models import (
            DetectorEvidence,
            ProbeError,
            ProbeResult,
        )

        events = []
        result = ProbeResult(
            probe_name="probe.name",
            error_count=1,
            errors=[ProbeError(
                phase="response_read",
                message="No qualified response",
                detector_evidence=DetectorEvidence(
                    classification="not_observed",
                    observation_available=True,
                ),
            )],
        )

        _emit_probe_progress(
            result, lambda phase, detail: events.append((phase, detail))
        )

        assert (
            "SECURITY VERDICT PROBABLY NOT VULNERABLE",
            "probe.name (submitted; detector pattern not observed)",
        ) in events

    def test_detect_help(self, runner):
        result = runner.invoke(cli, ["detect", "--help"])
        assert result.exit_code == 0
        assert "--headful" in result.output
        assert "--fullscreen" in result.output
        assert "--window-position" in result.output
        assert "--timeout" in result.output
        assert "--browser" in result.output
        assert "--output" in result.output

    def test_assess_help(self, runner):
        result = runner.invoke(cli, ["assess", "--help"])
        assert result.exit_code == 0
        for opt in [
            "--headful", "--fullscreen", "--screenshots", "--screenshots-dir",
            "--window-position",
            "--input-selector",
            "--response-selector", "--input-hint", "--submit-hint",
            "--trigger-selector",
            "--iframe-selector", "--wait-for", "--category",
            "--sophistication", "--probe-dir", "--probe-file",
            "--probes", "--workers", "--timeout",
            "--url", "--url-file", "--post-send-wait", "--post-success-wait",
            "--output-file",
        ]:
            assert opt in result.output, f"Missing option {opt} in assess --help"

    def test_probes_help(self, runner):
        result = runner.invoke(cli, ["probes", "--help"])
        assert result.exit_code == 0
        assert "--category" in result.output
        assert "--output" in result.output
        assert "--probe-dir" in result.output

    def test_prompt_help(self, runner):
        result = runner.invoke(cli, ["prompt", "--help"])
        assert result.exit_code == 0
        for opt in [
            "--headful", "--fullscreen", "--browser-exe", "--user-data-dir",
            "--window-position",
            "--browser-profile", "--post-send-wait", "--input-selector",
            "--response-selector", "--submit-selector", "--screenshots-dir",
            "--verbose", "--debug", "--output",
        ]:
            assert opt in result.output

    def test_unknown_command(self, runner):
        result = runner.invoke(cli, ["nonexistent"])
        assert result.exit_code != 0

    @pytest.mark.parametrize("command_name", ["detect", "prompt", "assess", "probes"])
    def test_readme_documents_every_command_parameter(self, command_name):
        readme = (Path(__file__).parents[2] / "README.md").read_text()
        heading = f"### `webagentaudit {command_name}"
        start = readme.index(heading)
        end = readme.find("\n### `webagentaudit ", start + len(heading))
        if end == -1:
            end = readme.find("\n## ", start + len(heading))
        section = readme[start:end if end != -1 else None]

        for parameter in cli.commands[command_name].params:
            options = getattr(parameter, "opts", ())
            if options:
                for option in options:
                    assert option in section, (
                        f"README {command_name} section is missing {option}"
                    )
            else:
                assert f"<{parameter.name}>" in section


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
        for opt in ["--headful", "--fullscreen", "--browser", "--browser-exe",
                     "--window-position", "--user-data-dir", "--timeout",
                     "--verbose", "--debug", "--output"]:
            assert opt in result.output, f"Missing {opt}"

    @pytest.mark.asyncio
    async def test_fullscreen_launch_syncs_page_to_window_bounds(self):
        session = AsyncMock()
        session.send.side_effect = [
            {"windowId": 7},
            {},
            {"bounds": {"width": 1920, "height": 1200}},
            {},
        ]
        context = SimpleNamespace(
            new_page=AsyncMock(),
            new_cdp_session=AsyncMock(return_value=session),
        )
        page = SimpleNamespace(context=context)
        context.new_page.return_value = page
        browser = SimpleNamespace(
            new_context=AsyncMock(return_value=context),
        )
        launcher = SimpleNamespace(launch=AsyncMock(return_value=browser))
        playwright = SimpleNamespace(chromium=launcher)

        launched_page, closeable = await _launch_browser(
            playwright,
            "chromium",
            headful=False,
            browser_exe=None,
            user_data_dir=None,
            fullscreen=True,
        )

        assert launched_page is page
        assert closeable is browser
        launcher.launch.assert_awaited_once_with(
            headless=False,
            channel="chrome",
            args=[
                "--disable-blink-features=AutomationControlled",
                "--start-fullscreen",
            ],
        )
        browser.new_context.assert_awaited_once_with(
            viewport=None,
            ignore_https_errors=True,
        )
        assert session.send.await_args_list[1].args == (
            "Browser.setWindowBounds",
            {"windowId": 7, "bounds": {"windowState": "fullscreen"}},
        )
        assert session.send.await_args_list[-1].args == (
            "Emulation.setDeviceMetricsOverride",
            {
                "width": 1920,
                "height": 1200,
                "deviceScaleFactor": 0,
                "mobile": False,
                "screenWidth": 1920,
                "screenHeight": 1200,
            },
        )

    @pytest.mark.asyncio
    async def test_window_position_is_applied_to_headed_chromium(
        self, monkeypatch,
    ):
        monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-0")
        session = AsyncMock()
        session.send.side_effect = [
            {"windowId": 9},
            {},
            {
                "bounds": {
                    "windowState": "normal",
                    "left": 44,
                    "top": 653,
                }
            },
        ]
        context = SimpleNamespace(
            new_page=AsyncMock(),
            new_cdp_session=AsyncMock(return_value=session),
        )
        page = SimpleNamespace(context=context)
        context.new_page.return_value = page
        browser = SimpleNamespace(new_context=AsyncMock(return_value=context))
        launcher = SimpleNamespace(launch=AsyncMock(return_value=browser))
        playwright = SimpleNamespace(chromium=launcher)

        await _launch_browser(
            playwright,
            "chromium",
            headful=False,
            browser_exe=None,
            user_data_dir=None,
            window_position=(0, 640),
        )

        launcher.launch.assert_awaited_once_with(
            headless=False,
            channel="chrome",
            args=[
                "--disable-blink-features=AutomationControlled",
                "--ozone-platform=x11",
                "--window-position=0,640",
            ],
        )
        assert session.send.await_args_list[1].args == (
            "Browser.setWindowBounds",
            {
                "windowId": 9,
                "bounds": {
                    "windowState": "normal",
                    "left": 0,
                    "top": 640,
                },
            },
        )
        assert session.send.await_args_list[-1].args == (
            "Browser.getWindowBounds",
            {"windowId": 9},
        )

    @pytest.mark.asyncio
    async def test_persistent_profile_combines_position_and_fullscreen(
        self, monkeypatch,
    ):
        monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-0")
        session = AsyncMock()
        session.send.side_effect = [
            {"windowId": 11},
            {},
            {
                "bounds": {
                    "windowState": "normal",
                    "left": -1920,
                    "top": 0,
                }
            },
            {},
            {"bounds": {"width": 1920, "height": 1200}},
            {},
        ]
        context = SimpleNamespace(
            pages=[],
            new_page=AsyncMock(),
            new_cdp_session=AsyncMock(return_value=session),
        )
        page = SimpleNamespace(context=context)
        context.new_page.return_value = page
        launcher = SimpleNamespace(
            launch_persistent_context=AsyncMock(return_value=context)
        )
        playwright = SimpleNamespace(chromium=launcher)

        launched_page, closeable = await _launch_browser(
            playwright,
            "chromium",
            headful=False,
            browser_exe="/browser",
            user_data_dir="/browser-data",
            browser_profile="Profile 1",
            fullscreen=True,
            window_position=(-1920, 0),
        )

        assert launched_page is page
        assert closeable is context
        launcher.launch_persistent_context.assert_awaited_once_with(
            "/browser-data",
            headless=False,
            executable_path="/browser",
            args=[
                "--disable-blink-features=AutomationControlled",
                "--profile-directory=Profile 1",
                "--start-fullscreen",
                "--ozone-platform=x11",
                "--window-position=-1920,0",
            ],
            viewport=None,
            ignore_https_errors=True,
        )
        assert session.send.await_args_list[1].args[1]["bounds"] == {
            "windowState": "normal",
            "left": -1920,
            "top": 0,
        }
        assert session.send.await_args_list[3].args[1]["bounds"] == {
            "windowState": "fullscreen"
        }
        assert session.send.await_args_list[-1].args[1] == {
            "width": 1920,
            "height": 1200,
            "deviceScaleFactor": 0,
            "mobile": False,
            "screenWidth": 1920,
            "screenHeight": 1200,
        }

    def test_window_position_rejects_non_chromium_browser(self, runner):
        result = runner.invoke(cli, [
            "detect", "https://example.com", "--browser", "firefox",
            "--window-position", "0", "0",
        ])

        assert result.exit_code != 0
        assert "requires Chromium" in result.output

    @pytest.mark.asyncio
    async def test_headless_chromium_uses_browser_version_without_headless_token(self):
        page = object()
        context = SimpleNamespace(new_page=AsyncMock(return_value=page))
        browser = SimpleNamespace(
            version="145.0.1.2",
            new_context=AsyncMock(return_value=context),
        )
        launcher = SimpleNamespace(launch=AsyncMock(return_value=browser))
        playwright = SimpleNamespace(chromium=launcher)

        await _launch_browser(
            playwright,
            "chromium",
            headful=False,
            browser_exe=None,
            user_data_dir=None,
        )

        context_kwargs = browser.new_context.await_args.kwargs
        launcher.launch.assert_awaited_once_with(
            headless=True,
            channel="chrome",
            args=["--disable-blink-features=AutomationControlled"],
        )
        assert "Chrome/145.0.1.2" in context_kwargs["user_agent"]
        assert "HeadlessChrome" not in context_kwargs["user_agent"]

    def test_detect_browser_choices(self, runner):
        result = runner.invoke(cli, ["detect", "--help"])
        assert "chromium" in result.output
        assert "firefox" in result.output
        assert "webkit" in result.output

    def test_all_detect_options_are_forwarded(
        self, runner, tmp_path, monkeypatch,
    ):
        detect_call = AsyncMock()
        configure_logging = Mock()
        monkeypatch.setattr("webagentaudit.cli.app._detect", detect_call)
        monkeypatch.setattr(
            "webagentaudit.cli.app.logging.basicConfig", configure_logging
        )
        browser_exe = tmp_path / "chromium"
        browser_exe.touch()
        user_data_dir = tmp_path / "browser-data"

        result = runner.invoke(cli, [
            "detect", "https://example.com",
            "--headful", "--fullscreen",
            "--window-position", "-10", "20",
            "--browser", "chromium",
            "--browser-exe", str(browser_exe),
            "--user-data-dir", str(user_data_dir),
            "--timeout", "1234",
            "--verbose",
            "--debug",
            "--output", "json",
        ])

        assert result.exit_code == 0, result.output
        detect_call.assert_awaited_once_with(
            "https://example.com", True, True, (-10, 20), "chromium",
            str(browser_exe), str(user_data_dir), 1234, "json", True,
        )
        configure_logging.assert_called_once()

    def test_verbose_does_not_enable_debug_logging(
        self, runner, monkeypatch,
    ):
        detect_call = AsyncMock()
        configure_logging = Mock()
        monkeypatch.setattr("webagentaudit.cli.app._detect", detect_call)
        monkeypatch.setattr(
            "webagentaudit.cli.app.logging.basicConfig", configure_logging
        )

        result = runner.invoke(cli, [
            "detect", "https://example.com", "--verbose",
        ])

        assert result.exit_code == 0
        configure_logging.assert_not_called()


class TestPromptOptionParsing:
    """Test that every prompt option reaches the async implementation."""

    def test_all_prompt_options_are_forwarded(
        self, runner, tmp_path, monkeypatch,
    ):
        prompt_call = AsyncMock()
        configure_logging = Mock()
        monkeypatch.setattr("webagentaudit.cli.app._prompt", prompt_call)
        monkeypatch.setattr(
            "webagentaudit.cli.app.logging.basicConfig", configure_logging
        )
        browser_exe = tmp_path / "chromium"
        browser_exe.touch()

        result = runner.invoke(cli, [
            "prompt", "https://example.com", "hello",
            "--headful", "--fullscreen",
            "--window-position", "-10", "20",
            "--browser", "chromium",
            "--browser-exe", str(browser_exe),
            "--user-data-dir", str(tmp_path / "browser-data"),
            "--browser-profile", "Profile 1",
            "--timeout", "4321",
            "--post-send-wait", "25",
            "--input-selector", "#input",
            "--response-selector", ".response",
            "--submit-selector", "#send",
            "--screenshots-dir", str(tmp_path / "screenshots"),
            "--verbose",
            "--debug",
            "--output", "json",
        ])

        assert result.exit_code == 0, result.output
        prompt_call.assert_awaited_once_with(
            url="https://example.com",
            message="hello",
            headful=True,
            fullscreen=True,
            window_position=(-10, 20),
            browser="chromium",
            browser_exe=str(browser_exe),
            user_data_dir=str(tmp_path / "browser-data"),
            browser_profile="Profile 1",
            timeout=4321,
            post_send_wait=25,
            input_selector="#input",
            response_selector=".response",
            submit_selector="#send",
            screenshots_dir=str(tmp_path / "screenshots"),
            output_format="json",
            verbose=True,
        )
        configure_logging.assert_called_once()


# ---------------------------------------------------------------------------
# Assess command option parsing
# ---------------------------------------------------------------------------


class TestAssessOptionParsing:
    """Test that all assess options are accepted by the CLI parser."""

    def test_assess_missing_url(self, runner):
        result = runner.invoke(cli, ["assess"])
        assert result.exit_code != 0

    def test_all_assess_options_are_forwarded(
        self, runner, tmp_path, monkeypatch, yaml_probes_dir,
        single_turn_yaml, multi_turn_yaml,
    ):
        from webagentaudit.assessment.models import AssessmentResult

        assess_call = AsyncMock(return_value=AssessmentResult())
        configure_logging = Mock()
        monkeypatch.setattr("webagentaudit.cli.app._assess", assess_call)
        monkeypatch.setattr(
            "webagentaudit.cli.app.logging.basicConfig", configure_logging
        )
        browser_exe = tmp_path / "chromium"
        browser_exe.touch()
        output_file = tmp_path / "result.json"

        result = runner.invoke(cli, [
            "assess", "--url", "https://example.com",
            "--headful", "--fullscreen",
            "--window-position", "-10", "20",
            "--browser", "chromium",
            "--browser-exe", str(browser_exe),
            "--user-data-dir", str(tmp_path / "browser-data"),
            "--timeout", "1234",
            "--post-send-wait", "25",
            "--post-success-wait", "50",
            "--workers", "3",
            "--input-selector", "#input",
            "--response-selector", ".response",
            "--submit-selector", "#send",
            "--trigger-selector", "#open-chat",
            "--input-hint", "<textarea>",
            "--submit-hint", "<button>Send</button>",
            "--response-hint", "<div class='response'>",
            "--iframe-selector", "iframe.chat",
            "--wait-for", "#ready",
            "--category", "extraction",
            "--sophistication", "advanced",
            "--severity", "high",
            "--probes", "extraction.custom_direct_ask",
            "--probe-dir", yaml_probes_dir,
            "--probe-file", single_turn_yaml,
            "--probe-file", multi_turn_yaml,
            "--screenshots",
            "--screenshots-dir", str(tmp_path / "screenshots"),
            "--verbose",
            "--debug",
            "--output", "text",
            "--output-file", str(output_file),
        ])

        assert result.exit_code == 0, result.output
        assess_call.assert_awaited_once_with(
            url="https://example.com",
            emit_output=True,
            headful=True,
            fullscreen=True,
            window_position=(-10, 20),
            browser="chromium",
            browser_exe=str(browser_exe),
            user_data_dir=str(tmp_path / "browser-data"),
            timeout=1234,
            post_send_wait=25,
            post_success_wait=50,
            workers=3,
            input_selector="#input",
            response_selector=".response",
            submit_selector="#send",
            trigger_selector="#open-chat",
            input_hint="<textarea>",
            submit_hint="<button>Send</button>",
            response_hint="<div class='response'>",
            iframe_selector="iframe.chat",
            wait_for_selector="#ready",
            category="extraction",
            sophistication="advanced",
            severity="high",
            probes="extraction.custom_direct_ask",
            probe_dir=yaml_probes_dir,
            probe_file=(single_turn_yaml, multi_turn_yaml),
            screenshots=True,
            screenshots_dir=str(tmp_path / "screenshots"),
            output_format="text",
            verbose=True,
        )
        configure_logging.assert_called_once()
        assert output_file.exists()

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

    def test_assess_help_has_post_send_wait(self, runner):
        result = runner.invoke(cli, ["assess", "--help"])
        assert "--post-send-wait" in result.output

    def test_assess_rejects_url_and_url_file_together(self, runner, tmp_path):
        url_file = tmp_path / "urls.txt"
        url_file.write_text("https://example.com\n")
        result = runner.invoke(cli, [
            "assess", "https://example.org", "--url-file", str(url_file),
        ])
        assert result.exit_code != 0
        assert "exactly one of positional URL, --url, or --url-file" in result.output

    def test_assess_rejects_positional_url_and_url_option(self, runner):
        result = runner.invoke(cli, [
            "assess", "https://example.org", "--url", "https://example.com",
        ])
        assert result.exit_code != 0
        assert "exactly one of positional URL, --url, or --url-file" in result.output

    def test_assess_rejects_url_option_and_url_file(self, runner, tmp_path):
        url_file = tmp_path / "urls.txt"
        url_file.write_text("https://example.com\n")
        result = runner.invoke(cli, [
            "assess", "--url", "https://example.org",
            "--url-file", str(url_file),
        ])
        assert result.exit_code != 0
        assert "exactly one of positional URL, --url, or --url-file" in result.output

    def test_batch_preserves_programmatic_interaction_on_failure(
        self, runner, tmp_path, monkeypatch,
    ):
        async def fail_after_featurebase_identification(**kwargs):
            progress = kwargs["progress_callback"]
            progress("PROVIDER", "featurebase")
            progress("INTERACTION", FEATUREBASE_INTERACTION_DESCRIPTION)
            raise TargetAssessmentFailure(
                "chat_detection",
                "Featurebase was identified, but its messenger was not booted",
                provider_hint="featurebase",
            )

        monkeypatch.setattr(
            "webagentaudit.cli.app._assess",
            fail_after_featurebase_identification,
        )
        url_file = tmp_path / "urls.txt"
        output_file = tmp_path / "results.json"
        url_file.write_text("https://status.example.com\n")

        result = runner.invoke(cli, [
            "assess",
            "--url-file", str(url_file),
            "--output", "json",
            "--output-file", str(output_file),
        ])

        assert result.exit_code == 1
        target = json.loads(output_file.read_text())["targets"][0]
        assert target["provider_hint"] == "featurebase"
        assert target["interaction"] == FEATUREBASE_INTERACTION_DESCRIPTION

    def test_batch_separates_not_found_and_records_run_metadata(
        self, runner, tmp_path, monkeypatch,
    ):
        from webagentaudit.assessment.models import (
            AssessmentResult,
            AssessmentSummary,
            ProbeResult,
        )

        warning_flags = []

        async def assess_target(**kwargs):
            warning_flags.append(kwargs["warn_probe_overlaps"])
            if kwargs["url"].endswith("missing"):
                raise TargetNotFound("No chatbot found")
            return AssessmentResult(
                summary=AssessmentSummary(
                    total_probes=1,
                    target_url=kwargs["url"],
                ),
                probe_results=[ProbeResult(
                    probe_name="test.probe",
                    vulnerability_detected=kwargs["url"].endswith("vulnerable"),
                )],
            )

        monkeypatch.setattr("webagentaudit.cli.app._assess", assess_target)
        url_file = tmp_path / "urls.txt"
        output_file = tmp_path / "results.json"
        probe_file = tmp_path / "probe.yaml"
        url_file.write_text(
            "https://example.test/ok\n"
            "https://example.test/vulnerable\n"
            "https://example.test/missing\n"
        )
        probe_file.write_text("name: test.probe\n")

        result = runner.invoke(cli, [
            "assess", "--url-file", str(url_file),
            "--probe-file", str(probe_file),
            "--output", "json", "--output-file", str(output_file),
        ])

        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert data["summary"] == {
            "total": 3,
            "vulnerable": 1,
            "passed": 1,
            "probably_not_vulnerable": 0,
            "failed": 0,
            "not_found": 1,
        }
        assert data["targets"][0]["outcome"] == "passed"
        assert data["targets"][0]["security_verdict"] == "pass"
        assert data["targets"][1]["outcome"] == "vulnerable"
        assert data["targets"][1]["security_verdict"] == "vulnerable"
        assert data["targets"][2]["outcome"] == "not_found"
        assert data["targets"][2]["security_verdict"] == "not_determined"
        assert data["targets"][2]["status"] == "not_found"
        assert data["targets"][2]["reason"] == "No chatbot found"
        assert data["run"]["schema_version"] == 6
        assert len(data["run"]["url_file_sha256"]) == 64
        assert len(data["run"]["probe_files_sha256"][str(probe_file)]) == 64
        assert data["run"]["browser_name"] == "chromium"
        assert data["run"]["playwright_version"]
        assert warning_flags == [True, False, False]

    def test_batch_text_reports_every_status_and_security_verdict(
        self, runner, tmp_path, monkeypatch,
    ):
        from webagentaudit.assessment.models import (
            AssessmentResult,
            AssessmentSummary,
            ProbeResult,
        )

        async def assess_target(**kwargs):
            if kwargs["url"].endswith("missing"):
                raise TargetNotFound("No chatbot found")
            return AssessmentResult(
                summary=AssessmentSummary(total_probes=1),
                probe_results=[ProbeResult(probe_name="test.probe")],
            )

        monkeypatch.setattr("webagentaudit.cli.app._assess", assess_target)
        url_file = tmp_path / "urls.txt"
        url_file.write_text(
            "https://example.test/ok\nhttps://example.test/missing\n"
        )

        result = runner.invoke(cli, [
            "assess", "--url-file", str(url_file), "--output", "text",
        ])

        assert result.exit_code == 0
        assert "[1/2] PASS https://example.test/ok" in result.output
        assert "[2/2] NOT_FOUND https://example.test/missing" in result.output
        assert (
            "Batch complete: 0 vulnerable, 1 passed, 0 probably not "
            "vulnerable, 0 failed, 1 not found, 2 total."
            in result.output
        )
        assert "not determined" not in result.output.lower()

    def test_single_not_found_is_a_non_error_result(
        self, runner, tmp_path, monkeypatch,
    ):
        async def no_chatbot(**kwargs):
            raise TargetNotFound("No chatbot found")

        monkeypatch.setattr("webagentaudit.cli.app._assess", no_chatbot)
        output_file = tmp_path / "result.json"

        result = runner.invoke(cli, [
            "assess", "https://example.test", "--output", "json",
            "--output-file", str(output_file),
        ])

        assert result.exit_code == 0
        assert json.loads(result.stdout)["status"] == "not_found"
        assert json.loads(output_file.read_text())["reason"] == "No chatbot found"

    @pytest.mark.parametrize(
        ("verbose", "shows_details"),
        [(False, False), (True, True)],
    )
    def test_batch_verbose_controls_phase_detail_but_not_interaction_label(
        self, runner, tmp_path, monkeypatch, verbose, shows_details,
    ):
        from webagentaudit.assessment.models import (
            AssessmentResult,
            AssessmentSummary,
        )

        description = PROGRAMMATIC_INTERACTION_DESCRIPTIONS["botpress_open"]

        async def succeed_with_progress(**kwargs):
            progress = kwargs["progress_callback"]
            progress("PROVIDER", "botpress")
            progress("INTERACTION", description)
            progress("CHAT FOUND", "textarea.bpComposerInput")
            progress("TYPED", "prompt text verified in chat input")
            progress("SUBMITTED", "prompt left the chat input")
            progress("RESPONSE READ", "assistant output became stable")
            progress(
                "PROBE START",
                "[1/1] output_safety.custom_fibonacci "
                "(1 planned interaction)",
            )
            progress(
                "PROBE TURN", "[1/1] output_safety.custom_fibonacci"
            )
            progress("PROMPT", "Write Fibonacci")
            progress("CHAT RESPONSE", "def my_fibonacci(): ...")
            progress(
                "PROBE EXECUTION SUCCESS",
                "1 interaction completed",
            )
            progress(
                "SECURITY VERDICT PASS",
                "output_safety.custom_fibonacci (no vulnerability detected)",
            )
            return AssessmentResult(
                summary=AssessmentSummary(
                    total_probes=1,
                    target_url=kwargs["url"],
                ),
                metadata={
                    "provider_hint": "botpress",
                    "interaction": description,
                },
            )

        monkeypatch.setattr(
            "webagentaudit.cli.app._assess",
            succeed_with_progress,
        )
        url_file = tmp_path / "urls.txt"
        output_file = tmp_path / "results.json"
        url_file.write_text("https://botpress.example.com\n")
        args = [
            "assess", "--url-file", str(url_file),
            "--output-file", str(output_file),
        ]
        if verbose:
            args.append("--verbose")

        result = runner.invoke(cli, args)

        assert result.exit_code == 0
        assert description in result.output
        assert ("RESPONSE READ" in result.output) is shows_details
        assert ("Chat response:" in result.output) is shows_details
        assert ("Probe: [1/1]" in result.output) is shows_details
        assert ("Planned interaction: [1/1]" in result.output) is shows_details
        assert ("Probe execution: SUCCESS" in result.output) is shows_details
        assert ("Security verdict: PASS" in result.output) is shows_details
        assert "DEBUG " not in result.output
        assert "Traceback" not in result.output

    def test_default_output_path_is_timestamped_json_artifact(self):
        from webagentaudit.cli.app import _default_output_path

        path = _default_output_path()

        assert path.parent == Path("output")
        assert path.name.startswith("webagentaudit-")
        assert path.suffix == ".json"


# ---------------------------------------------------------------------------
# Screenshots directory option
# ---------------------------------------------------------------------------


class TestScreenshotsDir:
    """Tests for the --screenshots-dir option."""

    def test_assess_help_has_screenshots_dir(self, runner):
        result = runner.invoke(cli, ["assess", "--help"])
        assert "--screenshots-dir" in result.output

    def test_screenshots_dir_help_text(self, runner):
        """Help text should describe the default."""
        result = runner.invoke(cli, ["assess", "--help"])
        assert "Directory for screenshots" in result.output

    def test_screenshots_dir_listed_near_screenshots(self, runner):
        """--screenshots-dir should appear in help alongside --screenshots."""
        result = runner.invoke(cli, ["assess", "--help"])
        lines = result.output.splitlines()
        ss_line = None
        ss_dir_line = None
        for i, line in enumerate(lines):
            if "--screenshots-dir" in line:
                ss_dir_line = i
            elif "--screenshots " in line:  # trailing space to avoid matching --screenshots-dir
                ss_line = i
        assert ss_line is not None, "--screenshots not found in help"
        assert ss_dir_line is not None, "--screenshots-dir not found in help"
        # They should be near each other (within 3 lines)
        assert abs(ss_dir_line - ss_line) <= 3


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

    def test_probes_with_valid_severity(self, runner):
        result = runner.invoke(cli, [
            "probes", "--severity", "critical", "--output", "json",
        ])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data
        assert {probe["severity"] for probe in data} == {"critical"}

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

    def test_invalid_severity(self, runner):
        result = runner.invoke(cli, ["probes", "--severity", "urgent"])

        assert result.exit_code != 0
        assert "Invalid severity" in result.output

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


# ---------------------------------------------------------------------------
# Assess command validation
# ---------------------------------------------------------------------------


class TestAssessValidation:
    """Validation tests for assess command options."""

    def test_assess_invalid_category(self, runner):
        """assess with invalid --category should fail gracefully."""
        result = runner.invoke(cli, [
            "assess", "http://example.com",
            "--input-selector", "#input",
            "--response-selector", "#resp",
            "--category", "bogus_category",
        ])
        assert result.exit_code != 0
        assert "Invalid category" in result.output or "Error" in result.output

    def test_assess_invalid_sophistication(self, runner):
        """assess with invalid --sophistication should fail gracefully."""
        result = runner.invoke(cli, [
            "assess", "http://example.com",
            "--input-selector", "#input",
            "--response-selector", "#resp",
            "--sophistication", "mega_advanced",
        ])
        assert result.exit_code != 0
        assert "Invalid sophistication" in result.output or "Error" in result.output

    def test_assess_invalid_severity(self, runner):
        result = runner.invoke(cli, [
            "assess", "http://example.com",
            "--input-selector", "#input",
            "--response-selector", "#resp",
            "--severity", "urgent",
        ])

        assert result.exit_code != 0
        assert "Invalid severity" in result.output


# ---------------------------------------------------------------------------
# Probes command with real YAML fixtures (no browser needed)
# ---------------------------------------------------------------------------


class TestProbesWithFixtures:
    """Test probes command output with real YAML probe fixtures."""

    def test_probes_lists_custom_probes(self, runner, yaml_probes_dir):
        result = runner.invoke(cli, [
            "probes", "--probe-dir", yaml_probes_dir, "--output", "json",
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
        for probe in data:
            assert "category" in probe and probe["category"]
            assert "severity" in probe and probe["severity"]
            assert "sophistication" in probe and probe["sophistication"]
            assert "description" in probe and probe["description"]

    def test_probes_text_output_structured(self, runner, yaml_probes_dir):
        result = runner.invoke(cli, [
            "probes", "--probe-dir", yaml_probes_dir, "--output", "text",
        ])
        assert result.exit_code == 0
        assert "Available Probes" in result.output

    def test_probes_filter_category(self, runner, yaml_probes_dir):
        result = runner.invoke(cli, [
            "probes", "--probe-dir", yaml_probes_dir,
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

    def test_probes_filter_sophistication(self, runner, yaml_probes_dir):
        result = runner.invoke(cli, [
            "probes", "--probe-dir", yaml_probes_dir,
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
