"""Request and response shapes for the auth, habit, data, risk and push routes."""
import re
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
TZ_RE = re.compile(r"^[A-Za-z0-9_+\-]+(/[A-Za-z0-9_+\-]+){0,2}$")
HHMM_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


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


def _check_reminder(v):
    """Reminder time as 'HH:MM' (24h, in the user's timezone). None or '' clears it."""
    if v is None or v == "":
        return None
    v = v.strip()
    if not HHMM_RE.match(v):
        raise ValueError("Use HH:MM, for example 08:30")
    return v


def _check_scheduled_days(v):
    """Weekdays use JavaScript's Sunday=0 through Saturday=6 numbering."""
    if v is None:
        return v
    if not v or any(day < 0 or day > 6 for day in v):
        raise ValueError("Select at least one weekday from 0 to 6")
    if len(set(v)) != len(v):
        raise ValueError("Weekdays must not contain duplicates")
    return sorted(v)


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
    reminder_time: Optional[str] = None  # "HH:MM" in the user's timezone, null = no reminder
    scheduled_days: list[int] = Field(default_factory=lambda: list(range(7)), min_length=1, max_length=7)

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

    @field_validator("reminder_time")
    @classmethod
    def check_reminder(cls, v):
        return _check_reminder(v)

    @field_validator("scheduled_days")
    @classmethod
    def check_scheduled_days(cls, v):
        return _check_scheduled_days(v)


class HabitUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = None
    reminder_time: Optional[str] = None
    scheduled_days: Optional[list[int]] = Field(default=None, min_length=1, max_length=7)

    @field_validator("name")
    @classmethod
    def clean_name(cls, v):
        if v is None:
            return v
        v = v.strip()
        if not v:
            raise ValueError("Name cannot be empty")
        return v

    @field_validator("reminder_time")
    @classmethod
    def check_reminder(cls, v):
        return _check_reminder(v)

    @field_validator("scheduled_days")
    @classmethod
    def check_scheduled_days(cls, v):
        return _check_scheduled_days(v)


class HabitOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str
    created_on: date
    archived_at: Optional[datetime] = None
    reminder_time: Optional[str] = None
    scheduled_days: Optional[list[int]] = None


# ---------- export / import ----------

class ExportHabit(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = ""
    created_on: date
    scheduled_days: list[int] = Field(default_factory=lambda: list(range(7)), min_length=1, max_length=7)
    completed_dates: list[date] = Field(default_factory=list, max_length=4000)

    @field_validator("created_on", mode="before")
    @classmethod
    def trim_created_on(cls, v):
        return _trim_date(v)

    @field_validator("scheduled_days")
    @classmethod
    def check_scheduled_days(cls, v):
        return _check_scheduled_days(v)


class ExportOut(BaseModel):
    version: int = 1
    exported_at: datetime
    habits: list[ExportHabit]


class ImportIn(BaseModel):
    habits: list[ExportHabit] = Field(max_length=200)


class ImportOut(BaseModel):
    habits_created: int
    completions_created: int


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


# ---------- push notifications ----------

class PushKeys(BaseModel):
    p256dh: str = Field(min_length=1, max_length=255)
    auth: str = Field(min_length=1, max_length=255)


class PushSubscribeIn(BaseModel):
    endpoint: str = Field(max_length=1024)
    keys: PushKeys

    @field_validator("endpoint")
    @classmethod
    def https_only(cls, v):
        if not v.startswith("https://"):
            raise ValueError("Push endpoint must be an https URL")
        return v


class PushUnsubscribeIn(BaseModel):
    endpoint: str = Field(max_length=1024)


class VapidKeyOut(BaseModel):
    public_key: str


class PushStatusOut(BaseModel):
    enabled: bool
    subscriptions: int
