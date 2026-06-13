"""First end-to-end agent graph from lesson 8.

Implement the graph described in docs/lessons/08-plan-execute-graph.md.
"""
from langgraph.constants import END, START
from langgraph.graph import StateGraph

from browser_agent.executor import make_execute_node
from browser_agent.graph import initialize
from browser_agent.planner_graph import make_plan_node
from browser_agent.state import AgentState


def build_agent_graph(model, browser):
    """compile initialize -> plan -> execute."""
    builder = StateGraph(AgentState)

    builder.add_node("initialize", initialize)
    builder.add_node("plan", make_plan_node(model))
    builder.add_node("execute", make_execute_node(browser))

    builder.add_edge(START, "initialize")
    builder.add_edge("initialize", "plan")
    builder.add_edge("plan", "execute")
    builder.add_edge("execute", END)

    return builder.compile()
