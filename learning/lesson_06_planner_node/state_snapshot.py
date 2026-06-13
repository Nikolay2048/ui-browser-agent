"""AgentState after adding planner fields in lesson 6."""

from typing import Literal, NotRequired, Required, TypedDict

from browser_agent.models import ActionResult, BrowserAction, TestCase


class AgentState(TypedDict):
    test_case: Required[TestCase]
    current_url: NotRequired[str]
    route: NotRequired[list[ActionResult]]
    step_count: NotRequired[int]
    status: NotRequired[Literal["running", "passed", "failed"]]
    page_snapshot: NotRequired[str]
    proposed_action: NotRequired[BrowserAction]
