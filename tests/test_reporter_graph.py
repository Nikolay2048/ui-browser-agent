from browser_agent.graph import build_agent_graph, route_after_classification
from browser_agent.domain import FailureClassification


def make_classification(should_create_bug: bool) -> FailureClassification:
    return FailureClassification(
        category="product_bug" if should_create_bug else "automation_error",
        confidence=0.9,
        rationale="Evidence-based classification.",
        evidence=["Observed failure evidence."],
        should_create_bug=should_create_bug,
    )


def test_route_after_classification_controls_bug_creation() -> None:
    assert (
        route_after_classification(
            {"classification": make_classification(True)}
        )
        == "report_bug"
    )
    assert (
        route_after_classification(
            {"classification": make_classification(False)}
        )
        == "end"
    )


class NoCallModel:
    def with_structured_output(self, _schema):
        raise RuntimeError("No model call is expected while compiling.")


class MinimalBrowser:
    current_url = "about:blank"


def test_graph_registers_bug_reporter_role() -> None:
    graph = build_agent_graph(
        NoCallModel(),
        MinimalBrowser(),
        reporter_model=NoCallModel(),
    )

    assert "report_bug" in graph.get_graph().nodes
