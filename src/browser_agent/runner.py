"""Composition layer for running the agent against a real browser."""

from collections.abc import Callable

from browser_agent.graph import build_agent_graph
from browser_agent.models import TestCase


def run_agent(
        model,
        browser,
        test_case: TestCase,
        on_state: Callable[[dict], None] | None = None,
) -> dict:
    """Open the start URL, stream the graph, and return its final state.

    learning/lesson_13_real_agent/README.md.
    """
    browser.open(test_case.start_url)
    graph = build_agent_graph(model, browser)
    final_state = None

    for state in graph.stream({"test_case": test_case}, stream_mode="values"):
        final_state = state

        if on_state is not None:
            on_state(state)

    if final_state is None:
        raise RuntimeError("Agent graph produced no state")

    return final_state
