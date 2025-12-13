-- Game Cycle Database Schema
-- Lightweight schema for stage-based NFL season progression

-- Teams (32 NFL teams - reference data)
CREATE TABLE IF NOT EXISTS teams (
    team_id INTEGER PRIMARY KEY CHECK(team_id BETWEEN 1 AND 32),
    name TEXT NOT NULL,
    abbreviation TEXT NOT NULL,
    conference TEXT NOT NULL CHECK(conference IN ('AFC', 'NFC')),
    division TEXT NOT NULL CHECK(division IN ('North', 'South', 'East', 'West')),
    UNIQUE(name),
    UNIQUE(abbreviation)
);

-- Standings with dynasty/season isolation
CREATE TABLE IF NOT EXISTS standings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dynasty_id TEXT NOT NULL,
    team_id INTEGER NOT NULL CHECK(team_id BETWEEN 1 AND 32),
    season INTEGER NOT NULL,
    season_type TEXT NOT NULL DEFAULT 'regular_season',
    wins INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0,
    ties INTEGER DEFAULT 0,
    points_for INTEGER DEFAULT 0,
    points_against INTEGER DEFAULT 0,
    division_wins INTEGER DEFAULT 0,
    division_losses INTEGER DEFAULT 0,
    conference_wins INTEGER DEFAULT 0,
    conference_losses INTEGER DEFAULT 0,
    home_wins INTEGER DEFAULT 0,
    home_losses INTEGER DEFAULT 0,
    away_wins INTEGER DEFAULT 0,
    away_losses INTEGER DEFAULT 0,
    playoff_seed INTEGER,
    FOREIGN KEY (team_id) REFERENCES teams(team_id),
    FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE,
    UNIQUE(dynasty_id, season, team_id, season_type)
);

CREATE INDEX IF NOT EXISTS idx_standings_dynasty ON standings(dynasty_id);
CREATE INDEX IF NOT EXISTS idx_standings_season ON standings(dynasty_id, season);
CREATE INDEX IF NOT EXISTS idx_standings_team ON standings(dynasty_id, team_id);

-- Schedule for games (regular season and playoffs)
CREATE TABLE IF NOT EXISTS schedule (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    week INTEGER,                           -- 1-18 for regular season, NULL for playoffs
    round_name TEXT,                        -- 'wild_card', 'divisional', 'conference', 'super_bowl'
    home_team_id INTEGER NOT NULL CHECK(home_team_id BETWEEN 1 AND 32),
    away_team_id INTEGER NOT NULL CHECK(away_team_id BETWEEN 1 AND 32),
    home_score INTEGER,
    away_score INTEGER,
    is_played INTEGER DEFAULT 0,
    is_divisional INTEGER DEFAULT 0,        -- 1 if divisional game
    is_conference INTEGER DEFAULT 0,        -- 1 if conference game
    FOREIGN KEY (home_team_id) REFERENCES teams(team_id),
    FOREIGN KEY (away_team_id) REFERENCES teams(team_id),
    CHECK(home_team_id != away_team_id)
);

-- Stage state persistence
CREATE TABLE IF NOT EXISTS stage_state (
    id INTEGER PRIMARY KEY CHECK(id = 1),   -- Single row table
    season_year INTEGER NOT NULL,
    current_stage TEXT NOT NULL,            -- e.g., 'REGULAR_WEEK_1', 'WILD_CARD'
    phase TEXT NOT NULL                     -- 'PRESEASON', 'REGULAR_SEASON', 'PLAYOFFS', 'OFFSEASON'
);

-- Playoff bracket tracking (dynasty/season isolated)
CREATE TABLE IF NOT EXISTS playoff_bracket (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dynasty_id TEXT NOT NULL,               -- Dynasty isolation
    season INTEGER NOT NULL,                -- Season year
    round_name TEXT NOT NULL,               -- 'wild_card', 'divisional', 'conference', 'super_bowl'
    conference TEXT NOT NULL CHECK(conference IN ('AFC', 'NFC', 'SUPER_BOWL')),
    game_number INTEGER NOT NULL,           -- 1-3 for wild card, 1-2 for divisional, 1 for conference/SB
    higher_seed INTEGER,                    -- team_id of higher seed (home team)
    lower_seed INTEGER,                     -- team_id of lower seed (away team)
    winner INTEGER,                         -- team_id of winner (NULL until played)
    home_score INTEGER,
    away_score INTEGER,
    -- Note: Foreign keys removed because teams table is empty in game_cycle.db
    -- Team data lives in nfl_simulation.db
    UNIQUE(dynasty_id, season, round_name, conference, game_number)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_schedule_week ON schedule(week);
CREATE INDEX IF NOT EXISTS idx_schedule_round ON schedule(round_name);
CREATE INDEX IF NOT EXISTS idx_schedule_teams ON schedule(home_team_id, away_team_id);
CREATE INDEX IF NOT EXISTS idx_schedule_played ON schedule(is_played);
CREATE INDEX IF NOT EXISTS idx_playoff_round ON playoff_bracket(round_name);
CREATE INDEX IF NOT EXISTS idx_playoff_bracket_dynasty_season ON playoff_bracket(dynasty_id, season);

-- ============================================
-- Schedule Rotation Tables (Milestone 11)
-- NFL-compliant opponent rotation tracking
-- ============================================

-- Schedule rotation state - tracks opponent rotation across seasons
-- Each division has a deterministic opponent rotation for in-conference
-- (3-year cycle) and cross-conference (4-year cycle) games
CREATE TABLE IF NOT EXISTS schedule_rotation (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dynasty_id TEXT NOT NULL,
    season INTEGER NOT NULL,
    division_id INTEGER NOT NULL CHECK(division_id BETWEEN 1 AND 8),

    -- 3-year in-conference rotation
    -- Which in-conference division this division plays in full this season
    in_conference_opponent_div INTEGER NOT NULL CHECK(in_conference_opponent_div BETWEEN 1 AND 8),

    -- 4-year cross-conference rotation
    -- Which cross-conference division this division plays in full this season
    cross_conference_opponent_div INTEGER NOT NULL CHECK(cross_conference_opponent_div BETWEEN 1 AND 8),

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE,
    CHECK (in_conference_opponent_div != division_id),  -- Can't play own division
    UNIQUE(dynasty_id, season, division_id)
);

-- Indexes for schedule_rotation
CREATE INDEX IF NOT EXISTS idx_schedule_rotation_dynasty ON schedule_rotation(dynasty_id, season);
CREATE INDEX IF NOT EXISTS idx_schedule_rotation_division ON schedule_rotation(dynasty_id, division_id);

-- ============================================
-- Player and Contract Tables (for Re-signing)
-- ============================================

-- Dynasty tracking table
CREATE TABLE IF NOT EXISTS dynasties (
    dynasty_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    team_id INTEGER NOT NULL CHECK(team_id BETWEEN 1 AND 32),
    season_year INTEGER NOT NULL DEFAULT 2025,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (team_id) REFERENCES teams(team_id)
);

-- Dynasty state tracking
CREATE TABLE IF NOT EXISTS dynasty_state (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dynasty_id TEXT NOT NULL,
    season INTEGER NOT NULL,
    current_date TEXT,
    current_phase TEXT DEFAULT 'regular_season',
    current_week INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(dynasty_id, season),
    FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id)
);

-- Players table
CREATE TABLE IF NOT EXISTS players (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dynasty_id TEXT NOT NULL,
    player_id INTEGER NOT NULL,
    source_player_id TEXT,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    number INTEGER NOT NULL,
    team_id INTEGER NOT NULL,
    positions TEXT NOT NULL,
    attributes TEXT NOT NULL,
    contract_id INTEGER,
    status TEXT DEFAULT 'active',
    years_pro INTEGER DEFAULT 0,
    birthdate TEXT DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE,
    UNIQUE(dynasty_id, player_id)
);

-- Player contracts table
CREATE TABLE IF NOT EXISTS player_contracts (
    contract_id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id INTEGER NOT NULL,
    team_id INTEGER NOT NULL,
    dynasty_id TEXT NOT NULL,
    start_year INTEGER NOT NULL,
    end_year INTEGER NOT NULL,
    contract_years INTEGER NOT NULL,
    contract_type TEXT NOT NULL CHECK(contract_type IN (
        'ROOKIE', 'VETERAN', 'FRANCHISE_TAG', 'TRANSITION_TAG', 'EXTENSION'
    )),
    total_value INTEGER NOT NULL,
    signing_bonus INTEGER DEFAULT 0,
    signing_bonus_proration INTEGER DEFAULT 0,
    guaranteed_at_signing INTEGER DEFAULT 0,
    injury_guaranteed INTEGER DEFAULT 0,
    total_guaranteed INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    signed_date DATE NOT NULL,
    voided_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE
);

-- Contract year details table
CREATE TABLE IF NOT EXISTS contract_year_details (
    detail_id INTEGER PRIMARY KEY AUTOINCREMENT,
    contract_id INTEGER NOT NULL,
    contract_year INTEGER NOT NULL,
    season_year INTEGER NOT NULL,
    base_salary INTEGER NOT NULL,
    roster_bonus INTEGER DEFAULT 0,
    workout_bonus INTEGER DEFAULT 0,
    option_bonus INTEGER DEFAULT 0,
    per_game_roster_bonus INTEGER DEFAULT 0,
    ltbe_incentives INTEGER DEFAULT 0,
    nltbe_incentives INTEGER DEFAULT 0,
    base_salary_guaranteed BOOLEAN DEFAULT FALSE,
    guarantee_type TEXT CHECK(guarantee_type IN ('FULL', 'INJURY', 'SKILL', 'NONE') OR guarantee_type IS NULL),
    guarantee_date DATE,
    signing_bonus_proration INTEGER DEFAULT 0,
    option_bonus_proration INTEGER DEFAULT 0,
    total_cap_hit INTEGER NOT NULL,
    cash_paid INTEGER NOT NULL,
    is_voided BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (contract_id) REFERENCES player_contracts(contract_id) ON DELETE CASCADE
);

