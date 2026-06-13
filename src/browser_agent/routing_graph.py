"""Conditional LangGraph from lesson 3.

Implement the router, terminal nodes, and graph described in
docs/lessons/03-conditional-routing.md.
"""
from langgraph.constants import END, START
from langgraph.graph import StateGraph

from browser_agent.graph import initialize
from browser_agent.state import AgentState


def route_start_url(state: AgentState) -> str:
    """return the name of the next node."""
    if state["current_url"].startswith(("http://", "https://")):
        return "pass_run"

    return "fail_run"


def pass_run(state: AgentState):
    """return a successful status update."""
    return {"status": "passed"}


def fail_run(state: AgentState):
    """return a failed status update."""
    return {"status": "failed"}


def build_routing_graph():
    builder = StateGraph(AgentState)

    # 1. Регистрация узлов
    builder.add_node("initialize", initialize)
    builder.add_node("pass_run", pass_run)
    builder.add_node("fail_run", fail_run)

    # 2. Безусловный переход
    builder.add_edge(START, "initialize")

    # 3. Условный переход
    builder.add_conditional_edges(
        "initialize",
        route_start_url,
        {
            "pass_run": "pass_run",
            "fail_run": "fail_run",
        },
    )

    # 4. Завершение обеих веток
    builder.add_edge("pass_run", END)
    builder.add_edge("fail_run", END)

    return builder.compile()
