from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from sqlalchemy import VARCHAR, Boolean, DateTime, Float, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.constants.roles import UserRole
from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    full_name: Mapped[str] = mapped_column(String(256), nullable=False)
    email: Mapped[str] = mapped_column(String(512), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(1024), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    role: Mapped[str] = mapped_column(String, default=UserRole.USER.value, nullable=False)

    # Relations
    sessions: Mapped[List["Session"]] = relationship(back_populates="user", cascade="all, delete")

    activity_user_rel: Mapped[List["ActivityUser"]] = relationship(back_populates="user")
    activity_items: Mapped[List["Activity"]] = relationship(
        secondary="activity_users", viewonly=True, back_populates="users"
    )

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


class ActivityType(Base):
    __tablename__ = "activity_types"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    title: Mapped[str] = mapped_column(VARCHAR(255), nullable=False, unique=True)

    activities: Mapped[List["Activity"]] = relationship(back_populates="activity_type")


class Activity(Base):
    __tablename__ = "activities"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    title: Mapped[str] = mapped_column(nullable=False)
    code: Mapped[str] = mapped_column(unique=True)

    expected_hours: Mapped[int] = mapped_column(nullable=False)

    # Relations
    activity_type_id: Mapped[UUID] = mapped_column(ForeignKey("activity_types.id", ondelete="SET NULL"), nullable=False)
    activity_type: Mapped[ActivityType] = relationship(back_populates="activities")

    activity_user_rel: Mapped[List["ActivityUser"]] = relationship(back_populates="activity")
    users: Mapped[List["User"]] = relationship(
        secondary="activity_users", viewonly=True, back_populates="activity_items"
    )

    activity_tasks: Mapped[List["ActivityTask"]] = relationship(back_populates="activity", cascade="all, delete-orphan")


class ActivityTask(Base):
    __tablename__ = "activity_tasks"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    title: Mapped[str] = mapped_column(unique=True, nullable=False)

    # Relations
    activity_id: Mapped[UUID] = mapped_column(ForeignKey("activities.id", ondelete="CASCADE"), nullable=False)
    activity: Mapped[Activity] = relationship(back_populates="activity_tasks")

    worklogs: Mapped[List["Worklog"]] = relationship(back_populates="activity_task")


class Worklog(Base):
    __tablename__ = "worklogs"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration: Mapped[float] = mapped_column(Float(precision=4), nullable=False)

    # Relations
    activity_task_id: Mapped[UUID] = mapped_column(ForeignKey("activity_tasks.id", ondelete="SET NULL"), nullable=False)
    activity_task: Mapped[ActivityTask] = relationship(back_populates="worklogs")


class ActivityUser(Base):
    __tablename__ = "activity_users"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Relations
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    user: Mapped[User] = relationship(back_populates="activity_user_rel")

    activity_id: Mapped[UUID] = mapped_column(ForeignKey("activities.id", ondelete="SET NULL"))
    activity: Mapped[Activity] = relationship(back_populates="activity_user_rel")

    __table_args__ = (UniqueConstraint("user_id", "activity_id", name="uq_user_activity"),)