-- Indexes for player/contract tables
CREATE INDEX IF NOT EXISTS idx_players_dynasty ON players(dynasty_id);
CREATE INDEX IF NOT EXISTS idx_players_team ON players(dynasty_id, team_id);
CREATE INDEX IF NOT EXISTS idx_players_lookup ON players(dynasty_id, player_id);
CREATE INDEX IF NOT EXISTS idx_contracts_player ON player_contracts(player_id);
CREATE INDEX IF NOT EXISTS idx_contracts_team_season ON player_contracts(team_id, start_year);
CREATE INDEX IF NOT EXISTS idx_contracts_dynasty ON player_contracts(dynasty_id);
CREATE INDEX IF NOT EXISTS idx_contracts_active ON player_contracts(is_active);
CREATE INDEX IF NOT EXISTS idx_contracts_team_active ON player_contracts(team_id, is_active);
CREATE INDEX IF NOT EXISTS idx_contract_details_contract ON contract_year_details(contract_id);
CREATE INDEX IF NOT EXISTS idx_contract_details_season ON contract_year_details(season_year);

-- ============================================
-- Draft System Tables
-- ============================================

-- Draft Classes (metadata for each year's draft class)
CREATE TABLE IF NOT EXISTS draft_classes (
    draft_class_id TEXT PRIMARY KEY,
    dynasty_id TEXT NOT NULL,
    season INTEGER NOT NULL,
    generation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_prospects INTEGER DEFAULT 0,
    is_complete BOOLEAN DEFAULT FALSE,
    UNIQUE(dynasty_id, season),
    FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_draft_classes_dynasty ON draft_classes(dynasty_id);
CREATE INDEX IF NOT EXISTS idx_draft_classes_season ON draft_classes(dynasty_id, season);

-- Draft Prospects (individual prospects in draft class)
CREATE TABLE IF NOT EXISTS draft_prospects (
    prospect_id INTEGER PRIMARY KEY AUTOINCREMENT,
    draft_class_id TEXT NOT NULL,
    dynasty_id TEXT NOT NULL,
    player_id INTEGER,  -- NULL until drafted, then links to players table
    roster_player_id INTEGER,  -- Links to roster player after conversion (for tracking)
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    position TEXT NOT NULL,
    college TEXT,
    age INTEGER NOT NULL DEFAULT 21,
    height_inches INTEGER,
    weight_lbs INTEGER,
    overall INTEGER NOT NULL,
    potential INTEGER NOT NULL,
    attributes TEXT NOT NULL,  -- JSON blob of ratings
    combine_results TEXT,      -- JSON blob of combine data
    scouting_grade TEXT,       -- A+, A, B+, B, C+, C, D, F
    projected_round INTEGER,
    draft_rank INTEGER,        -- Overall board ranking
    is_drafted BOOLEAN DEFAULT FALSE,
    drafted_team_id INTEGER,
    draft_round INTEGER,
    draft_pick INTEGER,
    draft_overall_pick INTEGER,
    FOREIGN KEY (draft_class_id) REFERENCES draft_classes(draft_class_id) ON DELETE CASCADE,
    FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_prospects_draft_class ON draft_prospects(draft_class_id);
CREATE INDEX IF NOT EXISTS idx_prospects_dynasty ON draft_prospects(dynasty_id);
CREATE INDEX IF NOT EXISTS idx_prospects_position ON draft_prospects(dynasty_id, position);
CREATE INDEX IF NOT EXISTS idx_prospects_available ON draft_prospects(dynasty_id, is_drafted);
CREATE INDEX IF NOT EXISTS idx_prospects_overall ON draft_prospects(draft_class_id, overall DESC);
CREATE INDEX IF NOT EXISTS idx_prospects_player_id ON draft_prospects(player_id);
CREATE INDEX IF NOT EXISTS idx_prospects_roster_player_id ON draft_prospects(roster_player_id);

-- Draft Order (picks for each round)
CREATE TABLE IF NOT EXISTS draft_order (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dynasty_id TEXT NOT NULL,
    season INTEGER NOT NULL,
    round INTEGER NOT NULL CHECK(round BETWEEN 1 AND 7),
    pick INTEGER NOT NULL CHECK(pick BETWEEN 1 AND 32),
    overall_pick INTEGER NOT NULL,
    team_id INTEGER NOT NULL CHECK(team_id BETWEEN 1 AND 32),
    is_traded BOOLEAN DEFAULT FALSE,
    original_team_id INTEGER,
    prospect_id INTEGER,  -- NULL until pick is made
    is_completed BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE,
    FOREIGN KEY (team_id) REFERENCES teams(team_id),
    FOREIGN KEY (prospect_id) REFERENCES draft_prospects(prospect_id),
    UNIQUE(dynasty_id, season, overall_pick)
);

CREATE INDEX IF NOT EXISTS idx_draft_order_dynasty_season ON draft_order(dynasty_id, season);
CREATE INDEX IF NOT EXISTS idx_draft_order_team ON draft_order(dynasty_id, season, team_id);
CREATE INDEX IF NOT EXISTS idx_draft_order_pending ON draft_order(dynasty_id, season, is_completed);

-- ============================================
-- Waiver Wire Tables (for Roster Cuts)
-- ============================================

-- Waiver wire - tracks cut players available for claims
CREATE TABLE IF NOT EXISTS waiver_wire (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dynasty_id TEXT NOT NULL,
    player_id INTEGER NOT NULL,
    former_team_id INTEGER NOT NULL CHECK(former_team_id BETWEEN 1 AND 32),
    waiver_status TEXT DEFAULT 'on_waivers' CHECK(waiver_status IN ('on_waivers', 'claimed', 'cleared')),
    waiver_order INTEGER,               -- Priority position when added to waivers
    claiming_team_id INTEGER,           -- Team that successfully claimed (NULL until claimed)
    dead_money INTEGER DEFAULT 0,       -- Cap hit to former team
    cap_savings INTEGER DEFAULT 0,      -- Cap savings to former team
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    cleared_at TIMESTAMP,               -- When player cleared to free agency
    season INTEGER NOT NULL,
    FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE,
    FOREIGN KEY (former_team_id) REFERENCES teams(team_id),
    FOREIGN KEY (claiming_team_id) REFERENCES teams(team_id),
    UNIQUE(dynasty_id, player_id, season)
);

-- Waiver claims - tracks teams' pending claims
CREATE TABLE IF NOT EXISTS waiver_claims (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dynasty_id TEXT NOT NULL,
    season INTEGER NOT NULL,
    waiver_id INTEGER NOT NULL,         -- Reference to waiver_wire entry
    player_id INTEGER NOT NULL,
    claiming_team_id INTEGER NOT NULL CHECK(claiming_team_id BETWEEN 1 AND 32),
    claim_priority INTEGER NOT NULL,    -- Team's waiver priority (1 = highest, worst record)
    claim_status TEXT DEFAULT 'pending' CHECK(claim_status IN ('pending', 'awarded', 'lost')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP,
    FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE,
    FOREIGN KEY (waiver_id) REFERENCES waiver_wire(id) ON DELETE CASCADE,
    FOREIGN KEY (claiming_team_id) REFERENCES teams(team_id),
    UNIQUE(dynasty_id, season, player_id, claiming_team_id)
);

-- Indexes for waiver tables
CREATE INDEX IF NOT EXISTS idx_waiver_wire_dynasty ON waiver_wire(dynasty_id);
CREATE INDEX IF NOT EXISTS idx_waiver_wire_status ON waiver_wire(dynasty_id, waiver_status);
CREATE INDEX IF NOT EXISTS idx_waiver_wire_season ON waiver_wire(dynasty_id, season);
CREATE INDEX IF NOT EXISTS idx_waiver_claims_dynasty ON waiver_claims(dynasty_id);
CREATE INDEX IF NOT EXISTS idx_waiver_claims_player ON waiver_claims(dynasty_id, player_id);
CREATE INDEX IF NOT EXISTS idx_waiver_claims_team ON waiver_claims(dynasty_id, claiming_team_id);
CREATE INDEX IF NOT EXISTS idx_waiver_claims_pending ON waiver_claims(dynasty_id, season, claim_status);

-- ============================================
-- Player Transactions (Audit Trail)
-- ============================================

-- Player transactions table - logs all roster moves
CREATE TABLE IF NOT EXISTS player_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dynasty_id TEXT NOT NULL,
    season INTEGER NOT NULL,
    transaction_type TEXT NOT NULL,
    player_id INTEGER NOT NULL,
    first_name TEXT,
    last_name TEXT,
    position TEXT,
    from_team_id INTEGER,
    to_team_id INTEGER,
    transaction_date TEXT,
    details TEXT,
    contract_id INTEGER,
    event_id TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_player_transactions_dynasty ON player_transactions(dynasty_id);
CREATE INDEX IF NOT EXISTS idx_player_transactions_player ON player_transactions(player_id);
CREATE INDEX IF NOT EXISTS idx_player_transactions_type ON player_transactions(transaction_type);
CREATE INDEX IF NOT EXISTS idx_player_transactions_season ON player_transactions(dynasty_id, season);
CREATE INDEX IF NOT EXISTS idx_player_transactions_lastname ON player_transactions(last_name);
CREATE INDEX IF NOT EXISTS idx_player_transactions_from_team ON player_transactions(from_team_id);
CREATE INDEX IF NOT EXISTS idx_player_transactions_to_team ON player_transactions(to_team_id);

-- ============================================
-- Player Progression History (Career Tracking)
-- ============================================

-- Tracks player attribute changes from training camp each season
CREATE TABLE IF NOT EXISTS player_progression_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dynasty_id TEXT NOT NULL,
    player_id INTEGER NOT NULL,
    season INTEGER NOT NULL,
    age INTEGER NOT NULL,
    position TEXT,
    team_id INTEGER,
    age_category TEXT,              -- 'YOUNG', 'PRIME', 'VETERAN'
    overall_before INTEGER NOT NULL,
    overall_after INTEGER NOT NULL,
    overall_change INTEGER NOT NULL,
    attribute_changes TEXT,          -- JSON: [{"attr": "speed", "old": 80, "new": 82, "change": 2}, ...]
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE,
    UNIQUE(dynasty_id, player_id, season)
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_progression_dynasty ON player_progression_history(dynasty_id);
CREATE INDEX IF NOT EXISTS idx_progression_player ON player_progression_history(player_id);
CREATE INDEX IF NOT EXISTS idx_progression_season ON player_progression_history(season);
CREATE INDEX IF NOT EXISTS idx_progression_player_season ON player_progression_history(player_id, season);

-- ============================================
-- Injury System Tables
-- ============================================

-- Player injuries tracking
CREATE TABLE IF NOT EXISTS player_injuries (
    injury_id INTEGER PRIMARY KEY AUTOINCREMENT,
    dynasty_id TEXT NOT NULL,
    player_id INTEGER NOT NULL,
    season INTEGER NOT NULL,
    week_occurred INTEGER NOT NULL,
    injury_type TEXT NOT NULL,          -- 'concussion', 'acl_tear', 'ankle_sprain', etc.
    body_part TEXT NOT NULL,            -- 'head', 'knee', 'ankle', 'shoulder', etc.
    severity TEXT NOT NULL,             -- 'minor', 'moderate', 'severe', 'season_ending'
    estimated_weeks_out INTEGER NOT NULL,
    actual_weeks_out INTEGER,           -- Filled when player returns
    occurred_during TEXT NOT NULL,      -- 'game', 'practice'
    game_id TEXT,                       -- NULL if practice injury
    play_description TEXT,              -- What happened (optional)
    is_active INTEGER DEFAULT 1,        -- 1 = currently injured, 0 = recovered
    ir_placement_date TEXT,             -- NULL if not on IR
    ir_return_date TEXT,                -- NULL if not returned from IR
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE
);

-- IR tracking per team per season (8 return slots max)
CREATE TABLE IF NOT EXISTS ir_tracking (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dynasty_id TEXT NOT NULL,
    team_id INTEGER NOT NULL CHECK(team_id BETWEEN 1 AND 32),
    season INTEGER NOT NULL,
    ir_return_slots_used INTEGER DEFAULT 0,
    UNIQUE(dynasty_id, team_id, season),
    FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE
);

-- Indexes for injury queries
CREATE INDEX IF NOT EXISTS idx_injuries_dynasty ON player_injuries(dynasty_id);
CREATE INDEX IF NOT EXISTS idx_injuries_player ON player_injuries(dynasty_id, player_id);
CREATE INDEX IF NOT EXISTS idx_injuries_active ON player_injuries(dynasty_id, is_active);
CREATE INDEX IF NOT EXISTS idx_injuries_season_week ON player_injuries(dynasty_id, season, week_occurred);
CREATE INDEX IF NOT EXISTS idx_ir_tracking_team ON ir_tracking(dynasty_id, team_id, season);

-- ============================================
-- PLAYER PERSONAS TABLES (Milestone 6)
-- ============================================

-- Player Personas Table
CREATE TABLE IF NOT EXISTS player_personas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dynasty_id TEXT NOT NULL,
    player_id INTEGER NOT NULL,

    -- Primary persona type
    persona_type TEXT NOT NULL CHECK(persona_type IN (
        'ring_chaser', 'hometown_hero', 'money_first', 'big_market',
        'small_market', 'legacy_builder', 'competitor', 'system_fit'
    )),

    -- Preference weights (0-100)
    money_importance INTEGER DEFAULT 50 CHECK(money_importance BETWEEN 0 AND 100),
    winning_importance INTEGER DEFAULT 50 CHECK(winning_importance BETWEEN 0 AND 100),
    location_importance INTEGER DEFAULT 50 CHECK(location_importance BETWEEN 0 AND 100),
    playing_time_importance INTEGER DEFAULT 50 CHECK(playing_time_importance BETWEEN 0 AND 100),
    loyalty_importance INTEGER DEFAULT 50 CHECK(loyalty_importance BETWEEN 0 AND 100),
    market_size_importance INTEGER DEFAULT 50 CHECK(market_size_importance BETWEEN 0 AND 100),
    coaching_fit_importance INTEGER DEFAULT 50 CHECK(coaching_fit_importance BETWEEN 0 AND 100),
    relationships_importance INTEGER DEFAULT 50 CHECK(relationships_importance BETWEEN 0 AND 100),

    -- Biographical data
    birthplace_state TEXT,
    college_state TEXT,
    drafting_team_id INTEGER CHECK(drafting_team_id IS NULL OR drafting_team_id BETWEEN 1 AND 32),

    -- Career context (updated during career)
    career_earnings INTEGER DEFAULT 0 CHECK(career_earnings >= 0),
    championship_count INTEGER DEFAULT 0 CHECK(championship_count >= 0),
    pro_bowl_count INTEGER DEFAULT 0 CHECK(pro_bowl_count >= 0),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE,
    UNIQUE(dynasty_id, player_id)
);

-- Team Attractiveness (per-season snapshot)
CREATE TABLE IF NOT EXISTS team_attractiveness (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dynasty_id TEXT NOT NULL,
    team_id INTEGER NOT NULL CHECK(team_id BETWEEN 1 AND 32),
    season INTEGER NOT NULL,

    -- Dynamic factors (updated each season)
    playoff_appearances_5yr INTEGER DEFAULT 0 CHECK(playoff_appearances_5yr BETWEEN 0 AND 5),
    super_bowl_wins_5yr INTEGER DEFAULT 0 CHECK(super_bowl_wins_5yr BETWEEN 0 AND 5),
    winning_culture_score INTEGER DEFAULT 50 CHECK(winning_culture_score BETWEEN 0 AND 100),
    coaching_prestige INTEGER DEFAULT 50 CHECK(coaching_prestige BETWEEN 0 AND 100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE,
    UNIQUE(dynasty_id, team_id, season)
);

-- Season Results History (for 5-year window calculations)
CREATE TABLE IF NOT EXISTS team_season_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dynasty_id TEXT NOT NULL,
    team_id INTEGER NOT NULL CHECK(team_id BETWEEN 1 AND 32),
    season INTEGER NOT NULL,
    wins INTEGER NOT NULL CHECK(wins >= 0 AND wins <= 17),
    losses INTEGER NOT NULL CHECK(losses >= 0 AND losses <= 17),
    made_playoffs INTEGER DEFAULT 0 CHECK(made_playoffs IN (0, 1)),
    playoff_round_reached TEXT CHECK(playoff_round_reached IS NULL OR playoff_round_reached IN (
        'wild_card', 'divisional', 'conference', 'super_bowl'
    )),
    won_super_bowl INTEGER DEFAULT 0 CHECK(won_super_bowl IN (0, 1)),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE,
    UNIQUE(dynasty_id, team_id, season)
);

-- Indexes for player_personas
CREATE INDEX IF NOT EXISTS idx_personas_dynasty ON player_personas(dynasty_id);
CREATE INDEX IF NOT EXISTS idx_personas_player ON player_personas(dynasty_id, player_id);

-- Indexes for team_attractiveness
CREATE INDEX IF NOT EXISTS idx_attractiveness_dynasty ON team_attractiveness(dynasty_id);
CREATE INDEX IF NOT EXISTS idx_attractiveness_team_season ON team_attractiveness(dynasty_id, team_id, season);

-- Indexes for team_season_history
CREATE INDEX IF NOT EXISTS idx_team_history_dynasty ON team_season_history(dynasty_id);
CREATE INDEX IF NOT EXISTS idx_team_history_team ON team_season_history(dynasty_id, team_id, season);

-- ============================================
-- TRADE SYSTEM TABLES (Milestone 6)
-- ============================================

-- Trade tracking table
CREATE TABLE IF NOT EXISTS trades (
    trade_id INTEGER PRIMARY KEY AUTOINCREMENT,
    dynasty_id TEXT NOT NULL,
    season INTEGER NOT NULL,
    trade_date TEXT NOT NULL,
    team1_id INTEGER NOT NULL CHECK(team1_id BETWEEN 1 AND 32),
    team2_id INTEGER NOT NULL CHECK(team2_id BETWEEN 1 AND 32),
    team1_assets TEXT NOT NULL,      -- JSON array of TradeAsset dicts
    team2_assets TEXT NOT NULL,      -- JSON array of TradeAsset dicts
    team1_total_value REAL NOT NULL,
    team2_total_value REAL NOT NULL,
    value_ratio REAL NOT NULL,       -- team2_value / team1_value
    fairness_rating TEXT NOT NULL CHECK(fairness_rating IN ('VERY_FAIR', 'FAIR', 'SLIGHTLY_UNFAIR', 'UNFAIR', 'VERY_UNFAIR')),
    status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'accepted', 'rejected', 'countered')),
    initiating_team_id INTEGER NOT NULL CHECK(initiating_team_id BETWEEN 1 AND 32),
    rounds_negotiated INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE
);

-- Draft pick ownership tracking (for trading picks)
CREATE TABLE IF NOT EXISTS draft_pick_ownership (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dynasty_id TEXT NOT NULL,
    season INTEGER NOT NULL,
    round INTEGER NOT NULL CHECK(round BETWEEN 1 AND 7),
    original_team_id INTEGER NOT NULL CHECK(original_team_id BETWEEN 1 AND 32),
    current_team_id INTEGER NOT NULL CHECK(current_team_id BETWEEN 1 AND 32),
    acquired_via_trade_id INTEGER,
    UNIQUE(dynasty_id, season, round, original_team_id),
    FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE,
    FOREIGN KEY (acquired_via_trade_id) REFERENCES trades(trade_id)
);

-- Indexes for trade tables
CREATE INDEX IF NOT EXISTS idx_trades_dynasty_season ON trades(dynasty_id, season);
CREATE INDEX IF NOT EXISTS idx_trades_teams ON trades(dynasty_id, team1_id, team2_id);
CREATE INDEX IF NOT EXISTS idx_trades_status ON trades(dynasty_id, status);
CREATE INDEX IF NOT EXISTS idx_pick_ownership_team ON draft_pick_ownership(dynasty_id, current_team_id, season);
CREATE INDEX IF NOT EXISTS idx_pick_ownership_season ON draft_pick_ownership(dynasty_id, season);

-- ============================================
-- ADVANCED ANALYTICS TABLES (Milestone 7)
-- PFF-style player grading and advanced metrics
-- ============================================

-- Per-play grades (FULL simulation mode only)
-- Stores granular per-play grades for detailed breakdown analysis
CREATE TABLE IF NOT EXISTS player_play_grades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dynasty_id TEXT NOT NULL,
    game_id TEXT NOT NULL,
    play_number INTEGER NOT NULL,

    player_id INTEGER NOT NULL,
    team_id INTEGER NOT NULL CHECK(team_id BETWEEN 1 AND 32),
    position TEXT NOT NULL,

    -- Play context
    quarter INTEGER CHECK(quarter BETWEEN 1 AND 5),  -- 5 for OT
    down INTEGER CHECK(down BETWEEN 1 AND 4),
    distance INTEGER,
    yard_line INTEGER CHECK(yard_line BETWEEN 1 AND 99),
    game_clock INTEGER,              -- Seconds remaining in quarter
    score_differential INTEGER,      -- Positive = player's team leading
    play_type TEXT NOT NULL,         -- 'pass', 'run', 'field_goal', 'punt', 'kickoff'
    is_offense INTEGER DEFAULT 1,    -- 1 = offense, 0 = defense

    -- Grade (0-100 scale, 60 = neutral)
    play_grade REAL NOT NULL CHECK(play_grade BETWEEN 0 AND 100),

    -- Position-specific sub-component grades (stored for detailed breakdown)
    grade_component_1 REAL,          -- e.g., accuracy for QB, vision for RB
    grade_component_2 REAL,          -- e.g., decision for QB, elusiveness for RB
    grade_component_3 REAL,          -- e.g., pocket_presence for QB, blocking for RB

    -- Play outcome
    was_positive_play INTEGER DEFAULT 0,  -- 1 if grade >= 70
    epa_contribution REAL,                -- Expected Points Added contribution

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE
);

