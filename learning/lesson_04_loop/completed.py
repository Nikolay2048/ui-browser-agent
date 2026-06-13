"""Deterministic agent loop from lesson 4.

Implement the nodes, router, and graph described in
docs/lessons/04-agent-loop.md.
"""
from langgraph.constants import START, END
from langgraph.graph import StateGraph

from browser_agent.graph import initialize
from browser_agent.state import AgentState


def perform_step(state) -> dict:
    """ increment the step counter."""
    return {"step_count": state["step_count"] + 1}


def route_after_step(state):
    """ continue the loop or finish it."""
    if state["step_count"] < state["test_case"].max_steps:
        return "perform_step"
    return "finish_run"


def finish_run(state):
    """ return the final successful status."""
    return {"status": "passed"}


def build_loop_graph():
    """ compile initialize -> perform_step loop -> finish_run."""
    builder = StateGraph(AgentState)

    # 1. Регистрация узлов
    builder.add_node("initialize", initialize)
    builder.add_node("perform_step", perform_step)
    builder.add_node("finish_run", finish_run)

    # 2. Безусловный переход
    builder.add_edge(START, "initialize")
    builder.add_edge("initialize", "perform_step")

    # 3. Условный переход
    builder.add_conditional_edges(
        "perform_step",
        route_after_step,
        {
            "perform_step": "perform_step",
            "finish_run": "finish_run",
        },
    )

    # 4. Завершение обеих веток
    builder.add_edge("finish_run", END)

    return builder.compile()