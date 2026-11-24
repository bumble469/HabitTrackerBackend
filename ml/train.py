"""Train the dropout-risk model from a CSV or Excel file in ml/data/.

Run from the repo root:
    python -m ml.train                       # uses the single file in ml/data/
    python -m ml.train --data ml/data/x.csv  # or name the file
    python -m ml.train --compare             # also report gradient boosting (slower)

Expected columns (see ml/data/README.md): habit_id, created_on, completed_on
Optional column: observed_until
"""
import argparse
import csv
import json
from datetime import date, datetime, timedelta
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from ml.features import FEATURES, MIN_HISTORY_DAYS, build_features

OUT_DIR = Path(__file__).resolve().parent
DATA_DIR = OUT_DIR / "data"
WARMUP_DAYS = MIN_HISTORY_DAYS 
HORIZON_DAYS = 3 

def find_data_file(arg) -> Path:
    if arg:
        path = Path(arg)
        if not path.exists():
            raise SystemExit(f"File not found: {path}")
        return path
    files = sorted(
        p for p in DATA_DIR.glob("*")
        if p.suffix.lower() in {".csv", ".xlsx"} and not p.name.startswith("~$")
    )
    if not files:
        raise SystemExit("No data file found. Put a .csv or .xlsx file in ml/data/ (see ml/data/README.md).")
    if len(files) > 1:
        raise SystemExit("Several data files in ml/data/. Keep one, or pass --data <file>.")
    return files[0]


def read_rows(path: Path) -> list[dict]:
    if path.suffix.lower() == ".csv":
        with open(path, newline="", encoding="utf-8-sig") as f:
            return [{(k or "").strip(): v for k, v in row.items()} for row in csv.DictReader(f)]
    from openpyxl import load_workbook  # only needed for Excel files (in requirements-dev.txt)

    sheet = load_workbook(path, read_only=True, data_only=True).active
    rows = sheet.iter_rows(values_only=True)
    header = [str(h).strip() if h is not None else "" for h in next(rows)]
    return [dict(zip(header, r)) for r in rows if any(c is not None for c in r)]


def to_date(value, field: str, row_no: int) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value).strip()[:10])
    except ValueError:
        raise SystemExit(f"Row {row_no}: column '{field}' must be a date like 2026-11-14, got {value!r}")


def is_blank(value) -> bool:
    return value is None or str(value).strip() == ""


def load_habits(path: Path) -> dict:
    """Return {habit_id: {"created": date, "done": set of dates, "until": date}}."""
    rows = read_rows(path)
    if not rows:
        raise SystemExit("The data file is empty.")
    missing = {"habit_id", "created_on", "completed_on"} - set(rows[0].keys())
    if missing:
        raise SystemExit(f"Missing column(s): {', '.join(sorted(missing))}. See ml/data/README.md.")

    habits: dict = {}
    all_dates: list[date] = []
    for n, row in enumerate(rows, start=2):  # row 1 is the header
        habit_id = str(row["habit_id"]).strip()
        created = to_date(row["created_on"], "created_on", n)
        habit = habits.setdefault(habit_id, {"created": created, "done": set(), "until": None})
        all_dates.append(created)
        if not is_blank(row["completed_on"]):  # blank = a habit row with no completion
            day = to_date(row["completed_on"], "completed_on", n)
            habit["done"].add(day)
            all_dates.append(day)
        if not is_blank(row.get("observed_until")):
            habit["until"] = to_date(row["observed_until"], "observed_until", n)
            all_dates.append(habit["until"])

    # Without observed_until, a habit is assumed to be tracked until the last date in the file.
    dataset_end = max(all_dates)
    for habit in habits.values():
        habit["until"] = habit["until"] or dataset_end
    return habits


# ---------- building the training table ----------

def build_dataset(habits: dict):
    """One row per habit per day. Label = 1 if the habit is missed on ALL of the next 3 days."""
    X, y, groups = [], [], []
    skipped = 0
    for g, habit in enumerate(habits.values()):
        created, done, until = habit["created"], habit["done"], habit["until"]
        day = created + timedelta(days=WARMUP_DAYS)
        last = until - timedelta(days=HORIZON_DAYS)  # the 3 future days must be inside the data
        if day > last:
            skipped += 1
            continue
        while day <= last:
            f = build_features(done, created, day)
            future = [day + timedelta(days=k) for k in range(1, HORIZON_DAYS + 1)]
            X.append([f[k] for k in FEATURES])
            y.append(int(not any(d in done for d in future)))
            groups.append(g)
            day += timedelta(days=1)
    return np.array(X), np.array(y), np.array(groups), skipped


# ---------- training and evaluation ----------

def scores(y_true, proba) -> dict:
    pred = (proba >= 0.5).astype(int)
    return {
        "accuracy": round(float(accuracy_score(y_true, pred)), 4),
        "f1": round(float(f1_score(y_true, pred, zero_division=0)), 4),
        "roc_auc": round(float(roc_auc_score(y_true, proba)), 4),
    }


def main(data_arg, compare: bool) -> None:
    path = find_data_file(data_arg)
    habits = load_habits(path)
    X, y, groups, skipped = build_dataset(habits)

    n_habits = len(set(groups.tolist()))
    if n_habits < 10:
        raise SystemExit(f"Only {n_habits} usable habits. Need at least 10 (more is better), each with 17+ days of data.")
    if len(set(y.tolist())) < 2:
        raise SystemExit("The data has only one outcome (all dropouts or none). Check the data.")

    # Split by habit, not by row, so consecutive days of one habit never leak into both sets.
    train_idx, test_idx = next(GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42).split(X, y, groups))

    model = Pipeline(
        [
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(class_weight="balanced", max_iter=1000)),
        ]
    )
    model.fit(X[train_idx], y[train_idx])

    results = {
        "logistic_regression": scores(y[test_idx], model.predict_proba(X[test_idx])[:, 1]),
        # Baseline: "always predict done" = never flag anything as at risk.
        "baseline_always_done": {
            "accuracy": round(float(accuracy_score(y[test_idx], np.zeros_like(y[test_idx]))), 4),
            "f1": 0.0,
            "roc_auc": 0.5,
        },
        "data": {
            "file": path.name,
            "habits_used": n_habits,
            "habits_skipped_too_short": skipped,
            "train_rows": int(len(train_idx)),
            "test_rows": int(len(test_idx)),
            "at_risk_rate": round(float(y.mean()), 4),
        },
    }

    if compare:
        gb = GradientBoostingClassifier(random_state=42).fit(X[train_idx], y[train_idx])
        results["gradient_boosting"] = scores(y[test_idx], gb.predict_proba(X[test_idx])[:, 1])

    joblib.dump(model, OUT_DIR / "model.joblib")
    (OUT_DIR / "metrics.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps(results, indent=2))
    print(f"\nSaved {OUT_DIR / 'model.joblib'} and metrics.json")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", help="path to the CSV/Excel file (default: the single file in ml/data/)")
    parser.add_argument("--compare", action="store_true", help="also train gradient boosting")
    args = parser.parse_args()
    main(args.data, args.compare)
