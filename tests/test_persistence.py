import pytest

from browser_agent.models import TestCase as AgentTestCase
from browser_agent.persistence import build_thread_config


def make_case() -> AgentTestCase:
    return AgentTestCase(
        id="checkpoint-case",
        name="Persist agent state",
        start_url="https://example.com/tasks",
        goal="Create a task",
    )


def test_thread_config_preserves_observability_fields() -> None:
    config = build_thread_config(make_case(), "run-123")

    assert config["run_name"] == "ui-test:checkpoint-case"
    assert "browser-agent" in config["tags"]
    assert config["metadata"]["test_case_id"] == "checkpoint-case"


def test_thread_config_adds_thread_id() -> None:
    config = build_thread_config(make_case(), "run-123")

    assert config["configurable"] == {"thread_id": "run-123"}


@pytest.mark.parametrize("thread_id", ["", "   "])
def test_thread_config_rejects_blank_thread_id(thread_id: str) -> None:
    with pytest.raises(ValueError, match="thread_id"):
        build_thread_config(make_case(), thread_id)
