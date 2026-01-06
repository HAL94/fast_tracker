from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import Field

from app.core.schema import BaseModel


class CreateUserActivityDto(BaseModel):
    user_id: UUID
    activity_id: UUID


class CreateActivityDto(BaseModel):
    title: str
    code: str
    expected_hours: int
    activity_type_id: UUID


class CreateActivityTaskDto(BaseModel):
    title: str
    activity_id: Optional[UUID] = None


class CreateWorklogDto(BaseModel):
    activity_task_id: Optional[UUID] = Field(default=None)
    date: datetime = Field(default=datetime.now())
    duration: int = Field(ge=1, le=8)
