from datetime import date as Date
from typing import List, Optional
from uuid import UUID

from pydantic import Field, model_validator

from app.core.exceptions import UnprocessableInputException
from app.core.schema import BaseModel
from app.models import Activity


# ======================
# Get reporting period for journal
# ======================
class ReportingPeriodQueryDto(BaseModel):
    month: int
    year: int


# ======================
# Grid fetch DTOs
# ======================
class GetJournalDto(BaseModel):
    period_id: UUID


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
    user_id: UUID
    worklogs: Optional[List[JournalActivityWorklogs]] = Field(default=[])


class UserJournalDto(BaseModel):
    project_assignments: List[JournalActivity]
    tasks: List[JournalActivityTask]


# ======================
# Grid update DTOs
# ======================
class UpsertActivityTask(BaseModel):
    # Will update task if exists, else create new
    id: Optional[UUID] = Field(default=None, description="Unique identifier of the activity task.")
    title: str = Field(description="Title of the activity task", min_length=3)
    activity_id: UUID = Field(description="Activity which the task belongs to.")
    worklogs: List["WorklogDto"] = Field(description="Worklogs associated with the activity task.", default=[])


class WorklogDto(BaseModel):
    # A null id indicates a creation
    id: Optional[UUID] = Field(default=None, description="Unique identifier of the worklog.")
    date: Date = Field(description="Date of the worklog represents a cell for a day")
    duration: Optional[float] = Field(default=None, description="Duration registered for the day for the task")
    task_id: Optional[UUID] = Field(default=None, description="The task which the worklog belongs to.")

    @model_validator(mode="after")
    def validate_data(self):
        if self.duration is None and self.id is None:
            raise UnprocessableInputException(
                message=f"Unprocessable entity, both 'duration' and 'id' fields are not provided, \
                    in object: {str(self)}"
            )
        return self


class TaskBatchDto(BaseModel):
    tasks: List[UpsertActivityTask] = Field(default=[])
    deletions: Optional[List[UUID]] = Field(default=[])
