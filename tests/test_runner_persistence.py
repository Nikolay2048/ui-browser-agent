import pytest
from langgraph.checkpoint.memory import InMemorySaver

from browser_agent.models import TestCase as AgentTestCase
from browser_agent.runner import run_agent


class StaticBrowser:
    def open(self, _url: str) -> None:
        pass


class RecordingGraph:
    def __init__(self) -> None:
        self.config = None

    def stream(self, _input, *, stream_mode, config=None):
        self.config = config
        assert stream_mode == "values"
        yield {
            "test_case": make_case(),
            "status": "passed",
        }


def make_case() -> AgentTestCase:
    return AgentTestCase(
        id="persistent-runner",
        name="Persistent runner",
        start_url="https://example.com",
        goal="Open page",
    )


def test_run_agent_passes_checkpointer_and_thread_id(monkeypatch) -> None:
    graph = RecordingGraph()
    received = {}

    def fake_build_graph(_model, _browser, **kwargs):
        received.update(kwargs)
        return graph

    monkeypatch.setattr(
        "browser_agent.runner.build_agent_graph",
        fake_build_graph,
    )
    checkpointer = InMemorySaver()

    run_agent(
        object(),
        StaticBrowser(),
        make_case(),
        checkpointer=checkpointer,
        thread_id="thread-42",
    )

    assert received["checkpointer"] is checkpointer
    assert graph.config["configurable"]["thread_id"] == "thread-42"


def test_run_agent_requires_thread_id_for_checkpointing() -> None:
    with pytest.raises(ValueError, match="thread_id"):
        run_agent(
            object(),
            StaticBrowser(),
            make_case(),
            checkpointer=InMemorySaver(),
        )
