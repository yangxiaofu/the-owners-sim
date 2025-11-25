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
