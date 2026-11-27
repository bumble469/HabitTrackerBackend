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


def build_features_scheduled(done: set, created: date, as_of: date, scheduled_days) -> tuple[dict, int]:
    """Features for a habit that only runs on some weekdays, judged on those days only.

    `scheduled_days` uses 0=Sunday .. 6=Saturday, like the app. Days the habit is not
    scheduled are removed from the timeline, so the scheduled days become consecutive
    "virtual" days and the model sees the same kind of history it was trained on:
    rates are over the last N scheduled days, a streak is consecutive scheduled days
    done, and nothing is counted as missed on an off day.

    Returns (features, number of scheduled days since the habit was created).
    """
    allowed = set(scheduled_days)
    span = max((as_of - created).days + 1, 0)
    occurrences = [
        d for d in (created + timedelta(i) for i in range(span)) if (d.weekday() + 1) % 7 in allowed
    ]
    virtual_done = {created + timedelta(i) for i, d in enumerate(occurrences) if d in done}
    virtual_end = created + timedelta(max(len(occurrences) - 1, 0))
    features = build_features(virtual_done, created, virtual_end)

    # Weekend flag: the next scheduled day, but only when the schedule mixes weekdays and
    # weekend days. A weekend-only (or weekday-only) schedule would otherwise be a constant.
    mixed = bool(allowed & {0, 6}) and bool(allowed & {1, 2, 3, 4, 5})
    features["next_weekend"] = 0
    if mixed:
        for k in range(1, 8):
            nxt = as_of + timedelta(k)
            if (nxt.weekday() + 1) % 7 in allowed:
                features["next_weekend"] = int(nxt.weekday() >= 5)
                break
    return features, len(occurrences)
