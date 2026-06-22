"""AgentState after lesson 2."""

from typing import Literal, NotRequired, Required, TypedDict

from browser_agent.domain import ActionResult, TestCase


class AgentState(TypedDict):
    test_case: Required[TestCase]
    current_url: NotRequired[str]
    route: NotRequired[list[ActionResult]]
    step_count: NotRequired[int]
    status: NotRequired[Literal["running", "passed", "failed"]]
