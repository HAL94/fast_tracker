import logging
from datetime import date as Date
from datetime import datetime
from typing import Any
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, NotFoundException, UnauthorizedException
from app.domain.activity import ActivityBase, ActivityUserBase
from app.domain.activity_task import ActivityTaskBase
from app.domain.activity_type import ActivityTypeBase
from app.domain.worklog import WorklogBase
from app.dto.journal import TaskBatchDto, UpsertActivityTask, WorklogDto
from app.services.journal import JournalService

from . import TaskBatchFactoryFn, TaskFactoryFn, WorklogFactoryFn

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class TestJournal:
    @pytest.mark.asyncio
    async def test_add_batch_worklog(
        self,
        user_id: UUID,
        async_session: AsyncSession,
        task_batch_factory: TaskBatchFactoryFn,
        random_task: dict[str, Any],
    ):
        """Tests creating a task in the worklog grid for a user with given id.
        Currently does not include adding worklogs"""

        tasks = [
            UpsertActivityTask(
                title=random_task.get("title"),
                month=random_task.get("month"),
                year=random_task.get("year"),
                activity_id=random_task.get("activity_id"),
                user_id=user_id,
                worklogs=[],
            )
        ]
        task_batch_dto = task_batch_factory(deletions=[], tasks=tasks)

        journal_service = JournalService(session=async_session)
        result = await journal_service.batch_worklog(data=task_batch_dto, user_id=user_id)

        assert result is not None
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_update_batch_worklog(
        self,
        user_id: UUID,
        async_session: AsyncSession,
        task_batch_factory: TaskBatchFactoryFn,
        persisted_task: ActivityTaskBase,
        worklog_factory: WorklogFactoryFn,
    ):
        """Tests updating an already existing task with worklogs in the worklog grid for a user with given id"""
        today = datetime.now()
        worklogs = worklog_factory(size=1, year=today.year, month=today.month)
        task = UpsertActivityTask(
            title=persisted_task.title,
            month=persisted_task.month,
            year=persisted_task.year,
            activity_id=persisted_task.activity_id,
            user_id=user_id,
            worklogs=worklogs,
        )
        task_batch_dto = task_batch_factory(
            deletions=[],
            tasks=[task],
        )

        journal_service = JournalService(session=async_session)
        result = await journal_service.batch_worklog(data=task_batch_dto, user_id=user_id)

        assert result is not None
        first_item = result[0]
        assert first_item is not None
        # ensure owner is the same user
        assert first_item.user_id == user_id
        # ensure that an activity_task_id is generated and equal to the one passed..
        assert first_item.activity_task_id == persisted_task.id

    @pytest.mark.asyncio
    async def test_update_and_delete_worklogs(
        self,
        user_id: UUID,
        async_session: AsyncSession,
        task_batch_factory: TaskBatchFactoryFn,
        persisted_task: ActivityTaskBase,
        sample_activity: ActivityBase,
        task_factory: TaskFactoryFn,
    ):
        """
        Manual Task Purge Test:
        - The Scenario: A user deletes an entire row (Task) from their UI.
        - The Test: Pass the task.id into the data.deletions list while simultaneously sending other updates.
        - The Goal: Ensure the ActivityTaskBase.delete_many correctly triggers the database ondelete="CASCADE",
            wiping the associated worklogs.
        """

        # Victim worklog for to test it gets deleted
        await WorklogBase.upsert_one(
            async_session,
            WorklogBase(date=datetime.now().date(), duration=1.0, activity_task_id=persisted_task.id, user_id=user_id),
            commit=False,
        )
        await async_session.flush()
        task_size = 1
        worklog_size = 2
        today = datetime.now()
        tasks = task_factory(sample_activity.id, task_size, worklog_size, today.year, today.month)
        deletions = [persisted_task.id]

        task_batch_dto = task_batch_factory(deletions=deletions, tasks=tasks)

        journal_service = JournalService(session=async_session)
        result = await journal_service.batch_worklog(task_batch_dto, user_id)

        deleted_task = await ActivityTaskBase.get_one(
            async_session, persisted_task.id, field=ActivityTaskBase.model.id, raise_not_found=False
        )

        worklogs_for_deleted_task = await WorklogBase.get_all(
            async_session, where_clause=[WorklogBase.model.activity_task_id == persisted_task.id]
        )

        assert result is not None
        assert deleted_task is None
        assert len(worklogs_for_deleted_task) == 0
        assert len(result) == worklog_size
        first_item = result[0]
        assert first_item.activity_task_id != persisted_task.id

    @pytest.mark.asyncio
    async def test_partial_batch_worklog_update(
        self,
        user_id: UUID,
        async_session: AsyncSession,
        task_batch_factory: TaskBatchFactoryFn,
        random_persisted_task: ActivityTaskBase,
    ):
        """
        - The Scenario: A task has worklogs on Monday (4h) and Wednesday (2h). The user only edits Monday to (5h)
        and sends a batch where the Wednesday worklog is missing from the DTO.
        - The Test: Send a TaskDto containing only the Monday worklog.
        - The Goal: Verify that Wednesday's 2h stay in the database untouched.
        This confirms loop-based upsert only affects what is explicitly provided.
        """
        monday = Date(2026, 3, 2)
        wedensday = Date(2026, 3, 4)

        monday_worklog = await WorklogBase.upsert_one(
            async_session,
            WorklogBase(date=monday, duration=4, activity_task_id=random_persisted_task.id, user_id=user_id),
            commit=False,
        )

        wedensday_worklog = await WorklogBase.upsert_one(
            async_session,
            WorklogBase(date=wedensday, duration=2, activity_task_id=random_persisted_task.id, user_id=user_id),
            commit=False,
        )

        await async_session.flush()
        monday_worklog_dto = WorklogDto(id=monday_worklog.id, date=monday_worklog.date, duration=2)

        tasks = UpsertActivityTask(
            id=random_persisted_task.id,
            activity_id=random_persisted_task.activity_id,
            title=random_persisted_task.title,
            year=random_persisted_task.year,
            month=random_persisted_task.month,
            worklogs=[monday_worklog_dto],
        )

        task_batch_dto = task_batch_factory(deletions=[], tasks=[tasks])

        journal_service = JournalService(session=async_session)

        result = await journal_service.batch_worklog(task_batch_dto, user_id)

        assert len(result) != 0
        first_item = result[0]
        assert first_item.duration == monday_worklog_dto.duration
        assert first_item.activity_task_id == random_persisted_task.id

        worklog_wednesday_fetched = await WorklogBase.get_one(
            async_session, wedensday_worklog.id, field=WorklogBase.model.id
        )

        # ensure wedensday is not touched
        assert worklog_wednesday_fetched.duration == wedensday_worklog.duration
        assert worklog_wednesday_fetched.id == wedensday_worklog.id

        # Verify total count for this task is still 2
        total_worklogs = await WorklogBase.get_all(
            async_session, where_clause=[WorklogBase.model.activity_task_id == random_persisted_task.id]
        )
        assert len(total_worklogs) == 2

    @pytest.mark.asyncio
    async def test_add_task_by_user(
        self,
        user_id: UUID,
        async_session: AsyncSession,
        sample_activity: ActivityBase,
        task_factory: TaskFactoryFn,
        task_batch_factory: TaskBatchFactoryFn,
    ):
        """
        Goal: Creates a random task and then attempts to add it.
        Test: check if user owns the provided task id if any (checked by service), if fails, will throw \
            an unthorized error.
        Outcome: Since this is a new task, should succeed to add it (happy case)
        """
        journal_service = JournalService(async_session)
        task_size = 1
        worklog_size = 1
        tasks = task_factory(sample_activity.id, task_size, worklog_size)
        task_batch_dto = task_batch_factory(
            deletions=[],
            tasks=tasks,
        )
        result = await journal_service.batch_worklog(data=task_batch_dto, user_id=user_id)
        assert result is not None
        assert len(result) == worklog_size

    @pytest.mark.asyncio
    async def test_activity_not_linked_to_user(
        self,
        tester_id: UUID,
        async_session: AsyncSession,
        random_persisted_task: ActivityTaskBase,
        worklog_factory: WorklogFactoryFn,
        task_batch_factory: TaskBatchFactoryFn,
    ):
        """
        Goal: Creates a worklog for an already persisted task but under an activity not linked to the user.
              User will attempt to update task.
        Test: check if user is linked to the activity if fails, will throw \
            an unthorized error.
        Outcome: Since the activity is not owned by the current user, should fail with a Unauthorized exception
        """
        journal_service = JournalService(async_session)
        worklog_size = 1

        worklogs = worklog_factory(worklog_size)
        task = UpsertActivityTask(
            id=random_persisted_task.id,
            title=random_persisted_task.title,
            activity_id=random_persisted_task.activity_id,
            month=random_persisted_task.month,
            year=random_persisted_task.year,
            worklogs=worklogs,
        )
        task_batch_dto = task_batch_factory(
            deletions=[],
            tasks=[task],
        )
        with pytest.raises(UnauthorizedException) as excinfo:
            await journal_service.batch_worklog(data=task_batch_dto, user_id=tester_id)

        assert "Not allowed to access activity resource" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_task_not_owned_by_user(
        self,
        tester_id: UUID,
        async_session: AsyncSession,
        random_persisted_task: ActivityTaskBase,
        worklog_factory: WorklogFactoryFn,
        task_batch_factory: TaskBatchFactoryFn,
    ):
        """
        Goal: Test if current user owns the resource (Task).
        Outcome: The user should not be able update the task since they do not own it.
        """
        # make a relationship between tester id and activity
        await ActivityUserBase.upsert_one(
            async_session,
            ActivityUserBase(user_id=tester_id, activity_id=random_persisted_task.activity_id),
        )
        worklog_size = 1
        worklogs = worklog_factory(worklog_size)
        task = UpsertActivityTask(
            id=random_persisted_task.id,
            title=random_persisted_task.title,
            activity_id=random_persisted_task.activity_id,
            month=random_persisted_task.month,
            year=random_persisted_task.year,
            worklogs=worklogs,
        )
        task_batch_dto = task_batch_factory(
            deletions=[],
            tasks=[task],
        )
        journal_service = JournalService(async_session)
        with pytest.raises(UnauthorizedException) as excinfo:
            await journal_service.batch_worklog(data=task_batch_dto, user_id=tester_id)

        assert "Not allowed to access task resource" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_worklog_not_owned_by_user(
        self,
        tester_id: UUID,
        async_session: AsyncSession,
        random_persisted_task: ActivityTaskBase,
        random_task: dict[str, Any],
        worklog_factory: WorklogFactoryFn,
        task_batch_factory: TaskBatchFactoryFn,
    ):
        """
        Goal: Test if current user owns the resource (Task).
        Outcome: The user should not be able update the task since they do not own it.
        """
        # make a relationship between tester id and activity
        await ActivityUserBase.upsert_one(
            async_session,
            ActivityUserBase(
                user_id=tester_id, activity_id=random_persisted_task.activity_id, updated_at=datetime.now()
            ),
            ["user_id", "activity_id"],
            commit=False,
        )
        worklog_size = 1
        worklogs = worklog_factory(worklog_size)
        worklog_dto: WorklogDto = worklogs[0]
        created_worklog = await WorklogBase.create(
            async_session,
            WorklogBase(
                date=worklog_dto.date,
                duration=worklog_dto.duration,
                activity_task_id=random_persisted_task.id,
                user_id=random_persisted_task.user_id,
            ),
            commit=False,
        )
        task = UpsertActivityTask(
            title=random_task.get("title"),
            activity_id=random_task.get("activity_id"),
            month=random_task.get("month"),
            year=random_task.get("year"),
            worklogs=[WorklogDto(id=created_worklog.id, date=created_worklog.date, duration=created_worklog.duration)],
        )
        task_batch_dto = task_batch_factory(
            deletions=[],
            tasks=[task],
        )
        journal_service = JournalService(async_session)
        with pytest.raises(UnauthorizedException) as excinfo:
            await journal_service.batch_worklog(data=task_batch_dto, user_id=tester_id)

        assert "Not allowed to access worklog resource" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_duration_exceed_8_hours(
        self,
        user_id: UUID,
        async_session: AsyncSession,
        random_task: dict[str, Any],
    ):
        """
        Goal: Validate the 8-hour rule for a given date across all tasks registred for that date.
        Test: check if logic for the sum aggregate across the date exceeds 8 hours. If fails, will throw \
            an error.
        Outcome: Should exceed 8-hour rule and throw a Bad Request error
        """
        sunday = datetime(2026, 2, 22)

        upserted_task = await ActivityTaskBase.upsert_one(
            async_session,
            ActivityTaskBase(
                id=random_task.get("id"),
                title=random_task.get("title"),
                activity_id=random_task.get("activity_id"),
                user_id=user_id,
                month=sunday.month,
                year=sunday.year,
            ),
            ["title", "activity_id", "month", "year"],
            commit=False,
        )
        await async_session.flush()
        worklogs: list[WorklogDto] = [
            WorklogDto(date=Date(year=sunday.year, month=sunday.month, day=sunday.day), duration=4)
        ]

        task_dto = UpsertActivityTask(
            id=upserted_task.id,
            title=upserted_task.title,
            activity_id=upserted_task.activity_id,
            month=sunday.month,
            year=sunday.year,
            worklogs=worklogs,
        )
        journal_service = JournalService(async_session)
        result = await journal_service.batch_worklog(TaskBatchDto(deletions=[], tasks=[task_dto]), user_id)

        assert result is not None
        first_item = result[0]
        assert first_item.duration == 4

        upserted_task = await ActivityTaskBase.upsert_one(
            async_session,
            ActivityTaskBase(
                id=random_task.get("id"),
                title="Conflicting Task",
                activity_id=random_task.get("activity_id"),
                user_id=user_id,
                month=sunday.month,
                year=sunday.year,
            ),
            ["title", "activity_id", "month", "year"],
            commit=False,
        )
        await async_session.flush()
        worklogs: list[WorklogDto] = [
            WorklogDto(date=Date(year=sunday.year, month=sunday.month, day=sunday.day), duration=5)
        ]

        task_dto = UpsertActivityTask(
            id=upserted_task.id,
            title=upserted_task.title,
            activity_id=upserted_task.activity_id,
            month=sunday.month,
            year=sunday.year,
            worklogs=worklogs,
        )

        with pytest.raises(BadRequestException) as excinfo:
            result = await journal_service.batch_worklog(TaskBatchDto(deletions=[], tasks=[task_dto]), user_id)
            logger.info(f"Result of violated call: {result}")
        assert "Daily limit exceeded" in str(excinfo.value)

        await async_session.rollback()
        # Verify that the 5-hour worklog was ROLLED BACK and does not exist in the DB.

        final_worklogs = await WorklogBase.get_all(
            async_session,
            where_clause=[
                WorklogBase.model.user_id == user_id,
                WorklogBase.model.date == datetime(sunday.year, sunday.month, sunday.day),
            ],
        )

        # We expect only the first 4-hour log to exist.
        assert len(final_worklogs) == 1
        assert final_worklogs[0].duration == 4

    @pytest.mark.asyncio
    async def test_activity_swap_violation(
        self,
        user_id: UUID,
        async_session: AsyncSession,
        project_activity_type: ActivityTypeBase,
        random_persisted_task: ActivityTaskBase,
        task_batch_factory: TaskBatchFactoryFn,
    ):
        """
        Goal: check if an activity change is occuring
        Test: users should not be able to move tasks between activities even if they own both activities
        """
        created_activity = await ActivityBase.create(
            async_session,
            ActivityBase(title="HR Project", code="ARMC-AIHR", activity_type_id=project_activity_type.id),
            commit=False,
        )

        logger.info(f"Created activity: {created_activity}")

        other_activity = await ActivityUserBase.create(
            async_session, ActivityUserBase(user_id=user_id, activity_id=created_activity.id), commit=False
        )

        logger.info(f"Activity User link: {other_activity}")

        await async_session.flush()

        task = UpsertActivityTask(
            id=random_persisted_task.id,
            title=random_persisted_task.title,
            activity_id=other_activity.activity_id,
            month=random_persisted_task.month,
            year=random_persisted_task.year,
            worklogs=[],
        )

        task_batch_dto = task_batch_factory(deletions=[], tasks=[task])
        journal_service = JournalService(async_session)

        with pytest.raises(BadRequestException) as exinfo:
            await journal_service.batch_worklog(task_batch_dto, user_id)

        assert "Moving tasks is not allowed" in str(exinfo.value)

    @pytest.mark.asyncio
    async def test_task_implicit_creation(
        self,
        user_id: UUID,
        async_session: AsyncSession,
        random_persisted_task: ActivityTaskBase,
        task_batch_factory: TaskBatchFactoryFn,
    ):
        """
        Test: A task is sent without an ID but with a title, month, and year that already exists in the for that
            activity in DB.
        Goal: The service should "Upsert" (update) the existing task rather than creating a duplicate,
            thanks to the composite key.
        """
        task = ActivityTaskBase(
            title=random_persisted_task.title,
            activity_id=random_persisted_task.activity_id,
            user_id=user_id,
            month=random_persisted_task.month,
            year=random_persisted_task.year,
        )
        task_dto = UpsertActivityTask(
            title=task.title, activity_id=task.activity_id, month=task.month, year=task.year, worklogs=[]
        )
        task_batch_dto = task_batch_factory(deletions=[], tasks=[task_dto])

        journal_service = JournalService(async_session)

        await journal_service.batch_worklog(task_batch_dto, user_id)

        found_task = await ActivityTaskBase.get_one(
            async_session, random_persisted_task.id, field=ActivityTaskBase.model.id
        )

        # by ensuring the id is still the same, we ensure an 'upsert' happend
        assert found_task.id == random_persisted_task.id
        assert found_task.month == task.month
        assert found_task.year == task.year
        assert found_task.title == task.title
        assert found_task.activity_id == task.activity_id

    @pytest.mark.asyncio
    async def test_task_deletion(
        self,
        user_id: UUID,
        async_session: AsyncSession,
        random_persisted_task: ActivityTaskBase,
        task_batch_factory: TaskBatchFactoryFn,
    ):
        """
        Test: The same task_id is included in both the deletions list AND the tasks update list.
        Goal: The task is deleted. The update is ignored (Sanitization takes precedence).
        """
        upsert_task = UpsertActivityTask(
            id=random_persisted_task.id,
            activity_id=random_persisted_task.activity_id,
            month=random_persisted_task.month,
            year=random_persisted_task.year,
            title=random_persisted_task.title,
            worklogs=[],
        )
        task_batch_dto = task_batch_factory(deletions=[random_persisted_task.id], tasks=[upsert_task])

        journal_service = JournalService(async_session)
        await journal_service.batch_worklog(task_batch_dto, user_id)

        with pytest.raises(NotFoundException) as exinfo:
            await ActivityTaskBase.get_one(async_session, random_persisted_task.id, field=ActivityTaskBase.model.id)

        assert "Resource not found" in str(exinfo.value)
