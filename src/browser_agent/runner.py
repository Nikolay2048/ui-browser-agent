"""Composition layer for running the agent against a real browser."""

from collections.abc import Callable
from pathlib import Path

from browser_agent.graph import build_agent_graph
from browser_agent.models import TestCase
from browser_agent.observability import build_trace_config
from browser_agent.persistence import build_thread_config
from browser_agent.reporting import build_run_report, save_run_report


def run_agent(
        model,
        browser,
        test_case: TestCase,
        on_state: Callable[[dict], None] | None = None,
        report_dir: str | Path | None = None,
        checkpointer=None,
        thread_id: str | None = None,
) -> dict:
    """Open the start URL, stream the graph, and return its final state.

    learning/lesson_13_real_agent/README.md.
    """
    if checkpointer is not None and thread_id is None:
        raise ValueError("thread_id is required when checkpointer is enabled")

    browser.open(test_case.start_url)
    if checkpointer is None:
        graph = build_agent_graph(model, browser)
    else:
        graph = build_agent_graph(
            model,
            browser,
            checkpointer=checkpointer,
        )
    final_state = None
    if checkpointer is None:
        run_config = build_trace_config(test_case)
    else:
        run_config = build_thread_config(test_case, thread_id)

    for state in graph.stream(
            {"test_case": test_case},
            config=run_config,
            stream_mode="values"
    ):
        final_state = state

        if on_state is not None:
            on_state(state)

    if final_state is None:
        raise RuntimeError("Agent graph produced no state")

    if report_dir is not None:
        report = build_run_report(final_state)
        save_run_report(report, report_dir)

    return final_state
