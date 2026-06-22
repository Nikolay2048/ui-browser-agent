import pytest
from pydantic import ValidationError

from browser_agent.graph import fail_run, pass_run
from browser_agent.domain import (
    ExpectedResultCheck,
    JudgeVerdict,
    RunTermination,
    TerminationKind,
    TestCase as AgentTestCase,
)


def make_case(
    *,
    max_steps: int = 5,
    max_failures: int = 2,
) -> AgentTestCase:
    return AgentTestCase(
        id="termination",
        name="Explain why the run stopped",
        start_url="https://example.com",
        goal="Reach the expected state",
        expected=["Expected state is visible"],
        max_steps=max_steps,
        max_failures=max_failures,
    )


def make_verdict(passed: bool) -> JudgeVerdict:
    return JudgeVerdict(
        passed=passed,
        checks=[
            ExpectedResultCheck(
                expected="Expected state is visible",
                passed=passed,
                evidence=(
                    "Expected state is visible."
                    if passed
                    else "Expected state is absent."
                ),
            )
        ],
        summary="Passed." if passed else "Expected result is not proven.",
    )


def test_run_termination_requires_non_empty_message() -> None:
    with pytest.raises(ValidationError):
        RunTermination(
            kind="step_limit",
            message="",
        )


def test_pass_run_records_judge_success_reason() -> None:
    update = pass_run({"verdict": make_verdict(True)})

    assert update["status"] == "passed"
    assert update["termination"].kind == TerminationKind.JUDGE_PASSED
    assert "Judge" in update["termination"].message


def test_fail_run_records_judge_failure_reason() -> None:
    update = fail_run(
        {
            "test_case": make_case(),
            "verdict": make_verdict(False),
            "step_count": 2,
            "failure_count": 0,
        }
    )

    assert update["status"] == "failed"
    assert update["termination"].kind == TerminationKind.JUDGE_FAILED
    assert "not proven" in update["termination"].message


def test_fail_run_records_step_limit_before_other_limits() -> None:
    update = fail_run(
        {
            "test_case": make_case(max_steps=3, max_failures=2),
            "step_count": 3,
            "failure_count": 2,
        }
    )

    assert update["termination"].kind == TerminationKind.STEP_LIMIT
    assert "3" in update["termination"].message


def test_fail_run_records_failure_limit() -> None:
    update = fail_run(
        {
            "test_case": make_case(max_steps=5, max_failures=2),
            "step_count": 2,
            "failure_count": 2,
        }
    )

    assert update["termination"].kind == TerminationKind.FAILURE_LIMIT
    assert "2" in update["termination"].message
