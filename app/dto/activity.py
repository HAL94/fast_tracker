from datetime import date as Date
from typing import List, Optional, Self
from uuid import UUID

from pydantic import Field, model_validator

from app.core.exceptions import UnprocessableInputException
from app.core.schema import BaseModel


class CreateUserActivityDto(BaseModel):
    user_id: UUID
    activity_id: UUID


class CreateActivityDto(BaseModel):
    title: str
    code: str
    activity_type_id: UUID


class CreateActivityTaskDto(BaseModel):
    title: str
    activity_id: Optional[UUID] = None


class UpsertActivityTask(BaseModel):
    # Will update task if exists, else create new
    id: Optional[UUID] = Field(default=None, description="Unique identifier of the activity task.")
    title: str = Field(description="Title of the activity task", min_length=3)
    activity_id: UUID = Field(description="Activity which the task belongs to.")
    month: int = Field(description="Month of the task")
    year: int = Field(description="Year of the task")
    worklogs: List["WorklogDto"] = Field(description="Worklogs associated with the activity task.", default=[])

    @model_validator(mode="after")
    def validate_worklogs_month_year(self) -> Self:
        for worklog_item in self.worklogs:
            worklog_date = worklog_item.date
            worklog_month = worklog_date.month
            worklog_year = worklog_date.year

            if self.month != worklog_month or self.year != worklog_year:
                raise UnprocessableInputException(
                    f"Worklogs contain a date at {worklog_item.date} that is not within ({self.month:02d}-{self.year})"
                )
        return self


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
