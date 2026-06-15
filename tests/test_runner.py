from langchain_core.runnables import RunnableLambda

from browser_agent.models import (
    BrowserAction,
    ExpectedResultCheck,
    JudgeVerdict,
    TestCase as AgentTestCase,
)
from browser_agent.runner import run_agent


class GoalAwareModel:
    def with_structured_output(self, schema):
        def respond(prompt_value):
            current_page = str(prompt_value.to_messages()[-1].content)
            if schema is JudgeVerdict:
                return JudgeVerdict(
                    passed=True,
                    checks=[
                        ExpectedResultCheck(
                            expected="Learn agents is visible",
                            passed=True,
                            evidence='Snapshot contains listitem "Learn agents".',
                        )
                    ],
                    summary="The requested task is visible.",
                )
            if 'textbox "Task"' in current_page:
                return BrowserAction(
                    action="fill",
                    target="label=Task",
                    value="Learn agents",
                    reason="Enter the task from test data.",
                )
            if 'button "Add"' in current_page:
                return BrowserAction(
                    action="click",
                    target='role=button[name="Add"]',
                    value=None,
                    reason="Submit the entered task.",
                )
            return BrowserAction(
                action="finish",
                target=None,
                value=None,
                reason="The requested task is visible.",
            )

        return RunnableLambda(respond)


class StatefulBrowser:
    def __init__(self) -> None:
        self.current_url = "about:blank"
        self.opened_urls = []
        self.value = ""
        self.added = False

    def open(self, url: str) -> None:
        self.opened_urls.append(url)
        self.current_url = url

    def snapshot(self) -> str:
        if self.added:
            return '- listitem "Learn agents"'
        if self.value:
            return '- button "Add"'
        return '- textbox "Task"'

    def fill(self, _target: str, value: str) -> None:
        self.value = value

    def click(self, _target: str) -> None:
        self.added = True

    def screenshot(self) -> str:
        return "artifacts/test-runner.png"


def make_case() -> AgentTestCase:
    return AgentTestCase(
        id="real-runner",
        name="Run composed agent",
        start_url="https://example.com/tasks",
        goal="Add task Learn agents",
        test_data={"task": "Learn agents"},
        expected=["Learn agents is visible"],
        max_steps=4,
    )


def test_run_agent_opens_start_url_and_returns_final_state() -> None:
    browser = StatefulBrowser()

    result = run_agent(GoalAwareModel(), browser, make_case())

    assert browser.opened_urls == ["https://example.com/tasks"]
    assert result["status"] == "passed"
    assert result["current_url"] == "https://example.com/tasks"
    assert result["step_count"] == 2
    assert len(result["route"]) == 2


def test_run_agent_reports_each_full_state() -> None:
    observed_states = []

    result = run_agent(
        GoalAwareModel(),
        StatefulBrowser(),
        make_case(),
        on_state=observed_states.append,
    )

    assert observed_states
    assert observed_states[-1] == result
    assert observed_states[-1]["status"] == "passed"
    assert any(state.get("step_count") == 1 for state in observed_states)
    assert any(state.get("step_count") == 2 for state in observed_states)
