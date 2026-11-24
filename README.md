# Habit Tracker Backend

FastAPI backend for the Habit Tracker project. Two separate parts in one repo:

- **`app/`** is the normal CRUD API: habits and completions, stored in Postgres.
- **`ml/`** is the machine-learning part: training, prediction and one stateless endpoint, `POST /api/risk`. It does not touch the database.

The React frontend lives in a separate repo.

## Structure

```
app/                  CRUD API
  main.py             app, CORS, routers, /health
  config.py  db.py  models.py  schemas.py  deps.py
  routers/            habits.py, completions.py
  services/data.py    data retrieval helpers
ml/                   machine learning
  data/               training CSV/Excel file lives here (see ml/data/README.md)
  generate_data.py    step 1: creates ml/data/habit_logs.csv (synthetic data)
  features.py         turns check-in dates into the 8 model features
  train.py            step 2: reads ml/data, trains, writes model.joblib + metrics.json
  predict.py          loads the model, scores habits, explains the score
  api.py, schemas.py  POST /api/risk
tests/                pytest
```

## Setup (Windows)

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
copy .env.example .env
```

### Generate the data, then train (two separate steps)
```
python -m ml.generate_data
python -m ml.train
```
1. `generate_data` writes `ml/data/habit_logs.csv` and prints a summary (completion rate, dropout share, habits per profile). Check it before training. You can skip this step and put your own `.csv` or `.xlsx` in `ml/data/` instead (columns in `ml/data/README.md`).
2. `train` only reads the file in `ml/data/`. It never generates data. It creates `ml/model.joblib` and `ml/metrics.json` (accuracy, F1, ROC-AUC against the "always predict done" baseline). Add `--compare` to also test gradient boosting.

### Run the API
```
uvicorn app.main:app --reload
```
Open http://localhost:8000/docs to try every endpoint. Run tests with `pytest`.

- **Database:** leave `DATABASE_URL` empty to use a local SQLite file, or paste your Neon connection string. Tables are created on startup.

## Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| GET | /health | status and whether the model is loaded |
| POST/GET | /api/habits | create / list habits |
| GET/PATCH/DELETE | /api/habits/{id} | read / update / delete a habit |
| GET | /api/completions | `{habitId: [dates]}` for the user |
| GET | /api/habits/{id}/completions | dates for one habit (`start`, `end` optional) |
| PUT/DELETE | /api/habits/{id}/completions/{YYYY-MM-DD} | check in / undo |
| POST | /api/risk | post `{today, habits, completions}`, get risk per habit (no database needed) |

CRUD endpoints need an `X-User-Id` header (any id the frontend generates once per browser).
Send dates as local `YYYY-MM-DD` (e.g. `toLocaleDateString('en-CA')`), not `toISOString()`, to avoid timezone shifts.

## Deployment

- **Render (web service):** build `pip install -r requirements.txt`, start `uvicorn app.main:app --host 0.0.0.0 --port $PORT`. Set `DATABASE_URL` and `CORS_ORIGINS` (your frontend URL).
- Commit `ml/model.joblib`, and pin the scikit-learn, numpy and joblib versions in `requirements.txt` to match the ones you trained with.
- Render's free tier sleeps when idle, so open `/health` a minute before a demo.
