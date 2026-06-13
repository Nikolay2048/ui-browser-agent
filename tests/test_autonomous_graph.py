from langchain_core.runnables import RunnableLambda

from browser_agent.autonomous_graph import (
    build_autonomous_graph,
    route_after_execution,
    route_planned_action,
)
from browser_agent.models import (
    ActionResult,
    BrowserAction,
    TestCase as AgentTestCase,
)


class SnapshotAwareModel:
    def with_structured_output(self, schema):
        def respond(prompt_value):
            rendered = "\n".join(
                str(message.content) for message in prompt_value.to_messages()
            )
            if "Goal reached" in rendered:
                return BrowserAction(
                    action="finish",
                    target=None,
                    value=None,
                    reason="The page confirms that the goal is reached.",
                )
            return BrowserAction(
                action="click",
                target='button "Continue"',
                value=None,
                reason="The Continue button advances the scenario.",
            )

        return RunnableLambda(respond)


class StatefulFakeBrowser:
    def __init__(self, fail_click: bool = False) -> None:
        self.current_url = "https://example.com/start"
        self.goal_reached = False
        self.fail_click = fail_click
        self.calls = []

    def snapshot(self) -> str:
        self.calls.append(("snapshot",))
        if self.goal_reached:
            return "Goal reached"
        return '- button "Continue"'

    def click(self, target: str) -> None:
        self.calls.append(("click", target))
        if self.fail_click:
            raise RuntimeError("Button is blocked")
        self.goal_reached = True
        self.current_url = "https://example.com/done"

    def screenshot(self) -> str:
        self.calls.append(("screenshot",))
        return "artifacts/step.png"


def make_state(
    action: BrowserAction,
    result: ActionResult | None = None,
    step_count: int = 0,
    max_steps: int = 3,
) -> dict:
    state = {
        "test_case": AgentTestCase(
            id="autonomous",
            name="Autonomous loop",
            start_url="https://example.com/start",
            goal="Reach the done page",
            max_steps=max_steps,
        ),
        "proposed_action": action,
        "step_count": step_count,
        "status": "running",
    }
    if result is not None:
        state["last_result"] = result
    return state


def test_route_planned_action_distinguishes_finish() -> None:
    finish = BrowserAction(
        action="finish",
        target=None,
        value=None,
        reason="Done",
    )
    click = BrowserAction(
        action="click",
        target='button "Continue"',
        value=None,
        reason="Continue",
    )

    assert route_planned_action(make_state(finish)) == "pass_run"
    assert route_planned_action(make_state(click)) == "execute"


def test_route_after_execution_handles_result_and_limit() -> None:
    action = BrowserAction(
        action="click",
        target='button "Continue"',
        value=None,
        reason="Continue",
    )
    success = ActionResult(
        success=True,
        url_before="https://example.com/start",
        url_after="https://example.com/next",
    )
    failure = ActionResult(
        success=False,
        url_before="https://example.com/start",
        url_after="https://example.com/start",
        error="Blocked",
    )

    assert route_after_execution(make_state(action, success, step_count=1)) == "observe"
    assert route_after_execution(make_state(action, failure, step_count=1)) == "fail_run"
    assert (
        route_after_execution(make_state(action, success, step_count=3, max_steps=3))
        == "fail_run"
    )


def test_autonomous_graph_observes_until_model_finishes() -> None:
    browser = StatefulFakeBrowser()
    graph = build_autonomous_graph(SnapshotAwareModel(), browser)
    case = make_state(
        BrowserAction(
            action="finish",
            target=None,
            value=None,
            reason="Unused",
        )
    )["test_case"]

    result = graph.invoke({"test_case": case})

    assert result["status"] == "passed"
    assert result["step_count"] == 1
    assert result["current_url"] == "https://example.com/done"
    assert browser.calls == [
        ("snapshot",),
        ("click", 'button "Continue"'),
        ("screenshot",),
        ("snapshot",),
    ]


def test_autonomous_graph_fails_after_browser_error() -> None:
    browser = StatefulFakeBrowser(fail_click=True)
    graph = build_autonomous_graph(SnapshotAwareModel(), browser)
    case = AgentTestCase(
        id="autonomous-failure",
        name="Autonomous failure",
        start_url="https://example.com/start",
        goal="Reach the done page",
    )

    result = graph.invoke({"test_case": case})

    assert result["status"] == "failed"
    assert result["step_count"] == 1
    assert result["last_result"].error == "Button is blocked"
