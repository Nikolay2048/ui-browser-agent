from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class TestStep(BaseModel):
    step_number: int = 0
    step: str
    expected: str


class TestCase(BaseModel):
    id: str
    name: str
    description: str
    start_url: str
    preconditions: list[str] = []
    steps: list[TestStep]
    tags: list[str] = []
    severity: Literal["critical", "high", "medium", "low"] = "medium"


class PlannedAction(BaseModel):
    step_number: int
    description: str
    tool_name: str
    tool_args: dict
    expected_result: str


class ExecutionPlan(BaseModel):
    test_case_id: str
    planned_actions: list[PlannedAction]
    notes: str = ""
    reasoning: str = ""


class StepResult(BaseModel):
    step_number: int
    description: str
    status: Literal["passed", "failed", "skipped", "broken"]
    actual_result: str
    expected_result: str
    screenshot_path: str | None = None
    error_message: str | None = None
    duration_ms: int = 0
    tool_calls: list[str] = []


class BugReport(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    title: str
    severity: Literal["critical", "high", "medium", "low"]
    type: str = "Functional"
    description: str
    steps_to_reproduce: list[str]
    expected_result: str
    actual_result: str
    screenshots: list[str] = []
    test_case_id: str
    test_case_name: str = ""
    step_number: int = 0
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class ClarificationItem(BaseModel):
    step_number: int
    question: str
    suggestion: str


class ClarificationRequest(BaseModel):
    needs_clarification: bool
    items: list[ClarificationItem] = []
    general_suggestions: list[str] = []
