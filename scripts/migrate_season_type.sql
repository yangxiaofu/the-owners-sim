-- Full database migration script
-- Version: 1.0
-- Purpose: Add season_type column for regular season/playoff separation
--
-- This migration adds the necessary columns to support full season simulation
-- with clear separation between regular season and playoff statistics.

BEGIN TRANSACTION;

-- Step 1: Add season_type column to games table
ALTER TABLE games ADD COLUMN season_type TEXT NOT NULL DEFAULT 'regular_season';

-- Step 2: game_type column already exists in current schema (line 95 of connection.py)
-- Verify it exists and has correct default
-- ALTER TABLE games ADD COLUMN game_type TEXT DEFAULT 'regular';  -- Already exists

-- Step 3: Add season_type column to player_game_stats table
ALTER TABLE player_game_stats ADD COLUMN season_type TEXT NOT NULL DEFAULT 'regular_season';

-- Step 4: Update existing playoff games (if any)
-- NFL playoff weeks are typically 19-22 (Wild Card, Divisional, Conference, Super Bowl)
UPDATE games
SET season_type = 'playoffs',
    game_type = CASE
        WHEN week = 19 THEN 'wildcard'
        WHEN week = 20 THEN 'divisional'
        WHEN week = 21 THEN 'conference'
        WHEN week = 22 THEN 'super_bowl'
        ELSE game_type  -- Keep existing value for regular season games
    END
WHERE week > 18;

-- Step 5: Update player_game_stats to match games season_type
-- This ensures consistency between games and player stats
UPDATE player_game_stats
SET season_type = (
    SELECT season_type
    FROM games
    WHERE games.game_id = player_game_stats.game_id
)
WHERE EXISTS (
    SELECT 1 FROM games WHERE games.game_id = player_game_stats.game_id
);

-- Step 6: Create performance indexes
-- These indexes optimize queries that filter by season_type
CREATE INDEX IF NOT EXISTS idx_games_season_type ON games(dynasty_id, season, season_type);
CREATE INDEX IF NOT EXISTS idx_games_type ON games(game_type);
CREATE INDEX IF NOT EXISTS idx_stats_season_type ON player_game_stats(dynasty_id, season_type);
CREATE INDEX IF NOT EXISTS idx_stats_player_type ON player_game_stats(player_id, season_type);

-- Step 7: Verify migration
SELECT 'Games by season_type:' as verification;
SELECT season_type, COUNT(*) as count FROM games GROUP BY season_type;

SELECT 'Player stats by season_type:' as verification;
SELECT season_type, COUNT(*) as count FROM player_game_stats GROUP BY season_type;

COMMIT;

-- Migration complete!
-- The database now supports separate tracking of regular season and playoff statistics.

-- ============================================================================
-- ROLLBACK SCRIPT (use only if migration needs to be reversed)
-- ============================================================================
-- Note: SQLite doesn't support DROP COLUMN directly, so rollback requires table recreation
-- Only use this if the migration causes critical issues
--
-- BEGIN TRANSACTION;
--
-- -- Drop the new indexes
-- DROP INDEX IF EXISTS idx_games_season_type;
-- DROP INDEX IF EXISTS idx_games_type;
-- DROP INDEX IF EXISTS idx_stats_season_type;
-- DROP INDEX IF EXISTS idx_stats_player_type;
--
-- -- To remove columns, you would need to:
-- -- 1. Create new tables without the season_type column
-- -- 2. Copy data from old tables to new tables
-- -- 3. Drop old tables
-- -- 4. Rename new tables to old names
-- -- This is complex and not recommended unless absolutely necessary.
--
-- COMMIT;
