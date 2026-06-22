"""End-to-end evaluation utilities for complete agent runs."""

from collections.abc import Callable, Sequence
from typing import Literal

from pydantic import BaseModel, Field

from browser_agent.domain import (
    RunTermination,
    TerminationKind,
    TestCase,
)


class EndToEndExpectation(BaseModel):
    """Trusted expectations for one complete agent run."""

    status: Literal["passed", "failed"]
    max_steps: int = Field(ge=0)
    termination_kind: TerminationKind
    expects_recovery: bool = False


class EndToEndEvaluationCase(BaseModel):
    """One test case and its trusted end-to-end expectations."""

    id: str = Field(min_length=1)
    test_case: TestCase
    expected: EndToEndExpectation


class EndToEndRunScore(BaseModel):
    """Component metrics for one completed agent run."""

    status_match: bool
    termination_match: bool
    within_step_budget: bool
    recovery_observed: bool
    recovery_match: bool
    exact_match: bool
    score: float = Field(ge=0.0, le=1.0)
    step_count: int = Field(ge=0)
    failure_count: int = Field(ge=0)


class EndToEndEvaluationSummary(BaseModel):
    """Aggregate system-level metrics for an evaluation suite."""

    total_cases: int = Field(ge=1)
    exact_matches: int = Field(ge=0)
    exact_accuracy: float = Field(ge=0.0, le=1.0)
    task_success_rate: float = Field(ge=0.0, le=1.0)
    termination_accuracy: float = Field(ge=0.0, le=1.0)
    step_budget_rate: float = Field(ge=0.0, le=1.0)
    recovery_accuracy: float = Field(ge=0.0, le=1.0)
    average_steps: float = Field(ge=0.0)
    average_failures: float = Field(ge=0.0)
    average_score: float = Field(ge=0.0, le=1.0)


def score_agent_run(
    expected: EndToEndExpectation,
    final_state: dict,
) -> EndToEndRunScore:
    """Score one completed AgentState against trusted expectations."""
    status = final_state["status"]
    step_count = final_state["step_count"]
    failure_count = final_state["failure_count"]

    termination = RunTermination.model_validate(
        final_state["termination"]
    )

    status_match = status == expected.status

    termination_match = (
        termination.kind == expected.termination_kind
    )

    within_step_budget = (
        step_count <= expected.max_steps
    )

    recovery_observed = (
        status == "passed"
        and failure_count > 0
    )

    recovery_match = (
        recovery_observed == expected.expects_recovery
    )

    exact_match = (
        status_match
        and termination_match
        and within_step_budget
        and recovery_match
    )

    component_score = sum([
        status_match,
        termination_match,
        within_step_budget,
        recovery_match,
    ]) / 4

    return EndToEndRunScore(
        status_match=status_match,
        termination_match=termination_match,
        within_step_budget=within_step_budget,
        recovery_observed=recovery_observed,
        recovery_match=recovery_match,
        exact_match=exact_match,
        score=component_score,
        step_count=step_count,
        failure_count=failure_count,
    )


def summarize_agent_runs(
    scores: Sequence[EndToEndRunScore],
) -> EndToEndEvaluationSummary:
    """Aggregate complete-run scores into system-level metrics."""
    if not scores:
        raise ValueError("scores must not be empty")

    total_cases = len(scores)

    exact_matches = sum(score.exact_match for score in scores)

    return EndToEndEvaluationSummary(
        total_cases=total_cases,
        exact_matches=exact_matches,
        exact_accuracy=exact_matches / total_cases,
        task_success_rate=sum(score.status_match for score in scores) / total_cases,
        termination_accuracy=sum(score.termination_match for score in scores) / total_cases,
        step_budget_rate=sum(score.within_step_budget for score in scores) / total_cases,
        recovery_accuracy=sum(score.recovery_match for score in scores) / total_cases,
        average_steps=sum(score.step_count for score in scores) / total_cases,
        average_failures=sum(score.failure_count for score in scores) / total_cases,
        average_score=sum(score.score for score in scores) / total_cases,
    )


def evaluate_end_to_end_case(
    run_case: Callable[[TestCase], dict],
    case: EndToEndEvaluationCase,
) -> tuple[dict, EndToEndRunScore]:
    """Execute one complete case through an injected runner and score it."""
    final_state = run_case(case.test_case)
    score = score_agent_run(case.expected, final_state)
    return final_state, score


def make_end_to_end_target(
    run_case: Callable[[TestCase], dict],
) -> Callable[[dict], dict]:
    """Adapt a complete-agent runner to the LangSmith target contract."""

    def target(inputs: dict) -> dict:
        test_case = TestCase.model_validate(
            inputs["test_case"]
        )

        final_state = run_case(test_case)

        termination = RunTermination.model_validate(
            final_state["termination"]
        )

        return {
            "status": final_state["status"],
            "step_count": final_state["step_count"],
            "failure_count": final_state["failure_count"],
            "termination": termination.model_dump(mode="json"),
        }

    return target


def end_to_end_evaluator(
    inputs: dict,
    outputs: dict,
    reference_outputs: dict,
) -> dict:
    """LangSmith feedback for exact complete-run behavior."""
    expected = EndToEndExpectation.model_validate(
        reference_outputs["expected"]
    )

    final_state = {
        "status": outputs["status"],
        "step_count": outputs["step_count"],
        "failure_count": outputs["failure_count"],
        "termination": outputs["termination"],
    }

    score = score_agent_run(
        expected=expected,
        final_state=final_state,
    )

    return {
        "key": "e2e_exact_match",
        "score": float(score.exact_match),
    }
