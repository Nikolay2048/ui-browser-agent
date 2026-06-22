"""Checkpoint configuration helpers for LangGraph runs."""

from langchain_core.runnables import RunnableConfig

from browser_agent.domain import TestCase
from browser_agent.observability import build_trace_config


def build_thread_config(
    test_case: TestCase,
    thread_id: str,
) -> RunnableConfig:
    """Combine trace metadata with a persistent LangGraph thread ID."""
    if not thread_id.strip():
        raise ValueError("thread_id must not be blank")

    config = build_trace_config(test_case)
    config["configurable"] = {"thread_id": thread_id}
    return config
