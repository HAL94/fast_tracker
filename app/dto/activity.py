from typing import Optional
from uuid import UUID

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
