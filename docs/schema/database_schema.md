# Database Schema Documentation

**Project**: The Owners Sim - NFL Football Simulation Engine
**Database**: SQLite3
**File Location**: `data/database/nfl_simulation.db`
**Schema Version**: 2.3.0 (with dynasty-isolated events)

## Table of Contents

1. [Overview](#overview)
2. [Architecture Principles](#architecture-principles)
3. [Table Definitions](#table-definitions)
4. [Relationships and Constraints](#relationships-and-constraints)
5. [Performance Indexes](#performance-indexes)
6. [Entity Relationship Diagram](#entity-relationship-diagram)
7. [Common Query Examples](#common-query-examples)
8. [Integration Notes](#integration-notes)
9. [Migration and Versioning](#migration-and-versioning)

---

## Overview

The NFL Simulation database provides comprehensive storage for dynasty management, game simulations, player statistics, standings, schedules, playoff systems, salary cap management, and a polymorphic event system. The schema is designed to support:

- **Multi-dynasty isolation**: Complete statistical separation between different user franchises
- **Comprehensive statistics**: Detailed player and team performance tracking
- **Playoff systems**: Seeding, tiebreakers, and tournament brackets
- **Salary cap management**: Complete NFL contract tracking, cap space calculations, and compliance validation
- **Event polymorphism**: Unified storage for games, scouting, media, trades, and future event types
- **Season persistence**: Historical data for multi-season dynasty modes

### Database Technology

- **Engine**: SQLite3
- **Transaction Support**: Full ACID compliance with automatic rollback on errors
- **File Format**: Single-file database for easy backup and transfer
- **In-Memory Option**: Supports `:memory:` for testing and performance
- **JSON Support**: Flexible schema for event data storage

### Key Features

- Dynasty-based data isolation (all statistics scoped to `dynasty_id`)
- Comprehensive player statistics (passing, rushing, receiving, defense, special teams, offensive line)
- NFL-realistic standings tracking with conference/division/home/away splits
- Playoff seeding with detailed tiebreaker tracking
- Complete salary cap system (contracts, dead money, franchise tags, compliance tracking)
- Polymorphic event system for mixed timelines
- Box score generation with quarter-by-quarter breakdowns

---

## Architecture Principles

### 1. Dynasty Isolation Pattern

Every table (except `dynasties`) includes a `dynasty_id` foreign key. This ensures complete statistical separation between different user franchises:

```sql
-- All statistics queries are scoped by dynasty
SELECT * FROM games WHERE dynasty_id = 'eagles_rebuild_2024';
SELECT * FROM player_game_stats WHERE dynasty_id = 'chiefs_dynasty';
```

**Benefits**:
- Multiple users can share same database
- Dynasty data never cross-contaminates
- Easy to export/import individual dynasties
- Supports testing and experimentation without affecting main dynasty

### 2. Referential Integrity

Foreign key constraints enforce data consistency:

```sql
FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id)
    ON DELETE CASCADE
```

**Cascade Behavior**:
- Deleting a dynasty removes all associated games, stats, standings, schedules
- Maintains database integrity automatically
- Prevents orphaned records

### 3. Optimized Indexing

Strategic indexes for common query patterns:

- Dynasty-scoped queries: `idx_games_dynasty_id`, `idx_stats_dynasty_id`
- Team lookups: `idx_games_team_id`, `idx_standings_team_id`
- Date-based queries: `idx_events_timestamp`, `idx_schedules_date`
- Event retrieval: `idx_events_game_id`, `idx_events_type`

### 4. Flexible JSON Storage

The `events` table uses JSON for the `data` field, supporting:

- Parameterized events (games with team IDs)
- Result-based events (scouting reports)
- Mixed event types in same timeline
- Future event types without schema changes

---

## Table Definitions

### 1. dynasties

Master record for each dynasty (user franchise).

```sql
CREATE TABLE dynasties (
    dynasty_id TEXT PRIMARY KEY,
    dynasty_name TEXT NOT NULL,
    owner_name TEXT,
    team_id INTEGER,  -- Nullable to support league-wide simulations
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_played TIMESTAMP,
    total_seasons INTEGER DEFAULT 0,
    championships_won INTEGER DEFAULT 0,
    super_bowls_won INTEGER DEFAULT 0,
    conference_championships INTEGER DEFAULT 0,
    division_titles INTEGER DEFAULT 0,
    total_wins INTEGER DEFAULT 0,
    total_losses INTEGER DEFAULT 0,
    total_ties INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE
);
```

**Columns**:

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `dynasty_id` | TEXT | PRIMARY KEY | Unique dynasty identifier (e.g., "eagles_rebuild_2024") |
| `dynasty_name` | TEXT | NOT NULL | Display name for dynasty |
| `owner_name` | TEXT | | Name of the dynasty owner/player |
| `team_id` | INTEGER | | Team ID (1-32) user controls, NULL for league-wide |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Dynasty creation timestamp |
| `last_played` | TIMESTAMP | | Last time this dynasty was played |
| `total_seasons` | INTEGER | DEFAULT 0 | Total seasons completed |
| `championships_won` | INTEGER | DEFAULT 0 | Total championships (all types) |
| `super_bowls_won` | INTEGER | DEFAULT 0 | Super Bowl victories |
| `conference_championships` | INTEGER | DEFAULT 0 | Conference championship wins |
| `division_titles` | INTEGER | DEFAULT 0 | Division titles won |
| `total_wins` | INTEGER | DEFAULT 0 | All-time wins across all seasons |
| `total_losses` | INTEGER | DEFAULT 0 | All-time losses across all seasons |
| `total_ties` | INTEGER | DEFAULT 0 | All-time ties across all seasons |
| `is_active` | BOOLEAN | DEFAULT TRUE | Whether dynasty is currently active |

**Indexes**: None (primary key only)

**Example Data**:
```sql
INSERT INTO dynasties VALUES (
    'eagles_rebuild_2024',
    'Philadelphia Eagles Rebuild',
    'John Smith',
    14,
    '2024-01-15T10:30:00',
    '2024-12-25T16:30:00',
    1,
    0,
    0,
    0,
    1,
    12,
    4,
    0,
    TRUE
);
```

---

### 2. games

Game results with comprehensive metadata and regular season/playoff separation.

```sql
CREATE TABLE games (
    game_id TEXT PRIMARY KEY,
    dynasty_id TEXT NOT NULL,
    season INTEGER NOT NULL,
    week INTEGER NOT NULL,

    -- Season type discriminator for regular season vs playoffs
    season_type TEXT NOT NULL DEFAULT 'regular_season',
    -- Values: 'regular_season' | 'playoffs'

    -- Specific game type for detailed tracking
    game_type TEXT DEFAULT 'regular',
    -- Values: 'regular', 'wildcard', 'divisional', 'conference', 'super_bowl'

    home_team_id INTEGER NOT NULL,
    away_team_id INTEGER NOT NULL,
    home_score INTEGER NOT NULL,
    away_score INTEGER NOT NULL,
    total_plays INTEGER,
    game_duration_minutes INTEGER,
    overtime_periods INTEGER DEFAULT 0,
    created_at TEXT,
    FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id)
);
```

**Columns**:

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `game_id` | TEXT | PRIMARY KEY | Unique game identifier |
| `dynasty_id` | TEXT | NOT NULL, FK | Dynasty isolation key |
| `season` | INTEGER | NOT NULL | Season year |
| `week` | INTEGER | NOT NULL | Week number (1-18 regular, 19+ playoffs) |
| `season_type` | TEXT | NOT NULL, DEFAULT 'regular_season' | **NEW**: 'regular_season' or 'playoffs' for stat separation |
| `game_type` | TEXT | DEFAULT 'regular' | Detailed game type: 'regular', 'wildcard', 'divisional', 'conference', 'super_bowl' |
| `home_team_id` | INTEGER | NOT NULL | Home team ID (1-32) |
| `away_team_id` | INTEGER | NOT NULL | Away team ID (1-32) |
| `home_score` | INTEGER | NOT NULL | Final home team score |
| `away_score` | INTEGER | NOT NULL | Final away team score |
| `total_plays` | INTEGER | | Total plays in game |
| `game_duration_minutes` | INTEGER | | Game duration in minutes |
| `overtime_periods` | INTEGER | DEFAULT 0 | Number of overtime periods |
| `created_at` | TEXT | | Record creation timestamp |

**Indexes**:
```sql
CREATE INDEX idx_games_dynasty ON games(dynasty_id);
CREATE INDEX idx_games_week ON games(week);
CREATE INDEX idx_games_season ON games(season);
CREATE INDEX idx_games_dynasty_season ON games(dynasty_id, season, week);
CREATE INDEX idx_games_teams ON games(home_team_id, away_team_id);

-- Season type indexes for regular season/playoff separation (v2.1.0+)
CREATE INDEX idx_games_season_type ON games(dynasty_id, season, season_type);
CREATE INDEX idx_games_type ON games(game_type);
```

**Example Data**:
```sql
INSERT INTO games VALUES (
    'game_20241225_22_at_23',
    'eagles_rebuild_2024',
    2024,
    17,
    'regular',
    23,  -- Green Bay Packers (home)
    22,  -- Detroit Lions (away)
    24,
    9,
    142,
    180,
    0,
    '2024-12-25T16:30:00'
);
```

---

### 3. player_game_stats

Player statistics for all positions with regular season/playoff separation.

```sql
CREATE TABLE player_game_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dynasty_id TEXT NOT NULL,
    game_id TEXT NOT NULL,

    -- Season type for stat filtering and separation
    season_type TEXT NOT NULL DEFAULT 'regular_season',
    -- Values: 'regular_season' | 'playoffs'

    player_id TEXT NOT NULL,
    player_name TEXT NOT NULL,
    team_id INTEGER NOT NULL,
    position TEXT NOT NULL,

    -- Passing stats
    passing_yards INTEGER DEFAULT 0,
    passing_tds INTEGER DEFAULT 0,
    passing_completions INTEGER DEFAULT 0,
    passing_attempts INTEGER DEFAULT 0,

    -- Rushing stats
    rushing_yards INTEGER DEFAULT 0,
    rushing_tds INTEGER DEFAULT 0,
    rushing_attempts INTEGER DEFAULT 0,

    -- Receiving stats
    receiving_yards INTEGER DEFAULT 0,
    receiving_tds INTEGER DEFAULT 0,
    receptions INTEGER DEFAULT 0,
    targets INTEGER DEFAULT 0,

    -- Defense stats
    tackles_total INTEGER DEFAULT 0,
    sacks REAL DEFAULT 0,
    interceptions INTEGER DEFAULT 0,

    -- Special teams stats
    field_goals_made INTEGER DEFAULT 0,
    field_goals_attempted INTEGER DEFAULT 0,
    extra_points_made INTEGER DEFAULT 0,
    extra_points_attempted INTEGER DEFAULT 0,

    -- Snap counts
    offensive_snaps INTEGER DEFAULT 0,
    defensive_snaps INTEGER DEFAULT 0,
    total_snaps INTEGER DEFAULT 0,

    FOREIGN KEY (game_id) REFERENCES games(game_id)
);
```

**Columns**: Essential statistical fields for core positions

**Key Fields**:
- `season_type`: **NEW** - Enables filtering regular season vs playoff statistics

**Position Groups**:
- **Passing**: QB statistics (completions, attempts, yards, TDs)
- **Rushing**: RB/QB rushing (attempts, yards, TDs)
- **Receiving**: WR/TE/RB receiving (receptions, targets, yards, TDs)
- **Defense**: Tackles, sacks, interceptions
- **Special Teams**: Kicking (FG, XP)
- **Snap Counts**: Offensive, defensive, and total snaps

**Indexes**:
```sql
CREATE INDEX idx_player_stats_game ON player_game_stats(game_id);
CREATE INDEX idx_player_stats_player ON player_game_stats(player_id);
CREATE INDEX idx_player_stats_dynasty ON player_game_stats(dynasty_id);

-- Season type indexes for filtering regular season vs playoff stats (v2.1.0+)
CREATE INDEX idx_stats_season_type ON player_game_stats(dynasty_id, season_type);
CREATE INDEX idx_stats_player_type ON player_game_stats(player_id, season_type);
```

**Example Data**:
```sql
INSERT INTO player_game_stats (
    dynasty_id, game_id, player_id, player_name, team_id, position,
    passing_attempts, passing_completions, passing_yards, passing_tds,
    offensive_snaps, total_snaps
) VALUES (
    'eagles_rebuild_2024',
    'game_20241225_22_at_23',
    'player_22_qb_1',
    'Detroit Starting QB',
    22,
    'QB',
    35, 22, 287, 2,
    65, 65
);
```

---

### 4. standings

Team records with conference/division/home/away splits, separated by season type (regular season vs playoffs).

```sql
CREATE TABLE standings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dynasty_id TEXT NOT NULL,
    team_id INTEGER NOT NULL,
    season INTEGER NOT NULL,

    -- Season type discriminator for regular season vs playoff separation
    season_type TEXT NOT NULL DEFAULT 'regular_season',
    -- Values: 'regular_season' | 'playoffs'

    -- Overall record
    wins INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0,
    ties INTEGER DEFAULT 0,

    -- Scoring
    points_for INTEGER DEFAULT 0,
    points_against INTEGER DEFAULT 0,

    -- Division record
    division_wins INTEGER DEFAULT 0,
    division_losses INTEGER DEFAULT 0,

    -- Conference record
    conference_wins INTEGER DEFAULT 0,
    conference_losses INTEGER DEFAULT 0,

    -- Home/Away splits
    home_wins INTEGER DEFAULT 0,
    home_losses INTEGER DEFAULT 0,
    away_wins INTEGER DEFAULT 0,
    away_losses INTEGER DEFAULT 0,

    -- Streaks and rankings
    current_streak TEXT,
    division_rank INTEGER,

    UNIQUE(dynasty_id, team_id, season, season_type)
);
```

**Columns**:

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Auto-generated ID |
| `dynasty_id` | TEXT | NOT NULL | Dynasty isolation |
| `team_id` | INTEGER | NOT NULL | Team ID (1-32) |
| `season` | INTEGER | NOT NULL | Season year |
| `season_type` | TEXT | NOT NULL, DEFAULT 'regular_season' | **NEW v2.4.0**: Season type for record separation ('regular_season' or 'playoffs') |
| `wins` | INTEGER | DEFAULT 0 | Total wins for this season type |
| `losses` | INTEGER | DEFAULT 0 | Total losses for this season type |
| `ties` | INTEGER | DEFAULT 0 | Total ties for this season type |
| `points_for` | INTEGER | DEFAULT 0 | Total points scored |
| `points_against` | INTEGER | DEFAULT 0 | Total points allowed |
| `division_wins` | INTEGER | DEFAULT 0 | Division game wins |
| `division_losses` | INTEGER | DEFAULT 0 | Division game losses |
| `conference_wins` | INTEGER | DEFAULT 0 | Conference wins |
| `conference_losses` | INTEGER | DEFAULT 0 | Conference losses |
| `home_wins` | INTEGER | DEFAULT 0 | Home game wins |
| `home_losses` | INTEGER | DEFAULT 0 | Home game losses |
| `away_wins` | INTEGER | DEFAULT 0 | Away game wins |
| `away_losses` | INTEGER | DEFAULT 0 | Away game losses |
| `current_streak` | TEXT | | Streak notation (e.g., "W3", "L2") |
| `division_rank` | INTEGER | | Current division rank |

**Unique Constraint**: One standings record per (dynasty_id, team_id, season, season_type)

**Season Type Separation** (v2.4.0):
Each team has TWO standings records per season:
- `season_type='regular_season'` - Regular season record (e.g., 14-3)
- `season_type='playoffs'` - Playoff record (e.g., 2-1)

This allows separate tracking and display of regular season vs playoff performance.

**Indexes**:
```sql
CREATE INDEX idx_standings_dynasty ON standings(dynasty_id);
CREATE INDEX idx_standings_team ON standings(team_id);
CREATE INDEX idx_standings_season ON standings(season);

-- v2.4.0: Season type indexes for efficient filtering
CREATE UNIQUE INDEX idx_standings_unique ON standings(dynasty_id, team_id, season, season_type);
CREATE INDEX idx_standings_season_type ON standings(dynasty_id, season, season_type);
CREATE INDEX idx_standings_team_season_type ON standings(team_id, season, season_type);
```

**Example Data**:
```sql
-- Regular season record
INSERT INTO standings VALUES (
    1,
    'eagles_rebuild_2024',
    22,  -- Detroit Lions
    2024,
    'regular_season',  -- Regular season record
    14, 3, 0,  -- 14-3 regular season record
    5, 1,      -- 5-1 division
    11, 2,     -- 11-2 conference
    8, 0,      -- 8-0 home
    6, 3,      -- 6-3 away
    456, 312,  -- Points
    'W3',      -- Winning streak
    1          -- Division rank
);

-- Playoff record (same team, same season, different season_type)
INSERT INTO standings VALUES (
    2,
    'eagles_rebuild_2024',
    22,  -- Detroit Lions
    2024,
    'playoffs',        -- Playoff record
    2, 1, 0,  -- 2-1 playoff record
    0, 0,      -- No division games in playoffs
    2, 1,      -- Conference games
    1, 0,      -- 1-0 home
    1, 1,      -- 1-1 away
    72, 65,    -- Points (3 playoff games)
    'L1',      -- Lost last game (Super Bowl)
    NULL       -- No division rank for playoffs
);
```

---

### 5. schedules

Game scheduling with metadata.

```sql
CREATE TABLE schedules (
    schedule_id INTEGER PRIMARY KEY AUTOINCREMENT,
    dynasty_id TEXT NOT NULL,
    season INTEGER NOT NULL,
    week INTEGER NOT NULL,
    away_team_id INTEGER NOT NULL,
    home_team_id INTEGER NOT NULL,
    game_date TEXT,
    game_time TEXT,
    game_type TEXT NOT NULL,
    status TEXT DEFAULT 'SCHEDULED',

    FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id)
        ON DELETE CASCADE
);
```

**Columns**:

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `schedule_id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Auto-generated ID |
| `dynasty_id` | TEXT | NOT NULL, FK | Dynasty isolation |
| `season` | INTEGER | NOT NULL | Season year |
| `week` | INTEGER | NOT NULL | Week number |
| `away_team_id` | INTEGER | NOT NULL | Away team (1-32) |
| `home_team_id` | INTEGER | NOT NULL | Home team (1-32) |
| `game_date` | TEXT | | ISO date |
| `game_time` | TEXT | | Game time |
| `game_type` | TEXT | NOT NULL | "REGULAR", "PLAYOFF", etc. |
| `status` | TEXT | DEFAULT 'SCHEDULED' | "SCHEDULED", "IN_PROGRESS", "COMPLETED" |

**Indexes**:
```sql
CREATE INDEX idx_schedules_dynasty_id ON schedules(dynasty_id);
CREATE INDEX idx_schedules_season_week ON schedules(season, week);
CREATE INDEX idx_schedules_date ON schedules(game_date);
```

**Example Data**:
```sql
INSERT INTO schedules VALUES (
    1,
    'eagles_rebuild_2024',
    2024,
    17,
    22,  -- Detroit
    23,  -- Green Bay
    '2024-12-25',
    '13:00',
    'REGULAR',
    'COMPLETED'
);
```

---

### 6. dynasty_seasons

Season summaries and awards.

```sql
CREATE TABLE dynasty_seasons (
    season_id INTEGER PRIMARY KEY AUTOINCREMENT,
    dynasty_id TEXT NOT NULL,
    season INTEGER NOT NULL,
    user_team_wins INTEGER DEFAULT 0,
    user_team_losses INTEGER DEFAULT 0,
    playoff_result TEXT,
    mvp_player_id TEXT,
    super_bowl_winner_id INTEGER,
    notes TEXT,

    FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id)
        ON DELETE CASCADE,
    UNIQUE(dynasty_id, season)
);
```

**Columns**:

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `season_id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Auto-generated ID |
| `dynasty_id` | TEXT | NOT NULL, FK | Dynasty isolation |
| `season` | INTEGER | NOT NULL | Season year |
| `user_team_wins` | INTEGER | DEFAULT 0 | User's team wins |
| `user_team_losses` | INTEGER | DEFAULT 0 | User's team losses |
| `playoff_result` | TEXT | | "WILD_CARD_EXIT", "SUPER_BOWL_CHAMPION", etc. |
| `mvp_player_id` | TEXT | | Season MVP player ID |
| `super_bowl_winner_id` | INTEGER | | Winning team ID |
| `notes` | TEXT | | Season notes/memories |

**Unique Constraint**: One season record per (dynasty_id, season)

**Indexes**:
```sql
CREATE INDEX idx_dynasty_seasons_dynasty_id ON dynasty_seasons(dynasty_id);
```

**Example Data**:
```sql
INSERT INTO dynasty_seasons VALUES (
    1,
    'eagles_rebuild_2024',
    2024,
    12,
    4,
    'DIVISIONAL_ROUND_EXIT',
    'player_14_qb_1',
    NULL,
    'Promising first season, young QB showed potential'
);
```

---

### 7. box_scores

Quarter-by-quarter game breakdowns.

```sql
CREATE TABLE box_scores (
    box_score_id INTEGER PRIMARY KEY AUTOINCREMENT,
    dynasty_id TEXT NOT NULL,
    game_id TEXT NOT NULL,
    away_team_id INTEGER NOT NULL,
    home_team_id INTEGER NOT NULL,

    -- Quarter scores
    away_q1 INTEGER DEFAULT 0,
    away_q2 INTEGER DEFAULT 0,
    away_q3 INTEGER DEFAULT 0,
    away_q4 INTEGER DEFAULT 0,
    away_ot INTEGER DEFAULT 0,
    home_q1 INTEGER DEFAULT 0,
    home_q2 INTEGER DEFAULT 0,
    home_q3 INTEGER DEFAULT 0,
    home_q4 INTEGER DEFAULT 0,
    home_ot INTEGER DEFAULT 0,

    -- Team statistics
    away_total_yards INTEGER DEFAULT 0,
    home_total_yards INTEGER DEFAULT 0,
    away_turnovers INTEGER DEFAULT 0,
    home_turnovers INTEGER DEFAULT 0,
    away_time_of_possession TEXT,
    home_time_of_possession TEXT,

    created_at TEXT DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id)
        ON DELETE CASCADE,
    FOREIGN KEY (game_id) REFERENCES games(game_id)
        ON DELETE CASCADE,
    UNIQUE(dynasty_id, game_id)
);
```

**Columns**:

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `box_score_id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Auto-generated ID |
| `dynasty_id` | TEXT | NOT NULL, FK | Dynasty isolation |
| `game_id` | TEXT | NOT NULL, FK | Associated game |
| `away_team_id` | INTEGER | NOT NULL | Away team (1-32) |
| `home_team_id` | INTEGER | NOT NULL | Home team (1-32) |
| `away_q1` - `away_q4` | INTEGER | DEFAULT 0 | Away quarter scores |
| `away_ot` | INTEGER | DEFAULT 0 | Away overtime score |
| `home_q1` - `home_q4` | INTEGER | DEFAULT 0 | Home quarter scores |
| `home_ot` | INTEGER | DEFAULT 0 | Home overtime score |
| `away_total_yards` | INTEGER | DEFAULT 0 | Away total yards |
| `home_total_yards` | INTEGER | DEFAULT 0 | Home total yards |
| `away_turnovers` | INTEGER | DEFAULT 0 | Away turnovers |
| `home_turnovers` | INTEGER | DEFAULT 0 | Home turnovers |
| `away_time_of_possession` | TEXT | | Away TOP (MM:SS) |
| `home_time_of_possession` | TEXT | | Home TOP (MM:SS) |
| `created_at` | TEXT | DEFAULT CURRENT_TIMESTAMP | Record creation |

**Unique Constraint**: One box score per (dynasty_id, game_id)

**Indexes**:
```sql
CREATE INDEX idx_box_scores_dynasty_id ON box_scores(dynasty_id);
CREATE INDEX idx_box_scores_game_id ON box_scores(game_id);
```

**Example Data**:
```sql
INSERT INTO box_scores VALUES (
    1,
    'eagles_rebuild_2024',
    'game_20241225_22_at_23',
    22, 23,
    0, 3, 3, 3, 0,  -- Away: 0-3-3-3
    7, 7, 7, 3, 0,  -- Home: 7-7-7-3
    287, 412,        -- Total yards
    2, 1,            -- Turnovers
    '26:45', '33:15',  -- Time of possession
    '2024-12-25T16:30:00'
);
```

---

### 8. playoff_seedings

Playoff bracket seeds with tiebreaker information.

```sql
CREATE TABLE playoff_seedings (
    seeding_id INTEGER PRIMARY KEY AUTOINCREMENT,
    dynasty_id TEXT NOT NULL,
    season INTEGER NOT NULL,
    conference TEXT NOT NULL,
    seed INTEGER NOT NULL,
    team_id INTEGER NOT NULL,
    wins INTEGER NOT NULL,
    losses INTEGER NOT NULL,
    ties INTEGER DEFAULT 0,
    tiebreaker_note TEXT,

    FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id)
        ON DELETE CASCADE,
    UNIQUE(dynasty_id, season, conference, seed)
);
```

**Columns**:

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `seeding_id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Auto-generated ID |
| `dynasty_id` | TEXT | NOT NULL, FK | Dynasty isolation |
| `season` | INTEGER | NOT NULL | Season year |
| `conference` | TEXT | NOT NULL | "AFC" or "NFC" |
| `seed` | INTEGER | NOT NULL | Playoff seed (1-7) |
| `team_id` | INTEGER | NOT NULL | Team ID (1-32) |
| `wins` | INTEGER | NOT NULL | Season wins |
| `losses` | INTEGER | NOT NULL | Season losses |
| `ties` | INTEGER | DEFAULT 0 | Season ties |
| `tiebreaker_note` | TEXT | | Tiebreaker explanation |

**Unique Constraint**: One team per (dynasty_id, season, conference, seed)

**Indexes**:
```sql
CREATE INDEX idx_playoff_seedings_dynasty_id ON playoff_seedings(dynasty_id);
CREATE INDEX idx_playoff_seedings_season ON playoff_seedings(season);
```

**Example Data**:
```sql
INSERT INTO playoff_seedings VALUES (
    1,
    'eagles_rebuild_2024',
    2024,
    'NFC',
    1,
    22,  -- Detroit Lions
    12, 4, 0,
    'Division winner, best conference record'
);
```

---

### 9. tiebreaker_applications

Detailed tracking of tiebreaker resolution.

```sql
CREATE TABLE tiebreaker_applications (
    tiebreaker_id INTEGER PRIMARY KEY AUTOINCREMENT,
    dynasty_id TEXT NOT NULL,
    season INTEGER NOT NULL,
    tiebreaker_type TEXT NOT NULL,
    teams_involved TEXT NOT NULL,
    tiebreaker_step TEXT NOT NULL,
    winner_team_id INTEGER,
    resolution_details TEXT,

    FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id)
        ON DELETE CASCADE
);
```

**Columns**:

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `tiebreaker_id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Auto-generated ID |
| `dynasty_id` | TEXT | NOT NULL, FK | Dynasty isolation |
| `season` | INTEGER | NOT NULL | Season year |
| `tiebreaker_type` | TEXT | NOT NULL | "DIVISION", "WILD_CARD", etc. |
| `teams_involved` | TEXT | NOT NULL | Comma-separated team IDs |
| `tiebreaker_step` | TEXT | NOT NULL | "HEAD_TO_HEAD", "DIVISION_RECORD", etc. |
| `winner_team_id` | INTEGER | | Winning team ID |
| `resolution_details` | TEXT | | Detailed explanation |

**Indexes**:
```sql
CREATE INDEX idx_tiebreakers_dynasty_id ON tiebreaker_applications(dynasty_id);
CREATE INDEX idx_tiebreakers_season ON tiebreaker_applications(season);
```

**Example Data**:
```sql
INSERT INTO tiebreaker_applications VALUES (
    1,
    'eagles_rebuild_2024',
    2024,
    'DIVISION',
    '22,23',
    'HEAD_TO_HEAD',
    22,
    'Lions won both games vs Packers (2-0)'
);
```

---

### 10. playoff_brackets

Tournament progression tracking.

```sql
CREATE TABLE playoff_brackets (
    bracket_id INTEGER PRIMARY KEY AUTOINCREMENT,
    dynasty_id TEXT NOT NULL,
    season INTEGER NOT NULL,
    conference TEXT NOT NULL,
    round TEXT NOT NULL,
    matchup_number INTEGER NOT NULL,
    home_team_id INTEGER NOT NULL,
    away_team_id INTEGER NOT NULL,
    home_score INTEGER,
    away_score INTEGER,
    winner_team_id INTEGER,
    game_id TEXT,

    FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id)
        ON DELETE CASCADE
);
```

**Columns**:

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `bracket_id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Auto-generated ID |
| `dynasty_id` | TEXT | NOT NULL, FK | Dynasty isolation |
| `season` | INTEGER | NOT NULL | Season year |
| `conference` | TEXT | NOT NULL | "AFC", "NFC", or "SUPER_BOWL" |
| `round` | TEXT | NOT NULL | "WILD_CARD", "DIVISIONAL", "CONFERENCE", "SUPER_BOWL" |
| `matchup_number` | INTEGER | NOT NULL | Matchup identifier (1-4 for wild card, etc.) |
| `home_team_id` | INTEGER | NOT NULL | Home team (1-32) |
| `away_team_id` | INTEGER | NOT NULL | Away team (1-32) |
| `home_score` | INTEGER | | Final home score |
| `away_score` | INTEGER | | Final away score |
| `winner_team_id` | INTEGER | | Winning team |
| `game_id` | TEXT | | Link to games table |

**Indexes**:
```sql
CREATE INDEX idx_playoff_brackets_dynasty_id ON playoff_brackets(dynasty_id);
CREATE INDEX idx_playoff_brackets_season ON playoff_brackets(season);
```

**Example Data**:
```sql
INSERT INTO playoff_brackets VALUES (
    1,
    'eagles_rebuild_2024',
    2024,
    'NFC',
    'DIVISIONAL',
    1,
    22,  -- Detroit (home, #1 seed)
    14,  -- Philadelphia (away, #5 seed)
    28, 31,
    14,
    'game_playoff_nfc_divisional_1'
);
```

---

### 11. player_contracts

Player contract records with comprehensive financial details.

```sql
CREATE TABLE player_contracts (
    contract_id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id INTEGER NOT NULL,
    team_id INTEGER NOT NULL,
    dynasty_id TEXT NOT NULL,

    -- Contract Duration
    start_year INTEGER NOT NULL,
    end_year INTEGER NOT NULL,
    contract_years INTEGER NOT NULL,

    -- Contract Type
    contract_type TEXT NOT NULL CHECK(contract_type IN (
        'ROOKIE', 'VETERAN', 'FRANCHISE_TAG', 'TRANSITION_TAG', 'EXTENSION'
    )),

    -- Financial Terms
    total_value INTEGER NOT NULL,
    signing_bonus INTEGER DEFAULT 0,
    signing_bonus_proration INTEGER DEFAULT 0,

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
);
```

**Columns**:

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `contract_id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Auto-generated contract ID |
| `player_id` | INTEGER | NOT NULL | Player identifier |
| `team_id` | INTEGER | NOT NULL | Team ID (1-32) |
| `dynasty_id` | TEXT | NOT NULL | Dynasty isolation |
| `start_year` | INTEGER | NOT NULL | Contract start year |
| `end_year` | INTEGER | NOT NULL | Contract end year |
| `contract_years` | INTEGER | NOT NULL | Total contract years |
| `contract_type` | TEXT | NOT NULL | Contract type (ROOKIE, VETERAN, etc.) |
| `total_value` | INTEGER | NOT NULL | Total contract value in dollars |
| `signing_bonus` | INTEGER | DEFAULT 0 | Signing bonus amount |
| `signing_bonus_proration` | INTEGER | DEFAULT 0 | Annual proration amount |
| `guaranteed_at_signing` | INTEGER | DEFAULT 0 | Guaranteed money at signing |
| `injury_guaranteed` | INTEGER | DEFAULT 0 | Injury guarantee amount |
| `total_guaranteed` | INTEGER | DEFAULT 0 | Total guaranteed money |
| `is_active` | BOOLEAN | DEFAULT TRUE | Contract active status |
| `signed_date` | DATE | NOT NULL | Contract signing date |
| `voided_date` | DATE | | Contract void date (if voided) |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Record creation |
| `modified_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Last modification |

**Indexes**:
```sql
CREATE INDEX idx_contracts_player ON player_contracts(player_id);
CREATE INDEX idx_contracts_team_season ON player_contracts(team_id, start_year);
CREATE INDEX idx_contracts_dynasty ON player_contracts(dynasty_id);
CREATE INDEX idx_contracts_active ON player_contracts(is_active);
CREATE INDEX idx_contracts_team_active ON player_contracts(team_id, is_active);
```

**Example Data**:
```sql
INSERT INTO player_contracts VALUES (
    1,
    12345,  -- Player ID
    7,      -- Detroit Lions
    'eagles_rebuild_2024',
    2025, 2028, 4,
    'VETERAN',
    40000000, 16000000, 4000000,
    23000000, 0, 23000000,
    TRUE,
    '2025-03-15',
    NULL,
    '2025-03-15T10:00:00',
    '2025-03-15T10:00:00'
);
```

---

### 12. contract_year_details

Year-by-year contract breakdown with cap hits and cash flow.

```sql
CREATE TABLE contract_year_details (
    detail_id INTEGER PRIMARY KEY AUTOINCREMENT,
    contract_id INTEGER NOT NULL,
    contract_year INTEGER NOT NULL,
    season_year INTEGER NOT NULL,

    -- Salary Components
    base_salary INTEGER NOT NULL,
    roster_bonus INTEGER DEFAULT 0,
    workout_bonus INTEGER DEFAULT 0,
    option_bonus INTEGER DEFAULT 0,
    per_game_roster_bonus INTEGER DEFAULT 0,

    -- Performance Incentives
    ltbe_incentives INTEGER DEFAULT 0,
    nltbe_incentives INTEGER DEFAULT 0,

    -- Guarantees
    base_salary_guaranteed BOOLEAN DEFAULT FALSE,
    guarantee_type TEXT CHECK(guarantee_type IN ('FULL', 'INJURY', 'SKILL', 'NONE') OR guarantee_type IS NULL),
    guarantee_date DATE,

    -- Cap Impact
    signing_bonus_proration INTEGER DEFAULT 0,
    option_bonus_proration INTEGER DEFAULT 0,
    total_cap_hit INTEGER NOT NULL,

    -- Cash Flow
    cash_paid INTEGER NOT NULL,

    -- Status
    is_voided BOOLEAN DEFAULT FALSE,

    FOREIGN KEY (contract_id) REFERENCES player_contracts(contract_id) ON DELETE CASCADE
);
```

**Columns**:

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `detail_id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Auto-generated detail ID |
| `contract_id` | INTEGER | NOT NULL, FK | Parent contract |
| `contract_year` | INTEGER | NOT NULL | Contract year (1, 2, 3, etc.) |
| `season_year` | INTEGER | NOT NULL | Absolute season year |
| `base_salary` | INTEGER | NOT NULL | Base salary for year |
| `roster_bonus` | INTEGER | DEFAULT 0 | Roster bonus |
| `workout_bonus` | INTEGER | DEFAULT 0 | Workout bonus |
| `signing_bonus_proration` | INTEGER | DEFAULT 0 | Prorated signing bonus |
| `total_cap_hit` | INTEGER | NOT NULL | Total cap hit for year |
| `cash_paid` | INTEGER | NOT NULL | Actual cash paid in year |
| `is_voided` | BOOLEAN | DEFAULT FALSE | Year is void year |

**Indexes**:
```sql
CREATE INDEX idx_contract_details_contract ON contract_year_details(contract_id);
CREATE INDEX idx_contract_details_season ON contract_year_details(season_year);
CREATE INDEX idx_contract_details_contract_year ON contract_year_details(contract_id, contract_year);
```

---

### 13. team_salary_cap

Team salary cap tracking with compliance data.

```sql
CREATE TABLE team_salary_cap (
    cap_id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id INTEGER NOT NULL,
    season INTEGER NOT NULL,
    dynasty_id TEXT NOT NULL,

    -- Cap Limits
    salary_cap_limit INTEGER NOT NULL,
    carryover_from_previous INTEGER DEFAULT 0,

    -- Current Status
    active_contracts_total INTEGER DEFAULT 0,
    dead_money_total INTEGER DEFAULT 0,
    ltbe_incentives_total INTEGER DEFAULT 0,
    practice_squad_total INTEGER DEFAULT 0,

    -- Top 51 Rule
    is_top_51_active BOOLEAN DEFAULT TRUE,
    top_51_total INTEGER DEFAULT 0,

    -- Cash Spending
    cash_spent_this_year INTEGER DEFAULT 0,

    -- Metadata
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(team_id, season, dynasty_id)
);
```

**Columns**:

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `cap_id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Auto-generated cap ID |
| `team_id` | INTEGER | NOT NULL | Team ID (1-32) |
| `season` | INTEGER | NOT NULL | Season year |
| `dynasty_id` | TEXT | NOT NULL | Dynasty isolation |
| `salary_cap_limit` | INTEGER | NOT NULL | League salary cap limit |
| `carryover_from_previous` | INTEGER | DEFAULT 0 | Cap carryover from previous year |
| `active_contracts_total` | INTEGER | DEFAULT 0 | Total active contract cap hits |
| `dead_money_total` | INTEGER | DEFAULT 0 | Total dead money |
| `ltbe_incentives_total` | INTEGER | DEFAULT 0 | Likely To Be Earned incentives |
| `practice_squad_total` | INTEGER | DEFAULT 0 | Practice squad cap total |
| `is_top_51_active` | BOOLEAN | DEFAULT TRUE | Top-51 rule active (offseason) |
| `top_51_total` | INTEGER | DEFAULT 0 | Top 51 contracts total |
| `cash_spent_this_year` | INTEGER | DEFAULT 0 | Cash spending for 89% floor |

**Indexes**:
```sql
CREATE INDEX idx_cap_team_season ON team_salary_cap(team_id, season);
CREATE INDEX idx_cap_dynasty ON team_salary_cap(dynasty_id);
CREATE INDEX idx_cap_season ON team_salary_cap(season);
```

---

### 14. franchise_tags

Franchise and transition tag tracking.

```sql
CREATE TABLE franchise_tags (
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
    deadline_date DATE NOT NULL,
    extension_deadline DATE,

    -- Status
    is_extended BOOLEAN DEFAULT FALSE,
    extension_contract_id INTEGER,
    consecutive_tag_number INTEGER DEFAULT 1,

    FOREIGN KEY (extension_contract_id) REFERENCES player_contracts(contract_id)
);
```

**Key Fields**:
- `tag_type`: FRANCHISE_EXCLUSIVE, FRANCHISE_NON_EXCLUSIVE, or TRANSITION
- `consecutive_tag_number`: Tracks 1st, 2nd, 3rd consecutive tags (with salary escalators)
- `extension_contract_id`: Links to long-term contract if extended

**Indexes**:
```sql
CREATE INDEX idx_tags_player ON franchise_tags(player_id);
CREATE INDEX idx_tags_team_season ON franchise_tags(team_id, season);
```

---

### 15. rfa_tenders

Restricted Free Agent tender tracking.

```sql
CREATE TABLE rfa_tenders (
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
    compensation_round INTEGER,

    -- Dates
    tender_date DATE NOT NULL,
    offer_sheet_deadline DATE,

    -- Status
    is_accepted BOOLEAN DEFAULT FALSE,
    has_offer_sheet BOOLEAN DEFAULT FALSE,
    is_matched BOOLEAN
);
```

**Key Fields**:
- `tender_level`: Four RFA tender levels with different draft pick compensation
- `compensation_round`: Draft pick compensation if offer sheet signed (NULL for right of first refusal)
- `is_matched`: Whether original team matched offer sheet

**Indexes**:
```sql
CREATE INDEX idx_tenders_player ON rfa_tenders(player_id);
CREATE INDEX idx_tenders_team_season ON rfa_tenders(team_id, season);
```

---

### 16. dead_money

Dead money tracking from player releases.

```sql
CREATE TABLE dead_money (
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
```

**Key Fields**:
- `is_june_1_designation`: June 1 designation splits dead money across 2 years
- `current_year_dead_money`: Dead money hit in current year
- `next_year_dead_money`: Dead money deferred to next year (June 1 only)

**Indexes**:
```sql
CREATE INDEX idx_dead_money_team_season ON dead_money(team_id, season);
CREATE INDEX idx_dead_money_contract ON dead_money(contract_id);
CREATE INDEX idx_dead_money_dynasty ON dead_money(dynasty_id);
```

---

### 17. cap_transactions

Complete audit trail of all salary cap transactions.

```sql
CREATE TABLE cap_transactions (
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
    cap_impact_current INTEGER DEFAULT 0,
    cap_impact_future TEXT,  -- JSON

    -- Cash Impact
    cash_impact INTEGER DEFAULT 0,
    dead_money_created INTEGER DEFAULT 0,

    -- Description
    description TEXT,

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (contract_id) REFERENCES player_contracts(contract_id)
);
```

**Transaction Types**:
- `SIGNING`: New contract signed
- `RELEASE`: Player released
- `RESTRUCTURE`: Contract restructured
- `TRADE`: Player traded
- `TAG`: Franchise/transition tag applied
- `TENDER`: RFA tender offered

**Indexes**:
```sql
CREATE INDEX idx_transactions_team_season ON cap_transactions(team_id, season);
CREATE INDEX idx_transactions_type ON cap_transactions(transaction_type);
CREATE INDEX idx_transactions_date ON cap_transactions(transaction_date);
CREATE INDEX idx_transactions_dynasty ON cap_transactions(dynasty_id);
```

---

### 18. league_salary_cap_history

Historical league-wide salary cap data.

```sql
CREATE TABLE league_salary_cap_history (
    season INTEGER PRIMARY KEY,
    salary_cap_amount INTEGER NOT NULL,
    increase_from_previous INTEGER,
    increase_percentage REAL,

    -- Metadata
    announcement_date DATE,
    notes TEXT
);
```

**Prepopulated Data**:
```sql
INSERT INTO league_salary_cap_history (season, salary_cap_amount) VALUES
    (2023, 224800000),
    (2024, 255400000),
    (2025, 279200000),
    (2026, 301000000),
    (2027, 325000000),
    (2028, 350000000),
    (2029, 375000000),
    (2030, 400000000);
```

---

### 19. events

Polymorphic event storage for games, scouting, media, trades, and future event types.

```sql
CREATE TABLE events (
    event_id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    timestamp INTEGER NOT NULL,
    game_id TEXT NOT NULL,
    dynasty_id TEXT NOT NULL,
    data TEXT NOT NULL,
    FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id)
        ON DELETE CASCADE
);
```

**Note**: This table follows the dynasty isolation pattern. All events are scoped to a specific dynasty for complete data separation.

**Columns**:

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `event_id` | TEXT | PRIMARY KEY | Unique event identifier (UUID) |
| `event_type` | TEXT | NOT NULL | Event type: "GAME", "SCOUTING", "MEDIA", "TRADE", etc. |
| `timestamp` | INTEGER | NOT NULL | Unix timestamp in milliseconds |
| `game_id` | TEXT | NOT NULL | Context identifier (season, timeline) |
| `dynasty_id` | TEXT | NOT NULL, FK | Dynasty isolation key |
| `data` | TEXT | NOT NULL | JSON with three-part structure (see below) |

**JSON Data Structure**:
```json
{
  "parameters": {
    // Input values for recreating/replaying event
    // GameEvent: away_team_id, home_team_id, week, etc.
    // ScoutingEvent: scout_type, target_positions, num_players
  },
  "results": {
    // Output after execution (optional, null if not executed yet)
    // GameEvent: away_score, home_score, player_stats
    // ScoutingEvent: scouting_reports, top_prospect
  },
  "metadata": {
    // Additional context
    // description, tags, dynasty_id, etc.
  }
}
```

**Indexes**:
```sql
-- Primary indexes for event retrieval
CREATE INDEX idx_events_game_id ON events(game_id);
CREATE INDEX idx_events_timestamp ON events(timestamp);
CREATE INDEX idx_events_event_type ON events(event_type);

-- Dynasty isolation indexes (v2.3.0+)
CREATE INDEX idx_events_dynasty_id ON events(dynasty_id);
CREATE INDEX idx_events_dynasty_timestamp ON events(dynasty_id, timestamp);
CREATE INDEX idx_events_dynasty_type ON events(dynasty_id, event_type);
```

**Event Types**:
- **GAME**: NFL game simulation (parameterized, replay-able)
- **SCOUTING**: Player evaluation reports (result-based)
- **MEDIA**: Press conferences, interviews (future)
- **TRADE**: Player/pick transactions (future)
- **INJURY**: Player injury reports (future)
- **CONTRACT**: Contract negotiations (future)

**Example Data**:

**GameEvent (parameterized)**:
```sql
INSERT INTO events VALUES (
    'event_550e8400-e29b-41d4-a716-446655440000',
    'GAME',
    1703509200000,  -- 2024-12-25 13:00:00 in milliseconds
    'game_20241225_22_at_23',
    'eagles_rebuild_2024',  -- Dynasty ID now a column (v2.3.0+)
    '{
        "parameters": {
            "away_team_id": 22,
            "home_team_id": 23,
            "week": 17,
            "season": 2024,
            "game_date": "2024-12-25T13:00:00"
        },
        "results": {
            "away_score": 9,
            "home_score": 24,
            "total_yards_away": 287,
            "total_yards_home": 412,
            "turnovers_away": 2,
            "turnovers_home": 1
        },
        "metadata": {
            "description": "Week 17: Lions @ Packers"
        }
    }'
);
```

**ScoutingEvent (result-based)**:
```sql
INSERT INTO events VALUES (
    'event_650e8400-e29b-41d4-a716-446655440001',
    'SCOUTING',
    1703595600000,
    'scouting_mid_season_2024',
    'eagles_rebuild_2024',  -- Dynasty ID now a column (v2.3.0+)
    '{
        "parameters": {
            "scout_type": "college",
            "target_positions": ["QB", "WR", "TE"],
            "num_players": 5
        },
        "results": {
            "total_players_evaluated": 5,
            "scouting_reports": [
                {
                    "player_name": "Jake Morrison",
                    "position": "QB",
                    "overall_grade": "B+",
                    "strengths": ["arm strength", "mobility"],
                    "draft_projection": "Round 2-3"
                }
            ],
            "top_prospect": {
                "name": "Jake Morrison",
                "position": "QB",
                "grade": "B+"
            }
        },
        "metadata": {
            "description": "Mid-season college scouting"
        }
    }'
);
```

---

## Relationships and Constraints

### Foreign Key Relationships

```
dynasties (1) ──┬──→ (N) games
                ├──→ (N) player_game_stats
                ├──→ (N) standings
                ├──→ (N) schedules
                ├──→ (N) dynasty_seasons
                ├──→ (N) box_scores
                ├──→ (N) playoff_seedings
                ├──→ (N) tiebreaker_applications
                ├──→ (N) playoff_brackets
                ├──→ (N) player_contracts
                ├──→ (N) team_salary_cap
                ├──→ (N) franchise_tags
                ├──→ (N) rfa_tenders
                ├──→ (N) dead_money
                ├──→ (N) cap_transactions
                └──→ (N) events (v2.3.0+)

games (1) ──┬──→ (N) player_game_stats
            └──→ (1) box_scores

player_contracts (1) ──┬──→ (N) contract_year_details
                       ├──→ (N) dead_money
                       ├──→ (N) cap_transactions
                       └──→ (N) franchise_tags (extension_contract_id)
```

### Cascade Behavior

**ON DELETE CASCADE**: When a dynasty is deleted, all associated records are automatically removed:

```sql
DELETE FROM dynasties WHERE dynasty_id = 'eagles_rebuild_2024';
-- Automatically deletes:
--   - All games for this dynasty
--   - All player_game_stats for these games
--   - All standings records
--   - All schedules
--   - All dynasty_seasons
--   - All box_scores
--   - All playoff_seedings
--   - All tiebreaker_applications
--   - All playoff_brackets
--   - All player_contracts
--   - All contract_year_details (via contracts)
--   - All team_salary_cap records
--   - All franchise_tags
--   - All rfa_tenders
--   - All dead_money records
--   - All cap_transactions
--   - All events (v2.3.0+)
```

### Unique Constraints

Prevent duplicate records for natural keys:

```sql
-- One standings record per team per season per dynasty
UNIQUE(dynasty_id, team_id, season)

-- One season record per season per dynasty
UNIQUE(dynasty_id, season)

-- One box score per game per dynasty
UNIQUE(dynasty_id, game_id)

-- One playoff seed per position per conference per season per dynasty
UNIQUE(dynasty_id, season, conference, seed)

-- One cap record per team per season per dynasty
UNIQUE(team_id, season, dynasty_id)
```

---

## Performance Indexes

### Primary Indexes

All tables have primary key indexes (automatic):
- `dynasties.dynasty_id`
- `games.game_id`
- `player_game_stats.stat_id`
- `standings.standing_id`
- `schedules.schedule_id`
- `dynasty_seasons.season_id`
- `box_scores.box_score_id`
- `playoff_seedings.seeding_id`
- `tiebreaker_applications.tiebreaker_id`
- `playoff_brackets.bracket_id`
- `player_contracts.contract_id`
- `contract_year_details.detail_id`
- `team_salary_cap.cap_id`
- `franchise_tags.tag_id`
- `rfa_tenders.tender_id`
- `dead_money.dead_money_id`
- `cap_transactions.transaction_id`
- `league_salary_cap_history.season`
- `events.event_id`

### Secondary Indexes

**Dynasty-scoped queries** (most common pattern):
```sql
CREATE INDEX idx_games_dynasty ON games(dynasty_id);
CREATE INDEX idx_player_stats_dynasty ON player_game_stats(dynasty_id);
CREATE INDEX idx_standings_dynasty ON standings(dynasty_id);
CREATE INDEX idx_schedules_dynasty ON schedules(dynasty_id, season, week);
CREATE INDEX idx_dynasty_seasons ON dynasty_seasons(dynasty_id, season);
CREATE INDEX idx_box_scores ON box_scores(dynasty_id, game_id);
CREATE INDEX idx_playoff_seedings_dynasty ON playoff_seedings(dynasty_id, season);
CREATE INDEX idx_playoff_seedings_conference ON playoff_seedings(dynasty_id, season, conference);
CREATE INDEX idx_tiebreaker_apps ON tiebreaker_applications(dynasty_id, season);
CREATE INDEX idx_playoff_brackets ON playoff_brackets(dynasty_id, season, round_name);
CREATE INDEX idx_events_dynasty_id ON events(dynasty_id);  -- v2.3.0+
CREATE INDEX idx_events_dynasty_timestamp ON events(dynasty_id, timestamp);  -- v2.3.0+
CREATE INDEX idx_events_dynasty_type ON events(dynasty_id, event_type);  -- v2.3.0+
```

**Team lookups**:
```sql
CREATE INDEX idx_games_teams ON games(home_team_id, away_team_id);
CREATE INDEX idx_standings_team ON standings(team_id);
CREATE INDEX idx_schedules_teams ON schedules(home_team_id, away_team_id);
```

**Player statistics**:
```sql
CREATE INDEX idx_player_stats_game ON player_game_stats(game_id);
CREATE INDEX idx_player_stats_player ON player_game_stats(player_id);
```

**Time-based queries**:
```sql
CREATE INDEX idx_games_week ON games(week);
CREATE INDEX idx_games_season ON games(season);
CREATE INDEX idx_games_dynasty_season ON games(dynasty_id, season, week);
CREATE INDEX idx_standings_season ON standings(season);
CREATE INDEX idx_events_timestamp ON events(timestamp);
```

**Events**:
```sql
CREATE INDEX idx_events_game_id ON events(game_id);
CREATE INDEX idx_events_timestamp ON events(timestamp);
CREATE INDEX idx_events_event_type ON events(event_type);
```

### Query Optimization Tips

1. **Always filter by dynasty_id first**: Dramatically reduces result set
   ```sql
   -- Good (uses index efficiently)
   SELECT * FROM games WHERE dynasty_id = 'eagles_rebuild_2024' AND week = 17;

   -- Less optimal (misses dynasty filter)
   SELECT * FROM games WHERE week = 17;
   ```

2. **Use composite conditions**: SQLite can use multiple indexes
   ```sql
   SELECT * FROM standings
   WHERE dynasty_id = 'eagles_rebuild_2024'
     AND season = 2024
     AND team_id = 22;
   ```

3. **Batch event retrieval**: Single call gets all event types
   ```sql
   -- Efficient polymorphic retrieval
   SELECT * FROM events
   WHERE game_id = 'season_2024_week_17'
   ORDER BY timestamp ASC;
   ```

4. **Leverage UNIQUE constraints**: For upsert patterns
   ```sql
   INSERT INTO standings (...)
   ON CONFLICT(dynasty_id, team_id, season)
   DO UPDATE SET wins = wins + 1;
   ```

---

## Entity Relationship Diagram

```
┌─────────────┐
│  dynasties  │ (Master franchise record)
│─────────────│
│ dynasty_id  │◄─────────────────────────────┐
│ dynasty_name│                              │
│ user_team_id│                              │
│ created_at  │                              │
│ settings    │                              │
└─────────────┘                              │
                                             │ FK: dynasty_id
                                             │ (ON DELETE CASCADE)
                                             │
        ┌────────────────────────────────────┼────────────────────────┐
        │                                    │                        │
        ▼                                    ▼                        ▼
┌─────────────┐                     ┌─────────────┐          ┌─────────────┐
│    games    │                     │  standings  │          │  schedules  │
│─────────────│                     │─────────────│          │─────────────│
│ game_id (PK)│◄────┐               │ standing_id │          │ schedule_id │
│ dynasty_id  │     │ FK: game_id   │ dynasty_id  │          │ dynasty_id  │
│ away_team_id│     │               │ team_id     │          │ season      │
│ home_team_id│     │               │ season      │          │ week        │
│ away_score  │     │               │ wins/losses │          │ away_team_id│
│ home_score  │     │               │ splits      │          │ home_team_id│
│ week/season │     │               └─────────────┘          │ game_date   │
└─────────────┘     │                                        │ status      │
        │           │                                        └─────────────┘
        │           │
        │           │               ┌─────────────┐          ┌──────────────┐
        │           │               │dynasty_     │          │playoff_      │
        │           │               │seasons      │          │seedings      │
        │           │               │─────────────│          │──────────────│
        │           │               │ season_id   │          │ seeding_id   │
        │           │               │ dynasty_id  │          │ dynasty_id   │
        │           │               │ season      │          │ season       │
        │           │               │ user_team   │          │ conference   │
        │           │               │ playoff_    │          │ seed         │
        │           │               │   result    │          │ team_id      │
        │           │               │ mvp_player  │          │ tiebreaker   │
        │           │               └─────────────┘          └──────────────┘
        │           │
        │           │               ┌─────────────┐          ┌──────────────┐
        │           └──────────────►│box_scores   │          │tiebreaker_   │
        │                           │─────────────│          │applications  │
        │                           │ box_score_id│          │──────────────│
        │                           │ dynasty_id  │          │ tiebreaker_id│
        │                           │ game_id (FK)│          │ dynasty_id   │
        │                           │ quarter     │          │ season       │
        │                           │   scores    │          │ tiebreaker_  │
        │                           │ team_stats  │          │   type       │
        │                           └─────────────┘          │ teams_       │
        │                                                    │   involved   │
        │                                                    └──────────────┘
        │
        │                           ┌─────────────┐
        └──────────────────────────►│player_game_ │
                                    │stats        │
                                    │─────────────│
                                    │ stat_id     │
                                    │ dynasty_id  │
                                    │ game_id (FK)│
                                    │ player_id   │
                                    │ team_id     │
                                    │ position    │
                                    │ pass_stats  │
                                    │ rush_stats  │
                                    │ recv_stats  │
                                    │ def_stats   │
                                    │ st_stats    │
                                    │ ol_stats    │
                                    └─────────────┘

┌──────────────┐                   ┌─────────────┐
│playoff_      │                   │   events    │ (Polymorphic)
│brackets      │                   │─────────────│
│──────────────│                   │ event_id    │
│ bracket_id   │                   │ event_type  │
│ dynasty_id   │◄──────────────────┤ dynasty_id  │ (v2.3.0+)
│ season       │                   │ timestamp   │
│ conference   │                   │ game_id     │
│ round        │                   │ data (JSON) │
│ matchup_num  │                   │   └─ parameters
│ home_team_id │                   │      └─ results
│ away_team_id │                   │      └─ metadata
│ winner_id    │                   └─────────────┘
│ game_id      │
└──────────────┘

Legend:
────► Foreign Key relationship (ON DELETE CASCADE)
═══► Unique constraint
```

---

## Common Query Examples

### Dynasty Queries

**Get all games for a dynasty**:
```sql
SELECT * FROM games
WHERE dynasty_id = 'eagles_rebuild_2024'
ORDER BY game_date DESC;
```

**Get current standings for a dynasty season**:
```sql
SELECT
    s.team_id,
    s.wins,
    s.losses,
    s.ties,
    s.points_for,
    s.points_against,
    (s.points_for - s.points_against) AS point_differential
FROM standings s
WHERE s.dynasty_id = 'eagles_rebuild_2024'
  AND s.season = 2024
ORDER BY s.wins DESC, point_differential DESC;
```

**Get user team history across seasons**:
```sql
SELECT
    ds.season,
    ds.user_team_wins,
    ds.user_team_losses,
    ds.playoff_result,
    ds.mvp_player_id
FROM dynasty_seasons ds
WHERE ds.dynasty_id = 'eagles_rebuild_2024'
ORDER BY ds.season ASC;
```

### Statistics Queries

**Get all passing stats for a player**:
```sql
SELECT
    pgs.game_id,
    pgs.pass_attempts,
    pgs.pass_completions,
    pgs.pass_yards,
    pgs.pass_touchdowns,
    pgs.interceptions,
    ROUND(pgs.pass_yards * 1.0 / pgs.pass_attempts, 1) AS yards_per_attempt,
    ROUND(pgs.pass_completions * 100.0 / pgs.pass_attempts, 1) AS completion_pct
FROM player_game_stats pgs
WHERE pgs.dynasty_id = 'eagles_rebuild_2024'
  AND pgs.player_id = 'player_22_qb_1'
  AND pgs.pass_attempts > 0
ORDER BY pgs.created_at DESC;
```

**Get season totals for a team**:
```sql
SELECT
    pgs.position,
    COUNT(DISTINCT pgs.player_id) AS num_players,
    SUM(pgs.rush_attempts) AS total_rush_attempts,
    SUM(pgs.rush_yards) AS total_rush_yards,
    SUM(pgs.rush_touchdowns) AS total_rush_tds,
    SUM(pgs.receptions) AS total_receptions,
    SUM(pgs.receiving_yards) AS total_rec_yards,
    SUM(pgs.receiving_touchdowns) AS total_rec_tds
FROM player_game_stats pgs
JOIN games g ON pgs.game_id = g.game_id
WHERE pgs.dynasty_id = 'eagles_rebuild_2024'
  AND pgs.team_id = 22
  AND g.season = 2024
GROUP BY pgs.position
ORDER BY pgs.position;
```

**Get top performers by category**:
```sql
-- Top passers by yards
SELECT
    pgs.player_name,
    pgs.team_id,
    COUNT(DISTINCT pgs.game_id) AS games_played,
    SUM(pgs.pass_yards) AS total_pass_yards,
    SUM(pgs.pass_touchdowns) AS total_pass_tds
FROM player_game_stats pgs
JOIN games g ON pgs.game_id = g.game_id
WHERE pgs.dynasty_id = 'eagles_rebuild_2024'
  AND g.season = 2024
  AND pgs.pass_attempts > 0
GROUP BY pgs.player_id, pgs.player_name, pgs.team_id
ORDER BY total_pass_yards DESC
LIMIT 10;
```

### Event Queries

**Get all events for a dynasty (polymorphic retrieval with dynasty isolation)**:
```sql
SELECT
    event_id,
    event_type,
    timestamp,
    game_id,
    dynasty_id,
    json_extract(data, '$.parameters') AS parameters,
    json_extract(data, '$.results') AS results,
    json_extract(data, '$.metadata') AS metadata
FROM events
WHERE dynasty_id = 'eagles_rebuild_2024'
ORDER BY timestamp ASC;
```

**Get events for specific dynasty and time range**:
```sql
SELECT * FROM events
WHERE dynasty_id = 'eagles_rebuild_2024'
  AND timestamp BETWEEN 1703509200000 AND 1704114000000
ORDER BY timestamp ASC;
```

**Get specific event type for dynasty**:
```sql
SELECT * FROM events
WHERE dynasty_id = 'eagles_rebuild_2024'
  AND event_type = 'SCOUTING'
ORDER BY timestamp DESC
LIMIT 10;
```

**Get games that need simulation (no results yet)**:
```sql
SELECT
    event_id,
    event_type,
    timestamp,
    json_extract(data, '$.parameters.away_team_id') AS away_team,
    json_extract(data, '$.parameters.home_team_id') AS home_team
FROM events
WHERE event_type = 'GAME'
  AND json_extract(data, '$.results') IS NULL
ORDER BY timestamp ASC;
```

**Update event with results after simulation**:
```sql
UPDATE events
SET data = json_set(
    data,
    '$.results',
    json('{"away_score": 9, "home_score": 24, "total_yards_away": 287}')
)
WHERE event_id = 'event_550e8400-e29b-41d4-a716-446655440000';
```

### Playoff Queries

**Get playoff bracket for a season**:
```sql
SELECT
    pb.conference,
    pb.round,
    pb.matchup_number,
    pb.away_team_id,
    pb.home_team_id,
    pb.away_score,
    pb.home_score,
    pb.winner_team_id
FROM playoff_brackets pb
WHERE pb.dynasty_id = 'eagles_rebuild_2024'
  AND pb.season = 2024
ORDER BY
    CASE pb.round
        WHEN 'WILD_CARD' THEN 1
        WHEN 'DIVISIONAL' THEN 2
        WHEN 'CONFERENCE' THEN 3
        WHEN 'SUPER_BOWL' THEN 4
    END,
    pb.conference,
    pb.matchup_number;
```

**Get playoff seedings with standings**:
```sql
SELECT
    ps.seed,
    ps.conference,
    ps.team_id,
    ps.wins,
    ps.losses,
    ps.tiebreaker_note,
    s.division_wins,
    s.conference_wins
FROM playoff_seedings ps
JOIN standings s
    ON ps.dynasty_id = s.dynasty_id
    AND ps.team_id = s.team_id
    AND ps.season = s.season
WHERE ps.dynasty_id = 'eagles_rebuild_2024'
  AND ps.season = 2024
ORDER BY ps.conference, ps.seed;
```

### Schedule Queries

**Get upcoming games for current week**:
```sql
SELECT
    sch.week,
    sch.game_date,
    sch.away_team_id,
    sch.home_team_id,
    sch.game_type,
    sch.status
FROM schedules sch
WHERE sch.dynasty_id = 'eagles_rebuild_2024'
  AND sch.season = 2024
  AND sch.week = 17
  AND sch.status = 'SCHEDULED'
ORDER BY sch.game_date;
```

**Get team's remaining schedule**:
```sql
SELECT
    sch.week,
    sch.game_date,
    CASE
        WHEN sch.away_team_id = 22 THEN 'Away'
        ELSE 'Home'
    END AS location,
    CASE
        WHEN sch.away_team_id = 22 THEN sch.home_team_id
        ELSE sch.away_team_id
    END AS opponent_id,
    sch.status
FROM schedules sch
WHERE sch.dynasty_id = 'eagles_rebuild_2024'
  AND sch.season = 2024
  AND (sch.away_team_id = 22 OR sch.home_team_id = 22)
  AND sch.status != 'COMPLETED'
ORDER BY sch.week;
```

---

## Integration Notes

### Event System Integration

The **events** table provides polymorphic storage for multiple event types. Integration patterns:

**1. GameEvent Integration**:
- Store game parameters when scheduling
- Execute simulation later via `FullGameSimulator`
- Update with results after simulation
- Link to `games` table via `game_id`

```python
from events import GameEvent, EventDatabaseAPI

# Create and schedule game
game = GameEvent(away_team_id=22, home_team_id=23, ...)
event_db = EventDatabaseAPI("data/database/nfl_simulation.db")
event_db.insert_event(game)  # Stores parameters only

# Later: simulate and update
result = game.simulate()
event_db.update_event(game)  # Adds cached results
```

**2. Linking Events to Games**:
- Events can reference `games.game_id` in metadata
- Games can be created from event results
- Box scores generated from event data

```python
# After simulation, create game record
game_record = {
    "game_id": game.get_game_id(),
    "dynasty_id": metadata["dynasty_id"],
    "away_team_id": game.away_team_id,
    "home_team_id": game.home_team_id,
    "away_score": result.data["away_score"],
    "home_score": result.data["home_score"],
    # ...
}
# Insert into games table
```

**3. Mixed Timeline Retrieval**:
- Single query gets all event types for a context
- Each event knows how to reconstruct itself
- Enables season timelines with games, scouting, trades, etc.

```python
# Get all events for a week
events = event_db.get_events_by_game_id("season_2024_week_17")

# Polymorphic processing
for event_data in events:
    if event_data['event_type'] == 'GAME':
        game = GameEvent.from_database(event_data)
        # Display game result or simulate if needed
    elif event_data['event_type'] == 'SCOUTING':
        scout = ScoutingEvent.from_database(event_data)
        # Display scouting reports
```

### Dynasty Isolation Implementation

**All statistics queries must scope by dynasty_id**:

```python
# Good: Dynasty-isolated query
cursor.execute('''
    SELECT * FROM games
    WHERE dynasty_id = ? AND week = ?
''', (dynasty_id, week))

# Bad: Missing dynasty isolation
cursor.execute('''
    SELECT * FROM games
    WHERE week = ?
''', (week,))  # Returns games from ALL dynasties!
```

**Use transactions for multi-table updates**:

```python
conn = sqlite3.connect(db_path)
try:
    conn.execute('BEGIN TRANSACTION')

    # Insert game
    conn.execute('''INSERT INTO games ...''')

    # Insert player stats
    conn.executemany('''INSERT INTO player_game_stats ...''', stats_records)

    # Update standings
    conn.execute('''UPDATE standings ...''')

    conn.execute('COMMIT')
except Exception as e:
    conn.execute('ROLLBACK')
    raise
```

### Performance Considerations

**Batch Inserts**:
- Use `executemany()` for multiple records
- Use transactions for atomic operations
- Event system supports `insert_events()` for batch performance

```python
# Single insert: O(n) transactions
for stat in player_stats:
    conn.execute('''INSERT INTO player_game_stats ...''')

# Batch insert: O(1) transaction (10-50x faster)
conn.execute('BEGIN TRANSACTION')
conn.executemany('''INSERT INTO player_game_stats ...''', player_stats)
conn.execute('COMMIT')
```

**Index Usage**:
- Always filter by `dynasty_id` first
- Use composite indexes for multi-column filters
- EXPLAIN QUERY PLAN to verify index usage

```sql
EXPLAIN QUERY PLAN
SELECT * FROM games
WHERE dynasty_id = 'eagles_rebuild_2024'
  AND week = 17;
-- Should show: SEARCH TABLE games USING INDEX idx_games_dynasty_id
```

---

## Migration and Versioning

### Schema Version

Current version: **2.3.0** (with dynasty-isolated events)

Version history:
- **1.0.0**: Initial schema with dynasty isolation
- **1.1.0**: Added events table for polymorphic event system
- **2.0.0**: Production schema update - simplified tables to match actual implementation, updated dynasties table with career tracking, streamlined player_game_stats, updated all indexes
- **2.1.0**: Added season_type support for regular season/playoff separation
- **2.2.0**: Added complete salary cap system - 8 new tables (player_contracts, contract_year_details, team_salary_cap, franchise_tags, rfa_tenders, dead_money, cap_transactions, league_salary_cap_history) with full dynasty isolation
- **2.3.0**: Added dynasty_id column to events table with foreign key constraint and composite indexes for proper dynasty isolation (migration: 001_add_dynasty_id_to_events.py)

### Adding New Tables

When adding new tables, follow the dynasty isolation pattern:

```sql
CREATE TABLE new_feature (
    feature_id INTEGER PRIMARY KEY AUTOINCREMENT,
    dynasty_id TEXT NOT NULL,
    -- other columns --
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id)
        ON DELETE CASCADE
);

CREATE INDEX idx_new_feature_dynasty_id ON new_feature(dynasty_id);
```

### Migration Guidelines

1. **Never drop columns**: Add new columns with DEFAULT values
2. **Use transactions**: Wrap schema changes in BEGIN/COMMIT
3. **Backup first**: Always backup database before migration
4. **Test on copy**: Test migration on database copy first
5. **Version tracking**: Update schema version in documentation

Example migration:

```sql
BEGIN TRANSACTION;

-- Add new column with default
ALTER TABLE games ADD COLUMN attendance INTEGER DEFAULT 0;

-- Create index if needed
CREATE INDEX idx_games_attendance ON games(attendance);

-- Update schema version (if you have a version table)
-- UPDATE schema_version SET version = '1.2.0';

COMMIT;
```

### Backward Compatibility

The database schema maintains backward compatibility:

- New columns use DEFAULT values (safe for existing code)
- Foreign keys use CASCADE for automatic cleanup
- Indexes don't affect correctness, only performance
- Event system uses flexible JSON (no schema changes for new event types)

---

## Summary

This database schema provides:

✅ **Dynasty isolation** for multi-user/multi-franchise support
✅ **Comprehensive statistics** tracking for all positions
✅ **NFL-realistic standings** with conference/division/home/away splits
✅ **Playoff systems** with seeding, tiebreakers, and tournament brackets
✅ **Complete salary cap system** with contracts, dead money, franchise tags, and compliance tracking
✅ **Polymorphic event system** for mixed timelines (games, scouting, etc.)
✅ **Performance optimization** through strategic indexing
✅ **Referential integrity** via foreign key constraints
✅ **Transaction support** for data consistency
✅ **Flexible JSON storage** for extensibility

For implementation details, see:
- `src/database/connection.py`: Database initialization
- `src/database/api.py`: Data retrieval API
- `src/database/migrations/002_salary_cap_schema.sql`: Salary cap schema migration
- `src/salary_cap/`: Complete salary cap system implementation
- `src/persistence/daily_persister.py`: Batch persistence
- `src/events/event_database_api.py`: Event storage API
- `docs/specifications/base_event_interface.md`: Event interface specification
- `docs/specifications/salary_cap_system.md`: Complete NFL salary cap rules
- `docs/plans/salary_cap_plan.md`: Salary cap implementation plan
