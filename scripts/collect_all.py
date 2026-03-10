"""Batch-collect rendered DOM and screenshots for all known LLM pages.

Usage:
    uv run python scripts/collect_all.py [--category CATEGORY] [--skip-existing] [--wait SECONDS]

Examples:
    uv run python scripts/collect_all.py                          # Collect all
    uv run python scripts/collect_all.py --category direct_apps   # Only direct apps
    uv run python scripts/collect_all.py --skip-existing           # Skip already collected
"""

import argparse
import asyncio
from pathlib import Path

from collect_page import DEFAULT_OUTPUT_DIR, DEFAULT_WAIT_EXTRA, collect_page
from known_llm_pages import PAGES, get_all_pages


async def collect_all(
    category: str | None = None,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    wait_extra: float = DEFAULT_WAIT_EXTRA,
    skip_existing: bool = False,
) -> dict[str, str]:
    """Collect all pages, optionally filtered by category.

    Returns a dict of {name: status} for each page.
    """
    if category:
        if category not in PAGES:
            available = ", ".join(PAGES.keys())
            raise ValueError(f"Unknown category '{category}'. Available: {available}")
        pages = PAGES[category]
    else:
        pages = get_all_pages()

    results: dict[str, str] = {}
    total = len(pages)

    for i, page_info in enumerate(pages, 1):
        name = page_info["name"]
        url = page_info["url"]
        page_dir = output_dir / name

        if skip_existing and (page_dir / "rendered_dom.html").exists():
            print(f"[{i}/{total}] Skipping {name} (already collected)")
            results[name] = "skipped"
            continue

        print(f"\n[{i}/{total}] Collecting: {name}")
        try:
            await collect_page(url, name, output_dir, wait_extra)
            results[name] = "ok"
        except Exception as e:
            print(f"  ERROR: {e}")
            results[name] = f"error: {e}"

    return results


def main():
    parser = argparse.ArgumentParser(description="Batch-collect pages from known LLM pages list")
    parser.add_argument(
        "--category",
        choices=list(PAGES.keys()),
        help="Only collect pages from this category",
    )
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
        help=f"Extra wait time in seconds (default: {DEFAULT_WAIT_EXTRA})",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip pages that already have collected data",
    )
    args = parser.parse_args()

    print(f"Starting batch collection...")
    if args.category:
        print(f"Category: {args.category}")
    print(f"Output: {args.output_dir}")
    print(f"Wait: {args.wait}s")

    results = asyncio.run(
        collect_all(args.category, args.output_dir, args.wait, args.skip_existing)
    )

    # Summary
    print("\n" + "=" * 60)
    print("Collection Summary:")
    ok = sum(1 for v in results.values() if v == "ok")
    skipped = sum(1 for v in results.values() if v == "skipped")
    errors = sum(1 for v in results.values() if v.startswith("error"))
    print(f"  Collected: {ok}")
    print(f"  Skipped:   {skipped}")
    print(f"  Errors:    {errors}")

    if errors:
        print("\nFailed pages:")
        for name, status in results.items():
            if status.startswith("error"):
                print(f"  {name}: {status}")


if __name__ == "__main__":
    main()
