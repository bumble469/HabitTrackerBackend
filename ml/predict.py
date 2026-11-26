from datetime import date, timedelta
from pathlib import Path

import joblib
import numpy as np

from ml.features import FEATURES, MIN_HISTORY_DAYS, build_features

MODEL_PATH = Path(__file__).resolve().parent / "model.joblib"

REASON_TEXT = {
    "rate_7": "Low completion over the last 7 days",
    "rate_14": "Low completion over the last 2 weeks",
    "rate_30": "Low completion over the last month",
    "trend": "Completion is dropping compared with the week before",
    "streak": "The streak has been broken",
    "days_since_last": "It has been several days since the last completion",
    "age_days": "The habit is still new",
    "next_weekend": "The coming days fall on a weekend",
}

_model = None


class ModelNotReady(Exception):
    pass


def model_available() -> bool:
    return MODEL_PATH.exists()


def get_model():
    global _model
    if _model is None:
        if not MODEL_PATH.exists():
            raise ModelNotReady("Model file not found. Train it first with: python -m ml.train")
        _model = joblib.load(MODEL_PATH)
    return _model


def level_for(p: float) -> str:
    return "high" if p >= 0.6 else "medium" if p >= 0.3 else "low"


def explain(model, features: dict, top_n: int = 2) -> list[str]:
    scaler, clf = model.named_steps["scaler"], model.named_steps["clf"]
    z = scaler.transform([[features[k] for k in FEATURES]])[0]
    contrib = clf.coef_[0] * z
    order = np.argsort(-contrib)[:top_n]

    reasons = []
    for i in order:
        if contrib[i] <= 0:
            continue
        name = FEATURES[i]
        if name == "age_days":
            reasons.append(
                "The habit is still new" if z[i] < 0
                else "Habits in the training data tended to fade as they got older"
            )
        else:
            reasons.append(REASON_TEXT[name])
    return reasons


def score_habits(habits, completions: dict, today: date) -> list[dict]:
    """habits: (habit_id, created_on[, scheduled_days]) tuples; completions map ids to dates.

    Features are computed as of yesterday because today may still be incomplete.
    """
    as_of = today - timedelta(days=1)
    out = []
    model = None
    for habit_data in habits:
        habit_id, created_on = habit_data[:2]
        scheduled_days = habit_data[2] if len(habit_data) > 2 else None
        if scheduled_days and set(scheduled_days) != set(range(7)):
            out.append(
                {
                    "habit_id": habit_id,
                    "risk": None,
                    "level": "unsupported_schedule",
                    "reasons": ["Risk estimates are not calibrated for custom schedules yet"],
                }
            )
            continue
        if (as_of - created_on).days < MIN_HISTORY_DAYS:
            out.append(
                {
                    "habit_id": habit_id,
                    "risk": None,
                    "level": "not_enough_data",
                    "reasons": ["Habit is too new to score yet"],
                }
            )
            continue
        if model is None:
            model = get_model()
        f = build_features(completions.get(habit_id, set()), created_on, as_of)
        p = float(model.predict_proba([[f[k] for k in FEATURES]])[0, 1])
        out.append(
            {
                "habit_id": habit_id,
                "risk": round(p, 2),
                "level": level_for(p),
                "reasons": explain(model, f) if level_for(p) != "low" else [],
            }
        )
    return out