-- Indexes for play grades
CREATE INDEX IF NOT EXISTS idx_play_grades_game ON player_play_grades(dynasty_id, game_id);
CREATE INDEX IF NOT EXISTS idx_play_grades_player ON player_play_grades(dynasty_id, player_id);
CREATE INDEX IF NOT EXISTS idx_play_grades_position ON player_play_grades(dynasty_id, position);

-- ============================================================
-- Player Game Stats (per-player per-game statistics)
-- Required for awards calculation via aggregate_season_grades_from_stats()
-- ============================================================
CREATE TABLE IF NOT EXISTS player_game_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dynasty_id TEXT NOT NULL,
    game_id TEXT NOT NULL,
    season_type TEXT NOT NULL DEFAULT 'regular_season',
    player_id TEXT NOT NULL,
    player_name TEXT,
    team_id INTEGER NOT NULL,
    position TEXT,

    -- Passing stats
    passing_yards INTEGER DEFAULT 0,
    passing_tds INTEGER DEFAULT 0,
    passing_attempts INTEGER DEFAULT 0,
    passing_completions INTEGER DEFAULT 0,
    passing_interceptions INTEGER DEFAULT 0,
    passing_sacks INTEGER DEFAULT 0,
    passing_sack_yards INTEGER DEFAULT 0,
    passing_rating REAL DEFAULT 0,
    air_yards INTEGER DEFAULT 0,

    -- Rushing stats
    rushing_yards INTEGER DEFAULT 0,
    rushing_tds INTEGER DEFAULT 0,
    rushing_attempts INTEGER DEFAULT 0,
    rushing_long INTEGER DEFAULT 0,
    rushing_fumbles INTEGER DEFAULT 0,
    yards_after_contact INTEGER DEFAULT 0,

    -- Receiving stats
    receiving_yards INTEGER DEFAULT 0,
    receiving_tds INTEGER DEFAULT 0,
    receptions INTEGER DEFAULT 0,
    targets INTEGER DEFAULT 0,
    receiving_long INTEGER DEFAULT 0,
    receiving_drops INTEGER DEFAULT 0,
    yards_after_catch INTEGER DEFAULT 0,

    -- Defensive stats
    tackles_total INTEGER DEFAULT 0,
    tackles_solo INTEGER DEFAULT 0,
    tackles_assist INTEGER DEFAULT 0,
    sacks REAL DEFAULT 0,
    interceptions INTEGER DEFAULT 0,
    forced_fumbles INTEGER DEFAULT 0,
    fumbles_recovered INTEGER DEFAULT 0,
    passes_defended INTEGER DEFAULT 0,
    tackles_for_loss INTEGER DEFAULT 0,
    qb_hits INTEGER DEFAULT 0,
    qb_pressures INTEGER DEFAULT 0,

    -- Coverage stats (DB/LB grading metrics)
    coverage_targets INTEGER DEFAULT 0,
    coverage_completions INTEGER DEFAULT 0,
    coverage_yards_allowed INTEGER DEFAULT 0,

    -- Pass rush stats (DL grading metrics)
    pass_rush_wins INTEGER DEFAULT 0,
    pass_rush_attempts INTEGER DEFAULT 0,
    times_double_teamed INTEGER DEFAULT 0,
    blocking_encounters INTEGER DEFAULT 0,

    -- Ball carrier advanced stats (RB/WR grading)
    broken_tackles INTEGER DEFAULT 0,
    tackles_faced INTEGER DEFAULT 0,

    -- QB advanced stats
    time_to_throw_total REAL DEFAULT 0.0,
    throw_count INTEGER DEFAULT 0,

    -- Special teams stats
    field_goals_made INTEGER DEFAULT 0,
    field_goals_attempted INTEGER DEFAULT 0,
    extra_points_made INTEGER DEFAULT 0,
    extra_points_attempted INTEGER DEFAULT 0,
    punts INTEGER DEFAULT 0,
    punt_yards INTEGER DEFAULT 0,
    net_punt_yards INTEGER DEFAULT 0,
    long_punt INTEGER DEFAULT 0,
    punts_inside_20 INTEGER DEFAULT 0,

    -- Offensive Line stats
    pancakes INTEGER DEFAULT 0,
    sacks_allowed INTEGER DEFAULT 0,
    hurries_allowed INTEGER DEFAULT 0,
    pressures_allowed INTEGER DEFAULT 0,
    pass_blocks INTEGER DEFAULT 0,
    run_blocking_grade REAL DEFAULT 0.0,
    pass_blocking_efficiency REAL DEFAULT 0.0,
    missed_assignments INTEGER DEFAULT 0,
    holding_penalties INTEGER DEFAULT 0,
    false_start_penalties INTEGER DEFAULT 0,
    downfield_blocks INTEGER DEFAULT 0,
    double_team_blocks INTEGER DEFAULT 0,
    chip_blocks INTEGER DEFAULT 0,

    -- Performance metrics
    snap_counts_offense INTEGER DEFAULT 0,
    snap_counts_defense INTEGER DEFAULT 0,
    snap_counts_special_teams INTEGER DEFAULT 0,
    fantasy_points REAL DEFAULT 0,

    -- Prevent duplicate stats for same player in same game
    UNIQUE(dynasty_id, game_id, player_id, season_type),
    FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id)
);

