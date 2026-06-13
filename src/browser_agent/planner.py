"""LLM planner from lesson 5.

The related lesson is archived in learning/lesson_05_planner/README.md.
"""
from langchain_core.prompts import ChatPromptTemplate

from browser_agent.models import BrowserAction
from browser_agent.state import AgentState

SYSTEM_PROMPT = """
You are a browser testing planner.

Your task is to choose exactly one next action.
Use the current page snapshot and the test case goal.
Do not invent elements, text, or selectors that are not present in the snapshot.
Use test data from the test case when input values are required.
Return only the next action, not a full plan.
The action must be valid according to the BrowserAction schema.
For click and assert_text, target is required.
For fill and press, both target and value are required.
For finish, target and value must be null.
Always provide a short reason for the chosen action.
""".strip()


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


def plan_next_action(model, test_case, page_snapshot):
    """ invoke the planner chain and return BrowserAction."""
    chain = build_planner_chain(model)

    return chain.invoke({
        "goal": test_case.goal,
        "test_data": test_case.test_data,
        "expected": test_case.expected,
        "page_snapshot": page_snapshot,
    })


def make_plan_node(model):
    """Create a LangGraph node that stores the next proposed action."""

    def plan(state: AgentState) -> dict:
        action = plan_next_action(
            model=model,
            test_case=state["test_case"],
            page_snapshot=state["page_snapshot"],
        )
        return {"proposed_action": action}

    return plan
