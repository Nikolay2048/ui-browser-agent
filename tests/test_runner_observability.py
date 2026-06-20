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
        id="runner-trace",
        name="Trace runner",
        start_url="https://example.com",
        goal="Open page",
    )


def test_run_agent_passes_trace_config_to_graph(monkeypatch) -> None:
    graph = RecordingGraph()
    monkeypatch.setattr(
        "browser_agent.runner.build_agent_graph",
        lambda _model, _browser: graph,
    )

    result = run_agent(object(), StaticBrowser(), make_case())

    assert result["status"] == "passed"
    assert graph.config["run_name"] == "ui-test:runner-trace"
    assert graph.config["metadata"]["test_case_id"] == "runner-trace"
