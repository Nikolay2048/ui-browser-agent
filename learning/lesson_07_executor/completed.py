"""Completed deterministic executor after lesson 7."""

from browser_agent.domain import ActionResult, BrowserActionType
from browser_agent.state import AgentState


def execute_action(browser, action):
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
        return ActionResult(
            success=True,
            url_before=url_before,
            url_after=browser.current_url,
            screenshot_path=screenshot_path,
        )
    except Exception as error:
        screenshot_path = browser.screenshot()
        return ActionResult(
            success=False,
            url_before=url_before,
            url_after=browser.current_url,
            error=str(error),
            screenshot_path=screenshot_path,
        )


def make_execute_node(browser):
    def execute(state: AgentState) -> dict:
        result = execute_action(browser, state["proposed_action"])
        return {
            "last_result": result,
            "step_count": state["step_count"] + 1,
        }

    return execute
