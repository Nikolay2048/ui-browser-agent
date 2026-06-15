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

Only use one of these target formats:
- role=button[name="Login"]
- label=Username
- text=Products
- css=.some-selector

The accessibility snapshot syntax is descriptive and is not a valid target.
Never copy snapshot entries directly into target.

Convert snapshot elements to target format:
- textbox "Task" -> label=Task
- button "Add" -> role=button[name="Add"]
- visible text "Products" -> text=Products

Invalid targets include:
- textbox="Task"
- textbox "Task"
- button "Add"
- get_by_label("Task")
- page.locator(...)

For click and assert_text, target is required.
For fill and press, both target and value are required.
For finish, target and value must be null.
Always provide a short reason for the chosen action.
Use the execution history to avoid repeating actions that already succeeded.
""".strip()


def format_execution_history(route: list[ExecutionStep]) -> str:
    """Format completed steps as compact planner memory.

    TODO lesson 14: implement the compact representation described in
    learning/lesson_14_planner_memory/README.md.
    """
    return "TODO lesson 14"


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
            # TODO lesson 14: pass the route stored in AgentState.
            route=[],
        )
        return {"proposed_action": action}

    return plan
