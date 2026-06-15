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

_SYSTEM = """You are a QA automation engineer operating a real browser via tools.

Your goal: execute ONE test step, verify the result, then call mark_step_complete.

FLOW (follow in order):
1. Call get_page_context() to see the current page
2. Execute the required action(s) — navigate, click, fill, select, etc.
3. Verify the expected result using verify_text_visible or verify_element_visible
4. Call mark_step_complete(status, actual_result, screenshot_name)
   screenshot_name is optional — pass a short name to capture the final state

CRITICAL RULES:
- mark_step_complete MUST be the final tool call — do not call anything after it
- Once you have verified the result, call mark_step_complete IMMEDIATELY
  Do NOT make additional tool calls after verification
- verify_text_visible returns VISIBLE for text that SHOULD be present → status MUST be 'passed'
- verify_text_visible returns NOT_VISIBLE for text that SHOULD be present → status MUST be 'failed'
- verify_text_visible returns NOT_VISIBLE for text that SHOULD be absent → that is CORRECT, not a failure
- ERROR or NOT_FOUND after 2 locator attempts → status MUST be 'broken'
- Valid status values: 'passed', 'failed', 'broken' — NOTHING ELSE

Locator priority (use in this order):
  click: click_by_role > click_by_text > click_by_css
  type:  fill_by_label > fill_by_placeholder > fill_by_css

If a locator returns NOT_FOUND: try ONE alternative strategy, then complete the step.

NAVIGATION BEFORE ACTION:
- If the step description says "open product page X", "navigate to X", "go to cart", or "click Back to Products",
  you MUST perform that navigation FIRST before any click/fill/verify action.
- After get_page_context(), if the current page is NOT the intended target page, navigate there first.
- NEVER click a button (Remove, Add to cart, etc.) on the current page if the step says to navigate
  to a different page first — even if the button is visible on the current page.

HANDLING LISTS WITH REPEATED BUTTON LABELS (e.g. multiple "Remove" or "Add to Cart" buttons):
- call get_page_context() first to inspect the page structure
- find a data-test, data-id, aria-label, or parent-child CSS selector that uniquely
  identifies the button for the specific item (e.g. [data-test="remove-sauce-labs-bike-light"])
- use click_by_css with that specific selector — do NOT use click_by_text when
  multiple buttons share the same label, as it clicks the first one found

CART BADGE COUNT: to read the number shown on the cart icon, use:
  get_element_text(selector='span.shopping_cart_badge')
  Do NOT use get_element_attribute with 'innerText'/'textContent' — those return ATTRIBUTE_NOT_FOUND.
  Alternatively, use verify_text_visible('2') to confirm the number is visible on page.

AFTER REMOVING AN ITEM FROM A CART / LIST:
- the item text may still appear on the catalog/inventory page — this is NORMAL
- verify success by: (1) checking the cart counter decreased, OR (2) navigating to
  the cart page to confirm the item is no longer listed
- do NOT re-click Remove just because the item text is still visible on the inventory page
"""


def _fmt_args(args: dict) -> str:
    """One-line representation of tool arguments — no truncation."""
    if not args:
        return ""
    return ", ".join(f"{k}={v!r}" for k, v in args.items())


