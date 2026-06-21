from browser_agent.approval import (
    build_approval_payload,
    reject_run,
    request_action_approval,
    route_after_approval,
)
from browser_agent.models import (
    ActionApproval,
    BrowserAction,
    BrowserTarget,
    BrowserTargetStrategy,
    TerminationKind,
)


def make_state() -> dict:
    return {
        "step_count": 2,
        "page_snapshot": '- button "Delete account"',
        "proposed_action": BrowserAction(
            action="click",
            target=BrowserTarget(
                strategy=BrowserTargetStrategy.ROLE,
                value="button",
                name="Delete account",
            ),
            value=None,
            reason="Continue the requested destructive scenario.",
        ),
    }


def test_approval_payload_contains_reviewable_action() -> None:
    payload = build_approval_payload(make_state())

    assert payload["type"] == "browser_action_approval"
    assert payload["step_number"] == 3
    assert payload["action"]["action"] == "click"
    assert payload["action"]["target"]["strategy"] == "role"
    assert payload["page_snapshot"] == '- button "Delete account"'


def test_approval_node_validates_resume_value(monkeypatch) -> None:
    captured = {}

    def fake_interrupt(payload):
        captured.update(payload)
        return {
            "approved": True,
            "reason": "Reviewed and approved.",
        }

    monkeypatch.setattr("browser_agent.approval.interrupt", fake_interrupt)

    update = request_action_approval(make_state())

    assert captured["type"] == "browser_action_approval"
    assert update == {
        "action_approval": ActionApproval(
            approved=True,
            reason="Reviewed and approved.",
        )
    }


def test_approval_router_uses_validated_decision() -> None:
    approved_state = {
        "action_approval": ActionApproval(
            approved=True,
            reason="Proceed.",
        )
    }
    rejected_state = {
        "action_approval": ActionApproval(
            approved=False,
            reason="Action is outside the test case.",
        )
    }

    assert route_after_approval(approved_state) == "execute"
    assert route_after_approval(rejected_state) == "reject_run"


def test_reject_run_records_human_termination() -> None:
    state = {
        "action_approval": ActionApproval(
            approved=False,
            reason="The target is destructive.",
        )
    }

    update = reject_run(state)

    assert update["status"] == "failed"
    assert update["termination"].kind is TerminationKind.HUMAN_REJECTED
    assert update["termination"].message == "The target is destructive."
