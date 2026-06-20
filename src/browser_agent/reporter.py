"""Structured bug reporter role for lesson 20."""

from langchain_core.prompts import ChatPromptTemplate

from browser_agent.models import BugReport
from browser_agent.planner import format_execution_history
from browser_agent.state import AgentState

REPORTER_SYSTEM_PROMPT = """
You are a senior QA engineer writing a product bug report.

Use only supplied evidence. Do not invent actions, UI elements, preconditions,
URLs, expected behavior, or actual behavior.

The report must be reproducible and concise.
Steps to reproduce must follow the successful and failed actions in the
execution history.
Expected result must come from the test case.
Actual result must come from the final snapshot, Judge verdict, failure
classification, or action errors.
Evidence must contain concrete observable facts.
""".strip()


def build_reporter_prompt() -> ChatPromptTemplate:
    """build the reporter prompt."""
    return ChatPromptTemplate.from_messages([
        (
            "system",
            REPORTER_SYSTEM_PROMPT
        ),
        (
            "human",
            """
            Test case:
            {test_case}
            
            Classification:
            {classification}
            
            Termination:
            {termination}
            
            Judge verdict:
            {judge_verdict}
            
            Execution history:
            {execution_history}
            
            Final page snapshot:
            {page_snapshot}
            """
        )
    ])


def build_reporter_chain(model):
    """compose prompt and structured BugReport output."""
    structured_model = model.with_structured_output(BugReport)
    prompt = build_reporter_prompt()
    return prompt | structured_model


def create_bug_report(
        model,
        test_case,
        classification,
        termination,
        page_snapshot,
        route,
        verdict=None,
) -> BugReport:
    """create one evidence-based bug report."""
    chain = build_reporter_chain(model)
    execution_history = format_execution_history(route)
    return chain.invoke({
        "test_case": test_case,
        "classification": classification,
        "termination": termination,
        "judge_verdict": verdict,
        "execution_history": execution_history,
        "page_snapshot": page_snapshot
    })


def make_reporter_node(model):
    """create a node that stores bug_report."""

    def report(state: AgentState) -> dict:
        bug_report = create_bug_report(model, state["test_case"], state["classification"], state["termination"],
                                       state["page_snapshot"], state["route"], state.get("verdict"))

        return {"bug_report": bug_report}

    return report
