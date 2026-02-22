"""Basic example: launch stealth browser and load a page."""

from cloakbrowser import launch

browser = launch(headless=False)
page = browser.new_page()

page.goto("https://example.com")
print(f"Title: {page.title()}")
print(f"URL: {page.url}")

browser.close()
print("Done!")
