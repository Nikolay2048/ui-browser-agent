"""BrowserAction schema after lesson 5 structured-output correction."""

from enum import StrEnum

from pydantic import BaseModel, model_validator


class BrowserActionType(StrEnum):
    CLICK = "click"
    FILL = "fill"
    PRESS = "press"
    ASSERT_TEXT = "assert_text"
    FINISH = "finish"


class BrowserAction(BaseModel):
    action: BrowserActionType
    target: str | None
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
        requires_value = {BrowserActionType.FILL, BrowserActionType.PRESS}
        if self.action in requires_target and self.target is None:
            raise ValueError(f"{self.action} requires target")
        if self.action in requires_value and self.value is None:
            raise ValueError(f"{self.action} requires value")
        return self
