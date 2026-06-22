import pytest
from pydantic import ValidationError

from browser_agent.domain import ActionResult, BrowserAction, TestCase


def test_valid_test_case() -> None:
    case = TestCase(
        id="todo-create",
        name="Create a todo",
        start_url="https://demo.playwright.dev/todomvc/",
        goal="Create task Learn LangGraph",
        test_data={"task": "Learn LangGraph"},
        expected=["Learn LangGraph is visible"],
    )
    assert case.max_steps == 20


def test_test_case_rejects_invalid_limits() -> None:
    with pytest.raises(ValidationError):
        TestCase(
            id="invalid",
            name="Invalid",
            start_url="https://example.com",
            goal="Do something",
            max_steps=0,
        )


@pytest.mark.parametrize(
    ("action", "target", "value"),
    [
        ("click", 'role=button[name="Login"]', None),
        ("fill", "label=Username", "standard_user"),
        ("press", "label=Username", "Enter"),
        ("assert_text", "text=Products", None),
        ("finish", None, None),
    ],
)
def test_valid_browser_actions(action, target, value) -> None:
    result = BrowserAction(
        action=action,
        target=target,
        value=value,
        reason="Required by the scenario",
    )
    assert result.action == action


def test_action_result() -> None:
    result = ActionResult(
        success=True,
        url_before="https://example.com/login",
        url_after="https://example.com/products",
    )
    assert result.success is True
