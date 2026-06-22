from langchain_core.runnables import RunnableLambda

from browser_agent.classifier import (
    build_classifier_chain,
    classify_failure,
    make_classifier_node,
)
from browser_agent.domain import (
    ActionResult,
    BrowserAction,
    BrowserTarget,
    ExecutionStep,
    FailureClassification,
    RunTermination,
    TestCase as AgentTestCase,
)


class FakeClassifierModel:
    def __init__(self) -> None:
        self.received_schema = None
        self.received_prompt = None

    def with_structured_output(self, schema):
        self.received_schema = schema

        def respond(prompt_value):
            self.received_prompt = prompt_value
            return FailureClassification(
                category="automation_error",
                confidence=0.8,
                rationale="The click failed at the automation layer.",
                evidence=["Action error: Element is not clickable."],
                should_create_bug=False,
            )

        return RunnableLambda(respond)


def make_case() -> AgentTestCase:
    return AgentTestCase(
        id="classifier",
        name="Classify failed run",
        start_url="https://example.com",
        goal="Submit the form",
        expected=["Success message is visible"],
    )


def make_route() -> list[ExecutionStep]:
    return [
        ExecutionStep(
            step_number=1,
            page_snapshot='- button "Submit"',
            action=BrowserAction(
                action="click",
                target=BrowserTarget(
                    strategy="role",
                    value="button",
                    name="Submit",
                ),
                value=None,
                reason="Submit the form.",
            ),
            result=ActionResult(
                success=False,
                url_before="https://example.com",
                url_after="https://example.com",
                error="Element is not clickable",
                screenshot_path="artifacts/failure.png",
            ),
        )
    ]


def make_termination() -> RunTermination:
    return RunTermination(
        kind="failure_limit",
        message="Failure limit 1 was reached.",
    )


def test_classifier_chain_uses_classification_schema() -> None:
    model = FakeClassifierModel()

    build_classifier_chain(model)

    assert model.received_schema is FailureClassification


def test_classify_failure_passes_complete_evidence() -> None:
    model = FakeClassifierModel()

    result = classify_failure(
        model=model,
        test_case=make_case(),
        termination=make_termination(),
        page_snapshot='- button "Submit"',
        route=make_route(),
    )

    rendered = "\n".join(
        str(message.content)
        for message in model.received_prompt.to_messages()
    )
    assert result.category == "automation_error"
    assert "Success message is visible" in rendered
    assert "failure_limit" in rendered
    assert "Element is not clickable" in rendered
    assert '- button "Submit"' in rendered


def test_classifier_node_returns_partial_update() -> None:
    node = make_classifier_node(FakeClassifierModel())

    update = node(
        {
            "test_case": make_case(),
            "termination": make_termination(),
            "page_snapshot": '- button "Submit"',
            "route": make_route(),
            "status": "failed",
        }
    )

    assert list(update) == ["classification"]
    assert update["classification"].category == "automation_error"
