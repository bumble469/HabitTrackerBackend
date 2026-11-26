import uuid
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def new_id() -> str:
    return uuid.uuid4().hex


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)  # store lowercase
    password_hash: Mapped[str] = mapped_column(String(255))  # never the plain password
    display_name: Mapped[str] = mapped_column(String(100), default="")
    timezone: Mapped[str] = mapped_column(String(64), default="UTC")  # IANA name, e.g. Asia/Kolkata; decides what "today" is
    ai_enabled: Mapped[bool] = mapped_column(Boolean, default=True)  # the Settings "AI on/off" toggle
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    habits: Mapped[list["Habit"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    push_subscriptions: Mapped[list["PushSubscription"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Habit(Base):
    __tablename__ = "habits"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    created_on: Mapped[date] = mapped_column(Date, default=date.today)
    archived_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)  
    reminder_time: Mapped[Optional[str]] = mapped_column(String(5), nullable=True)
    scheduled_days: Mapped[Optional[list[int]]] = mapped_column(
        JSON, nullable=True, default=lambda: list(range(7))
    )
    user: Mapped["User"] = relationship(back_populates="habits")
    completions: Mapped[list["Completion"]] = relationship(
        back_populates="habit", cascade="all, delete-orphan"
    )
    predictions: Mapped[list["RiskPrediction"]] = relationship(
        back_populates="habit", cascade="all, delete-orphan"
    )


class Completion(Base):
    """One row = the habit was done on that day. A missed day has NO row (the ML code relies on this)."""

    __tablename__ = "completions"
    __table_args__ = (UniqueConstraint("habit_id", "day", name="uq_completion_habit_day"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    habit_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("habits.id", ondelete="CASCADE"), index=True
    )
    day: Mapped[date] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)  # when it was ticked

    habit: Mapped["Habit"] = relationship(back_populates="completions")


class RiskPrediction(Base):
    """History of the model's output: one snapshot per habit per day."""

    __tablename__ = "risk_predictions"
    __table_args__ = (UniqueConstraint("habit_id", "as_of", name="uq_prediction_habit_asof"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    habit_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("habits.id", ondelete="CASCADE"), index=True
    )
    as_of: Mapped[date] = mapped_column(Date)  # day the features were computed for (yesterday in the app)
    risk: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # NULL = habit too new to score
    level: Mapped[str] = mapped_column(String(20))  # low / medium / high / not_enough_data
    reasons: Mapped[list] = mapped_column(JSON, default=list)
    model_version: Mapped[str] = mapped_column(String(50), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    habit: Mapped["Habit"] = relationship(back_populates="predictions")


class PushSubscription(Base):
    __tablename__ = "push_subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    endpoint: Mapped[str] = mapped_column(String(1024), unique=True)
    p256dh: Mapped[str] = mapped_column(String(255))
    auth: Mapped[str] = mapped_column(String(255))
    user_agent: Mapped[str] = mapped_column(String(255), default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="push_subscriptions")


class ReminderLog(Base):
    """One row = a reminder was sent for that habit on that local day (prevents duplicates)."""

    __tablename__ = "reminder_logs"
    __table_args__ = (UniqueConstraint("habit_id", "day", name="uq_reminder_habit_day"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    habit_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("habits.id", ondelete="CASCADE"), index=True
    )
    day: Mapped[date] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)