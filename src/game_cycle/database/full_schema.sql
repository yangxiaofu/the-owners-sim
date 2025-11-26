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
                total_yards_home INTEGER,
                total_yards_away INTEGER,
                turnovers_home INTEGER DEFAULT 0,
                turnovers_away INTEGER DEFAULT 0,
                time_of_possession_home INTEGER,  -- in seconds
                time_of_possession_away INTEGER,
                game_duration_minutes INTEGER,
                overtime_periods INTEGER DEFAULT 0,
                game_date INTEGER,  -- Game date/time in milliseconds (for calendar)
                weather_conditions TEXT,
                attendance INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id)
            );
CREATE TABLE player_game_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dynasty_id TEXT NOT NULL,
                game_id TEXT NOT NULL,

                -- Season type for stat filtering and separation
                season_type TEXT NOT NULL DEFAULT 'regular_season',
                -- Values: 'regular_season' | 'playoffs'

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
                
                -- Rushing stats
                rushing_yards INTEGER DEFAULT 0,
                rushing_tds INTEGER DEFAULT 0,
                rushing_attempts INTEGER DEFAULT 0,
                rushing_long INTEGER DEFAULT 0,
                rushing_fumbles INTEGER DEFAULT 0,
                
                -- Receiving stats
                receiving_yards INTEGER DEFAULT 0,
                receiving_tds INTEGER DEFAULT 0,
                receptions INTEGER DEFAULT 0,
                targets INTEGER DEFAULT 0,
                receiving_long INTEGER DEFAULT 0,
                receiving_drops INTEGER DEFAULT 0,
                
                -- Defensive stats
                tackles_total INTEGER DEFAULT 0,
                tackles_solo INTEGER DEFAULT 0,
                tackles_assist INTEGER DEFAULT 0,
                sacks REAL DEFAULT 0,
                interceptions INTEGER DEFAULT 0,
                forced_fumbles INTEGER DEFAULT 0,
                fumbles_recovered INTEGER DEFAULT 0,
                passes_defended INTEGER DEFAULT 0,
                
                -- Special teams stats
                field_goals_made INTEGER DEFAULT 0,
                field_goals_attempted INTEGER DEFAULT 0,
                extra_points_made INTEGER DEFAULT 0,
                extra_points_attempted INTEGER DEFAULT 0,
                punts INTEGER DEFAULT 0,
                punt_yards INTEGER DEFAULT 0,

                -- Comprehensive Offensive Line stats
                pancakes INTEGER DEFAULT 0,
                sacks_allowed INTEGER DEFAULT 0,
                hurries_allowed INTEGER DEFAULT 0,
                pressures_allowed INTEGER DEFAULT 0,
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
                
                FOREIGN KEY (game_id) REFERENCES games(game_id),
                FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id)
            );
CREATE TABLE standings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dynasty_id TEXT NOT NULL,
                team_id INTEGER NOT NULL,
                season INTEGER NOT NULL,
                season_type TEXT NOT NULL DEFAULT 'regular_season',

                -- Regular season record
                wins INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0,
                ties INTEGER DEFAULT 0,

                -- Division record
                division_wins INTEGER DEFAULT 0,
                division_losses INTEGER DEFAULT 0,
                division_ties INTEGER DEFAULT 0,

                -- Conference record
                conference_wins INTEGER DEFAULT 0,
                conference_losses INTEGER DEFAULT 0,
                conference_ties INTEGER DEFAULT 0,

                -- Home/Away splits
                home_wins INTEGER DEFAULT 0,
                home_losses INTEGER DEFAULT 0,
                home_ties INTEGER DEFAULT 0,
                away_wins INTEGER DEFAULT 0,
                away_losses INTEGER DEFAULT 0,
                away_ties INTEGER DEFAULT 0,

                -- Points and differentials
                points_for INTEGER DEFAULT 0,
                points_against INTEGER DEFAULT 0,
                point_differential INTEGER DEFAULT 0,

                -- Streaks and rankings
                current_streak TEXT,
                division_rank INTEGER,
                conference_rank INTEGER,
                league_rank INTEGER,

                -- Playoff information
                playoff_seed INTEGER,
                made_playoffs BOOLEAN DEFAULT FALSE,
                made_wild_card BOOLEAN DEFAULT FALSE,
                won_wild_card BOOLEAN DEFAULT FALSE,
                won_division_round BOOLEAN DEFAULT FALSE,
                won_conference BOOLEAN DEFAULT FALSE,
                won_super_bowl BOOLEAN DEFAULT FALSE,

                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id)
                -- NOTE: UNIQUE constraint created as index below (not inline)
            );
