"""LLM planner from lesson 5.

The related lesson is archived in learning/lesson_05_planner/README.md.
"""
from langchain_core.prompts import ChatPromptTemplate

from browser_agent.models import BrowserAction, ExecutionStep
from browser_agent.state import AgentState

SYSTEM_PROMPT = """
You are a browser testing planner.

Your task is to choose exactly one next action.
Use the current page snapshot and the test case goal.
Do not invent elements, text, or selectors that are not present in the snapshot.
Use test data from the test case when input values are required.
Return only the next action, not a full plan.
The action must be valid according to the BrowserAction schema.

Target must be an object.

Use one of these target object formats:

Role target:
{
  "strategy": "role",
  "value": "button",
  "name": "Login"
}

Label target:
{
  "strategy": "label",
  "value": "Username"
}

Text target:
{
  "strategy": "text",
  "value": "Products"
}

CSS target:
{
  "strategy": "css",
  "value": ".some-selector"
}

The accessibility snapshot syntax is descriptive and is not a valid target.
Never copy snapshot entries directly into target.

Convert snapshot elements to target objects:
- textbox "Task" -> {"strategy": "label", "value": "Task"}
- button "Add" -> {"strategy": "role", "value": "button", "name": "Add"}
- visible text "Products" -> {"strategy": "text", "value": "Products"}

Invalid targets include:
- "label=Task"
- "role=button[name=\\"Add\\"]"
- "text=Products"
- "css=.some-selector"
- "textbox=\\"Task\\""
- "textbox \\"Task\\""
- "button \\"Add\\""
- "get_by_label(\\"Task\\")"
- "page.locator(...)"

For click and assert_text, target is required.
For fill and press, both target and value are required.
For finish, target and value must be null.
Always provide a short reason for the chosen action.
Use the execution history to avoid repeating actions that already succeeded.
""".strip()


def format_execution_history(route: list[ExecutionStep]) -> str:
    """Format completed steps as compact planner memory.    """
    if not route:
        return "No actions have been executed yet."
    history = []
    for step in route:
        lines = [
            f"Step {step.step_number}",
            f"action={step.action.action}",
            f"target={step.action.target}",
            f"value={step.action.value}",
            f"success={step.result.success}",
            f"url={step.result.url_before} -> {step.result.url_after}",
        ]

        if step.result.error is not None:
            lines.append(f"error={step.result.error}")

        history.append("\n".join(lines))

    return "\n\n".join(history)


def build_planner_prompt() -> ChatPromptTemplate:
    """ return a ChatPromptTemplate."""
    return ChatPromptTemplate.from_messages([
        (
            "system",
            SYSTEM_PROMPT
        ),
        (
            "human",
            """
            Goal:
            {goal}
            
            Test data:
            {test_data}
            
            Expected results:
            {expected}

            Execution history:
            {execution_history}
            
            Current page:
            {page_snapshot}
            """
        )
    ])


def build_planner_chain(model):
    """ compose the prompt with structured BrowserAction output."""
    prompt = build_planner_prompt()
    structured_model = model.with_structured_output(BrowserAction)

    return prompt | structured_model


def plan_next_action(model, test_case, page_snapshot, route=None):
    """ invoke the planner chain and return BrowserAction."""
    chain = build_planner_chain(model)
    execution_history = format_execution_history(route or [])

    return chain.invoke({
        "goal": test_case.goal,
        "test_data": test_case.test_data,
        "expected": test_case.expected,
        "execution_history": execution_history,
        "page_snapshot": page_snapshot,
    })


def make_plan_node(model):
    """Create a LangGraph node that stores the next proposed action."""

    def plan(state: AgentState) -> dict:
        action = plan_next_action(
            model=model,
            test_case=state["test_case"],
            page_snapshot=state["page_snapshot"],
            route=state["route"]
        )
        return {"proposed_action": action}

    return plan
