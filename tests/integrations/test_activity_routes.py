import logging
import uuid

import pytest
from httpx import AsyncClient

from app.domain.activity import ActivityBase, ActivityUserBase
from app.domain.user import UserBase

# from app.models import Activity

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class TestActivityRoutes:
    """Test all activity routes"""

    @pytest.mark.asyncio
    async def test_get_all_activities(self, admin_client: AsyncClient):
        response = await admin_client.get("/activity/")

        assert response.status_code == 200
        result = response.json()

        assert result is not None
        data = result.get("data")
        assert isinstance(data, list)
        data = [ActivityBase.model_validate(item) for item in data]
        assert len(data) > 0

    @pytest.mark.asyncio
    async def test_add_activity(self, admin_client: AsyncClient, sample_data: ActivityBase):
        response = await admin_client.post(
            "/activity/",
            json={
                "title": sample_data.title,
                "code": sample_data.code,
                "activity_type_id": str(sample_data.activity_type_id),
            },
        )
        assert response.status_code == 201
        result = response.json()
        assert result is not None
        data = result.get("data")
        assert data is not None
        data = ActivityBase.model_validate(data)
        assert isinstance(data.id, uuid.UUID)

    @pytest.mark.asyncio
    async def test_add_activity_to_unknown_activity_type(self, admin_client: AsyncClient):
        """Test that should fail if adding for an activity_type_id that should not exist (integrity error),
        should return 400 status code"""
        response = await admin_client.post(
            "/activity/",
            json={
                "title": "RandomActivity",
                "code": "SMPL102",
                "activity_type_id": str(uuid.uuid4()),
            },
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_assign_unknown_activity_to_user(self, admin_client: AsyncClient, user: UserBase):
        """Test that should fail if adding for an activity_type_id that should not exist (integrity error),
        should return 400 status code"""
        response = await admin_client.post(
            "/activity/assign",
            json={
                "userId": str(user.id),
                "activityId": str(uuid.uuid4()),
            },
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_assign_unknown_user_to_activity(self, admin_client: AsyncClient, sample_activity: ActivityBase):
        """Test that should fail if adding for a user_id that should not exist (integrity error),
        should return 400 status code"""
        response = await admin_client.post(
            "/activity/assign",
            json={
                "user_id": str(uuid.uuid4()),
                "activity_id": str(sample_activity.id),
            },
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_assign_activity_to_user(
        self, admin_client: AsyncClient, user: UserBase, sample_activity: ActivityBase
    ):
        """Test assigning a user by the admin"""
        response = await admin_client.post(
            "/activity/assign",
            json={
                "userId": str(user.id),
                "activityId": str(sample_activity.id),
            },
        )
        assert response.status_code == 201
        result = response.json()
        assert result is not None
        data = result.get("data")
        assert data is not None
        data = ActivityUserBase.model_validate(data)
        assert isinstance(data.id, uuid.UUID)

    @pytest.mark.asyncio
    async def test_assign_activity_to_user_by_unauthorized_admin(
        self, user_client: AsyncClient, user: UserBase, sample_activity: ActivityBase
    ):
        """Test assigning a user by the admin"""
        response = await user_client.post(
            "/activity/assign",
            json={
                "userId": str(user.id),
                "activityId": str(sample_activity.id),
            },
        )
        assert response.status_code == 401
