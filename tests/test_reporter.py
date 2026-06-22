from langchain_core.runnables import RunnableLambda

from browser_agent.domain import (
    ActionResult,
    BrowserAction,
    BrowserTarget,
    BugReport,
    ExecutionStep,
    FailureClassification,
    RunTermination,
    TestCase as AgentTestCase,
)
from browser_agent.reporter import (
    build_reporter_chain,
    create_bug_report,
    make_reporter_node,
)


class FakeReporterModel:
    def __init__(self) -> None:
        self.received_schema = None
        self.received_prompt = None

    def with_structured_output(self, schema):
        self.received_schema = schema

        def respond(prompt_value):
            self.received_prompt = prompt_value
            return BugReport(
                test_case_id="create-task",
                title="Task is not added after clicking Add",
                severity="major",
                preconditions=["Tasks page is open"],
                steps_to_reproduce=[
                    "Fill Task with Learn AI Agents",
                    "Click the Add button",
                ],
                expected_result="Learn AI Agents is visible.",
                actual_result="Learn AI Agents is absent.",
                evidence=["Judge did not find the task in the final snapshot."],
            )

        return RunnableLambda(respond)


def make_case() -> AgentTestCase:
    return AgentTestCase(
        id="create-task",
        name="Create task",
        start_url="https://example.com/tasks",
        goal="Add Learn AI Agents",
        test_data={"task": "Learn AI Agents"},
        expected=["Learn AI Agents is visible"],
    )


def make_route() -> list[ExecutionStep]:
    return [
        ExecutionStep(
            step_number=1,
            page_snapshot='- textbox "Task"\n- button "Add"',
            action=BrowserAction(
                action="fill",
                target=BrowserTarget(strategy="label", value="Task"),
                value="Learn AI Agents",
                reason="Enter the task.",
            ),
            result=ActionResult(
                success=True,
                url_before="https://example.com/tasks",
                url_after="https://example.com/tasks",
            ),
        )
    ]


def make_classification() -> FailureClassification:
    return FailureClassification(
        category="product_bug",
        confidence=0.9,
        rationale="The expected task is absent after successful actions.",
        evidence=["Final snapshot does not contain the task."],
        should_create_bug=True,
    )


def make_termination() -> RunTermination:
    return RunTermination(
        kind="judge_failed",
        message="Expected task was not proven.",
    )


def test_reporter_chain_uses_bug_report_schema() -> None:
    model = FakeReporterModel()

    build_reporter_chain(model)

    assert model.received_schema is BugReport


def test_create_bug_report_passes_complete_evidence() -> None:
    model = FakeReporterModel()

    report = create_bug_report(
        model=model,
        test_case=make_case(),
        classification=make_classification(),
        termination=make_termination(),
        page_snapshot='- textbox "Task"\n- button "Add"',
        route=make_route(),
    )

    rendered = "\n".join(
        str(message.content)
        for message in model.received_prompt.to_messages()
    )
    assert report.severity == "major"
    assert "create-task" in rendered
    assert "Learn AI Agents is visible" in rendered
    assert "product_bug" in rendered
    assert "action=fill" in rendered


def test_reporter_node_returns_partial_update() -> None:
    node = make_reporter_node(FakeReporterModel())

    update = node(
        {
            "test_case": make_case(),
            "classification": make_classification(),
            "termination": make_termination(),
            "page_snapshot": '- textbox "Task"\n- button "Add"',
            "route": make_route(),
            "status": "failed",
        }
    )

    assert list(update) == ["bug_report"]
    assert update["bug_report"].test_case_id == "create-task"
