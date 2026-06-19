"""Termination reason completed in lesson 18."""

from enum import StrEnum

from pydantic import BaseModel, Field


class TerminationKind(StrEnum):
    JUDGE_PASSED = "judge_passed"
    JUDGE_FAILED = "judge_failed"
    STEP_LIMIT = "step_limit"
    FAILURE_LIMIT = "failure_limit"


class RunTermination(BaseModel):
    kind: TerminationKind
    message: str = Field(min_length=1)
