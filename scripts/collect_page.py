"""Collect rendered DOM and screenshot from a single page using Playwright.

Usage:
    uv run python scripts/collect_page.py <url> <name> [--output-dir DIR] [--wait SECONDS]

Example:
    uv run python scripts/collect_page.py https://chatgpt.com chatgpt --wait 5
"""

import argparse
import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path

from playwright.async_api import async_playwright

DEFAULT_OUTPUT_DIR = Path("tests/fixtures/rendered")
DEFAULT_WAIT_EXTRA = 3.0


async def collect_page(
    url: str,
    name: str,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    wait_extra: float = DEFAULT_WAIT_EXTRA,
) -> Path:
    """Navigate to a URL, wait for dynamic content, and save rendered DOM + screenshot.

    Returns the path to the output directory for this page.
    """
    page_dir = output_dir / name
    page_dir.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            ),
        )
        page = await context.new_page()

        print(f"  Navigating to {url} ...")
        try:
            await page.goto(url, wait_until="networkidle", timeout=30_000)
        except Exception:
            # Some pages never reach networkidle — fall back to domcontentloaded
            print(f"  networkidle timeout, falling back to domcontentloaded")
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=60_000)
            except Exception:
                print(f"  domcontentloaded also timed out, using whatever loaded")

        # Extra wait for lazy-loaded widgets (chatbots, iframes, etc.)
        print(f"  Waiting {wait_extra}s for dynamic content ...")
        await page.wait_for_timeout(int(wait_extra * 1000))

        # Capture rendered DOM
        html = await page.content()
        dom_path = page_dir / "rendered_dom.html"
        dom_path.write_text(html, encoding="utf-8")
        print(f"  Saved DOM ({len(html):,} chars) → {dom_path}")

        # Capture screenshot (viewport only — full_page can timeout on long pages)
        screenshot_path = page_dir / "screenshot.png"
        try:
            await page.screenshot(path=str(screenshot_path), timeout=15_000)
            print(f"  Saved screenshot → {screenshot_path}")
        except Exception as e:
            print(f"  Screenshot failed (non-fatal): {e}")

        # Extract metadata
        title = await page.title()
        scripts = await page.evaluate(
            "() => [...document.scripts].map(s => s.src).filter(Boolean)"
        )
        iframes = await page.evaluate(
            """() => [...document.querySelectorAll('iframe')].map(f => ({
                src: f.src || '',
                id: f.id || '',
                name: f.name || '',
                width: f.width || '',
                height: f.height || ''
            }))"""
        )
        inline_script_count = await page.evaluate(
            "() => [...document.scripts].filter(s => !s.src && s.textContent.trim()).length"
        )

        metadata = {
            "url": url,
            "name": name,
            "title": title,
            "collected_at": datetime.now(UTC).isoformat(),
            "dom_length": len(html),
            "scripts": scripts,
            "script_count": len(scripts),
            "inline_script_count": inline_script_count,
            "iframes": iframes,
            "iframe_count": len(iframes),
        }
        metadata_path = page_dir / "metadata.json"
        metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        print(f"  Saved metadata ({len(scripts)} scripts, {len(iframes)} iframes) → {metadata_path}")

        await browser.close()

    return page_dir


def main():
    parser = argparse.ArgumentParser(description="Collect rendered DOM and screenshot from a page")
    parser.add_argument("url", help="URL to collect")
    parser.add_argument("name", help="Short name for the page (used as directory name)")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--wait",
        type=float,
        default=DEFAULT_WAIT_EXTRA,
        help=f"Extra wait time in seconds for dynamic content (default: {DEFAULT_WAIT_EXTRA})",
    )
    args = parser.parse_args()

    print(f"Collecting: {args.name} ({args.url})")
    result_dir = asyncio.run(collect_page(args.url, args.name, args.output_dir, args.wait))
    print(f"Done! Output: {result_dir}")


if __name__ == "__main__":
    main()
