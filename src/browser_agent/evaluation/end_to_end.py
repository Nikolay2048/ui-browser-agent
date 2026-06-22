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
    raise NotImplementedError("Complete lesson 29.1")


def summarize_agent_runs(
    scores: Sequence[EndToEndRunScore],
) -> EndToEndEvaluationSummary:
    """Aggregate complete-run scores into system-level metrics."""
    raise NotImplementedError("Complete lesson 29.2")


def evaluate_end_to_end_case(
    run_case: Callable[[TestCase], dict],
    case: EndToEndEvaluationCase,
) -> tuple[dict, EndToEndRunScore]:
    """Execute one complete case through an injected runner and score it."""
    raise NotImplementedError("Complete lesson 29.3")


def make_end_to_end_target(
    run_case: Callable[[TestCase], dict],
) -> Callable[[dict], dict]:
    """Adapt a complete-agent runner to the LangSmith target contract."""
    raise NotImplementedError("Complete lesson 29.4")


def end_to_end_evaluator(
    inputs: dict,
    outputs: dict,
    reference_outputs: dict,
) -> dict:
    """LangSmith feedback for exact complete-run behavior."""
    raise NotImplementedError("Complete lesson 29.5")
