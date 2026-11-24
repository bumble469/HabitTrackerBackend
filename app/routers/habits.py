from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import User
from app.schemas import HabitCreate, HabitOut, HabitUpdate
from app.services import habit_service

router = APIRouter(prefix="/api/habits", tags=["habits"])


@router.post("", response_model=HabitOut, status_code=201)
def create_habit(body: HabitCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return habit_service.create_habit(db, user, body)


@router.get("", response_model=list[HabitOut])
def list_habits(
    include_archived: bool = False, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return habit_service.list_habits(db, user, include_archived)


@router.get("/{habit_id}", response_model=HabitOut)
def get_habit(habit_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return habit_service.get_habit(db, user, habit_id)


@router.patch("/{habit_id}", response_model=HabitOut)
def update_habit(
    habit_id: str, body: HabitUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return habit_service.update_habit(db, user, habit_id, body)


@router.delete("/{habit_id}", status_code=204)
def delete_habit(
    habit_id: str,
    permanent: bool = False,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Archives the habit (history kept). ?permanent=true deletes it and its history for good."""
    habit_service.delete_habit(db, user, habit_id, permanent)


@router.post("/{habit_id}/restore", response_model=HabitOut)
def restore_habit(habit_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return habit_service.restore_habit(db, user, habit_id)
