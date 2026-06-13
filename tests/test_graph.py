from browser_agent.graph import build_learning_graph, complete, initialize
from browser_agent.models import TestCase as AgentTestCase


def make_case() -> AgentTestCase:
    return AgentTestCase(
        id="lesson-2",
        name="Learn state",
        start_url="https://example.com",
        goal="Understand LangGraph state",
    )


def test_initialize_node_returns_state_update() -> None:
    update = initialize({"test_case": make_case()})

    assert update == {
        "current_url": "https://example.com",
        "route": [],
        "step_count": 0,
        "status": "running",
    }


def test_complete_node_returns_only_changed_fields() -> None:
    update = complete(
        {
            "test_case": make_case(),
            "current_url": "https://example.com",
            "route": [],
            "step_count": 0,
            "status": "running",
        }
    )

    assert update == {"status": "passed"}


def test_learning_graph_executes_nodes_in_order() -> None:
    graph = build_learning_graph()

    result = graph.invoke({"test_case": make_case()})

    assert result["current_url"] == "https://example.com"
    assert result["route"] == []
    assert result["step_count"] == 0
    assert result["status"] == "passed"
