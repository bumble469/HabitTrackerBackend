import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import models 
from app.config import (
    CORS_ALLOW_CREDENTIALS,
    CORS_ALLOW_HEADERS,
    CORS_ALLOW_METHODS,
    CORS_ORIGIN_REGEX,
    CORS_ORIGINS,
    JWT_SECRET_IS_DEFAULT,
    PUSH_SCHEDULER_ENABLED,
)
from app.db import Base, engine
from app.routers import auth, completions, habits, push, transfer
from app.routers import risk as risk_routes
from app.services import push_service, reminder_scheduler
from ml.api import router as stateless_risk_router 
from ml.predict import model_available


logger = logging.getLogger("habit-tracker")


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"[cors] origins={CORS_ORIGINS} regex={CORS_ORIGIN_REGEX}")
    if not CORS_ORIGINS and not CORS_ORIGIN_REGEX:
        print("[warn] CORS_ORIGINS is not set: browsers will block every cross-origin request")
    if JWT_SECRET_IS_DEFAULT:
        print("[warn] JWT_SECRET is not set: using an insecure development secret")
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as exc:  # POST /api/risk needs no database, so keep serving it
        print(f"[warn] database init failed: {exc}")

    scheduler = None
    if PUSH_SCHEDULER_ENABLED:
        if push_service.push_enabled():
            scheduler = reminder_scheduler.start_scheduler()
        else:
            print("[reminders] scheduler not started: VAPID keys are not configured")
    else:
        print("[reminders] scheduler not started: PUSH_SCHEDULER_ENABLED is false")
    yield
    if scheduler:
        scheduler.shutdown(wait=False)


app = FastAPI(title="Habit Tracker Backend", version="0.3.0", lifespan=lifespan)

# Added BEFORE CORSMiddleware so it sits inside it. Unhandled errors are turned into a normal
# JSON 500 here, which then passes through CORSMiddleware and gets CORS headers. Without this the
# browser shows a 500 as a "CORS error" and hides the real problem.
@app.middleware("http")
async def json_500_inside_cors(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception:
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse({"detail": "Internal server error"}, status_code=500)


app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_origin_regex=CORS_ORIGIN_REGEX,
    allow_credentials=CORS_ALLOW_CREDENTIALS,
    allow_methods=CORS_ALLOW_METHODS,
    allow_headers=CORS_ALLOW_HEADERS,
)

for router in (
    auth.router,
    habits.router,
    completions.router,
    transfer.router,
    risk_routes.router,
    push.router,
    stateless_risk_router,
):
    app.include_router(router)


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok", "model_loaded": model_available()}
