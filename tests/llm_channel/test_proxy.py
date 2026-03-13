"""Tests for proxy configuration, parsing, and rotation."""

import pytest
from pathlib import Path

from webagentaudit.llm_channel.proxy import (
    ProxyRotationStrategy,
    ProxyRotator,
    load_proxy_file,
    parse_proxy_url,
)
from webagentaudit.llm_channel.models import ProxyConfig


class TestParseProxyUrl:
    def test_simple_http(self):
        config = parse_proxy_url("http://proxy.example.com:8080")
        assert config.server == "http://proxy.example.com:8080"
        assert config.username is None
        assert config.password is None

    def test_with_auth(self):
        config = parse_proxy_url("http://user:pass@proxy.example.com:8080")
        assert config.server == "http://proxy.example.com:8080"
        assert config.username == "user"
        assert config.password == "pass"

    def test_socks5(self):
        config = parse_proxy_url("socks5://proxy.example.com:1080")
        assert config.server == "socks5://proxy.example.com:1080"
        assert config.username is None

    def test_no_port(self):
        config = parse_proxy_url("http://proxy.example.com")
        assert config.server == "http://proxy.example.com"

    def test_special_chars_in_password(self):
        config = parse_proxy_url("http://user:p%40ss@proxy.example.com:8080")
        assert config.username == "user"
        assert config.password == "p@ss"


class TestProxyRotator:
    def test_round_robin(self):
        proxies = [
            ProxyConfig(server=f"http://proxy{i}.example.com:8080")
            for i in range(3)
        ]
        rotator = ProxyRotator(proxies=proxies)
        results = [rotator.next() for _ in range(6)]
        assert results[0].server == "http://proxy0.example.com:8080"
        assert results[1].server == "http://proxy1.example.com:8080"
        assert results[2].server == "http://proxy2.example.com:8080"
        assert results[3].server == "http://proxy0.example.com:8080"  # wraps around

    def test_random_uses_all_proxies(self):
        proxies = [
            ProxyConfig(server=f"http://proxy{i}.example.com:8080")
            for i in range(3)
        ]
        rotator = ProxyRotator(
            proxies=proxies,
            strategy=ProxyRotationStrategy.RANDOM,
        )
        seen = set()
        for _ in range(100):
            seen.add(rotator.next().server)
        assert len(seen) == 3  # all proxies used

    def test_empty_proxies_raises(self):
        rotator = ProxyRotator(proxies=[])
        with pytest.raises(ValueError, match="No proxies"):
            rotator.next()

    def test_single_proxy(self):
        proxies = [ProxyConfig(server="http://proxy.example.com:8080")]
        rotator = ProxyRotator(proxies=proxies)
        for _ in range(5):
            assert rotator.next().server == "http://proxy.example.com:8080"


class TestLoadProxyFile:
    def test_load_valid_file(self, tmp_path):
        proxy_file = tmp_path / "proxies.txt"
        proxy_file.write_text(
            "http://proxy1.example.com:8080\n"
            "http://user:pass@proxy2.example.com:8080\n"
            "socks5://proxy3.example.com:1080\n"
        )
        proxies = load_proxy_file(proxy_file)
        assert len(proxies) == 3
        assert proxies[0].server == "http://proxy1.example.com:8080"
        assert proxies[1].username == "user"
        assert proxies[2].server == "socks5://proxy3.example.com:1080"

    def test_skips_blank_lines_and_comments(self, tmp_path):
        proxy_file = tmp_path / "proxies.txt"
        proxy_file.write_text(
            "# This is a comment\n"
            "\n"
            "http://proxy1.example.com:8080\n"
            "  \n"
            "# Another comment\n"
            "http://proxy2.example.com:8080\n"
        )
        proxies = load_proxy_file(proxy_file)
        assert len(proxies) == 2

    def test_empty_file(self, tmp_path):
        proxy_file = tmp_path / "proxies.txt"
        proxy_file.write_text("")
        proxies = load_proxy_file(proxy_file)
        assert proxies == []
