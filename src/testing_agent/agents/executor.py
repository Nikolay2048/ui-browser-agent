from __future__ import annotations

import json
import time

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

from testing_agent.browser_manager import BrowserManager
from testing_agent.config import MAX_STEP_ITERATIONS, get_execution_llm
from testing_agent.models import ExecutionPlan, PlannedAction, StepResult, TestCase
from testing_agent.state import AgentState
from testing_agent.tools.browser_tools import BROWSER_TOOLS

_TOOL_MAP = {t.name: t for t in BROWSER_TOOLS}

_SYSTEM = """/no_think
You are a QA automation engineer operating a real browser via tools.

Your goal: execute ONE test step completely, then call mark_step_complete.

Workflow:
1. Call get_page_context() to see the current page
2. Execute the required action(s)
3. Verify the expected result (use verify_text_visible or verify_element_visible)
4. Take a screenshot with take_screenshot(descriptive_name)
5. Call mark_step_complete(status, actual_result, screenshot_name)

Locator priority (use in this order):
  click: click_by_role > click_by_text > click_by_css
  type:  fill_by_label > fill_by_placeholder > fill_by_css

If an action returns NOT_FOUND or ERROR:
- Try a different locator strategy
- Look at get_page_context() output to find the right element

mark_step_complete MUST be the last tool call. Do not loop after calling it.
status must be: 'passed', 'failed', or 'broken'
"""


def _run_tool(tool_call: dict) -> str:
    name = tool_call["name"]
    args = tool_call["args"]
    if name not in _TOOL_MAP:
        return f"ERROR: unknown tool '{name}'"
    try:
        return str(_TOOL_MAP[name].invoke(args))
    except Exception as e:
        return f"ERROR in {name}: {e}"


def executor_node(state: AgentState) -> dict:
    step_idx = state["current_step_index"]
    plan: ExecutionPlan | None = state.get("execution_plan")

    if plan is None or step_idx >= len(plan.planned_actions):
        return {"current_step_index": step_idx + 1}

    action: PlannedAction = plan.planned_actions[step_idx]
    start_time = time.time()

    llm = get_execution_llm()
    llm_with_tools = llm.bind_tools(BROWSER_TOOLS)

    tc: TestCase = state["test_case"]
    messages = [
        SystemMessage(_SYSTEM),
        HumanMessage(
            f"Execute step {action.step_number}: {action.description}\n"
            f"Expected result: {action.expected_result}\n\n"
            f"Test start URL: {tc.start_url}\n"
            f"Planner suggestion — tool: {action.tool_name}, args: {json.dumps(action.tool_args)}\n"
            f"Start with get_page_context() first. If the page is blank or wrong domain, "
            f"navigate to {tc.start_url} before doing anything else."
        ),
    ]

    tool_calls_log: list[str] = []
    step_result_data: dict | None = None
    no_tool_retries = 0

    for _ in range(MAX_STEP_ITERATIONS):
        response = llm_with_tools.invoke(messages)
        messages.append(response)

        if not response.tool_calls:
            if step_result_data:
                break
            no_tool_retries += 1
            if no_tool_retries <= 2:
                # Nudge the LLM to actually use tools
                messages.append(
                    HumanMessage(
                        "You must call tools to complete this step. "
                        "Start with get_page_context() to see what is currently on the page, "
                        f"then navigate to {tc.start_url} if needed."
                    )
                )
                continue
            step_result_data = {
                "status": "broken",
                "actual_result": str(response.content)[:500] or "No tool calls made",
                "screenshot_path": None,
            }
            break

        done = False
        for tc in response.tool_calls:
            arg_preview = json.dumps(tc["args"], ensure_ascii=False)[:120]
            tool_calls_log.append(f"{tc['name']}({arg_preview})")

            result = _run_tool(tc)
            messages.append(ToolMessage(content=result, tool_call_id=tc["id"]))

            if tc["name"] == "mark_step_complete" or (
                isinstance(result, str) and result.startswith("STEP_COMPLETE::")
            ):
                mgr = BrowserManager.get_instance()
                stored = mgr._last_step_result
                if stored:
                    step_result_data = stored
                    mgr._last_step_result = None
                else:
                    parts = result.split("::")
                    step_result_data = {
                        "status": parts[1] if len(parts) > 1 else "broken",
                        "actual_result": parts[2] if len(parts) > 2 else result,
                        "screenshot_path": None,
                    }
                done = True
                break

        if done:
            break

    duration_ms = int((time.time() - start_time) * 1000)

    if step_result_data is None:
        step_result_data = {
            "status": "broken",
            "actual_result": "Step did not complete — max iterations reached",
            "screenshot_path": None,
        }

    sr = StepResult(
        step_number=action.step_number,
        description=action.description,
        status=step_result_data["status"],
        actual_result=step_result_data["actual_result"],
        expected_result=action.expected_result,
        screenshot_path=step_result_data.get("screenshot_path"),
        duration_ms=duration_ms,
        tool_calls=tool_calls_log,
    )

    print(
        f"  Step {action.step_number} [{sr.status.upper()}] {action.description[:60]} "
        f"({duration_ms}ms)"
    )

    return {
        "step_results": [sr],
        "current_step_index": step_idx + 1,
    }
