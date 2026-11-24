"""Request and response shapes for the auth, habit, data and coach routes."""
import re
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
TZ_RE = re.compile(r"^[A-Za-z0-9_+\-]+(/[A-Za-z0-9_+\-]+){0,2}$")


def _trim_date(v):
    """Accept '2026-11-20T10:00:00.000Z' as well as '2026-11-20'."""
    if isinstance(v, str) and len(v) > 10:
        return v[:10]
    return v


def _check_timezone(v):
    if v is None:
        return v
    v = v.strip()
    if not TZ_RE.match(v):
        raise ValueError("Use an IANA timezone name such as Asia/Kolkata")
    return v


# ---------- auth ----------

class RegisterIn(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(default="", max_length=100)
    timezone: str = Field(default="UTC", max_length=64)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v):
        v = v.strip().lower()
        if not EMAIL_RE.match(v):
            raise ValueError("Enter a valid email address")
        return v

    @field_validator("timezone")
    @classmethod
    def check_tz(cls, v):
        return _check_timezone(v)


class LoginIn(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v):
        return v.strip().lower()


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    display_name: str
    timezone: str
    ai_enabled: bool


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class UserUpdate(BaseModel):
    display_name: Optional[str] = Field(default=None, max_length=100)
    timezone: Optional[str] = Field(default=None, max_length=64)
    ai_enabled: Optional[bool] = None

    @field_validator("timezone")
    @classmethod
    def check_tz(cls, v):
        return _check_timezone(v)


# ---------- habits ----------

class HabitCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = ""
    created_on: Optional[date] = None

    @field_validator("name")
    @classmethod
    def clean_name(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Name cannot be empty")
        return v

    @field_validator("created_on", mode="before")
    @classmethod
    def trim_created_on(cls, v):
        return _trim_date(v)


class HabitUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = None

    @field_validator("name")
    @classmethod
    def clean_name(cls, v):
        if v is None:
            return v
        v = v.strip()
        if not v:
            raise ValueError("Name cannot be empty")
        return v


class HabitOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str
    created_on: date
    archived_at: Optional[datetime] = None
    is_demo: bool = False


# ---------- export / import / demo ----------

class ExportHabit(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = ""
    created_on: date
    completed_dates: list[date] = Field(default_factory=list, max_length=4000)

    @field_validator("created_on", mode="before")
    @classmethod
    def trim_created_on(cls, v):
        return _trim_date(v)


class ExportOut(BaseModel):
    version: int = 1
    exported_at: datetime
    habits: list[ExportHabit]


class ImportIn(BaseModel):
    habits: list[ExportHabit] = Field(max_length=200)


class ImportOut(BaseModel):
    habits_created: int
    completions_created: int


class DemoOut(BaseModel):
    habits_created: int
    completions_created: int


class DemoRemoveOut(BaseModel):
    habits_removed: int


# ---------- risk ----------

class RiskOut(BaseModel):
    habit_id: str
    as_of: date
    risk: Optional[float]
    level: str
    reasons: list[str]


class RiskHistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    as_of: date
    risk: Optional[float]
    level: str
    reasons: list[str]


# ---------- coach ----------

class SourceOut(BaseModel):
    id: int
    title: str


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: str
    content: str
    sources: Optional[list[SourceOut]] = None
    created_at: datetime


class CoachChatIn(BaseModel):
    conversation_id: Optional[str] = None
    message: str = Field(min_length=1, max_length=1000)

    @field_validator("message")
    @classmethod
    def clean_message(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Message cannot be empty")
        return v


class CoachChatOut(BaseModel):
    conversation_id: str
    mode: str  # "llm", "retrieval_only" or "placeholder" (until the RAG is built)
    message: MessageOut


class ConversationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    created_at: datetime
    updated_at: datetime


class ConversationDetail(ConversationOut):
    messages: list[MessageOut]
