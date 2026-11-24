"""'Load demo data': four synthetic habits with up to 90 days of history (REQ-05)."""
import random
from datetime import timedelta

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Completion, Habit, User
from app.services.data import today_for

# (name, description, days of history, chance of a check-in on day i of the history)
PROFILES = [
    ("Morning walk", "Demo: a habit you keep up", 90, lambda i, d: 0.88),
    ("Read 20 pages", "Demo: a habit that has been slipping", 90, lambda i, d: 0.85 if i < 62 else 0.1),
    ("Gym", "Demo: weekday habit, skipped at weekends", 90, lambda i, d: 0.1 if d.weekday() >= 5 else 0.8),
    ("Learn Spanish", "Demo: a habit started a week ago", 7, lambda i, d: 0.7),  # too new to score
]


def load_demo_data(db: Session, user: User) -> dict:
    already = db.scalar(
        select(Habit.id).where(Habit.user_id == user.id, Habit.is_demo.is_(True)).limit(1)
    )
    if already is not None:
        raise HTTPException(status_code=409, detail="Demo data is already loaded")

    rng = random.Random()
    today = today_for(user)
    habits_created = completions_created = 0
    for name, description, age_days, chance in PROFILES:
        start = today - timedelta(days=age_days)
        habit = Habit(
            user_id=user.id, name=name, description=description, created_on=start, is_demo=True
        )
        db.add(habit)
        db.flush()  # assigns habit.id
        for i in range(age_days):  # from the start date up to yesterday
            day = start + timedelta(days=i)
            if rng.random() < chance(i, day):
                db.add(Completion(habit_id=habit.id, day=day))
                completions_created += 1
        habits_created += 1
    db.commit()
    return {"habits_created": habits_created, "completions_created": completions_created}


def remove_demo_data(db: Session, user: User) -> dict:
    habits = list(db.scalars(select(Habit).where(Habit.user_id == user.id, Habit.is_demo.is_(True))))
    for habit in habits:
        db.delete(habit)  # their check-ins and risk history go with them
    db.commit()
    return {"habits_removed": len(habits)}