CREATE UNIQUE INDEX idx_standings_unique
            ON standings(dynasty_id, team_id, season, season_type)
        ;
CREATE INDEX idx_standings_dynasty
            ON standings(dynasty_id, season)
        ;
CREATE INDEX idx_standings_team
            ON standings(team_id, season)
        ;
CREATE INDEX idx_standings_season_type
            ON standings(dynasty_id, season, season_type)
        ;
CREATE INDEX idx_standings_team_season_type
            ON standings(team_id, season, season_type)
        ;
CREATE TABLE schedules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dynasty_id TEXT NOT NULL,
                season INTEGER NOT NULL,
                week INTEGER NOT NULL,
                game_type TEXT DEFAULT 'regular',
                home_team_id INTEGER NOT NULL,
                away_team_id INTEGER NOT NULL,
                
                -- Schedule metadata
                time_slot TEXT,
                is_primetime BOOLEAN DEFAULT FALSE,
                is_divisional BOOLEAN DEFAULT FALSE,
                is_conference BOOLEAN DEFAULT FALSE,
                is_played BOOLEAN DEFAULT FALSE,
                
                -- Link to game result
                game_id TEXT,
                
                -- Schedule creation
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                scheduled_date DATE,
                
                FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id),
                FOREIGN KEY (game_id) REFERENCES games(game_id)
            );
CREATE TABLE dynasty_seasons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dynasty_id TEXT NOT NULL,
                season INTEGER NOT NULL,
                
                -- Season record
                final_wins INTEGER,
                final_losses INTEGER,
                final_ties INTEGER,
                win_percentage REAL,
                
                -- Rankings
                division_rank INTEGER,
                conference_rank INTEGER,
                league_rank INTEGER,
                power_ranking INTEGER,
                
                -- Playoff results
                made_playoffs BOOLEAN DEFAULT FALSE,
                playoff_seed INTEGER,
                playoff_wins INTEGER DEFAULT 0,
                playoff_losses INTEGER DEFAULT 0,
                playoff_result TEXT,  -- 'missed', 'wild_card', 'division', 'conference', 'super_bowl_loss', 'super_bowl_win'
                
                -- Draft
                draft_position INTEGER,
                draft_picks_total INTEGER,
                
                -- Season stats
                total_points_for INTEGER,
                total_points_against INTEGER,
                total_yards_offense INTEGER,
                total_yards_defense INTEGER,
                
                -- Awards
                mvp_winner TEXT,
                dpoy_winner TEXT,
                oroy_winner TEXT,
                droy_winner TEXT,
                
                completed_at TIMESTAMP,
                
                FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id),
                UNIQUE(dynasty_id, season)
            );
CREATE TABLE dynasty_state (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dynasty_id TEXT NOT NULL,
                season INTEGER NOT NULL,
                "current_date" TEXT NOT NULL,
                current_phase TEXT NOT NULL,
                current_week INTEGER,
                last_simulated_game_id TEXT,
                current_draft_pick INTEGER DEFAULT 0,
                draft_in_progress INTEGER DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id),
                UNIQUE(dynasty_id, season)
            );
