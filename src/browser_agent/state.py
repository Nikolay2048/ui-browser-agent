"""LangGraph state contract.

Lesson 2: implement AgentState as described in docs/lessons/02-state-and-graph.md.
"""
from typing import TypedDict, NotRequired, Required, Literal

from src.browser_agent.models import TestCase, ActionResult


class AgentState(TypedDict):
    test_case: Required[TestCase]

    current_url: NotRequired[str]
    route: NotRequired[list[ActionResult]]
    step_count: NotRequired[int]
    status: NotRequired[Literal["running", "passed", "failed"]]
