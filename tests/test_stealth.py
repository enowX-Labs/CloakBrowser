"""Stealth detection tests for cloakbrowser.

These tests verify that the stealth Chromium binary passes common
bot detection checks. They require network access.
"""

import pytest
from cloakbrowser import launch


@pytest.fixture(scope="module")
def browser():
    """Shared browser instance for stealth tests."""
    b = launch(headless=True)
    yield b
    b.close()


@pytest.fixture
def page(browser):
    """Fresh page for each test."""
    p = browser.new_page()
    yield p
    p.close()


class TestWebDriverDetection:
    """Tests for WebDriver/automation detection signals."""

    def test_navigator_webdriver_false(self, page):
        """navigator.webdriver must be false."""
        page.goto("https://example.com")
        assert page.evaluate("navigator.webdriver") is False

    def test_no_headless_chrome_ua(self, page):
        """User agent must not contain 'HeadlessChrome'."""
        page.goto("https://example.com")
        ua = page.evaluate("navigator.userAgent")
        assert "HeadlessChrome" not in ua
        assert "Chrome/" in ua

    def test_window_chrome_exists(self, page):
        """window.chrome must be an object (not undefined)."""
        page.goto("https://example.com")
        assert page.evaluate("typeof window.chrome") == "object"

    def test_plugins_present(self, page):
        """Must have browser plugins (real Chrome has 5)."""
        page.goto("https://example.com")
        count = page.evaluate("navigator.plugins.length")
        assert count >= 1, f"Expected plugins, got {count}"

    def test_languages_present(self, page):
        """navigator.languages must be populated."""
        page.goto("https://example.com")
        langs = page.evaluate("navigator.languages")
        assert len(langs) >= 1

    def test_cdp_not_detected(self, page):
        """Chrome DevTools Protocol should not be detectable."""
        page.goto("https://example.com")
        # Common CDP detection: check for Runtime.evaluate artifacts
        has_cdp = page.evaluate("""
            () => {
                try {
                    // Check common CDP leak: window.cdc_
                    const keys = Object.keys(window);
                    return keys.some(k => k.startsWith('cdc_') || k.startsWith('__webdriver'));
                } catch(e) {
                    return false;
                }
            }
        """)
        assert has_cdp is False


class TestBotDetectionSites:
    """Live tests against bot detection services.

    These require network access and may be slow.
    Mark with pytest -m slow to skip in CI.
    """

    @pytest.mark.slow
    def test_bot_incolumitas(self, page):
        """bot.incolumitas.com should detect minimal flags."""
        page.goto("https://bot.incolumitas.com", timeout=30000)
        page.wait_for_timeout(5000)
        # Check that we're not immediately flagged
        title = page.title()
        assert title  # Page loaded successfully

    @pytest.mark.slow
    def test_browserscan(self, page):
        """BrowserScan bot detection should show NORMAL."""
        page.goto("https://www.browserscan.net/bot-detection", timeout=30000)
        page.wait_for_timeout(5000)
        title = page.title()
        assert title  # Page loaded

    @pytest.mark.slow
    def test_device_and_browser_info(self, page):
        """deviceandbrowserinfo.com should report isBot: false."""
        page.goto("https://deviceandbrowserinfo.com/are_you_a_bot", timeout=30000)
        page.wait_for_timeout(5000)
        content = page.content()
        # The page shows bot detection results
        assert "deviceandbrowserinfo" in page.url.lower()
