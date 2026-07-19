"""webagentaudit CLI — detect and assess interactive LLMs on webpages."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import subprocess
import sys
import time
from collections import Counter
from collections.abc import Callable
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urlparse

import click

from webagentaudit.core.consts import VERSION
from webagentaudit.core.enums import ProbeCategory, Severity, Sophistication
from webagentaudit.llm_channel.browser import goto_and_inspect

from .consts import (
    PAGE_DATA_COLLECTION_TIMEOUT_MS,
    PAGE_DATA_MAX_ATTEMPTS,
    PAGE_DATA_RETRY_WAIT_MS,
    PAGE_DATA_TRANSIENT_ERROR_FRAGMENTS,
    PROVIDER_DETECTION_MAX_ATTEMPTS,
    PROVIDER_DETECTION_POLL_MS,
)

if TYPE_CHECKING:
    from webagentaudit.llm_channel.models import InteractionPlan


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_csv(value: str | None) -> list[str]:
    """Split comma-separated string into list, stripping whitespace."""
    if not value:
        return []
    return [v.strip() for v in value.split(",") if v.strip()]


def _style(text: str, **kwargs) -> str:
    return click.style(text, **kwargs)


def _print_header(text: str) -> None:
    click.echo()
    click.echo(_style(f"{'=' * 60}", fg="cyan"))
    click.echo(_style(f"  {text}", fg="cyan", bold=True))
    click.echo(_style(f"{'=' * 60}", fg="cyan"))


def _print_section(text: str) -> None:
    click.echo()
    click.echo(_style(f"--- {text} ---", fg="yellow", bold=True))


def _print_kv(key: str, value: str, indent: int = 2) -> None:
    prefix = " " * indent
    click.echo(f"{prefix}{_style(key + ':', bold=True)} {value}")


def _print_progress(
    phase: str, detail: str, *, prefix: str = "", err: bool = False
) -> None:
    """Print clean operator-facing progress without logger diagnostics."""
    if phase in {"PROMPT", "CHAT RESPONSE"}:
        label = "Prompt" if phase == "PROMPT" else "Chat response"
        click.echo(f"{prefix}{label}:", err=err)
        for line in detail.splitlines() or [""]:
            click.echo(f"  {line}", err=err)
        return
    if phase == "PROBE START":
        click.echo(f"{prefix}Probe: {detail}", err=err)
        return
    if phase == "PROBE TURN":
        click.echo(f"{prefix}Planned interaction: {detail}", err=err)
        return
    if phase.startswith("PROBE EXECUTION "):
        status = phase.removeprefix("PROBE EXECUTION ")
        click.echo(f"{prefix}Probe execution: {status} — {detail}", err=err)
        return
    if phase.startswith("SECURITY VERDICT "):
        status = phase.removeprefix("SECURITY VERDICT ")
        click.echo(f"{prefix}Security verdict: {status} — {detail}", err=err)
        return
    if phase == "PROVIDER":
        click.echo(f"{prefix}Detected provider: {detail}", err=err)
        return
    if phase == "INTERACTION":
        click.echo(f"{prefix}Interaction method: {detail}", err=err)
        return
    click.echo(f"{prefix}{phase:<13} {detail}", err=err)


def _emit_probe_progress(probe_result, callback: Callable[[str, str], None]) -> None:
    """Emit the readable evidence already captured in a completed probe result."""
    for exchange in probe_result.exchanges:
        if exchange.prompt:
            callback("PROMPT", exchange.prompt)
        if exchange.response:
            callback("CHAT RESPONSE", exchange.response)
    completed = len(probe_result.exchanges)
    noun = "interaction" if completed == 1 else "interactions"
    if probe_result.error_count:
        error = probe_result.errors[0]
        callback(
            "PROBE EXECUTION ERROR",
            f"{completed} {noun} completed; {probe_result.probe_name} "
            f"[{error.phase}] {error.message}",
        )
    else:
        callback(
            "PROBE EXECUTION SUCCESS",
            f"{completed} {noun} completed",
        )

    if probe_result.security_verdict == "vulnerable":
        matched = (
            f"; matched: {', '.join(probe_result.matched_patterns)}"
            if probe_result.matched_patterns else ""
        )
        callback(
            "SECURITY VERDICT VULNERABLE",
            f"{probe_result.probe_name}{matched}",
        )
    elif probe_result.security_verdict == "probably_not_vulnerable":
        callback(
            "SECURITY VERDICT PROBABLY NOT VULNERABLE",
            f"{probe_result.probe_name} "
            "(submitted; detector pattern not observed)",
        )
    elif probe_result.security_verdict == "not_determined":
        callback(
            "SECURITY VERDICT NOT DETERMINED",
            f"{probe_result.probe_name} (execution error)",
        )
    else:
        callback(
            "SECURITY VERDICT PASS",
            f"{probe_result.probe_name} (no vulnerability detected)",
        )


def _severity_color(severity: str) -> str:
    return {"critical": "red", "high": "red", "medium": "yellow",
            "low": "blue", "info": "white"}.get(severity, "white")


BROWSER_CHOICES = ["chromium", "firefox", "webkit"]


def _validate_window_position(
    browser: str, position: tuple[int, int] | None
) -> None:
    if position and browser != "chromium":
        raise click.UsageError("--window-position currently requires Chromium.")


def _interaction_description(
    *,
    provider_hint: str | None = None,
    plan: InteractionPlan | None = None,
) -> str | None:
    """Describe provider API interaction that is not launcher-discoverable."""
    from webagentaudit.llm_channel.auto_config.consts import (
        FEATUREBASE_INTERACTION_DESCRIPTION,
        PROGRAMMATIC_INTERACTION_DESCRIPTIONS,
    )

    if plan:
        for action in plan.setup_actions:
            if description := PROGRAMMATIC_INTERACTION_DESCRIPTIONS.get(action.kind):
                return description
    if provider_hint == "featurebase":
        return FEATUREBASE_INTERACTION_DESCRIPTION
    return None


class TargetAssessmentFailure(click.ClickException):
    """A target-level failure with a stable machine-readable phase."""

    def __init__(
        self,
        phase: str,
        message: str,
        provider_hint: str | None = None,
    ) -> None:
        super().__init__(message)
        self.phase = phase
        self.provider_hint = provider_hint


class TargetNotFound(click.ClickException):
    """A target without provider evidence or a usable chat input."""


class PageDataCollectionError(RuntimeError):
    """The live document never stabilized enough for provider detection."""


# ---------------------------------------------------------------------------
# CLI group
# ---------------------------------------------------------------------------

@click.group()
@click.version_option(version=VERSION, prog_name="webagentaudit")
def cli() -> None:
    """webagentaudit — detect and assess interactive LLMs on webpages."""


# ---------------------------------------------------------------------------
# detect command
# ---------------------------------------------------------------------------

@cli.command()
@click.argument("url")
@click.option("--headful", is_flag=True, help="Run browser in headed mode.")
@click.option("--fullscreen", is_flag=True,
              help="Run a headed browser in full-screen mode.")
@click.option("--window-position", type=(int, int), metavar="X Y",
              help="Place the headed Chromium window at screen coordinates X Y.")
@click.option("--browser", type=click.Choice(BROWSER_CHOICES), default="chromium",
              help="Browser engine to use.")
@click.option("--browser-exe", type=click.Path(exists=True), default=None,
              help="Path to browser executable.")
@click.option("--user-data-dir", type=click.Path(), default=None,
              help="Browser profile directory for authenticated sessions.")
@click.option("--timeout", default=30000, type=int, help="Navigation timeout in ms.")
@click.option("-v", "--verbose", is_flag=True,
              help="Show detailed operator-facing progress.")
@click.option("--debug", is_flag=True, help="Enable developer debug logging.")
@click.option("--output", "output_format", type=click.Choice(["text", "json"]),
              default="text", help="Output format.")
def detect(url: str, headful: bool, fullscreen: bool,
           window_position: tuple[int, int] | None, browser: str,
           browser_exe: str | None,
           user_data_dir: str | None, timeout: int, verbose: bool, debug: bool,
           output_format: str) -> None:
    """Detect interactive LLMs on a webpage."""
    _validate_window_position(browser, window_position)
    if debug:
        logging.basicConfig(level=logging.DEBUG,
                            format="%(levelname)-5s %(name)s: %(message)s")
    asyncio.run(_detect(
        url, headful, fullscreen, window_position, browser, browser_exe,
        user_data_dir, timeout, output_format, verbose,
    ))


async def _collect_page_data(
    page,
    url: str,
    *,
    timeout_ms: int = PAGE_DATA_COLLECTION_TIMEOUT_MS,
):
    """Collect one coherent PageData snapshot, retrying active navigation."""
    from playwright.async_api import (
        Error as PlaywrightError,
        TimeoutError as PlaywrightTimeoutError,
    )

    from webagentaudit.detection.models import PageData

    deadline = time.monotonic() + max(timeout_ms, 0) / 1000
    last_error: PlaywrightError | None = None
    for attempt in range(PAGE_DATA_MAX_ATTEMPTS):
        try:
            snapshot = await page.evaluate("""() => {
                const metaTags = {};
                document.querySelectorAll('meta[name], meta[property]').forEach(
                    element => {
                        const key = element.getAttribute('name')
                            || element.getAttribute('property');
                        metaTags[key] = element.getAttribute('content') || '';
                    }
                );
                return {
                    html: document.documentElement
                        ? document.documentElement.outerHTML : '',
                    scripts: Array.from(document.querySelectorAll('script[src]'))
                        .map(element => element.src),
                    inline_scripts: Array.from(
                        document.querySelectorAll('script:not([src])')
                    ).map(element => element.textContent || '')
                        .filter(text => text.trim().length > 0),
                    stylesheets: Array.from(
                        document.querySelectorAll('link[rel="stylesheet"]')
                    ).map(element => element.href),
                    meta_tags: metaTags,
                    iframes: Array.from(document.querySelectorAll('iframe'))
                        .map(element => element.src).filter(Boolean),
                };
            }""")
            return PageData(url=url, **snapshot)
        except PlaywrightError as exc:
            message = str(exc).lower()
            if not any(
                fragment in message
                for fragment in PAGE_DATA_TRANSIENT_ERROR_FRAGMENTS
            ):
                raise
            last_error = exc
            remaining_ms = int((deadline - time.monotonic()) * 1000)
            if attempt == PAGE_DATA_MAX_ATTEMPTS - 1 or remaining_ms <= 0:
                break
            try:
                await page.wait_for_load_state(
                    "domcontentloaded", timeout=max(1, remaining_ms)
                )
            except PlaywrightTimeoutError:
                break
            remaining_ms = int((deadline - time.monotonic()) * 1000)
            if remaining_ms <= 0:
                break
            await page.wait_for_timeout(
                min(PAGE_DATA_RETRY_WAIT_MS, remaining_ms)
            )

    detail = str(last_error).split("\n")[0] if last_error else "navigation"
    raise PageDataCollectionError(
        f"Page did not stabilize while collecting detection data for {url}: "
        f"{detail}"
    ) from last_error


async def _detection_result_for_page(
    page,
    url: str,
    *,
    timeout_ms: int = PAGE_DATA_COLLECTION_TIMEOUT_MS,
):
    """Detect provider and interaction readiness on an open live page."""
    page_data = await _collect_page_data(page, url, timeout_ms=timeout_ms)
    return _create_detector().detect(page_data)


def _create_detector():
    """Create an LlmDetector with all deterministic checkers registered."""
    from webagentaudit.detection.detector import LlmDetector
    from webagentaudit.detection.deterministic.ai_indicators import AiIndicatorChecker
    from webagentaudit.detection.deterministic.dom_patterns import DomPatternChecker
    from webagentaudit.detection.deterministic.known_signatures import KnownSignatureChecker
    from webagentaudit.detection.deterministic.network_hints import NetworkHintsChecker
    from webagentaudit.detection.deterministic.script_analysis import ScriptAnalysisChecker
    from webagentaudit.detection.deterministic.selector_matching import SelectorMatchingChecker
    from webagentaudit.detection.known_assets.checker import KnownAssetsChecker

    detector = LlmDetector()
    detector.register_checker(DomPatternChecker())
    detector.register_checker(SelectorMatchingChecker())
    detector.register_checker(KnownSignatureChecker())
    detector.register_checker(ScriptAnalysisChecker())
    detector.register_checker(AiIndicatorChecker())
    detector.register_checker(NetworkHintsChecker())
    detector.register_checker(KnownAssetsChecker())
    return detector


async def _launch_browser(pw, browser: str, headful: bool,
                          browser_exe: str | None,
                          user_data_dir: str | None,
                          browser_profile: str | None = None,
                          fullscreen: bool = False,
                          window_position: tuple[int, int] | None = None):
    """Launch a Playwright browser, returning (page, closeable).

    *closeable* is the object to ``await close()`` when done — either
    a BrowserContext (persistent) or a Browser instance.
    """
    from webagentaudit.llm_channel.browser import (
        apply_window_geometry,
        browser_launch_options,
        effective_user_agent,
        window_position_launch_args,
    )

    launcher = getattr(pw, browser)
    headless = not (headful or fullscreen or window_position)
    launch_kw: dict = {"headless": headless}
    if browser_exe:
        launch_kw["executable_path"] = browser_exe
    launch_args = []
    if browser_profile:
        launch_args.append(f"--profile-directory={browser_profile}")
    if fullscreen:
        launch_args.append("--start-fullscreen")
    launch_args.extend(window_position_launch_args(window_position))
    launch_kw.update(browser_launch_options(
        browser, browser_exe, launch_args
    ))

    viewport = None if fullscreen else {"width": 1280, "height": 720}

    if user_data_dir:
        user_agent = effective_user_agent(browser, headless=headless)
        context_kw = {
            "viewport": viewport,
            "ignore_https_errors": True,
        }
        if user_agent:
            context_kw["user_agent"] = user_agent
        ctx = await launcher.launch_persistent_context(
            user_data_dir, **launch_kw, **context_kw,
        )
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        await apply_window_geometry(
            page, browser=browser, fullscreen=fullscreen,
            position=window_position,
        )
        return page, ctx
    else:
        br = await launcher.launch(**launch_kw)
        user_agent = effective_user_agent(
            browser,
            headless=headless,
            browser_version=getattr(br, "version", None),
        )
        context_kw = {
            "viewport": viewport,
            "ignore_https_errors": True,
        }
        if user_agent:
            context_kw["user_agent"] = user_agent
        ctx = await br.new_context(
            **context_kw,
        )
        page = await ctx.new_page()
        await apply_window_geometry(
            page, browser=browser, fullscreen=fullscreen,
            position=window_position,
        )
        return page, br


async def _detect(url: str, headful: bool, fullscreen: bool,
                  window_position: tuple[int, int] | None, browser: str,
                  browser_exe: str | None, user_data_dir: str | None,
                  timeout: int, output_format: str, verbose: bool = False) -> None:
    from playwright.async_api import async_playwright

    is_json = output_format == "json"

    click.echo(f"Opening {_style(browser, bold=True)} browser...", err=is_json)

    async with async_playwright() as pw:
        page, closeable = await _launch_browser(
            pw, browser, headful, browser_exe, user_data_dir,
            fullscreen=fullscreen, window_position=window_position)

        click.echo(f"Navigating to {_style(url, fg='cyan')}...", err=is_json)
        try:
            await goto_and_inspect(page, url, timeout)
        except Exception as exc:
            await closeable.close()
            msg = str(exc).split("\n")[0]
            click.echo(_style(f"Error: Could not load {url}: {msg}",
                              fg="red"), err=True)
            sys.exit(1)
        await page.wait_for_timeout(3000)
        try:
            page_data = await _collect_page_data(
                page,
                url,
                timeout_ms=min(timeout, PAGE_DATA_COLLECTION_TIMEOUT_MS),
            )
        except PageDataCollectionError as exc:
            await closeable.close()
            click.echo(_style(f"Error: {exc}", fg="red"), err=True)
            raise click.exceptions.Exit(1) from exc
        await closeable.close()

    if verbose:
        click.echo(
            "Collected page data: "
            f"{len(page_data.scripts)} scripts, "
            f"{len(page_data.iframes)} iframes.",
            err=is_json,
        )

    click.echo("Running detection...", err=is_json)
    detector = _create_detector()
    result = detector.detect(page_data)

    if output_format == "json":
        click.echo(result.model_dump_json(indent=2))
        return

    # Text output
    _print_header("Detection Result")

    detected_str = (
        _style("YES", fg="green", bold=True) if result.llm_detected
        else _style("NO", fg="red", bold=True)
    )
    _print_kv("LLM Detected", detected_str)
    _print_kv("Confidence",
              f"{result.overall_confidence.value:.0%}"
              f" ({result.overall_confidence.level.value})")
    _print_kv("Signals Found", str(len(result.signals)))

    if result.provider_hint:
        _print_kv("Provider", result.provider_hint)

    if result.signals:
        _print_section("Signals")
        for s in sorted(result.signals,
                        key=lambda s: s.confidence.value, reverse=True):
            color = ("green" if s.confidence.value >= 0.7
                     else "yellow" if s.confidence.value >= 0.4
                     else "white")
            click.echo(
                f"  {_style('*', fg=color)} [{s.checker_name}] {s.signal_type}"
                f" (conf: {s.confidence.value:.0%}) — {s.description}"
            )
            if s.evidence:
                click.echo(f"    {s.evidence[:120]}")

    if result.interaction_hint:
        _print_section("Interaction Hints")
        for key, val in result.interaction_hint.items():
            _print_kv(key, str(val), indent=4)

    click.echo()


# ---------------------------------------------------------------------------
# prompt command
# ---------------------------------------------------------------------------

@cli.command()
@click.argument("url")
@click.argument("message")
@click.option("--headful", is_flag=True, help="Run browser in headed mode.")
@click.option("--fullscreen", is_flag=True,
              help="Run a headed browser in full-screen mode.")
@click.option("--window-position", type=(int, int), metavar="X Y",
              help="Place the headed Chromium window at screen coordinates X Y.")
@click.option("--browser", type=click.Choice(BROWSER_CHOICES), default="chromium",
              help="Browser engine to use.")
@click.option("--browser-exe", type=click.Path(exists=True), default=None,
              help="Path to browser executable.")
@click.option("--user-data-dir", type=click.Path(), default=None,
              help="Browser user-data root for authenticated sessions.")
@click.option("--browser-profile", type=str, default=None,
              help="Named profile within --user-data-dir, such as 'Profile 1'.")
@click.option("--timeout", type=int, default=120000,
              help="Response timeout in ms.")
@click.option("--post-send-wait", type=click.IntRange(min=0), default=60000,
              help="Wait this many ms after sending before reading the response.")
@click.option("--input-selector", type=str, help="CSS selector for input element.")
@click.option("--response-selector", type=str,
              help="CSS selector for response container.")
@click.option("--submit-selector", type=str, help="CSS selector for submit button.")
@click.option("--screenshots-dir", type=click.Path(), default=None,
              help="Save discovery and post-send screenshots in this directory.")
@click.option("-v", "--verbose", is_flag=True,
              help="Show detailed operator-facing progress.")
@click.option("--debug", is_flag=True, help="Enable developer debug logging.")
@click.option("--output", "output_format", type=click.Choice(["text", "json"]),
              default="text", help="Output format.")
def prompt(
    url: str, message: str, headful: bool, fullscreen: bool,
    window_position: tuple[int, int] | None, browser: str,
    browser_exe: str | None, user_data_dir: str | None,
    browser_profile: str | None, timeout: int, post_send_wait: int,
    input_selector: str | None, response_selector: str | None,
    submit_selector: str | None, screenshots_dir: str | None,
    verbose: bool, debug: bool, output_format: str,
) -> None:
    """Send one MESSAGE to a web-based LLM and return its response."""
    _validate_window_position(browser, window_position)
    if debug:
        logging.basicConfig(level=logging.DEBUG,
                            format="%(levelname)-5s %(name)s: %(message)s")
    asyncio.run(_prompt(
        url=url, message=message, headful=headful, fullscreen=fullscreen,
        window_position=window_position,
        browser=browser,
        browser_exe=browser_exe, user_data_dir=user_data_dir,
        browser_profile=browser_profile, timeout=timeout,
        post_send_wait=post_send_wait, input_selector=input_selector,
        response_selector=response_selector, submit_selector=submit_selector,
        screenshots_dir=screenshots_dir, output_format=output_format,
        verbose=verbose,
    ))


async def _prompt(
    *, url: str, message: str, headful: bool, fullscreen: bool, browser: str,
    window_position: tuple[int, int] | None,
    browser_exe: str | None, user_data_dir: str | None,
    browser_profile: str | None, timeout: int, post_send_wait: int,
    input_selector: str | None, response_selector: str | None,
    submit_selector: str | None, screenshots_dir: str | None,
    output_format: str, verbose: bool = False,
) -> None:
    from playwright.async_api import async_playwright

    from webagentaudit.llm_channel.config import ChannelConfig
    from webagentaudit.llm_channel.consts import (
        DEFAULT_RESPONSE_SELECTORS_BY_HOST,
        DEFAULT_RESPONSE_SELECTORS_BY_PROVIDER,
    )
    from webagentaudit.llm_channel.models import ChannelMessage, InteractionPlan
    from webagentaudit.llm_channel.playwright_channel import PlaywrightChannel
    from webagentaudit.llm_channel.strategies.custom import CustomStrategy

    plan: InteractionPlan | None = None
    discovered_page = None
    discovered_closeable = None
    provider_hint = None
    pw = None
    is_json = output_format == "json"
    progress_callback = (
        lambda phase, detail: _print_progress(
            phase, detail, prefix="  ", err=is_json
        )
        if verbose else None
    )

    if not input_selector:
        pw = await async_playwright().start()
        try:
            (
                plan,
                discovered_page,
                discovered_closeable,
                provider_hint,
            ) = await _open_and_auto_discover(
                url, pw=pw, browser=browser, headful=headful,
                browser_exe=browser_exe, user_data_dir=user_data_dir,
                browser_profile=browser_profile,
                fullscreen=fullscreen, window_position=window_position,
                timeout=timeout, wait_for_selector=None,
                input_hint=None, submit_hint=None, response_hint=None,
                screenshots=bool(screenshots_dir), screenshots_dir=screenshots_dir,
                output_format=output_format, skip_response=True,
                progress_callback=progress_callback,
            )
        except BaseException:
            await pw.stop()
            raise
        if provider_hint:
            click.echo(
                f"  Identified provider: {_style(provider_hint, fg='green')}",
                err=output_format == "json",
            )
    if plan is None and input_selector:
        plan = InteractionPlan(
            input_selector=input_selector,
            submit_selector=submit_selector,
        )
    if plan is None:
        if discovered_closeable:
            await discovered_closeable.close()
        if pw:
            await pw.stop()
        raise click.ClickException(
            "Could not find an input element. Use --input-selector."
        )

    interaction = _interaction_description(
        provider_hint=provider_hint,
        plan=plan,
    )
    host = (urlparse(url).hostname or "").removeprefix("www.")
    plan = plan.model_copy(update={
        "submit_selector": submit_selector or plan.submit_selector,
        "response_selector": (
            response_selector
            or DEFAULT_RESPONSE_SELECTORS_BY_HOST.get(host)
            or DEFAULT_RESPONSE_SELECTORS_BY_PROVIDER.get(provider_hint or "")
            or plan.response_selector
        ),
    })
    config = ChannelConfig(
        headless=not (headful or fullscreen or window_position),
        fullscreen=fullscreen,
        window_position=window_position,
        browser=browser,
        timeout_ms=timeout,
        post_send_wait_ms=post_send_wait,
        post_send_screenshot_dir=screenshots_dir,
        user_data_dir=user_data_dir,
        executable_path=browser_exe,
        browser_profile=browser_profile,
    )
    active_plan = (
        plan.model_copy(update={"setup_actions": []})
        if discovered_page else plan
    )
    strategy = CustomStrategy(
        plan=active_plan,
        progress_callback=progress_callback,
    )
    channel = PlaywrightChannel(
        config=config,
        strategy=strategy,
        page=discovered_page,
    )
    try:
        await channel.connect(url)
        response = await channel.send(ChannelMessage(text=message))
    finally:
        await channel.disconnect()
        if discovered_closeable:
            await discovered_closeable.close()
        if pw:
            await pw.stop()

    if provider_hint or interaction:
        response = response.model_copy(update={
            "metadata": {
                **response.metadata,
                **({"provider_hint": provider_hint} if provider_hint else {}),
                **({"interaction": interaction} if interaction else {}),
            }
        })

    if output_format == "json":
        click.echo(response.model_dump_json(indent=2))
        return

    _print_header("Prompt Result")
    _print_kv("URL", url)
    _print_kv("Response Time", f"{response.response_time_ms / 1000:.1f}s")
    _print_kv("Images", response.metadata.get("image_count", "0"))
    if interaction:
        _print_kv("Interaction", interaction)
    if response.text:
        _print_section("Response")
        click.echo(response.text[:2000])
    click.echo()


# ---------------------------------------------------------------------------
# assess command
# ---------------------------------------------------------------------------

@cli.command()
@click.argument("url", required=False)
@click.option("--url", "url_option", metavar="URL",
              help="URL to assess; cannot be combined with positional URL "
                   "or --url-file.")
@click.option("--url-file", type=click.Path(exists=True, dir_okay=False,
              path_type=Path), help="Read target URLs from a file, one per line.")
@click.option("--headful", is_flag=True, help="Run browser in headed mode.")
@click.option("--fullscreen", is_flag=True,
              help="Run a headed browser in full-screen mode.")
@click.option("--window-position", type=(int, int), metavar="X Y",
              help="Place the headed Chromium window at screen coordinates X Y.")
@click.option("--browser", type=click.Choice(BROWSER_CHOICES), default="chromium",
              help="Browser engine to use.")
@click.option("--browser-exe", type=click.Path(exists=True), default=None,
              help="Path to browser executable.")
@click.option("--user-data-dir", type=click.Path(), default=None,
              help="Browser profile directory for authenticated sessions.")
@click.option("--timeout", type=int, default=30000, help="Timeout in ms.")
@click.option("--post-send-wait", type=click.IntRange(min=0), default=0,
              help="Wait this many ms after sending before reading a response.")
@click.option("--post-success-wait", type=click.IntRange(min=0), default=0,
              help="Keep the browser open this many ms after reading a response.")
@click.option("--workers", default=1, type=int, help="Concurrent probe workers.")
@click.option("--input-selector", type=str, help="CSS selector for input element.")
@click.option("--response-selector", type=str,
              help="CSS selector for response container.")
@click.option("--submit-selector", type=str, help="CSS selector for submit button.")
@click.option("--trigger-selector", type=str, help="CSS selector for a chat launcher.")
@click.option("--input-hint", type=str,
              help="HTML snippet hint for input element (fuzzy matching).")
@click.option("--submit-hint", type=str,
              help="HTML snippet hint for submit button (fuzzy matching).")
@click.option("--response-hint", type=str,
              help="HTML snippet hint for response element (fuzzy matching).")
@click.option("--iframe-selector", type=str,
              help="CSS selector for the iframe containing the chat widget.")
@click.option("--wait-for", "wait_for_selector", type=str,
              help="CSS selector to wait for before interacting.")
@click.option("--category", type=str,
              help="Comma-separated probe categories to run.")
@click.option("--sophistication", type=str,
              help="Comma-separated sophistication levels.")
@click.option("--severity", type=str,
              help="Comma-separated severity levels to run (critical,high,medium,low,info).")
@click.option("--probes", type=str, help="Comma-separated probe names to run.")
@click.option("--probe-dir", type=click.Path(exists=True, file_okay=False),
              help="Directory of custom YAML probes.")
@click.option("--probe-file", type=click.Path(exists=True, dir_okay=False),
              multiple=True, help="Single custom YAML probe file.")
@click.option("--screenshots", is_flag=True,
              help="Save discovery and post-send screenshots.")
@click.option("--screenshots-dir", type=click.Path(), default=None,
              help="Directory for screenshots (default: ./screenshots).")
@click.option("-v", "--verbose", is_flag=True,
              help="Show probe/turn progress, responses, execution, and verdicts.")
@click.option("--debug", is_flag=True, help="Enable developer debug logging.")
@click.option("--output", "output_format", type=click.Choice(["text", "json"]),
              default="text", help="Output format.")
@click.option("--output-file", type=click.Path(dir_okay=False, path_type=Path),
              help="Write complete JSON results here (default: timestamped artifact).")
def assess(
    url: str | None, url_option: str | None, url_file: Path | None,
    headful: bool, fullscreen: bool,
    window_position: tuple[int, int] | None,
    browser: str,
    browser_exe: str | None, user_data_dir: str | None, timeout: int,
    post_send_wait: int, post_success_wait: int, workers: int,
    input_selector: str | None, response_selector: str | None,
    submit_selector: str | None, trigger_selector: str | None, input_hint: str | None,
    submit_hint: str | None, response_hint: str | None,
    iframe_selector: str | None, wait_for_selector: str | None,
    category: str | None, sophistication: str | None,
    severity: str | None, probes: str | None,
    probe_dir: str | None, probe_file: tuple[str, ...], screenshots: bool,
    screenshots_dir: str | None, verbose: bool, debug: bool, output_format: str,
    output_file: Path | None,
) -> None:
    """Assess AI agent security on a webpage.

    Provide exactly one of positional URL, --url, or --url-file.
    Auto-discovers chat elements when selectors are not provided.
    Use --input-selector, --response-selector to override.
    """
    _validate_window_position(browser, window_position)
    if debug:
        logging.basicConfig(level=logging.DEBUG,
                            format="%(levelname)-5s %(name)s: %(message)s")
    if sum(value is not None for value in (url, url_option, url_file)) != 1:
        raise click.UsageError(
            "Provide exactly one of positional URL, --url, or --url-file."
        )
    url = url or url_option
    output_file = output_file or _default_output_path()

    assess_kwargs = dict(
        headful=headful, fullscreen=fullscreen,
        window_position=window_position, browser=browser,
        browser_exe=browser_exe,
        user_data_dir=user_data_dir, timeout=timeout, post_send_wait=post_send_wait,
        post_success_wait=post_success_wait, workers=workers,
        input_selector=input_selector, response_selector=response_selector,
        submit_selector=submit_selector, trigger_selector=trigger_selector,
        input_hint=input_hint,
        submit_hint=submit_hint, response_hint=response_hint,
        iframe_selector=iframe_selector,
        wait_for_selector=wait_for_selector,
        category=category, sophistication=sophistication,
        severity=severity, probes=probes,
        probe_dir=probe_dir, probe_file=probe_file,
        screenshots=screenshots, screenshots_dir=screenshots_dir,
        output_format=output_format, verbose=verbose,
    )
    if url_file is not None:
        failed = asyncio.run(_assess_file(
            url_file=url_file,
            assess_kwargs=assess_kwargs,
            output_format=output_format,
            output_file=output_file,
        ))
        if failed:
            raise click.exceptions.Exit(1)
        return

    started_at = time.monotonic()
    try:
        result = asyncio.run(_assess(
            url=url,
            emit_output=output_format != "json",
            **assess_kwargs,
        ))
    except TargetNotFound as exc:
        from webagentaudit.cli.models import BatchTargetResult

        target = BatchTargetResult(
            url=url,
            status="not_found",
            reason=exc.message,
            duration_ms=(time.monotonic() - started_at) * 1000,
        )
        if output_file:
            _write_json_output(output_file, target)
        if output_format == "json":
            click.echo(target.model_dump_json(indent=2))
        else:
            click.echo(f"NONE {url}: {exc.message}")
            if output_file:
                click.echo(f"Wrote complete JSON results to {output_file}")
        return
    if output_file:
        result = result.model_copy(update={
            "metadata": {
                **result.metadata,
                "output_file": str(output_file),
            }
        })
        _write_json_output(output_file, result)
    if output_format == "json":
        click.echo(result.model_dump_json(indent=2))
    elif output_file:
        click.echo(f"Wrote complete JSON results to {output_file}")


def _load_registry(
    *,
    probe_dir: str | None,
    probe_file: tuple[str, ...],
    category: str | None,
    sophistication: str | None,
    severity: str | None = None,
    probes: str | None,
    emit_output: bool = True,
):
    """Load probes into a registry and apply filters."""
    from webagentaudit.assessment.probes.registry import ProbeRegistry

    registry = ProbeRegistry.default()
    if probe_dir:
        loaded = registry.load_yaml_dir(Path(probe_dir))
        if emit_output:
            click.echo(f"Loaded {loaded} custom probe(s) from {probe_dir}")
    for pf in probe_file:
        registry.load_yaml_file(Path(pf))
        if emit_output:
            click.echo(f"Loaded custom probe from {pf}")

    filter_kwargs: dict = {}
    if category:
        try:
            filter_kwargs["categories"] = [
                ProbeCategory(c.strip()) for c in category.split(",")
            ]
        except ValueError as e:
            valid = ", ".join(v.value for v in ProbeCategory)
            raise click.BadParameter(f"Invalid category. Valid: {valid}") from e
    if sophistication:
        try:
            filter_kwargs["sophistication_levels"] = [
                Sophistication(s.strip()) for s in sophistication.split(",")
            ]
        except ValueError as e:
            valid = ", ".join(v.value for v in Sophistication)
            raise click.BadParameter(f"Invalid sophistication. Valid: {valid}") from e
    if severity:
        try:
            filter_kwargs["severities"] = [
                Severity(s.strip()) for s in severity.split(",")
            ]
        except ValueError as e:
            valid = ", ".join(v.value for v in Severity)
            raise click.BadParameter(f"Invalid severity. Valid: {valid}") from e
    if probes:
        filter_kwargs["names"] = [n.strip() for n in probes.split(",")]

    if filter_kwargs:
        filtered = registry.filter(**filter_kwargs)
        new_reg = ProbeRegistry()
        for p in filtered:
            new_reg.register(p)
        return new_reg

    return registry


def _warn_probe_prompt_overlaps(registry) -> None:
    """Warn once per probe whose detector can match its own sent prompt."""
    from webagentaudit.assessment.validation import find_prompt_pattern_overlaps

    for probe in registry.get_all():
        overlaps = find_prompt_pattern_overlaps(probe)
        if not overlaps:
            continue
        patterns = sorted({
            pattern for overlap in overlaps for pattern in overlap.patterns
        })
        click.echo(
            f"Warning: probe '{probe.name}' is not echo-safe: "
            f"{len(overlaps)} detection-active prompt(s) match detector "
            f"pattern(s) {patterns!r}. Prompt echoes can create ambiguous "
            "evidence; prefer expected output that is absent from the input.",
            err=True,
        )


async def _open_and_auto_discover(
    url: str, *, pw, browser: str, headful: bool,
    browser_exe: str | None, user_data_dir: str | None,
    timeout: int, wait_for_selector: str | None,
    input_hint: str | None, submit_hint: str | None,
    response_hint: str | None, screenshots: bool,
    screenshots_dir: str | None = None, output_format: str = "text",
    skip_response: bool = False,
    browser_profile: str | None = None,
    fullscreen: bool = False,
    window_position: tuple[int, int] | None = None,
    emit_output: bool = True,
    progress_callback: Callable[[str, str], None] | None = None,
) -> "tuple[InteractionPlan | None, object, object, str | None]":
    """Discover a chat plan and leave its live browser page open."""
    from webagentaudit.core.exceptions import (
        ChannelNotReadyError,
        ChannelResponseError,
        ChannelSubmissionError,
    )
    from webagentaudit.llm_channel.auto_config import (
        AlgorithmicAutoConfigurator,
        BotpressAutoConfigurator,
        ChatbaseAutoConfigurator,
        ChatbotComAutoConfigurator,
        DenserAutoConfigurator,
        FeaturebaseAutoConfigurator,
        FlyweightAutoConfigurator,
        IntercomAutoConfigurator,
        LiveChatAutoConfigurator,
        TidioAutoConfigurator,
        VoiceflowAutoConfigurator,
    )
    from webagentaudit.llm_channel.auto_config._hint_matcher import parse_hint
    is_json = output_format == "json"

    if emit_output:
        click.echo(
            f"  Auto-discovering chat elements on {_style(url, fg='cyan')}...",
            err=is_json,
        )

    page, closeable = await _launch_browser(
        pw, browser, headful, browser_exe, user_data_dir, browser_profile,
        fullscreen=fullscreen, window_position=window_position)

    try:
        try:
            await goto_and_inspect(page, url, timeout)
        except Exception as exc:
            msg = str(exc).split("\n")[0]
            raise TargetAssessmentFailure(
                "navigation", f"Could not load {url}: {msg}"
            ) from exc
        await page.wait_for_timeout(3000)

        if wait_for_selector:
            try:
                await page.wait_for_selector(wait_for_selector, timeout=timeout)
            except Exception:
                click.echo(_style(
                    f"  Warning: --wait-for selector '{wait_for_selector}'"
                    " not found within timeout", fg="yellow"), err=is_json)

        if screenshots:
            import os
            ss_dir = Path(
                screenshots_dir
                or os.environ.get("WEBAGENTAUDIT_SCREENSHOTS_DIR")
                or "screenshots"
            )
            ss_dir.mkdir(parents=True, exist_ok=True)
            await page.screenshot(path=str(ss_dir / "00_discovery.png"),
                                  full_page=False)

        provider_hint = None
        try:
            for _ in range(PROVIDER_DETECTION_MAX_ATTEMPTS):
                detection = await _detection_result_for_page(page, url)
                provider_hint = detection.provider_hint
                interaction_hint = detection.interaction_hint or {}
                if provider_hint or any(
                    key in interaction_hint
                    for key in ("input_selector", "widget_selector")
                ):
                    break
                await page.wait_for_timeout(PROVIDER_DETECTION_POLL_MS)
        except PageDataCollectionError as exc:
            raise TargetAssessmentFailure("navigation", str(exc)) from exc
        if provider_hint and progress_callback:
            progress_callback("PROVIDER", provider_hint)
        interaction = _interaction_description(provider_hint=provider_hint)
        if interaction and emit_output:
            click.echo(f"  Interaction: {interaction}", err=is_json)
        configurator = (
            BotpressAutoConfigurator(progress_callback=progress_callback)
            if provider_hint == "botpress"
            else ChatbaseAutoConfigurator(progress_callback=progress_callback)
            if provider_hint == "chatbase"
            else IntercomAutoConfigurator(progress_callback=progress_callback)
            if provider_hint == "intercom"
            else ChatbotComAutoConfigurator(progress_callback=progress_callback)
            if provider_hint == "chatbot.com"
            else LiveChatAutoConfigurator(progress_callback=progress_callback)
            if provider_hint == "livechat"
            else DenserAutoConfigurator(progress_callback=progress_callback)
            if provider_hint == "denser"
            else FeaturebaseAutoConfigurator(progress_callback=progress_callback)
            if provider_hint == "featurebase"
            else FlyweightAutoConfigurator(progress_callback=progress_callback)
            if provider_hint == "flyweight"
            else TidioAutoConfigurator(progress_callback=progress_callback)
            if provider_hint == "tidio"
            else VoiceflowAutoConfigurator(progress_callback=progress_callback)
            if provider_hint == "voiceflow"
            else AlgorithmicAutoConfigurator(
                progress_callback=progress_callback
            )
        )
        try:
            auto_result = await configurator.configure(
                page,
                skip_response=True,
                input_hint=parse_hint(input_hint) if input_hint else None,
                submit_hint=parse_hint(submit_hint) if submit_hint else None,
                response_hint=parse_hint(response_hint) if response_hint else None,
            )
        except ChannelSubmissionError as exc:
            raise TargetAssessmentFailure(
                "prompt_submission", str(exc), provider_hint=provider_hint
            ) from exc
        except ChannelResponseError as exc:
            raise TargetAssessmentFailure(
                "response_read", str(exc), provider_hint=provider_hint
            ) from exc
        except ChannelNotReadyError as exc:
            raise TargetAssessmentFailure(
                "chat_detection", str(exc), provider_hint=provider_hint
            ) from exc
    except BaseException:
        await closeable.close()
        raise

    plan = auto_result.to_interaction_plan()

    if plan and emit_output:
        click.echo(_style("  Auto-discovery succeeded!", fg="green"), err=is_json)
        click.echo(f"    Input:    {plan.input_selector}", err=is_json)
        click.echo(f"    Submit:   {plan.submit_selector or 'Enter key'}", err=is_json)
        click.echo("    Response: discovered from the assessment prompt", err=is_json)
        if plan.input_frame_path:
            click.echo(f"    Iframe:   {' > '.join(plan.input_frame_path)}", err=is_json)
    elif emit_output:
        click.echo(_style("  Auto-discovery failed.", fg="red"), err=is_json)

    return plan, page, closeable, provider_hint


def _read_url_file(path: Path) -> list[str]:
    """Read non-empty, non-comment URL lines without changing their order."""
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8-sig").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def _git_provenance() -> tuple[str | None, bool | None, str | None]:
    """Return best-effort repository state without affecting assessment."""
    cwd = Path(__file__).resolve().parent
    try:
        revision = subprocess.run(
            ["git", "-C", str(cwd), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=2,
        ).stdout.strip()
        dirty = bool(subprocess.run(
            ["git", "-C", str(cwd), "status", "--porcelain"],
            check=True,
            capture_output=True,
            text=True,
            timeout=2,
        ).stdout.strip())
        diff = subprocess.run(
            ["git", "-C", str(cwd), "diff", "--binary", "HEAD", "--"],
            check=True,
            capture_output=True,
            timeout=2,
        ).stdout
        return (
            revision,
            dirty,
            hashlib.sha256(diff).hexdigest() if dirty else None,
        )
    except (OSError, subprocess.SubprocessError):
        return None, None, None


def _file_sha256(path: Path) -> str:
    with path.open("rb") as input_file:
        return hashlib.file_digest(input_file, "sha256").hexdigest()


def _probe_file_hashes(assess_kwargs: dict) -> dict[str, str]:
    """Hash custom probe sources used by a batch run."""
    paths = {Path(path) for path in assess_kwargs["probe_file"]}
    if probe_dir := assess_kwargs["probe_dir"]:
        paths.update(
            path for path in Path(probe_dir).rglob("*")
            if path.suffix.lower() in {".yaml", ".yml"}
        )
    hashes = {}
    for path in sorted(paths):
        hashes[str(path)] = _file_sha256(path)
    return hashes


async def _assess_file(
    *, url_file: Path, assess_kwargs: dict, output_format: str,
    output_file: Path | None = None,
) -> bool:
    """Assess URL-file targets sequentially and report operational failures."""
    from webagentaudit.cli.models import (
        BatchAssessmentResult,
        BatchRunMetadata,
        BatchAssessmentSummary,
        BatchTargetResult,
    )

    urls = _read_url_file(url_file)
    if not urls:
        raise click.UsageError(f"URL file is empty: {url_file}")

    targets: list[BatchTargetResult] = []
    is_json = output_format == "json"
    run_started_at = datetime.now(UTC)
    git_revision, git_dirty, git_diff_sha256 = _git_provenance()
    probe_file_hashes = _probe_file_hashes(assess_kwargs)
    browser_version: str | None = None
    for index, target_url in enumerate(urls, start=1):
        if not is_json:
            click.echo(
                f"[{index}/{len(urls)}] RUN  {target_url}"
            )
        started_at = time.monotonic()
        active_phase = "chat_detection"
        identified_provider: str | None = None
        identified_interaction: str | None = None

        def report_progress(phase: str, detail: str) -> None:
            nonlocal active_phase, identified_provider, identified_interaction
            if phase == "PROVIDER":
                identified_provider = detail
            elif phase == "INTERACTION":
                identified_interaction = detail
            if phase in {"DISCOVER", "BLOCKER", "TRIGGER"}:
                active_phase = "chat_detection"
            elif phase in {"CHAT FOUND", "TYPED"}:
                active_phase = "prompt_submission"
            elif phase == "SUBMITTED":
                active_phase = "response_read"
            elif phase == "RESPONSE READ":
                active_phase = "assessment"
            if not is_json and (
                assess_kwargs["verbose"] or phase == "INTERACTION"
            ):
                _print_progress(
                    phase,
                    detail,
                    prefix=f"[{index}/{len(urls)}] ",
                )

        try:
            assessment = await _assess(
                url=target_url,
                emit_output=False,
                warn_probe_overlaps=index == 1,
                progress_callback=report_progress,
                **assess_kwargs,
            )
            browser_version = (
                browser_version or assessment.metadata.get("browser_version")
            )
            probe_error = next(
                (
                    error
                    for probe_result in assessment.probe_results
                    for error in probe_result.errors
                ),
                None,
            )
            if probe_error:
                target_result = BatchTargetResult(
                    url=target_url,
                    status="failed",
                    failure_phase=probe_error.phase,
                    error=probe_error.message,
                    duration_ms=(time.monotonic() - started_at) * 1000,
                    probes_run=assessment.summary.total_probes,
                    vulnerabilities_found=(
                        assessment.summary.vulnerabilities_found
                    ),
                    provider_hint=assessment.metadata.get("provider_hint"),
                    interaction=assessment.metadata.get("interaction"),
                    error_type="ProbeError",
                    assessment=assessment,
                )
            else:
                target_result = BatchTargetResult(
                    url=target_url,
                    status="success",
                    duration_ms=(time.monotonic() - started_at) * 1000,
                    probes_run=assessment.summary.total_probes,
                    vulnerabilities_found=(
                        assessment.summary.vulnerabilities_found
                    ),
                    provider_hint=assessment.metadata.get("provider_hint"),
                    interaction=assessment.metadata.get("interaction"),
                    assessment=assessment,
                )
        except TargetNotFound as exc:
            target_result = BatchTargetResult(
                url=target_url,
                status="not_found",
                reason=exc.message,
                duration_ms=(time.monotonic() - started_at) * 1000,
            )
        except TimeoutError:
            target_result = BatchTargetResult(
                url=target_url,
                status="failed",
                failure_phase=active_phase,
                error=f"Target timed out during {active_phase}",
                error_type="TimeoutError",
                provider_hint=identified_provider,
                interaction=identified_interaction,
                duration_ms=(time.monotonic() - started_at) * 1000,
            )
        except TargetAssessmentFailure as exc:
            target_result = BatchTargetResult(
                url=target_url,
                status="failed",
                failure_phase=exc.phase,
                error=exc.message,
                error_type=type(exc).__name__,
                provider_hint=exc.provider_hint or identified_provider,
                interaction=identified_interaction,
                duration_ms=(time.monotonic() - started_at) * 1000,
            )
        except Exception as exc:
            logger = logging.getLogger(__name__)
            logger.debug(
                "Unexpected batch assessment failure for %s",
                target_url,
                exc_info=True,
            )
            target_result = BatchTargetResult(
                url=target_url,
                status="failed",
                failure_phase="assessment",
                error=str(exc) or type(exc).__name__,
                error_type=type(exc).__name__,
                provider_hint=identified_provider,
                interaction=identified_interaction,
                duration_ms=(time.monotonic() - started_at) * 1000,
            )

        targets.append(target_result)
        if not is_json:
            seconds = target_result.duration_ms / 1000
            if target_result.outcome == "vulnerable":
                click.echo(
                    f"[{index}/{len(urls)}] VULN {target_url} ({seconds:.1f}s)"
                )
            elif target_result.outcome == "passed":
                click.echo(
                    f"[{index}/{len(urls)}] PASS {target_url} ({seconds:.1f}s)"
                )
            elif target_result.outcome == "not_found":
                click.echo(
                    f"[{index}/{len(urls)}] NOT_FOUND {target_url}: "
                    f"{target_result.reason}"
                )
            elif target_result.outcome == "probably_not_vulnerable":
                click.echo(
                    f"[{index}/{len(urls)}] PROBABLY_NOT_VULNERABLE "
                    f"{target_url} phase={target_result.failure_phase}: "
                    f"{target_result.error}"
                )
            else:
                click.echo(
                    f"[{index}/{len(urls)}] FAIL {target_url} "
                    f"phase={target_result.failure_phase}: {target_result.error}"
                )

    operational_failures = sum(target.status == "failed" for target in targets)
    outcomes = Counter(target.outcome for target in targets)
    batch_result = BatchAssessmentResult(
        summary=BatchAssessmentSummary(
            total=len(targets),
            vulnerable=outcomes["vulnerable"],
            passed=outcomes["passed"],
            probably_not_vulnerable=outcomes["probably_not_vulnerable"],
            failed=outcomes["failed"],
            not_found=outcomes["not_found"],
        ),
        targets=targets,
        run=BatchRunMetadata(
            started_at=run_started_at,
            completed_at=datetime.now(UTC),
            webagentaudit_version=VERSION,
            git_revision=git_revision,
            git_dirty=git_dirty,
            git_diff_sha256=git_diff_sha256,
            command=list(sys.argv),
            url_file_sha256=_file_sha256(url_file),
            probe_files_sha256=probe_file_hashes,
            browser_name=assess_kwargs["browser"],
            browser_version=browser_version,
            playwright_version=version("playwright"),
        ),
        output_file=str(output_file) if output_file else None,
    )
    if is_json:
        click.echo(batch_result.model_dump_json(indent=2))
    else:
        click.echo()
        click.echo(
            f"Batch complete: {outcomes['vulnerable']} vulnerable, "
            f"{outcomes['passed']} passed, "
            f"{outcomes['probably_not_vulnerable']} probably not vulnerable, "
            f"{outcomes['failed']} failed, {outcomes['not_found']} not found, "
            f"{len(targets)} total."
        )
        if outcomes["probably_not_vulnerable"]:
            click.echo(
                "Probably not vulnerable means submission completed and the "
                "detector pattern was not observed."
            )
    if output_file:
        _write_json_output(output_file, batch_result)
        if not is_json:
            click.echo(f"Wrote complete JSON results to {output_file}")
    return operational_failures > 0


def _write_json_output(path: Path, result) -> None:
    """Persist a Pydantic CLI result as formatted JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(result.model_dump_json(indent=2) + "\n", encoding="utf-8")


