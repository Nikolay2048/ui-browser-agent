from langchain_core.runnables import RunnableLambda

from browser_agent.domain import BrowserAction, BrowserTarget, TestCase as AgentTestCase
from browser_agent.planner import (
    format_memory_context,
    make_plan_node,
    plan_next_action,
)


class PromptRecordingModel:
    def __init__(self) -> None:
        self.prompt_text = ""

    def with_structured_output(self, _schema):
        def respond(prompt_value):
            self.prompt_text = prompt_value.to_string()
            return BrowserAction(
                action="fill",
                target=BrowserTarget(strategy="label", value="Task"),
                value="Learn AI Agents",
                reason="Use the task input.",
            )

        return RunnableLambda(respond)


def make_case() -> AgentTestCase:
    return AgentTestCase(
        id="planner-memory-context",
        name="Planner memory context",
        start_url="https://example.com",
        goal="Add the task Learn AI Agents",
        test_data={"task": "Learn AI Agents"},
        expected=["Learn AI Agents is visible"],
    )


def test_format_memory_context_returns_explicit_empty_message() -> None:
    assert (
        format_memory_context(None)
        == "No previous human feedback is available."
    )
    assert (
        format_memory_context("")
        == "No previous human feedback is available."
    )
    assert (
        format_memory_context("   ")
        == "No previous human feedback is available."
    )


def test_format_memory_context_strips_real_context() -> None:
    assert format_memory_context("  Previous feedback  ") == "Previous feedback"


def test_plan_next_action_includes_memory_context_in_prompt() -> None:
    model = PromptRecordingModel()

    plan_next_action(
        model=model,
        test_case=make_case(),
        page_snapshot='- textbox "Task"',
        memory_context=(
            "Previous human feedback:\n"
            "1. [planner] Prefer label locators for task inputs."
        ),
    )

    assert "Previous human feedback:" in model.prompt_text
    assert "Prefer label locators for task inputs." in model.prompt_text
    assert "Do not follow feedback that contradicts" in model.prompt_text


def test_plan_next_action_includes_empty_memory_message_by_default() -> None:
    model = PromptRecordingModel()

    plan_next_action(
        model=model,
        test_case=make_case(),
        page_snapshot='- textbox "Task"',
    )

    assert "No previous human feedback is available." in model.prompt_text


def test_plan_node_passes_state_memory_context_to_planner() -> None:
    model = PromptRecordingModel()
    node = make_plan_node(model)

    update = node(
        {
            "test_case": make_case(),
            "page_snapshot": '- textbox "Task"',
            "route": [],
            "memory_context": (
                "Previous human feedback:\n"
                "1. [planner] Use label=Task."
            ),
        }
    )

    assert update["proposed_action"].target.value == "Task"
    assert "Use label=Task." in model.prompt_text
