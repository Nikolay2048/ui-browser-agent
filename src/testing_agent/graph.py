from __future__ import annotations

import time
from datetime import datetime

from langgraph.graph import END, START, StateGraph

from testing_agent.agents.executor import executor_node
from testing_agent.agents.observer import observer_node
from testing_agent.agents.planner import planner_node
from testing_agent.agents.test_generator import test_generator_node
from testing_agent.models import TestCase
from testing_agent.reporting.allure_reporter import write_allure_result
from testing_agent.state import AgentState

_graph_start_time: dict[str, str] = {}


def _allure_node(state: AgentState) -> dict:
    tc: TestCase = state["test_case"]
    step_results = state.get("step_results", [])
    bugs = state.get("bugs", [])
    code = state.get("generated_test_code", "")
    status = state.get("overall_status", "broken")
    clarification = state.get("clarification")

    start_iso = _graph_start_time.get(tc.id, datetime.now().isoformat())
    duration_ms = sum(r.duration_ms for r in step_results)

    write_allure_result(
        test_case=tc,
        step_results=step_results,
        bugs=bugs,
        generated_code=code,
        overall_status=status,
        start_iso=start_iso,
        duration_ms=duration_ms,
        clarification=clarification,
        plan_reasoning=state.get("plan_reasoning", ""),
        analysis_reasoning=state.get("analysis_reasoning", ""),
    )
    return {}


def _route_after_step(state: AgentState) -> str:
    plan = state.get("execution_plan")
    idx = state.get("current_step_index", 0)
    if plan is not None and idx < len(plan.planned_actions):
        return "execute_step"
    return "observer"


def build_testing_graph():
    builder = StateGraph(AgentState)

    builder.add_node("planner", planner_node)
    builder.add_node("execute_step", executor_node)
    builder.add_node("observer", observer_node)
    builder.add_node("test_generator", test_generator_node)
    builder.add_node("allure_reporter", _allure_node)

    builder.add_edge(START, "planner")
    builder.add_edge("planner", "execute_step")

    builder.add_conditional_edges(
        "execute_step",
        _route_after_step,
        {"execute_step": "execute_step", "observer": "observer"},
    )

    builder.add_edge("observer", "test_generator")
    builder.add_edge("test_generator", "allure_reporter")
    builder.add_edge("allure_reporter", END)

    return builder.compile()


_compiled_graph = None


def get_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_testing_graph()
    return _compiled_graph


def run_test_case(test_case: TestCase) -> AgentState:
    _graph_start_time[test_case.id] = datetime.now().isoformat()

    initial: AgentState = {
        "test_case": test_case,
        "execution_plan": None,
        "current_step_index": 0,
        "step_results": [],
        "bugs": [],
        "messages": [],
        "generated_test_code": "",
        "overall_status": "running",
        "clarification": None,
        "plan_reasoning": "",
        "analysis_reasoning": "",
        "error": None,
    }

    graph = get_graph()
    return graph.invoke(initial)
