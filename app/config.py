import os

from dotenv import load_dotenv

load_dotenv()

_db_url = os.getenv("DATABASE_URL", "").strip() or "sqlite:///./dev.db"
for prefix in ("postgres://", "postgresql://"):
    if _db_url.startswith(prefix):
        _db_url = "postgresql+psycopg2://" + _db_url[len(prefix):]
        break
DATABASE_URL = _db_url

CORS_ORIGINS = [
    o.strip()
    for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    if o.strip()
]

JWT_SECRET = os.getenv("JWT_SECRET", "").strip()
JWT_SECRET_IS_DEFAULT = not JWT_SECRET
if JWT_SECRET_IS_DEFAULT:
    if not DATABASE_URL.startswith("sqlite"):
        raise RuntimeError(
            "JWT_SECRET is not set. Add it to .env (or your host's environment settings). "
            'Generate one with: python -c "import secrets; print(secrets.token_urlsafe(48))"'
        )
    JWT_SECRET = "dev-only-secret-change-me-before-deploying-0123456789"
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "10080"))
VAPID_PUBLIC_KEY = os.getenv("VAPID_PUBLIC_KEY", "").strip()
VAPID_PRIVATE_KEY = os.getenv("VAPID_PRIVATE_KEY", "").strip()
VAPID_SUBJECT = os.getenv("VAPID_SUBJECT", "mailto:admin@example.com").strip()
PUSH_SCHEDULER_ENABLED = os.getenv("PUSH_SCHEDULER_ENABLED", "false").lower() == "true"