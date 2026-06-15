"""Run lesson 13 with Ollama, LangGraph, Playwright, and visible Chromium."""

import os
from pathlib import Path
from pprint import pprint
import sys

from langchain_ollama import ChatOllama
from playwright.sync_api import sync_playwright

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from browser_agent.browser import PlaywrightBrowser
from browser_agent.models import TestCase
from browser_agent.runner import run_agent


def print_state(state: dict) -> None:
    print("\n" + "=" * 80)
    print(
        f"status={state.get('status')} "
        f"step_count={state.get('step_count')} "
        f"url={state.get('current_url')}"
    )
    if action := state.get("proposed_action"):
        print("proposed_action:")
        pprint(action.model_dump(), sort_dicts=False)
    if result := state.get("last_result"):
        print("last_result:")
        pprint(result.model_dump(), sort_dicts=False)


def main() -> None:
    fixture_url = (
        PROJECT_ROOT / "examples" / "playwright_fixture.html"
    ).resolve().as_uri()
    model_name = os.getenv("OLLAMA_MODEL", "qwen3.6:35b")

    test_case = TestCase(
        id="first-real-agent",
        name="Create a task using the autonomous agent",
        start_url=fixture_url,
        goal="Add the task 'Learn AI Agents' to the task list",
        test_data={"task": "Learn AI Agents"},
        expected=["Learn AI Agents is visible in the task list"],
        max_steps=5,
    )
    model = ChatOllama(
        model=model_name,
        temperature=0,
        validate_model_on_init=True,
    )

    with sync_playwright() as playwright:
        chromium = playwright.chromium.launch(
            headless=False,
            slow_mo=500,
        )
        page = chromium.new_page()
        browser = PlaywrightBrowser(
            page,
            artifacts_dir=PROJECT_ROOT / "artifacts" / test_case.id,
        )

        result = run_agent(
            model=model,
            browser=browser,
            test_case=test_case,
            on_state=print_state,
        )

        print("\nFINAL RESULT")
        print(f"status: {result['status']}")
        print(f"steps: {result['step_count']}")
        print(f"route records: {len(result['route'])}")
        input("\nPress Enter to close Chromium...")
        chromium.close()


if __name__ == "__main__":
    main()
