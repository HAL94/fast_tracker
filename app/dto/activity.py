from datetime import date as Date
from typing import List, Optional
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
    expected_hours_monthly: int
    activity_type_id: UUID


class CreateActivityTaskDto(BaseModel):
    title: str
    activity_id: Optional[UUID] = None


class WorklogDto(BaseModel):
    id: Optional[UUID] = Field(default=None)
    date: Date
    duration: Optional[float] = Field(default=None)
    task_id: UUID

    @model_validator(mode="after")
    def validate_data(self):
        if self.duration is None and self.id is None:
            raise UnprocessableInputException(
                message=f"422 Unprocessable entity, both 'duration' and 'id' fields are not provided, \
                    in object: {str(self)}"
            )
        return self


class WorklogBatchDto(BaseModel):
    worklogs: List[WorklogDto] = []
