from browser_agent.domain import TestCase as AgentTestCase
from browser_agent.observability import build_trace_config


def make_case() -> AgentTestCase:
    return AgentTestCase(
        id="trace-case",
        name="Trace browser agent",
        start_url="https://example.com/tasks",
        goal="Create a task",
        test_data={
            "task": "Learn observability",
            "password": "must-not-be-trace-metadata",
        },
        expected=["Task is visible"],
        max_steps=7,
        max_failures=3,
    )


def test_trace_config_names_and_tags_the_top_level_run() -> None:
    config = build_trace_config(make_case())

    assert config["run_name"] == "ui-test:trace-case"
    assert "browser-agent" in config["tags"]
    assert "ui-test" in config["tags"]


def test_trace_config_adds_searchable_test_case_metadata() -> None:
    config = build_trace_config(make_case())

    assert config["metadata"] == {
        "test_case_id": "trace-case",
        "test_case_name": "Trace browser agent",
        "start_url": "https://example.com/tasks",
        "max_steps": 7,
        "max_failures": 3,
    }


def test_trace_metadata_does_not_copy_test_data() -> None:
    config = build_trace_config(make_case())

    serialized = str(config["metadata"])

    assert "password" not in serialized
    assert "must-not-be-trace-metadata" not in serialized
