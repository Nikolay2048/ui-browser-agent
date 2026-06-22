"""Deterministic action executor from lesson 7.

The related lesson is archived in learning/lesson_07_executor/README.md.
"""

from browser_agent.domain import (
    ActionResult,
    BrowserActionType,
    ExecutionStep,
)
from browser_agent.state import AgentState


def execute_action(browser, action):
    """dispatch BrowserAction to the browser adapter."""
    url_before = browser.current_url

    try:
        if action.action == BrowserActionType.CLICK:
            browser.click(action.target)

        elif action.action == BrowserActionType.FILL:
            browser.fill(action.target, action.value)

        elif action.action == BrowserActionType.PRESS:
            browser.press(action.target, action.value)

        elif action.action == BrowserActionType.ASSERT_TEXT:
            browser.assert_text(action.target)

        elif action.action == BrowserActionType.FINISH:
            pass

        screenshot_path = browser.screenshot()
        url_after = browser.current_url

        return ActionResult(
            success=True,
            url_before=url_before,
            url_after=url_after,
            screenshot_path=screenshot_path,
        )

    except Exception as error:
        screenshot_path = browser.screenshot()
        url_after = browser.current_url

        return ActionResult(
            success=False,
            url_before=url_before,
            url_after=url_after,
            error=str(error),
            screenshot_path=screenshot_path,
        )


def make_execute_node(browser):
    """return a LangGraph node that executes proposed_action."""

    def execute(state: AgentState) -> dict:
        next_step_number = state["step_count"] + 1

        result = execute_action(
            browser=browser,
            action=state["proposed_action"],
        )

        next_failure_count = state["failure_count"]
        if not result.success:
            next_failure_count += 1
        step = ExecutionStep(
            step_number=next_step_number,
            page_snapshot=state["page_snapshot"],
            action=state["proposed_action"],
            result=result,
        )

        return {
            "last_result": result,
            "step_count": next_step_number,
            "failure_count": next_failure_count,
            "route": [*state["route"], step],
        }

    return execute
