"""webagentaudit CLI — detect and assess interactive LLMs on webpages."""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from pathlib import Path

import click

from webagentaudit.core.consts import VERSION
from webagentaudit.core.enums import ProbeCategory, Severity, Sophistication


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


def _severity_color(severity: str) -> str:
    return {"critical": "red", "high": "red", "medium": "yellow",
            "low": "blue", "info": "white"}.get(severity, "white")


BROWSER_CHOICES = ["chromium", "firefox", "webkit"]


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
@click.option("--browser", type=click.Choice(BROWSER_CHOICES), default="chromium",
              help="Browser engine to use.")
@click.option("--browser-exe", type=click.Path(exists=True), default=None,
              help="Path to browser executable.")
@click.option("--user-data-dir", type=click.Path(), default=None,
              help="Browser profile directory for authenticated sessions.")
@click.option("--timeout", default=30000, type=int, help="Navigation timeout in ms.")
@click.option("-v", "--verbose", is_flag=True, help="Enable verbose debug logging.")
@click.option("--output", "output_format", type=click.Choice(["text", "json"]),
              default="text", help="Output format.")
def detect(url: str, headful: bool, browser: str, browser_exe: str | None,
           user_data_dir: str | None, timeout: int, verbose: bool,
           output_format: str) -> None:
    """Detect interactive LLMs on a webpage."""
    if verbose:
        logging.basicConfig(level=logging.DEBUG,
                            format="%(levelname)-5s %(name)s: %(message)s")
    asyncio.run(_detect(url, headful, browser, browser_exe,
                        user_data_dir, timeout, output_format))


async def _collect_page_data(page, url: str):
    """Collect PageData from a live Playwright page."""
    from webagentaudit.detection.models import PageData

    html = await page.content()
    scripts = await page.evaluate(
        "() => Array.from(document.querySelectorAll('script[src]')).map(s => s.src)"
    )
    inline_scripts = await page.evaluate(
        "() => Array.from(document.querySelectorAll('script:not([src])'))"
        ".map(s => s.textContent || '').filter(t => t.trim().length > 0)"
    )
    stylesheets = await page.evaluate(
        "() => Array.from(document.querySelectorAll('link[rel=\"stylesheet\"]'))"
        ".map(l => l.href)"
    )
    meta_tags = await page.evaluate("""() => {
        const m = {};
        document.querySelectorAll('meta[name], meta[property]').forEach(el => {
            const key = el.getAttribute('name') || el.getAttribute('property');
            m[key] = el.getAttribute('content') || '';
        });
        return m;
    }""")
    iframes = await page.evaluate(
        "() => Array.from(document.querySelectorAll('iframe'))"
        ".map(f => f.src).filter(s => s)"
    )
    return PageData(
        url=url, html=html, scripts=scripts, inline_scripts=inline_scripts,
        stylesheets=stylesheets, meta_tags=meta_tags, iframes=iframes,
    )


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
                          user_data_dir: str | None):
    """Launch a Playwright browser, returning (page, closeable).

    *closeable* is the object to ``await close()`` when done — either
    a BrowserContext (persistent) or a Browser instance.
    """
    launcher = getattr(pw, browser)
    launch_kw: dict = {"headless": not headful}
    if browser_exe:
        launch_kw["executable_path"] = browser_exe

    if user_data_dir:
        ctx = await launcher.launch_persistent_context(
            user_data_dir, **launch_kw,
            viewport={"width": 1280, "height": 720},
        )
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        return page, ctx
    else:
        br = await launcher.launch(**launch_kw)
        page = await br.new_page()
        return page, br


async def _detect(url: str, headful: bool, browser: str,
                  browser_exe: str | None, user_data_dir: str | None,
                  timeout: int, output_format: str) -> None:
    from playwright.async_api import async_playwright

    click.echo(f"Opening {_style(browser, bold=True)} browser...")

    async with async_playwright() as pw:
        page, closeable = await _launch_browser(
            pw, browser, headful, browser_exe, user_data_dir)

        click.echo(f"Navigating to {_style(url, fg='cyan')}...")
        await page.goto(url, wait_until="domcontentloaded", timeout=timeout)
        await page.wait_for_timeout(3000)
        page_data = await _collect_page_data(page, url)
        await closeable.close()

    click.echo("Running detection...")
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
# assess command
# ---------------------------------------------------------------------------

@cli.command()
@click.argument("url")
@click.option("--headful", is_flag=True, help="Run browser in headed mode.")
@click.option("--browser", type=click.Choice(BROWSER_CHOICES), default="chromium",
              help="Browser engine to use.")
