from fastapi import APIRouter, Depends, Query

from app.constants.roles import UserRole
from app.core.schema import AppResponse
from app.dependencies.auth import CurrentUser, ValidateRole
from app.dependencies.db_session import DbSession
from app.dto.journal import GetJournalDto
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
