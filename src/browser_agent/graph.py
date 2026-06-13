"""Autonomous agent loop from lesson 10.

Implement routers and graph described in
learning/lesson_10_autonomous_loop/README.md.
"""
from browser_agent.state import AgentState


def initialize(state: AgentState) -> dict:
    """Initialize one agent run."""
    return {
        "current_url": state["test_case"].start_url,
        "route": [],
        "step_count": 0,
        "status": "running",
    }


def pass_run(_state: AgentState) -> dict:
    """Mark the scenario as passed."""
    return {"status": "passed"}


def fail_run(_state: AgentState) -> dict:
    """Mark the scenario as failed."""
    return {"status": "failed"}


def route_planned_action(state: AgentState) -> str:
    """TODO: route finish actions to success and other actions to executor."""
    raise NotImplementedError


def route_after_execution(state: AgentState) -> str:
    """TODO: retry observation or terminate after failure/step limit."""
    raise NotImplementedError


def build_agent_graph(model, browser):
    """TODO: compile the first autonomous observe-plan-act loop."""
    raise NotImplementedError
