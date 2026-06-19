from langchain_core.runnables import RunnableLambda

from browser_agent.executor import make_execute_node
from browser_agent.graph import build_agent_graph, initialize, route_after_execution
from browser_agent.models import (
    ActionResult,
    BrowserAction,
    BrowserTarget,
    ExpectedResultCheck,
    JudgeVerdict,
    TestCase as AgentTestCase,
)


def make_case(max_failures: int = 2) -> AgentTestCase:
    return AgentTestCase(
        id="recovery",
        name="Recover from one action failure",
        start_url="https://example.com/start",
        goal="Reach the done state",
        expected=["Done is visible"],
        max_steps=5,
        max_failures=max_failures,
    )


def make_action(name: str = "Primary") -> BrowserAction:
    return BrowserAction(
        action="click",
        target=BrowserTarget(strategy="role", value="button", name=name),
        value=None,
        reason="Try the available route.",
    )


def make_router_state(
    *,
    success: bool,
    step_count: int,
    failure_count: int,
    max_failures: int = 2,
) -> dict:
    return {
        "test_case": make_case(max_failures=max_failures),
        "last_result": ActionResult(
            success=success,
            url_before="https://example.com/start",
            url_after="https://example.com/start",
            error=None if success else "Primary button is blocked",
        ),
        "step_count": step_count,
        "failure_count": failure_count,
    }


def test_initialize_starts_with_zero_failures() -> None:
    update = initialize({"test_case": make_case()})

    assert update["failure_count"] == 0


def test_execute_node_counts_failed_actions() -> None:
    class FailingBrowser:
        current_url = "https://example.com/start"

        def click(self, _target) -> None:
            raise RuntimeError("Primary button is blocked")

        def screenshot(self) -> str:
            return "artifacts/failure.png"

    node = make_execute_node(FailingBrowser())
    update = node(
        {
            "test_case": make_case(),
            "page_snapshot": '- button "Primary"',
            "proposed_action": make_action(),
            "route": [],
            "step_count": 0,
            "failure_count": 0,
            "status": "running",
        }
    )

    assert update["last_result"].success is False
    assert update["step_count"] == 1
    assert update["failure_count"] == 1


def test_route_recovers_before_failure_budget_is_exhausted() -> None:
    assert (
        route_after_execution(
            make_router_state(
                success=False,
                step_count=1,
                failure_count=1,
                max_failures=2,
            )
        )
        == "observe"
    )


def test_route_fails_when_failure_budget_is_exhausted() -> None:
    assert (
        route_after_execution(
            make_router_state(
                success=False,
                step_count=2,
                failure_count=2,
                max_failures=2,
            )
        )
        == "fail_run"
    )


class RecoveryModel:
    def with_structured_output(self, schema):
        def respond(prompt_value):
            rendered = "\n".join(
                str(message.content) for message in prompt_value.to_messages()
            )
            if schema is JudgeVerdict:
                return JudgeVerdict(
                    passed=True,
                    checks=[
                        ExpectedResultCheck(
                            expected="Done is visible",
                            passed=True,
                            evidence='Snapshot contains status "Done".',
                        )
                    ],
                    summary="The expected done state is visible.",
                )
            if 'status "Done"' in rendered:
                return BrowserAction(
                    action="finish",
                    target=None,
                    value=None,
                    reason="The goal is reached.",
                )
            if "Primary button is blocked" in rendered:
                return make_action("Alternative")
            return make_action("Primary")

        return RunnableLambda(respond)


class RecoveringBrowser:
    def __init__(self) -> None:
        self.current_url = "https://example.com/start"
        self.done = False
        self.clicks = []

    def snapshot(self) -> str:
        if self.done:
            return '- status "Done"'
        return '- button "Primary"\n- button "Alternative"'

    def click(self, target: BrowserTarget) -> None:
        self.clicks.append(target.name)
        if target.name == "Primary":
            raise RuntimeError("Primary button is blocked")
        self.done = True

    def screenshot(self) -> str:
        return "artifacts/recovery.png"


def test_graph_replans_and_recovers_after_first_failure() -> None:
    browser = RecoveringBrowser()
    graph = build_agent_graph(RecoveryModel(), browser)

    result = graph.invoke({"test_case": make_case()})

    assert result["status"] == "passed"
    assert result["failure_count"] == 1
    assert result["step_count"] == 2
    assert [step.result.success for step in result["route"]] == [False, True]
    assert browser.clicks == ["Primary", "Alternative"]
