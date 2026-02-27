from typing import Any
from unittest.mock import patch
from uuid import UUID

import pytest
from fastapi import status
from httpx import AsyncClient

from app.domain.user import UserWithoutPassword
from app.dto.auth import LoginUserDto, RegisterUserDto
from app.services.auth import AuthService


class TestAuthRoutes:
    """Test all auth routes"""

    @pytest.fixture
    def auth_service(self, mocker):
        with patch("app.api.v1.auth.AuthService") as auth_service_class:
            auth_service = mocker.MagicMock(spec=AuthService)

            auth_service.get_current_user = mocker.AsyncMock()

            auth_service_class.return_value = auth_service
            yield auth_service

    @pytest.mark.asyncio
    async def test_register(self, client: AsyncClient, register_user_payload: RegisterUserDto, user_id):
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
    async def test_login(self, client: AsyncClient, login_user_payload: LoginUserDto, app_session):
        """Run test for logging in user"""
        response = await client.post(
            "/auth/login", data={"username": login_user_payload.email, "password": login_user_payload.password}
        )

        app_session["data"] = response.cookies
        assert response.status_code == status.HTTP_200_OK

        payload: dict[str, Any] = response.json()
        assert payload is not None
        is_success = payload.get("success")
        assert is_success
        data: dict[str, Any] = payload.get("data", None)
        assert data is not None
        assert data.get("sessionId") is not None

    @pytest.mark.asyncio
    async def test_me(self, client: AsyncClient, app_session, user_id):
        """Test getting authorized user data from endpoint"""
        client.cookies.update(app_session["data"])

        response = await client.get("/auth/me")
        result = response.json()

        assert result is not None
        data = result.get("data")
        assert data is not None

        payload = UserWithoutPassword.model_validate(data)
        current_user_id = payload.id
        assert current_user_id is not None
        assert isinstance(current_user_id, UUID)
