from langchain_core.runnables import RunnableLambda

from browser_agent.domain import BrowserAction, BrowserTarget, TestCase as AgentTestCase
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
                target=BrowserTarget(strategy="label", value="Username"),
                value="standard_user",
                reason="The login form requires a username.",
            )

        return RunnableLambda(respond)


def make_case() -> AgentTestCase:
    return AgentTestCase(
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
    model = FakeStructuredModel()

    result = plan_next_action(
        model=model,
        test_case=make_case(),
        page_snapshot='- textbox "Username"\n- button "Login"',
    )

    assert isinstance(result, BrowserAction)
    assert result.action == "fill"
    assert result.target == BrowserTarget(strategy="label", value="Username")


def test_planner_prompt_contains_runtime_context() -> None:
    model = FakeStructuredModel()
    snapshot = '- textbox "Username"\n- button "Login"'

    plan_next_action(model=model, test_case=make_case(), page_snapshot=snapshot)

    messages = model.received_prompt.to_messages()
    rendered = "\n".join(str(message.content) for message in messages)

    assert "Log in as the test user" in rendered
    assert "standard_user" in rendered
    assert snapshot in rendered


def test_planner_prompt_defines_supported_target_language() -> None:
    model = FakeStructuredModel()

    plan_next_action(
        model=model,
        test_case=make_case(),
        page_snapshot='- textbox "Username"\n- button "Login"',
    )

    messages = model.received_prompt.to_messages()
    system_prompt = str(messages[0].content)

    assert "target must be an object" in system_prompt.lower()
    assert '"strategy": "role"' in system_prompt
    assert '"value": "button"' in system_prompt
    assert '"name": "Login"' in system_prompt
    assert '"strategy": "label"' in system_prompt
    assert '"strategy": "text"' in system_prompt
    assert '"strategy": "css"' in system_prompt
