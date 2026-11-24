from datetime import date, timedelta


MIN_HISTORY_DAYS = 14

FEATURES = [
    "rate_7",
    "rate_14",
    "rate_30",
    "trend",
    "streak",
    "days_since_last",
    "age_days",
    "next_weekend",
]


def rate(done: set, end: date, window: int, start: date) -> float:
    """Completion rate over `window` days ending at `end`, ignoring days before the habit existed."""
    days = [end - timedelta(i) for i in range(window) if end - timedelta(i) >= start]
    return sum(d in done for d in days) / max(len(days), 1)


def streak(done: set, end: date) -> int:
    n = 0
    while end - timedelta(n) in done:
        n += 1
    return n


def days_since_last(done: set, end: date, cap: int = 30) -> int:
    for i in range(cap):
        if end - timedelta(i) in done:
            return i
    return cap


def build_features(done: set, created: date, as_of: date) -> dict:
    """Features for one habit as of day `as_of` (all computable from dates only)."""
    r7 = rate(done, as_of, 7, created)
    return {
        "rate_7": r7,
        "rate_14": rate(done, as_of, 14, created),
        "rate_30": rate(done, as_of, 30, created),
        "trend": r7 - rate(done, as_of - timedelta(7), 7, created),
        "streak": streak(done, as_of),
        "days_since_last": days_since_last(done, as_of),
        "age_days": max(0, min((as_of - created).days, 90)),
        "next_weekend": int((as_of + timedelta(1)).weekday() >= 5),
    }
