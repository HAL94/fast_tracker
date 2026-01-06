from typing import Any
from uuid import UUID

import pytest
from fastapi import status
from httpx import AsyncClient

from app.dto.auth import LoginUserDto, RegisterUserDto


class TestAuthRoutes:
    """Test all auth routes"""

    @pytest.mark.asyncio
    async def test_register(self, client: AsyncClient, register_user_payload: RegisterUserDto):
        """Run register endpoint which will create user"""
        response = await client.post("/auth/register", json=register_user_payload.model_dump(by_alias=True))

        assert response.status_code == status.HTTP_200_OK
        payload: dict[str, Any] = response.json()

        assert payload is not None
        user_id = payload.get("id")

        assert user_id is not None
        assert UUID(user_id) is not None

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
        data = response.json()

        assert data is not None
        current_user_id = data.get("id")
        assert current_user_id is not None
        assert user_id is not None