@click.option("--browser-exe", type=click.Path(exists=True), default=None,
              help="Path to browser executable.")
@click.option("--user-data-dir", type=click.Path(), default=None,
              help="Browser profile directory for authenticated sessions.")
@click.option("--timeout", type=int, default=30000, help="Timeout in ms.")
@click.option("--workers", default=1, type=int, help="Concurrent probe workers.")
@click.option("--input-selector", type=str, help="CSS selector for input element.")
@click.option("--response-selector", type=str,
              help="CSS selector for response container.")
@click.option("--submit-selector", type=str, help="CSS selector for submit button.")
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
              help="Save screenshots during auto-discovery.")
@click.option("-v", "--verbose", is_flag=True, help="Enable verbose debug logging.")
@click.option("--output", "output_format", type=click.Choice(["text", "json"]),
              default="text", help="Output format.")
def assess(
    url: str, headful: bool, browser: str, browser_exe: str | None,
    user_data_dir: str | None, timeout: int, workers: int,
    input_selector: str | None, response_selector: str | None,
    submit_selector: str | None, input_hint: str | None,
    submit_hint: str | None, response_hint: str | None,
    iframe_selector: str | None, wait_for_selector: str | None,
    category: str | None, sophistication: str | None,
    severity: str | None, probes: str | None,
    probe_dir: str | None, probe_file: tuple[str, ...], screenshots: bool,
    verbose: bool, output_format: str,
) -> None:
    """Assess AI agent security on a webpage.

    Auto-discovers chat elements when selectors are not provided.
    Use --input-selector, --response-selector to override.
    """
    if verbose:
        logging.basicConfig(level=logging.DEBUG,
                            format="%(levelname)-5s %(name)s: %(message)s")
    asyncio.run(_assess(
        url=url, headful=headful, browser=browser, browser_exe=browser_exe,
        user_data_dir=user_data_dir, timeout=timeout, workers=workers,
        input_selector=input_selector, response_selector=response_selector,
        submit_selector=submit_selector, input_hint=input_hint,
        submit_hint=submit_hint, response_hint=response_hint,
        iframe_selector=iframe_selector,
        wait_for_selector=wait_for_selector,
        category=category, sophistication=sophistication,
        severity=severity, probes=probes,
        probe_dir=probe_dir, probe_file=probe_file,
        screenshots=screenshots, output_format=output_format,
    ))


def _load_registry(
    *,
    probe_dir: str | None,
    probe_file: tuple[str, ...],
    category: str | None,
    sophistication: str | None,
    severity: str | None = None,
    probes: str | None,
):
    """Load probes into a registry and apply filters."""
    from webagentaudit.assessment.probes.registry import ProbeRegistry

    registry = ProbeRegistry.default()
    if probe_dir:
        loaded = registry.load_yaml_dir(Path(probe_dir))
        click.echo(f"Loaded {loaded} custom probe(s) from {probe_dir}")
    for pf in probe_file:
        registry.load_yaml_file(Path(pf))
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


async def _auto_discover(
    url: str, *, pw, browser: str, headful: bool,
    browser_exe: str | None, user_data_dir: str | None,
    timeout: int, wait_for_selector: str | None,
    input_hint: str | None, submit_hint: str | None,
    response_hint: str | None, screenshots: bool,
) -> tuple[str | None, str | None, str | None]:
    """Run auto-discovery to find chat element selectors."""
    from webagentaudit.llm_channel.auto_config import AlgorithmicAutoConfigurator
    from webagentaudit.llm_channel.auto_config._hint_matcher import parse_hint

    click.echo(f"  Auto-discovering chat elements on {_style(url, fg='cyan')}...")

    page, closeable = await _launch_browser(
        pw, browser, headful, browser_exe, user_data_dir)

    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=timeout)
        await page.wait_for_timeout(3000)

        if wait_for_selector:
            try:
                await page.wait_for_selector(wait_for_selector, timeout=timeout)
            except Exception:
                click.echo(_style(
                    f"  Warning: --wait-for selector '{wait_for_selector}'"
                    " not found within timeout", fg="yellow"))

        if screenshots:
            Path("screenshots").mkdir(exist_ok=True)
            await page.screenshot(path="screenshots/00_discovery.png",
                                  full_page=False)

        configurator = AlgorithmicAutoConfigurator()
        auto_result = await configurator.configure(
            page,
            input_hint=parse_hint(input_hint) if input_hint else None,
            submit_hint=parse_hint(submit_hint) if submit_hint else None,
            response_hint=parse_hint(response_hint) if response_hint else None,
        )
    finally:
        await closeable.close()

    inp = auto_result.input_selector
    sub = auto_result.submit_selector
    resp = auto_result.response_selector

    if inp:
        click.echo(_style("  Auto-discovery succeeded!", fg="green"))
        click.echo(f"    Input:    {inp}")
        click.echo(f"    Submit:   {sub or 'Enter key'}")
        click.echo(f"    Response: {resp or 'not found'}")
    else:
        click.echo(_style("  Auto-discovery failed.", fg="red"))

    return inp, sub, resp


