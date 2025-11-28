-- ============================================================================
-- PLAYER TRANSACTIONS SYSTEM - DATABASE SCHEMA
-- ============================================================================
-- Migration: 003
-- Description: Player transactions table for tracking all roster moves,
--              contract actions, and personnel changes
-- Date: 2025-10-19
-- Based on: NFL transaction rules and dynasty management requirements
-- ============================================================================

-- ============================================================================
-- PLAYER TRANSACTIONS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS player_transactions (
    transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
    dynasty_id TEXT NOT NULL,
    season INTEGER NOT NULL,

    -- Transaction Type
    transaction_type TEXT NOT NULL CHECK(transaction_type IN (
        'DRAFT',
        'UDFA_SIGNING',
        'UFA_SIGNING',
        'RFA_SIGNING',
        'RELEASE',
        'WAIVER_CLAIM',
        'TRADE',
        'ROSTER_CUT',
        'PRACTICE_SQUAD_ADD',
        'PRACTICE_SQUAD_REMOVE',
        'PRACTICE_SQUAD_ELEVATE',
        'FRANCHISE_TAG',
        'TRANSITION_TAG',
        'RESTRUCTURE'
    )),

    -- Player Information
    player_id INTEGER NOT NULL,
    first_name TEXT,
    last_name TEXT,
    position TEXT,

    -- Team Movement
    from_team_id INTEGER,  -- NULL for draft/UDFA signings
    to_team_id INTEGER,    -- NULL for releases/cuts

    -- Transaction Date
    transaction_date DATE NOT NULL,

    -- Additional Details
    details TEXT,  -- JSON storage for transaction-specific data
                   -- Examples:
                   -- Draft: {"round": 1, "pick": 15, "overall": 15}
                   -- UFA: {"contract_years": 3, "contract_value": 45000000}
                   -- Trade: {"compensation": "2025 1st round pick + 2026 3rd"}
                   -- Release: {"pre_june_1": false, "cap_savings": 5000000}

    -- Foreign Key References
    contract_id INTEGER,   -- NULL for non-contract transactions
    event_id TEXT,         -- NULL for manual transactions

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Foreign Keys
    FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE,
    FOREIGN KEY (contract_id) REFERENCES player_contracts(contract_id)
);

-- ============================================================================
-- INDEXES FOR PLAYER TRANSACTIONS
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_transactions_dynasty ON player_transactions(dynasty_id);
CREATE INDEX IF NOT EXISTS idx_transactions_player ON player_transactions(player_id);
CREATE INDEX IF NOT EXISTS idx_transactions_type ON player_transactions(transaction_type);
CREATE INDEX IF NOT EXISTS idx_transactions_date ON player_transactions(transaction_date);
CREATE INDEX IF NOT EXISTS idx_transactions_team_from ON player_transactions(from_team_id);
CREATE INDEX IF NOT EXISTS idx_transactions_team_to ON player_transactions(to_team_id);

-- ============================================================================
-- MIGRATION COMPLETE
-- ============================================================================
-- This schema provides complete support for:
-- ✓ All NFL transaction types (draft, free agency, trades, roster moves)
-- ✓ Player movement tracking (from_team → to_team)
-- ✓ Contract integration via contract_id foreign key
-- ✓ Event system integration via event_id reference
-- ✓ Dynasty isolation for multi-save support
-- ✓ Flexible JSON details storage for transaction-specific metadata
-- ✓ Efficient querying via comprehensive indexes
-- ============================================================================
