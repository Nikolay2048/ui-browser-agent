"""Human feedback memory for completed agent runs."""
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator


class FeedbackScope(StrEnum):
    RUN = "run"
    STEP = "step"
    PLANNER = "planner"
    JUDGE = "judge"
    BUG_REPORT = "bug_report"


class HumanFeedbackRecord(BaseModel):
    feedback_id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    test_case_id: str = Field(min_length=1)
    created_at: datetime
    scope: FeedbackScope
    step_number: int | None = Field(default=None, ge=1)
    summary: str = Field(min_length=1)
    correction: str = Field(min_length=1)
    tags: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_step_scope(self) -> "HumanFeedbackRecord":
        if self.scope == FeedbackScope.STEP and self.step_number is None:
            raise ValueError("scope=step requires step_number")
        if self.scope != FeedbackScope.STEP and self.step_number is not None:
            raise ValueError("step_number is only allowed when scope is STEP")
        return self


def build_human_feedback_record(
        *,
        run_id: str,
        test_case_id: str,
        scope: FeedbackScope,
        summary: str,
        correction: str,
        step_number: int | None = None,
        tags: list[str] | None = None,
        feedback_id: str | None = None,
        created_at: datetime | None = None,
) -> HumanFeedbackRecord:
    if feedback_id is None:
        feedback_id = str(uuid4())

    if created_at is None:
        created_at = datetime.now(timezone.utc)

    if tags is None:
        tags = []

    return HumanFeedbackRecord(
        feedback_id=feedback_id,
        run_id=run_id,
        test_case_id=test_case_id,
        created_at=created_at,
        scope=scope,
        step_number=step_number,
        summary=summary,
        correction=correction,
        tags=tags,
    )

class JsonlFeedbackStore:
    """Persist human feedback records as one JSON object per line."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def append(self, record: HumanFeedbackRecord) -> None:
        """Append one feedback record."""
        self.path.parent.mkdir(parents=True, exist_ok=True)

        with self.path.open("a", encoding="utf-8") as feedback_file:
            feedback_file.write(record.model_dump_json() + "\n")

    def load_all(self) -> list[HumanFeedbackRecord]:
        """Load all feedback records in append order."""
        if not self.path.exists():
            return []

        records: list[HumanFeedbackRecord] = []

        with self.path.open("r", encoding="utf-8") as feedback_file:
            for line in feedback_file:
                line = line.strip()

                if not line:
                    continue

                record = HumanFeedbackRecord.model_validate_json(line)
                records.append(record)

        return records

    def find_by_test_case_id(
            self,
            test_case_id: str,
    ) -> list[HumanFeedbackRecord]:
        """Return feedback for one test case."""
        return [
            record
            for record in self.load_all()
            if record.test_case_id == test_case_id
        ]

    def find_by_run_id(
            self,
            run_id: str,
    ) -> list[HumanFeedbackRecord]:
        """Return feedback for one run."""
        return [
            record
            for record in self.load_all()
            if record.run_id == run_id
        ]
