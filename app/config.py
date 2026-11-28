import os

from dotenv import load_dotenv

load_dotenv()

_db_url = os.getenv("DATABASE_URL", "").strip() or "sqlite:///./dev.db"
for prefix in ("postgres://", "postgresql://"):
    if _db_url.startswith(prefix):
        _db_url = "postgresql+psycopg2://" + _db_url[len(prefix):]
        break
DATABASE_URL = _db_url

def _csv_env(name: str, default: str = "") -> list[str]:
    """Comma-separated env var -> list. Tolerates spaces, quotes and trailing slashes."""
    return [
        item.strip().strip("\"'").rstrip("/")
        for item in os.getenv(name, default).split(",")
        if item.strip().strip("\"'")
    ]


# Everything CORS-related comes from the environment (no hardcoded origins).
# CORS_ORIGINS=https://app.vercel.app,https://www.example.com,http://localhost:5173
CORS_ORIGINS = _csv_env("CORS_ORIGINS")
# Optional, e.g. to allow Vercel preview deploys: https://.*\.vercel\.app
CORS_ORIGIN_REGEX = os.getenv("CORS_ORIGIN_REGEX", "").strip().strip("\"'") or None
CORS_ALLOW_METHODS = _csv_env("CORS_ALLOW_METHODS", "*")
CORS_ALLOW_HEADERS = _csv_env("CORS_ALLOW_HEADERS", "*")
CORS_ALLOW_CREDENTIALS = os.getenv("CORS_ALLOW_CREDENTIALS", "false").strip().lower() == "true"

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