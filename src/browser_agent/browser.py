"""Playwright adapter used by the browser testing agent.

Implement the TODOs from learning/lesson_12_playwright_adapter/README.md.
Keep LangGraph and LLM logic out of this module.
"""

from pathlib import Path


class PlaywrightBrowser:
    """Translate agent browser operations into Playwright calls."""

    def __init__(self, page, artifacts_dir: str | Path = "artifacts") -> None:
        self.page = page
        self.artifacts_dir = Path(artifacts_dir)
        self.screenshot_number = 0

    @property
    def current_url(self) -> str:
        """Return the URL currently loaded by Playwright."""
        raise NotImplementedError

    def open(self, url: str) -> None:
        """Navigate to the test case start URL."""
        raise NotImplementedError

    def _resolve_target(self, target: str):
        """Convert the agent target language into a Playwright locator."""
        raise NotImplementedError

    def snapshot(self) -> str:
        """Return a model-friendly accessibility snapshot of the page."""
        raise NotImplementedError

    def click(self, target: str) -> None:
        """Click the resolved target."""
        raise NotImplementedError

    def fill(self, target: str, value: str) -> None:
        """Fill the resolved target."""
        raise NotImplementedError

    def press(self, target: str, value: str) -> None:
        """Press a key on the resolved target."""
        raise NotImplementedError

    def assert_text(self, target: str) -> None:
        """Wait until the resolved text target is visible."""
        raise NotImplementedError

    def screenshot(self) -> str:
        """Save a numbered screenshot and return its path."""
        raise NotImplementedError
