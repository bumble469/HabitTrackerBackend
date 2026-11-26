from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.config import VAPID_PUBLIC_KEY
from app.db import get_db
from app.deps import get_current_user
from app.models import User
from app.schemas import PushStatusOut, PushSubscribeIn, PushUnsubscribeIn, VapidKeyOut
from app.services import push_service

router = APIRouter(prefix="/api/push", tags=["push"])


@router.get("/public-key", response_model=VapidKeyOut)
def public_key():
    if not push_service.push_enabled():
        raise HTTPException(status_code=503, detail="Push notifications are not configured")
    return VapidKeyOut(public_key=VAPID_PUBLIC_KEY)


@router.post("/subscribe", status_code=201)
def subscribe(
    body: PushSubscribeIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    user_agent: Optional[str] = Header(default=None),
):
    push_service.save_subscription(db, user, body, user_agent)
    return {"ok": True}


@router.post("/unsubscribe", status_code=204)
def unsubscribe(body: PushUnsubscribeIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    push_service.remove_subscription(db, user, body.endpoint)


@router.get("/status", response_model=PushStatusOut)
def status(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    n = push_service.count_active(db, user)
    return PushStatusOut(enabled=n > 0, subscriptions=n)


@router.post("/test")
def send_test(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    sent = push_service.send_to_user(
        db, user.id, {"title": "Habit Tracker", "body": "Test notification", "url": "/"}
    )
    return {"sent": sent}