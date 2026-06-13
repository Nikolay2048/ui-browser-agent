"""Agent graph with browser observation from lesson 9."""
from langgraph.constants import START, END
from langgraph.graph import StateGraph

from browser_agent.executor import make_execute_node
from browser_agent.graph import initialize
from browser_agent.observer import make_observe_node
from browser_agent.planner_graph import make_plan_node
from browser_agent.state import AgentState


def build_observing_agent_graph(model, browser):
    """compile initialize -> observe -> plan -> execute."""
    builder = StateGraph(AgentState)

    # 1. Регистрация узлов
    builder.add_node("initialize", initialize)
    builder.add_node("observe", make_observe_node(browser))
    builder.add_node("plan", make_plan_node(model))
    builder.add_node("execute", make_execute_node(browser))

    # 2. Безусловный переход
    builder.add_edge(START, "initialize")
    builder.add_edge("initialize", "observe")
    builder.add_edge("observe", "plan")
    builder.add_edge("plan", "execute")
    builder.add_edge("execute", END)

    return builder.compile()
