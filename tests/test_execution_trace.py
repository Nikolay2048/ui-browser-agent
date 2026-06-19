import pytest
from pydantic import ValidationError

from browser_agent.executor import make_execute_node
from browser_agent.models import (
    ActionResult,
    BrowserAction,
    BrowserTarget,
    ExecutionStep,
    TestCase as AgentTestCase,
)


class FakeBrowser:
    def __init__(self) -> None:
        self.current_url = "https://example.com/start"

    def click(self, _target: str) -> None:
        self.current_url = "https://example.com/next"

    def screenshot(self) -> str:
        return "artifacts/step.png"


def make_action() -> BrowserAction:
    return BrowserAction(
        action="click",
        target=BrowserTarget(strategy="role", value="button", name="Continue"),
        value=None,
        reason="Continue to the next page.",
    )


def make_result() -> ActionResult:
    return ActionResult(
        success=True,
        url_before="https://example.com/start",
        url_after="https://example.com/next",
        screenshot_path="artifacts/step.png",
    )


def make_state(route: list[ExecutionStep] | None = None) -> dict:
    return {
        "test_case": AgentTestCase(
            id="trace",
            name="Record execution trace",
            start_url="https://example.com/start",
            goal="Reach the next page",
        ),
        "current_url": "https://example.com/start",
        "route": [] if route is None else route,
        "step_count": len(route or []),
        "failure_count": 0,
        "status": "running",
        "page_snapshot": '- button "Continue"',
        "proposed_action": make_action(),
    }


def test_execution_step_model_keeps_complete_context() -> None:
    step = ExecutionStep(
        step_number=1,
        page_snapshot='- button "Continue"',
        action=make_action(),
        result=make_result(),
    )

    assert step.step_number == 1
    assert step.page_snapshot == '- button "Continue"'
    assert step.action.reason == "Continue to the next page."
    assert step.result.url_after == "https://example.com/next"


def test_execution_step_model_rejects_zero_number() -> None:
    with pytest.raises(ValidationError):
        ExecutionStep(
            step_number=0,
            page_snapshot='- button "Continue"',
            action=make_action(),
            result=make_result(),
        )


def test_execute_node_adds_complete_step_to_route() -> None:
    node = make_execute_node(FakeBrowser())

    update = node(make_state())

    assert update["step_count"] == 1
    assert len(update["route"]) == 1
    step = update["route"][0]
    assert step.step_number == 1
    assert step.page_snapshot == '- button "Continue"'
    assert step.action == make_action()
    assert step.result == update["last_result"]


def test_execute_node_preserves_previous_route_without_mutation() -> None:
    previous_step = ExecutionStep(
        step_number=1,
        page_snapshot='- button "Start"',
        action=make_action(),
        result=make_result(),
    )
    original_route = [previous_step]
    state = make_state(original_route)
    node = make_execute_node(FakeBrowser())

    update = node(state)

    assert state["route"] is original_route
    assert state["route"] == [previous_step]
    assert update["route"] is not original_route
    assert [step.step_number for step in update["route"]] == [1, 2]
