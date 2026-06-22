from langchain_core.runnables import RunnableLambda

from browser_agent.domain import BrowserAction, TestCase as AgentTestCase
from browser_agent.observing_agent_graph import build_observing_agent_graph


class FakeStructuredModel:
    def with_structured_output(self, schema):
        def respond(prompt_value):
            return BrowserAction(
                action="click",
                target='button "Login"',
                value=None,
                reason="The login form can be submitted.",
            )

        return RunnableLambda(respond)


class FakeBrowser:
    def __init__(self) -> None:
        self.current_url = "https://example.com/login"
        self.calls = []

    def snapshot(self) -> str:
        self.calls.append(("snapshot",))
        return '- button "Login"'

    def click(self, target: str) -> None:
        self.calls.append(("click", target))
        self.current_url = "https://example.com/products"

    def screenshot(self) -> str:
        self.calls.append(("screenshot",))
        return "artifacts/001-login.png"


def test_observing_graph_reads_page_before_planning() -> None:
    browser = FakeBrowser()
    graph = build_observing_agent_graph(
        model=FakeStructuredModel(),
        browser=browser,
    )
    test_case = AgentTestCase(
        id="observe-plan-execute",
        name="Observe, plan and execute",
        start_url="https://example.com/login",
        goal="Submit the login form",
    )

    result = graph.invoke({"test_case": test_case})

    assert browser.calls == [
        ("snapshot",),
        ("click", 'button "Login"'),
        ("screenshot",),
    ]
    assert result["page_snapshot"] == '- button "Login"'
    assert result["last_result"].url_after == "https://example.com/products"
    assert result["step_count"] == 1
