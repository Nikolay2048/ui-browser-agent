from browser_agent.loop_graph import (
    build_loop_graph,
    finish_run,
    perform_step,
    route_after_step,
)
from browser_agent.domain import TestCase as AgentTestCase


def make_state(step_count: int, max_steps: int = 3) -> dict:
    return {
        "test_case": AgentTestCase(
            id="loop",
            name="Learn loops",
            start_url="https://example.com",
            goal="Repeat deterministic steps",
            max_steps=max_steps,
        ),
        "current_url": "https://example.com",
        "route": [],
        "step_count": step_count,
        "status": "running",
    }


def test_perform_step_returns_incremented_counter() -> None:
    assert perform_step(make_state(step_count=1)) == {"step_count": 2}


def test_router_continues_before_limit() -> None:
    assert route_after_step(make_state(step_count=2, max_steps=3)) == "perform_step"


def test_router_finishes_at_limit() -> None:
    assert route_after_step(make_state(step_count=3, max_steps=3)) == "finish_run"


def test_finish_run_returns_partial_update() -> None:
    assert finish_run(make_state(step_count=3)) == {"status": "passed"}


def test_loop_graph_reaches_max_steps_and_finishes() -> None:
    case = make_state(step_count=0, max_steps=3)["test_case"]

    result = build_loop_graph().invoke({"test_case": case})

    assert result["step_count"] == 3
    assert result["status"] == "passed"
