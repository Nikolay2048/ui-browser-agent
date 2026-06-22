from langchain_core.runnables import RunnableLambda

from browser_agent.agent_graph import build_agent_graph
from browser_agent.domain import BrowserAction, TestCase as AgentTestCase


class FakeStructuredModel:
    def with_structured_output(self, schema):
        def respond(prompt_value):
            return BrowserAction(
                action="fill",
                target="label=Username",
                value="standard_user",
                reason="The username is required before login.",
            )

        return RunnableLambda(respond)


class FakeBrowser:
    def __init__(self) -> None:
        self.current_url = "https://example.com/login"
        self.calls = []

    def fill(self, target: str, value: str) -> None:
        self.calls.append(("fill", target, value))

    def screenshot(self) -> str:
        self.calls.append(("screenshot",))
        return "artifacts/001-fill.png"


def test_agent_graph_plans_and_executes_one_action() -> None:
    browser = FakeBrowser()
    graph = build_agent_graph(
        model=FakeStructuredModel(),
        browser=browser,
    )
    test_case = AgentTestCase(
        id="plan-execute",
        name="Plan and execute",
        start_url="https://example.com/login",
        goal="Fill in the username",
        test_data={"username": "standard_user"},
    )

    result = graph.invoke(
        {
            "test_case": test_case,
            "page_snapshot": '- textbox "Username"',
        }
    )

    assert browser.calls == [
        ("fill", "label=Username", "standard_user"),
        ("screenshot",),
    ]
    assert result["proposed_action"].action == "fill"
    assert result["last_result"].success is True
    assert result["step_count"] == 1
    assert result["status"] == "running"
