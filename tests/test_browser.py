from pathlib import Path

import pytest

from browser_agent.browser import PlaywrightBrowser


class FakeLocator:
    def __init__(self, calls: list) -> None:
        self.calls = calls

    def click(self) -> None:
        self.calls.append(("click",))

    def fill(self, value: str) -> None:
        self.calls.append(("fill", value))

    def press(self, value: str) -> None:
        self.calls.append(("press", value))

    def wait_for(self, **kwargs) -> None:
        self.calls.append(("wait_for", kwargs))

    def aria_snapshot(self) -> str:
        self.calls.append(("aria_snapshot",))
        return '- textbox "Task"\n- button "Add"'


class FakePage:
    def __init__(self) -> None:
        self.url = "about:blank"
        self.calls = []
        self.locator_result = FakeLocator(self.calls)

    def goto(self, url: str) -> None:
        self.calls.append(("goto", url))
        self.url = url

    def get_by_role(self, role: str, **kwargs):
        self.calls.append(("get_by_role", role, kwargs))
        return self.locator_result

    def get_by_label(self, label: str):
        self.calls.append(("get_by_label", label))
        return self.locator_result

    def get_by_text(self, text: str, **kwargs):
        self.calls.append(("get_by_text", text, kwargs))
        return self.locator_result

    def locator(self, selector: str):
        self.calls.append(("locator", selector))
        return self.locator_result

    def screenshot(self, **kwargs) -> None:
        self.calls.append(("screenshot", kwargs))


def test_current_url_and_open_delegate_to_page() -> None:
    page = FakePage()
    browser = PlaywrightBrowser(page)

    browser.open("https://example.com")

    assert browser.current_url == "https://example.com"
    assert page.calls == [("goto", "https://example.com")]


@pytest.mark.parametrize(
    ("target", "expected_call"),
    [
        (
            'role=button[name="Add"]',
            ("get_by_role", "button", {"name": "Add", "exact": True}),
        ),
        ("label=Task", ("get_by_label", "Task")),
        ("text=Saved", ("get_by_text", "Saved", {"exact": True})),
        ("css=.todo-list li", ("locator", ".todo-list li")),
    ],
)
def test_resolve_target_supports_locator_language(
    target: str,
    expected_call: tuple,
) -> None:
    page = FakePage()
    browser = PlaywrightBrowser(page)

    locator = browser._resolve_target(target)

    assert locator is page.locator_result
    assert page.calls == [expected_call]


def test_resolve_target_rejects_unknown_syntax() -> None:
    browser = PlaywrightBrowser(FakePage())

    with pytest.raises(ValueError, match="Unsupported target"):
        browser._resolve_target('button "Add"')


def test_snapshot_uses_body_accessibility_tree() -> None:
    page = FakePage()
    browser = PlaywrightBrowser(page)

    snapshot = browser.snapshot()

    assert snapshot == '- textbox "Task"\n- button "Add"'
    assert page.calls == [
        ("locator", "body"),
        ("aria_snapshot",),
    ]


def test_actions_use_resolved_locator() -> None:
    page = FakePage()
    browser = PlaywrightBrowser(page)

    browser.click('role=button[name="Add"]')
    browser.fill("label=Task", "Learn Playwright")
    browser.press("label=Task", "Enter")
    browser.assert_text("text=Learn Playwright")

    assert ("click",) in page.calls
    assert ("fill", "Learn Playwright") in page.calls
    assert ("press", "Enter") in page.calls
    assert ("wait_for", {"state": "visible"}) in page.calls


def test_screenshot_creates_directory_and_numbered_paths(tmp_path: Path) -> None:
    page = FakePage()
    artifacts_dir = tmp_path / "screenshots"
    browser = PlaywrightBrowser(page, artifacts_dir=artifacts_dir)

    first_path = browser.screenshot()
    second_path = browser.screenshot()

    assert artifacts_dir.is_dir()
    assert Path(first_path).name == "step-001.png"
    assert Path(second_path).name == "step-002.png"
    screenshot_calls = [call for call in page.calls if call[0] == "screenshot"]
    assert screenshot_calls == [
        ("screenshot", {"path": first_path, "full_page": True}),
        ("screenshot", {"path": second_path, "full_page": True}),
    ]
