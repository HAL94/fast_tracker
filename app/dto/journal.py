from datetime import date as Date
from typing import List, Optional
from uuid import UUID

from pydantic import Field

from app.core.schema import BaseModel


class GetJournalDto(BaseModel):
    start_date: Date
    end_date: Date


class JournalActivityType(BaseModel):
    id: Optional[UUID] = Field(exclude=True)
    title: str


class JournalActivity(BaseModel):
    activity_type_id: UUID = Field(exclude=True)
    title: str
    code: str
    expected_hours_monthly: int
    activity_type: JournalActivityType
    tasks: Optional[List["JournalActivityTask"]] = Field(default=[])


class JournalActivityWorklogs(BaseModel):
    id: Optional[UUID] = Field(default=None)
    date: Date
    duration: Optional[float] = None


class JournalActivityTask(BaseModel):
    id: Optional[UUID] = Field(default=None)
    title: str
    activity_id: UUID
    worklogs: Optional[List[JournalActivityWorklogs]] = Field(default=[])


class UserJournalDto(BaseModel):
    project_assignments: List[JournalActivity]
    tasks: List[JournalActivityTask]
