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

# Secret used to sign login tokens. Set a long random value in .env (and in Render):
#   python -c "import secrets; print(secrets.token_urlsafe(48))"
JWT_SECRET = os.getenv("JWT_SECRET", "").strip()
JWT_SECRET_IS_DEFAULT = not JWT_SECRET
if JWT_SECRET_IS_DEFAULT:
    JWT_SECRET = "dev-only-secret-change-me-before-deploying-0123456789"
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "10080"))  # 7 days
