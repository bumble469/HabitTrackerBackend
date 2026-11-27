"""Habit CRUD. 'Delete' archives the habit so its history is kept."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Habit, User, utcnow
from app.schemas import HabitCreate, HabitUpdate
from app.services.data import get_owned_habit, today_for


def create_habit(db: Session, user: User, body: HabitCreate) -> Habit:
    habit = Habit(
        user_id=user.id,
        name=body.name,
        description=body.description,
        created_on=body.created_on or today_for(user),
        reminder_time=body.reminder_time,
        scheduled_days=body.scheduled_days,
    )
    db.add(habit)
    db.commit()
    db.refresh(habit)
    return habit


def list_habits(db: Session, user: User, include_archived: bool = False) -> list[Habit]:
    query = select(Habit).where(Habit.user_id == user.id)
    if not include_archived:
        query = query.where(Habit.archived_at.is_(None))
    return list(db.scalars(query.order_by(Habit.created_on, Habit.id)))


def get_habit(db: Session, user: User, habit_id: str) -> Habit:
    return get_owned_habit(db, habit_id, user.id)


def update_habit(db: Session, user: User, habit_id: str, body: HabitUpdate) -> Habit:
    habit = get_owned_habit(db, habit_id, user.id)
    if body.name is not None:
        habit.name = body.name
    if body.description is not None:
        habit.description = body.description
    if "reminder_time" in body.model_fields_set:
        habit.reminder_time = body.reminder_time
    if "scheduled_days" in body.model_fields_set:
        habit.scheduled_days = body.scheduled_days
    db.commit()
    db.refresh(habit)
    return habit


def delete_habit(db: Session, user: User, habit_id: str, permanent: bool = False) -> None:
    """Archive by default (history kept). permanent=True removes the habit and all its history."""
    habit = get_owned_habit(db, habit_id, user.id, include_archived=permanent)
    if permanent:
        db.delete(habit)
    else:
        habit.archived_at = utcnow()
    db.commit()


def restore_habit(db: Session, user: User, habit_id: str) -> Habit:
    habit = get_owned_habit(db, habit_id, user.id, include_archived=True)
    habit.archived_at = None
    db.commit()
    db.refresh(habit)
    return habit
