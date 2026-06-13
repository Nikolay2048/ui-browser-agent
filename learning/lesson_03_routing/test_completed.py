from browser_agent.models import TestCase as AgentTestCase
from browser_agent.routing_graph import (
    build_routing_graph,
    fail_run,
    pass_run,
    route_start_url,
)


def make_state(url: str) -> dict:
    return {
        "test_case": AgentTestCase(
            id="routing",
            name="Learn routing",
            start_url=url,
            goal="Choose the correct graph branch",
        ),
        "current_url": url,
        "route": [],
        "step_count": 0,
        "status": "running",
    }


def test_router_selects_pass_node_for_http_url() -> None:
    assert route_start_url(make_state("https://example.com")) == "pass_run"


def test_router_selects_fail_node_for_unsupported_url() -> None:
    assert route_start_url(make_state("ftp://example.com")) == "fail_run"


def test_terminal_nodes_return_partial_updates() -> None:
    state = make_state("https://example.com")

    assert pass_run(state) == {"status": "passed"}
    assert fail_run(state) == {"status": "failed"}


def test_routing_graph_passes_http_case() -> None:
    result = build_routing_graph().invoke(
        {"test_case": make_state("https://example.com")["test_case"]}
    )

    assert result["status"] == "passed"


def test_routing_graph_fails_unsupported_scheme() -> None:
    result = build_routing_graph().invoke(
        {"test_case": make_state("ftp://example.com")["test_case"]}
    )

    assert result["status"] == "failed"
