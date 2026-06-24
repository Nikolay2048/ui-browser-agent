from datetime import datetime, timezone

from langchain_core.runnables import RunnableLambda

from browser_agent.domain import (
    BrowserAction,
    BrowserTarget,
    ExpectedResultCheck,
    FailureCategory,
    FailureClassification,
    JudgeVerdict,
    TestCase as AgentTestCase,
)
from browser_agent.feedback import FeedbackScope, HumanFeedbackRecord
from browser_agent.runner import build_feedback_memory_context, run_agent


class PromptRecordingModel:
    def __init__(self) -> None:
        self.prompts: list[str] = []

    def with_structured_output(self, schema):
        def respond(prompt_value):
            prompt_text = prompt_value.to_string()
            current_page = prompt_text.rsplit("Current page:", 1)[-1]
            self.prompts.append(prompt_text)

            if schema is JudgeVerdict:
                return JudgeVerdict(
                    passed=True,
                    checks=[
                        ExpectedResultCheck(
                            expected="Task is visible",
                            passed=True,
                            evidence="The task is visible.",
                        )
                    ],
                    summary="The task is visible.",
                )

            if schema is FailureClassification:
                return FailureClassification(
                    category=FailureCategory.AGENT_ERROR,
                    confidence=0.9,
                    rationale="The fake model classified a failed run.",
                    evidence=["Fake classifier evidence."],
                    should_create_bug=False,
                )

            if 'textbox "Task"' in current_page:
                return BrowserAction(
                    action="fill",
                    target=BrowserTarget(strategy="label", value="Task"),
                    value="Learn AI Agents",
                    reason="Use the task input.",
                )

            if 'button "Add"' in current_page:
                return BrowserAction(
                    action="click",
                    target=BrowserTarget(
                        strategy="role",
                        value="button",
                        name="Add",
                    ),
                    value=None,
                    reason="Submit the task.",
                )

            return BrowserAction(
                action="finish",
                target=None,
                value=None,
                reason="The task is visible.",
            )

        return RunnableLambda(respond)


class StatefulBrowser:
    def __init__(self) -> None:
        self.current_url = "about:blank"
        self.value = ""
        self.added = False

    def open(self, url: str) -> None:
        self.current_url = url

    def snapshot(self) -> str:
        if self.added:
            return '- listitem "Learn AI Agents"'
        if self.value:
            return '- button "Add"'
        return '- textbox "Task"'

    def fill(self, _target: str, value: str) -> None:
        self.value = value

    def click(self, _target: str) -> None:
        self.added = True

    def screenshot(self) -> str:
        return "artifacts/test-runner-feedback-memory.png"


class InMemoryFeedbackStore:
    def __init__(self, records: list[HumanFeedbackRecord]) -> None:
        self.records = records

    def load_all(self) -> list[HumanFeedbackRecord]:
        return self.records


def make_case(test_case_id: str = "memory-runner") -> AgentTestCase:
    return AgentTestCase(
        id=test_case_id,
        name="Runner feedback memory",
        start_url="https://example.com/tasks",
        goal="Add task Learn AI Agents",
        test_data={"task": "Learn AI Agents"},
        expected=["Task is visible"],
        max_steps=4,
    )


def make_feedback(
    feedback_id: str,
    *,
    test_case_id: str = "memory-runner",
    scope: FeedbackScope = FeedbackScope.PLANNER,
    minute: int = 0,
) -> HumanFeedbackRecord:
    return HumanFeedbackRecord(
        feedback_id=feedback_id,
        run_id=f"run-{feedback_id}",
        test_case_id=test_case_id,
        created_at=datetime(
            2026,
            6,
            24,
            10,
            minute,
            tzinfo=timezone.utc,
        ),
        scope=scope,
        step_number=(1 if scope is FeedbackScope.STEP else None),
        summary=f"Summary {feedback_id}",
        correction=f"Correction {feedback_id}",
        tags=["planner"],
    )


def test_build_feedback_memory_context_filters_for_planner_memory() -> None:
    store = InMemoryFeedbackStore(
        [
            make_feedback("planner-old", minute=1),
            make_feedback("judge", scope=FeedbackScope.JUDGE, minute=2),
            make_feedback("other-case", test_case_id="other", minute=3),
            make_feedback("step-new", scope=FeedbackScope.STEP, minute=4),
        ]
    )

    context = build_feedback_memory_context(make_case(), store)

    assert "Correction step-new" in context
    assert "Correction planner-old" in context
    assert "Correction judge" not in context
    assert "Correction other-case" not in context
    assert context.index("Correction step-new") < context.index(
        "Correction planner-old"
    )


def test_run_agent_without_feedback_store_keeps_baseline_behavior() -> None:
    model = PromptRecordingModel()

    result = run_agent(model, StatefulBrowser(), make_case())

    assert result["status"] == "passed"
    assert any(
        "No previous human feedback is available." in prompt
        for prompt in model.prompts
    )


def test_run_agent_passes_retrieved_feedback_to_planner_prompt() -> None:
    model = PromptRecordingModel()
    store = InMemoryFeedbackStore(
        [
            make_feedback("planner", minute=1),
            make_feedback("other", test_case_id="other-case", minute=2),
            make_feedback("judge", scope=FeedbackScope.JUDGE, minute=3),
        ]
    )

    result = run_agent(
        model,
        StatefulBrowser(),
        make_case(),
        feedback_store=store,
    )

    assert result["status"] == "passed"
    assert any("Correction planner" in prompt for prompt in model.prompts)
    assert all("Correction other" not in prompt for prompt in model.prompts)
    assert all("Correction judge" not in prompt for prompt in model.prompts)
