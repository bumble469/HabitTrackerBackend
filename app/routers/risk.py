from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import require_ai
from app.models import User
from app.schemas import RiskHistoryOut, RiskOut
from app.services import risk_service
from ml.predict import ModelNotReady

router = APIRouter(prefix="/api", tags=["risk"])


@router.get("/risk", response_model=list[RiskOut])
def my_risk(
    today: Optional[date] = None, user: User = Depends(require_ai), db: Session = Depends(get_db)
):
    """Risk for every active habit, computed from the database. ?today=YYYY-MM-DD overrides the date."""
    try:
        return risk_service.compute_risk(db, user, today)
    except ModelNotReady as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@router.get("/habits/{habit_id}/risk/history", response_model=list[RiskHistoryOut])
def risk_history(
    habit_id: str,
    start: Optional[date] = None,
    end: Optional[date] = None,
    user: User = Depends(require_ai),
    db: Session = Depends(get_db),
):
    """Saved daily risk snapshots for one habit, oldest first (for a trend chart)."""
    return risk_service.risk_history(db, user, habit_id, start, end)
