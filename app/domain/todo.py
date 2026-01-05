from typing import ClassVar, Optional
from uuid import UUID

from pydantic import Field
from sqlalchemy.orm import selectinload

from app.core.database import BaseModelDatabaseMixin
from app.models import Subtask as SubtaskModel
from app.models import Todo as TodoModel


class TodoBase(BaseModelDatabaseMixin[TodoModel]):
    model: ClassVar[type[TodoModel]] = TodoModel

    id: Optional[UUID] = Field(default=None)
    title: str
    user_id: UUID


class TodoWithTasks(TodoBase):
    @classmethod
    def relations(cls):
        return [selectinload(cls.model.subtasks)]

    subtasks: Optional[list["SubtaskBase"]] = Field(default=[])


class SubtaskBase(BaseModelDatabaseMixin):
    model: ClassVar[type[SubtaskModel]] = SubtaskModel

    id: Optional[UUID] = None
    title: Optional[str] = None
    priority: int
