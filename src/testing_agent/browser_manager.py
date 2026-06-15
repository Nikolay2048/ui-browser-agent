from __future__ import annotations

from pathlib import Path

from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright


class BrowserManager:
    _instance: BrowserManager | None = None

    def __init__(self) -> None:
        self._playwright = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None
        self._screenshots_dir: str = "screenshots"
        self._last_step_result: dict | None = None

    @classmethod
    def get_instance(cls) -> BrowserManager:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def start(self, headless: bool = False, screenshots_dir: str = "screenshots") -> None:
        self._screenshots_dir = screenshots_dir
        Path(screenshots_dir).mkdir(parents=True, exist_ok=True)

        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(
            headless=headless,
            slow_mo=350,
        )
        self._context = self._browser.new_context(
            viewport={"width": 1280, "height": 720},
        )
        self._page = self._context.new_page()
        self._page.set_default_timeout(10000)

    def stop(self) -> None:
        if self._context:
            self._context.close()
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()
        self._page = None
        self._browser = None
        self._playwright = None

    @property
    def page(self) -> Page:
        if self._page is None:
            raise RuntimeError("Browser not started. Call BrowserManager.get_instance().start() first.")
        return self._page

    @property
    def screenshots_dir(self) -> str:
        return self._screenshots_dir
