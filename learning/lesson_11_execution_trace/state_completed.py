"""Relevant AgentState fragment completed in lesson 11."""

from typing import NotRequired, Required, TypedDict

from browser_agent.domain import ExecutionStep, TestCase


class AgentState(TypedDict):
    test_case: Required[TestCase]
    route: NotRequired[list[ExecutionStep]]
