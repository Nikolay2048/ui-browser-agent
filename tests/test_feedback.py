import json
from datetime import datetime, timezone

import pytest

from browser_agent.feedback import (
    FeedbackScope,
    HumanFeedbackRecord,
    JsonlFeedbackStore,
    build_human_feedback_record,
)


def make_record(
    feedback_id: str,
    *,
    run_id: str = "run-1",
    test_case_id: str = "case-1",
    scope: FeedbackScope = FeedbackScope.RUN,
    step_number: int | None = None,
    minute: int = 0,
) -> HumanFeedbackRecord:
    return HumanFeedbackRecord(
        feedback_id=feedback_id,
        run_id=run_id,
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
        step_number=step_number,
        summary="Planner used the wrong locator.",
        correction="Prefer label=Email for the email field.",
        tags=["planner", "locator"],
    )


def test_build_feedback_record_generates_identity_and_utc_time() -> None:
    record = build_human_feedback_record(
        run_id="run-1",
        test_case_id="case-1",
        scope=FeedbackScope.RUN,
        summary="The run used an inefficient path.",
        correction="Avoid clicking Save when the success toast is already visible.",
    )

    assert record.feedback_id
    assert record.created_at.tzinfo is not None
    assert record.created_at.utcoffset() == timezone.utc.utcoffset(None)
    assert record.run_id == "run-1"
    assert record.test_case_id == "case-1"
    assert record.tags == []


def test_build_feedback_record_accepts_injected_identity_time_and_tags() -> None:
    created_at = datetime(2026, 6, 24, 12, 0, tzinfo=timezone.utc)

    record = build_human_feedback_record(
        feedback_id="feedback-fixed",
        created_at=created_at,
        run_id="run-1",
        test_case_id="case-1",
        scope=FeedbackScope.PLANNER,
        summary="Planner selected a fragile locator.",
        correction="Use role=button[name='Save profile'].",
        tags=["planner", "locator"],
    )

    assert record.feedback_id == "feedback-fixed"
    assert record.created_at == created_at
    assert record.tags == ["planner", "locator"]


def test_step_feedback_requires_step_number() -> None:
    with pytest.raises(ValueError, match="step_number"):
        build_human_feedback_record(
            run_id="run-1",
            test_case_id="case-1",
            scope=FeedbackScope.STEP,
            summary="Step feedback must point to a concrete route step.",
            correction="Set step_number for step-scoped feedback.",
        )


def test_non_step_feedback_rejects_step_number() -> None:
    with pytest.raises(ValueError, match="step_number"):
        build_human_feedback_record(
            run_id="run-1",
            test_case_id="case-1",
            scope=FeedbackScope.RUN,
            step_number=2,
            summary="Run feedback should not point to one route step.",
            correction="Use scope=step when feedback targets a concrete step.",
        )


def test_append_creates_parent_and_writes_one_json_object_per_line(tmp_path) -> None:
    path = tmp_path / "feedback" / "records.jsonl"
    store = JsonlFeedbackStore(path)

    store.append(make_record("feedback-1"))
    store.append(make_record("feedback-2", minute=1))

    lines = path.read_text(encoding="utf-8").splitlines()

    assert len(lines) == 2
    assert json.loads(lines[0])["feedback_id"] == "feedback-1"
    assert json.loads(lines[1])["feedback_id"] == "feedback-2"


def test_missing_feedback_file_loads_as_empty_list(tmp_path) -> None:
    store = JsonlFeedbackStore(tmp_path / "missing" / "records.jsonl")

    assert store.load_all() == []


def test_load_all_restores_typed_records_in_append_order(tmp_path) -> None:
    store = JsonlFeedbackStore(tmp_path / "records.jsonl")
    first = make_record("feedback-1")
    second = make_record("feedback-2", minute=1)

    store.append(first)
    store.append(second)

    assert store.load_all() == [first, second]


def test_find_by_test_case_id_filters_feedback(tmp_path) -> None:
    store = JsonlFeedbackStore(tmp_path / "records.jsonl")
    store.append(make_record("feedback-a1", test_case_id="case-a"))
    store.append(make_record("feedback-b1", test_case_id="case-b", minute=1))
    store.append(make_record("feedback-a2", test_case_id="case-a", minute=2))

    records = store.find_by_test_case_id("case-a")

    assert [record.feedback_id for record in records] == [
        "feedback-a1",
        "feedback-a2",
    ]


def test_find_by_run_id_filters_feedback(tmp_path) -> None:
    store = JsonlFeedbackStore(tmp_path / "records.jsonl")
    store.append(make_record("feedback-a1", run_id="run-a"))
    store.append(make_record("feedback-b1", run_id="run-b", minute=1))
    store.append(make_record("feedback-a2", run_id="run-a", minute=2))

    records = store.find_by_run_id("run-a")

    assert [record.feedback_id for record in records] == [
        "feedback-a1",
        "feedback-a2",
    ]