CREATE TABLE box_scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dynasty_id TEXT NOT NULL,
                game_id TEXT NOT NULL,
                team_id INTEGER NOT NULL,
                
                -- Quarter scores
                q1_score INTEGER DEFAULT 0,
                q2_score INTEGER DEFAULT 0,
                q3_score INTEGER DEFAULT 0,
                q4_score INTEGER DEFAULT 0,
                ot_score INTEGER DEFAULT 0,
                
                -- Team totals
                first_downs INTEGER DEFAULT 0,
                third_down_att INTEGER DEFAULT 0,
                third_down_conv INTEGER DEFAULT 0,
                fourth_down_att INTEGER DEFAULT 0,
                fourth_down_conv INTEGER DEFAULT 0,
                
                total_yards INTEGER DEFAULT 0,
                passing_yards INTEGER DEFAULT 0,
                rushing_yards INTEGER DEFAULT 0,
                
                turnovers INTEGER DEFAULT 0,
                penalties INTEGER DEFAULT 0,
                penalty_yards INTEGER DEFAULT 0,
                
                time_of_possession INTEGER,  -- in seconds
                
                FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id),
                FOREIGN KEY (game_id) REFERENCES games(game_id),
                UNIQUE(game_id, team_id)
            );
CREATE TABLE playoff_seedings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dynasty_id TEXT NOT NULL,
                season INTEGER NOT NULL,
                conference TEXT NOT NULL,  -- 'AFC' or 'NFC'
                seed_number INTEGER NOT NULL,  -- 1-7
                team_id INTEGER NOT NULL,
                wins INTEGER NOT NULL,
                losses INTEGER NOT NULL,
                ties INTEGER DEFAULT 0,
                division_winner BOOLEAN NOT NULL,
                tiebreaker_applied TEXT,  -- Description of tiebreaker used
                eliminated_teams TEXT,    -- JSON array of team IDs eliminated
                points_for INTEGER DEFAULT 0,
                points_against INTEGER DEFAULT 0,
                strength_of_victory REAL DEFAULT 0.0,
                strength_of_schedule REAL DEFAULT 0.0,
                seeding_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id),
                UNIQUE(dynasty_id, season, conference, seed_number)
            );
CREATE TABLE tiebreaker_applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dynasty_id TEXT NOT NULL,
                season INTEGER NOT NULL,
                tiebreaker_type TEXT NOT NULL,  -- 'division', 'wildcard'
                rule_applied TEXT NOT NULL,     -- 'head_to_head', 'strength_of_victory', etc.
                teams_involved TEXT NOT NULL,   -- JSON array of team IDs
                winner_team_id INTEGER NOT NULL,
                calculation_details TEXT,       -- JSON with calculation breakdown
                application_order INTEGER,      -- Order tiebreaker was applied
                description TEXT,               -- Human-readable description

                FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id)
            );
CREATE TABLE playoff_brackets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dynasty_id TEXT NOT NULL,
                season INTEGER NOT NULL,
                round_name TEXT NOT NULL,       -- 'wild_card', 'divisional', 'conference', 'super_bowl'
                game_number INTEGER NOT NULL,   -- Game within round
                conference TEXT,                -- 'AFC', 'NFC', or NULL for Super Bowl
                home_seed INTEGER NOT NULL,
                away_seed INTEGER NOT NULL,
                home_team_id INTEGER NOT NULL,
                away_team_id INTEGER NOT NULL,
                game_date DATE,
                scheduled_time TIME,
                winner_team_id INTEGER,         -- NULL until game completed
                winner_score INTEGER,
                loser_score INTEGER,
                overtime_periods INTEGER DEFAULT 0,

                FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id)
            );
CREATE TABLE events (
                event_id TEXT PRIMARY KEY,
                event_type TEXT NOT NULL,       -- 'GAME', 'MEDIA', 'TRADE', 'INJURY', etc.
                timestamp INTEGER NOT NULL,     -- Unix timestamp in milliseconds
                game_id TEXT NOT NULL,          -- Game/context identifier for grouping
                dynasty_id TEXT NOT NULL,       -- Dynasty isolation (FK to dynasties)
                data TEXT NOT NULL,             -- JSON event data
                FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE
            );
