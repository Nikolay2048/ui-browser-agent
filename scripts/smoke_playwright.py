"""Manual visible-browser check for lesson 12."""

from pathlib import Path
import sys

from playwright.sync_api import sync_playwright

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from browser_agent.browser import PlaywrightBrowser
from browser_agent.models import BrowserTarget


def main() -> None:
    fixture_url = (
        PROJECT_ROOT / "examples" / "playwright_fixture.html"
    ).resolve().as_uri()

    with sync_playwright() as playwright:
        chromium = playwright.chromium.launch(
            headless=False,
            slow_mo=500,
        )
        page = chromium.new_page()
        browser = PlaywrightBrowser(
            page,
            artifacts_dir=PROJECT_ROOT / "artifacts",
        )

        browser.open(fixture_url)
        print("\nINITIAL SNAPSHOT\n")
        print(browser.snapshot())

        browser.fill(
            BrowserTarget(strategy="label", value="Task"),
            "Learn Playwright",
        )
        browser.click(
            BrowserTarget(strategy="role", value="button", name="Add"),
        )
        browser.assert_text(
            BrowserTarget(strategy="text", value="Learn Playwright"),
        )

        print("\nFINAL SNAPSHOT\n")
        print(browser.snapshot())
        print(f"\nScreenshot: {browser.screenshot()}")
        input("\nPress Enter to close Chromium...")

        chromium.close()


if __name__ == "__main__":
    main()
