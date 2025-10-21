-- ============================================================================
-- Draft Class Generation System Database Schema
-- ============================================================================
-- This migration adds tables for draft class generation and management.
--
-- Tables:
--   1. draft_classes: Stores metadata about generated draft classes per dynasty
--   2. draft_prospects: Stores individual player prospects within each draft class
--
-- Dependencies:
--   - dynasties table must exist (for foreign key constraints)
--
-- Version: 1.0.0
-- Created: 2025-10-19
-- ============================================================================

-- ============================================================================
-- Table: draft_classes
-- ============================================================================
-- Stores metadata about generated draft classes for each dynasty season.
-- Each dynasty can have one draft class per season.
--
-- Columns:
--   - draft_class_id: Unique identifier (format: "DRAFT_<dynasty_id>_<season>")
--   - dynasty_id: Foreign key to dynasties table
--   - season: NFL season year (e.g., 2024)
--   - generation_date: When the draft class was generated
--   - total_prospects: Number of prospects in this draft class
--   - status: Draft class status ('active', 'completed', 'archived')
--   - created_at: Timestamp when record was created
-- ============================================================================

CREATE TABLE IF NOT EXISTS draft_classes (
    draft_class_id TEXT PRIMARY KEY,
    dynasty_id TEXT NOT NULL,
    season INTEGER NOT NULL,
    generation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_prospects INTEGER DEFAULT 0,
    status TEXT DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE,
    UNIQUE(dynasty_id, season)
);

-- Indexes for draft_classes table
CREATE INDEX IF NOT EXISTS idx_draft_classes_dynasty ON draft_classes(dynasty_id);
CREATE INDEX IF NOT EXISTS idx_draft_classes_season ON draft_classes(dynasty_id, season);

-- ============================================================================
-- Table: draft_prospects
-- ============================================================================
-- Stores individual player prospects within each draft class.
-- Links to draft_classes and supports scouting, drafting, and development.
--
-- Columns:
--   - player_id: Unique player identifier (numeric)
--   - draft_class_id: Foreign key to draft_classes table
--   - dynasty_id: Foreign key to dynasties table
--   - first_name, last_name: Player name
--   - position: Player position (QB, RB, WR, etc.)
--   - age: Player age at draft time
--   - draft_round: Expected draft round (1-7)
--   - draft_pick: Expected pick within round
--   - projected_pick_min: Lower bound of projected draft position
--   - projected_pick_max: Upper bound of projected draft position
--   - overall: True overall rating (0-100)
--   - attributes: JSON string of all player attributes
--   - college: College/university name
--   - hometown: Player's hometown
--   - home_state: Player's home state/province
--   - archetype_id: Player archetype identifier
--   - scouted_overall: Scouted rating (may differ from true overall)
--   - scouting_confidence: Scouting confidence level ('low', 'medium', 'high')
--   - is_drafted: Whether player has been drafted
--   - drafted_by_team_id: Team that drafted the player
--   - drafted_round: Actual draft round
--   - drafted_pick: Actual draft pick
--   - development_curve: Player development trajectory ('early', 'normal', 'late')
--   - created_at: Timestamp when record was created
--   - updated_at: Timestamp when record was last updated
-- ============================================================================

CREATE TABLE IF NOT EXISTS draft_prospects (
    player_id INTEGER NOT NULL,
    draft_class_id TEXT NOT NULL,
    dynasty_id TEXT NOT NULL,

    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    position TEXT NOT NULL,
    age INTEGER NOT NULL,

    draft_round INTEGER NOT NULL,
    draft_pick INTEGER NOT NULL,
    projected_pick_min INTEGER,
    projected_pick_max INTEGER,

    overall INTEGER NOT NULL,
    attributes TEXT NOT NULL,

    college TEXT,
    hometown TEXT,
    home_state TEXT,

    archetype_id TEXT,

    scouted_overall INTEGER,
    scouting_confidence TEXT DEFAULT 'medium',

    is_drafted BOOLEAN DEFAULT FALSE,
    drafted_by_team_id INTEGER,
    drafted_round INTEGER,
    drafted_pick INTEGER,

    development_curve TEXT DEFAULT 'normal',

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (dynasty_id, player_id),
    FOREIGN KEY (draft_class_id) REFERENCES draft_classes(draft_class_id) ON DELETE CASCADE,
    FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE
);

-- Indexes for draft_prospects table
CREATE INDEX IF NOT EXISTS idx_prospects_draft_class ON draft_prospects(draft_class_id);
CREATE INDEX IF NOT EXISTS idx_prospects_dynasty ON draft_prospects(dynasty_id);
CREATE INDEX IF NOT EXISTS idx_prospects_position ON draft_prospects(dynasty_id, position);
CREATE INDEX IF NOT EXISTS idx_prospects_available ON draft_prospects(dynasty_id, is_drafted);
CREATE INDEX IF NOT EXISTS idx_prospects_overall ON draft_prospects(draft_class_id, overall DESC);
CREATE INDEX IF NOT EXISTS idx_prospects_player_id ON draft_prospects(player_id);

-- ============================================================================
-- Migration Complete
-- ============================================================================
