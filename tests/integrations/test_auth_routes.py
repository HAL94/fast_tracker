import logging
import uuid
from typing import Any
from uuid import UUID

import pytest
from fastapi import status
from httpx import AsyncClient

from app.domain.user import UserWithoutPassword
from app.dto.auth import LoginUserDto, RegisterUserDto, UserSession

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class TestAuthRoutes:
    """Test all auth routes"""

    @pytest.mark.asyncio
    async def test_register(self, client: AsyncClient, register_user_payload: RegisterUserDto):
        """Run register endpoint which will create user"""
        response = await client.post("/auth/register", json=register_user_payload.model_dump(by_alias=True))

        assert response.status_code == status.HTTP_200_OK
        result: dict[str, Any] = response.json()

        data = result.get("data")
        assert data is not None

        payload = UserWithoutPassword.model_validate(data)

        assert payload is not None
        returned_user_id = payload.id

        assert returned_user_id is not None

    @pytest.mark.asyncio
    async def test_login(self, client: AsyncClient, login_user_payload: LoginUserDto):
        """Run test for logging in user"""
        response = await client.post(
            "/auth/login", data={"username": login_user_payload.email, "password": login_user_payload.password}
        )

        assert response.status_code == status.HTTP_200_OK

        payload: dict[str, Any] = response.json()
        assert payload is not None
        is_success = payload.get("success")
        assert is_success
        data: dict[str, Any] = payload.get("data", None)
        assert data is not None
        assert data.get("sessionId") is not None

    @pytest.mark.asyncio
    async def test_login_unknown_credentials(self, client: AsyncClient):
        """Run test for logging in user with unknown credentials"""
        response = await client.post(
            "/auth/login", data={"username": f"{str(uuid.uuid4())}@example.com", "password": str(uuid.uuid4())}
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_me(self, user_client: AsyncClient):
        """Test getting authorized user data from endpoint"""
        response = await user_client.get("/auth/me")
        result: dict[str, Any] = response.json()

        assert result is not None
        data = result.get("data")
        assert data is not None

        payload = UserWithoutPassword.model_validate(data)
        current_user_id = payload.id
        assert current_user_id is not None
        assert isinstance(current_user_id, UUID)

    @pytest.mark.asyncio
    async def test_refresh_session(self, user_client: AsyncClient):
        """Test refreshing the session"""

        response = await user_client.post("/auth/refresh")
        result = response.json()

        assert result is not None
        data = result.get("data")
        assert data is not None

        payload = UserSession.model_validate(data)
        refresh_token = payload.refresh_token
        access_token = payload.access_token

        assert refresh_token is not None
        assert access_token is not None
        assert payload.token_type == "bearer"
