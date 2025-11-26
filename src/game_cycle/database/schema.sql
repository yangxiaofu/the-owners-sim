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

-- Standings for current season
CREATE TABLE IF NOT EXISTS standings (
    team_id INTEGER PRIMARY KEY CHECK(team_id BETWEEN 1 AND 32),
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
    FOREIGN KEY (team_id) REFERENCES teams(team_id)
);

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

-- Playoff bracket tracking
CREATE TABLE IF NOT EXISTS playoff_bracket (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    round_name TEXT NOT NULL,               -- 'wild_card', 'divisional', 'conference', 'super_bowl'
    conference TEXT NOT NULL CHECK(conference IN ('AFC', 'NFC', 'SUPER_BOWL')),
    game_number INTEGER NOT NULL,           -- 1-3 for wild card, 1-2 for divisional, 1 for conference/SB
    higher_seed INTEGER,                    -- team_id of higher seed
    lower_seed INTEGER,                     -- team_id of lower seed
    winner INTEGER,                         -- team_id of winner (NULL until played)
    home_score INTEGER,
    away_score INTEGER,
    FOREIGN KEY (higher_seed) REFERENCES teams(team_id),
    FOREIGN KEY (lower_seed) REFERENCES teams(team_id),
    FOREIGN KEY (winner) REFERENCES teams(team_id),
    UNIQUE(round_name, conference, game_number)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_schedule_week ON schedule(week);
CREATE INDEX IF NOT EXISTS idx_schedule_round ON schedule(round_name);
CREATE INDEX IF NOT EXISTS idx_schedule_teams ON schedule(home_team_id, away_team_id);
CREATE INDEX IF NOT EXISTS idx_schedule_played ON schedule(is_played);
CREATE INDEX IF NOT EXISTS idx_playoff_round ON playoff_bracket(round_name);

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
