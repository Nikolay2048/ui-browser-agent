from langchain_core.runnables import RunnableLambda

from browser_agent.domain import (
    BrowserAction,
    BrowserTarget,
    ExpectedResultCheck,
    FailureCategory,
    FailureClassification,
    JudgeVerdict,
)


class EndToEndModel:
    def __init__(self, scenario_id: str) -> None:
        self.scenario_id = scenario_id

    def with_structured_output(self, schema):
        def respond(prompt_value):
            messages = prompt_value.to_messages()

            current_context = str(messages[-1].content)

            if schema is JudgeVerdict:
                return JudgeVerdict(
                    passed=True,
                    checks=[
                        ExpectedResultCheck(
                            expected="Scenario completed",
                            passed=True,
                            evidence="Final snapshot proves completion.",
                        )
                    ],
                    summary="Expected result is proven.",
                )

            if schema is FailureClassification:
                return FailureClassification(
                    category=FailureCategory.AUTOMATION_ERROR,
                    confidence=1.0,
                    rationale="Browser action repeatedly failed.",
                    evidence=["Failure limit was reached."],
                    should_create_bug=False,
                )

            return self._plan(current_context)

        return RunnableLambda(respond)

    def _plan(self, prompt: str) -> BrowserAction:
        if self.scenario_id == "create-task-happy-path":
            if 'textbox "Task"' in prompt:
                return BrowserAction(
                    action="fill",
                    target=BrowserTarget(
                        strategy="label",
                        value="Task",
                    ),
                    value="Learn AI Agents",
                    reason="Enter the task.",
                )

            if 'button "Add"' in prompt:
                return BrowserAction(
                    action="click",
                    target=BrowserTarget(
                        strategy="role",
                        value="button",
                        name="Add",
                    ),
                    value=None,
                    reason="Add the task.",
                )

        if self.scenario_id == "recover-after-first-action":
            button_name = (
                "Alternative"
                if "Primary button is blocked" in prompt
                else "Primary"
            )

            if 'status "Done"' not in prompt:
                return BrowserAction(
                    action="click",
                    target=BrowserTarget(
                        strategy="role",
                        value="button",
                        name=button_name,
                    ),
                    value=None,
                    reason="Try the available route.",
                )

        if self.scenario_id == "failure-budget-exhausted":
            return BrowserAction(
                action="click",
                target=BrowserTarget(
                    strategy="role",
                    value="button",
                    name="Submit",
                ),
                value=None,
                reason="Try to submit the form.",
            )

        return BrowserAction(
            action="finish",
            target=None,
            value=None,
            reason="The expected result is visible.",
        )

class HappyPathBrowser:
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

    def fill(self, _target, value: str) -> None:
        self.value = value

    def click(self, _target) -> None:
        self.added = True

    def screenshot(self) -> str:
        return "artifacts/e2e-happy.png"

class RecoveryBrowser:
    def __init__(self) -> None:
        self.current_url = "about:blank"
        self.done = False

    def open(self, url: str) -> None:
        self.current_url = url

    def snapshot(self) -> str:
        if self.done:
            return '- status "Done"'
        return '- button "Primary"\n- button "Alternative"'

    def click(self, target) -> None:
        if target.name == "Primary":
            raise RuntimeError("Primary button is blocked")
        self.done = True

    def screenshot(self) -> str:
        return "artifacts/e2e-recovery.png"

class FailingBrowser:
    def __init__(self) -> None:
        self.current_url = "about:blank"

    def open(self, url: str) -> None:
        self.current_url = url

    def snapshot(self) -> str:
        return '- button "Submit"'

    def click(self, _target) -> None:
        raise RuntimeError("Submit button is blocked")

    def screenshot(self) -> str:
        return "artifacts/e2e-failure.png"

def build_scenario(case_id: str):
    browsers = {
        "create-task-happy-path": HappyPathBrowser,
        "recover-after-first-action": RecoveryBrowser,
        "failure-budget-exhausted": FailingBrowser,
    }

    browser_class = browsers.get(case_id)

    if browser_class is None:
        raise ValueError(f"Unknown E2E scenario: {case_id}")

    return EndToEndModel(case_id), browser_class()