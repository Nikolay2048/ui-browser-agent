from datetime import datetime, timezone

import pytest

from browser_agent.domain import TestCase as AgentTestCase
from browser_agent.feedback import FeedbackScope, HumanFeedbackRecord
from browser_agent.feedback_retrieval import (
    FeedbackRetrievalQuery,
    format_feedback_for_prompt,
    retrieve_feedback,
    retrieve_feedback_from_store,
)


def make_case(test_case_id: str = "case-a") -> AgentTestCase:
    return AgentTestCase(
        id=test_case_id,
        name="Feedback retrieval case",
        start_url="https://example.com",
        goal="Save a profile form",
        expected=["Profile saved message is visible"],
    )


def make_record(
    feedback_id: str,
    *,
    test_case_id: str = "case-a",
    scope: FeedbackScope = FeedbackScope.PLANNER,
    tags: list[str] | None = None,
    minute: int = 0,
) -> HumanFeedbackRecord:
    return HumanFeedbackRecord(
        feedback_id=feedback_id,
        run_id=f"run-{feedback_id}",
        test_case_id=test_case_id,
        created_at=datetime(
            2026,
            6,
            24,
            10,
            minute,
            tzinfo=timezone.utc,
        ),
        scope=scope,
        step_number=None,
        summary=f"Summary for {feedback_id}",
        correction=f"Correction for {feedback_id}",
        tags=tags or [],
    )


class InMemoryFeedbackStore:
    def __init__(self, records: list[HumanFeedbackRecord]) -> None:
        self.records = records

    def load_all(self) -> list[HumanFeedbackRecord]:
        return self.records


def test_query_rejects_invalid_limit() -> None:
    with pytest.raises(ValueError, match="limit"):
        FeedbackRetrievalQuery(test_case=make_case(), limit=0)


def test_retrieve_feedback_filters_by_test_case_and_returns_newest_first() -> None:
    records = [
        make_record("old", minute=1),
        make_record("other-case", test_case_id="case-b", minute=2),
        make_record("new", minute=3),
    ]
    query = FeedbackRetrievalQuery(test_case=make_case("case-a"))

    result = retrieve_feedback(query, records)

    assert [record.feedback_id for record in result] == ["new", "old"]


def test_retrieve_feedback_sorts_by_created_at_not_input_order() -> None:
    records = [
        make_record("new", minute=3),
        make_record("old", minute=1),
        make_record("middle", minute=2),
    ]
    query = FeedbackRetrievalQuery(test_case=make_case("case-a"))

    result = retrieve_feedback(query, records)

    assert [record.feedback_id for record in result] == [
        "new",
        "middle",
        "old",
    ]


def test_retrieve_feedback_filters_by_scope() -> None:
    records = [
        make_record("planner", scope=FeedbackScope.PLANNER, minute=1),
        make_record("judge", scope=FeedbackScope.JUDGE, minute=2),
        make_record("bug", scope=FeedbackScope.BUG_REPORT, minute=3),
    ]
    query = FeedbackRetrievalQuery(
        test_case=make_case(),
        scopes=[FeedbackScope.PLANNER, FeedbackScope.JUDGE],
    )

    result = retrieve_feedback(query, records)

    assert [record.feedback_id for record in result] == ["judge", "planner"]


def test_retrieve_feedback_filters_by_any_required_tag() -> None:
    records = [
        make_record("planner-memory", tags=["planner", "memory"], minute=1),
        make_record("judge-evidence", tags=["judge", "evidence"], minute=2),
        make_record("bug-title", tags=["bug-report"], minute=3),
    ]
    query = FeedbackRetrievalQuery(
        test_case=make_case(),
        required_tags=["planner", "evidence"],
    )

    result = retrieve_feedback(query, records)

    assert [record.feedback_id for record in result] == [
        "judge-evidence",
        "planner-memory",
    ]


def test_retrieve_feedback_applies_limit_after_sorting() -> None:
    records = [
        make_record("one", minute=1),
        make_record("two", minute=2),
        make_record("three", minute=3),
    ]
    query = FeedbackRetrievalQuery(test_case=make_case(), limit=2)

    result = retrieve_feedback(query, records)

    assert [record.feedback_id for record in result] == ["three", "two"]


def test_retrieve_feedback_from_store_loads_records() -> None:
    store = InMemoryFeedbackStore(
        [
            make_record("old", minute=1),
            make_record("new", minute=2),
        ]
    )
    query = FeedbackRetrievalQuery(test_case=make_case())

    result = retrieve_feedback_from_store(query, store)

    assert [record.feedback_id for record in result] == ["new", "old"]


def test_format_feedback_for_prompt_returns_empty_string_for_no_records() -> None:
    assert format_feedback_for_prompt([]) == ""


def test_format_feedback_for_prompt_renders_records_in_input_order() -> None:
    records = [
        make_record(
            "first",
            scope=FeedbackScope.PLANNER,
            tags=["planner", "locator"],
        ),
        make_record(
            "second",
            scope=FeedbackScope.JUDGE,
            tags=[],
        ),
    ]

    text = format_feedback_for_prompt(records)

    assert text.startswith("Previous human feedback:")
    assert "1. [planner] Summary for first" in text
    assert "Correction: Correction for first" in text
    assert "Tags: planner, locator" in text
    assert "2. [judge] Summary for second" in text
    assert "Correction: Correction for second" in text
