import asyncio
import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.constants.roles import UserRole
from app.core.database import session_manager
from app.core.security.jwt import hash_password
from app.domain.activity import ActivityBase, ActivityUserBase
from app.domain.activity_task import ActivityTaskBase
from app.domain.activity_type import ActivityTypeBase
from app.domain.tenant import TenantBase
from app.domain.user import UserBase
from app.repositories.activity_repository import ActivityRepository
from app.repositories.task_repository import ActivityTaskRepository
from app.repositories.tenant_repository import TenantRepository
from app.repositories.user_repository import UserRepository


async def seed_tenants() -> List[TenantBase]:
    scai_tenant_id = uuid.UUID("8d17597b-55c4-45fc-bf47-2081fbad971a")
    astek_tenant_id = uuid.UUID("2e5b17e0-1621-4853-a98a-f42867b05a38")
    data = [
        TenantBase(id=scai_tenant_id, organization_name="SCAI"),
        TenantBase(id=astek_tenant_id, organization_name="Astek"),
    ]
    async with session_manager.session() as session:
        repo = TenantRepository(session)
        return await repo.upsert(data, commit=True)


async def seed_admin_user(tenants: List[TenantBase]) -> List[UserBase]:
    tenant_admins = [
        UserBase(
            full_name=f"{tenant.organization_name} Admin",
            email=f"{tenant.organization_name.lower()}_admin@example.com",
            hashed_password=hash_password("123456"),
            is_active=True,
            is_admin=True,
            role=UserRole.ADMIN,
            tenant_id=tenant.id,
        )
        for tenant in tenants
    ]
    async with session_manager.session() as session:
        repo = UserRepository(session)
        return await repo.upsert(tenant_admins, ["email"], commit=True)


async def seed_employee_users(tenants: List[TenantBase]) -> List[UserBase]:
    jason_limbu = UserBase(
        full_name="Jason Limbu",
        email="jason@example.com",
        hashed_password=hash_password("123456"),
        is_active=True,
        is_admin=False,
        role=UserRole.USER,
        id=uuid.UUID("04026c86-9a31-44ed-a93f-b6ab1f4f8030"),
        tenant_id=tenants[0].id,
    )
    james_brown = UserBase(
        full_name="James Brown",
        email="james@example.com",
        hashed_password=hash_password("123456"),
        is_active=True,
        is_admin=False,
        role=UserRole.USER,
        id=uuid.UUID("f30f1a7b-303d-44ce-bab6-29334ac39539"),
        tenant_id=tenants[1].id,
    )
    data = [jason_limbu, james_brown]
    index_elements = ["email"]

    async with session_manager.session() as session:
        repo = UserRepository(session)
        return await repo.upsert(data, index_elements, commit=True)


async def seed_activity_types() -> List[ActivityTypeBase]:
    project_activities = ActivityTypeBase(title="Projects", id=uuid.UUID("93a1d5c0-0f4a-4a8f-b7e5-0af5ef267f6d"))
    non_project_activities = ActivityTypeBase(
        title="Non Project Activities", id=uuid.UUID("2f31c0e0-8fab-42bf-bf6e-b38cf5ba09a4")
    )
    leave = ActivityTypeBase(title="Leave", id=uuid.UUID("a632f36d-4ead-427f-98fe-6bb6d6896960"))
    data = [project_activities, non_project_activities, leave]

    async with session_manager.session() as session:
        ActivityType = ActivityTypeBase.model

        stmt = pg_insert(ActivityType)
        data_json = [item.model_dump(by_alias=False, exclude_none=True, exclude_unset=True) for item in data]

        stmt = stmt.on_conflict_do_update(index_elements=["id"], set_={"title": getattr(stmt.excluded, "title")})
        stmt = stmt.returning(ActivityType)

        result = await session.scalars(stmt, data_json, execution_options={"populate_existing": True})

        await session.commit()

        return [ActivityTypeBase.model_validate(item, from_attributes=True) for item in result]


