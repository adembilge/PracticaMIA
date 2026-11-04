"""Strict API schemas for synthetic demo cases."""
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


Answer = Literal["yes", "no", "unsure"]


class CreateCase(BaseModel):
    model_config = ConfigDict(extra="forbid")
    procedure: Literal["milan_residence_change"] = "milan_residence_change"


class ScopeUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    answers: list[Answer] = Field(min_length=1, max_length=5)


class CaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    procedure: str
    status: str
    scope_answers: list[Answer]
    created_at: datetime
    updated_at: datetime
