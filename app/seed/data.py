import asyncio
import uuid
from typing import List, Optional

from app.constants.roles import UserRole
from app.core.database import session_manager
from app.core.security.jwt import hash_password
from app.domain.activity import ActivityBase, ActivityTaskBase, ActivityTypeBase, ActivityUserBase
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


async def seed_activity_types() -> List[ActivityTypeBase]:
    project_activities = ActivityTypeBase(title="Projects", id=uuid.UUID("93a1d5c0-0f4a-4a8f-b7e5-0af5ef267f6d"))
    non_project_activities = ActivityTypeBase(
        title="Non Project Activities", id=uuid.UUID("2f31c0e0-8fab-42bf-bf6e-b38cf5ba09a4")
    )
    leave = ActivityTypeBase(title="Leave", id=uuid.UUID("a632f36d-4ead-427f-98fe-6bb6d6896960"))
    index_elements = ["id"]
    data = [project_activities, non_project_activities, leave]

    async with session_manager.session() as session:
        return await ActivityTypeBase.upsert_many(session, data, index_elements)


async def seed_activities(activity_types: List[ActivityTypeBase]) -> List[ActivityBase]:
    project_activity, non_project_activity = activity_types[0], activity_types[1]

    project_activities = [
        ActivityBase(
            id=uuid.UUID("fef3f3aa-1aba-46f7-b3cc-75ec10375218"),
            activity_type_id=project_activity.id,
            title="Saudi Company for Artificial Intelligence",
            code="SCAI-AUG",
        ),
        ActivityBase(
            id=uuid.UUID("d66fdcfc-ed02-49a8-b660-d3720f63ecd2"),
            activity_type_id=project_activity.id,
            title="Saudi Aramco",
            code="ARMC-HIS",
        ),
        ActivityBase(
            id=uuid.UUID("bf2678aa-a630-49aa-97f1-332221bf4449"),
            activity_type_id=project_activity.id,
            title="Saudi Aramco",
            code="ARMC-HUG",
        ),
    ]

    non_project_activities = [
        ActivityBase(
            id=uuid.UUID("40876b01-943f-487b-9c95-bc799e997025"),
            activity_type_id=non_project_activity.id,
            title="OTH - Other",
            code="oth",
        ),
        ActivityBase(
            id=uuid.UUID("99c50518-0d15-4877-939e-5f8aa0dda520"),
            activity_type_id=non_project_activity.id,
            title="Business Development",
            code="BUS-DEV",
        ),
        ActivityBase(
            id=uuid.UUID("837a9f19-e1cd-48f6-9496-3f22e4183eb9"),
            activity_type_id=non_project_activity.id,
            title="Delivery and Program Management",
            code="DEL-PROG",
        ),
    ]

    index_elements = ["id"]
    async with session_manager.session() as session:
        created_projet_activities = await ActivityBase.upsert_many(session, project_activities, index_elements)
        created_non_project_activities = await ActivityBase.upsert_many(session, non_project_activities, index_elements)

    return created_projet_activities, created_non_project_activities


async def seed_emplyee_activities(
    activities: List[ActivityBase], employees: List[UserBase], admin_id: Optional[uuid.UUID] = None
) -> List[ActivityUserBase]:
    data = []
    if len(employees) <= 0 or len(activities) <= 0:
        raise ValueError(
            "Cannot proceed with seeding employee activities, as one of the lists\
                          ['activities', 'employees'] is empty"
        )

    for activity in activities:
        for employee in employees:
            data.append(
                ActivityUserBase(
                    id=uuid.uuid4(),
                    user_id=employee.id,
                    activity_id=activity.id,
                    assigned_by_id=admin_id,
                )
            )
    index_elements = ["user_id", "activity_id"]

    async with session_manager.session() as session:
        return await ActivityUserBase.upsert_many(session, data, index_elements)


async def seed_employee_tasks(activities: List[ActivityBase], employees: List[UserBase]):
    data = []
    for activity in activities:
        for employee in employees:
            data.append(
                ActivityTaskBase(
                    title=f"Task for {activity.code} for employee {employee.full_name}",
                    user_id=employee.id,
                    activity_id=activity.id,
                )
            )

    index_elements = ["title", "user_id"]
    async with session_manager.session() as session:
        await ActivityTaskBase.upsert_many(session, data, index_elements)


async def seed_data():
    admin = await seed_admin_user()
    print("Successfully created admin user")

    employees = await seed_employee_users()
    print(f"Successfully created {len(employees)} employees")

    activity_types = await seed_activity_types()
    print(f"Successfully created {len(activity_types)} activity types")

    activities, _ = await seed_activities(activity_types)
    print(f"Successfully created {len(activities)} activities")

    await seed_emplyee_activities(activities, employees, admin.id)
    print(f"Successfully assigned {len(activities)} activities for {len(employees)} employees")

    await seed_employee_tasks(activities, employees)
    print("Successfully added tasks for all activities and employees")


if __name__ == "__main__":
    asyncio.run(seed_data())
