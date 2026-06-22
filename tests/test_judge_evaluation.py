import pytest
from langchain_core.runnables import RunnableLambda

from browser_agent.evaluation.judge import (
    JudgeEvaluationCase,
    JudgePredictionScore,
    evaluate_judge_case,
    judge_correctness_evaluator,
    judge_false_positive_evaluator,
    make_judge_target,
    score_judge_verdict,
    summarize_judge_scores,
)
from browser_agent.domain import (
    ExpectedResultCheck,
    JudgeVerdict,
    TestCase as AgentTestCase,
)


def verdict(passed: bool) -> JudgeVerdict:
    return JudgeVerdict(
        passed=passed,
        checks=[
            ExpectedResultCheck(
                expected="Task is visible",
                passed=passed,
                evidence=(
                    "Snapshot contains the task."
                    if passed
                    else "Snapshot does not contain the task."
                ),
            )
        ],
        summary="Passed." if passed else "Expected result is not proven.",
    )


@pytest.mark.parametrize(
    ("expected", "actual", "outcome", "correct"),
    [
        (True, True, "tp", True),
        (False, False, "tn", True),
        (False, True, "fp", False),
        (True, False, "fn", False),
    ],
)
def test_score_judge_verdict_classifies_outcome(
    expected,
    actual,
    outcome,
    correct,
) -> None:
    score = score_judge_verdict(expected, verdict(actual))

    assert score.outcome == outcome
    assert score.correct is correct


def test_summary_builds_confusion_matrix_and_rates() -> None:
    scores = [
        JudgePredictionScore(
            expected_passed=True,
            actual_passed=True,
            outcome="tp",
            correct=True,
        ),
        JudgePredictionScore(
            expected_passed=False,
            actual_passed=False,
            outcome="tn",
            correct=True,
        ),
        JudgePredictionScore(
            expected_passed=False,
            actual_passed=True,
            outcome="fp",
            correct=False,
        ),
        JudgePredictionScore(
            expected_passed=True,
            actual_passed=False,
            outcome="fn",
            correct=False,
        ),
    ]

    summary = summarize_judge_scores(scores)

    assert summary.total_cases == 4
    assert summary.true_positives == 1
    assert summary.true_negatives == 1
    assert summary.false_positives == 1
    assert summary.false_negatives == 1
    assert summary.accuracy == 0.5
    assert summary.precision == 0.5
    assert summary.recall == 0.5
    assert summary.false_positive_rate == 0.5
    assert summary.false_negative_rate == 0.5


def test_summary_uses_zero_for_undefined_rates() -> None:
    summary = summarize_judge_scores([
        JudgePredictionScore(
            expected_passed=False,
            actual_passed=False,
            outcome="tn",
            correct=True,
        )
    ])

    assert summary.precision == 0.0
    assert summary.recall == 0.0
    assert summary.false_positive_rate == 0.0
    assert summary.false_negative_rate == 0.0


def test_summary_rejects_empty_experiment() -> None:
    with pytest.raises(ValueError, match="scores"):
        summarize_judge_scores([])


def make_case(expected_passed: bool = True) -> JudgeEvaluationCase:
    return JudgeEvaluationCase(
        id="judge-case",
        test_case=AgentTestCase(
            id="judge-case",
            name="Judge case",
            start_url="https://example.com/tasks",
            goal="Verify task",
            expected=["Task is visible"],
        ),
        page_snapshot='- listitem "Task"',
        expected_passed=expected_passed,
    )


class FixedJudgeModel:
    def __init__(self, result: JudgeVerdict) -> None:
        self.result = result

    def with_structured_output(self, _schema):
        return RunnableLambda(lambda _prompt: self.result)


def test_evaluate_case_runs_production_judge() -> None:
    actual, score = evaluate_judge_case(
        FixedJudgeModel(verdict(True)),
        make_case(expected_passed=True),
    )

    assert actual.passed is True
    assert score.outcome == "tp"


def test_langsmith_target_returns_json_verdict() -> None:
    target = make_judge_target(FixedJudgeModel(verdict(False)))
    case = make_case(expected_passed=False)

    output = target({
        "test_case": case.test_case.model_dump(mode="json"),
        "page_snapshot": case.page_snapshot,
        "route": [],
    })

    assert output["verdict"]["passed"] is False


def test_langsmith_correctness_evaluator() -> None:
    feedback = judge_correctness_evaluator(
        inputs={},
        outputs={"verdict": verdict(True).model_dump(mode="json")},
        reference_outputs={"passed": False},
    )

    assert feedback == {
        "key": "judge_correct",
        "score": 0.0,
    }


def test_langsmith_false_positive_evaluator() -> None:
    feedback = judge_false_positive_evaluator(
        inputs={},
        outputs={"verdict": verdict(True).model_dump(mode="json")},
        reference_outputs={"passed": False},
    )

    assert feedback == {
        "key": "judge_false_positive",
        "score": 1.0,
    }