-- Indexes for player_game_stats
CREATE INDEX IF NOT EXISTS idx_player_stats_dynasty ON player_game_stats(dynasty_id, game_id);
CREATE INDEX IF NOT EXISTS idx_player_stats_player ON player_game_stats(player_id, dynasty_id);
CREATE INDEX IF NOT EXISTS idx_player_stats_team_game ON player_game_stats(dynasty_id, team_id, game_id);
CREATE INDEX IF NOT EXISTS idx_player_stats_team ON player_game_stats(dynasty_id, team_id);
CREATE INDEX IF NOT EXISTS idx_player_stats_season_type ON player_game_stats(dynasty_id, season_type);

-- Game-aggregated grades
-- Stores weighted average of play grades for each player per game
CREATE TABLE IF NOT EXISTS player_game_grades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dynasty_id TEXT NOT NULL,
    game_id TEXT NOT NULL,
    season INTEGER NOT NULL,
    week INTEGER NOT NULL,

    player_id INTEGER NOT NULL,
    team_id INTEGER NOT NULL CHECK(team_id BETWEEN 1 AND 32),
    position TEXT NOT NULL,

    -- Overall game grade (weighted average of play grades)
    overall_grade REAL NOT NULL CHECK(overall_grade BETWEEN 0 AND 100),

    -- Position-specific sub-grades (NULL if not applicable to position)
    passing_grade REAL CHECK(passing_grade IS NULL OR passing_grade BETWEEN 0 AND 100),
    rushing_grade REAL CHECK(rushing_grade IS NULL OR rushing_grade BETWEEN 0 AND 100),
    receiving_grade REAL CHECK(receiving_grade IS NULL OR receiving_grade BETWEEN 0 AND 100),
    pass_blocking_grade REAL CHECK(pass_blocking_grade IS NULL OR pass_blocking_grade BETWEEN 0 AND 100),
    run_blocking_grade REAL CHECK(run_blocking_grade IS NULL OR run_blocking_grade BETWEEN 0 AND 100),
    pass_rush_grade REAL CHECK(pass_rush_grade IS NULL OR pass_rush_grade BETWEEN 0 AND 100),
    run_defense_grade REAL CHECK(run_defense_grade IS NULL OR run_defense_grade BETWEEN 0 AND 100),
    coverage_grade REAL CHECK(coverage_grade IS NULL OR coverage_grade BETWEEN 0 AND 100),
    tackling_grade REAL CHECK(tackling_grade IS NULL OR tackling_grade BETWEEN 0 AND 100),

    -- Snap counts (for weighting and context)
    offensive_snaps INTEGER DEFAULT 0,
    defensive_snaps INTEGER DEFAULT 0,
    special_teams_snaps INTEGER DEFAULT 0,

    -- Advanced metrics for this game
    epa_total REAL DEFAULT 0.0,
    success_rate REAL CHECK(success_rate IS NULL OR success_rate BETWEEN 0 AND 1),

    -- Play tracking
    play_count INTEGER DEFAULT 0,
    positive_plays INTEGER DEFAULT 0,
    negative_plays INTEGER DEFAULT 0,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE,
    UNIQUE(dynasty_id, game_id, player_id)
);

