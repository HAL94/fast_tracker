from typing import ClassVar, List, Optional
from uuid import UUID

from pydantic import Field
from sqlalchemy.orm import selectinload

from app.constants.roles import UserRole
from app.domain.activity import ActivityWithType
from app.domain.base import BaseDomain
from app.models import Activity, User


class UserBase(BaseDomain[User]):
    model: ClassVar[User] = User

    id: Optional[UUID] = None
    tenant_id: UUID
    full_name: str
    email: str
    hashed_password: str
    is_active: bool = True
    is_admin: bool = False
    role: UserRole = UserRole.USER


class UserWithActivities(BaseDomain[User]):
    model: ClassVar[User] = User

    @classmethod
    def relations(cls):
        return [selectinload(User.activity_items).joinedload(Activity.activity_type)]

    full_name: str
    activity_items: List[ActivityWithType]


class UserWithoutPassword(UserBase):
    hashed_password: Optional[str] = Field(exclude=True, default=None)
