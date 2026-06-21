"""LangGraph state contract.

State contract shared by the current agent graph.
"""
from typing import TypedDict, NotRequired, Required, Literal

from browser_agent.models import (
    ActionResult,
    ActionApproval,
    BugReport,
    BrowserAction,
    ExecutionStep,
    FailureClassification,
    JudgeVerdict,
    RunTermination,
    TestCase,
)


class AgentState(TypedDict):
    test_case: Required[TestCase]

    current_url: NotRequired[str]
    route: NotRequired[list[ExecutionStep]]
    step_count: NotRequired[int]
    failure_count: NotRequired[int]
    status: NotRequired[Literal["running", "passed", "failed"]]
    page_snapshot: NotRequired[str]
    proposed_action: NotRequired[BrowserAction]
    last_result: NotRequired[ActionResult]
    verdict: NotRequired[JudgeVerdict]
    termination: NotRequired[RunTermination]
    classification: NotRequired[FailureClassification]
    bug_report: NotRequired[BugReport]
    action_approval: NotRequired[ActionApproval]