def _fmt_result(tool_name: str, result: str) -> str:
    """One-line summary of a tool result. get_page_context is compacted to avoid noise."""
    if tool_name == "get_page_context":
        try:
            data = json.loads(result)
            url = data.get("url", "")
            elems = data.get("interactive_elements", [])
            alerts = data.get("alerts_messages", [])
            alert_str = f" | alerts: {alerts[0]!r}" if alerts else ""
            return f"url={url} | {len(elems)} elements{alert_str}"
        except Exception:
            pass
    if tool_name == "mark_step_complete":
        parts = result.split("::")
        status = parts[1] if len(parts) > 1 else "?"
        return f"COMPLETE -> {status.upper()}"
    return result.replace("\n", " ")


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

    test_case: TestCase = state["test_case"]

    total = len(plan.planned_actions)
    print(
        f"\n  [Action {step_idx + 1}/{total}] "
        f"step={action.step_number} | {action.description}"
    )

    messages = [
        SystemMessage(_SYSTEM),
        HumanMessage(
            f"Execute step {action.step_number}: {action.description}\n"
            f"Expected result: {action.expected_result}\n\n"
            f"Test start URL: {test_case.start_url}\n"
            f"Planner suggestion — tool: {action.tool_name}, args: {json.dumps(action.tool_args)}\n"
            f"Start with get_page_context() first. If the page is blank or wrong domain, "
            f"navigate to {test_case.start_url} before doing anything else."
        ),
    ]

    tool_calls_log: list[str] = []
    step_result_data: dict | None = None
    no_tool_retries = 0

    for iteration in range(MAX_STEP_ITERATIONS):
        response = llm_with_tools.invoke(messages)
        messages.append(response)

        if not response.tool_calls:
            if step_result_data:
                break
            no_tool_retries += 1
            if no_tool_retries <= 2:
                print(f"    [retry {no_tool_retries}] no tool call — nudging model")
                messages.append(
                    HumanMessage(
                        "You MUST call a tool — do not respond with text only. "
                        "Options: get_page_context() to inspect the page, "
                        "verify_text_visible('text') to check content, "
                        "select_option(css, value) for dropdowns, "
                        "get_element_attribute(selector, attr) for HTML attributes, "
                        f"navigate_to_url('{test_case.start_url}') if page is wrong, "
                        "or mark_step_complete('broken', 'reason') if truly stuck."
                    )
                )
                continue
            step_result_data = {
                "status": "broken",
                "actual_result": str(response.content) or "No tool calls made",
                "screenshot_path": None,
            }
            print(f"    [broken] model returned no tool calls after nudges")
            break

        done = False
        for tool_call in response.tool_calls:
            name = tool_call["name"]
            print(f"    -> {name}({_fmt_args(tool_call['args'])})")

            tool_calls_log.append(f"{name}({json.dumps(tool_call['args'], ensure_ascii=False)})")

            result = _run_tool(tool_call)
            messages.append(ToolMessage(content=result, tool_call_id=tool_call["id"]))

            print(f"    <- {_fmt_result(name, result)}")

            if name == "mark_step_complete" or (
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

        # Two iterations before the hard limit — give the LLM one last chance to decide
        if iteration == MAX_STEP_ITERATIONS - 3 and not done:
            print(f"    [deadline] iteration {iteration + 1}/{MAX_STEP_ITERATIONS} — nudging to complete")
            messages.append(
                HumanMessage(
                    "FINAL CHANCE: call mark_step_complete NOW using what you already know. "
                    "Expected result observed → status='passed'. "
                    "Expected result NOT observed → status='failed'. "
                    "Could not determine → status='broken'. "
                    "Do NOT call any other tool."
                )
            )

    duration_ms = int((time.time() - start_time) * 1000)

    if step_result_data is None:
        step_result_data = {
            "status": "broken",
            "actual_result": "Step did not complete — max iterations reached",
            "screenshot_path": None,
        }
        print(f"    [broken] max iterations ({MAX_STEP_ITERATIONS}) reached")

    _VALID_STATUSES = {"passed", "failed", "skipped", "broken"}
    raw_status = str(step_result_data.get("status", "broken")).lower()
    # LLMs sometimes use synonyms — map them to valid values
    _STATUS_ALIASES = {"complete": "passed", "completed": "passed", "success": "passed",
                       "error": "broken", "timeout": "broken", "unknown": "broken"}
    status = raw_status if raw_status in _VALID_STATUSES else _STATUS_ALIASES.get(raw_status, "broken")

    sr = StepResult(
        step_number=action.step_number,
        description=action.description,
        status=status,
        actual_result=step_result_data["actual_result"],
        expected_result=action.expected_result,
        screenshot_path=step_result_data.get("screenshot_path"),
        duration_ms=duration_ms,
        tool_calls=tool_calls_log,
    )

    status_icon = "+" if sr.status == "passed" else "-"
    print(
        f"  [{status_icon}] Step {action.step_number} [{sr.status.upper()}]"
        f"  {duration_ms // 1000}s"
    )

    return {
        "step_results": [sr],
        "current_step_index": step_idx + 1,
    }
