-- Removes leftovers of two dropped features: the AI coach (RAG) and demo data.
-- Run once against the database (Neon SQL Editor) BEFORE starting the updated backend.
-- Safe to run twice. SQLite (dev.db) cannot run this: for local development just delete dev.db.

-- AI coach tables (chat_messages references conversations, so it goes first)
DROP TABLE IF EXISTS chat_messages;
DROP TABLE IF EXISTS conversations;
DROP TABLE IF EXISTS kb_notes;

-- Demo data flag. The backend no longer filters on it, so any demo habits are deleted first
-- (their check-ins and risk history go with them) instead of suddenly appearing in the app.
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'habits' AND column_name = 'is_demo'
  ) THEN
    DELETE FROM habits WHERE is_demo = TRUE;
    ALTER TABLE habits DROP COLUMN is_demo;
  END IF;
END $$;