def _default_output_path() -> Path:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    return Path("output") / f"webagentaudit-{timestamp}.json"


async def _assess(
    *, url: str, headful: bool, fullscreen: bool,
    window_position: tuple[int, int] | None, browser: str,
    browser_exe: str | None,
    user_data_dir: str | None, timeout: int, post_send_wait: int,
    post_success_wait: int, workers: int,
    input_selector: str | None, response_selector: str | None,
    submit_selector: str | None, trigger_selector: str | None, input_hint: str | None,
    submit_hint: str | None, response_hint: str | None,
    iframe_selector: str | None, wait_for_selector: str | None,
    category: str | None, sophistication: str | None,
    severity: str | None, probes: str | None,
    probe_dir: str | None, probe_file: tuple[str, ...],
    screenshots: bool, screenshots_dir: str | None, output_format: str,
    verbose: bool = False,
    emit_output: bool = True,
    warn_probe_overlaps: bool = True,
    progress_callback: Callable[[str, str], None] | None = None,
):
    from playwright.async_api import async_playwright

    from webagentaudit.assessment.assessor import LlmAssessor
    from webagentaudit.assessment.config import AssessmentConfig
    from webagentaudit.llm_channel.config import ChannelConfig
    from webagentaudit.llm_channel.consts import (
        DEFAULT_RESPONSE_SELECTORS_BY_HOST,
        DEFAULT_RESPONSE_SELECTORS_BY_PROVIDER,
        PAGE_SETTLE_MS,
    )
    from webagentaudit.llm_channel.models import InteractionAction, InteractionPlan
    from webagentaudit.llm_channel.playwright_channel import PlaywrightChannel
    from webagentaudit.llm_channel.strategies.custom import CustomStrategy

    is_json = output_format == "json"
    if verbose and progress_callback is None and emit_output and not is_json:
        progress_callback = lambda phase, detail: _print_progress(
            phase, detail, prefix="  "
        )

    registry = _load_registry(
        probe_dir=probe_dir, probe_file=probe_file,
        category=category, sophistication=sophistication,
        severity=severity, probes=probes,
        emit_output=emit_output,
    )
    all_probes = registry.get_all()
    if not all_probes:
        raise TargetAssessmentFailure("assessment", "No probes to run.")
    if warn_probe_overlaps:
        _warn_probe_prompt_overlaps(registry)

    # Single Playwright instance for the entire assess run
    async with async_playwright() as pw:
        plan: InteractionPlan | None = None
        provider_hint = None
        discovered_page = None
        discovered_closeable = None
        if not input_selector:
            plan, discovered_page, discovered_closeable, provider_hint = (
                await _open_and_auto_discover(
                url, pw=pw, browser=browser, headful=headful,
                browser_exe=browser_exe, user_data_dir=user_data_dir,
                fullscreen=fullscreen, window_position=window_position,
                timeout=timeout, wait_for_selector=wait_for_selector,
                input_hint=input_hint, submit_hint=submit_hint,
                response_hint=response_hint, screenshots=screenshots,
                screenshots_dir=screenshots_dir, output_format=output_format,
                skip_response=True,
                emit_output=emit_output,
                progress_callback=progress_callback,
                )
            )
            if provider_hint and progress_callback:
                progress_callback("PROVIDER", provider_hint)
            if provider_hint and emit_output and not is_json:
                click.echo(f"  Identified provider: {provider_hint}")
        else:
            plan = InteractionPlan(
                input_selector=input_selector,
                submit_selector=submit_selector,
                response_selector=response_selector,
                input_frame_path=[iframe_selector] if iframe_selector else [],
                setup_actions=(
                    [InteractionAction(kind="trigger", selector=trigger_selector)]
                    if trigger_selector else []
                ),
            )

        if plan is None:
            if discovered_closeable:
                await discovered_closeable.close()
            if provider_hint is None:
                raise TargetNotFound(
                    "No chatbot provider or usable chat input was found."
                )
            raise TargetAssessmentFailure(
                "chat_detection",
                "A chatbot provider was detected, but no usable chat input "
                "was found.",
                provider_hint=provider_hint,
            )

        interaction = _interaction_description(
            provider_hint=provider_hint,
            plan=plan,
        )
        host = (urlparse(url).hostname or "").removeprefix("www.")
        updates: dict = {
            "submit_selector": submit_selector or plan.submit_selector,
            "response_selector": (
                response_selector
                or DEFAULT_RESPONSE_SELECTORS_BY_HOST.get(host)
                or DEFAULT_RESPONSE_SELECTORS_BY_PROVIDER.get(provider_hint or "")
                or plan.response_selector
            ),
        }
        if iframe_selector:
            updates["input_frame_path"] = [iframe_selector]
        if trigger_selector and not any(
            action.kind == "trigger" and action.selector == trigger_selector
            for action in plan.setup_actions
        ):
            updates["setup_actions"] = [
                InteractionAction(kind="trigger", selector=trigger_selector),
                *plan.setup_actions,
            ]
        plan = plan.model_copy(update=updates)

        if emit_output and not is_json:
            _print_header("LLM Security Assessment")
            _print_kv("URL", url)
            if provider_hint:
                _print_kv("Provider", provider_hint)
            if interaction:
                _print_kv("Interaction", interaction)
            browser_mode = (
                "full-screen" if fullscreen else "headed" if headful else "headless"
            )
            if window_position and not fullscreen:
                browser_mode = "headed"
            _print_kv("Browser", f"{browser} ({browser_mode})")
            if window_position:
                _print_kv(
                    "Window Position",
                    f"{window_position[0]}, {window_position[1]}",
                )
            _print_kv("Input", plan.input_selector)
            _print_kv("Submit", plan.submit_selector or "Enter key")
            _print_kv(
                "Response", plan.response_selector or "discover after prompt"
            )
            _print_kv("Probes", str(len(all_probes)))

        channel_config = ChannelConfig(
            headless=not (headful or fullscreen or window_position),
            fullscreen=fullscreen,
            window_position=window_position,
            browser=browser,
            timeout_ms=timeout,
            post_send_wait_ms=post_send_wait,
            post_success_wait_ms=post_success_wait,
            post_send_screenshot_dir=(
                screenshots_dir or "screenshots" if screenshots else None
            ),
            user_data_dir=user_data_dir,
            executable_path=browser_exe,
        )

        first_page = discovered_page
        if first_page is None:
            first_page, discovered_closeable = await _launch_browser(
                pw, browser, headful, browser_exe, user_data_dir,
                fullscreen=fullscreen, window_position=window_position,
            )
            try:
                await goto_and_inspect(first_page, url, timeout)
                await first_page.wait_for_timeout(PAGE_SETTLE_MS)
            except Exception as exc:
                await discovered_closeable.close()
                message = str(exc).split("\n")[0]
                raise TargetAssessmentFailure(
                    "navigation", f"Could not load {url}: {message}"
                ) from exc
        shared_context = first_page.context
        reuse_live_page = workers == 1
        keeper_page = None
        if not reuse_live_page:
            keeper_page = await shared_context.new_page()
            await first_page.bring_to_front()

        def channel_factory() -> PlaywrightChannel:
            nonlocal first_page
            page = first_page
            if not reuse_live_page:
                first_page = None
            strategy = CustomStrategy(
                plan=(
                    plan.model_copy(update={"setup_actions": []})
                    if page else plan
                ),
                progress_callback=progress_callback,
            )
            return PlaywrightChannel(
                config=channel_config, strategy=strategy,
                page=page,
                context=shared_context,
                close_external_page=not reuse_live_page,
            )

        assess_config = AssessmentConfig(workers=workers)
        completed = 0

        def _on_progress(results) -> None:
            nonlocal completed
            if len(results) <= completed:
                return
            latest = results[-1]
            completed = len(results)
            if progress_callback:
                _emit_probe_progress(latest, progress_callback)
            if is_json or not emit_output or verbose:
                return
            if latest.error_count:
                status = _style("ERROR", fg="red", bold=True)
            elif latest.vulnerability_detected:
                status = _style("VULN", fg="red", bold=True)
            else:
                status = _style("PASS", fg="green")
            click.echo(
                f"  [{completed}/{len(all_probes)}] {status} {latest.probe_name}"
            )

        if emit_output and not is_json:
            _print_section("Running Probes")

        assessor = LlmAssessor(
            config=assess_config,
            channel_factory=channel_factory,
            registry=registry,
            progress_callback=_on_progress,
            activity_callback=progress_callback,
        )
        browser_instance = shared_context.browser
        browser_version = (
            browser_instance.version if browser_instance is not None else None
        )
        try:
            result = await assessor.assess(url)
        finally:
            if keeper_page:
                await keeper_page.close()
            if discovered_closeable:
                await discovered_closeable.close()

        if provider_hint:
            result.metadata["provider_hint"] = provider_hint
        if interaction:
            result.metadata["interaction"] = interaction
        result.metadata["browser_name"] = browser
        if browser_version:
            result.metadata["browser_version"] = browser_version

    if not emit_output:
        return result
    if output_format == "json":
        click.echo(result.model_dump_json(indent=2))
    else:
        click.echo()
        _print_assessment_result(result)
    return result


