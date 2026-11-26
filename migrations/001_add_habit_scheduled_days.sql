-- Add optional weekly scheduling to existing habits.
-- NULL preserves the existing behavior: the habit is scheduled every day.
ALTER TABLE habits ADD COLUMN IF NOT EXISTS scheduled_days JSON;
