# Training data

Put ONE `.csv` or `.xlsx` file in this folder, then run `python -m ml.train` from the repo root.
To create a synthetic file here, run `python -m ml.generate_data` first (it writes `habit_logs.csv`). Keep only one data file in this folder.

## Columns

| Column | Required | Example | Meaning |
| --- | --- | --- | --- |
| habit_id | yes | h1 | Unique id of one habit |
| created_on | yes | 2026-10-01 | Day the habit started (same value on every row of a habit) |
| completed_on | yes | 2026-11-14 | A day the habit was done. One row per completed day |
| observed_until | no | 2026-12-31 | Last day this habit was tracked. If missing, the latest date in the file is used for all habits |

```
habit_id,created_on,completed_on
h1,2026-10-01,2026-11-14
h1,2026-10-01,2026-11-15
h2,2026-09-10,2026-11-19
```

## Rules

- Dates must look like `YYYY-MM-DD`. In Excel, real date cells are also fine.
- Days with no row count as missed, exactly like in the app. Do not add rows for missed days.
- A habit with no completions at all: add one row with `completed_on` left blank.
- Use many habits (at least 10, ideally hundreds), each with 60-90 days of history. Habits shorter than 17 days are skipped.
- The file is training data only. It is not used when the API runs.
