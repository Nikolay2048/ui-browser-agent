"""Autonomous agent loop from lesson 10.

Implement routers and graph described in
learning/lesson_10_autonomous_loop/README.md.
"""
from langgraph.constants import END, START
from langgraph.graph import StateGraph

from browser_agent.executor import make_execute_node
from browser_agent.models import BrowserActionType
from browser_agent.observer import make_observe_node
from browser_agent.planner import make_plan_node
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
    """Route finish actions to success and other actions to executor."""
    if state["proposed_action"].action == BrowserActionType.FINISH:
        return "pass_run"
    return "execute"


def route_after_execution(state: AgentState) -> str:
    """Retry observation or terminate after failure/step limit."""
    if not state["last_result"].success or state["step_count"] >= state["test_case"].max_steps:
        return "fail_run"
    return "observe"


def build_agent_graph(model, browser):
    """Compile the first autonomous observe-plan-act loop."""
    builder = StateGraph(AgentState)

    builder.add_node("initialize", initialize)
    builder.add_node("observe", make_observe_node(browser))
    builder.add_node("plan", make_plan_node(model))
    builder.add_node("execute", make_execute_node(browser))
    builder.add_node("pass_run", pass_run)
    builder.add_node("fail_run", fail_run)

    builder.add_edge(START, "initialize")
    builder.add_edge("initialize", "observe")
    builder.add_edge("observe", "plan")
    builder.add_edge("pass_run", END)
    builder.add_edge("fail_run", END)

    builder.add_conditional_edges(
        "plan",
        route_planned_action,
        {
            "pass_run": "pass_run",
            "execute": "execute"

        }
    )
    builder.add_conditional_edges(
        "execute",
        route_after_execution,
        {
            "fail_run": "fail_run",
            "observe": "observe"
        })

    return builder.compile()
