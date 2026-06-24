import json
from datetime import datetime, timezone

import pytest

from browser_agent.domain import (
    RunReport,
    RunTermination,
    TerminationKind,
    TestCase as AgentTestCase,
)
from browser_agent.run_history import (
    JsonlRunHistoryStore,
    RunHistoryRecord,
    build_run_history_record,
)


def make_report(
    *,
    test_case_id: str = "history-case",
    status: str = "passed",
) -> RunReport:
    return RunReport(
        test_case=AgentTestCase(
            id=test_case_id,
            name="History case",
            start_url="https://example.com",
            goal="Verify the page",
            expected=["Page is visible"],
        ),
        status=status,
        final_url="https://example.com",
        final_snapshot='heading "Example"',
        step_count=0,
        failure_count=0,
        route=[],
        termination=RunTermination(
            kind=(
                TerminationKind.JUDGE_PASSED
                if status == "passed"
                else TerminationKind.JUDGE_FAILED
            ),
            message="History fixture termination.",
        ),
    )


def make_record(
    run_id: str,
    *,
    test_case_id: str = "history-case",
    minute: int = 0,
) -> RunHistoryRecord:
    return RunHistoryRecord(
        run_id=run_id,
        recorded_at=datetime(
            2026,
            6,
            23,
            10,
            minute,
            tzinfo=timezone.utc,
        ),
        report=make_report(test_case_id=test_case_id),
    )


def test_build_record_generates_identity_and_utc_time() -> None:
    record = build_run_history_record(make_report())

    assert record.run_id
    assert record.recorded_at.tzinfo is not None
    assert record.recorded_at.utcoffset() == timezone.utc.utcoffset(None)
    assert record.report.test_case.id == "history-case"


def test_build_record_accepts_injected_identity_and_time() -> None:
    recorded_at = datetime(2026, 6, 23, 12, 0, tzinfo=timezone.utc)

    record = build_run_history_record(
        make_report(),
        run_id="run-fixed",
        recorded_at=recorded_at,
    )

    assert record.run_id == "run-fixed"
    assert record.recorded_at == recorded_at


def test_build_record_rejects_explicit_blank_run_id() -> None:
    with pytest.raises(ValueError, match="run_id"):
        build_run_history_record(make_report(), run_id="")


def test_missing_history_file_loads_as_empty_list(tmp_path) -> None:
    store = JsonlRunHistoryStore(tmp_path / "history" / "runs.jsonl")

    assert store.load_all() == []


def test_append_creates_parent_and_writes_one_json_object_per_line(
    tmp_path,
) -> None:
    path = tmp_path / "history" / "runs.jsonl"
    store = JsonlRunHistoryStore(path)

    store.append(make_record("run-1"))
    store.append(make_record("run-2", minute=1))

    lines = path.read_text(encoding="utf-8").splitlines()

    assert len(lines) == 2
    assert json.loads(lines[0])["run_id"] == "run-1"
    assert json.loads(lines[1])["run_id"] == "run-2"


def test_load_all_restores_typed_records_in_append_order(tmp_path) -> None:
    store = JsonlRunHistoryStore(tmp_path / "runs.jsonl")
    first = make_record("run-1")
    second = make_record("run-2", minute=1)

    store.append(first)
    store.append(second)

    assert store.load_all() == [first, second]


def test_find_by_test_case_id_filters_history(tmp_path) -> None:
    store = JsonlRunHistoryStore(tmp_path / "runs.jsonl")
    store.append(make_record("run-a1", test_case_id="case-a"))
    store.append(make_record("run-b1", test_case_id="case-b", minute=1))
    store.append(make_record("run-a2", test_case_id="case-a", minute=2))

    records = store.find_by_test_case_id("case-a")

    assert [record.run_id for record in records] == [
        "run-a1",
        "run-a2",
    ]


def test_latest_for_test_case_returns_last_match_or_none(tmp_path) -> None:
    store = JsonlRunHistoryStore(tmp_path / "runs.jsonl")
    store.append(make_record("run-a1", test_case_id="case-a"))
    store.append(make_record("run-b1", test_case_id="case-b", minute=1))
    store.append(make_record("run-a2", test_case_id="case-a", minute=2))

    latest = store.latest_for_test_case("case-a")

    assert latest is not None
    assert latest.run_id == "run-a2"
    assert store.latest_for_test_case("missing") is None
