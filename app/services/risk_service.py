"""Risk scores computed from the database, with a saved snapshot per habit per day."""
from datetime import date, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import RiskPrediction, User
from app.services.data import get_owned_habit, load_user_data, today_for
from ml.predict import MODEL_PATH, score_habits  # score_habits raises ModelNotReady if untrained


def _model_version() -> str:
    try:
        return f"model-{int(MODEL_PATH.stat().st_mtime)}"
    except OSError:
        return ""


def compute_risk(db: Session, user: User, today: Optional[date] = None) -> list[dict]:
    habits, completions = load_user_data(db, user.id)
    if not habits:
        return []
    t = today_for(user, today)
    as_of = t - timedelta(days=1)  # today may still be incomplete
    items = score_habits(
        [(h.id, h.created_on, h.scheduled_days) for h in habits], completions, t
    )

    version = _model_version()
    for item in items:
        row = db.scalar(
            select(RiskPrediction).where(
                RiskPrediction.habit_id == item["habit_id"], RiskPrediction.as_of == as_of
            )
        )
        if row is None:
            row = RiskPrediction(habit_id=item["habit_id"], as_of=as_of)
            db.add(row)
        row.risk = item["risk"]
        row.level = item["level"]
        row.reasons = item["reasons"]
        row.model_version = version
        item["as_of"] = as_of
    db.commit()
    return items


def risk_history(
    db: Session, user: User, habit_id: str, start: Optional[date] = None, end: Optional[date] = None
) -> list[RiskPrediction]:
    habit = get_owned_habit(db, habit_id, user.id, include_archived=True)
    query = (
        select(RiskPrediction)
        .where(RiskPrediction.habit_id == habit.id)
        .order_by(RiskPrediction.as_of)
    )
    if start:
        query = query.where(RiskPrediction.as_of >= start)
    if end:
        query = query.where(RiskPrediction.as_of <= end)
    return list(db.scalars(query))
