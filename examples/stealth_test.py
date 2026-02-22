"""Run stealth tests against major bot detection services.

Tests cloakbrowser against multiple detection sites and reports results.
"""

from cloakbrowser import launch

TESTS = [
    {
        "name": "bot.incolumitas.com",
        "url": "https://bot.incolumitas.com",
        "check": "Bot detection analysis",
    },
    {
        "name": "BrowserScan",
        "url": "https://www.browserscan.net/bot-detection",
        "check": "Bot detection status",
    },
    {
        "name": "deviceandbrowserinfo.com",
        "url": "https://deviceandbrowserinfo.com/are_you_a_bot",
        "check": "isBot flag",
    },
    {
        "name": "FingerprintJS",
        "url": "https://demo.fingerprint.com/web-scraping",
        "check": "Bot detection result",
    },
]

browser = launch(headless=True)
page = browser.new_page()

print("=" * 60)
print("CloakBrowser Stealth Test Suite")
print("=" * 60)

for test in TESTS:
    print(f"\n--- {test['name']} ---")
    print(f"URL: {test['url']}")
    try:
        page.goto(test["url"], wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(3000)

        # Screenshot each test
        filename = f"stealth_test_{test['name'].replace('.', '_').replace(' ', '_')}.png"
        page.screenshot(path=filename)
        print(f"Screenshot: {filename}")
        print(f"Title: {page.title()}")
    except Exception as e:
        print(f"Error: {e}")

browser.close()

print("\n" + "=" * 60)
print("Tests complete. Check screenshots for results.")
print("=" * 60)
