"""Autonomous agent loop from lesson 10.

Implement routers and graph described in
learning/lesson_10_autonomous_loop/README.md.
"""
from langgraph.constants import END, START
from langgraph.graph import StateGraph

from browser_agent.classifier import make_classifier_node
from browser_agent.executor import make_execute_node
from browser_agent.judge import make_judge_node
from browser_agent.models import BrowserActionType, RunTermination, TerminationKind
from browser_agent.observer import make_observe_node
from browser_agent.planner import make_plan_node
from browser_agent.state import AgentState


def initialize(state: AgentState) -> dict:
    """Initialize one agent run."""
    return {
        "current_url": state["test_case"].start_url,
        "route": [],
        "step_count": 0,
        "failure_count": 0,
        "status": "running",
    }


def pass_run(state: AgentState) -> dict:
    """Mark the scenario as passed."""
    return {
        "status": "passed",
        "termination": RunTermination(
            kind=TerminationKind.JUDGE_PASSED,
            message="Judge proved every expected result.",
        ),
    }


def fail_run(state: AgentState) -> dict:
    """Mark the scenario as failed."""
    if state["step_count"] >= state["test_case"].max_steps:
        kind = TerminationKind.STEP_LIMIT
        message = f"Step limit {state['test_case'].max_steps} was reached."
    elif state["failure_count"] >= state["test_case"].max_failures:
        kind = TerminationKind.FAILURE_LIMIT
        message = f"Failure limit {state['test_case'].max_failures} was reached."
    elif "verdict" in state and not state["verdict"].passed:
        kind = TerminationKind.JUDGE_FAILED
        message = state["verdict"].summary
    else:
        raise RuntimeError("Cannot determine failure termination reason")
    return {
        "status": "failed",
        "termination": RunTermination(
            kind=kind,
            message=message
        )}


def route_planned_action(state: AgentState) -> str:
    """Route finish actions to success and other actions to executor."""
    if state["proposed_action"].action == BrowserActionType.FINISH:
        return "judge"
    return "execute"


def route_after_execution(state: AgentState) -> str:
    if state["step_count"] >= state["test_case"].max_steps:
        return "fail_run"

    if state["last_result"].success:
        return "observe"

    if state["failure_count"] >= state["test_case"].max_failures:
        return "fail_run"

    return "observe"


def route_after_judge(state: AgentState) -> str:
    if state["verdict"].passed:
        return "pass_run"
    return "fail_run"


def build_agent_graph(model, browser, judge_model=None, classifier_model=None):
    """Compile the first autonomous observe-plan-act loop."""
    judge_model = judge_model or model
    classifier_model = classifier_model or model

    builder = StateGraph(AgentState)

    builder.add_node("initialize", initialize)
    builder.add_node("observe", make_observe_node(browser))
    builder.add_node("plan", make_plan_node(model))
    builder.add_node("execute", make_execute_node(browser))
    builder.add_node("judge", make_judge_node(judge_model))
    builder.add_node("classify_failure", make_classifier_node(classifier_model))
    builder.add_node("pass_run", pass_run)
    builder.add_node("fail_run", fail_run)

    builder.add_edge(START, "initialize")
    builder.add_edge("initialize", "observe")
    builder.add_edge("observe", "plan")
    builder.add_edge("pass_run", END)
    builder.add_edge("fail_run", "classify_failure")
    builder.add_edge("classify_failure", END)

    builder.add_conditional_edges(
        "plan",
        route_planned_action,
        {
            "judge": "judge",
            "execute": "execute"

        }
    )
    builder.add_conditional_edges(
        "judge",
        route_after_judge,
        {
            "pass_run": "pass_run",
            "fail_run": "fail_run",
        },
    )
    builder.add_conditional_edges(
        "execute",
        route_after_execution,
        {
            "fail_run": "fail_run",
            "observe": "observe"
        })

    return builder.compile()
