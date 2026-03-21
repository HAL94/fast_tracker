import logging
from typing import AsyncGenerator, Generator
from uuid import UUID

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.database.url import DATABASE_URL
from app.core.security.jwt import JwtManager
from app.core.setup import app
from app.dependencies.db_session import get_async_session
from app.domain.activity import ActivityBase
from app.domain.activity_type import ActivityTypeBase
from app.domain.user import UserBase
from app.dto.auth import LoginUserDto, RegisterUserDto
from app.services.auth import AuthService

AsyncSessionMaker = async_sessionmaker[AsyncSession]

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


async def _create_authenticated_client(
    email: str, password: str, fast_api: FastAPI, session: AsyncSession
) -> AsyncClient:
    """Helper to seed a session and return a client with signed cookies."""
    base_url = f"http://{settings.HOST}:{settings.APP_PORT}/api/v1"

    auth_service = AuthService(session)
    user_session = await auth_service.login(LoginUserDto(email=email, password=password))

    at_options = JwtManager.at_cookie_options(user_session.access_token)
    rt_options = JwtManager.rt_cookie_options(user_session.refresh_token)

    client = AsyncClient(transport=ASGITransport(app=fast_api), base_url=base_url)

    # Set Cookies on the client
    for opt in [at_options, rt_options]:
        client.cookies.set(name=opt.get("key"), value=opt.get("value"))

    return client


@pytest_asyncio.fixture(scope="session")
async def engine():
    """Create a single engine for the entire test session."""
    engine = create_async_engine(DATABASE_URL, future=True)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def async_session(engine: AsyncEngine) -> AsyncGenerator[AsyncSession]:
    """
    Provides a function-scoped AsyncSession wrapped in a transaction that is rolled back
    after the test finishes to ensure a clean slate for the next test.
    """
    session_maker = AsyncSessionMaker(
        autocommit=False,
        bind=engine,
        expire_on_commit=False,
    )

    async with session_maker() as session:
        try:
            yield session
        finally:
            await session.rollback()
            await engine.dispose()


@pytest.fixture
def fast_api(async_session: AsyncSession) -> Generator[FastAPI, None]:
    async def _get_test_db():
        yield async_session

    app.dependency_overrides[get_async_session] = _get_test_db
    yield app
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client(fast_api: FastAPI) -> AsyncGenerator[None, AsyncClient]:
    """Base client for the use of testing routes"""
    base_url = f"http://{settings.HOST}:{settings.APP_PORT}/api/v1"
    async with AsyncClient(transport=ASGITransport(app=fast_api), base_url=base_url) as client:
        yield client


@pytest_asyncio.fixture
def register_user_payload() -> RegisterUserDto:
    return RegisterUserDto(full_name="Tester Mate", email="tester@example.com", password="123456")


@pytest_asyncio.fixture()
def login_user_payload() -> LoginUserDto:
    return LoginUserDto(email="jason@example.com", password="123456")


@pytest_asyncio.fixture
async def admin_user(async_session: AsyncSession) -> UserBase:
    """Fixture to create a brand new user in the DB for each test."""
    user = await UserBase.get_one(async_session, "admin@example.com", field=UserBase.model.email)
    return user


@pytest_asyncio.fixture
async def user(async_session: AsyncSession) -> UserBase:
    """Fixture to create a brand new user in the DB for each test."""
    user = await UserBase.get_one(async_session, "jason@example.com", field=UserBase.model.email)
    return user


@pytest_asyncio.fixture
async def jason_user_id(async_session: AsyncSession) -> UUID:
    """Fixture to get the user id of a user named Jason."""
    user = await UserBase.get_one(async_session, "jason@example.com", field=UserBase.model.email)
    return user.id


@pytest_asyncio.fixture
async def admin_client(
    fast_api: FastAPI, async_session: AsyncSession, admin_user: UserBase
) -> AsyncGenerator[None, AsyncClient]:
    """Update the client with an admin credentials in cookies"""
    client = await _create_authenticated_client(admin_user.email, "123456", fast_api, async_session)
    yield client
    await client.aclose()


@pytest_asyncio.fixture
async def user_client(
    fast_api: FastAPI, async_session: AsyncSession, user: UserBase
) -> AsyncGenerator[None, AsyncClient]:
    """Update the client with the role of a user cookies"""
    client = await _create_authenticated_client(user.email, "123456", fast_api, async_session)
    yield client
    await client.aclose()


@pytest_asyncio.fixture
async def project_activity_type(async_session: AsyncSession) -> ActivityTypeBase:
    return await ActivityTypeBase.get_one(async_session, "Projects", field=ActivityTypeBase.model.title)


@pytest_asyncio.fixture
async def sample_activity(async_session: AsyncSession, project_activity_type: ActivityTypeBase) -> ActivityBase:
    """Creates a sample activity for other tests to use."""
    activity = ActivityBase(
        title="SampleActivity",
        code="SPL101",
        activity_type_id=str(project_activity_type.id),
    )
    activity_upserted = await ActivityBase.upsert_one(async_session, activity, ["code"], commit=False)
    await async_session.flush()
    return activity_upserted