async def _assess(
    *, url: str, headful: bool, browser: str, browser_exe: str | None,
    user_data_dir: str | None, timeout: int, workers: int,
    input_selector: str | None, response_selector: str | None,
    submit_selector: str | None, input_hint: str | None,
    submit_hint: str | None, response_hint: str | None,
    iframe_selector: str | None, wait_for_selector: str | None,
    category: str | None, sophistication: str | None,
    severity: str | None, probes: str | None,
    probe_dir: str | None, probe_file: tuple[str, ...],
    screenshots: bool, output_format: str,
) -> None:
    from playwright.async_api import async_playwright

    from webagentaudit.assessment.assessor import LlmAssessor
    from webagentaudit.assessment.config import AssessmentConfig
    from webagentaudit.llm_channel.config import ChannelConfig
    from webagentaudit.llm_channel.playwright_channel import PlaywrightChannel
    from webagentaudit.llm_channel.strategies.custom import CustomStrategy

    registry = _load_registry(
        probe_dir=probe_dir, probe_file=probe_file,
        category=category, sophistication=sophistication,
        severity=severity, probes=probes,
    )
    all_probes = registry.get_all()
    if not all_probes:
        click.echo("No probes to run.", err=True)
        sys.exit(1)

    # Resolve selectors via auto-discovery if needed
    actual_input = input_selector
    actual_submit = submit_selector
    actual_response = response_selector

    if not actual_input or not actual_response:
        async with async_playwright() as pw:
            disc_inp, disc_sub, disc_resp = await _auto_discover(
                url, pw=pw, browser=browser, headful=headful,
                browser_exe=browser_exe, user_data_dir=user_data_dir,
                timeout=timeout, wait_for_selector=wait_for_selector,
                input_hint=input_hint, submit_hint=submit_hint,
                response_hint=response_hint, screenshots=screenshots,
            )
        actual_input = actual_input or disc_inp
        actual_submit = actual_submit or disc_sub
        actual_response = actual_response or disc_resp

    if not actual_input:
        click.echo("Error: Could not find input element. Use --input-selector.",
                    err=True)
        sys.exit(1)
    if not actual_response:
        click.echo("Error: Could not find response element."
                    " Use --response-selector.", err=True)
        sys.exit(1)

    _print_header("LLM Security Assessment")
    _print_kv("URL", url)
    _print_kv("Browser", f"{browser} ({'headed' if headful else 'headless'})")
    _print_kv("Input", actual_input)
    _print_kv("Submit", actual_submit or "Enter key")
    _print_kv("Response", actual_response)
    _print_kv("Probes", str(len(all_probes)))

    channel_config = ChannelConfig(
        headless=not headful,
        timeout_ms=timeout,
        user_data_dir=user_data_dir,
    )

    # Capture for closure
    _inp, _sub, _resp = actual_input, actual_submit, actual_response

    def channel_factory() -> PlaywrightChannel:
        strategy = CustomStrategy(
            input_selector=_inp,
            response_selector=_resp,
            submit_selector=_sub,
            iframe_selector=iframe_selector,
        )
        return PlaywrightChannel(config=channel_config, strategy=strategy)

    assess_config = AssessmentConfig(workers=workers)
    completed = 0

    def _on_progress(results) -> None:
        nonlocal completed
        if len(results) > completed:
            latest = results[-1]
            completed = len(results)
            status = (
                _style("VULN", fg="red", bold=True)
                if latest.vulnerability_detected
                else _style("PASS", fg="green")
            )
            click.echo(f"  [{completed}/{len(all_probes)}] {status}"
                       f" {latest.probe_name}")

    _print_section("Running Probes")

    assessor = LlmAssessor(
        config=assess_config,
        channel_factory=channel_factory,
        registry=registry,
        progress_callback=_on_progress,
    )
    result = await assessor.assess(url)

    click.echo()
    if output_format == "json":
        click.echo(result.model_dump_json(indent=2))
    else:
        _print_assessment_result(result)


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
            if pr.vulnerability_detected:
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
