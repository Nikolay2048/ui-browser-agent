"""Playwright browser adapter completed in lesson 12."""

import re
from pathlib import Path


class PlaywrightBrowser:
    def __init__(self, page, artifacts_dir: str | Path = "artifacts") -> None:
        self.page = page
        self.artifacts_dir = Path(artifacts_dir)
        self.screenshot_number = 0

    @property
    def current_url(self) -> str:
        return self.page.url

    def open(self, url: str) -> None:
        self.page.goto(url)

    def _resolve_target(self, target: str):
        match = re.fullmatch(
            r'role=([A-Za-z0-9_-]+)\[name="([^"]+)"\]',
            target,
        )
        if match:
            return self.page.get_by_role(
                match.group(1),
                name=match.group(2),
                exact=True,
            )
        if target.startswith("label="):
            return self.page.get_by_label(target.removeprefix("label="))
        if target.startswith("text="):
            return self.page.get_by_text(
                target.removeprefix("text="),
                exact=True,
            )
        if target.startswith("css="):
            return self.page.locator(target.removeprefix("css="))
        raise ValueError(f"Unsupported target: {target}")

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
