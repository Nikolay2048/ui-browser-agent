from __future__ import annotations

import json
import re

from langchain_core.messages import HumanMessage, SystemMessage

from testing_agent.config import get_planning_llm
from testing_agent.models import (
    BugReport,
    ClarificationItem,
    ClarificationRequest,
    StepResult,
    TestCase,
)
from testing_agent.state import AgentState

_SYSTEM = """/no_think
You are a senior QA analyst. Analyze test execution results and produce two outputs:
1. Bug reports for real website defects
2. Clarification requests for ambiguous or incomplete test case steps

Return ONLY valid JSON (no markdown):
{
  "overall_status": "passed|failed|broken",
  "reasoning": "Твои рассуждения: объясни почему ты пришёл к такому выводу, что именно указывает на баги или их отсутствие, как ты интерпретировал расхождения между ожидаемым и фактическим результатом",
  "observations": ["..."],
  "bugs": [
    {
      "title": "Short bug title",
      "severity": "critical|high|medium|low",
      "type": "Functional|UI|UX|Performance",
      "description": "Detailed description",
      "steps_to_reproduce": ["Step 1: ...", "Step 2: ..."],
      "expected_result": "...",
      "actual_result": "...",
      "step_number": 3
    }
  ],
  "clarification": {
    "needs_clarification": true,
    "items": [
      {
        "step_number": 2,
        "question": "The step says 'fill the form' but doesn't specify which fields are mandatory. Should validation be checked?",
        "suggestion": "Rewrite as: 'Fill Name with X, Email with Y, Password with Z and click Submit'"
      }
    ],
    "general_suggestions": [
      "Consider adding a step to verify the URL after redirect",
      "Add a negative case: what happens with empty password?"
    ]
  }
}

Status rules:
- "passed": ALL steps passed AND no bugs found
- "failed": one or more steps failed (wrong actual result vs expected)
- "broken": one or more steps had execution errors / timeouts

Bug rules — only report bugs for REAL website defects:
- Wrong error message text
- Missing UI element that should be there
- Redirect goes to wrong page
- Form submits with invalid data
- Functionality described in expected result does not work
DO NOT report bugs for: agent tool errors, LLM issues, slow network, ambiguous steps.

Clarification rules — flag a step when:
- The action is ambiguous (multiple elements could match)
- The expected result is too vague to verify ("should work correctly")
- Important data (credentials, values) is missing from the step
- The step skips over a required precondition (e.g. login needed but not described)
- A step could be split into more precise atomic actions
If the test case is well-written and all steps are clear, set needs_clarification to false.
"""


def observer_node(state: AgentState) -> dict:
    tc: TestCase = state["test_case"]
    step_results: list[StepResult] = state["step_results"]

    results_text = "\n".join(
        f"Step {r.step_number} [{r.status.upper()}]: {r.description}\n"
        f"  Expected : {r.expected_result}\n"
        f"  Actual   : {r.actual_result}\n"
        f"  Error    : {r.error_message or 'none'}\n"
        f"  Tools    : {', '.join(r.tool_calls[:5]) or 'none'}"
        for r in step_results
    )

    original_steps = "\n".join(
        f"Step {s.step_number}: {s.step}\n  Expected: {s.expected}"
        for s in tc.steps
    )

    human = f"""Analyze this test execution:

Test Case: {tc.name} (ID: {tc.id})
URL: {tc.start_url}
Description: {tc.description}

Original test steps (natural language):
{original_steps}

Execution results:
{results_text}

Return your analysis as JSON.
"""

    llm = get_planning_llm()
    json_llm = _JsonLLM(llm)
    analysis = _parse_json(json_llm.invoke([SystemMessage(_SYSTEM), HumanMessage(human)]))

    bugs: list[BugReport] = []
    for bd in analysis.get("bugs", []):
        step_num = bd.get("step_number", 0)
        screenshots = [
            r.screenshot_path
            for r in step_results
            if r.screenshot_path and r.step_number == step_num
        ]
        bugs.append(
            BugReport(
                title=bd.get("title", "Untitled bug"),
                severity=bd.get("severity", "medium"),
                type=bd.get("type", "Functional"),
                description=bd.get("description", ""),
                steps_to_reproduce=bd.get("steps_to_reproduce", []),
                expected_result=bd.get("expected_result", ""),
                actual_result=bd.get("actual_result", ""),
                screenshots=[s for s in screenshots if s],
                test_case_id=tc.id,
                test_case_name=tc.name,
                step_number=step_num,
            )
        )

    raw_clarification = analysis.get("clarification", {})
    clarification = ClarificationRequest(
        needs_clarification=raw_clarification.get("needs_clarification", False),
        items=[
            ClarificationItem(**item)
            for item in raw_clarification.get("items", [])
        ],
        general_suggestions=raw_clarification.get("general_suggestions", []),
    )

    status = analysis.get("overall_status", "broken")
    reasoning = analysis.get("reasoning", "Рассуждение аналитика недоступно")
    needs = clarification.needs_clarification
    print(f"  [Observer] {reasoning[:120]}...")
    print(
        f"  Observer: {status.upper()} | {len(bugs)} bug(s) | "
        f"clarification={'needed' if needs else 'not needed'}"
    )

    return {
        "bugs": bugs,
        "overall_status": status,
        "clarification": clarification,
        "analysis_reasoning": reasoning,
    }


class _JsonLLM:
    def __init__(self, llm):
        from langchain_ollama import ChatOllama
        self._llm = ChatOllama(
            model=getattr(llm, "model", "qwen3.5:35b"),
            temperature=0,
            num_ctx=getattr(llm, "num_ctx", 8192),
            format="json",
        )

    def invoke(self, messages):
        return self._llm.invoke(messages).content


def _parse_json(text: str) -> dict:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return {
        "overall_status": "broken",
        "observations": ["JSON parse error in observer"],
        "bugs": [],
        "clarification": {"needs_clarification": False, "items": [], "general_suggestions": []},
    }
