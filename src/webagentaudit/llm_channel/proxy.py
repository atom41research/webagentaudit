"""Proxy rotation utilities for LLM channels."""

import random
from enum import Enum
from pathlib import Path
from urllib.parse import urlparse, unquote

from .models import ProxyConfig


class ProxyRotationStrategy(Enum):
    """Strategy for rotating through proxy servers."""
    ROUND_ROBIN = "round_robin"
    RANDOM = "random"


class ProxyRotator:
    """Rotates through a list of proxy configurations."""

    def __init__(
        self,
        proxies: list[ProxyConfig],
        strategy: ProxyRotationStrategy = ProxyRotationStrategy.ROUND_ROBIN,
    ) -> None:
        self._proxies = proxies
        self._strategy = strategy
        self._index = 0

    def next(self) -> ProxyConfig:
        """Return the next proxy according to the rotation strategy."""
        if not self._proxies:
            raise ValueError("No proxies available")

        if self._strategy == ProxyRotationStrategy.RANDOM:
            return random.choice(self._proxies)

        proxy = self._proxies[self._index % len(self._proxies)]
        self._index += 1
        return proxy


def parse_proxy_url(url: str) -> ProxyConfig:
    """Parse a proxy URL into a ProxyConfig.

    Supports URLs like:
        http://proxy.example.com:8080
        http://user:pass@proxy.example.com:8080
        socks5://proxy.example.com:1080

    Passwords are URL-decoded (e.g., %40 -> @).
    """
    parsed = urlparse(url)

    username = unquote(parsed.username) if parsed.username else None
    password = unquote(parsed.password) if parsed.password else None

    # Reconstruct the server URL without auth credentials, preserving path/query
    server = f"{parsed.scheme}://{parsed.hostname}"
    if parsed.port:
        server += f":{parsed.port}"
    if parsed.path and parsed.path != "/":
        server += parsed.path
    if parsed.query:
        server += f"?{parsed.query}"

    return ProxyConfig(
        server=server,
        username=username,
        password=password,
    )


def load_proxy_file(path: Path) -> list[ProxyConfig]:
    """Load proxy configurations from a text file.

    Each line should contain a proxy URL. Blank lines and lines
    starting with # are skipped.
    """
    proxies: list[ProxyConfig] = []
    text = path.read_text()

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        proxies.append(parse_proxy_url(stripped))

    return proxies
