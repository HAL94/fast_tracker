import asyncio
from typing import List
from uuid import uuid4

from app.constants.roles import UserRole
from app.core.database import session_manager
from app.core.security.jwt import hash_password
from app.domain.activity import ActivityTypeBase
from app.domain.user import UserBase


async def seed_admin_user() -> UserBase:
    data = UserBase(
        full_name="Admin User",
        email="admin@example.com",
        hashed_password=hash_password("123456"),
        is_active=True,
        is_admin=True,
        role=UserRole.ADMIN,
    )

    async with session_manager.session() as session:
        return await UserBase.upsert_one(session, data, ["email"])


async def seed_employee_users() -> List[UserBase]:
    jason_limbu = UserBase(
        full_name="Jason Limbu",
        email="jason@example.com",
        hashed_password=hash_password("123456"),
        is_active=True,
        is_admin=False,
        role=UserRole.USER,
    )
    james_brown = UserBase(
        full_name="James Brown",
        email="james@example.com",
        hashed_password=hash_password("123456"),
        is_active=True,
        is_admin=False,
        role=UserRole.USER,
    )
    data = [jason_limbu, james_brown]
    index_elements = ["email"]

    async with session_manager.session() as session:
        return await UserBase.upsert_many(session, data, index_elements)


async def seed_activity() -> List[ActivityTypeBase]:
    project_activities = ActivityTypeBase(title="Projects", id=uuid4())
    non_project_activities = ActivityTypeBase(title="Non Project Activities", id=uuid4())
    leave = ActivityTypeBase(title="Leave", id=uuid4())
    index_elements = ["title"]
    data = [project_activities, non_project_activities, leave]

    async with session_manager.session() as session:
        return await ActivityTypeBase.upsert_many(session, data, index_elements)


async def seed_data():
    admin_user = await seed_admin_user()
    print(f"Successfully created user: {admin_user}")

    users = await seed_employee_users()
    print(f"Successfully created users: {users}")

    activities = await seed_activity()
    print(f"Successfully created a list of activities: {activities}")


if __name__ == "__main__":
    asyncio.run(seed_data())
