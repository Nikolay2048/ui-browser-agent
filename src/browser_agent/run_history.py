"""Durable append-only history of completed agent runs."""

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel, Field

from browser_agent.domain import RunReport


class RunHistoryRecord(BaseModel):
    """One completed run stored as episodic agent memory."""

    run_id: str = Field(min_length=1)
    recorded_at: datetime
    report: RunReport


def build_run_history_record(
        report: RunReport,
        *,
        run_id: str | None = None,
    recorded_at: datetime | None = None,
) -> RunHistoryRecord:
    """Create a history record with injectable identity and time."""
    if run_id is None:
        run_id = str(uuid4())

    if recorded_at is None:
        recorded_at = datetime.now(timezone.utc)

    return RunHistoryRecord(
        run_id=run_id,
        recorded_at=recorded_at,
        report=report,
    )


class JsonlRunHistoryStore:
    """Persist run records as one JSON object per line."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def append(self, record: RunHistoryRecord) -> None:
        """Append one record without rewriting existing history."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as history_file:
            history_file.write(record.model_dump_json() + "\n")

    def load_all(self) -> list[RunHistoryRecord]:
        """Load records in append order."""
        if not self.path.exists():
            return []

        records: list[RunHistoryRecord] = []

        with self.path.open("r", encoding="utf-8") as history_file:
            for line in history_file:
                line = line.strip()

                if not line:
                    continue

                record = RunHistoryRecord.model_validate_json(line)
                records.append(record)

        return records

    def find_by_test_case_id(
            self,
            test_case_id: str,
    ) -> list[RunHistoryRecord]:
        """Return records for one test case in append order."""

        records: list[RunHistoryRecord] = self.load_all()
        test_case_records: list[RunHistoryRecord] = list()
        for record in records:
            if record.report.test_case.id == test_case_id:
                test_case_records.append(record)
        return test_case_records

    def latest_for_test_case(
            self,
            test_case_id: str,
    ) -> RunHistoryRecord | None:
        """Return the latest matching record or None."""

        records = self.find_by_test_case_id(test_case_id)

        if not records:
            return None

        return records[-1]
