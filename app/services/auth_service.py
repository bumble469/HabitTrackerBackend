"""Register, log in and update the account."""
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import User
from app.schemas import RegisterIn, UserUpdate
from app.security import hash_password, verify_password

# Checked when the email is unknown, so a wrong email and a wrong password take the same time.
_DUMMY_HASH = hash_password("not-a-real-password")


def register_user(db: Session, body: RegisterIn) -> User:
    if db.scalar(select(User.id).where(User.email == body.email)) is not None:
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    user = User(
        email=body.email,
        password_hash=hash_password(body.password),
        display_name=body.display_name.strip(),
        timezone=body.timezone,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:  # two sign-ups with the same email at the same moment
        db.rollback()
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    db.refresh(user)
    return user


def authenticate(db: Session, email: str, password: str) -> User:
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        verify_password(password, _DUMMY_HASH)
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    if not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    return user


def update_user(db: Session, user: User, body: UserUpdate) -> User:
    data = body.model_dump(exclude_unset=True)
    if data.get("display_name") is not None:
        user.display_name = data["display_name"].strip()
    if data.get("timezone") is not None:
        user.timezone = data["timezone"]
    if data.get("ai_enabled") is not None:
        user.ai_enabled = data["ai_enabled"]
    db.commit()
    db.refresh(user)
    return user
