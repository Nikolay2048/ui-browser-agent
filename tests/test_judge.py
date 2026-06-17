from langchain_core.runnables import RunnableLambda

from browser_agent.judge import (
    build_judge_chain,
    judge_run,
    make_judge_node,
)
from browser_agent.models import (
    ActionResult,
    BrowserAction,
    BrowserTarget,
    ExecutionStep,
    ExpectedResultCheck,
    JudgeVerdict,
    TestCase as AgentTestCase,
)


class FakeJudgeModel:
    def __init__(self) -> None:
        self.received_schema = None
        self.received_prompt = None

    def with_structured_output(self, schema):
        self.received_schema = schema

        def respond(prompt_value):
            self.received_prompt = prompt_value
            return JudgeVerdict(
                passed=True,
                checks=[
                    ExpectedResultCheck(
                        expected="Learn AI Agents is visible",
                        passed=True,
                        evidence='Snapshot contains listitem "Learn AI Agents".',
                    )
                ],
                summary="The expected task is visible.",
            )

        return RunnableLambda(respond)


def make_case() -> AgentTestCase:
    return AgentTestCase(
        id="judge",
        name="Judge expected result",
        start_url="https://example.com/tasks",
        goal="Add task Learn AI Agents",
        expected=["Learn AI Agents is visible"],
    )


def make_route() -> list[ExecutionStep]:
    action = BrowserAction(
        action="click",
        target=BrowserTarget(strategy="role", value="button", name="Add"),
        value=None,
        reason="Submit the task.",
    )
    result = ActionResult(
        success=True,
        url_before="https://example.com/tasks",
        url_after="https://example.com/tasks",
        screenshot_path="artifacts/step-002.png",
    )
    return [
        ExecutionStep(
            step_number=2,
            page_snapshot='- textbox "Task": Learn AI Agents\n- button "Add"',
            action=action,
            result=result,
        )
    ]


def test_build_judge_chain_uses_verdict_schema() -> None:
    model = FakeJudgeModel()

    build_judge_chain(model)

    assert model.received_schema is JudgeVerdict


def test_judge_run_passes_expected_snapshot_and_history() -> None:
    model = FakeJudgeModel()

    verdict = judge_run(
        model=model,
        test_case=make_case(),
        page_snapshot='- listitem "Learn AI Agents"',
        route=make_route(),
    )

    rendered = "\n".join(
        str(message.content)
        for message in model.received_prompt.to_messages()
    )
    assert verdict.passed is True
    assert "Learn AI Agents is visible" in rendered
    assert '- listitem "Learn AI Agents"' in rendered
    assert "action=click" in rendered


def test_judge_node_returns_partial_state_update() -> None:
    node = make_judge_node(FakeJudgeModel())

    update = node(
        {
            "test_case": make_case(),
            "page_snapshot": '- listitem "Learn AI Agents"',
            "route": make_route(),
            "status": "running",
        }
    )

    assert list(update) == ["verdict"]
    assert update["verdict"].passed is True
