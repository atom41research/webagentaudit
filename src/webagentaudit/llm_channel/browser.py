"""Browser compatibility helpers for web-based LLM channels."""

_CHROMIUM_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/{version} Safari/537.36"
)


def effective_user_agent(
    browser: str,
    *,
    headless: bool,
    configured: str | None = None,
    browser_version: str | None = None,
) -> str | None:
    """Return a usable UA while preserving explicit and headed settings."""
    if configured:
        return configured
    if browser != "chromium" or not headless:
        return None
    return _CHROMIUM_USER_AGENT.format(version=browser_version or "120.0.0.0")
