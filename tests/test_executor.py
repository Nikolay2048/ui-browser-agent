from browser_agent.executor import execute_action, make_execute_node
from browser_agent.models import ActionResult, BrowserAction, TestCase as AgentTestCase


class FakeBrowser:
    def __init__(self) -> None:
        self.calls = []
        self.current_url = "https://example.com/login"

    def click(self, target: str) -> None:
        self.calls.append(("click", target))

    def fill(self, target: str, value: str) -> None:
        self.calls.append(("fill", target, value))

    def press(self, target: str, value: str) -> None:
        self.calls.append(("press", target, value))

    def assert_text(self, target: str) -> None:
        self.calls.append(("assert_text", target))

    def screenshot(self) -> str:
        self.calls.append(("screenshot",))
        return "artifacts/001-action.png"


def make_action(action: str, target=None, value=None) -> BrowserAction:
    return BrowserAction(
        action=action,
        target=target,
        value=value,
        reason="Required by the scenario.",
    )


def make_state(action: BrowserAction) -> dict:
    return {
        "test_case": AgentTestCase(
            id="executor",
            name="Learn executor",
            start_url="https://example.com/login",
            goal="Execute one browser action",
        ),
        "current_url": "https://example.com/login",
        "route": [],
        "step_count": 0,
        "status": "running",
        "page_snapshot": '- button "Login"',
        "proposed_action": action,
    }


def test_execute_action_dispatches_fill() -> None:
    browser = FakeBrowser()

    result = execute_action(
        browser,
        make_action("fill", target="label=Username", value="standard_user"),
    )

    assert browser.calls == [
        ("fill", "label=Username", "standard_user"),
        ("screenshot",),
    ]
    assert result == ActionResult(
        success=True,
        url_before="https://example.com/login",
        url_after="https://example.com/login",
        screenshot_path="artifacts/001-action.png",
    )


def test_execute_action_converts_browser_error_to_result() -> None:
    class FailingBrowser(FakeBrowser):
        def click(self, target: str) -> None:
            raise RuntimeError("Element not found")

    result = execute_action(
        FailingBrowser(),
        make_action("click", target='button "Missing"'),
    )

    assert result.success is False
    assert result.error == "Element not found"
    assert result.screenshot_path == "artifacts/001-action.png"


def test_execute_node_returns_partial_update() -> None:
    browser = FakeBrowser()
    node = make_execute_node(browser)

    update = node(
        make_state(make_action("click", target='button "Login"'))
    )

    assert list(update) == ["last_result", "step_count", "route"]
    assert update["last_result"].success is True
    assert update["step_count"] == 1
