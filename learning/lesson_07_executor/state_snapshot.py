"""AgentState after adding executor result in lesson 7."""

from typing import Literal, NotRequired, Required, TypedDict

from browser_agent.domain import ActionResult, BrowserAction, TestCase


class AgentState(TypedDict):
    test_case: Required[TestCase]
    current_url: NotRequired[str]
    route: NotRequired[list[ActionResult]]
    step_count: NotRequired[int]
    status: NotRequired[Literal["running", "passed", "failed"]]
    page_snapshot: NotRequired[str]
    proposed_action: NotRequired[BrowserAction]
    last_result: NotRequired[ActionResult]
