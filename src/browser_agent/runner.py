"""Composition layer for running the agent against a real browser."""

from collections.abc import Callable
from pathlib import Path

from browser_agent.domain import TestCase
from browser_agent.feedback import FeedbackScope
from browser_agent.feedback_retrieval import (
    FeedbackRetrievalQuery,
    format_feedback_for_prompt,
    retrieve_feedback_from_store,
)
from browser_agent.graph import build_agent_graph
from browser_agent.observability import build_trace_config
from browser_agent.persistence import build_thread_config
from browser_agent.reporting import build_run_report, save_run_report
from browser_agent.run_history import RunHistoryStore, build_run_history_record


def build_feedback_memory_context(
        test_case: TestCase,
        feedback_store,
) -> str:
    query = FeedbackRetrievalQuery(
        test_case=test_case,
        scopes=[FeedbackScope.PLANNER, FeedbackScope.STEP],
    )
    records = retrieve_feedback_from_store(query, feedback_store)
    return format_feedback_for_prompt(records)


def run_agent(
        model,
        browser,
        test_case: TestCase,
        on_state: Callable[[dict], None] | None = None,
        report_dir: str | Path | None = None,
        checkpointer=None,
        thread_id: str | None = None,
        history_store: RunHistoryStore | None = None,
        run_id: str | None = None,
        feedback_store=None,
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

    if checkpointer is None:
        run_config = build_trace_config(test_case)
    else:
        run_config = build_thread_config(test_case, thread_id)

    initial_state = {"test_case": test_case}

    if feedback_store is not None:
        initial_state["memory_context"] = build_feedback_memory_context(
            test_case,
            feedback_store,
        )

    final_state = None

    for state in graph.stream(
            initial_state,
            config=run_config,
            stream_mode="values",
    ):
        final_state = state

        if on_state is not None:
            on_state(state)

    if final_state is None:
        raise RuntimeError("Agent graph produced no state")

    report = None

    if report_dir is not None or history_store is not None:
        report = build_run_report(final_state)

    if report_dir is not None:
        save_run_report(report, report_dir)

    if history_store is not None:
        history_store.append(
            build_run_history_record(
                report=report,
                run_id=run_id,
            )
        )

    return final_state