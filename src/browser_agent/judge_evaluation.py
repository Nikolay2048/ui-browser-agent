"""Deterministic evaluation utilities for the Judge role."""

from collections.abc import Callable, Sequence
from typing import Literal

from pydantic import BaseModel, Field

from browser_agent.judge import judge_run
from browser_agent.models import (
    ExecutionStep,
    JudgeVerdict,
    TestCase,
)


class JudgeEvaluationCase(BaseModel):
    """One fixed Judge input with a trusted expected pass/fail label."""

    id: str = Field(min_length=1)
    test_case: TestCase
    page_snapshot: str = Field(min_length=1)
    route: list[ExecutionStep] = Field(default_factory=list)
    expected_passed: bool


class JudgePredictionScore(BaseModel):
    """Classification result for one Judge prediction."""

    expected_passed: bool
    actual_passed: bool
    outcome: Literal["tp", "tn", "fp", "fn"]
    correct: bool


class JudgeEvaluationSummary(BaseModel):
    """Confusion matrix and derived metrics for one Judge experiment."""

    total_cases: int = Field(ge=1)
    true_positives: int = Field(ge=0)
    true_negatives: int = Field(ge=0)
    false_positives: int = Field(ge=0)
    false_negatives: int = Field(ge=0)
    accuracy: float = Field(ge=0.0, le=1.0)
    precision: float = Field(ge=0.0, le=1.0)
    recall: float = Field(ge=0.0, le=1.0)
    false_positive_rate: float = Field(ge=0.0, le=1.0)
    false_negative_rate: float = Field(ge=0.0, le=1.0)


def score_judge_verdict(
        expected_passed: bool,
        actual: JudgeVerdict,
) -> JudgePredictionScore:
    """Map one expected/actual pair to TP, TN, FP, or FN."""
    actual_passed = actual.passed

    if expected_passed and actual_passed:
        outcome = "tp"
    elif not expected_passed and not actual_passed:
        outcome = "tn"
    elif not expected_passed and actual_passed:
        outcome = "fp"
    else:
        outcome = "fn"
    return JudgePredictionScore(
        expected_passed=expected_passed,
        actual_passed=actual_passed,
        outcome=outcome,
        correct=outcome in {"tp", "tn"}
    )

def safe_divide(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


def summarize_judge_scores(
    scores: Sequence[JudgePredictionScore],
) -> JudgeEvaluationSummary:
    if not scores:
        raise ValueError("scores must not be empty")

    total_cases = len(scores)

    true_positives = sum(
        score.outcome == "tp"
        for score in scores
    )
    true_negatives = sum(
        score.outcome == "tn"
        for score in scores
    )
    false_positives = sum(
        score.outcome == "fp"
        for score in scores
    )
    false_negatives = sum(
        score.outcome == "fn"
        for score in scores
    )

    return JudgeEvaluationSummary(
        total_cases=total_cases,
        true_positives=true_positives,
        true_negatives=true_negatives,
        false_positives=false_positives,
        false_negatives=false_negatives,
        accuracy=safe_divide(
            true_positives + true_negatives,
            total_cases,
        ),
        precision=safe_divide(
            true_positives,
            true_positives + false_positives,
        ),
        recall=safe_divide(
            true_positives,
            true_positives + false_negatives,
        ),
        false_positive_rate=safe_divide(
            false_positives,
            false_positives + true_negatives,
        ),
        false_negative_rate=safe_divide(
            false_negatives,
            false_negatives + true_positives,
        ),
    )

def evaluate_judge_case(
        model,
        case: JudgeEvaluationCase,
) -> tuple[JudgeVerdict, JudgePredictionScore]:
    """Run the production Judge once and score its verdict."""
    actual = judge_run(
        model=model,
        test_case=case.test_case,
        page_snapshot=case.page_snapshot,
        route=case.route,
    )

    score = score_judge_verdict(
        expected_passed=case.expected_passed,
        actual=actual,
    )

    return actual, score


def make_judge_target(model) -> Callable[[dict], dict]:
    """Adapt Judge inputs and outputs to the LangSmith target contract."""
    def target(inputs: dict) -> dict:
        test_case = TestCase.model_validate(
            inputs["test_case"]
        )

        route = [
            ExecutionStep.model_validate(step)
            for step in inputs.get("route", [])
        ]

        verdict = judge_run(
            model=model,
            test_case=test_case,
            page_snapshot=inputs["page_snapshot"],
            route=route,
        )

        return {
            "verdict": verdict.model_dump(mode="json"),
        }

    return target


def judge_correctness_evaluator(
        inputs: dict,
        outputs: dict,
        reference_outputs: dict,
) -> dict:
    """LangSmith feedback: 1 when the pass/fail label is correct."""
    actual = JudgeVerdict.model_validate(
        outputs["verdict"]
    )
    expected_passed = bool(
        reference_outputs["passed"]
    )

    score = score_judge_verdict(
        expected_passed=expected_passed,
        actual=actual,
    )

    return {
        "key": "judge_correct",
        "score": float(score.correct),
    }


def judge_false_positive_evaluator(
        inputs: dict,
        outputs: dict,
        reference_outputs: dict,
) -> dict:
    """LangSmith feedback: 1 only for a dangerous false positive."""
    actual = JudgeVerdict.model_validate(
        outputs["verdict"]
    )
    expected_passed = bool(
        reference_outputs["passed"]
    )

    score = score_judge_verdict(
        expected_passed=expected_passed,
        actual=actual,
    )
    return {
        "key": "judge_false_positive",
        "score": float(score.outcome == "fp"),
    }
