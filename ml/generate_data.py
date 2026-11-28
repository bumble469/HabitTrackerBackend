import argparse
import csv
import random
from datetime import date, timedelta
from pathlib import Path
import math

OUT_FILE = Path(__file__).resolve().parent / "data" / "habit_logs.csv"
FIRST_CREATED = date(2026, 1, 1)
LAST_CREATED = date(2026, 8, 31)
LAST_DAY = date(2026, 11, 20) 

PROFILES = [
    ("reliable", 0.25),
    ("average", 0.25),
    ("inconsistent", 0.15),
    ("quitter", 0.15),
    ("fading", 0.10),
    ("comeback", 0.05),
    ("weekday_specific", 0.05),
]

def make_habit(rng: random.Random, profile: str) -> dict:
    """Pick the personal parameters of one habit."""
    created = FIRST_CREATED + timedelta(days=rng.randint(0, (LAST_CREATED - FIRST_CREATED).days))
    length = min(rng.randint(60, 120), (LAST_DAY - created).days + 1)
    h = {
        "profile": profile,
        "created": created,
        "length": length,
        "offset": rng.uniform(-0.05, 0.05), 
        "momentum": 0.12,
        "weekend": rng.uniform(0.75, 0.90) if rng.random() < 0.6 else 1.0, 
    }
    if profile == "reliable":
        h["base"] = rng.uniform(0.80, 0.95)
    elif profile == "average":
        h["base"] = rng.uniform(0.50, 0.75)
    elif profile == "inconsistent":
        h["base"] = rng.uniform(0.30, 0.50)
        h["momentum"] = 0.25 
    elif profile == "quitter":
        h["base"] = rng.uniform(0.80, 0.95)
        h["quit_at"] = rng.randint(20, length - 10)
        h["after"] = rng.uniform(0.02, 0.15)
    elif profile == "fading":
        h["start"] = rng.uniform(0.85, 0.95)
        h["end"] = rng.uniform(0.20, 0.40)
    elif profile == "comeback":
        h["base"] = rng.uniform(0.70, 0.90)
        h["dip_start"] = rng.randint(10, length - 25)
        h["dip_len"] = rng.randint(7, 21)
        h["dip_p"] = rng.uniform(0.02, 0.10)
    elif profile == "weekday_specific":
        h["base"] = rng.uniform(0.80, 0.92)
        h["weak_days"] = rng.sample(range(7), rng.randint(1, 2))
        h["weak_p"] = rng.uniform(0.10, 0.30)
    return h


def base_probability(h: dict, i: int, weekday: int) -> float:
    """Chance of completing on day i of the habit, before momentum."""
    p = h.get("base", 0.5)
    profile = h["profile"]
    if profile == "quitter" and i >= h["quit_at"]:
        p = h["after"]
    elif profile == "fading":
        p = h["start"] + (h["end"] - h["start"]) * i / max(h["length"] - 1, 1)
    elif profile == "comeback" and h["dip_start"] <= i < h["dip_start"] + h["dip_len"]:
        p = h["dip_p"]
    elif profile == "weekday_specific" and weekday in h["weak_days"]:
        p = h["weak_p"]
    p += h["offset"]
    if weekday >= 5:
        p *= h["weekend"]
    if i < 14:
        p *= 0.92  
    return p


def simulate(rng: random.Random, h: dict, sharpness: float = 1.0) -> set:
    done = set()
    prev_done = rng.random() < 0.7
    for i in range(h["length"]):
        day = h["created"] + timedelta(days=i)
        p = base_probability(h, i, day.weekday())
        p += h["momentum"] if prev_done else -h["momentum"] 
        p = min(max(p, 0.01), 0.99)
        p = 1 / (1 + math.exp(-sharpness * math.log(p / (1 - p))))
        prev_done = rng.random() < p
        if prev_done:
            done.add(day)
    return done


def generate(n_habits: int, seed: int, sharpness: float = 1.0) -> list[dict]:
    rng = random.Random(seed)
    names = [name for name, _ in PROFILES]
    weights = [share for _, share in PROFILES]
    habits = []
    for n in range(1, n_habits + 1):
        h = make_habit(rng, rng.choices(names, weights)[0])
        h["id"] = f"h{n:04d}"
        h["done"] = simulate(rng, h, sharpness)
        h["until"] = h["created"] + timedelta(days=h["length"] - 1)
        habits.append(h)
    return habits


def write_csv(habits: list[dict], path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = 0
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["habit_id", "created_on", "completed_on", "observed_until"])
        for h in sorted(habits, key=lambda x: x["id"]):
            days = sorted(h["done"]) or [None]  # a habit with no completions gets one blank row
            for d in days:
                w.writerow([h["id"], h["created"], d or "", h["until"]])
                rows += 1
    return rows


def summary(habits: list[dict], rows: int, path: Path) -> None:
    habit_days = sum(h["length"] for h in habits)
    completed = sum(len(h["done"]) for h in habits)
    labels = dropouts = 0
    for h in habits:  
        day = h["created"] + timedelta(days=14)
        last = h["until"] - timedelta(days=3)
        while day <= last:
            labels += 1
            if not any(day + timedelta(days=k) in h["done"] for k in (1, 2, 3)):
                dropouts += 1
            day += timedelta(days=1)
    by_profile = {}
    for h in habits:
        by_profile[h["profile"]] = by_profile.get(h["profile"], 0) + 1
    latest = max(h["until"] for h in habits)

    print(f"Saved {path}")
    print(f"Habits: {len(habits)}   Rows: {rows}")
    print(f"Overall completion rate: {completed / habit_days:.1%}")
    print(f"Dropout-label share:     {dropouts / max(labels, 1):.1%}  ({labels} labelled days)")
    print("Habits per profile:      " + ", ".join(f"{k}={v}" for k, v in sorted(by_profile.items())))
    print(f"Latest date in data:     {latest}  (limit {LAST_DAY})")
    print(f"Habits with no completions: {sum(1 for h in habits if not h['done'])}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--habits", type=int, default=7500)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", default=str(OUT_FILE))
    parser.add_argument("--sharpness", type=float, default=2.0, help="1.0 = noisiest; higher = less random")
    args = parser.parse_args()

    data = generate(args.habits, args.seed, args.sharpness)
    out = Path(args.out)
    summary(data, write_csv(data, out), out)
