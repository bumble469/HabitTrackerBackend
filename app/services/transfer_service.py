"""Export and import of a user's account habits and completion history."""
from datetime import timedelta

from sqlalchemy.orm import Session

from app.models import Completion, Habit, User, utcnow
from app.schemas import ImportIn
from app.services.data import load_user_data, today_for


def export_user_data(db: Session, user: User) -> dict:
    habits, completions = load_user_data(db, user.id)
    return {
        "version": 1,
        "exported_at": utcnow(),
        "habits": [
            {
                "name": h.name,
                "description": h.description,
                "created_on": h.created_on,
                "scheduled_days": h.scheduled_days or list(range(7)),
                "completed_dates": sorted(completions.get(h.id, set())),
            }
            for h in habits
            if not h.is_demo
        ],
    }


def import_user_data(db: Session, user: User, body: ImportIn) -> dict:
    """Create new habits (new ids) with their check-ins. Future dates are skipped."""
    latest = today_for(user) + timedelta(days=1)
    habits_created = completions_created = 0
    for item in body.habits:
        habit = Habit(
            user_id=user.id,
            name=item.name.strip() or "Untitled habit",
            description=item.description,
            created_on=item.created_on,
            scheduled_days=item.scheduled_days,
        )
        db.add(habit)
        db.flush()  # assigns habit.id
        for day in sorted(set(item.completed_dates)):
            if day > latest:
                continue
            db.add(Completion(habit_id=habit.id, day=day))
            completions_created += 1
        habits_created += 1
    db.commit()
    return {"habits_created": habits_created, "completions_created": completions_created}
