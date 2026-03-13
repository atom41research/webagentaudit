"""Shared fixtures for end-to-end tests.

Provides a local HTTP server serving the docs/ demo pages, plus
Playwright browser fixtures.
"""

from __future__ import annotations

import socket
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

import pytest
from playwright.async_api import async_playwright


DOCS_DIR = Path(__file__).resolve().parent.parent.parent / "docs"


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class _QuietHandler(SimpleHTTPRequestHandler):
    """HTTP handler that suppresses access log noise in tests."""

    def __init__(self, *args, directory=None, **kwargs):
        super().__init__(*args, directory=str(DOCS_DIR), **kwargs)

    def log_message(self, format, *args):
        pass  # suppress request logs during tests


# Module-level server (started once, shared across all tests)
_server = None
_server_url = None


def _ensure_server():
    global _server, _server_url
    if _server is None:
        port = _find_free_port()
        _server = HTTPServer(("127.0.0.1", port), _QuietHandler)
        thread = threading.Thread(target=_server.serve_forever, daemon=True)
        thread.start()
        _server_url = f"http://127.0.0.1:{port}"
    return _server_url


@pytest.fixture
def demo_server():
    """Start a local HTTP server for the docs/ demo pages.

    Yields the base URL (e.g. ``http://127.0.0.1:PORT``).
    """
    return _ensure_server()


@pytest.fixture
async def page():
    """Fresh Playwright page per test."""
    pw = await async_playwright().start()
    browser = await pw.chromium.launch(headless=True)
    context = await browser.new_context()
    pg = await context.new_page()
    yield pg
    await context.close()
    await browser.close()
    await pw.stop()