-- Indexes for game grades
CREATE INDEX IF NOT EXISTS idx_game_grades_dynasty_season ON player_game_grades(dynasty_id, season);
CREATE INDEX IF NOT EXISTS idx_game_grades_player ON player_game_grades(dynasty_id, player_id);
CREATE INDEX IF NOT EXISTS idx_game_grades_team ON player_game_grades(dynasty_id, team_id, season);
CREATE INDEX IF NOT EXISTS idx_game_grades_position ON player_game_grades(dynasty_id, position, season);
CREATE INDEX IF NOT EXISTS idx_game_grades_game ON player_game_grades(dynasty_id, game_id);

-- Season-aggregated grades with rankings
-- Stores weighted average of game grades with position and overall rankings
CREATE TABLE IF NOT EXISTS player_season_grades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dynasty_id TEXT NOT NULL,
    season INTEGER NOT NULL,

    player_id INTEGER NOT NULL,
    team_id INTEGER NOT NULL CHECK(team_id BETWEEN 1 AND 32),
    position TEXT NOT NULL,

    -- Overall season grade (weighted by snap count)
    overall_grade REAL NOT NULL CHECK(overall_grade BETWEEN 0 AND 100),

    -- Position-specific season grades
    passing_grade REAL CHECK(passing_grade IS NULL OR passing_grade BETWEEN 0 AND 100),
    rushing_grade REAL CHECK(rushing_grade IS NULL OR rushing_grade BETWEEN 0 AND 100),
    receiving_grade REAL CHECK(receiving_grade IS NULL OR receiving_grade BETWEEN 0 AND 100),
    pass_blocking_grade REAL CHECK(pass_blocking_grade IS NULL OR pass_blocking_grade BETWEEN 0 AND 100),
    run_blocking_grade REAL CHECK(run_blocking_grade IS NULL OR run_blocking_grade BETWEEN 0 AND 100),
    pass_rush_grade REAL CHECK(pass_rush_grade IS NULL OR pass_rush_grade BETWEEN 0 AND 100),
    run_defense_grade REAL CHECK(run_defense_grade IS NULL OR run_defense_grade BETWEEN 0 AND 100),
    coverage_grade REAL CHECK(coverage_grade IS NULL OR coverage_grade BETWEEN 0 AND 100),
    tackling_grade REAL CHECK(tackling_grade IS NULL OR tackling_grade BETWEEN 0 AND 100),

    -- Season totals
    total_snaps INTEGER DEFAULT 0,
    games_graded INTEGER DEFAULT 0,
    total_plays_graded INTEGER DEFAULT 0,
    positive_play_rate REAL CHECK(positive_play_rate IS NULL OR positive_play_rate BETWEEN 0 AND 1),

    -- EPA metrics
    epa_total REAL DEFAULT 0.0,
    epa_per_play REAL,

    -- Rankings (calculated after all games)
    position_rank INTEGER,           -- Rank among same position
    overall_rank INTEGER,            -- Rank among all players

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE,
    UNIQUE(dynasty_id, season, player_id)
);

-- Indexes for season grades
CREATE INDEX IF NOT EXISTS idx_season_grades_dynasty_season ON player_season_grades(dynasty_id, season);
CREATE INDEX IF NOT EXISTS idx_season_grades_player ON player_season_grades(dynasty_id, player_id);
CREATE INDEX IF NOT EXISTS idx_season_grades_position ON player_season_grades(dynasty_id, position, season);
CREATE INDEX IF NOT EXISTS idx_season_grades_overall ON player_season_grades(dynasty_id, season, overall_grade DESC);
CREATE INDEX IF NOT EXISTS idx_season_grades_position_rank ON player_season_grades(dynasty_id, season, position, position_rank);

-- Advanced game metrics per team
-- Team-level advanced statistics for each game
CREATE TABLE IF NOT EXISTS advanced_game_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dynasty_id TEXT NOT NULL,
    game_id TEXT NOT NULL,
    team_id INTEGER NOT NULL CHECK(team_id BETWEEN 1 AND 32),

    -- EPA (Expected Points Added)
    epa_total REAL,
    epa_passing REAL,
    epa_rushing REAL,
    epa_per_play REAL,

    -- Success Rates (% of plays gaining positive EPA or meeting down targets)
    success_rate REAL CHECK(success_rate IS NULL OR success_rate BETWEEN 0 AND 1),
    passing_success_rate REAL CHECK(passing_success_rate IS NULL OR passing_success_rate BETWEEN 0 AND 1),
    rushing_success_rate REAL CHECK(rushing_success_rate IS NULL OR rushing_success_rate BETWEEN 0 AND 1),

    -- Passing advanced metrics
    air_yards_total INTEGER DEFAULT 0,
    yac_total INTEGER DEFAULT 0,               -- Yards After Catch
    completion_pct_over_expected REAL,          -- Actual - Expected completion %
    avg_time_to_throw REAL,                     -- Seconds
    pressure_rate REAL CHECK(pressure_rate IS NULL OR pressure_rate BETWEEN 0 AND 1),

    -- Defensive advanced metrics
    pass_rush_win_rate REAL CHECK(pass_rush_win_rate IS NULL OR pass_rush_win_rate BETWEEN 0 AND 1),
    coverage_success_rate REAL CHECK(coverage_success_rate IS NULL OR coverage_success_rate BETWEEN 0 AND 1),
    missed_tackle_rate REAL CHECK(missed_tackle_rate IS NULL OR missed_tackle_rate BETWEEN 0 AND 1),
    forced_incompletions INTEGER DEFAULT 0,
    qb_hits INTEGER DEFAULT 0,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE,
    UNIQUE(dynasty_id, game_id, team_id)
);

-- Indexes for advanced metrics
CREATE INDEX IF NOT EXISTS idx_adv_metrics_dynasty_game ON advanced_game_metrics(dynasty_id, game_id);
CREATE INDEX IF NOT EXISTS idx_adv_metrics_team ON advanced_game_metrics(dynasty_id, team_id);

-- ============================================
-- FREE AGENCY DEPTH TABLES (Milestone 7)
-- Multi-wave free agency with offer windows
-- ============================================

