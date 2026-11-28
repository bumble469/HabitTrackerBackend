from datetime import date, timedelta

from ml.features import build_features, build_features_scheduled, days_since_last, rate, streak

D = date(2026, 11, 20)


def test_streak_counts_consecutive_days():
    done = {D, D - timedelta(1), D - timedelta(2)}
    assert streak(done, D) == 3
    assert streak(done, D + timedelta(1)) == 0


def test_days_since_last():
    assert days_since_last({D - timedelta(3)}, D) == 3
    assert days_since_last(set(), D) == 30  # capped


def test_rate_ignores_days_before_habit_existed():
    created = D - timedelta(1)  # habit is 2 days old
    assert rate({D, D - timedelta(1)}, D, 7, created) == 1.0


def test_brand_new_habit_has_no_negative_age():
    f = build_features(set(), D + timedelta(1), D)  # created after as_of
    assert f["age_days"] == 0


def test_next_weekend_flag():
    friday = date(2026, 11, 20)
    assert build_features(set(), friday - timedelta(30), friday)["next_weekend"] == 1  # Saturday next
    thursday = date(2026, 11, 19)
    assert build_features(set(), thursday - timedelta(30), thursday)["next_weekend"] == 0


MON_WED_FRI = [1, 3, 5]  # 0 = Sunday, like the app


def _scheduled(created, end, allowed):
    days = (created + timedelta(i) for i in range((end - created).days + 1))
    return [d for d in days if (d.weekday() + 1) % 7 in allowed]


def test_scheduled_habit_is_not_penalised_for_off_days():
    created = D - timedelta(45)
    done = set(_scheduled(created, D, MON_WED_FRI))
    f, count = build_features_scheduled(done, created, D, MON_WED_FRI)
    assert f["rate_7"] == 1.0 and f["rate_30"] == 1.0
    assert f["streak"] == count
    assert f["days_since_last"] == 0
    # The same check-ins judged as a daily habit would look like lots of misses.
    assert build_features(done, created, D)["rate_30"] < 0.6


def test_scheduled_habit_counts_misses_on_scheduled_days():
    created = D - timedelta(45)
    days = _scheduled(created, D, MON_WED_FRI)
    f, _ = build_features_scheduled(set(days[:-3]), created, D, MON_WED_FRI)  # last 3 missed
    assert f["days_since_last"] == 3
    assert f["streak"] == 0


def test_weekday_only_schedule_has_neutral_weekend_flag():
    f, _ = build_features_scheduled(set(), D - timedelta(45), D, MON_WED_FRI)
    assert f["next_weekend"] == 0
