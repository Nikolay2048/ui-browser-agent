import pytest
from pydantic import ValidationError

from browser_agent.domain import FailureCategory, FailureClassification


def test_product_bug_classification_can_recommend_bug_report() -> None:
    classification = FailureClassification(
        category="product_bug",
        confidence=0.9,
        rationale="The expected task is absent from the final page.",
        evidence=["Judge check failed: task is not visible."],
        should_create_bug=True,
    )

    assert classification.category == FailureCategory.PRODUCT_BUG
    assert classification.confidence == 0.9
    assert classification.should_create_bug is True


@pytest.mark.parametrize("confidence", [-0.01, 1.01])
def test_classification_rejects_invalid_confidence(confidence: float) -> None:
    with pytest.raises(ValidationError):
        FailureClassification(
            category="agent_error",
            confidence=confidence,
            rationale="Planner repeated an invalid action.",
            evidence=["The same failed action appears twice."],
            should_create_bug=False,
        )


def test_non_product_category_cannot_recommend_bug_report() -> None:
    with pytest.raises(ValidationError):
        FailureClassification(
            category="automation_error",
            confidence=0.8,
            rationale="Playwright locator timed out.",
            evidence=["Locator.wait_for timed out."],
            should_create_bug=True,
        )
