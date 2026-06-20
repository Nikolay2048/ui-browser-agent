from langgraph.checkpoint.memory import InMemorySaver

from browser_agent.graph import build_agent_graph


class NoopModel:
    def with_structured_output(self, _schema):
        return object()


class NoopBrowser:
    pass


def test_graph_is_compiled_with_supplied_checkpointer() -> None:
    checkpointer = InMemorySaver()

    graph = build_agent_graph(
        NoopModel(),
        NoopBrowser(),
        checkpointer=checkpointer,
    )

    assert graph.checkpointer is checkpointer