-- Pending offers during free agency waves
-- Tracks all offers submitted by teams (user and AI) before decisions are made
CREATE TABLE IF NOT EXISTS pending_offers (
    offer_id INTEGER PRIMARY KEY AUTOINCREMENT,
    dynasty_id TEXT NOT NULL,
    season INTEGER NOT NULL,
    wave INTEGER NOT NULL CHECK(wave BETWEEN 0 AND 4),  -- 0=legal tampering, 1-3=waves, 4=post-draft

    -- Offer parties
    player_id INTEGER NOT NULL,
    offering_team_id INTEGER NOT NULL CHECK(offering_team_id BETWEEN 1 AND 32),

    -- Contract terms
    aav INTEGER NOT NULL,                 -- Average annual value in dollars
    total_value INTEGER NOT NULL,         -- Total contract value
    years INTEGER NOT NULL CHECK(years BETWEEN 1 AND 7),
    guaranteed INTEGER NOT NULL,          -- Guaranteed money
    signing_bonus INTEGER DEFAULT 0,

    -- Decision tracking
    decision_deadline INTEGER NOT NULL,   -- Wave "day" when decision due (1-3)
    status TEXT DEFAULT 'pending' CHECK(status IN (
        'pending',      -- Awaiting decision
        'accepted',     -- Player signed with this team
        'rejected',     -- Player chose different team
        'expired',      -- Decision deadline passed without acceptance
        'withdrawn',    -- Team withdrew offer
        'surprise'      -- Player signed early (surprise signing by AI)
    )),

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP,

    FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE,
    UNIQUE(dynasty_id, season, wave, player_id, offering_team_id)
);

-- FA Wave State - tracks current wave progression
CREATE TABLE IF NOT EXISTS fa_wave_state (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dynasty_id TEXT NOT NULL,
    season INTEGER NOT NULL,

    -- Wave progression
    current_wave INTEGER DEFAULT 0 CHECK(current_wave BETWEEN 0 AND 4),
    current_day INTEGER DEFAULT 1 CHECK(current_day BETWEEN 1 AND 3),
    wave_complete INTEGER DEFAULT 0 CHECK(wave_complete IN (0, 1)),

    -- Post-draft tracking
    post_draft_available INTEGER DEFAULT 0 CHECK(post_draft_available IN (0, 1)),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE,
    UNIQUE(dynasty_id, season)
);

-- Indexes for pending_offers
CREATE INDEX IF NOT EXISTS idx_pending_offers_dynasty ON pending_offers(dynasty_id);
CREATE INDEX IF NOT EXISTS idx_pending_offers_player ON pending_offers(dynasty_id, player_id, status);
CREATE INDEX IF NOT EXISTS idx_pending_offers_team ON pending_offers(dynasty_id, offering_team_id, status);
CREATE INDEX IF NOT EXISTS idx_pending_offers_wave ON pending_offers(dynasty_id, season, wave, status);
CREATE INDEX IF NOT EXISTS idx_pending_offers_status ON pending_offers(dynasty_id, status);

-- Indexes for fa_wave_state
CREATE INDEX IF NOT EXISTS idx_fa_wave_state_dynasty ON fa_wave_state(dynasty_id, season);

-- ============================================
-- AWARDS SYSTEM TABLES (Milestone 10)
-- End-of-season awards, All-Pro, Pro Bowl, stat leaders
-- ============================================

-- Award definitions (pre-populated with 8 awards)
CREATE TABLE IF NOT EXISTS award_definitions (
    award_id TEXT PRIMARY KEY,  -- 'mvp', 'opoy', 'dpoy', 'oroy', 'droy', 'cpoy', 'coy', 'eoy'
    award_name TEXT NOT NULL,
    award_type TEXT NOT NULL CHECK(award_type IN ('INDIVIDUAL', 'ALL_PRO', 'PRO_BOWL')),
    category TEXT CHECK(category IN ('OFFENSE', 'DEFENSE', 'SPECIAL_TEAMS', 'COACHING', 'MANAGEMENT')),
    description TEXT,
    eligible_positions TEXT,  -- JSON array (NULL = all positions)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Award winners (top 5 vote-getters per award)
CREATE TABLE IF NOT EXISTS award_winners (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dynasty_id TEXT NOT NULL,
    season INTEGER NOT NULL,
    award_id TEXT NOT NULL,
    player_id INTEGER,
    team_id INTEGER NOT NULL CHECK(team_id BETWEEN 1 AND 32),
    vote_points INTEGER,    -- Total weighted points (10-5-3-2-1 system)
    vote_share REAL,        -- Percentage of possible points (0.0-1.0)
    rank INTEGER,           -- 1 = winner, 2-5 = finalists
    is_winner INTEGER DEFAULT 0,
    voting_date DATE,
    FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE,
    FOREIGN KEY (award_id) REFERENCES award_definitions(award_id),
    UNIQUE(dynasty_id, season, award_id, rank)
);

-- Award nominees (top 10 candidates with stats snapshot)
CREATE TABLE IF NOT EXISTS award_nominees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dynasty_id TEXT NOT NULL,
    season INTEGER NOT NULL,
    award_id TEXT NOT NULL,
    player_id INTEGER,
    team_id INTEGER NOT NULL CHECK(team_id BETWEEN 1 AND 32),
    nomination_rank INTEGER,
    stats_snapshot TEXT,    -- JSON of key stats
    grade_snapshot REAL,    -- Overall grade at nomination
    FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE,
    UNIQUE(dynasty_id, season, award_id, player_id)
);

-- All-Pro selections (44 players: 22 first team + 22 second team)
CREATE TABLE IF NOT EXISTS all_pro_selections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dynasty_id TEXT NOT NULL,
    season INTEGER NOT NULL,
    player_id INTEGER NOT NULL,
    team_id INTEGER NOT NULL CHECK(team_id BETWEEN 1 AND 32),
    position TEXT NOT NULL,
    team_type TEXT NOT NULL CHECK(team_type IN ('FIRST_TEAM', 'SECOND_TEAM')),
    vote_points INTEGER,
    vote_share REAL,
    selection_date DATE,
    FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE,
    UNIQUE(dynasty_id, season, position, team_type, player_id)
);

-- Pro Bowl selections (AFC/NFC rosters)
CREATE TABLE IF NOT EXISTS pro_bowl_selections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dynasty_id TEXT NOT NULL,
    season INTEGER NOT NULL,
    player_id INTEGER NOT NULL,
    team_id INTEGER NOT NULL CHECK(team_id BETWEEN 1 AND 32),
    conference TEXT NOT NULL CHECK(conference IN ('AFC', 'NFC')),
    position TEXT NOT NULL,
    selection_type TEXT NOT NULL CHECK(selection_type IN ('STARTER', 'RESERVE', 'ALTERNATE')),
    combined_score REAL,  -- Fan (40%) + Coach (20%) + Player (40%)
    selection_date DATE,
    FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE,
    UNIQUE(dynasty_id, season, conference, position, selection_type, player_id)
);

-- Statistical leaders (top 10 per category)
CREATE TABLE IF NOT EXISTS statistical_leaders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dynasty_id TEXT NOT NULL,
    season INTEGER NOT NULL,
    stat_category TEXT NOT NULL,  -- 'passing_yards', 'rushing_yards', 'sacks', etc.
    player_id INTEGER NOT NULL,
    team_id INTEGER NOT NULL CHECK(team_id BETWEEN 1 AND 32),
    position TEXT NOT NULL,
    stat_value INTEGER NOT NULL,
    league_rank INTEGER NOT NULL,
    recorded_date DATE,
    FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE,
    UNIQUE(dynasty_id, season, stat_category, league_rank)
);

-- Indexes for award tables
CREATE INDEX IF NOT EXISTS idx_award_winners_dynasty_season ON award_winners(dynasty_id, season);
CREATE INDEX IF NOT EXISTS idx_award_winners_player ON award_winners(dynasty_id, player_id);
CREATE INDEX IF NOT EXISTS idx_award_winners_award ON award_winners(dynasty_id, award_id);
CREATE INDEX IF NOT EXISTS idx_award_nominees_dynasty_season ON award_nominees(dynasty_id, season);
CREATE INDEX IF NOT EXISTS idx_award_nominees_player ON award_nominees(dynasty_id, player_id);
CREATE INDEX IF NOT EXISTS idx_all_pro_dynasty_season ON all_pro_selections(dynasty_id, season);
CREATE INDEX IF NOT EXISTS idx_all_pro_player ON all_pro_selections(dynasty_id, player_id);
CREATE INDEX IF NOT EXISTS idx_all_pro_position ON all_pro_selections(dynasty_id, season, position);
CREATE INDEX IF NOT EXISTS idx_pro_bowl_dynasty_season ON pro_bowl_selections(dynasty_id, season);
CREATE INDEX IF NOT EXISTS idx_pro_bowl_player ON pro_bowl_selections(dynasty_id, player_id);
CREATE INDEX IF NOT EXISTS idx_pro_bowl_conference ON pro_bowl_selections(dynasty_id, season, conference);
CREATE INDEX IF NOT EXISTS idx_stat_leaders_dynasty_season ON statistical_leaders(dynasty_id, season);
CREATE INDEX IF NOT EXISTS idx_stat_leaders_category ON statistical_leaders(dynasty_id, stat_category);
CREATE INDEX IF NOT EXISTS idx_stat_leaders_player ON statistical_leaders(dynasty_id, player_id);

