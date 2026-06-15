from __future__ import annotations

import re
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage

from testing_agent.config import get_generation_llm
from testing_agent.models import StepResult, TestCase
from testing_agent.state import AgentState

_SYSTEM = """You are a Python test automation expert. Write a pytest test using Playwright.

Rules:
- Use playwright's page fixtures from conftest.py
- Use semantic locators: get_by_role, get_by_label, get_by_placeholder, get_by_text
- Use expect() assertions from playwright.sync_api
- Add allure decorators: @allure.title, @allure.severity, @allure.step, @allure.description
- Follow the AAA pattern (Arrange, Act, Assert)
- Each test step = one with allure.step() block
- Add proper error handling with clear failure messages
- Make the test self-contained (handles login if needed)

Output ONLY the Python code. No markdown fences, no explanation.

Import template:
import pytest
import allure
from playwright.sync_api import Page, expect
"""

_SEVERITY_MAP = {
    "critical": "allure.severity_level.CRITICAL",
    "high": "allure.severity_level.NORMAL",
    "medium": "allure.severity_level.MINOR",
    "low": "allure.severity_level.TRIVIAL",
}


def test_generator_node(state: AgentState) -> dict:
    tc: TestCase = state["test_case"]
    step_results: list[StepResult] = state["step_results"]

    passed_steps = [r for r in step_results if r.status == "passed"]

    if not passed_steps:
        code = _minimal_test(tc)
    else:
        steps_detail = "\n".join(
            f"Step {r.step_number}: {r.description}\n"
            f"  Tools used: {', '.join(r.tool_calls)}\n"
            f"  Actual result: {r.actual_result}"
            for r in passed_steps
        )

        human = f"""Generate a pytest + allure test for:

Test Case: {tc.name}
ID: {tc.id}
URL: {tc.start_url}
Description: {tc.description}
Severity: {tc.severity}
Tags: {tc.tags}

Executed steps (passed):
{steps_detail}

Function name: test_{tc.id.replace('-', '_').replace(' ', '_')}
"""
        llm = get_generation_llm()
        messages = [SystemMessage(_SYSTEM), HumanMessage(human)]
        response = llm.invoke(messages)
        code = _extract_code(response.content)

    _save_test(tc.id, code)
    return {"generated_test_code": code}


def _extract_code(text: str) -> str:
    match = re.search(r"```python\n(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    match = re.search(r"```\n(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text.strip()


def _minimal_test(tc: TestCase) -> str:
    fn_name = f"test_{tc.id.replace('-', '_')}"
    severity = _SEVERITY_MAP.get(tc.severity, "allure.severity_level.NORMAL")
    return f'''import pytest
import allure
from playwright.sync_api import Page, expect


@allure.title("{tc.name}")
@allure.severity({severity})
@allure.description("""{tc.description}""")
def {fn_name}(page: Page) -> None:
    """Auto-generated from test case {tc.id}. All steps failed — requires manual review."""
    with allure.step("Navigate to start URL"):
        page.goto("{tc.start_url}")
        page.wait_for_load_state("domcontentloaded")

    # TODO: All steps failed during agent execution.
    # Review the Allure report for agent execution details and screenshots.
    pytest.skip("All steps failed during agent execution — review Allure report")
'''


def _save_test(test_id: str, code: str) -> None:
    out_dir = Path("generated_tests")
    out_dir.mkdir(exist_ok=True)
    path = out_dir / f"test_{test_id}.py"
    path.write_text(code, encoding="utf-8")
    print(f"  Generated test: {path}")
