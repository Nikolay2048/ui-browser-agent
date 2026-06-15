import pytest
from pydantic import ValidationError

from browser_agent.models import ExpectedResultCheck, JudgeVerdict


def test_judge_verdict_contains_checks_and_summary() -> None:
    verdict = JudgeVerdict(
        passed=True,
        checks=[
            ExpectedResultCheck(
                expected="Learn AI Agents is visible",
                passed=True,
                evidence='Current page contains listitem "Learn AI Agents".',
            )
        ],
        summary="Every expected result is proven.",
    )

    assert verdict.passed is True
    assert verdict.checks[0].expected == "Learn AI Agents is visible"
    assert verdict.checks[0].passed is True
    assert verdict.checks[0].evidence.startswith("Current page")


def test_judge_verdict_requires_at_least_one_check() -> None:
    with pytest.raises(ValidationError):
        JudgeVerdict(
            passed=True,
            checks=[],
            summary="No checks were performed.",
        )


def test_judge_verdict_rejects_inconsistent_overall_result() -> None:
    with pytest.raises(ValidationError):
        JudgeVerdict(
            passed=True,
            checks=[
                ExpectedResultCheck(
                    expected="Task is visible",
                    passed=False,
                    evidence="Task was not found in the snapshot.",
                )
            ],
            summary="Contradictory result.",
        )
