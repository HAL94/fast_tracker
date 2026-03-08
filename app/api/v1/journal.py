from typing import List

from fastapi import APIRouter, Depends, Query

from app.constants.roles import UserRole
from app.core.schema import AppResponse
from app.dependencies.auth import CurrentUser, ValidateRole
from app.dependencies.db_session import DbSession
from app.domain.worklog import WorklogBase
from app.dto.journal import GetJournalDto, ReportingPeriodQueryDto, TaskBatchDto
from app.services.journal import JournalService

journal_router = APIRouter(prefix="/journal", tags=["Journal"])


@journal_router.get("/", dependencies=[Depends(ValidateRole(UserRole.USER))])
async def get_journal(session: DbSession, user: CurrentUser, query: GetJournalDto = Query(...)):
    """
    Represents the matrix the employee will see in an excel-sheet style for a given monthly period, this
    is still experimental, so response should include necessary data for the employee to perform their
    intended operation. Response model are yet to be fully determined.
    """
    journal_service = JournalService(session)
    result = await journal_service.get_journal(query, user.id)
    return AppResponse(data=result)

@journal_router.get("/period", dependencies=[Depends(ValidateRole(UserRole.USER))])
async def get_period(session: DbSession, user: CurrentUser, query: ReportingPeriodQueryDto = Query(...)):
    """
    Given the month and year values, a reporting period is retrieved. If not exists will be created.
    """
    journal_service = JournalService(session)
    period = await journal_service.get_or_create_period(query)
    return AppResponse(data=period)

@journal_router.post(
    "/worklog-batch",
    dependencies=[Depends(ValidateRole(UserRole.USER))],
    response_model=AppResponse[List[WorklogBase]],
)
async def worklog_batch(session: DbSession, user: CurrentUser, data: TaskBatchDto) -> AppResponse[List[WorklogBase]]:
    """Add/update/delete worklog batch for multiple activities, core endpoint for employee tracking their hours"""
    journal_service = JournalService(session)
    worklogs = await journal_service.batch_worklog(data, user.id)
    return AppResponse(data=worklogs)
