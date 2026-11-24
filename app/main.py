from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import models  # noqa: F401  (registers tables with Base)
from app.config import CORS_ORIGINS, JWT_SECRET_IS_DEFAULT
from app.db import Base, engine
from app.routers import auth, coach, completions, habits, transfer
from app.routers import risk as risk_routes
from ml.api import router as stateless_risk_router  # POST /api/risk, no login or database
from ml.predict import model_available


@asynccontextmanager
async def lifespan(app: FastAPI):
    if JWT_SECRET_IS_DEFAULT:
        print("[warn] JWT_SECRET is not set: using an insecure development secret")
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as exc:  # POST /api/risk needs no database, so keep serving it
        print(f"[warn] database init failed: {exc}")
    yield


app = FastAPI(title="Habit Tracker Backend", version="0.3.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

for router in (
    auth.router,
    habits.router,
    completions.router,
    transfer.router,
    risk_routes.router,
    coach.router,
    stateless_risk_router,
):
    app.include_router(router)


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok", "model_loaded": model_available()}
