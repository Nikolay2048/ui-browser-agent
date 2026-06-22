import pytest
from pydantic import ValidationError

from browser_agent.domain import (
    ActionResult,
    BrowserAction,
    BrowserActionType,
    BrowserTarget,
    BrowserTargetStrategy,
    ExecutionStep,
    RunReport,
    RunTermination,
    TerminationKind,
    TestCase as AgentTestCase,
)


def make_report(**overrides) -> RunReport:
    values = {
        "test_case": AgentTestCase(
            id="report-case",
            name="Create task",
            start_url="https://example.com/tasks",
            goal="Create task Learn agents",
            expected=["Learn agents is visible"],
        ),
        "status": "passed",
        "final_url": "https://example.com/tasks",
        "final_snapshot": 'listitem "Learn agents"',
        "step_count": 1,
        "failure_count": 0,
        "route": [
            ExecutionStep(
                step_number=1,
                page_snapshot='textbox "Task"',
                action=BrowserAction(
                    action=BrowserActionType.FILL,
                    target=BrowserTarget(
                        strategy=BrowserTargetStrategy.LABEL,
                        value="Task",
                    ),
                    value="Learn agents",
                    reason="Enter test data.",
                ),
                result=ActionResult(
                    success=True,
                    url_before="https://example.com/tasks",
                    url_after="https://example.com/tasks",
                ),
            )
        ],
        "termination": RunTermination(
            kind=TerminationKind.JUDGE_PASSED,
            message="All expected results passed.",
        ),
        "verdict": None,
        "classification": None,
        "bug_report": None,
    }
    values.update(overrides)
    return RunReport(**values)


def test_run_report_accepts_completed_run() -> None:
    report = make_report()

    assert report.test_case.id == "report-case"
    assert report.status == "passed"
    assert report.step_count == 1


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("final_url", ""),
        ("step_count", -1),
        ("failure_count", -1),
    ],
)
def test_run_report_rejects_invalid_summary(field, value) -> None:
    with pytest.raises(ValidationError):
        make_report(**{field: value})
