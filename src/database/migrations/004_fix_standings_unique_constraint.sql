-- Migration: Fix standings UNIQUE constraint to include season_type
-- Version: 2.4.1
-- Date: 2025-10-26
-- Purpose: Remove inline UNIQUE constraint and use index-based constraint only
--
-- Problem: The standings table had two UNIQUE constraints:
--   1. Inline constraint: UNIQUE(dynasty_id, team_id, season) - OLD, blocks season_type
--   2. Index constraint: idx_standings_unique with season_type - NEW, correct
--
-- Solution: Recreate table without inline constraint

BEGIN TRANSACTION;

-- Step 1: Create new table with correct schema (no inline UNIQUE constraint)
CREATE TABLE standings_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dynasty_id TEXT NOT NULL,
    team_id INTEGER NOT NULL,
    season INTEGER NOT NULL,
    season_type TEXT NOT NULL DEFAULT 'regular_season',

    -- Regular season record
    wins INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0,
    ties INTEGER DEFAULT 0,

    -- Division record
    division_wins INTEGER DEFAULT 0,
    division_losses INTEGER DEFAULT 0,
    division_ties INTEGER DEFAULT 0,

    -- Conference record
    conference_wins INTEGER DEFAULT 0,
    conference_losses INTEGER DEFAULT 0,
    conference_ties INTEGER DEFAULT 0,

    -- Home/Away splits
    home_wins INTEGER DEFAULT 0,
    home_losses INTEGER DEFAULT 0,
    home_ties INTEGER DEFAULT 0,
    away_wins INTEGER DEFAULT 0,
    away_losses INTEGER DEFAULT 0,
    away_ties INTEGER DEFAULT 0,

    -- Points and differentials
    points_for INTEGER DEFAULT 0,
    points_against INTEGER DEFAULT 0,
    point_differential INTEGER DEFAULT 0,

    -- Streaks and rankings
    current_streak TEXT,
    division_rank INTEGER,
    conference_rank INTEGER,
    league_rank INTEGER,

    -- Playoff information
    playoff_seed INTEGER,
    made_playoffs BOOLEAN DEFAULT FALSE,
    made_wild_card BOOLEAN DEFAULT FALSE,
    won_wild_card BOOLEAN DEFAULT FALSE,
    won_division_round BOOLEAN DEFAULT FALSE,
    won_conference BOOLEAN DEFAULT FALSE,
    won_super_bowl BOOLEAN DEFAULT FALSE,

    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id)
    -- IMPORTANT: NO inline UNIQUE constraint here!
    -- UNIQUE constraint will be created as an index in Step 5
);

-- Step 2: Copy all data from old table
INSERT INTO standings_new
SELECT id, dynasty_id, team_id, season, season_type,
       wins, losses, ties,
       division_wins, division_losses, division_ties,
       conference_wins, conference_losses, conference_ties,
       home_wins, home_losses, home_ties,
       away_wins, away_losses, away_ties,
       points_for, points_against, point_differential,
       current_streak, division_rank, conference_rank, league_rank,
       playoff_seed, made_playoffs, made_wild_card, won_wild_card,
       won_division_round, won_conference, won_super_bowl,
       last_updated
FROM standings;

-- Step 3: Drop old table
DROP TABLE standings;

-- Step 4: Rename new table
ALTER TABLE standings_new RENAME TO standings;

-- Step 5: Recreate all indexes (including correct UNIQUE index with season_type)
CREATE INDEX idx_standings_dynasty ON standings(dynasty_id, season);
CREATE INDEX idx_standings_team ON standings(team_id, season);

-- CRITICAL: This is the ONLY UNIQUE constraint (includes season_type)
CREATE UNIQUE INDEX idx_standings_unique ON standings(dynasty_id, team_id, season, season_type);

CREATE INDEX idx_standings_season_type ON standings(dynasty_id, season, season_type);
CREATE INDEX idx_standings_team_season_type ON standings(team_id, season, season_type);

COMMIT;

-- Verification queries (run manually if needed):
-- SELECT sql FROM sqlite_master WHERE type='table' AND name='standings';
-- SELECT sql FROM sqlite_master WHERE type='index' AND tbl_name='standings';
