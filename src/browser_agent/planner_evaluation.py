"""Deterministic evaluation utilities for the Planner role."""

from collections.abc import Callable, Sequence

from pydantic import BaseModel, Field

from browser_agent.models import (
    BrowserAction,
    ExecutionStep,
    TestCase,
)
from browser_agent.planner import plan_next_action


class PlannerEvaluationCase(BaseModel):
    """One fixed Planner input with a human-approved reference action."""

    id: str = Field(min_length=1)
    test_case: TestCase
    page_snapshot: str = Field(min_length=1)
    route: list[ExecutionStep] = Field(default_factory=list)
    expected_action: BrowserAction


class PlannerActionScore(BaseModel):
    """Component-level comparison of actual and reference actions."""

    action_match: bool
    target_match: bool
    value_match: bool
    exact_match: bool
    score: float = Field(ge=0.0, le=1.0)


class PlannerEvaluationSummary(BaseModel):
    """Aggregate metrics for one Planner experiment."""

    total_cases: int = Field(ge=1)
    exact_matches: int = Field(ge=0)
    exact_accuracy: float = Field(ge=0.0, le=1.0)
    action_accuracy: float = Field(ge=0.0, le=1.0)
    target_accuracy: float = Field(ge=0.0, le=1.0)
    value_accuracy: float = Field(ge=0.0, le=1.0)
    average_score: float = Field(ge=0.0, le=1.0)


def score_planner_action(
        expected: BrowserAction,
        actual: BrowserAction,
) -> PlannerActionScore:
    """Compare behaviorally relevant BrowserAction fields."""
    action_match = expected.action == actual.action
    target_match = expected.target == actual.target
    value_match = expected.value == actual.value
    exact_match = action_match and target_match and value_match

    component_score = sum(
        [action_match, target_match, value_match]
    ) / 3
    return PlannerActionScore(action_match=action_match, target_match=target_match, value_match=value_match,
                              exact_match=exact_match, score=component_score)


def summarize_planner_scores(
        scores: Sequence[PlannerActionScore],
) -> PlannerEvaluationSummary:
    """Aggregate case scores into experiment-level metrics."""
    if not scores:
        raise ValueError("scores must not be empty")

    total_cases = len(scores)

    exact_matches = sum(score.exact_match for score in scores)

    return PlannerEvaluationSummary(
        total_cases=total_cases,
        exact_matches=exact_matches,
        exact_accuracy=exact_matches / total_cases,
        action_accuracy=sum(score.action_match for score in scores) / total_cases,
        target_accuracy=sum(score.target_match for score in scores) / total_cases,
        value_accuracy=sum(score.value_match for score in scores) / total_cases,
        average_score=sum(score.score for score in scores) / total_cases,
    )


def evaluate_planner_case(
        model,
        case: PlannerEvaluationCase,
) -> tuple[BrowserAction, PlannerActionScore]:
    """Run the real Planner once and score its output."""
    actual = plan_next_action(
        model=model,
        test_case=case.test_case,
        page_snapshot=case.page_snapshot,
        route=case.route,
    )

    score = score_planner_action(
        case.expected_action,
        actual,
    )

    return actual, score


def make_planner_target(model) -> Callable[[dict], dict]:
    """Adapt Planner inputs and outputs to the LangSmith target contract."""

    def target(inputs: dict) -> dict:
        test_case = TestCase.model_validate(inputs["test_case"])
        route = [
            ExecutionStep.model_validate(step)
            for step in inputs.get("route", [])
        ]

        action = plan_next_action(
            model=model,
            test_case=test_case,
            page_snapshot=inputs["page_snapshot"],
            route=route,
        )

        return {
            "action": action.model_dump(mode="json"),
        }

    return target


def planner_action_evaluator(
        inputs: dict,
        outputs: dict,
        reference_outputs: dict,
) -> dict:
    """LangSmith code evaluator for exact behavioral action match."""
    actual = BrowserAction.model_validate(outputs["action"])
    expected = BrowserAction.model_validate(
        reference_outputs["action"]
    )

    score = score_planner_action(
        expected=expected,
        actual=actual,
    )

    return {
        "key": "planner_exact_match",
        "score": float(score.exact_match),
    }
