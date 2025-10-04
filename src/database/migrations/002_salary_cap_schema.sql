-- ============================================================================
-- NFL SALARY CAP SYSTEM - DATABASE SCHEMA
-- ============================================================================
-- Migration: 002
-- Description: Complete salary cap tables for contract management,
--              cap space tracking, franchise tags, and compliance
-- Date: 2025-10-04
-- Based on: 2024-2025 NFL CBA
-- ============================================================================

-- ============================================================================
-- PLAYER CONTRACTS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS player_contracts (
    contract_id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id INTEGER NOT NULL,
    team_id INTEGER NOT NULL,
    dynasty_id TEXT NOT NULL,

    -- Contract Duration
    start_year INTEGER NOT NULL,
    end_year INTEGER NOT NULL,
    contract_years INTEGER NOT NULL,  -- Total years

    -- Contract Type
    contract_type TEXT NOT NULL CHECK(contract_type IN (
        'ROOKIE', 'VETERAN', 'FRANCHISE_TAG', 'TRANSITION_TAG', 'EXTENSION'
    )),

    -- Financial Terms
    total_value INTEGER NOT NULL,
    signing_bonus INTEGER DEFAULT 0,
    signing_bonus_proration INTEGER DEFAULT 0,  -- Annual proration amount

    -- Guarantees
    guaranteed_at_signing INTEGER DEFAULT 0,
    injury_guaranteed INTEGER DEFAULT 0,
    total_guaranteed INTEGER DEFAULT 0,

    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    signed_date DATE NOT NULL,
    voided_date DATE,

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

    -- Note: Foreign keys would reference players/teams tables
);

CREATE INDEX IF NOT EXISTS idx_contracts_player ON player_contracts(player_id);
CREATE INDEX IF NOT EXISTS idx_contracts_team_season ON player_contracts(team_id, start_year);
CREATE INDEX IF NOT EXISTS idx_contracts_dynasty ON player_contracts(dynasty_id);
CREATE INDEX IF NOT EXISTS idx_contracts_active ON player_contracts(is_active);
CREATE INDEX IF NOT EXISTS idx_contracts_team_active ON player_contracts(team_id, is_active);


