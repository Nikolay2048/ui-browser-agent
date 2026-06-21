"""Deterministic policy for deciding when human approval is required."""

from collections.abc import Callable

from browser_agent.models import (
    ApprovalPolicyDecision,
    BrowserAction,
    BrowserActionType,
)
from browser_agent.state import AgentState


ApprovalPolicy = Callable[[BrowserAction], ApprovalPolicyDecision]


RISKY_CLICK_KEYWORDS = {
    "delete",
    "remove",
    "pay",
    "purchase",
    "checkout",
    "confirm",
    "publish",
    "send",
    "submit",
}

SENSITIVE_FILL_KEYWORDS = {
    "password",
    "passcode",
    "token",
    "secret",
    "card",
    "cvv",
}


def _target_text(action: BrowserAction) -> str:
    """Normalize action target text for keyword checks."""
    if action.target is None:
        return ""

    parts = [action.target.value]

    if action.target.name:
        parts.append(action.target.name)

    return " ".join(parts).lower()


def assess_action_risk(action: BrowserAction) -> ApprovalPolicyDecision:
    """Classify one proposed action using explicit safety rules."""
    target_text = _target_text(action)

    if action.action == BrowserActionType.FINISH:
        return ApprovalPolicyDecision(
            requires_approval=False,
            reason="finish action is always safe",
        )

    if action.action == BrowserActionType.ASSERT_TEXT:
        return ApprovalPolicyDecision(
            requires_approval=False,
            reason="assert_text action is always safe",
        )

    if action.action == BrowserActionType.FILL:
        if any(keyword in target_text for keyword in SENSITIVE_FILL_KEYWORDS):
            return ApprovalPolicyDecision(
                requires_approval=True,
                reason="fill action targets a sensitive field",
            )

        return ApprovalPolicyDecision(
            requires_approval=False,
            reason="fill action targets a regular field",
        )

    if action.action == BrowserActionType.PRESS:
        pressed_value = ""
        for attr in ("text", "value", "key"):
            value = getattr(action, attr, None)
            if value:
                pressed_value = str(value).lower()
                break

        if pressed_value == "enter":
            return ApprovalPolicyDecision(
                requires_approval=True,
                reason="press Enter action requires approval",
            )

    if action.action == BrowserActionType.CLICK:
        if any(keyword in target_text for keyword in RISKY_CLICK_KEYWORDS):
            return ApprovalPolicyDecision(
                requires_approval=True,
                reason="click action targets a risky keyword",
            )

        return ApprovalPolicyDecision(
            requires_approval=False,
            reason="click action has no risky target keyword",
        )

    return ApprovalPolicyDecision(
        requires_approval=False,
        reason="action does not match any risky policy rule",
    )


def make_assess_action_node(
    policy: ApprovalPolicy = assess_action_risk,
):
    """Create a LangGraph node that stores the policy decision."""

    def assess(state: AgentState) -> dict:
        decision = policy(state["proposed_action"])
        return {"approval_policy_decision": decision}

    return assess


def route_after_risk_assessment(state: AgentState) -> str:
    """Route safe actions to execution and risky actions to approval."""
    if state["approval_policy_decision"].requires_approval:
        return "request_approval"

    return "execute"