async def seed_activities(activity_types: List[ActivityTypeBase], tenants: List[TenantBase]) -> List[ActivityBase]:
    project_activity = activity_types[0]

    project_activities = [
        ActivityBase(
            id=uuid.UUID("fef3f3aa-1aba-46f7-b3cc-75ec10375218"),
            activity_type_id=project_activity.id,
            title="Saudi Company for Artificial Intelligence",
            code="SCAI-AUG",
            tenant_id=tenants[0].id,
        ),
        ActivityBase(
            id=uuid.UUID("d66fdcfc-ed02-49a8-b660-d3720f63ecd2"),
            activity_type_id=project_activity.id,
            title="Astek",
            code="ASTK-HIS",
            tenant_id=tenants[1].id,
        ),
    ]

    async with session_manager.session() as session:
        repo = ActivityRepository(session)
        created_project_activities = await repo.upsert(project_activities, commit=True)

    return created_project_activities


async def seed_emplyee_activities(
    activities: List[ActivityBase], employees: List[UserBase], admins: Optional[List[UserBase]] = None
) -> List[ActivityUserBase]:
    data = []
    if len(employees) <= 0 or len(activities) <= 0:
        raise ValueError(
            "Cannot proceed with seeding employee activities, as one of the lists\
                          ['activities', 'employees'] is empty"
        )

    tenant_admin_map = {admin_user.tenant_id: admin_user.id for admin_user in admins}

    for activity in activities:
        for employee in employees:
            if activity.tenant_id == employee.tenant_id:
                admin_id = tenant_admin_map.get(activity.tenant_id)
                data.append(
                    ActivityUserBase(
                        id=uuid.uuid4(),
                        user_id=employee.id,
                        activity_id=activity.id,
                        assigned_by_id=admin_id,
                        tenant_id=activity.tenant_id,
                    )
                )
    index_elements = ["user_id", "activity_id", "tenant_id"]
    async with session_manager.session() as session:
        ActivityUser = ActivityUserBase.model
        stmt = pg_insert(ActivityUser)
        stmt = stmt.on_conflict_do_update(
            index_elements=index_elements,
            set_={
                col.key: getattr(stmt.excluded, col.key)
                for col in ActivityUser.columns()
                if col.key not in index_elements
            },
        )
        stmt = stmt.returning(ActivityUser)
        data_json = [item.model_dump(exclude_unset=True, by_alias=False, exclude_none=True) for item in data]
        result = await session.scalars(stmt, data_json)
        return [ActivityUserBase.model_validate(item, from_attributes=True) for item in result.all()]


async def seed_employee_tasks(activities: List[ActivityBase], employees: List[UserBase]) -> list[ActivityTaskBase]:
    data = []
    for activity in activities:
        for employee in employees:
            if employee.tenant_id == activity.tenant_id:
                data.append(
                    ActivityTaskBase(
                        title=f"Task for {activity.code} for employee {employee.full_name}",
                        user_id=employee.id,
                        activity_id=activity.id,
                        updated_at=datetime.now(),
                        tenant_id=activity.tenant_id,
                    )
                )

    async with session_manager.session() as session:
        index_elements = ["activity_id", "title", "user_id"]
        repo = ActivityTaskRepository(session)
        return await repo.upsert(data, index_elements, commit=True)


async def seed_data():
    tenants = await seed_tenants()
    print(f"Successfully seeded {len(tenants)} tenants")

    admins = await seed_admin_user(tenants)
    print(f"Successfully seeded {len(admins)} admin users")

    employees = await seed_employee_users(tenants)
    print(f"Successfully seeded {len(employees)} employees")

    activity_types = await seed_activity_types()
    print(f"Successfully seeded {len(activity_types)} activity types")

    activities = await seed_activities(activity_types, tenants)
    print(f"Successfully seeded {len(activities)} activities")

    await seed_emplyee_activities(activities, employees, admins)
    print(f"Successfully assigned {len(activities)} activities for {len(employees)} employees")

    await seed_employee_tasks(activities, employees)
    print("Successfully added tasks for all activities and employees")


if __name__ == "__main__":
    asyncio.run(seed_data())
