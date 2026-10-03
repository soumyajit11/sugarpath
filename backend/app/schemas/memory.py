from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

MemoryType = Literal["routine", "preference", "patient_fact", "system_observation"]
MemorySource = Literal["user_explicit", "user_confirmed", "system_observation"]


class MemoryCreate(BaseModel):
    memory_type: MemoryType
    content: str = Field(min_length=3, max_length=500)
    source: MemorySource

    @field_validator("content")
    @classmethod
    def clean_content(cls, value: str) -> str:
        return " ".join(value.strip().split())


class MemoryUpdate(BaseModel):
    memory_type: MemoryType | None = None
    content: str | None = Field(default=None, min_length=3, max_length=500)
    source: MemorySource | None = None

    @field_validator("content")
    @classmethod
    def clean_content(cls, value: str | None) -> str | None:
        return " ".join(value.strip().split()) if value else value


class MemoryOut(BaseModel):
    id: int
    memory_type: MemoryType
    content: str
    source: MemorySource
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}
