"""Run lesson 13 with Ollama, LangGraph, Playwright, and visible Chromium."""

import os
import sys
from pathlib import Path
from pprint import pprint
from uuid import uuid4
from langgraph.checkpoint.memory import InMemorySaver
from dotenv import load_dotenv
from langchain_ollama import ChatOllama
from playwright.sync_api import sync_playwright

from browser_agent.graph import build_agent_graph
from browser_agent.persistence import build_thread_config

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from browser_agent.browser import PlaywrightBrowser
from browser_agent.models import TestCase
from browser_agent.runner import run_agent




def print_state(state: dict) -> None:
    print("\n" + "=" * 80)
    print(
        f"status={state.get('status')} "
        f"step_count={state.get('step_count')} "
        f"failure_count={state.get('failure_count')} "
        f"url={state.get('current_url')}"
    )
    if action := state.get("proposed_action"):
        print("proposed_action:")
        pprint(action.model_dump(), sort_dicts=False)
    if result := state.get("last_result"):
        print("last_result:")
        pprint(result.model_dump(), sort_dicts=False)
    if verdict := state.get("verdict"):
        print("verdict:")
        pprint(verdict.model_dump(), sort_dicts=False)
    if termination := state.get("termination"):
        print("termination:")
        pprint(termination.model_dump(), sort_dicts=False)
    if classification := state.get("classification"):
        print("classification:")
        pprint(classification.model_dump(), sort_dicts=False)
    if bug_report := state.get("bug_report"):
        print("bug_report:")
        pprint(bug_report.model_dump(), sort_dicts=False)


def main() -> None:
    fixture_url = (
            PROJECT_ROOT / "examples" / "playwright_fixture.html"
    ).resolve().as_uri()
    model_name = os.getenv("OLLAMA_MODEL", "qwen3.6:35b")

    print(f"model name: {model_name}")
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
        metadata={
            "ls_model_name": model_name,
            "ls_provider": "ollama",
        },
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
        checkpointer = InMemorySaver()
        thread_id = f"{test_case.id}:{uuid4()}"

        result = run_agent(
            model=model,
            browser=browser,
            test_case=test_case,
            on_state=print_state,
            report_dir=PROJECT_ROOT / "artifacts" / test_case.id / "report",
            checkpointer=checkpointer,
            thread_id=thread_id,
        )

        config = build_thread_config(test_case, thread_id)

        checkpoint_graph = build_agent_graph(
            model,
            browser,
            checkpointer=checkpointer,
        )

        snapshot = checkpoint_graph.get_state(config)

        print("\nCHECKPOINT")
        print(f"checkpoint thread: {thread_id}")
        print(f"checkpoint status: {snapshot.values['status']}")
        print(f"checkpoint next: {snapshot.next}")

        print("\nFINAL RESULT")
        print(f"status: {result['status']}")
        print(f"steps: {result['step_count']}")
        print(f"failures: {result['failure_count']}")
        print(f"termination: {result['termination'].kind}")
        if classification := result.get("classification"):
            print(f"classification: {classification.category}")
            print(f"confidence: {classification.confidence}")
            print(f"create bug: {classification.should_create_bug}")
        if bug_report := result.get("bug_report"):
            print(f"bug title: {bug_report.title}")
            print(f"bug severity: {bug_report.severity}")
        print(f"route records: {len(result['route'])}")
        input("\nPress Enter to close Chromium...")
        chromium.close()


if __name__ == "__main__":
    main()
