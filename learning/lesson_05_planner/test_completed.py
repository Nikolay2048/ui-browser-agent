from langchain_core.runnables import RunnableLambda

from browser_agent.domain import BrowserAction, TestCase
from browser_agent.planner import build_planner_chain, plan_next_action


class FakeStructuredModel:
    def __init__(self) -> None:
        self.received_schema = None
        self.received_prompt = None

    def with_structured_output(self, schema):
        self.received_schema = schema

        def respond(prompt_value):
            self.received_prompt = prompt_value
            return BrowserAction(
                action="fill",
                target="label=Username",
                value="standard_user",
                reason="The login form requires a username.",
            )

        return RunnableLambda(respond)


def make_case() -> TestCase:
    return TestCase(
        id="login",
        name="Login",
        start_url="https://example.com/login",
        goal="Log in as the test user",
        test_data={"username": "standard_user"},
        expected=["Products page is visible"],
    )


def test_build_planner_chain_uses_browser_action_schema() -> None:
    model = FakeStructuredModel()
    build_planner_chain(model)
    assert model.received_schema is BrowserAction


def test_plan_next_action_returns_typed_action() -> None:
    result = plan_next_action(
        model=FakeStructuredModel(),
        test_case=make_case(),
        page_snapshot='- textbox "Username"\n- button "Login"',
    )
    assert isinstance(result, BrowserAction)
