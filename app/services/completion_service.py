"""Check-ins: one Completion row per habit per done day."""
from datetime import date, timedelta
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Completion, Habit, User
from app.services.data import get_owned_habit, today_for


def completions_map(
    db: Session, user: User, start: Optional[date] = None, end: Optional[date] = None
) -> dict[str, list[date]]:
    """{habitId: [dates]} for every active habit, the same shape the frontend uses."""
    habit_ids = list(
        db.scalars(        select(Habit.id).where(
            Habit.user_id == user.id,
            Habit.archived_at.is_(None),
            Habit.is_demo.is_(False),
        ))
    )
    result: dict[str, list[date]] = {hid: [] for hid in habit_ids}
    if not habit_ids:
        return result
    query = select(Completion.habit_id, Completion.day).where(Completion.habit_id.in_(habit_ids))
    if start:
        query = query.where(Completion.day >= start)
    if end:
        query = query.where(Completion.day <= end)
    for habit_id, day in db.execute(query.order_by(Completion.day)):
        result[habit_id].append(day)
    return result


def list_days(
    db: Session, user: User, habit_id: str, start: Optional[date] = None, end: Optional[date] = None
) -> list[date]:
    habit = get_owned_habit(db, habit_id, user.id)
    query = select(Completion.day).where(Completion.habit_id == habit.id).order_by(Completion.day)
    if start:
        query = query.where(Completion.day >= start)
    if end:
        query = query.where(Completion.day <= end)
    return list(db.scalars(query))


def check_in(db: Session, user: User, habit_id: str, day: date) -> None:
    """Mark a day as done. Safe to call twice."""
    habit = get_owned_habit(db, habit_id, user.id)
    if day > today_for(user) + timedelta(days=1):  # one day of slack for timezone differences
        raise HTTPException(status_code=422, detail="Cannot check in for a future date")
    weekday = (day.weekday() + 1) % 7
    if habit.scheduled_days and weekday not in habit.scheduled_days:
        raise HTTPException(status_code=422, detail="This habit is not scheduled for that day")
    exists = db.scalar(select(Completion.id).where(Completion.habit_id == habit.id, Completion.day == day))
    if exists is None:
        db.add(Completion(habit_id=habit.id, day=day))
        try:
            db.commit()
        except IntegrityError:  # the same check-in arrived twice at the same moment
            db.rollback()


def undo_check_in(db: Session, user: User, habit_id: str, day: date) -> None:
    habit = get_owned_habit(db, habit_id, user.id)
    row = db.scalar(select(Completion).where(Completion.habit_id == habit.id, Completion.day == day))
    if row is not None:
        db.delete(row)
        db.commit()
