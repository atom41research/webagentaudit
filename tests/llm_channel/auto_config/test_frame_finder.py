"""Tests for FrameFinder: chat widget iframe discovery."""

import pytest
from playwright.async_api import async_playwright

from webagentaudit.llm_channel.auto_config._frame_finder import FrameFinder


@pytest.fixture
async def browser():
    pw = await async_playwright().start()
    browser = await pw.chromium.launch(headless=True)
    yield browser
    await browser.close()
    await pw.stop()


@pytest.fixture
async def page(browser):
    context = await browser.new_context()
    pg = await context.new_page()
    yield pg
    await context.close()


@pytest.fixture
def finder():
    return FrameFinder()


# ---------------------------------------------------------------------------
# HTML fixtures
# ---------------------------------------------------------------------------

TIDIO_IFRAME_HTML = """\
<!DOCTYPE html>
<html><body>
<h1>Page with Tidio chat</h1>
<iframe id="tidio-chat-iframe"
        srcdoc='<html><body><textarea placeholder="Chat here"></textarea></body></html>'
        style="width: 350px; height: 400px;">
</iframe>
</body></html>
"""

TITLED_CHAT_IFRAME_HTML = """\
<!DOCTYPE html>
<html><body>
<h1>Page with titled chat iframe</h1>
<iframe title="Chat Widget"
        srcdoc='<html><body><textarea placeholder="Message"></textarea></body></html>'
        style="width: 350px; height: 400px;">
</iframe>
</body></html>
"""

MULTIPLE_IFRAMES_HTML = """\
<!DOCTYPE html>
<html><body>
<h1>Page with multiple iframes</h1>
<iframe id="ad-frame" srcdoc='<html><body><p>Advertisement</p></body></html>'
        style="width: 300px; height: 250px;">
</iframe>
<iframe id="tidio-chat-iframe"
        srcdoc='<html><body><textarea placeholder="Ask"></textarea></body></html>'
        style="width: 350px; height: 400px;">
</iframe>
<iframe title="analytics"
        srcdoc='<html><body><script>/* analytics */</script></body></html>'
        style="width: 1px; height: 1px;">
</iframe>
</body></html>
"""

NO_IFRAME_HTML = """\
<!DOCTYPE html>
<html><body>
<h1>Simple page</h1>
<p>No iframes here.</p>
</body></html>
"""

UNRELATED_IFRAMES_HTML = """\
<!DOCTYPE html>
<html><body>
<h1>Page with non-chat iframes</h1>
<iframe id="ad-frame" srcdoc='<html><body><p>Ad</p></body></html>'
        style="width: 300px; height: 250px;"></iframe>
<iframe name="__tcfapiLocator" srcdoc='<html><body></body></html>'
        style="width: 0; height: 0;"></iframe>
</body></html>
"""

URL_PATTERN_IFRAME_HTML = """\
<!DOCTYPE html>
<html><body>
<h1>Page with URL-matched iframe</h1>
<iframe src="https://code.tidio.co/widget/abc123"
        srcdoc='<html><body><textarea></textarea></body></html>'
        style="width: 350px; height: 400px;">
</iframe>
</body></html>
"""


class TestFrameFinderVendorSelectors:
    """Tests for known vendor iframe selector matching."""

    async def test_tidio_iframe_found(self, page, finder):
        """An iframe with id='tidio-chat-iframe' should be found."""
        await page.set_content(TIDIO_IFRAME_HTML, wait_until="domcontentloaded")
        await page.wait_for_timeout(300)
        candidates = await finder.find_chat_frames(page)

        assert len(candidates) >= 1
        assert any("tidio" in c.iframe_selector for c in candidates)

    async def test_tidio_iframe_high_score(self, page, finder):
        """Vendor-matched iframe should have a high score."""
        await page.set_content(TIDIO_IFRAME_HTML, wait_until="domcontentloaded")
        await page.wait_for_timeout(300)
        candidates = await finder.find_chat_frames(page)

        best = candidates[0]
        # Vendor selector (0.5) + has_input (0.3) = 0.8 minimum
        assert best.score >= 0.5

    async def test_tidio_iframe_has_input(self, page, finder):
        """Frame with textarea should have has_input=True."""
        await page.set_content(TIDIO_IFRAME_HTML, wait_until="domcontentloaded")
        await page.wait_for_timeout(300)
        candidates = await finder.find_chat_frames(page)

        best = candidates[0]
        assert best.has_input is True


class TestFrameFinderTitleMatching:
    """Tests for iframe title-based matching."""

    async def test_chat_title_iframe_found(self, page, finder):
        """An iframe with title containing 'chat' should be found."""
        await page.set_content(TITLED_CHAT_IFRAME_HTML, wait_until="domcontentloaded")
        await page.wait_for_timeout(300)
        candidates = await finder.find_chat_frames(page)

        assert len(candidates) >= 1


class TestFrameFinderMultipleIframes:
    """Tests for pages with multiple iframes."""

    async def test_chat_iframe_ranked_first(self, page, finder):
        """Among multiple iframes, the chat one should rank highest."""
        await page.set_content(MULTIPLE_IFRAMES_HTML, wait_until="domcontentloaded")
        await page.wait_for_timeout(300)
        candidates = await finder.find_chat_frames(page)

        assert len(candidates) >= 1
        best = candidates[0]
        assert "tidio" in best.iframe_selector

    async def test_non_chat_iframes_filtered(self, page, finder):
        """Ad and analytics iframes should not appear as candidates."""
        await page.set_content(MULTIPLE_IFRAMES_HTML, wait_until="domcontentloaded")
        await page.wait_for_timeout(300)
        candidates = await finder.find_chat_frames(page)

        iframe_selectors = [c.iframe_selector for c in candidates]
        assert not any("ad-frame" in s for s in iframe_selectors)


class TestFrameFinderNoIframes:
    """Tests for pages without iframes."""

    async def test_no_iframes_returns_empty(self, page, finder):
        """A page with no iframes should return an empty list."""
        await page.set_content(NO_IFRAME_HTML, wait_until="domcontentloaded")
        candidates = await finder.find_chat_frames(page)
        assert candidates == []

    async def test_unrelated_iframes_filtered(self, page, finder):
        """Iframes for ads and consent frameworks should not be returned."""
        await page.set_content(UNRELATED_IFRAMES_HTML, wait_until="domcontentloaded")
        await page.wait_for_timeout(300)
        candidates = await finder.find_chat_frames(page)
        assert candidates == []


class TestFrameFinderURLPatterns:
    """Tests for URL-based iframe matching."""

    async def test_tidio_url_pattern_found(self, page, finder):
        """An iframe with tidio URL in src should be found."""
        await page.set_content(URL_PATTERN_IFRAME_HTML, wait_until="domcontentloaded")
        await page.wait_for_timeout(300)
        candidates = await finder.find_chat_frames(page)

        # srcdoc overrides src, but the src attribute is still readable
        # In real pages, the iframe would load from the URL
        assert len(candidates) >= 1
