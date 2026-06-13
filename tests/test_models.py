import pytest
from pydantic import ValidationError

from browser_agent.models import (
    ActionResult,
    BrowserAction,
    TestCase as AgentTestCase,
)


def test_valid_test_case() -> None:
    case = AgentTestCase(
        id="todo-create",
        name="Create a todo",
        start_url="https://demo.playwright.dev/todomvc/",
        goal="Create task Learn LangGraph",
        test_data={"task": "Learn LangGraph"},
        expected=["Learn LangGraph is visible"],
    )

    assert case.max_steps == 20
    assert case.test_data["task"] == "Learn LangGraph"


def test_test_case_rejects_invalid_limits() -> None:
    with pytest.raises(ValidationError):
        AgentTestCase(
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
def test_valid_browser_actions(
    action: str,
    target: str | None,
    value: str | None,
) -> None:
    browser_action = BrowserAction(
        action=action,
        target=target,
        value=value,
        reason="Required by the scenario",
    )

    assert browser_action.action == action


@pytest.mark.parametrize(
    "payload",
    [
        {"action": "click", "reason": "Missing target"},
        {"action": "fill", "target": "label=Username", "reason": "Missing value"},
        {"action": "unknown", "target": "body", "reason": "Unknown action"},
    ],
)
def test_browser_action_rejects_invalid_contract(payload: dict[str, str]) -> None:
    with pytest.raises(ValidationError):
        BrowserAction.model_validate(payload)


def test_action_result() -> None:
    result = ActionResult(
        success=True,
        url_before="https://example.com/login",
        url_after="https://example.com/products",
        error=None,
        screenshot_path="artifacts/001-login.png",
    )

    assert result.success is True
    assert result.error is None
