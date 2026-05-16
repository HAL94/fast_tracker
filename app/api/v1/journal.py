from typing import List

from fastapi import APIRouter, Depends, Query

from app.constants.roles import UserRole
from app.core.schema import AppResponse
from app.dependencies.auth import CurrentUser, ValidateRole
from app.dependencies.db_session import DbSession
from app.domain.worklog import WorklogBase
from app.dto.journal import GetJournalDto, JournalActivity, TaskBatchDto
from app.services.journal.service import JournalService

journal_router = APIRouter(prefix="/journal", tags=["Journal"])


@journal_router.get(
    "/", dependencies=[Depends(ValidateRole(UserRole.USER))], response_model=AppResponse[List[JournalActivity]]
)
async def get_journal(
    session: DbSession, user: CurrentUser, query: GetJournalDto = Query(...)
) -> AppResponse[List[JournalActivity]]:
    """
    Represents the matrix the employee will see in an excel-sheet style for a given monthly period, this
    is still experimental, so response should include necessary data for the employee to perform their
    intended operation. Response model are yet to be fully determined.
    """
    journal_service = JournalService(session)
    result = await journal_service.get_journal(query, user.id, user.tenant_id)
    return AppResponse(data=result)


@journal_router.post(
    "/worklog-batch", dependencies=[Depends(ValidateRole(UserRole.USER))], response_model=AppResponse[List[WorklogBase]]
)
async def worklog_batch(session: DbSession, user: CurrentUser, data: TaskBatchDto) -> AppResponse[List[WorklogBase]]:
    """Add/update/delete worklog batch for multiple activities, core endpoint for employee tracking their hours"""
    journal_service = JournalService(session)
    worklogs = await journal_service.batch_worklog(data, user.id, user.tenant_id)
    return AppResponse(data=worklogs)
