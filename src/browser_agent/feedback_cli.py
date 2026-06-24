"""Command-line helpers for collecting human feedback."""


import argparse
from pathlib import Path
from typing import Sequence

from browser_agent.feedback import (
    FeedbackScope,
    HumanFeedbackRecord,
    JsonlFeedbackStore,
    build_human_feedback_record,
)

DEFAULT_FEEDBACK_PATH = Path("artifacts") / "feedback" / "feedback.jsonl"


def parse_tags(raw: str | None) -> list[str]:
    if raw is None:
        return []

    return [
        tag.strip()
        for tag in raw.split(",")
        if tag.strip()
    ]


def build_feedback_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Add human feedback for a completed agent run."
    )

    parser.add_argument("--run-id", required=True)
    parser.add_argument("--test-case-id", required=True)
    parser.add_argument(
        "--scope",
        required=True,
        choices=[scope.value for scope in FeedbackScope],
    )
    parser.add_argument("--summary", required=True)
    parser.add_argument("--correction", required=True)
    parser.add_argument("--step-number", type=int)
    parser.add_argument("--tags")
    parser.add_argument(
        "--feedback-path",
        type=Path,
        default=DEFAULT_FEEDBACK_PATH,
    )

    return parser


def save_feedback_from_args(args: argparse.Namespace) -> HumanFeedbackRecord:
    store = JsonlFeedbackStore(args.feedback_path)

    record = build_human_feedback_record(
        run_id=args.run_id,
        test_case_id=args.test_case_id,
        scope=FeedbackScope(args.scope),
        summary=args.summary,
        correction=args.correction,
        step_number=args.step_number,
        tags=parse_tags(args.tags),
    )

    store.append(record)
    return record


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_feedback_parser()
    args = parser.parse_args(argv)

    record = save_feedback_from_args(args)

    print(record.model_dump_json(indent=2))
    return 0