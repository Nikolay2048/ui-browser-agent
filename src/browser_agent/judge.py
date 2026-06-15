"""Independent expected-result Judge for lesson 15."""

from langchain_core.prompts import ChatPromptTemplate

from browser_agent.models import JudgeVerdict
from browser_agent.planner import format_execution_history
from browser_agent.state import AgentState

JUDGE_SYSTEM_PROMPT = """
You are an independent UI test judge.

Evaluate every expected result using only the supplied evidence.
Do not assume that a successful browser action proves a business result.
Do not trust the planner's finish decision.
Each expected result must have its own check and concrete evidence.
The overall verdict passes only when every expected result is proven.
If evidence is missing or ambiguous, fail the verdict.
""".strip()


def build_judge_prompt() -> ChatPromptTemplate:
    return ChatPromptTemplate.from_messages([
        (
            "system",
            JUDGE_SYSTEM_PROMPT
        ),
        (
            "human",
            """
            Expected results:
            {expected}
            
            Execution history:
            {execution_history}
            
            Current page snapshot:
            {page_snapshot}
            """
        )
    ])


def build_judge_chain(model):
    prompt = build_judge_prompt()
    structured_model = model.with_structured_output(JudgeVerdict)
    return prompt | structured_model


def judge_run(model, test_case, page_snapshot, route) -> JudgeVerdict:
    chain = build_judge_chain(model)
    execution_history = format_execution_history(route)
    return chain.invoke({
        "execution_history": execution_history,
        "expected": test_case.expected,
        "page_snapshot": page_snapshot
    })


def make_judge_node(model):
    def judge(state: AgentState) -> dict:
        verdict = judge_run(model, state["test_case"], state["page_snapshot"], state["route"])
        return {"verdict": verdict}

    return judge
