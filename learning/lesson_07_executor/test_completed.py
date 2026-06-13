from browser_agent.executor import execute_action, make_execute_node
from browser_agent.models import BrowserAction


class FakeBrowser:
    def __init__(self) -> None:
        self.calls = []
        self.current_url = "https://example.com/login"

    def fill(self, target: str, value: str) -> None:
        self.calls.append(("fill", target, value))

    def screenshot(self) -> str:
        self.calls.append(("screenshot",))
        return "artifacts/001-action.png"


def test_execute_action_dispatches_fill() -> None:
    browser = FakeBrowser()
    result = execute_action(
        browser,
        BrowserAction(
            action="fill",
            target="label=Username",
            value="standard_user",
            reason="Required",
        ),
    )
    assert result.success is True
    assert browser.calls[0] == ("fill", "label=Username", "standard_user")


def test_make_execute_node_returns_function() -> None:
    assert callable(make_execute_node(FakeBrowser()))
