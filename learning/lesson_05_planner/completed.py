"""Completed LangChain planner after lesson 5."""

from langchain_core.prompts import ChatPromptTemplate

from browser_agent.domain import BrowserAction

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
    return ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT),
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
                """,
            ),
        ]
    )


def build_planner_chain(model):
    prompt = build_planner_prompt()
    structured_model = model.with_structured_output(BrowserAction)
    return prompt | structured_model


def plan_next_action(model, test_case, page_snapshot):
    chain = build_planner_chain(model)
    return chain.invoke(
        {
            "goal": test_case.goal,
            "test_data": test_case.test_data,
            "expected": test_case.expected,
            "page_snapshot": page_snapshot,
        }
    )