CREATE TABLE players (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dynasty_id TEXT NOT NULL,
                player_id INTEGER NOT NULL,     -- Auto-generated unique ID per dynasty
                source_player_id TEXT,          -- Original JSON player_id (for reference only)
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                number INTEGER NOT NULL,
                team_id INTEGER NOT NULL,       -- 0 = free agent, 1-32 = teams
                positions TEXT NOT NULL,        -- JSON array: ["quarterback", "punter"]
                attributes TEXT NOT NULL,       -- JSON object: {"overall": 85, "speed": 90, ...}
                contract_id INTEGER,            -- FK to player_contracts (future salary cap integration)
                status TEXT DEFAULT 'active',   -- 'active', 'injured', 'suspended', 'practice_squad'
                years_pro INTEGER DEFAULT 0,
                birthdate TEXT DEFAULT NULL,    -- Player birth date (YYYY-MM-DD format)
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE,
                -- Note: contract_id FK will be added when player_contracts table exists
                UNIQUE(dynasty_id, player_id)   -- Guaranteed unique with auto-generated IDs
            );
CREATE TABLE team_rosters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dynasty_id TEXT NOT NULL,
                team_id INTEGER NOT NULL,
                player_id INTEGER NOT NULL,     -- References players.player_id (auto-generated int)
                depth_chart_order INTEGER DEFAULT 99,  -- Lower = higher on depth chart
                roster_status TEXT DEFAULT 'active',   -- 'active', 'inactive', 'injured_reserve', 'practice_squad'
                joined_date TEXT,

                FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE,
                UNIQUE(dynasty_id, team_id, player_id)
            );
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
                modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE
            );
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

                -- Guarantees for this year
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
CREATE TABLE draft_order (
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
                is_executed INTEGER DEFAULT 0,

                -- Compensatory Picks
                is_compensatory INTEGER DEFAULT 0,
                comp_round_end INTEGER DEFAULT 0,

                -- Trade Information
                acquired_via_trade BOOLEAN NOT NULL DEFAULT FALSE,
                trade_date TIMESTAMP,
                original_trade_id TEXT,

                -- Metadata
                created_at INTEGER DEFAULT (strftime('%s', 'now') * 1000),
                updated_at INTEGER DEFAULT (strftime('%s', 'now') * 1000),

                FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE
            );
