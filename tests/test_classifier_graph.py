from browser_agent.graph import build_agent_graph
class SchemaRecordingModel:
    def with_structured_output(self, schema):
        raise RuntimeError("No model call is expected while compiling the graph.")


class MinimalBrowser:
    current_url = "about:blank"


def test_graph_registers_failure_classifier_role() -> None:
    planner_model = SchemaRecordingModel()
    classifier_model = SchemaRecordingModel()

    graph = build_agent_graph(
        planner_model,
        MinimalBrowser(),
        classifier_model=classifier_model,
    )

    assert "classify_failure" in graph.get_graph().nodes
