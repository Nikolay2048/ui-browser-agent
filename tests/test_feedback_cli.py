from pathlib import Path

from browser_agent.feedback import FeedbackScope, HumanFeedbackRecord
from browser_agent.feedback_cli import (
    DEFAULT_FEEDBACK_PATH,
    build_feedback_parser,
    main,
    parse_tags,
    save_feedback_from_args,
)


def test_parse_tags_handles_empty_values_and_trims_spaces() -> None:
    assert parse_tags(None) == []
    assert parse_tags("") == []
    assert parse_tags("planner, locator ,, task-input ") == [
        "planner",
        "locator",
        "task-input",
    ]


def test_parser_builds_expected_arguments(tmp_path) -> None:
    parser = build_feedback_parser()

    args = parser.parse_args(
        [
            "--run-id",
            "run-1",
            "--test-case-id",
            "case-1",
            "--scope",
            "step",
            "--step-number",
            "2",
            "--summary",
            "Planner selected a fragile locator.",
            "--correction",
            "Use label=Email for the email input.",
            "--tags",
            "planner,locator",
            "--feedback-path",
            str(tmp_path / "feedback.jsonl"),
        ]
    )

    assert args.run_id == "run-1"
    assert args.test_case_id == "case-1"
    assert args.scope == "step"
    assert args.step_number == 2
    assert args.summary == "Planner selected a fragile locator."
    assert args.correction == "Use label=Email for the email input."
    assert args.tags == "planner,locator"
    assert args.feedback_path == tmp_path / "feedback.jsonl"


def test_parser_uses_default_feedback_path() -> None:
    parser = build_feedback_parser()

    args = parser.parse_args(
        [
            "--run-id",
            "run-1",
            "--test-case-id",
            "case-1",
            "--scope",
            "run",
            "--summary",
            "The run used an inefficient path.",
            "--correction",
            "Avoid clicking Save when success is already visible.",
        ]
    )

    assert args.feedback_path == DEFAULT_FEEDBACK_PATH


def test_save_feedback_from_args_appends_record(tmp_path) -> None:
    parser = build_feedback_parser()
    feedback_path = tmp_path / "feedback" / "records.jsonl"
    args = parser.parse_args(
        [
            "--run-id",
            "run-1",
            "--test-case-id",
            "case-1",
            "--scope",
            "step",
            "--step-number",
            "3",
            "--summary",
            "Planner selected a fragile locator.",
            "--correction",
            "Use role=button[name='Save profile'].",
            "--tags",
            "planner, locator",
            "--feedback-path",
            str(feedback_path),
        ]
    )

    record = save_feedback_from_args(args)

    assert isinstance(record, HumanFeedbackRecord)
    assert record.run_id == "run-1"
    assert record.test_case_id == "case-1"
    assert record.scope == FeedbackScope.STEP
    assert record.step_number == 3
    assert record.tags == ["planner", "locator"]
    assert feedback_path.is_file()

    loaded = HumanFeedbackRecord.model_validate_json(
        feedback_path.read_text(encoding="utf-8").strip()
    )
    assert loaded == record


def test_main_saves_feedback_and_prints_json(tmp_path, capsys) -> None:
    feedback_path = tmp_path / "records.jsonl"

    exit_code = main(
        [
            "--run-id",
            "run-1",
            "--test-case-id",
            "case-1",
            "--scope",
            "planner",
            "--summary",
            "Planner ignored previous evidence.",
            "--correction",
            "Check visible success messages before proposing another action.",
            "--tags",
            "planner,memory",
            "--feedback-path",
            str(feedback_path),
        ]
    )

    output = capsys.readouterr().out

    assert exit_code == 0
    assert '"run_id": "run-1"' in output
    assert '"scope": "planner"' in output
    assert feedback_path.is_file()
