from __future__ import annotations

import json
import re

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama

from testing_agent.config import NUM_CTX, PLANNING_MODEL
from testing_agent.models import ExecutionPlan, PlannedAction, TestCase
from testing_agent.state import AgentState
from testing_agent.tools.browser_tools import BROWSER_TOOLS

# Build tool listing dynamically from tool definitions — single source of truth
_TOOLS_LISTING = "\n".join(
    f"- {t.name}: {(t.description or '').splitlines()[0]}"
    for t in BROWSER_TOOLS
)

_SYSTEM = f"""/no_think
You are a senior test automation engineer. Read the natural-language test case and produce
a precise browser automation plan.

Available tools:
{_TOOLS_LISTING}

Return ONLY valid JSON with no markdown or explanation:
{{
  "test_case_id": "...",
  "reasoning": "Explain your strategy: how you interpret each step, which locators you will use and why",
  "planned_actions": [
    {{
      "step_number": 1,
      "description": "...",
      "tool_name": "navigate_to_url",
      "tool_args": {{"url": "..."}},
      "expected_result": "..."
    }}
  ],
  "notes": "Additional remarks"
}}

Rules:
- planned_actions count MUST equal the number of test steps in the input — one entry per step, no more
- step_number MUST match the original test step number (1, 2, 3 ...)
- The first planned_action (step 1) MUST use navigate_to_url as the starting tool
- Each planned_action is an independent executor session: describe everything that session must do
  in the description field, including navigation, fills, clicks, verifications, and mark_step_complete
  DO NOT split "fill username" / "fill password" / "click login" into separate planned_actions —
  combine them into ONE: description = "Navigate to URL, fill username=X, fill password=Y, click Login, verify redirect"
- Locator priority: click_by_role > click_by_text > click_by_css; fill_by_label > fill_by_placeholder > fill_by_css
"""


def planner_node(state: AgentState) -> dict:
    tc: TestCase = state["test_case"]

    # ChatOllama with format="json" is more reliable than with_structured_output for qwen3
    llm = ChatOllama(
        model=PLANNING_MODEL,
        temperature=0,
        num_ctx=NUM_CTX,
        num_predict=4096,
        format="json",
    )

    steps_text = "\n".join(
        f"Step {s.step_number}: {s.step}\n  Expected result: {s.expected}"
        for s in tc.steps
    )

    human = f"""Create an automation plan for this test case:

ID: {tc.id}
Name: {tc.name}
Description: {tc.description}
Start URL: {tc.start_url}
Preconditions: {tc.preconditions}

Test steps:
{steps_text}
"""

    messages = [SystemMessage(_SYSTEM), HumanMessage(human)]
    print(f"  [Planner] Generating plan for {len(tc.steps)} steps...")

    plan: ExecutionPlan | None = None
    try:
        text = llm.invoke(messages).content
        data = _extract_json(text)
        if data:
            plan = _build_plan(data, tc)
    except Exception as e:
        print(f"  [Planner] parse failed ({type(e).__name__}: {e!s:.100})")

    if plan is None or not plan.planned_actions:
        print("  [Planner] using minimal fallback plan")
        plan = _minimal_plan(tc)

    reasoning = plan.reasoning or "Planner reasoning unavailable"
    print(f"  [Planner] {len(plan.planned_actions)} actions | {reasoning}")

    return {
        "execution_plan": plan,
        "current_step_index": 0,
        "overall_status": "running",
        "plan_reasoning": reasoning,
    }


def _extract_json(text: str) -> dict | None:
    # Strip qwen3 thinking tags
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass

    return None


def _build_plan(data: dict, tc: TestCase) -> ExecutionPlan:
    """Build ExecutionPlan from parsed JSON, tolerating minor schema mismatches.

    Enforces one planned_action per test step: if the LLM produced more actions than
    test steps, only the first action for each step_number is kept.
    """
    raw_actions = data.get("planned_actions", [])
    expected_steps = {s.step_number for s in tc.steps}

    # Parse all actions first
    parsed: list[PlannedAction] = []
    for i, raw in enumerate(raw_actions, start=1):
        step_num = raw.get("step_number") or raw.get("step_num") or i
        if not isinstance(step_num, int):
            try:
                step_num = int(step_num)
            except (ValueError, TypeError):
                step_num = i

        tool_args = raw.get("tool_args") or raw.get("args") or {}
        if not isinstance(tool_args, dict):
            tool_args = {}

        parsed.append(
            PlannedAction(
                step_number=step_num,
                description=raw.get("description") or raw.get("action") or f"Step {i}",
                tool_name=raw.get("tool_name") or raw.get("tool") or "get_page_context",
                tool_args=tool_args,
                expected_result=raw.get("expected_result") or raw.get("expected") or "",
            )
        )

    # Keep only the first planned_action per step_number
    seen: set[int] = set()
    actions: list[PlannedAction] = []
    for a in parsed:
        if a.step_number not in seen:
            seen.add(a.step_number)
            actions.append(a)

    # If LLM ignored step numbers and just used sequential 1..N > len(tc.steps),
    # remap them to the actual test step numbers
    if actions and not (seen & expected_steps):
        for action, step in zip(actions, tc.steps):
            action.step_number = step.step_number

    if len(actions) > len(tc.steps):
        print(f"  [Planner] trimmed {len(actions)} → {len(tc.steps)} actions (one per step)")
        actions = actions[: len(tc.steps)]

    return ExecutionPlan(
        test_case_id=data.get("test_case_id") or tc.id,
        planned_actions=actions,
        notes=data.get("notes") or "",
        reasoning=data.get("reasoning") or "",
    )


def _minimal_plan(tc: TestCase) -> ExecutionPlan:
    """Last-resort: navigate first, then one action per test step."""
    actions = [
        PlannedAction(
            step_number=0,
            description=f"Navigate to start URL: {tc.start_url}",
            tool_name="navigate_to_url",
            tool_args={"url": tc.start_url},
            expected_result="Page loaded",
        )
    ]
    for s in tc.steps:
        actions.append(
            PlannedAction(
                step_number=s.step_number,
                description=s.step,
                tool_name="get_page_context",
                tool_args={},
                expected_result=s.expected,
            )
        )
    return ExecutionPlan(
        test_case_id=tc.id,
        reasoning="Fallback: minimal plan — executor works from step descriptions",
        planned_actions=actions,
        notes="Fallback plan",
    )
