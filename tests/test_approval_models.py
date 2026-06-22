import pytest
from pydantic import ValidationError

from browser_agent.domain import ActionApproval


def test_action_approval_accepts_explicit_decision() -> None:
    decision = ActionApproval(
        approved=True,
        reason="The proposed action matches the test case.",
    )

    assert decision.approved is True
    assert decision.reason.startswith("The proposed action")


@pytest.mark.parametrize("reason", ["", "   "])
def test_action_approval_rejects_blank_reason(reason: str) -> None:
    with pytest.raises(ValidationError):
        ActionApproval(approved=False, reason=reason)
