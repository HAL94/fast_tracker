from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.dto.activity import TaskBatchDto
from app.services.journal import JournalService

from . import WorklogFactoryFn


class TestJournal:
    @pytest.mark.asyncio
    async def test_add_batch_worklog(
        self, worklog_batch: TaskBatchDto, jason_user_id: UUID, async_session: AsyncSession
    ):
        """Tests creating a task in the worklog grid for a user with given id"""
        journal_service = JournalService(session=async_session)
        result = await journal_service.batch_worklog(data=worklog_batch, user_id=jason_user_id)

        assert result is not None
        first_item = result[0]
        assert first_item is not None
        # ensure owner is the same user
        assert first_item.user_id == jason_user_id
        # ensure that an activity_task_id is generated..
        assert first_item.activity_task_id is not None

    @pytest.mark.asyncio
    async def test_update_batch_worklog(self, async_session: AsyncSession, worklog_batch_factory: WorklogFactoryFn):
        worklog_batch_factory()
