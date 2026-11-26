import json
import logging
from typing import Optional

from pywebpush import WebPushException, webpush
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import VAPID_PRIVATE_KEY, VAPID_PUBLIC_KEY, VAPID_SUBJECT
from app.models import PushSubscription, User, utcnow
from app.schemas import PushSubscribeIn

log = logging.getLogger(__name__)


def push_enabled() -> bool:
    return bool(VAPID_PUBLIC_KEY and VAPID_PRIVATE_KEY)


def save_subscription(db: Session, user: User, body: PushSubscribeIn, user_agent: Optional[str]) -> PushSubscription:
    sub = db.scalar(select(PushSubscription).where(PushSubscription.endpoint == body.endpoint))
    if sub is None:
        sub = PushSubscription(endpoint=body.endpoint)
        db.add(sub)
    sub.user_id = user.id  
    sub.p256dh = body.keys.p256dh
    sub.auth = body.keys.auth
    sub.user_agent = (user_agent or "")[:255]
    sub.is_active = True
    db.commit()
    db.refresh(sub)
    return sub


def remove_subscription(db: Session, user: User, endpoint: str) -> None:
    sub = db.scalar(
        select(PushSubscription).where(
            PushSubscription.endpoint == endpoint, PushSubscription.user_id == user.id
        )
    )
    if sub is not None:
        db.delete(sub)
        db.commit()


def count_active(db: Session, user: User) -> int:
    return len(list(db.scalars(select(PushSubscription.id).where(
        PushSubscription.user_id == user.id, PushSubscription.is_active.is_(True)))))


def send_to_user(db: Session, user_id: str, payload: dict) -> int:
    """Send to every active browser of this user. Returns how many succeeded."""
    if not push_enabled():
        print("[push] send skipped: VAPID public/private keys are not configured")
        return 0
    subs = list(db.scalars(select(PushSubscription).where(
        PushSubscription.user_id == user_id, PushSubscription.is_active.is_(True))))
    print(f"[push] user={user_id} active_subscriptions={len(subs)}")
    sent = 0
    for sub in subs:
        try:
            webpush(
                subscription_info={"endpoint": sub.endpoint, "keys": {"p256dh": sub.p256dh, "auth": sub.auth}},
                data=json.dumps(payload),
                vapid_private_key=VAPID_PRIVATE_KEY,
                vapid_claims={"sub": VAPID_SUBJECT},  # fresh dict each call, pywebpush mutates it
                ttl=3600,
            )
            sub.last_used_at = utcnow()
            sent += 1
            print(f"[push] delivery accepted by push service for subscription={sub.id}")
        except WebPushException as exc:
            status = getattr(exc.response, "status_code", None)
            print(f"[push] delivery failed for subscription={sub.id}: status={status}")
            if status in (404, 410):  # browser says the subscription is gone
                sub.is_active = False
            else:
                log.warning("push failed (%s): %s", status, exc)
        except Exception as exc:
            print(
                f"[push] error for subscription={sub.id}: "
                f"{type(exc).__name__}: {exc}"
            )
            log.warning("push error: %s", exc)
    db.commit()
    print(f"[push] delivery summary user={user_id}: sent={sent}/{len(subs)}")
    return sent