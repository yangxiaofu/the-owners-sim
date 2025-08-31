-- Initial database schema for Football Owner Simulation

-- Teams table
CREATE TABLE teams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    city TEXT NOT NULL,
    abbreviation TEXT NOT NULL UNIQUE,
    conference TEXT NOT NULL,
    division TEXT NOT NULL,
    founded_year INTEGER,
    owner_id INTEGER,
    stadium_id INTEGER,
    salary_cap_space INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Players table  
CREATE TABLE players (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    position TEXT NOT NULL,
    jersey_number INTEGER,
    team_id INTEGER,
    age INTEGER NOT NULL,
    height INTEGER, -- inches
    weight INTEGER, -- pounds
    college TEXT,
    draft_year INTEGER,
    draft_round INTEGER,
    draft_pick INTEGER,
    years_pro INTEGER DEFAULT 0,
    contract_id INTEGER,
    injury_status TEXT DEFAULT 'healthy',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (team_id) REFERENCES teams(id),
    FOREIGN KEY (contract_id) REFERENCES contracts(id)
);

-- Player attributes table
CREATE TABLE player_attributes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id INTEGER NOT NULL,
    -- Physical attributes
    speed INTEGER DEFAULT 50,
    strength INTEGER DEFAULT 50,
    agility INTEGER DEFAULT 50,
    stamina INTEGER DEFAULT 50,
    -- Mental attributes  
    football_iq INTEGER DEFAULT 50,
    work_ethic INTEGER DEFAULT 50,
    leadership INTEGER DEFAULT 50,
    -- Position specific (will expand based on position)
    overall_rating INTEGER DEFAULT 50,
    potential INTEGER DEFAULT 50,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (player_id) REFERENCES players(id) ON DELETE CASCADE
);

-- Contracts table
CREATE TABLE contracts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id INTEGER NOT NULL,
    team_id INTEGER NOT NULL,
    total_value INTEGER NOT NULL, -- in dollars
    years INTEGER NOT NULL,
    guaranteed_money INTEGER DEFAULT 0,
    signing_bonus INTEGER DEFAULT 0,
    start_year INTEGER NOT NULL,
    end_year INTEGER NOT NULL,
    cap_hit INTEGER NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (player_id) REFERENCES players(id),
    FOREIGN KEY (team_id) REFERENCES teams(id)
);

-- Games/Matches table
CREATE TABLE games (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    season INTEGER NOT NULL,
    week INTEGER NOT NULL,
    home_team_id INTEGER NOT NULL,
    away_team_id INTEGER NOT NULL,
    home_score INTEGER DEFAULT 0,
    away_score INTEGER DEFAULT 0,
    game_date DATETIME,
    is_playoff BOOLEAN DEFAULT false,
    is_simulated BOOLEAN DEFAULT false,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (home_team_id) REFERENCES teams(id),
    FOREIGN KEY (away_team_id) REFERENCES teams(id)
);

-- Seasons table
CREATE TABLE seasons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    year INTEGER NOT NULL UNIQUE,
    salary_cap INTEGER NOT NULL,
    is_active BOOLEAN DEFAULT false,
    current_week INTEGER DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Team finances table
CREATE TABLE team_finances (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id INTEGER NOT NULL,
    season INTEGER NOT NULL,
    revenue_tickets INTEGER DEFAULT 0,
    revenue_merchandise INTEGER DEFAULT 0,
    revenue_concessions INTEGER DEFAULT 0,
    revenue_luxury_boxes INTEGER DEFAULT 0,
    revenue_naming_rights INTEGER DEFAULT 0,
    revenue_tv_local INTEGER DEFAULT 0,
    revenue_league_sharing INTEGER DEFAULT 0,
    expenses_salaries INTEGER DEFAULT 0,
    expenses_staff INTEGER DEFAULT 0,
    expenses_operations INTEGER DEFAULT 0,
    expenses_stadium INTEGER DEFAULT 0,
    net_income INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (team_id) REFERENCES teams(id),
    UNIQUE(team_id, season)
);

-- Create indexes for performance
CREATE INDEX idx_players_team_id ON players(team_id);
CREATE INDEX idx_players_position ON players(position);
CREATE INDEX idx_games_season_week ON games(season, week);
CREATE INDEX idx_games_teams ON games(home_team_id, away_team_id);
CREATE INDEX idx_contracts_player_team ON contracts(player_id, team_id);
CREATE INDEX idx_team_finances_season ON team_finances(team_id, season);