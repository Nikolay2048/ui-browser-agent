import pytest
from pydantic import ValidationError

from browser_agent.models import BugReport, BugSeverity


def make_payload() -> dict:
    return {
        "test_case_id": "create-task",
        "title": "Task is not added after clicking Add",
        "severity": "major",
        "preconditions": ["Tasks page is open"],
        "steps_to_reproduce": [
            "Fill Task with Learn AI Agents",
            "Click the Add button",
        ],
        "expected_result": "Learn AI Agents is visible in the task list.",
        "actual_result": "The task is absent from the final page.",
        "evidence": [
            'Final snapshot does not contain listitem "Learn AI Agents".',
            "Judge marked the expected result as failed.",
        ],
    }


def test_bug_report_contains_reproducible_structure() -> None:
    report = BugReport(**make_payload())

    assert report.test_case_id == "create-task"
    assert report.severity == BugSeverity.MAJOR
    assert len(report.steps_to_reproduce) == 2
    assert report.evidence


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("title", ""),
        ("steps_to_reproduce", []),
        ("evidence", []),
    ],
)
def test_bug_report_rejects_incomplete_content(field: str, value) -> None:
    payload = make_payload()
    payload[field] = value

    with pytest.raises(ValidationError):
        BugReport(**payload)
