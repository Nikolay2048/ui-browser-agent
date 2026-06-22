import pytest

from browser_agent.approval_policy import (
    assess_action_risk,
    make_assess_action_node,
    route_after_risk_assessment,
)
from browser_agent.domain import (
    ApprovalPolicyDecision,
    BrowserAction,
    BrowserTarget,
    BrowserTargetStrategy,
)


def action(
    action_type: str,
    *,
    strategy: str = "role",
    value: str = "button",
    name: str | None = "Continue",
    input_value: str | None = None,
) -> BrowserAction:
    target = None
    if action_type != "finish":
        target = BrowserTarget(
            strategy=BrowserTargetStrategy(strategy),
            value=value,
            name=name if strategy == "role" else None,
        )
    return BrowserAction(
        action=action_type,
        target=target,
        value=input_value,
        reason="Continue the test scenario.",
    )


@pytest.mark.parametrize(
    "proposed_action",
    [
        action("click", name="Continue"),
        action(
            "fill",
            strategy="label",
            value="Search",
            name=None,
            input_value="LangGraph",
        ),
        action(
            "assert_text",
            strategy="text",
            value="Completed",
            name=None,
        ),
        action("finish", name=None),
    ],
)
def test_safe_actions_do_not_require_approval(proposed_action) -> None:
    decision = assess_action_risk(proposed_action)

    assert decision.requires_approval is False
    assert decision.reason


@pytest.mark.parametrize(
    "proposed_action",
    [
        action("click", name="Delete account"),
        action("click", name="Pay now"),
        action(
            "fill",
            strategy="label",
            value="Password",
            name=None,
            input_value="secret",
        ),
        action(
            "press",
            strategy="label",
            value="Checkout form",
            name=None,
            input_value="Enter",
        ),
    ],
)
def test_risky_actions_require_approval(proposed_action) -> None:
    decision = assess_action_risk(proposed_action)

    assert decision.requires_approval is True
    assert decision.reason


def test_policy_node_stores_decision() -> None:
    proposed_action = action("click", name="Delete task")
    node = make_assess_action_node()

    update = node({"proposed_action": proposed_action})

    assert update["approval_policy_decision"].requires_approval is True


def test_policy_router_uses_stored_decision() -> None:
    safe_state = {
        "approval_policy_decision": ApprovalPolicyDecision(
            requires_approval=False,
            reason="Read-only assertion.",
        )
    }
    risky_state = {
        "approval_policy_decision": ApprovalPolicyDecision(
            requires_approval=True,
            reason="Destructive action.",
        )
    }

    assert route_after_risk_assessment(safe_state) == "execute"
    assert route_after_risk_assessment(risky_state) == "request_approval"
