from __future__ import annotations

from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages

from testing_agent.models import BugReport, ClarificationRequest, ExecutionPlan, StepResult, TestCase


def _merge_lists(a: list, b: list) -> list:
    return a + b


class AgentState(TypedDict):
    test_case: TestCase
    execution_plan: ExecutionPlan | None
    current_step_index: int
    step_results: Annotated[list[StepResult], _merge_lists]
    bugs: Annotated[list[BugReport], _merge_lists]
    messages: Annotated[list, add_messages]
    generated_test_code: str
    overall_status: str
    clarification: ClarificationRequest | None
    plan_reasoning: str
    analysis_reasoning: str
    error: str | None