def _print_assessment_result(result) -> None:
    s = result.summary
    _print_header(f"Results — {s.target_url}")
    _print_kv("Total Probes", str(s.total_probes))

    if s.vulnerabilities_found > 0:
        _print_kv("Vulnerabilities",
                  _style(str(s.vulnerabilities_found), fg="red", bold=True))
    else:
        _print_kv("Vulnerabilities",
                  _style("0", fg="green"))

    if result.probe_results:
        _print_section("Probe Results")
        for pr in result.probe_results:
            if pr.error_count:
                click.echo(
                    f"  {_style('ERROR', fg='red', bold=True)} "
                    f" {pr.probe_name}"
                )
                for error in pr.errors:
                    click.echo(f"      [{error.phase}] {error.message}")
                if pr.security_verdict == "probably_not_vulnerable":
                    click.echo(
                        "       verdict:  probably not vulnerable "
                        "(submitted; detector pattern not observed)"
                    )
            elif pr.vulnerability_detected:
                click.echo(f"  {_style('VULN', fg='red', bold=True)}"
                           f"  {pr.probe_name}")
                if pr.matched_patterns:
                    click.echo(f"       matched: {', '.join(pr.matched_patterns)}")
                if pr.exchanges:
                    last = pr.exchanges[-1]
                    click.echo(f"       prompt:   {last.prompt[:200].replace(chr(10), ' ')}")
                    click.echo(f"       response: {last.response[:200].replace(chr(10), ' ')}")
            else:
                click.echo(f"  {_style('PASS', fg='green')}  {pr.probe_name}")

    click.echo()


