"""Manual integration check with local Ollama."""

from langchain_ollama import ChatOllama

from browser_agent.models import TestCase
from browser_agent.planner import plan_next_action

model = ChatOllama(
    model="qwen3.5:35b",
    temperature=0,
    validate_model_on_init=True,
)
test_case = TestCase(
    id="manual-login",
    name="Manual planner check",
    start_url="https://www.saucedemo.com/",
    goal="Log in using the supplied test credentials",
    test_data={"username": "standard_user", "password": "secret_sauce"},
    expected=["Products page is visible"],
)
snapshot = """
URL: https://www.saucedemo.com/
TITLE: Swag Labs
- textbox "Username"
- textbox "Password"
- button "Login"
"""
print(
    plan_next_action(
        model=model,
        test_case=test_case,
        page_snapshot=snapshot,
    ).model_dump_json(indent=2)
)
