-- Migration: Add season_type to standings table
-- Version: 2.4.0
-- Date: 2025-10-12
-- Purpose: Separate regular season and playoff standings records

BEGIN TRANSACTION;

-- Step 1: Add season_type column with default value
-- All existing records will be marked as 'regular_season'
ALTER TABLE standings
ADD COLUMN season_type TEXT NOT NULL DEFAULT 'regular_season';

-- Step 2: Ensure all existing records have season_type set
-- (This is redundant with DEFAULT but ensures consistency)
UPDATE standings
SET season_type = 'regular_season'
WHERE season_type IS NULL OR season_type = '';

-- Step 3: Drop old unique constraint if it exists
-- Note: SQLite doesn't have ALTER INDEX, so we drop and recreate
DROP INDEX IF EXISTS idx_standings_unique;

-- Step 4: Create new unique constraint including season_type
-- This allows one regular_season record AND one playoffs record per team/season
CREATE UNIQUE INDEX idx_standings_unique
ON standings(dynasty_id, team_id, season, season_type);

-- Step 5: Add index for fast filtering by season_type
CREATE INDEX idx_standings_season_type
ON standings(dynasty_id, season, season_type);

-- Step 6: Add composite index for common query patterns
CREATE INDEX idx_standings_team_season_type
ON standings(team_id, season, season_type);

COMMIT;

-- Rollback instructions (if needed):
-- BEGIN TRANSACTION;
-- DROP INDEX IF EXISTS idx_standings_unique;
-- DROP INDEX IF EXISTS idx_standings_season_type;
-- DROP INDEX IF EXISTS idx_standings_team_season_type;
-- CREATE UNIQUE INDEX idx_standings_unique ON standings(dynasty_id, team_id, season);
-- ALTER TABLE standings DROP COLUMN season_type;  -- Note: SQLite may not support this
-- COMMIT;
