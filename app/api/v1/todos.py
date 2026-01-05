from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.core.schema import AppResponse
from app.dependencies.auth import CurrentUser, get_current_active_user
from app.dependencies.db_session import DbSession
from app.domain.todo import TodoWithTasks
from app.dto.todo import TodoCreate
from app.services.todo import TodoService

todos_router = APIRouter(prefix="/todos", tags=["Todos"], dependencies=[Depends(get_current_active_user)])


@todos_router.get("/", response_model=AppResponse[List[TodoWithTasks]])
async def get_toods(session: DbSession, user: CurrentUser) -> AppResponse[List[TodoWithTasks]]:
    service = TodoService(session=session)
    todos = await service.get_todos(user_id=user.id)
    return AppResponse(data=todos)


@todos_router.get("/{todo_id}", response_model=AppResponse[TodoWithTasks])
async def get_a_todo(todo_id: UUID, session: DbSession, user: CurrentUser) -> AppResponse[TodoWithTasks]:
    service = TodoService(session=session)
    todo = await service.get_todo(todo_id, user_id=user.id)
    return AppResponse(data=todo)


@todos_router.post("/", status_code=status.HTTP_201_CREATED, response_model=AppResponse[TodoWithTasks])
async def create_todo(
    todo: TodoCreate,
    session: DbSession,
    user: CurrentUser,
) -> AppResponse[TodoWithTasks]:
    service = TodoService(session=session)
    todos = await service.create_todo(todo, user.id)
    return AppResponse(data=todos)
