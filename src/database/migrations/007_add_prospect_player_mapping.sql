-- Migration: Add prospect-to-player mapping column
-- Date: 2025-11-24
-- Purpose: Track which roster player_id each draft prospect became after conversion
-- Related: NFL Draft player conversion system - links draft prospects to final roster players

-- ============================================================================
-- Add roster_player_id column to draft_prospects table
-- ============================================================================
-- This column tracks the final player_id assigned when a draft prospect was
-- converted to a roster player after being drafted.
--
-- Values:
--   NULL     = Prospect not yet converted (still in draft pool or undrafted)
--   Non-NULL = Prospect converted to roster player, points to players.player_id
--
-- Use Cases:
--   1. Historical tracking: "Show me all players from the 2025 draft class"
--   2. Reverse lookup: "What were this player's original draft prospect stats?"
--   3. Development tracking: Compare prospect projections vs actual performance
--   4. Draft analysis: Evaluate draft pick value vs career outcomes
-- ============================================================================

ALTER TABLE draft_prospects
ADD COLUMN roster_player_id INTEGER DEFAULT NULL;

-- ============================================================================
-- Create indexes for efficient lookups
-- ============================================================================

-- Index for finding all roster players from a specific draft class
-- Query example: "Show all active players from 2025 draft"
CREATE INDEX IF NOT EXISTS idx_prospects_roster_player
ON draft_prospects(roster_player_id);

-- Composite index for dynasty-aware reverse lookups
-- Query example: "Find the original draft prospect for player_id 12345 in dynasty X"
CREATE INDEX IF NOT EXISTS idx_prospects_mapping
ON draft_prospects(dynasty_id, roster_player_id)
WHERE roster_player_id IS NOT NULL;

-- ============================================================================
-- Verification Query
-- ============================================================================
-- After migration, verify the column exists:
--
-- SELECT dynasty_id, player_id, first_name, last_name, position,
--        is_drafted, drafted_by_team_id, roster_player_id
-- FROM draft_prospects
-- WHERE dynasty_id='your_dynasty'
-- LIMIT 10;
--
-- Expected: roster_player_id column should exist with NULL values for all prospects
-- ============================================================================

-- ============================================================================
-- Migration Complete
-- ============================================================================