-- Pre-populate award definitions
INSERT OR IGNORE INTO award_definitions (award_id, award_name, award_type, category, description, eligible_positions) VALUES
('mvp', 'Most Valuable Player', 'INDIVIDUAL', NULL, 'The most outstanding player in the league', NULL),
('opoy', 'Offensive Player of the Year', 'INDIVIDUAL', 'OFFENSE', 'The most outstanding offensive player', '["QB", "RB", "WR", "TE", "LT", "LG", "C", "RG", "RT", "FB"]'),
('dpoy', 'Defensive Player of the Year', 'INDIVIDUAL', 'DEFENSE', 'The most outstanding defensive player', '["LE", "DT", "RE", "LOLB", "MLB", "ROLB", "CB", "FS", "SS", "EDGE"]'),
('oroy', 'Offensive Rookie of the Year', 'INDIVIDUAL', 'OFFENSE', 'The most outstanding offensive rookie', '["QB", "RB", "WR", "TE", "LT", "LG", "C", "RG", "RT", "FB"]'),
('droy', 'Defensive Rookie of the Year', 'INDIVIDUAL', 'DEFENSE', 'The most outstanding defensive rookie', '["LE", "DT", "RE", "LOLB", "MLB", "ROLB", "CB", "FS", "SS", "EDGE"]'),
('cpoy', 'Comeback Player of the Year', 'INDIVIDUAL', NULL, 'Outstanding comeback from injury or decline', NULL),
('coy', 'Coach of the Year', 'INDIVIDUAL', 'COACHING', 'The most outstanding head coach', NULL),
('eoy', 'Executive of the Year', 'INDIVIDUAL', 'MANAGEMENT', 'The most outstanding general manager', NULL);

-- Award race tracking (weekly tracking for performance optimization)
-- Tracks top performers each week starting at week 10 for faster end-of-season calculation
CREATE TABLE IF NOT EXISTS award_race_tracking (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dynasty_id TEXT NOT NULL,
    season INTEGER NOT NULL,
    week INTEGER NOT NULL CHECK(week BETWEEN 1 AND 18),
    award_type TEXT NOT NULL CHECK(award_type IN ('mvp', 'opoy', 'dpoy', 'oroy', 'droy')),
    player_id INTEGER NOT NULL,
    team_id INTEGER NOT NULL CHECK(team_id BETWEEN 1 AND 32),
    position TEXT NOT NULL,
    cumulative_score REAL NOT NULL,  -- Simple weighted score (stats + grades)
    week_score REAL,                 -- This week's performance only
    rank INTEGER NOT NULL,           -- Rank among tracked players for this award
    first_name TEXT,                 -- Denormalized for display
    last_name TEXT,                  -- Denormalized for display
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE,
    UNIQUE(dynasty_id, season, week, award_type, player_id)
);

-- Indexes for award race tracking
CREATE INDEX IF NOT EXISTS idx_award_race_dynasty_season ON award_race_tracking(dynasty_id, season);
CREATE INDEX IF NOT EXISTS idx_award_race_latest ON award_race_tracking(dynasty_id, season, week DESC);
CREATE INDEX IF NOT EXISTS idx_award_race_award_type ON award_race_tracking(dynasty_id, season, award_type);
CREATE INDEX IF NOT EXISTS idx_award_race_player ON award_race_tracking(dynasty_id, player_id);

-- ============================================
-- RIVALRIES TABLE (Milestone 11: Schedule & Rivalries)
-- Tracks team rivalries for schedule prioritization and gameplay effects
-- ============================================

-- Rivalries table - tracks all team rivalries
CREATE TABLE IF NOT EXISTS rivalries (
    rivalry_id INTEGER PRIMARY KEY AUTOINCREMENT,
    dynasty_id TEXT NOT NULL,
    team_a_id INTEGER NOT NULL CHECK(team_a_id BETWEEN 1 AND 32),
    team_b_id INTEGER NOT NULL CHECK(team_b_id BETWEEN 1 AND 32),
    rivalry_type TEXT NOT NULL CHECK(rivalry_type IN ('division', 'historic', 'geographic', 'recent')),
    rivalry_name TEXT NOT NULL,
    intensity INTEGER NOT NULL DEFAULT 50 CHECK(intensity BETWEEN 1 AND 100),
    is_protected INTEGER DEFAULT 0 CHECK(is_protected IN (0, 1)),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    CHECK(team_a_id < team_b_id),  -- Enforce consistent ordering (lower ID always team_a)
    CHECK(team_a_id != team_b_id), -- Teams must be different
    FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE,
    UNIQUE(dynasty_id, team_a_id, team_b_id)  -- One rivalry per team pair per dynasty
);

-- Indexes for rivalries
CREATE INDEX IF NOT EXISTS idx_rivalries_dynasty ON rivalries(dynasty_id);
CREATE INDEX IF NOT EXISTS idx_rivalries_team_a ON rivalries(dynasty_id, team_a_id);
CREATE INDEX IF NOT EXISTS idx_rivalries_team_b ON rivalries(dynasty_id, team_b_id);
CREATE INDEX IF NOT EXISTS idx_rivalries_type ON rivalries(dynasty_id, rivalry_type);
CREATE INDEX IF NOT EXISTS idx_rivalries_protected ON rivalries(dynasty_id, is_protected);
CREATE INDEX IF NOT EXISTS idx_rivalries_intensity ON rivalries(dynasty_id, intensity DESC);

-- ============================================
-- HEAD-TO-HEAD HISTORY TABLE (Milestone 11, Tollgate 2)
-- Tracks all-time records between any two teams
-- ============================================

-- Head-to-head records between teams
CREATE TABLE IF NOT EXISTS head_to_head (
    record_id INTEGER PRIMARY KEY AUTOINCREMENT,
    dynasty_id TEXT NOT NULL,

    -- Team pairing (enforce team_a_id < team_b_id for consistent lookup)
    team_a_id INTEGER NOT NULL CHECK(team_a_id BETWEEN 1 AND 32),
    team_b_id INTEGER NOT NULL CHECK(team_b_id BETWEEN 1 AND 32),

    -- Regular season record (from team_a's perspective)
    team_a_wins INTEGER DEFAULT 0 CHECK(team_a_wins >= 0),
    team_b_wins INTEGER DEFAULT 0 CHECK(team_b_wins >= 0),
    ties INTEGER DEFAULT 0 CHECK(ties >= 0),

    -- Home/away splits (from team_a's perspective)
    -- team_a_home_wins = wins by team_a when hosting team_b
    -- team_a_away_wins = wins by team_a when visiting team_b
    team_a_home_wins INTEGER DEFAULT 0 CHECK(team_a_home_wins >= 0),
    team_a_away_wins INTEGER DEFAULT 0 CHECK(team_a_away_wins >= 0),

    -- Last meeting info
    last_meeting_season INTEGER,
    last_meeting_winner INTEGER CHECK(last_meeting_winner IS NULL OR last_meeting_winner BETWEEN 1 AND 32),

    -- Current streak (team on winning streak, NULL = no streak or tie broke it)
    current_streak_team INTEGER CHECK(current_streak_team IS NULL OR current_streak_team BETWEEN 1 AND 32),
    current_streak_count INTEGER DEFAULT 0 CHECK(current_streak_count >= 0),

    -- Playoff record (tracked separately)
    playoff_meetings INTEGER DEFAULT 0 CHECK(playoff_meetings >= 0),
    playoff_team_a_wins INTEGER DEFAULT 0 CHECK(playoff_team_a_wins >= 0),
    playoff_team_b_wins INTEGER DEFAULT 0 CHECK(playoff_team_b_wins >= 0),

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    CHECK(team_a_id < team_b_id),  -- Enforce consistent ordering (lower ID always team_a)
    CHECK(team_a_id != team_b_id), -- Teams must be different
    FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE,
    UNIQUE(dynasty_id, team_a_id, team_b_id)  -- One record per team pair per dynasty
);

-- Indexes for head_to_head queries
CREATE INDEX IF NOT EXISTS idx_h2h_dynasty ON head_to_head(dynasty_id);
CREATE INDEX IF NOT EXISTS idx_h2h_team_a ON head_to_head(dynasty_id, team_a_id);
CREATE INDEX IF NOT EXISTS idx_h2h_team_b ON head_to_head(dynasty_id, team_b_id);
CREATE INDEX IF NOT EXISTS idx_h2h_total_games ON head_to_head(dynasty_id, (team_a_wins + team_b_wins + ties) DESC);
CREATE INDEX IF NOT EXISTS idx_h2h_streak ON head_to_head(dynasty_id, current_streak_count DESC);

-- ============================================
-- BYE WEEKS TABLE (Milestone 11, Tollgate 3)
-- Tracks bye week assignments per team per season
-- ============================================

-- Bye week assignments
CREATE TABLE IF NOT EXISTS bye_weeks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dynasty_id TEXT NOT NULL,
    season INTEGER NOT NULL,
    team_id INTEGER NOT NULL CHECK(team_id BETWEEN 1 AND 32),
    bye_week INTEGER NOT NULL CHECK(bye_week BETWEEN 5 AND 14),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE,
    UNIQUE(dynasty_id, season, team_id)  -- One bye week per team per season
);

-- Indexes for bye_weeks queries
CREATE INDEX IF NOT EXISTS idx_bye_weeks_dynasty_season ON bye_weeks(dynasty_id, season);
CREATE INDEX IF NOT EXISTS idx_bye_weeks_week ON bye_weeks(dynasty_id, season, bye_week);
CREATE INDEX IF NOT EXISTS idx_bye_weeks_team ON bye_weeks(dynasty_id, team_id);

-- ============================================================================
-- GAME SLOTS TABLE (Milestone 11, Tollgate 4)
-- Tracks primetime and special game slot assignments
-- ============================================================================
CREATE TABLE IF NOT EXISTS game_slots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dynasty_id TEXT NOT NULL,
    season INTEGER NOT NULL,
    game_id TEXT NOT NULL,
    week INTEGER NOT NULL,
    slot TEXT NOT NULL,  -- 'TNF', 'SNF', 'MNF', 'SUN_EARLY', 'SUN_LATE', etc.
    home_team_id INTEGER NOT NULL CHECK(home_team_id BETWEEN 1 AND 32),
    away_team_id INTEGER NOT NULL CHECK(away_team_id BETWEEN 1 AND 32),
    appeal_score INTEGER DEFAULT 0,  -- 0-100 matchup appeal
    broadcast_network TEXT,
    is_flex_eligible INTEGER DEFAULT 1,  -- Boolean: can be flexed weeks 12-17
    flexed_from TEXT,  -- Original slot if game was flexed
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE,
    UNIQUE(dynasty_id, season, game_id)  -- One slot assignment per game
);

