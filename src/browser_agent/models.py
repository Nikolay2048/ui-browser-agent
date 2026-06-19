"""Domain contracts for the browser testing agent.

Lesson 1 is archived in learning/lesson_01_models/README.md.
Do not add LangGraph, LangChain, or Playwright code to this module.
"""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, model_validator


class TestCase(BaseModel):
    """Input test scenario."""

    id: str = Field(pattern=r"^[A-Za-z0-9_-]+$")
    name: str
    start_url: str
    goal: str
    test_data: dict[str, Any] = Field(default_factory=dict)
    expected: list[str] = Field(default_factory=list)
    max_steps: int = Field(default=20, ge=1, le=100)
    max_failures: int = Field(default=2, ge=1, le=20)


class BrowserActionType(StrEnum):
    CLICK = "click"
    FILL = "fill"
    PRESS = "press"
    ASSERT_TEXT = "assert_text"
    FINISH = "finish"


class BrowserTargetStrategy(StrEnum):
    ROLE = "role"
    LABEL = "label"
    TEXT = "text"
    CSS = "css"


class BrowserTarget(BaseModel):
    """Structured browser target.
    learning/lesson_16_typed_targets/README.md.
    """

    strategy: BrowserTargetStrategy
    value: str = Field(min_length=1)
    name: str | None = None

    @model_validator(mode="after")
    def validate_target(self) -> "BrowserTarget":
        if self.strategy is BrowserTargetStrategy.ROLE:
            if not self.name:
                raise ValueError("strategy=ROLE requires name")
        elif self.name is not None:
            raise ValueError("name is allowed only for strategy=ROLE")

        if (
                self.strategy is BrowserTargetStrategy.TEXT
                and len(self.value) >= 2
                and self.value[0] == self.value[-1]
                and self.value[0] in {"'", '"'}
        ):
            raise ValueError(
                "TEXT value must not start and end with quotes"
            )

        return self

    def __str__(self) -> str:
        match self.strategy:
            case BrowserTargetStrategy.ROLE:
                return f'role={self.value}[name="{self.name}"]'
            case _:
                return f"{self.strategy.value}={self.value}"


class BrowserAction(BaseModel):
    """Exactly one action proposed by the planner."""

    action: BrowserActionType
    target: BrowserTarget | None
    value: str | None
    reason: str

    @model_validator(mode="after")
    def validate_action(self):
        requires_target = {
            BrowserActionType.CLICK,
            BrowserActionType.FILL,
            BrowserActionType.PRESS,
            BrowserActionType.ASSERT_TEXT,
        }

        requires_value = {
            BrowserActionType.FILL,
            BrowserActionType.PRESS,
        }

        if self.action in requires_target and self.target is None:
            raise ValueError(f"{self.action} requires target")

        if self.action in requires_value and self.value is None:
            raise ValueError(f"{self.action} requires value")

        return self


class ActionResult(BaseModel):
    """Deterministic result of executing an action."""

    success: bool
    url_before: str
    url_after: str
    error: str | None = None
    screenshot_path: str | None = None


class ExecutionStep(BaseModel):
    """One complete observe-plan-execute record."""

    step_number: int = Field(ge=1)
    page_snapshot: str
    action: BrowserAction
    result: ActionResult


class ExpectedResultCheck(BaseModel):
    """Judge evidence for one expected result."""
    expected: str = Field(min_length=1)
    passed: bool
    evidence: str = Field(min_length=1)


class JudgeVerdict(BaseModel):
    """Independent test verdict produced by the Judge."""

    passed: bool
    checks: list[ExpectedResultCheck] = Field(min_length=1)
    summary: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_verdict(self):
        checks_passed = all(check.passed for check in self.checks)

        if self.passed != checks_passed:
            raise ValueError("passed must be true only when every check passed")

        return self


class TerminationKind(StrEnum):
    JUDGE_PASSED = "judge_passed"
    JUDGE_FAILED = "judge_failed"
    STEP_LIMIT = "step_limit"
    FAILURE_LIMIT = "failure_limit"


class RunTermination(BaseModel):
    """Why the graph stopped."""

    kind: TerminationKind
    message: str = Field(min_length=1)
