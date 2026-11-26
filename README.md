# Habit Tracker Backend

FastAPI backend for the Habit Tracker project. Users register and log in, their habits and check-ins are stored in Postgres (Neon), and a machine-learning model estimates which habits are at risk.

The React frontend lives in a separate repo.

## Structure

```
app/                    API
  main.py               app, CORS, routers, /health
  config.py  db.py  models.py  schemas.py  deps.py  security.py
  routers/              thin route files: auth, habits, completions, transfer, risk, push
  services/             the logic behind the routes (controllers)
    auth_service, habit_service, completion_service, transfer_service, demo_service, risk_service
    push_service        manages browser push subscriptions and notifications
    reminder_scheduler  sends scheduled habit reminders
ml/                     machine learning
  data/                 training CSV lives here (see ml/data/README.md)
  generate_data.py      step 1: creates ml/data/habit_logs.csv (synthetic data)
  features.py           turns check-in dates into the model features
  train.py              step 2: trains, writes model.joblib + metrics.json
  predict.py            loads the model, scores habits, explains the score
  api.py, schemas.py    stateless POST /api/risk
tests/                  pytest (uses an in-memory database)
```

## Setup (Windows)

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
```
Create a `.env` file in the backend root and add the settings you need from the table below. Never commit `.env`.

| Variable | Needed | What it is |
| --- | --- | --- |
| `DATABASE_URL` | no | Neon connection string. Empty uses a local SQLite file (`dev.db`). |
| `JWT_SECRET` | yes with Postgres | Signs login tokens. Generate: `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `CORS_ORIGINS` | no | Comma-separated frontend origins allowed to call the API (default `http://localhost:5173`). |
| `PUSH_SCHEDULER_ENABLED` | no | Set to `true` to run habit reminders; requires VAPID settings and an always-on backend instance. |
| `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY` | for push | Web Push application server keys. Keep the private key secret. |
| `VAPID_SUBJECT` | for push | Contact URI for Web Push, such as `mailto:you@example.com`. |

Tables are created on startup. `create_all` never changes an existing table. For an existing database, apply `migrations/001_add_habit_scheduled_days.sql` once before starting the updated backend. Existing habits remain scheduled every day.

### Run
```
uvicorn app.main:app --reload
```
Open http://localhost:8000/docs to try every endpoint (use the Authorize button with the token from register or login). Run the tests with `pytest`.

### Train the model (only if you change the data or features)
```
python -m ml.generate_data
python -m ml.train
```
`train` writes `ml/model.joblib` and `ml/metrics.json` (accuracy, F1, ROC-AUC against an "always predict done" baseline, split by habit). Add `--compare` to also test gradient boosting. The data is synthetic, so the metrics show the model behaves sensibly, not how accurate it is on real users.

## Endpoints

All routes need `Authorization: Bearer <token>` except register, login, `/health` and `POST /api/risk`. Dates are local `YYYY-MM-DD` (use `toLocaleDateString('en-CA')`, not `toISOString()`).

| Method | Path | Purpose |
| --- | --- | --- |
| POST | /api/auth/register | create account, returns token + user (send the browser timezone) |
| POST | /api/auth/login | returns token + user |
| GET/PATCH | /api/auth/me | read / update name, timezone, `ai_enabled` |
| POST/GET | /api/habits | create / list (`?include_archived=true`) |
| GET/PATCH/DELETE | /api/habits/{id} | read / update / archive (`?permanent=true` deletes for good) |
| POST | /api/habits/{id}/restore | un-archive |
| GET | /api/completions | `{habitId: [dates]}` for all active habits (`start`, `end` optional) |
| GET | /api/habits/{id}/completions | dates of one habit |
| PUT/DELETE | /api/habits/{id}/completions/{date} | check in / undo |
| GET | /api/risk | ML risk for every habit, from the database (`?today=` optional). Needs AI on. |
| GET | /api/habits/{id}/risk/history | saved daily risk snapshots |
| POST | /api/risk | stateless: post `{today, habits, completions}`, no login or database |
| GET | /api/push/public-key | public VAPID key for browser subscription |
| POST | /api/push/subscribe, POST /api/push/unsubscribe | manage browser push subscription |
| GET | /api/push/status | view push subscription status |
| POST | /api/push/test | send a test notification |
| GET | /api/export, POST /api/import | move habits in and out as JSON |
| GET | /health | status and whether the model is loaded |

## Deployment

- **Render (web service):** build `pip install -r requirements.txt`, start `uvicorn app.main:app --host 0.0.0.0 --port $PORT`. Set `DATABASE_URL`, `JWT_SECRET`, `CORS_ORIGINS` (your frontend URL), and the VAPID settings if push notifications are enabled.
- `ml/model.joblib` is committed on purpose. Keep the scikit-learn, numpy and joblib versions in `requirements.txt` the same as the ones used to train it.
- Render's free tier sleeps when idle, so open `/health` a minute before a demo.