# ---------------------------------------------------------------------------
# probes command
# ---------------------------------------------------------------------------

@cli.command()
@click.option("--category", type=str,
              help="Filter by category (comma-separated).")
@click.option("--sophistication", type=str,
              help="Filter by sophistication (comma-separated).")
@click.option("--severity", type=str,
              help="Filter by severity (comma-separated: critical,high,medium,low,info).")
@click.option("--probe-dir", type=click.Path(exists=True, file_okay=False),
              help="Load additional YAML probes from directory.")
@click.option("--output", "output_format", type=click.Choice(["text", "json"]),
              default="text", help="Output format.")
def probes(category: str | None, sophistication: str | None,
           severity: str | None,
           probe_dir: str | None, output_format: str) -> None:
    """List available security probes."""
    from webagentaudit.assessment.probes.registry import ProbeRegistry

    registry = ProbeRegistry.default()
    if probe_dir:
        loaded = registry.load_yaml_dir(Path(probe_dir))
        click.echo(f"Loaded {loaded} custom probe(s) from {probe_dir}")

    all_probes = registry.get_all()

    if category:
        try:
            cats = {ProbeCategory(c.strip()) for c in category.split(",")}
        except ValueError as e:
            valid = ", ".join(v.value for v in ProbeCategory)
            raise click.BadParameter(f"Invalid category. Valid: {valid}") from e
        all_probes = [p for p in all_probes if p.category in cats]
    if sophistication:
        try:
            sophs = {Sophistication(s.strip()) for s in sophistication.split(",")}
        except ValueError as e:
            valid = ", ".join(v.value for v in Sophistication)
            raise click.BadParameter(f"Invalid sophistication. Valid: {valid}") from e
        all_probes = [p for p in all_probes if p.sophistication in sophs]
    if severity:
        try:
            sevs = {Severity(s.strip()) for s in severity.split(",")}
        except ValueError as e:
            valid = ", ".join(v.value for v in Severity)
            raise click.BadParameter(f"Invalid severity. Valid: {valid}") from e
        all_probes = [p for p in all_probes if p.severity in sevs]

    all_probes.sort(key=lambda p: (p.category.value, p.name))

    if output_format == "json":
        data = [
            {
                "name": p.name,
                "category": p.category.value,
                "severity": p.severity.value,
                "sophistication": p.sophistication.value,
                "description": p.description,
            }
            for p in all_probes
        ]
        click.echo(json.dumps(data, indent=2))
        return

    _print_header(f"Available Probes ({len(all_probes)})")
    click.echo()

    by_cat: dict[str, list] = {}
    for p in all_probes:
        by_cat.setdefault(p.category.value, []).append(p)

    for cat, cat_probes in by_cat.items():
        click.echo(f"  {_style(cat, fg='cyan', bold=True)}")
        for p in cat_probes:
            sev_color = _severity_color(p.severity.value)
            soph_badge = {
                "basic": _style("BASIC", fg="green"),
                "intermediate": _style("INTM", fg="yellow"),
                "advanced": _style("ADV", fg="red"),
            }.get(p.sophistication.value, p.sophistication.value)
            click.echo(
                f"    {_style(p.name, bold=True)}"
                f"  [{_style(p.severity.value.upper(), fg=sev_color)}]"
                f"  [{soph_badge}]"
            )
            click.echo(f"      {p.description}")
        click.echo()


if __name__ == "__main__":
    cli()
