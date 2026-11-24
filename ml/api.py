from datetime import date

from fastapi import APIRouter, HTTPException

from ml.predict import ModelNotReady, score_habits
from ml.schemas import RiskItem, RiskRequest

router = APIRouter(prefix="/api", tags=["risk"])


@router.post("/risk", response_model=list[RiskItem])
def risk(req: RiskRequest):
    """Stateless: the caller posts its habits and completions, and gets a risk per habit.

    No database is involved, so the ML part works without the CRUD part.
    """
    today = req.today or date.today()
    habits = [(h.id, h.created_on) for h in req.habits]
    completions = {k: set(v) for k, v in req.completions.items()}
    try:
        return score_habits(habits, completions, today)
    except ModelNotReady as exc:
        raise HTTPException(status_code=503, detail=str(exc))
