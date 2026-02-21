from datetime import date as Date
from typing import List, Optional
from uuid import UUID

from pydantic import Field

from app.core.schema import BaseModel
from app.models import Activity


class GetJournalDto(BaseModel):
    start_date: Date
    end_date: Date


class JournalActivityType(BaseModel):
    id: Optional[UUID] = Field(exclude=True)
    title: str


class JournalActivity(BaseModel):
    id: UUID
    title: str
    code: str
    activity_type: str
    tasks: Optional[List["JournalActivityTask"]] = Field(default=[])

    @classmethod
    def from_activity_model(cls, activity: Activity):
        return cls(
            id=activity.id,
            title=activity.title,
            code=activity.code,
            activity_type=activity.activity_type.title,
            tasks=[JournalActivityTask.model_validate(item, from_attributes=True) for item in activity.tasks],
        )


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
