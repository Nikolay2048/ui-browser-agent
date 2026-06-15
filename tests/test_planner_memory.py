from langchain_core.runnables import RunnableLambda

from browser_agent.models import (
    ActionResult,
    BrowserAction,
    ExecutionStep,
    TestCase as AgentTestCase,
)
from browser_agent.planner import (
    format_execution_history,
    make_plan_node,
)


def make_step(
    number: int,
    action: str,
    target: str,
    value: str | None,
    *,
    success: bool = True,
    error: str | None = None,
) -> ExecutionStep:
    return ExecutionStep(
        step_number=number,
        page_snapshot="snapshot intentionally omitted from formatted history",
        action=BrowserAction(
            action=action,
            target=target,
            value=value,
            reason="Reason intentionally omitted from assertions.",
        ),
        result=ActionResult(
            success=success,
            url_before="https://example.com/start",
            url_after="https://example.com/tasks",
            error=error,
            screenshot_path=f"artifacts/step-{number:03d}.png",
        ),
    )


def make_case() -> AgentTestCase:
    return AgentTestCase(
        id="planner-memory",
        name="Planner sees execution history",
        start_url="https://example.com/start",
        goal="Add task Learn agents",
        test_data={"task": "Learn agents"},
        expected=["Learn agents is visible"],
    )


class PromptCapturingModel:
    def __init__(self) -> None:
        self.rendered_prompt = ""

    def with_structured_output(self, _schema):
        def respond(prompt_value):
            self.rendered_prompt = "\n".join(
                str(message.content) for message in prompt_value.to_messages()
            )
            return BrowserAction(
                action="finish",
                target=None,
                value=None,
                reason="Only capture the prompt.",
            )

        return RunnableLambda(respond)


def test_empty_route_has_explicit_memory_message() -> None:
    assert format_execution_history([]) == "No actions have been executed yet."


def test_history_contains_facts_but_omits_heavy_fields() -> None:
    route = [
        make_step(1, "fill", "label=Task", "Learn agents"),
        make_step(
            2,
            "click",
            'role=button[name="Add"]',
            None,
            success=False,
            error="Button is blocked",
        ),
    ]

    history = format_execution_history(route)

    assert "Step 1" in history
    assert "action=fill" in history
    assert "target=label=Task" in history
    assert "value=Learn agents" in history
    assert "success=True" in history
    assert "Step 2" in history
    assert "success=False" in history
    assert "error=Button is blocked" in history
    assert "https://example.com/start -> https://example.com/tasks" in history
    assert "snapshot intentionally omitted" not in history
    assert "artifacts/step-" not in history


def test_plan_node_passes_state_route_to_prompt() -> None:
    model = PromptCapturingModel()
    route = [make_step(1, "fill", "label=Task", "Learn agents")]
    node = make_plan_node(model)

    node(
        {
            "test_case": make_case(),
            "page_snapshot": '- textbox "Task": Learn agents\n- button "Add"',
            "route": route,
            "step_count": 1,
            "status": "running",
        }
    )

    assert "Step 1" in model.rendered_prompt
    assert "action=fill" in model.rendered_prompt
    assert "target=label=Task" in model.rendered_prompt
