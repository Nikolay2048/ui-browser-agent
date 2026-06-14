"""Executor node completed in lesson 11."""

from browser_agent.executor import execute_action
from browser_agent.models import ExecutionStep
from browser_agent.state import AgentState


def make_execute_node(browser):
    def execute(state: AgentState) -> dict:
        next_step_number = state["step_count"] + 1
        result = execute_action(
            browser=browser,
            action=state["proposed_action"],
        )
        step = ExecutionStep(
            step_number=next_step_number,
            page_snapshot=state["page_snapshot"],
            action=state["proposed_action"],
            result=result,
        )
        return {
            "last_result": result,
            "step_count": next_step_number,
            "route": [*state["route"], step],
        }

    return execute
