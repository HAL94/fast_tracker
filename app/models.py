from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from sqlalchemy import (
    VARCHAR,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, WriteOnlyMapped, mapped_column, relationship

from app.constants.roles import UserRole
from app.core.database import Base


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    organization_name: Mapped[str] = mapped_column(String(512), nullable=False)

    # relations
    users: WriteOnlyMapped["User"] = relationship(back_populates="tenant")
    activities: WriteOnlyMapped["Activity"] = relationship(back_populates="tenant")
    activity_tasks: WriteOnlyMapped["ActivityTask"] = relationship(back_populates="tenant")
    worklogs: WriteOnlyMapped["Worklog"] = relationship(back_populates="tenant")
    user_activities: WriteOnlyMapped["ActivityUser"] = relationship(back_populates="tenant")
    sessions: WriteOnlyMapped["Session"] = relationship(back_populates="tenant")

    tenant_config: Mapped["TenantConfig"] = relationship(back_populates="tenant", uselist=False, lazy="joined")


class TenantConfig(Base):
    __tablename__ = "tenant_configs"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), unique=True)

    settings: Mapped[dict] = mapped_column(JSONB, server_default="{}", nullable=False)
    tenant: Mapped[Tenant] = relationship(back_populates="tenant_config")


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    full_name: Mapped[str] = mapped_column(String(256), nullable=False)
    email: Mapped[str] = mapped_column(String(512), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(1024), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    role: Mapped[str] = mapped_column(String, default=UserRole.USER.value, nullable=False)

    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"))

    # Relations
    sessions: Mapped[List["Session"]] = relationship(back_populates="user", cascade="all, delete")
    tenant: Mapped[Tenant] = relationship(back_populates="users")

    # Activities assigned TO this user
    user_activities: WriteOnlyMapped["ActivityUser"] = relationship(
        back_populates="user", foreign_keys="[ActivityUser.user_id]"
    )
    activity_items: Mapped[List["Activity"]] = relationship(
        secondary="activity_users",
        viewonly=True,
        back_populates="users",
        foreign_keys="[ActivityUser.user_id, ActivityUser.activity_id]",
        # primaryjoin="User.id == ActivityUser.user_id",
        # secondaryjoin="Activity.id == ActivityUser.activity_id",
    )

    # Activities assigned BY this user
    assignments_given: Mapped[List["ActivityUser"]] = relationship(
        back_populates="assigned_by", foreign_keys="[ActivityUser.assigned_by_id]"
    )

    tasks: Mapped[List["ActivityTask"]] = relationship(back_populates="user")
    worklogs: Mapped[List["Worklog"]] = relationship(back_populates="user")

    @property
    def user_role(self) -> UserRole:
        """Get role as enum."""
        return UserRole(self.role)


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    refresh_token_hash: Mapped[str] = mapped_column(String, index=True, nullable=False)
    access_token_hash: Mapped[str] = mapped_column(String, index=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_used_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.now)
    device_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    device_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relations
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    user: Mapped["User"] = relationship(back_populates="sessions")

    tenant_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"))
    tenant: Mapped[Tenant] = relationship(back_populates="sessions")


class ActivityType(Base):
    __tablename__ = "activity_types"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    # For now types should be unique system wide
    title: Mapped[str] = mapped_column(VARCHAR(255), nullable=False, unique=True)

    activities: Mapped[List["Activity"]] = relationship(back_populates="activity_type")


class Activity(Base):
    __tablename__ = "activities"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    title: Mapped[str] = mapped_column(nullable=False)
    code: Mapped[str] = mapped_column(unique=True)

    # Relations
    activity_type_id: Mapped[UUID] = mapped_column(ForeignKey("activity_types.id", ondelete="SET NULL"), nullable=False)
    activity_type: Mapped[ActivityType] = relationship(back_populates="activities")

    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"))
    tenant: Mapped[Tenant] = relationship(back_populates="activities")

    user_activities: WriteOnlyMapped["ActivityUser"] = relationship(back_populates="activity")
    users: WriteOnlyMapped["User"] = relationship(
        secondary="activity_users",
        viewonly=True,
        back_populates="activity_items",
        foreign_keys="[ActivityUser.user_id, ActivityUser.activity_id]",
    )

    tasks: Mapped[List["ActivityTask"]] = relationship(
        back_populates="activity", cascade="all, delete-orphan", order_by="ActivityTask.title.asc()"
    )

    __table_args__ = (
        UniqueConstraint("code", "tenant_id", name="uq_activity_code_tenant"),
        Index("ix_activity_tenant_id", "tenant_id"),
    )


class ActivityTask(Base):
    __tablename__ = "activity_tasks"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    title: Mapped[str] = mapped_column(nullable=False)

    # Relations
    activity_id: Mapped[UUID] = mapped_column(ForeignKey("activities.id", ondelete="SET NULL"), nullable=True)
    activity: Mapped[Activity] = relationship(back_populates="tasks")

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    user: Mapped[User] = relationship(back_populates="tasks")

    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"))
    tenant: Mapped[Tenant] = relationship(back_populates="activity_tasks")

    worklogs: Mapped[List["Worklog"]] = relationship(
        back_populates="activity_task", cascade="all, delete-orphan", order_by="Worklog.date"
    )

    __table_args__ = (
        UniqueConstraint("title", "activity_id", "user_id", name="uq_title_activity_id_user_id"),
        # Optimized for: select * from activity_tasks where tenant_id = X and user_id = Y
        Index("ix_task_tenant_user", "tenant_id", "user_id"),
    )


class Worklog(Base):
    __tablename__ = "worklogs"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    date: Mapped[Date] = mapped_column(Date(), nullable=False)
    duration: Mapped[Float] = mapped_column(Numeric(precision=3, scale=1), nullable=False)

    # Relations
    activity_task_id: Mapped[UUID] = mapped_column(ForeignKey("activity_tasks.id", ondelete="CASCADE"))
    activity_task: Mapped[ActivityTask] = relationship(back_populates="worklogs")

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    user: Mapped[User] = relationship(back_populates="worklogs")

    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"))
    tenant: Mapped[Tenant] = relationship(back_populates="worklogs")

    __table_args__ = (
        CheckConstraint("duration >= 1 AND duration <= 8"),
        UniqueConstraint("activity_task_id", "user_id", "date", name="uq_user_activity_task_date"),
        # CRITICAL for the Grid: select ... where user_id = X and date between Y and Z
        # Including tenant_id here acts as a security anchor
        Index("ix_worklog_tenant_user_data", "tenant_id", "user_id", "date"),
        # CRITICAL for Admin Reporting: select ... where tenant_id = X and date between Y and Z
        # Allows for fast company-wide monthly reports
        Index("ix_worklog_tenant_date", "tenant_id", "date"),
    )


class ActivityUser(Base):
    __tablename__ = "activity_users"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Relations
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    user: Mapped[User] = relationship(back_populates="user_activities", foreign_keys=[user_id])

    activity_id: Mapped[UUID] = mapped_column(ForeignKey("activities.id"))
    activity: Mapped[Activity] = relationship(back_populates="user_activities")

    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"))
    tenant: Mapped[Tenant] = relationship(back_populates="user_activities")

    assigned_by_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    # Define the relationship
    assigned_by: Mapped["User"] = relationship(
        foreign_keys=[assigned_by_id]  # Specify this FK to avoid ambiguity
    )
    __table_args__ = (UniqueConstraint("tenant_id", "user_id", "activity_id", name="uq_tenant_user_activity"),)
