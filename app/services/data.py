"""Shared lookups used by the services."""
from collections import defaultdict
from datetime import date, datetime, timezone
from typing import Optional
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Completion, Habit, User


def today_for(user: User, override: Optional[date] = None) -> date:
    """The user's local 'today'. The frontend may send its own date instead (?today=...)."""
    if override is not None:
        return override
    try:
        return datetime.now(ZoneInfo(user.timezone)).date()
    except Exception:  # unknown timezone name, or no timezone database installed
        return datetime.now(timezone.utc).date()


def get_owned_habit(db: Session, habit_id: str, user_id: str, include_archived: bool = False) -> Habit:
    habit = db.get(Habit, habit_id)
    if habit is None or habit.user_id != user_id:
        raise HTTPException(status_code=404, detail="Habit not found")
    if habit.archived_at is not None and not include_archived:
        raise HTTPException(status_code=404, detail="Habit not found")
    return habit


def load_user_data(db: Session, user_id: str, include_archived: bool = False):
    """Return (habits, {habit_id: set of completed dates}) for one user."""
    query = select(Habit).where(Habit.user_id == user_id, Habit.is_demo.is_(False))
    if not include_archived:
        query = query.where(Habit.archived_at.is_(None))
    habits = list(db.scalars(query.order_by(Habit.created_on, Habit.id)))
    completions: dict[str, set[date]] = defaultdict(set)
    if habits:
        rows = db.execute(
            select(Completion.habit_id, Completion.day).where(
                Completion.habit_id.in_([h.id for h in habits])
            )
        )
        for habit_id, day in rows:
            completions[habit_id].add(day)
    return habits, dict(completions)