-- ============================================================================
-- CONTRACT YEAR DETAILS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS contract_year_details (
    detail_id INTEGER PRIMARY KEY AUTOINCREMENT,
    contract_id INTEGER NOT NULL,
    contract_year INTEGER NOT NULL,  -- 1, 2, 3, etc. (relative to contract)
    season_year INTEGER NOT NULL,    -- 2025, 2026, etc. (absolute)

    -- Salary Components
    base_salary INTEGER NOT NULL,
    roster_bonus INTEGER DEFAULT 0,
    workout_bonus INTEGER DEFAULT 0,
    option_bonus INTEGER DEFAULT 0,
    per_game_roster_bonus INTEGER DEFAULT 0,

    -- Performance Incentives
    ltbe_incentives INTEGER DEFAULT 0,  -- Likely To Be Earned
    nltbe_incentives INTEGER DEFAULT 0, -- Not Likely To Be Earned

    -- Guarantees for this year
    base_salary_guaranteed BOOLEAN DEFAULT FALSE,
    guarantee_type TEXT CHECK(guarantee_type IN ('FULL', 'INJURY', 'SKILL', 'NONE') OR guarantee_type IS NULL),
    guarantee_date DATE,   -- When guarantee vests

    -- Cap Impact
    signing_bonus_proration INTEGER DEFAULT 0,
    option_bonus_proration INTEGER DEFAULT 0,
    total_cap_hit INTEGER NOT NULL,

    -- Cash Flow
    cash_paid INTEGER NOT NULL,  -- Actual cash in this year

    -- Status
    is_voided BOOLEAN DEFAULT FALSE,

    FOREIGN KEY (contract_id) REFERENCES player_contracts(contract_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_contract_details_contract ON contract_year_details(contract_id);
CREATE INDEX IF NOT EXISTS idx_contract_details_season ON contract_year_details(season_year);
CREATE INDEX IF NOT EXISTS idx_contract_details_contract_year ON contract_year_details(contract_id, contract_year);


-- ============================================================================
-- TEAM SALARY CAP TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS team_salary_cap (
    cap_id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id INTEGER NOT NULL,
    season INTEGER NOT NULL,
    dynasty_id TEXT NOT NULL,

    -- Cap Limits
    salary_cap_limit INTEGER NOT NULL,  -- League-wide cap (e.g., $279.2M)

    -- Carryover
    carryover_from_previous INTEGER DEFAULT 0,

    -- Current Status
    active_contracts_total INTEGER DEFAULT 0,
    dead_money_total INTEGER DEFAULT 0,
    ltbe_incentives_total INTEGER DEFAULT 0,
    practice_squad_total INTEGER DEFAULT 0,

    -- Top 51 Rule (offseason only)
    is_top_51_active BOOLEAN DEFAULT TRUE,
    top_51_total INTEGER DEFAULT 0,

    -- Cash Spending (for 89% floor validation)
    cash_spent_this_year INTEGER DEFAULT 0,

    -- Metadata
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(team_id, season, dynasty_id)
);

CREATE INDEX IF NOT EXISTS idx_cap_team_season ON team_salary_cap(team_id, season);
CREATE INDEX IF NOT EXISTS idx_cap_dynasty ON team_salary_cap(dynasty_id);
CREATE INDEX IF NOT EXISTS idx_cap_season ON team_salary_cap(season);


-- ============================================================================
-- FRANCHISE TAGS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS franchise_tags (
    tag_id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id INTEGER NOT NULL,
    team_id INTEGER NOT NULL,
    season INTEGER NOT NULL,
    dynasty_id TEXT NOT NULL,

    -- Tag Details
    tag_type TEXT NOT NULL CHECK(tag_type IN (
        'FRANCHISE_EXCLUSIVE', 'FRANCHISE_NON_EXCLUSIVE', 'TRANSITION'
    )),
    tag_salary INTEGER NOT NULL,

    -- Dates
    tag_date DATE NOT NULL,
    deadline_date DATE NOT NULL,  -- March 4
    extension_deadline DATE,       -- Mid-July

    -- Status
    is_extended BOOLEAN DEFAULT FALSE,
    extension_contract_id INTEGER,  -- If player signed extension

    -- Consecutive Tag Tracking
    consecutive_tag_number INTEGER DEFAULT 1,  -- 1st, 2nd, 3rd tag

    FOREIGN KEY (extension_contract_id) REFERENCES player_contracts(contract_id)
);

CREATE INDEX IF NOT EXISTS idx_tags_player ON franchise_tags(player_id);
CREATE INDEX IF NOT EXISTS idx_tags_team_season ON franchise_tags(team_id, season);
CREATE INDEX IF NOT EXISTS idx_tags_season ON franchise_tags(season);


-- ============================================================================
-- RFA TENDERS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS rfa_tenders (
    tender_id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id INTEGER NOT NULL,
    team_id INTEGER NOT NULL,
    season INTEGER NOT NULL,
    dynasty_id TEXT NOT NULL,

    -- Tender Details
    tender_level TEXT NOT NULL CHECK(tender_level IN (
        'FIRST_ROUND', 'SECOND_ROUND', 'ORIGINAL_ROUND', 'RIGHT_OF_FIRST_REFUSAL'
    )),
    tender_salary INTEGER NOT NULL,
    compensation_round INTEGER,   -- NULL if right of first refusal only

    -- Dates
    tender_date DATE NOT NULL,
    offer_sheet_deadline DATE,    -- April 22

    -- Status
    is_accepted BOOLEAN DEFAULT FALSE,
    has_offer_sheet BOOLEAN DEFAULT FALSE,
    is_matched BOOLEAN  -- NULL if no offer sheet
);

CREATE INDEX IF NOT EXISTS idx_tenders_player ON rfa_tenders(player_id);
CREATE INDEX IF NOT EXISTS idx_tenders_team_season ON rfa_tenders(team_id, season);
CREATE INDEX IF NOT EXISTS idx_tenders_season ON rfa_tenders(season);


-- ============================================================================
-- DEAD MONEY TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS dead_money (
    dead_money_id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id INTEGER NOT NULL,
    player_id INTEGER NOT NULL,
    season INTEGER NOT NULL,
    dynasty_id TEXT NOT NULL,

    -- Source
    contract_id INTEGER NOT NULL,
    release_date DATE NOT NULL,

    -- Dead Money Amount
    dead_money_amount INTEGER NOT NULL,

    -- June 1 Designation
    is_june_1_designation BOOLEAN DEFAULT FALSE,
    current_year_dead_money INTEGER NOT NULL,
    next_year_dead_money INTEGER DEFAULT 0,

    -- Breakdown
    remaining_signing_bonus INTEGER NOT NULL,
    guaranteed_salary INTEGER DEFAULT 0,

    FOREIGN KEY (contract_id) REFERENCES player_contracts(contract_id)
);

CREATE INDEX IF NOT EXISTS idx_dead_money_team_season ON dead_money(team_id, season);
CREATE INDEX IF NOT EXISTS idx_dead_money_contract ON dead_money(contract_id);
CREATE INDEX IF NOT EXISTS idx_dead_money_dynasty ON dead_money(dynasty_id);


-- ============================================================================
-- CAP TRANSACTIONS LOG TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS cap_transactions (
    transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id INTEGER NOT NULL,
    season INTEGER NOT NULL,
    dynasty_id TEXT NOT NULL,

    -- Transaction Type
    transaction_type TEXT NOT NULL CHECK(transaction_type IN (
        'SIGNING', 'RELEASE', 'RESTRUCTURE', 'TRADE', 'TAG', 'TENDER'
    )),

    -- Related Entities
    player_id INTEGER,
    contract_id INTEGER,

    -- Transaction Date
    transaction_date DATE NOT NULL,

    -- Cap Impact
    cap_impact_current INTEGER DEFAULT 0,   -- Impact on current year cap
    cap_impact_future TEXT,                 -- JSON: {"2026": -5000000, "2027": -4000000}

    -- Cash Impact
    cash_impact INTEGER DEFAULT 0,

    -- Dead Money Created
    dead_money_created INTEGER DEFAULT 0,

    -- Description
    description TEXT,

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (contract_id) REFERENCES player_contracts(contract_id)
);

CREATE INDEX IF NOT EXISTS idx_transactions_team_season ON cap_transactions(team_id, season);
CREATE INDEX IF NOT EXISTS idx_transactions_type ON cap_transactions(transaction_type);
CREATE INDEX IF NOT EXISTS idx_transactions_date ON cap_transactions(transaction_date);
CREATE INDEX IF NOT EXISTS idx_transactions_dynasty ON cap_transactions(dynasty_id);


-- ============================================================================
-- LEAGUE SALARY CAP HISTORY TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS league_salary_cap_history (
    season INTEGER PRIMARY KEY,
    salary_cap_amount INTEGER NOT NULL,
    increase_from_previous INTEGER,
    increase_percentage REAL,

    -- Metadata
    announcement_date DATE,
    notes TEXT
);

-- Prepopulate with historical and projected data
INSERT OR IGNORE INTO league_salary_cap_history (season, salary_cap_amount, increase_from_previous, increase_percentage) VALUES
    (2023, 224800000, NULL, NULL),
    (2024, 255400000, 30600000, 13.6),
    (2025, 279200000, 23800000, 9.3),
    (2026, 295000000, 15800000, 5.7),  -- Projected
    (2027, 310000000, 15000000, 5.1),  -- Projected
    (2028, 325000000, 15000000, 4.8),  -- Projected
    (2029, 340000000, 15000000, 4.6),  -- Projected
    (2030, 355000000, 15000000, 4.4);  -- Projected

-- ============================================================================
-- VIEWS FOR CONVENIENCE
-- ============================================================================

-- View: Current Year Contracts with Cap Hits
CREATE VIEW IF NOT EXISTS vw_current_contracts AS
SELECT
    c.contract_id,
    c.player_id,
    c.team_id,
    c.dynasty_id,
    c.contract_type,
    c.start_year,
    c.end_year,
    c.total_value,
    c.signing_bonus,
    c.is_active,
    cyd.season_year,
    cyd.base_salary,
    cyd.total_cap_hit,
    cyd.cash_paid,
    cyd.base_salary_guaranteed
FROM player_contracts c
JOIN contract_year_details cyd ON c.contract_id = cyd.contract_id
WHERE c.is_active = TRUE;

-- View: Team Cap Summary
CREATE VIEW IF NOT EXISTS vw_team_cap_summary AS
SELECT
    tsc.team_id,
    tsc.season,
    tsc.dynasty_id,
    tsc.salary_cap_limit,
    tsc.carryover_from_previous,
    (tsc.salary_cap_limit + tsc.carryover_from_previous) as total_cap_available,
    tsc.active_contracts_total,
    tsc.dead_money_total,
    tsc.ltbe_incentives_total,
    tsc.practice_squad_total,
    tsc.top_51_total,
    (tsc.active_contracts_total + tsc.dead_money_total + tsc.ltbe_incentives_total + tsc.practice_squad_total) as total_cap_used,
    (tsc.salary_cap_limit + tsc.carryover_from_previous - tsc.active_contracts_total - tsc.dead_money_total - tsc.ltbe_incentives_total - tsc.practice_squad_total) as cap_space_available,
    tsc.is_top_51_active,
    tsc.cash_spent_this_year
FROM team_salary_cap tsc;

-- ============================================================================
-- MIGRATION COMPLETE
-- ============================================================================
-- This schema provides complete support for:
-- ✓ Player contracts with year-by-year details
-- ✓ Salary cap tracking per team/season/dynasty
-- ✓ Franchise tags and RFA tenders
-- ✓ Dead money calculation and tracking
-- ✓ Complete transaction logging
-- ✓ Historical cap data
-- ✓ Dynasty isolation for multi-save support
-- ============================================================================