-- Indexes for game_slots queries
CREATE INDEX IF NOT EXISTS idx_game_slots_dynasty_season ON game_slots(dynasty_id, season);
CREATE INDEX IF NOT EXISTS idx_game_slots_week ON game_slots(dynasty_id, season, week);
CREATE INDEX IF NOT EXISTS idx_game_slots_slot ON game_slots(dynasty_id, season, slot);
CREATE INDEX IF NOT EXISTS idx_game_slots_primetime ON game_slots(dynasty_id, season, slot)
    WHERE slot IN ('TNF', 'SNF', 'MNF', 'KICKOFF', 'TG_EARLY', 'TG_LATE', 'TG_NIGHT', 'XMAS');

-- ============================================
-- OWNER REVIEW TABLES (Milestone 13)
-- GM/HC staff management and owner strategic directives
-- ============================================

-- Team Staff Assignments - GM and HC per team/season
-- Persists procedurally generated staff with traits and history
CREATE TABLE IF NOT EXISTS team_staff_assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dynasty_id TEXT NOT NULL,
    team_id INTEGER NOT NULL CHECK(team_id BETWEEN 1 AND 32),
    season INTEGER NOT NULL,

    -- GM Assignment
    gm_id TEXT NOT NULL,                    -- UUID identifier
    gm_name TEXT NOT NULL,
    gm_archetype_key TEXT NOT NULL,         -- Key into base_archetypes.json
    gm_custom_traits TEXT,                  -- JSON overrides for archetype traits
    gm_history TEXT,                        -- Generated background story
    gm_hire_season INTEGER NOT NULL,        -- Season hired

    -- HC Assignment
    hc_id TEXT NOT NULL,                    -- UUID identifier
    hc_name TEXT NOT NULL,
    hc_archetype_key TEXT NOT NULL,         -- Key into head_coaches/*.json
    hc_custom_traits TEXT,                  -- JSON overrides for archetype traits
    hc_history TEXT,                        -- Generated background story
    hc_hire_season INTEGER NOT NULL,        -- Season hired

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE,
    UNIQUE(dynasty_id, team_id, season)
);

-- Owner Directives - Persistent strategic guidance
-- Set during Owner Review, influences GM behavior in draft/FA/re-signing
CREATE TABLE IF NOT EXISTS owner_directives (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dynasty_id TEXT NOT NULL,
    team_id INTEGER NOT NULL CHECK(team_id BETWEEN 1 AND 32),
    season INTEGER NOT NULL,               -- Season these directives apply to

    -- Win Target
    target_wins INTEGER CHECK(target_wins IS NULL OR target_wins BETWEEN 0 AND 17),

    -- Priority Positions (for draft/FA)
    priority_positions TEXT,               -- JSON array: ["WR", "CB", "EDGE"]

    -- Player Wishlists (specific targets)
    fa_wishlist TEXT,                      -- JSON array of player names
    draft_wishlist TEXT,                   -- JSON array of prospect names

    -- Draft Strategy (maps to DraftStrategy enum)
    draft_strategy TEXT DEFAULT 'balanced' CHECK(draft_strategy IN (
        'bpa', 'balanced', 'needs_based', 'position_focus'
    )),

    -- FA Strategy (maps to FAPhilosophy enum)
    fa_philosophy TEXT DEFAULT 'balanced' CHECK(fa_philosophy IN (
        'aggressive', 'balanced', 'conservative'
    )),
    max_contract_years INTEGER DEFAULT 5 CHECK(max_contract_years BETWEEN 1 AND 5),
    max_guaranteed_percent REAL DEFAULT 0.75 CHECK(max_guaranteed_percent BETWEEN 0 AND 1),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE,
    UNIQUE(dynasty_id, team_id, season)
);

-- Staff Candidates - Pool generated when firing GM/HC
-- Cleared after hire is complete
CREATE TABLE IF NOT EXISTS staff_candidates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dynasty_id TEXT NOT NULL,
    team_id INTEGER NOT NULL CHECK(team_id BETWEEN 1 AND 32),
    season INTEGER NOT NULL,

    candidate_id TEXT NOT NULL,            -- UUID
    staff_type TEXT NOT NULL CHECK(staff_type IN ('GM', 'HC')),
    name TEXT NOT NULL,
    archetype_key TEXT NOT NULL,
    custom_traits TEXT,                    -- JSON trait variations
    history TEXT NOT NULL,                 -- Generated background
    is_selected INTEGER DEFAULT 0,         -- 1 if user selected this candidate

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE
);

-- Indexes for Owner Review tables
CREATE INDEX IF NOT EXISTS idx_staff_assignments_dynasty ON team_staff_assignments(dynasty_id, team_id);
CREATE INDEX IF NOT EXISTS idx_staff_assignments_season ON team_staff_assignments(dynasty_id, season);
CREATE INDEX IF NOT EXISTS idx_owner_directives_dynasty ON owner_directives(dynasty_id, team_id);
CREATE INDEX IF NOT EXISTS idx_owner_directives_season ON owner_directives(dynasty_id, season);
CREATE INDEX IF NOT EXISTS idx_staff_candidates_dynasty ON staff_candidates(dynasty_id, team_id, season);
CREATE INDEX IF NOT EXISTS idx_staff_candidates_type ON staff_candidates(dynasty_id, staff_type);

-- ============================================
-- Play-by-Play Persistence
-- Stores drive and play-level data for historical game review
-- ============================================

-- Game Drives - Drive-level summaries
CREATE TABLE IF NOT EXISTS game_drives (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dynasty_id TEXT NOT NULL,
    game_id TEXT NOT NULL,
    drive_number INTEGER NOT NULL,

    -- Team possession
    possession_team_id INTEGER NOT NULL,

    -- Drive context
    quarter_started INTEGER CHECK(quarter_started BETWEEN 1 AND 5),
    starting_clock_seconds INTEGER,
    starting_field_position INTEGER,
    starting_down INTEGER DEFAULT 1,
    starting_distance INTEGER DEFAULT 10,

    -- Drive outcome
    ending_field_position INTEGER,
    drive_outcome TEXT NOT NULL,  -- 'touchdown', 'field_goal', 'punt', 'turnover', 'turnover_on_downs', 'end_of_half', 'safety'
    points_scored INTEGER DEFAULT 0,

    -- Drive totals
    total_plays INTEGER DEFAULT 0,
    total_yards INTEGER DEFAULT 0,
    time_elapsed INTEGER DEFAULT 0,  -- seconds

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE,
    UNIQUE(dynasty_id, game_id, drive_number)
);

CREATE INDEX IF NOT EXISTS idx_drives_game ON game_drives(dynasty_id, game_id);

-- Game Plays - Individual play records with full context
CREATE TABLE IF NOT EXISTS game_plays (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dynasty_id TEXT NOT NULL,
    game_id TEXT NOT NULL,

    -- Sequencing
    play_number INTEGER NOT NULL,        -- Global play number in game
    drive_number INTEGER NOT NULL,
    drive_play_number INTEGER NOT NULL,  -- Play number within drive

    -- Situation BEFORE play
    quarter INTEGER CHECK(quarter BETWEEN 1 AND 5),
    game_clock_seconds INTEGER,
    down INTEGER,
    distance INTEGER,
    yard_line INTEGER,  -- 1-99 (own 1 to opp 1)
    possession_team_id INTEGER NOT NULL,

    -- Score state
    home_score INTEGER,
    away_score INTEGER,

    -- Play details
    play_type TEXT NOT NULL,  -- 'pass', 'run', 'punt', 'field_goal', 'kickoff', 'extra_point', 'two_point', 'kneel', 'spike'
    play_description TEXT,    -- Human-readable description

    -- Outcome
    yards_gained INTEGER DEFAULT 0,
    outcome TEXT,  -- 'complete', 'incomplete', 'sack', 'interception', 'fumble', 'touchdown', etc.

    -- Flags
    is_scoring_play INTEGER DEFAULT 0,
    is_turnover INTEGER DEFAULT 0,
    turnover_type TEXT,  -- 'interception', 'fumble', 'downs'
    is_first_down INTEGER DEFAULT 0,
    is_penalty INTEGER DEFAULT 0,
    penalty_type TEXT,
    penalty_yards INTEGER,
    penalty_team_id INTEGER,

    -- Points (if scoring play)
    points_scored INTEGER DEFAULT 0,

    -- State AFTER play
    down_after INTEGER,
    distance_after INTEGER,
    field_position_after INTEGER,

    -- Time elapsed
    time_elapsed_seconds REAL DEFAULT 0,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE,
    UNIQUE(dynasty_id, game_id, play_number)
);

CREATE INDEX IF NOT EXISTS idx_plays_game ON game_plays(dynasty_id, game_id, play_number);
CREATE INDEX IF NOT EXISTS idx_plays_drive ON game_plays(dynasty_id, game_id, drive_number);
