import logging
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.db import SessionLocal
from app.models import Completion, Habit, ReminderLog, User
from app.services import push_service

log = logging.getLogger(__name__)
WINDOW_MINUTES = 10  

def run_reminders(now_utc: datetime | None = None) -> int:
    now_utc = now_utc or datetime.now(timezone.utc)
    sent_total = 0
    print(f"[reminders] scan started at {now_utc.isoformat()}")
    with SessionLocal() as db:
        rows = db.execute(
            select(Habit, User).join(User, Habit.user_id == User.id)
            .where(Habit.archived_at.is_(None), Habit.reminder_time.is_not(None))
        ).all()
        print(f"[reminders] found {len(rows)} active habit(s) with reminders")
        for habit, user in rows:
            try:
                local = now_utc.astimezone(ZoneInfo(user.timezone))
            except Exception as exc:
                print(
                    f"[reminders] invalid timezone for user={user.id}: "
                    f"{user.timezone!r} ({type(exc).__name__}); using UTC"
                )
                local = now_utc
            h, m = map(int, habit.reminder_time.split(":"))
            minutes_since = (local.hour * 60 + local.minute) - (h * 60 + m)
            print(
                f"[reminders] habit={habit.id} user={user.id} "
                f"local_time={local:%Y-%m-%d %H:%M} timezone={user.timezone} "
                f"reminder_time={habit.reminder_time} minutes_since={minutes_since}"
            )
            if not 0 <= minutes_since < WINDOW_MINUTES:
                print(f"[reminders] skip habit={habit.id}: outside reminder window")
                continue
            today = local.date()
            weekday = (today.weekday() + 1) % 7
            if habit.scheduled_days and weekday not in habit.scheduled_days:
                print(f"[reminders] skip habit={habit.id}: not scheduled today")
                continue
            if db.scalar(select(Completion.id).where(Completion.habit_id == habit.id, Completion.day == today)):
                print(f"[reminders] skip habit={habit.id}: already completed today")
                continue
            log_entry = ReminderLog(habit_id=habit.id, day=today)
            db.add(log_entry)
            try:
                db.commit()  
            except IntegrityError:
                db.rollback()
                print(f"[reminders] skip habit={habit.id}: already attempted today")
                continue
            print(f"[reminders] sending push for habit={habit.id}")
            sent = push_service.send_to_user(
                db, user.id,
                {"title": "Time for your habit", "body": habit.name, "url": f"/#habit={habit.id}"},
            )
            if sent:
                sent_total += sent
                print(f"[reminders] push succeeded for habit={habit.id}: sent={sent}")
            else:
                db.delete(log_entry)
                db.commit()
                print(f"[reminders] no push delivered for habit={habit.id}; will retry")
    print(f"[reminders] scan finished; delivered={sent_total}")
    return sent_total


def start_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.add_job(run_reminders, "interval", minutes=1, max_instances=1, coalesce=True)
    scheduler.start()
    print("[reminders] scheduler started; interval=1 minute")
    return scheduler