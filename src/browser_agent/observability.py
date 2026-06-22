"""LangSmith trace configuration for one browser-agent run."""

from langchain_core.runnables import RunnableConfig

from browser_agent.domain import TestCase


def build_trace_config(test_case: TestCase) -> RunnableConfig:
    """Build searchable, non-secret metadata for a LangSmith trace."""

    return {
        "run_name": f"ui-test:{test_case.id}",
        "tags": ["browser-agent", "ui-test"],
        "metadata": {
            "test_case_id": test_case.id,
            "test_case_name": test_case.name,
            "start_url": test_case.start_url,
            "max_steps": test_case.max_steps,
            "max_failures": test_case.max_failures,
        },
    }
