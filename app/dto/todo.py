from typing import Optional

from pydantic import Field

from app.core.schema import BaseModel


class TodoCreate(BaseModel):
    title: str
    subtasks: Optional[list["SubtaskCreate"]] = Field(default=[])


class SubtaskCreate(BaseModel):
    title: Optional[str] = None
    priority: Optional[int] = Field(default=0)
