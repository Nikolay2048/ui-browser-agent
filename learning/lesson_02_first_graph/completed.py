"""The first deterministic LangGraph.

Lesson 2: implement the nodes and graph described in
docs/lessons/02-state-and-graph.md.
"""
from langgraph.constants import START, END
from langgraph.graph import StateGraph
from langgraph.graph.state import CompiledStateGraph

from browser_agent.state import AgentState


def initialize(state: AgentState) -> dict:
    """initialize a new agent run."""
    return {
        "current_url": state["test_case"].start_url,
        "route": [],
        "step_count": 0,
        "status": "running",
    }


def complete(state: AgentState) -> dict:
    """mark the learning graph as successfully completed."""
    return {"status": "passed"}


def build_learning_graph() -> CompiledStateGraph:
    """compile and return START -> initialize -> complete -> END."""
    builder = StateGraph(AgentState)

    builder.add_node("initialize", initialize)
    builder.add_node("complete", complete)

    builder.add_edge(START, "initialize")
    builder.add_edge("initialize", "complete")
    builder.add_edge("complete", END)

    return builder.compile()
