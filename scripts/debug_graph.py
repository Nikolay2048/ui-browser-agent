"""Run the current agent graph step by step without Ollama or Playwright."""

from pprint import pprint
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from langchain_core.runnables import RunnableLambda

from browser_agent.graph import build_agent_graph
from browser_agent.models import BrowserAction, BrowserTarget, TestCase


class DebugModel:
    """Deterministic planner used to inspect graph behavior."""

    def with_structured_output(self, _schema):
        def respond(prompt_value):
            prompt_text = "\n".join(
                str(message.content) for message in prompt_value.to_messages()
            )

            if 'button "Continue"' in prompt_text:
                return BrowserAction(
                    action="click",
                    target=BrowserTarget(
                        strategy="role",
                        value="button",
                        name="Continue",
                    ),
                    value=None,
                    reason="The visible Continue button advances the scenario.",
                )

            return BrowserAction(
                action="finish",
                target=None,
                value=None,
                reason="The latest snapshot confirms the goal.",
            )

        return RunnableLambda(respond)


class DebugBrowser:
    """Small in-memory browser adapter with observable state changes."""

    def __init__(self) -> None:
        self.current_url = "https://example.com/start"
        self.goal_reached = False

    def snapshot(self) -> str:
        print("\n[BROWSER] snapshot()")
        if self.goal_reached:
            return 'heading "Goal reached"'
        return 'button "Continue"'

    def click(self, target: str) -> None:
        print(f"\n[BROWSER] click({target!r})")
        self.goal_reached = True
        self.current_url = "https://example.com/done"

    def screenshot(self) -> str:
        print("\n[BROWSER] screenshot()")
        return "artifacts/debug-step.png"


def main() -> None:
    browser = DebugBrowser()
    graph = build_agent_graph(DebugModel(), browser)
    test_case = TestCase(
        id="debug-current-graph",
        name="Debug the autonomous graph",
        start_url=browser.current_url,
        goal="Reach the page containing Goal reached",
        max_steps=3,
    )

    print("Streaming partial state updates from LangGraph:")

    for event in graph.stream(
        {"test_case": test_case},
        stream_mode="updates",
    ):
        print("\n" + "=" * 70)
        pprint(event, sort_dicts=False)


if __name__ == "__main__":
    main()
