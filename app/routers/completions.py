from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import User
from app.services import completion_service

router = APIRouter(prefix="/api", tags=["completions"])


@router.get("/completions", response_model=dict[str, list[date]])
def all_completions(
    start: Optional[date] = None,
    end: Optional[date] = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """{habitId: [dates]} for every active habit of the user."""
    return completion_service.completions_map(db, user, start, end)


@router.get("/habits/{habit_id}/completions", response_model=list[date])
def habit_completions(
    habit_id: str,
    start: Optional[date] = None,
    end: Optional[date] = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return completion_service.list_days(db, user, habit_id, start, end)


@router.put("/habits/{habit_id}/completions/{day}", status_code=204)
def check_in(habit_id: str, day: date, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Mark a day as done. Safe to call twice."""
    completion_service.check_in(db, user, habit_id, day)


@router.delete("/habits/{habit_id}/completions/{day}", status_code=204)
def undo_check_in(
    habit_id: str, day: date, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    completion_service.undo_check_in(db, user, habit_id, day)
