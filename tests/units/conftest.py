import random
import uuid
from datetime import date as Date
from datetime import datetime
from typing import List, Optional

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.activity import ActivityBase
from app.domain.activity_task import ActivityTaskBase
from app.dto.journal import TaskBatchDto, UpsertActivityTask, WorklogDto
from tests.helpers.utils import generate_random_date
from tests.units import WorklogFactoryFn


@pytest.fixture
def worklog_batch(fixed_title: str) -> TaskBatchDto:
    return TaskBatchDto(
        tasks=[
            UpsertActivityTask(
                title=fixed_title,
                activity_id=uuid.UUID("fef3f3aa-1aba-46f7-b3cc-75ec10375218"),
                month=datetime.now().month,
                year=datetime.now().year,
                worklogs=[WorklogDto(date=datetime(2026, 3, 21), duration=3)],
            )
        ]
    )


@pytest.fixture
def task_batch_factory():
    def _make(tasks: Optional[List[WorklogDto]] = None):
        return TaskBatchDto(
            tasks=tasks or [],
        )

    return _make


@pytest.fixture
def worklog_factory():
    """Create a factory function that will generate a list of worklogs independently of any given task"""

    def _make(size: Optional[int] = None, year: Optional[int] = None, month: Optional[int] = None) -> List[WorklogDto]:
        if size is None:
            size = 1
        today = datetime.now()
        date_obj = Date(year=today.year, month=today.month, day=today.day)
        if year is not None and year > 0:
            date_obj = Date(year=year, month=date_obj.month, day=date_obj.day)
        if month is not None and month > 0:
            date_obj = Date(year=date_obj.year, month=month, day=date_obj.day)

        worklogs: List[WorklogDto] = []
        for i in range(size):
            # discard current day and use a random one
            date = generate_random_date(date_obj.year, date_obj.month)
            duration = random.randint(1, 8)
            worklogs.append(WorklogDto(date=date, duration=duration))
        return worklogs

    return _make


@pytest.fixture
def sample_task(fixed_title: str, sample_activity: ActivityBase):
    return {"title": fixed_title, "activity_id": sample_activity.id}


@pytest.fixture
def random_task(random_title: str, sample_activity: ActivityBase):
    return {"title": random_title, "activity_id": sample_activity.id}


@pytest_asyncio.fixture
async def persisted_task(async_session: AsyncSession, sample_task: dict, user_id: uuid.UUID) -> ActivityTaskBase:
    """Creates a task in the DB and returns the model with a generated ID. It is a fixed task we can refer back to it
    due to the created constraints (title, activity_id, user_id)"""

    # 1. Create the model instance from your dictionary fixture
    task = ActivityTaskBase(
        title=sample_task["title"], activity_id=sample_task["activity_id"], user_id=user_id, updated_at=datetime.now()
    )
    upserted_task = await ActivityTaskBase.upsert_one(
        async_session, task, ["title", "user_id", "activity_id"], commit=False
    )
    # 2. Add and Flush (not commit) to trigger ID generation in the current transaction
    await async_session.flush()

    return upserted_task


@pytest_asyncio.fixture
async def random_persisted_task(async_session: AsyncSession, random_task: dict, user_id: uuid.UUID) -> ActivityTaskBase:
    """Creates a task in the DB and returns the model with a generated ID.
    This is going to random every time"""

    # 1. Create the model instance from your dictionary fixture
    task = ActivityTaskBase(
        title=random_task["title"],
        activity_id=random_task["activity_id"],
        user_id=user_id,
    )
    upserted_task = await ActivityTaskBase.upsert_one(
        async_session, task, ["title", "activity_id", "user_id"], commit=False
    )
    # 2. Add and Flush (not commit) to trigger ID generation in the current transaction
    await async_session.flush()

    return upserted_task


@pytest.fixture
def task_factory(random_title: str, worklog_factory: WorklogFactoryFn):
    """Create a factory function that will generate a list of tasks with their worklogs"""

    def _make(
        activity_id: Optional[uuid.UUID] = None,
        size: Optional[int] = None,
        worklog_size: Optional[int] = None,
    ) -> List[UpsertActivityTask]:
        if size is None:
            size = 1

        if worklog_size is None:
            worklog_size = 2

        tasks: List[UpsertActivityTask] = []
        today = datetime.now()
        task_worklogs: List[WorklogDto] = worklog_factory(size=worklog_size, year=today.year, month=today.month)

        for _ in range(size):
            tasks.append(UpsertActivityTask(title=random_title, activity_id=activity_id, worklogs=task_worklogs))

        return tasks

    return _make
