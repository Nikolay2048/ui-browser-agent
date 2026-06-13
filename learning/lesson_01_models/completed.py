"""Completed domain models after lesson 1."""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, model_validator


class TestCase(BaseModel):
    id: str = Field(pattern=r"^[A-Za-z0-9_-]+$")
    name: str
    start_url: str
    goal: str
    test_data: dict[str, Any] = Field(default_factory=dict)
    expected: list[str] = Field(default_factory=list)
    max_steps: int = Field(default=20, ge=1, le=100)


class BrowserActionType(StrEnum):
    CLICK = "click"
    FILL = "fill"
    PRESS = "press"
    ASSERT_TEXT = "assert_text"
    FINISH = "finish"


class BrowserAction(BaseModel):
    action: BrowserActionType
    target: str | None = None
    value: str | None = None
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
    success: bool
    url_before: str
    url_after: str
    error: str | None = None
    screenshot_path: str | None = None
