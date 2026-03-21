import pytest_asyncio

from app.domain.activity import ActivityBase
from app.domain.activity_type import ActivityTypeBase


@pytest_asyncio.fixture
async def sample_data(project_activity_type: ActivityTypeBase) -> ActivityBase:
    return ActivityBase(title="SampleActivity", code="SPL100", activity_type_id=str(project_activity_type.id))

