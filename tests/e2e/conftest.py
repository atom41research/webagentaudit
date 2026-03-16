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


def pytest_addoption(parser):
    parser.addoption("--headed", action="store_true", default=False,
                     help="Run browser in headed (visible) mode")
    parser.addoption("--slowmo", type=int, default=0,
                     help="Slow down Playwright actions by N milliseconds")
    parser.addoption("--pause", type=int, default=0,
                     help="Pause N seconds before closing browser (useful with --headed)")


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


@pytest.fixture(scope="session")
async def _pw():
    """Single Playwright instance per session/worker."""
    pw = await async_playwright().start()
    yield pw
    await pw.stop()


@pytest.fixture(scope="session")
async def _browser(_pw, request):
    """Single browser per session/worker."""
    headed = request.config.getoption("--headed")
    slowmo = request.config.getoption("--slowmo")
    b = await _pw.chromium.launch(headless=not headed, slow_mo=slowmo)
    yield b
    await b.close()


@pytest.fixture
async def page(_browser, request):
    """Fresh context per test from shared browser (cheap)."""
    pause = request.config.getoption("--pause")
    context = await _browser.new_context()
    pg = await context.new_page()
    yield pg
    if pause > 0:
        await pg.wait_for_timeout(pause * 1000)
    await context.close()
