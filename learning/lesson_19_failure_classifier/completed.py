"""Failure classification contract completed in lesson 19."""

from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


class FailureCategory(StrEnum):
    PRODUCT_BUG = "product_bug"
    AGENT_ERROR = "agent_error"
    AUTOMATION_ERROR = "automation_error"
    ENVIRONMENT_ERROR = "environment_error"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class FailureClassification(BaseModel):
    category: FailureCategory
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str = Field(min_length=1)
    evidence: list[str] = Field(min_length=1)
    should_create_bug: bool

    @model_validator(mode="after")
    def validate_bug_recommendation(self):
        if (
            self.should_create_bug
            and self.category != FailureCategory.PRODUCT_BUG
        ):
            raise ValueError("Only product_bug can recommend creating a bug")
        return self
