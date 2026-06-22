from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command
from langchain_core.runnables import RunnableLambda

from browser_agent.graph import build_agent_graph
from browser_agent.domain import (
    BrowserAction,
    BrowserTarget,
    BrowserTargetStrategy,
    ExpectedResultCheck,
    JudgeVerdict,
    TerminationKind,
    TestCase as AgentTestCase,
)
from browser_agent.persistence import build_thread_config


class ApprovalModel:
    def with_structured_output(self, schema):
        def respond(_prompt):
            if schema is JudgeVerdict:
                return JudgeVerdict(
                    passed=True,
                    checks=[
                        ExpectedResultCheck(
                            expected="Action completed",
                            passed=True,
                            evidence="The final snapshot contains completed.",
                        )
                    ],
                    summary="The action completed.",
                )
            if not browser.completed:
                return BrowserAction(
                    action="click",
                    target=BrowserTarget(
                        strategy=BrowserTargetStrategy.ROLE,
                        value="button",
                        name="Run",
                    ),
                    value=None,
                    reason="Execute the test action.",
                )
            return BrowserAction(
                action="finish",
                target=None,
                value=None,
                reason="The expected state is visible.",
            )

        return RunnableLambda(respond)


class ApprovalBrowser:
    def __init__(self) -> None:
        self.current_url = "https://example.com"
        self.completed = False
        self.click_count = 0

    def snapshot(self) -> str:
        if self.completed:
            return 'status "completed"'
        return '- button "Run"'

    def click(self, _target: str) -> None:
        self.click_count += 1
        self.completed = True

    def screenshot(self) -> str:
        return "artifacts/approval.png"


def make_case() -> AgentTestCase:
    return AgentTestCase(
        id="approval-case",
        name="Approve browser action",
        start_url="https://example.com",
        goal="Complete the action",
        expected=["Action completed"],
        max_steps=3,
    )


browser = ApprovalBrowser()


def make_graph_and_config(thread_id: str):
    global browser
    browser = ApprovalBrowser()
    checkpointer = InMemorySaver()
    graph = build_agent_graph(
        ApprovalModel(),
        browser,
        checkpointer=checkpointer,
        require_approval=True,
    )
    config = build_thread_config(make_case(), thread_id)
    return graph, config


def test_graph_interrupts_before_browser_execution() -> None:
    graph, config = make_graph_and_config("approval-pause")

    paused = graph.invoke({"test_case": make_case()}, config=config)

    assert paused["__interrupt__"]
    assert paused["__interrupt__"][0].value["type"] == "browser_action_approval"
    assert browser.click_count == 0


def test_approved_action_resumes_and_executes() -> None:
    graph, config = make_graph_and_config("approval-yes")
    graph.invoke({"test_case": make_case()}, config=config)

    result = graph.invoke(
        Command(
            resume={
                "approved": True,
                "reason": "The action matches the scenario.",
            }
        ),
        config=config,
    )

    assert result["status"] == "passed"
    assert browser.click_count == 1


def test_rejected_action_resumes_without_execution() -> None:
    graph, config = make_graph_and_config("approval-no")
    graph.invoke({"test_case": make_case()}, config=config)

    result = graph.invoke(
        Command(
            resume={
                "approved": False,
                "reason": "The target must not be clicked.",
            }
        ),
        config=config,
    )

    assert result["status"] == "failed"
    assert result["termination"].kind is TerminationKind.HUMAN_REJECTED
    assert browser.click_count == 0
