"""Typed browser targets completed in lesson 16."""

from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


class BrowserTargetStrategy(StrEnum):
    ROLE = "role"
    LABEL = "label"
    TEXT = "text"
    CSS = "css"


class BrowserTarget(BaseModel):
    strategy: BrowserTargetStrategy
    value: str = Field(min_length=1)
    name: str | None = None

    @model_validator(mode="after")
    def validate_target(self):
        if self.strategy == BrowserTargetStrategy.ROLE and not self.name:
            raise ValueError("strategy=role requires name")
        if self.strategy != BrowserTargetStrategy.ROLE and self.name is not None:
            raise ValueError("name is allowed only for strategy=role")
        if (
            self.strategy == BrowserTargetStrategy.TEXT
            and len(self.value) >= 2
            and self.value[0] == self.value[-1]
            and self.value[0] in {"'", '"'}
        ):
            raise ValueError("text value must not be wrapped in quotes")
        return self

    def __str__(self) -> str:
        if self.strategy == BrowserTargetStrategy.ROLE:
            return f'role={self.value}[name="{self.name}"]'
        return f"{self.strategy.value}={self.value}"
