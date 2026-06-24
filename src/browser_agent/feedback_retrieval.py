"""Retrieval helpers for human feedback memory."""

from pydantic import BaseModel, Field

from browser_agent.domain import TestCase
from browser_agent.feedback import FeedbackScope, HumanFeedbackRecord


class FeedbackRetrievalQuery(BaseModel):
    test_case: TestCase
    scopes: list[FeedbackScope] = Field(default_factory=list)
    required_tags: list[str] = Field(default_factory=list)
    limit: int = Field(default=5, ge=1, le=20)


def retrieve_feedback(
        query: FeedbackRetrievalQuery,
        records: list[HumanFeedbackRecord],
) -> list[HumanFeedbackRecord]:
    matching_records: list[HumanFeedbackRecord] = []

    required_tags = set(query.required_tags)

    for record in records:
        if record.test_case_id != query.test_case.id:
            continue

        if query.scopes and record.scope not in query.scopes:
            continue

        if required_tags and not set(record.tags).intersection(required_tags):
            continue

        matching_records.append(record)

    matching_records.sort(
        key=lambda record: record.created_at,
        reverse=True,
    )

    return matching_records[: query.limit]


def retrieve_feedback_from_store(
        query: FeedbackRetrievalQuery,
        store,
) -> list[HumanFeedbackRecord]:
    records = store.load_all()
    return retrieve_feedback(query, records)


def format_feedback_for_prompt(records: list[HumanFeedbackRecord]) -> str:
    if not records:
        return ""

    lines = ["Previous human feedback:"]

    for index, record in enumerate(records, start=1):
        tags = ", ".join(record.tags) if record.tags else "none"

        lines.extend(
            [
                f"{index}. [{record.scope.value}] {record.summary}",
                f"   Correction: {record.correction}",
                f"   Tags: {tags}",
            ]
        )

    return "\n".join(lines)
