from langchain_core.runnables import RunnableLambda

from browser_agent.domain import BrowserAction, TestCase as AgentTestCase
from browser_agent.planner_graph import build_planner_graph, make_plan_node


class FakeStructuredModel:
    def with_structured_output(self, schema):
        def respond(prompt_value):
            return BrowserAction(
                action="click",
                target='button "Login"',
                value=None,
                reason="The login form is ready to submit.",
            )

        return RunnableLambda(respond)


def make_case() -> AgentTestCase:
    return AgentTestCase(
        id="planner-node",
        name="Planner node",
        start_url="https://example.com/login",
        goal="Submit the login form",
    )


def test_plan_node_returns_partial_state_update() -> None:
    plan_node = make_plan_node(FakeStructuredModel())

    update = plan_node(
        {
            "test_case": make_case(),
            "page_snapshot": '- button "Login"',
        }
    )

    assert list(update) == ["proposed_action"]
    assert update["proposed_action"].action == "click"


def test_planner_graph_preserves_snapshot_and_adds_action() -> None:
    graph = build_planner_graph(FakeStructuredModel())
    snapshot = '- button "Login"'

    result = graph.invoke(
        {
            "test_case": make_case(),
            "page_snapshot": snapshot,
        }
    )

    assert result["page_snapshot"] == snapshot
    assert result["current_url"] == "https://example.com/login"
    assert result["status"] == "running"
    assert result["proposed_action"].target == 'button "Login"'
