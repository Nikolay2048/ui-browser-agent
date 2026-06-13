"""Deterministic action executor from lesson 7.

Implement the dispatch and node factory described in
docs/lessons/07-action-executor.md.
"""

from browser_agent.models import (
    ActionResult,
    BrowserAction,
    BrowserActionType,
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
        result = execute_action(
            browser=browser,
            action=state["proposed_action"],
        )

        return {
            "last_result": result,
            "step_count": state["step_count"] + 1,
        }

    return execute
