"""Human approval before executing a proposed browser action."""

from langgraph.types import interrupt

from browser_agent.models import ActionApproval, RunTermination, TerminationKind
from browser_agent.state import AgentState


def build_approval_payload(state: AgentState) -> dict:
    """Build the JSON-serializable value exposed by interrupt()."""
    return {
        "type": "browser_action_approval",
        "step_number": state["step_count"] + 1,
        "action": state["proposed_action"].model_dump(mode="json"),
        "page_snapshot": state["page_snapshot"],
    }


def request_action_approval(state: AgentState) -> dict:
    """Pause the graph and validate the decision supplied on resume."""
    resume_value = interrupt(build_approval_payload(state))
    decision = ActionApproval.model_validate(resume_value)
    return {"action_approval": decision}


def route_after_approval(state: AgentState) -> str:
    """Route an approved action to execution and a rejection to termination."""
    if state["action_approval"].approved:
        return "execute"
    return "reject_run"


def reject_run(state: AgentState) -> dict:
    """Terminate a run after a human rejects the proposed action."""
    return {
        "status": "failed",
        "termination": RunTermination(
            kind=TerminationKind.HUMAN_REJECTED,
            message=state["action_approval"].reason,
        ),
    }
