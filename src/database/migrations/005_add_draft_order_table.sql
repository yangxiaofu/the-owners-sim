-- ============================================================================
-- NFL DRAFT ORDER SYSTEM - DATABASE SCHEMA
-- ============================================================================
-- Migration: 005
-- Description: Draft order table for managing draft picks, trades, and
--              compensatory picks across multiple seasons and dynasties
-- Date: 2025-11-16
-- Dependencies: dynasties table, draft_classes table (optional)
-- ============================================================================

-- ============================================================================
-- DRAFT ORDER TABLE
-- ============================================================================
-- Stores the complete NFL draft order for each season and dynasty.
-- Supports 7-round drafts with 32 picks per round (262 total picks).
-- Handles pick trades, compensatory picks, and pick execution tracking.
--
-- Key Features:
--   - Dynasty isolation for multi-save support
--   - Pick ownership tracking (original vs current owner)
--   - Compensatory pick management (placed at end of rounds)
--   - Trade tracking (when and how pick was acquired)
--   - Pick execution status (whether player has been selected)
--   - Integration with draft_classes and players tables
--
-- Pick Numbering:
--   - round_number: 1-7 (NFL draft rounds)
--   - pick_in_round: 1-32 (position within round, compensatory picks > 32)
--   - overall_pick: 1-262+ (calculated overall position in draft)
--
-- Compensatory Picks:
--   - is_compensatory: TRUE for compensatory picks
--   - comp_round_end: TRUE to place at end of round
--   - pick_in_round: Set to 33+ for picks awarded at round end
--
-- Trade Tracking:
--   - acquired_via_trade: TRUE if pick ownership changed
--   - trade_date: When the trade occurred
--   - original_trade_id: Reference to trade record (future implementation)
--   - original_team_id: Team that originally owned the pick
--   - current_team_id: Team that currently owns the pick
--
-- Pick Execution:
--   - is_executed: FALSE until pick is made
--   - player_id: NULL until player is selected, then FK to players
--
-- ============================================================================

CREATE TABLE IF NOT EXISTS draft_order (
    -- Primary Key
    pick_id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Dynasty Context
    dynasty_id TEXT NOT NULL,
    season INTEGER NOT NULL,

    -- Pick Position
    round_number INTEGER NOT NULL CHECK(round_number BETWEEN 1 AND 7),
    pick_in_round INTEGER NOT NULL CHECK(pick_in_round >= 1),
    overall_pick INTEGER NOT NULL CHECK(overall_pick >= 1),

    -- Pick Ownership
    original_team_id INTEGER NOT NULL CHECK(original_team_id BETWEEN 1 AND 32),
    current_team_id INTEGER NOT NULL CHECK(current_team_id BETWEEN 1 AND 32),

    -- Pick Execution
    player_id INTEGER,
    draft_class_id TEXT,
    is_executed BOOLEAN NOT NULL DEFAULT FALSE,

    -- Compensatory Picks
    is_compensatory BOOLEAN NOT NULL DEFAULT FALSE,
    comp_round_end BOOLEAN NOT NULL DEFAULT FALSE,

    -- Trade Information
    acquired_via_trade BOOLEAN NOT NULL DEFAULT FALSE,
    trade_date TIMESTAMP,
    original_trade_id TEXT,

    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Foreign Keys
    FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE,

    -- Business Constraints
    -- Each dynasty/season/round/pick combination must be unique
    UNIQUE(dynasty_id, season, round_number, pick_in_round)
);

-- ============================================================================
-- INDEXES
-- ============================================================================

-- Dynasty-based queries (most common)
CREATE INDEX IF NOT EXISTS idx_draft_order_dynasty
ON draft_order(dynasty_id);

-- Season-based queries (draft year filtering)
CREATE INDEX IF NOT EXISTS idx_draft_order_season
ON draft_order(dynasty_id, season);

-- Team pick queries (current ownership)
CREATE INDEX IF NOT EXISTS idx_draft_order_team
ON draft_order(current_team_id, season);

-- Original ownership tracking
CREATE INDEX IF NOT EXISTS idx_draft_order_original_team
ON draft_order(original_team_id, season);

-- Pick execution status (available picks)
CREATE INDEX IF NOT EXISTS idx_draft_order_execution
ON draft_order(dynasty_id, season, is_executed);

-- Pick position lookups (round and overall)
CREATE INDEX IF NOT EXISTS idx_draft_order_position
ON draft_order(dynasty_id, season, overall_pick);

-- Compensatory pick filtering
CREATE INDEX IF NOT EXISTS idx_draft_order_compensatory
ON draft_order(season, is_compensatory);

-- Trade tracking
CREATE INDEX IF NOT EXISTS idx_draft_order_trades
ON draft_order(dynasty_id, season, acquired_via_trade);

-- Player linkage (drafted players)
CREATE INDEX IF NOT EXISTS idx_draft_order_player
ON draft_order(player_id);

-- Draft class linkage
CREATE INDEX IF NOT EXISTS idx_draft_order_draft_class
ON draft_order(draft_class_id);

-- ============================================================================
-- TRIGGERS
-- ============================================================================

-- Trigger: Update updated_at timestamp on any modification
CREATE TRIGGER IF NOT EXISTS trg_draft_order_updated_at
AFTER UPDATE ON draft_order
FOR EACH ROW
BEGIN
    UPDATE draft_order
    SET updated_at = CURRENT_TIMESTAMP
    WHERE pick_id = NEW.pick_id;
END;

-- ============================================================================
-- MIGRATION COMPLETE
-- ============================================================================
-- This schema provides complete support for:
-- ✓ Dynasty-isolated draft order tracking
-- ✓ 7-round NFL draft with compensatory picks
-- ✓ Pick ownership tracking (original vs current)
-- ✓ Pick trade management with trade metadata
-- ✓ Pick execution status and player linkage
-- ✓ Compensatory pick placement (round end)
-- ✓ Draft class integration (optional FK)
-- ✓ Comprehensive indexing for performance
-- ✓ Automatic timestamp management
-- ============================================================================
