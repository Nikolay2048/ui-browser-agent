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
Ты старший инженер по автоматизации тестирования. Прочитай тест-кейс на естественном языке
и составь точный план автоматизации в браузере.

Доступные инструменты:
{_TOOLS_LISTING}

Верни ТОЛЬКО валидный JSON без каких-либо пояснений или markdown:
{{
  "test_case_id": "...",
  "reasoning": "Объясни свою стратегию: как ты интерпретируешь каждый шаг, какие локаторы выберешь и почему",
  "planned_actions": [
    {{
      "step_number": 1,
      "description": "...",
      "tool_name": "navigate_to_url",
      "tool_args": {{"url": "..."}},
      "expected_result": "..."
    }}
  ],
  "notes": "Дополнительные замечания"
}}

Стратегия:
- ПЕРВОЕ действие ВСЕГДА navigate_to_url со стартовым URL тест-кейса
- Локаторы по приоритету: click_by_role > click_by_text > click_by_css; fill_by_label > fill_by_placeholder > fill_by_css
- После смены страницы — добавляй verify_text_visible или verify_element_visible
- После важного взаимодействия — take_screenshot
- ПОСЛЕДНЕЕ действие каждого шага — mark_step_complete(status, actual_result, screenshot_name)
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
        f"Шаг {s.step_number}: {s.step}\n  Ожидаемый результат: {s.expected}"
        for s in tc.steps
    )

    human = f"""Составь план автоматизации для тест-кейса:

ID: {tc.id}
Название: {tc.name}
Описание: {tc.description}
Стартовый URL: {tc.start_url}
Предусловия: {tc.preconditions}

Шаги тест-кейса:
{steps_text}
"""

    messages = [SystemMessage(_SYSTEM), HumanMessage(human)]

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

    reasoning = plan.reasoning or "Рассуждение планировщика недоступно"
    print(f"  [Planner] {len(plan.planned_actions)} actions | {reasoning[:100]}...")

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
    """Build ExecutionPlan from parsed JSON, tolerating minor schema mismatches."""
    actions: list[PlannedAction] = []
    for i, raw in enumerate(data.get("planned_actions", []), start=1):
        step_num = raw.get("step_number") or raw.get("step_num") or i
        if not isinstance(step_num, int):
            try:
                step_num = int(step_num)
            except (ValueError, TypeError):
                step_num = i

        tool_args = raw.get("tool_args") or raw.get("args") or {}
        if not isinstance(tool_args, dict):
            tool_args = {}

        actions.append(
            PlannedAction(
                step_number=step_num,
                description=raw.get("description") or raw.get("action") or f"Step {i}",
                tool_name=raw.get("tool_name") or raw.get("tool") or "get_page_context",
                tool_args=tool_args,
                expected_result=raw.get("expected_result") or raw.get("expected") or "",
            )
        )

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
            description=f"Перейти на стартовый URL: {tc.start_url}",
            tool_name="navigate_to_url",
            tool_args={"url": tc.start_url},
            expected_result="Страница загружена",
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
        reasoning="Fallback: minimal plan — executor работает по описанию шагов",
        planned_actions=actions,
        notes="Fallback plan",
    )
