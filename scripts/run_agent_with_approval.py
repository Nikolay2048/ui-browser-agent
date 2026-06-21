import os
import sys
from pathlib import Path
from pprint import pprint
from uuid import uuid4

from dotenv import load_dotenv
from langchain_ollama import ChatOllama
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command
from playwright.sync_api import sync_playwright

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from browser_agent.browser import PlaywrightBrowser
from browser_agent.graph import build_agent_graph
from browser_agent.models import TestCase
from browser_agent.persistence import build_thread_config


def main() -> None:
    fixture_url = (
            PROJECT_ROOT / "examples" / "playwright_fixture.html"
    ).resolve().as_uri()

    test_case = TestCase(
        id="approval-agent",
        name="Create task with human approval",
        start_url=fixture_url,
        goal="Add the task 'Learn AI Agents' to the task list",
        test_data={"task": "Learn AI Agents"},
        expected=["Learn AI Agents is visible in the task list"],
        max_steps=5,
    )

    model_name = os.getenv("OLLAMA_MODEL", "qwen3.6:35b")

    model = ChatOllama(
        model=model_name,
        temperature=0,
        validate_model_on_init=True,
        metadata={
            "ls_model_name": model_name,
            "ls_provider": "ollama",
        },
    )

    checkpointer = InMemorySaver()
    thread_id = f"{test_case.id}:{uuid4()}"

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
        browser.open(test_case.start_url)

        graph = build_agent_graph(
            model,
            browser,
            checkpointer=checkpointer,
            approval_policy_enabled=True,
        )

        config = build_thread_config(test_case, thread_id)
        current_input = {"test_case": test_case}

        while True:
            result = graph.invoke(
                current_input,
                config=config,
            )

            interrupts = result.get("__interrupt__", ())

            if not interrupts:
                final_state = result
                break

            payload = interrupts[0].value

            print("\nPROPOSED ACTION")
            pprint(payload, sort_dicts=False)

            while True:
                answer = input(
                    "\nApprove action? [y/n]: "
                ).strip().lower()

                if answer in {"y", "n"}:
                    break

                print("Enter only 'y' or 'n'.")

            while True:
                reason = input("Reason: ").strip()

                if reason:
                    break

                print("Reason must not be blank.")

            current_input = Command(
                resume={
                    "approved": answer == "y",
                    "reason": reason,
                }
            )

        print("\nFINAL RESULT")
        print(f"status: {final_state['status']}")
        print(f"steps: {final_state['step_count']}")
        print(f"failures: {final_state['failure_count']}")
        print(f"termination: {final_state['termination'].kind}")
        print(f"thread_id: {thread_id}")

        input("\nPress Enter to close Chromium...")
        chromium.close()


if __name__ == "__main__":
    main()
