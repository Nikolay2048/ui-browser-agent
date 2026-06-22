"""Domain model added in lesson 11."""

from pydantic import BaseModel, Field

from browser_agent.domain import ActionResult, BrowserAction


class ExecutionStep(BaseModel):
    step_number: int = Field(ge=1)
    page_snapshot: str
    action: BrowserAction
    result: ActionResult
