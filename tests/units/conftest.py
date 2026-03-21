import uuid
from datetime import date as Date
from datetime import datetime

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.activity import ActivityBase
from app.domain.activity_task import ActivityTaskBase
from app.domain.worklog import WorklogBase
from app.dto.activity import TaskBatchDto, UpsertActivityTask, WorklogDto


@pytest.fixture
def worklog_batch() -> TaskBatchDto:
    return TaskBatchDto(
        tasks=[
            UpsertActivityTask(
                title="A new task",
                activity_id=uuid.UUID("fef3f3aa-1aba-46f7-b3cc-75ec10375218"),
                month=datetime.now().month,
                year=datetime.now().year,
                worklogs=[WorklogDto(date=datetime(2026, 3, 21), duration=3)],
            )
        ]
    )


@pytest.fixture
def worklog_batch_factory(jason_user_id: uuid.UUID, sample_activity: ActivityBase):
    def _make(duration=2, date_obj=None):
        today = datetime.now()
        return TaskBatchDto(
            deletions=[],
            tasks=[
                {
                    "id": None,
                    "title": "Coding",
                    "activity_id": sample_activity.id,
                    "month": 3,
                    "year": 2026,
                    "worklogs": [{"date": date_obj or Date(today.year, today.month, today.day), "duration": duration}],
                }
            ],
        )

    return _make


@pytest_asyncio.fixture
async def existing_worklog(
    async_session: AsyncSession, jason_user_id: uuid.UUID, sample_activity: ActivityBase
) -> WorklogBase:
    """Creates a task and worklog in the DB so we can test UPDATING them."""
    # noqa: PLC0415
    today = datetime.now()
    # 1. Create the Task
    task = ActivityTaskBase(
        title="Initial Task", activity_id=sample_activity.id, user_id=jason_user_id, month=3, year=2026
    )
    task_db = await ActivityTaskBase.upsert_one(async_session, task, commit=False)
    await async_session.flush()

    # 2. Create the Worklog
    worklog = WorklogBase(
        date=Date(today.year, today.month, today.day),
        duration=4,  # Original duration
        activity_task_id=task_db.id,
        user_id=jason_user_id,
    )
    worklog_db = await WorklogBase.upsert_one(async_session, worklog, commit=False)
    await async_session.flush()
    await async_session.refresh(worklog_db)

    return worklog_db
