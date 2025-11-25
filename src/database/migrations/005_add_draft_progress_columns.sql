-- Migration: Add draft progress tracking columns to dynasty_state table
-- Date: 2025-11-23
-- Purpose: Support save/resume functionality for NFL Draft interactive dialog
-- Related: docs/project/nfl_draft_event/implementation_plan.md (Phase 3)

-- Add current_draft_pick column (tracks which pick number 1-262)
ALTER TABLE dynasty_state ADD COLUMN current_draft_pick INTEGER DEFAULT 0;

-- Add draft_in_progress column (boolean flag: 0=no draft, 1=draft active)
ALTER TABLE dynasty_state ADD COLUMN draft_in_progress INTEGER DEFAULT 0;

-- Update any existing records to have default values (SQLite ALTER TABLE with DEFAULT handles this automatically)
-- No UPDATE statement needed

-- Verification query:
-- SELECT dynasty_id, season, current_draft_pick, draft_in_progress FROM dynasty_state;
