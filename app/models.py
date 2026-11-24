import uuid
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    LargeBinary,
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
    conversations: Mapped[list["Conversation"]] = relationship(
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
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)  # created by "Load demo data"; shown with a Demo tag

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


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(200), default="New chat")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    user: Mapped["User"] = relationship(back_populates="conversations")
    messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan", order_by="ChatMessage.id"
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    __table_args__ = (CheckConstraint("role IN ('user', 'assistant')", name="ck_chat_role"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    conversation_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("conversations.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(10))  # "user" or "assistant"
    content: Mapped[str] = mapped_column(Text)
    sources: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)  # kb_notes ids used for this answer
    context: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # habit/risk summary sent to the LLM
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")


class KbNote(Base):
    """One short habit-science note = one retrieval chunk (notes are only a few hundred words)."""

    __tablename__ = "kb_notes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200))
    topic: Mapped[str] = mapped_column(String(100), index=True)
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True)
    embedding_model: Mapped[str] = mapped_column(String(100), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)