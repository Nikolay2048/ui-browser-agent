"""Failure classification role for lesson 19."""
from typing import Any

from anyio.itertools import Chain
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable

from browser_agent.models import FailureClassification, TestCase
from browser_agent.planner import format_execution_history
from browser_agent.state import AgentState

CLASSIFIER_SYSTEM_PROMPT = """
You are an independent failure classifier for UI test runs.

Classify only from supplied evidence. Do not invent missing facts.

Categories:
- product_bug: the observed product behavior contradicts an expected result.
- agent_error: the planner selected an invalid, irrelevant, or repeatedly failing action.
- automation_error: locators, timing, assertions, or browser automation failed without enough evidence of a product defect.
- environment_error: the site, browser, network, credentials, or test environment is unavailable or broken.
- insufficient_evidence: the available evidence does not support a reliable category.

Recommend creating a bug only for product_bug with concrete product evidence.
""".strip()


def build_classifier_prompt() -> ChatPromptTemplate:
    return ChatPromptTemplate.from_messages([
        (
            "system",
            CLASSIFIER_SYSTEM_PROMPT,
        ),
        (
            "human",
            """
            Goal:
            {goal}

            Expected results:
            {expected}

            Termination:
            {termination}

            Judge verdict:
            {judge_verdict}

            Execution history:
            {execution_history}

            Final page snapshot:
            {page_snapshot}
            """,
        ),
    ])


def build_classifier_chain(model) -> Runnable:
    """compose prompt and structured classification output."""

    prompt = build_classifier_prompt()
    structured_model = model.with_structured_output(FailureClassification)
    return prompt | structured_model


def classify_failure(
        model,
        test_case: TestCase,
        termination,
        page_snapshot,
        route,
        verdict=None,
) -> FailureClassification:
    """classify one failed run."""
    execution_history = format_execution_history(route)
    chain = build_classifier_chain(model)
    return chain.invoke(
        {
            "goal": test_case.goal,
            "expected": test_case.expected,
            "termination": termination,
            "judge_verdict": verdict,
            "execution_history": execution_history,
            "page_snapshot": page_snapshot,
        })


def make_classifier_node(model):
    """create a node that stores failure classification."""

    def classify(state: AgentState):
        classification = classify_failure(
            model,
            state["test_case"],
            state["termination"],
            state["page_snapshot"],
            state["route"],
            state.get("verdict")
        )
        return {"classification": classification}

    return classify