CREATE INDEX idx_games_dynasty_season ON games(dynasty_id, season, week);
CREATE INDEX idx_games_teams ON games(home_team_id, away_team_id);
CREATE INDEX idx_games_dynasty_date ON games(dynasty_id, game_date);
CREATE INDEX idx_games_type ON games(game_type);
CREATE INDEX idx_player_stats_dynasty ON player_game_stats(dynasty_id, game_id);
CREATE INDEX idx_player_stats_player ON player_game_stats(player_id, dynasty_id);
CREATE INDEX idx_schedules_dynasty ON schedules(dynasty_id, season, week);
CREATE INDEX idx_schedules_teams ON schedules(home_team_id, away_team_id);
CREATE INDEX idx_dynasty_seasons ON dynasty_seasons(dynasty_id, season);
CREATE INDEX idx_box_scores ON box_scores(dynasty_id, game_id);
CREATE INDEX idx_players_dynasty ON players(dynasty_id);
CREATE INDEX idx_players_team ON players(dynasty_id, team_id);
CREATE INDEX idx_players_lookup ON players(dynasty_id, player_id);
CREATE INDEX idx_rosters_team ON team_rosters(dynasty_id, team_id);
CREATE INDEX idx_rosters_player ON team_rosters(dynasty_id, player_id);
CREATE INDEX idx_playoff_seedings_dynasty ON playoff_seedings(dynasty_id, season);
CREATE INDEX idx_playoff_seedings_conference ON playoff_seedings(dynasty_id, season, conference);
CREATE INDEX idx_tiebreaker_apps ON tiebreaker_applications(dynasty_id, season);
CREATE INDEX idx_playoff_brackets ON playoff_brackets(dynasty_id, season, round_name);
CREATE INDEX idx_events_game_id ON events(game_id);
CREATE INDEX idx_events_timestamp ON events(timestamp);
CREATE INDEX idx_events_type ON events(event_type);
CREATE INDEX idx_events_dynasty_timestamp ON events(dynasty_id, timestamp);
CREATE INDEX idx_events_dynasty_type ON events(dynasty_id, event_type);
CREATE INDEX idx_contracts_player ON player_contracts(player_id);
CREATE INDEX idx_contracts_team_season ON player_contracts(team_id, start_year);
CREATE INDEX idx_contracts_dynasty ON player_contracts(dynasty_id);
CREATE INDEX idx_contracts_active ON player_contracts(is_active);
CREATE INDEX idx_contracts_team_active ON player_contracts(team_id, is_active);
CREATE INDEX idx_contract_details_contract ON contract_year_details(contract_id);
CREATE INDEX idx_contract_details_season ON contract_year_details(season_year);
CREATE INDEX idx_contract_details_contract_year ON contract_year_details(contract_id, contract_year);
CREATE INDEX idx_draft_order_dynasty ON draft_order(dynasty_id);
CREATE INDEX idx_draft_order_season ON draft_order(season);
CREATE INDEX idx_draft_order_dynasty_season ON draft_order(dynasty_id, season);
CREATE INDEX idx_draft_order_overall ON draft_order(overall_pick);
CREATE INDEX idx_draft_order_team ON draft_order(current_team_id);
CREATE INDEX idx_draft_order_round ON draft_order(round_number, pick_in_round);
CREATE TABLE draft_classes (
    draft_class_id TEXT PRIMARY KEY,
    dynasty_id TEXT NOT NULL,
    season INTEGER NOT NULL,
    generation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_prospects INTEGER DEFAULT 0,
    status TEXT DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE,
    UNIQUE(dynasty_id, season)
);
CREATE INDEX idx_draft_classes_dynasty ON draft_classes(dynasty_id);
CREATE INDEX idx_draft_classes_season ON draft_classes(dynasty_id, season);
CREATE TABLE draft_prospects (
    player_id INTEGER NOT NULL,
    draft_class_id TEXT NOT NULL,
    dynasty_id TEXT NOT NULL,

    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    position TEXT NOT NULL,
    age INTEGER NOT NULL,

    draft_round INTEGER NOT NULL,
    draft_pick INTEGER NOT NULL,
    projected_pick_min INTEGER,
    projected_pick_max INTEGER,

    overall INTEGER NOT NULL,
    attributes TEXT NOT NULL,

    college TEXT,
    hometown TEXT,
    home_state TEXT,

    archetype_id TEXT,

    scouted_overall INTEGER,
    scouting_confidence TEXT DEFAULT 'medium',

    is_drafted BOOLEAN DEFAULT FALSE,
    drafted_by_team_id INTEGER,
    drafted_round INTEGER,
    drafted_pick INTEGER,

    development_curve TEXT DEFAULT 'normal',

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (dynasty_id, player_id),
    FOREIGN KEY (draft_class_id) REFERENCES draft_classes(draft_class_id) ON DELETE CASCADE,
    FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE
);
CREATE INDEX idx_prospects_draft_class ON draft_prospects(draft_class_id);
CREATE INDEX idx_prospects_dynasty ON draft_prospects(dynasty_id);
CREATE INDEX idx_prospects_position ON draft_prospects(dynasty_id, position);
CREATE INDEX idx_prospects_available ON draft_prospects(dynasty_id, is_drafted);
CREATE INDEX idx_prospects_overall ON draft_prospects(draft_class_id, overall DESC);
CREATE INDEX idx_prospects_player_id ON draft_prospects(player_id);
CREATE INDEX idx_game_id ON events(game_id);
CREATE INDEX idx_timestamp ON events(timestamp);
CREATE INDEX idx_event_type ON events(event_type);
CREATE TABLE schema_migrations (
                        migration_name TEXT PRIMARY KEY,
                        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
