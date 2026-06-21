from langchain_core.runnables import RunnableLambda
from langgraph.checkpoint.memory import InMemorySaver

from browser_agent.graph import build_agent_graph
from browser_agent.models import (
    BrowserAction,
    BrowserTarget,
    BrowserTargetStrategy,
    ExpectedResultCheck,
    JudgeVerdict,
    TestCase as AgentTestCase,
)
from browser_agent.persistence import build_thread_config


class OneActionModel:
    def __init__(self, button_name: str, browser) -> None:
        self.button_name = button_name
        self.browser = browser

    def with_structured_output(self, schema):
        def respond(_prompt):
            if schema is JudgeVerdict:
                return JudgeVerdict(
                    passed=True,
                    checks=[
                        ExpectedResultCheck(
                            expected="Action completed",
                            passed=True,
                            evidence="The browser executed the action.",
                        )
                    ],
                    summary="The action completed.",
                )
            if self.browser.click_count:
                return BrowserAction(
                    action="finish",
                    target=None,
                    value=None,
                    reason="The requested action completed.",
                )
            return BrowserAction(
                action="click",
                target=BrowserTarget(
                    strategy=BrowserTargetStrategy.ROLE,
                    value="button",
                    name=self.button_name,
                ),
                value=None,
                reason="Execute the requested action.",
            )

        return RunnableLambda(respond)


class RecordingBrowser:
    current_url = "https://example.com"

    def __init__(self) -> None:
        self.click_count = 0

    def snapshot(self) -> str:
        return '- button "Continue"\n- button "Delete account"'

    def click(self, _target: str) -> None:
        self.click_count += 1

    def screenshot(self) -> str:
        return "artifacts/policy.png"


def make_case() -> AgentTestCase:
    return AgentTestCase(
        id="policy-case",
        name="Apply approval policy",
        start_url="https://example.com",
        goal="Click the requested button",
        expected=["Action completed"],
        max_steps=2,
    )


def run_until_stop(button_name: str, thread_id: str):
    browser = RecordingBrowser()
    checkpointer = InMemorySaver()
    graph = build_agent_graph(
        OneActionModel(button_name, browser),
        browser,
        checkpointer=checkpointer,
        approval_policy_enabled=True,
    )
    config = build_thread_config(make_case(), thread_id)
    result = graph.invoke({"test_case": make_case()}, config=config)
    return result, browser


def test_safe_action_bypasses_human_approval() -> None:
    result, browser = run_until_stop("Continue", "policy-safe")

    assert "__interrupt__" not in result
    assert browser.click_count == 1


def test_risky_action_interrupts_before_execution() -> None:
    result, browser = run_until_stop("Delete account", "policy-risky")

    assert result["__interrupt__"]
    assert browser.click_count == 0
