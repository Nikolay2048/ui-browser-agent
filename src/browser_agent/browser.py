"""Playwright adapter used by the browser testing agent."""

import re
from pathlib import Path

from browser_agent.domain import BrowserTargetStrategy, BrowserTarget


class PlaywrightBrowser:
    """Translate agent browser operations into Playwright calls."""

    def __init__(self, page, artifacts_dir: str | Path = "artifacts") -> None:
        self.page = page
        self.artifacts_dir = Path(artifacts_dir)
        self.screenshot_number = 0

    @property
    def current_url(self) -> str:
        return self.page.url

    def open(self, url: str) -> None:
        self.page.goto(url)

    def _resolve_target(self, target: BrowserTarget):
        if not isinstance(target, BrowserTarget):
            raise TypeError("target must be BrowserTarget")

        match target.strategy:
            case BrowserTargetStrategy.ROLE:
                return self.page.get_by_role(
                    target.value,
                    name=target.name,
                    exact=True,
                )

            case BrowserTargetStrategy.LABEL:
                return self.page.get_by_label(target.value)

            case BrowserTargetStrategy.TEXT:
                return self.page.get_by_text(target.value, exact=True)

            case BrowserTargetStrategy.CSS:
                return self.page.locator(target.value)

    def snapshot(self) -> str:
        return self.page.locator("body").aria_snapshot()

    def click(self, target: str) -> None:
        self._resolve_target(target).click()

    def fill(self, target: str, value: str) -> None:
        self._resolve_target(target).fill(value)

    def press(self, target: str, value: str) -> None:
        self._resolve_target(target).press(value)

    def assert_text(self, target: str) -> None:
        self._resolve_target(target).wait_for(state="visible")

    def screenshot(self) -> str:
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.screenshot_number += 1

        path = self.artifacts_dir / f"step-{self.screenshot_number:03d}.png"
        self.page.screenshot(path=str(path), full_page=True)

        return str(path)