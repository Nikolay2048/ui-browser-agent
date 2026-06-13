"""LangGraph integration for the LLM planner.

Lesson 6: implement the node factory and graph described in
docs/lessons/06-planner-node.md.
"""

from langgraph.constants import END, START
from langgraph.graph import StateGraph

from browser_agent.graph import initialize
from browser_agent.planner import plan_next_action
from browser_agent.state import AgentState


def make_plan_node(model):
    """create and return a LangGraph node that uses the supplied model."""

    def plan(state: AgentState) -> dict:
        action = plan_next_action(
            model=model,
            test_case=state["test_case"],
            page_snapshot=state["page_snapshot"],
        )

        return {"proposed_action": action}

    return plan


def build_planner_graph(model):
    """compile START -> initialize -> plan -> END."""
    builder = StateGraph(AgentState)

    # 1. Регистрация узлов
    builder.add_node("initialize", initialize)
    builder.add_node("plan", make_plan_node(model))

    # 2. Безусловный переход
    builder.add_edge(START, "initialize")
    builder.add_edge("initialize", "plan")

    # 4. Завершение обеих веток
    builder.add_edge("plan", END)

    return builder.compile()
