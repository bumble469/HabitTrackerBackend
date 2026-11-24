from datetime import date, timedelta

from ml.features import build_features, days_since_last, rate, streak

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
