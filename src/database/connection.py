"""
Database Connection Module

Manages SQLite database connections and schema for NFL simulation.
Supports multiple dynasties with complete data isolation.
"""

import sqlite3
import os
from pathlib import Path
from datetime import datetime
import uuid
from typing import Optional, Dict, Any
import logging


class DatabaseConnection:
    """
    Manages SQLite database connection and operations.
    
    Features:
    - WAL mode for better concurrency
    - Dynasty-based data isolation
    - Automatic schema creation
    - Performance-optimized indexes
    """
    
    def __init__(self, db_path: str = "data/database/nfl_simulation.db"):
        """
        Initialize database connection.
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        
        # Ensure directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
    def initialize_database(self) -> None:
        """Initialize database with WAL mode and create all tables."""
        conn = sqlite3.connect(self.db_path)
        
        try:
            # Enable WAL mode for better concurrency
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA foreign_keys=ON")
            
            # Create initial schema
            self._create_tables(conn)
            
            conn.commit()
            self.logger.info(f"Database initialized successfully at {self.db_path}")
            
        except Exception as e:
            conn.rollback()
            self.logger.error(f"Error initializing database: {e}")
            raise
        finally:
            conn.close()
    
    def _create_tables(self, conn: sqlite3.Connection) -> None:
        """Create all database tables with dynasty support."""
        
        # Dynasties table - master record for each dynasty/franchise
        conn.execute('''
            CREATE TABLE IF NOT EXISTS dynasties (
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
            )
        ''')
        
        # Games table with dynasty_id
        conn.execute('''
            CREATE TABLE IF NOT EXISTS games (
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
            )
        ''')
        
        # Player stats table with dynasty_id
        conn.execute('''
            CREATE TABLE IF NOT EXISTS player_game_stats (
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
            )
        ''')
        
        # Standings table with dynasty_id
        conn.execute('''
            CREATE TABLE IF NOT EXISTS standings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dynasty_id TEXT NOT NULL,
                team_id INTEGER NOT NULL,
                season INTEGER NOT NULL,
                
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
                
                FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id),
                UNIQUE(dynasty_id, team_id, season)
            )
        ''')
        
        # Schedules table with dynasty_id
        conn.execute('''
            CREATE TABLE IF NOT EXISTS schedules (
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
            )
        ''')
        
        # Season summary table for dynasty progress
        conn.execute('''
            CREATE TABLE IF NOT EXISTS dynasty_seasons (
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
            )
        ''')

        # Dynasty state table - tracks current simulation state
        conn.execute('''
            CREATE TABLE IF NOT EXISTS dynasty_state (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dynasty_id TEXT NOT NULL,
                season INTEGER NOT NULL,
                current_date TEXT NOT NULL,
                current_phase TEXT NOT NULL,
                current_week INTEGER,
                last_simulated_game_id TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id),
                UNIQUE(dynasty_id, season)
            )
        ''')

        # Box scores table for detailed game information
        conn.execute('''
            CREATE TABLE IF NOT EXISTS box_scores (
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
            )
        ''')

        # Playoff seedings table - results of playoff seeding calculations
        conn.execute('''
            CREATE TABLE IF NOT EXISTS playoff_seedings (
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
            )
        ''')

        # Tiebreaker applications table - detailed tracking of tiebreaker usage
        conn.execute('''
            CREATE TABLE IF NOT EXISTS tiebreaker_applications (
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
            )
        ''')

        # Playoff brackets table - for managing playoff tournament progression
        conn.execute('''
            CREATE TABLE IF NOT EXISTS playoff_brackets (
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
            )
        ''')

        # Events table - generic event storage for polymorphic event system
        # Implements Event Database API specification
        conn.execute('''
            CREATE TABLE IF NOT EXISTS events (
                event_id TEXT PRIMARY KEY,
                event_type TEXT NOT NULL,       -- 'GAME', 'MEDIA', 'TRADE', 'INJURY', etc.
                timestamp INTEGER NOT NULL,     -- Unix timestamp in milliseconds
                game_id TEXT NOT NULL,          -- Game/context identifier for grouping
                dynasty_id TEXT NOT NULL,       -- Dynasty isolation (FK to dynasties)
                data TEXT NOT NULL,             -- JSON event data
                FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE
            )
        ''')

        # Players table - master player data per dynasty
        # Stores all player attributes and identities (JSON files only used for initialization)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS players (
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
            )
        ''')

        # Team rosters table - links players to teams for roster management
        # Supports depth chart ordering and roster status tracking
        conn.execute('''
            CREATE TABLE IF NOT EXISTS team_rosters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dynasty_id TEXT NOT NULL,
                team_id INTEGER NOT NULL,
                player_id INTEGER NOT NULL,     -- References players.player_id (auto-generated int)
                depth_chart_order INTEGER DEFAULT 99,  -- Lower = higher on depth chart
                roster_status TEXT DEFAULT 'active',   -- 'active', 'inactive', 'injured_reserve', 'practice_squad'
                joined_date TEXT,

                FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE,
                UNIQUE(dynasty_id, team_id, player_id)
            )
        ''')

        # ============================================================================
        # SALARY CAP SYSTEM TABLES
        # ============================================================================

        # Player contracts table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS player_contracts (
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
            )
        ''')

        # Contract year details table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS contract_year_details (
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
            )
        ''')

        # Create indexes for performance
        conn.execute("CREATE INDEX IF NOT EXISTS idx_games_dynasty_season ON games(dynasty_id, season, week)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_games_teams ON games(home_team_id, away_team_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_games_dynasty_date ON games(dynasty_id, game_date)")

        # Season type indexes for regular season/playoff separation (Phase 1 - Full Season Simulation)
        # NOTE: season_type column doesn't exist in current schema - using game_type instead
        # conn.execute("CREATE INDEX IF NOT EXISTS idx_games_season_type ON games(dynasty_id, season, season_type)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_games_type ON games(game_type)")

        conn.execute("CREATE INDEX IF NOT EXISTS idx_player_stats_dynasty ON player_game_stats(dynasty_id, game_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_player_stats_player ON player_game_stats(player_id, dynasty_id)")

        # Player stats season type indexes for filtering regular season vs playoff stats
        # NOTE: season_type column doesn't exist in player_game_stats table - commented out
        # conn.execute("CREATE INDEX IF NOT EXISTS idx_stats_season_type ON player_game_stats(dynasty_id, season_type)")
        # conn.execute("CREATE INDEX IF NOT EXISTS idx_stats_player_type ON player_game_stats(player_id, season_type)")

        conn.execute("CREATE INDEX IF NOT EXISTS idx_standings_dynasty ON standings(dynasty_id, season)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_standings_team ON standings(team_id, season)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_schedules_dynasty ON schedules(dynasty_id, season, week)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_schedules_teams ON schedules(home_team_id, away_team_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_dynasty_seasons ON dynasty_seasons(dynasty_id, season)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_box_scores ON box_scores(dynasty_id, game_id)")

        # Player roster indexes for fast lookups
        conn.execute("CREATE INDEX IF NOT EXISTS idx_players_dynasty ON players(dynasty_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_players_team ON players(dynasty_id, team_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_players_lookup ON players(dynasty_id, player_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_rosters_team ON team_rosters(dynasty_id, team_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_rosters_player ON team_rosters(dynasty_id, player_id)")

        # Playoff system indexes
        conn.execute("CREATE INDEX IF NOT EXISTS idx_playoff_seedings_dynasty ON playoff_seedings(dynasty_id, season)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_playoff_seedings_conference ON playoff_seedings(dynasty_id, season, conference)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tiebreaker_apps ON tiebreaker_applications(dynasty_id, season)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_playoff_brackets ON playoff_brackets(dynasty_id, season, round_name)")

        # Events table indexes for polymorphic event retrieval
        conn.execute("CREATE INDEX IF NOT EXISTS idx_events_game_id ON events(game_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type)")
        # Dynasty-aware composite indexes for efficient dynasty-filtered queries
        conn.execute("CREATE INDEX IF NOT EXISTS idx_events_dynasty_timestamp ON events(dynasty_id, timestamp)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_events_dynasty_type ON events(dynasty_id, event_type)")

        # Salary cap system indexes
        conn.execute("CREATE INDEX IF NOT EXISTS idx_contracts_player ON player_contracts(player_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_contracts_team_season ON player_contracts(team_id, start_year)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_contracts_dynasty ON player_contracts(dynasty_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_contracts_active ON player_contracts(is_active)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_contracts_team_active ON player_contracts(team_id, is_active)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_contract_details_contract ON contract_year_details(contract_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_contract_details_season ON contract_year_details(season_year)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_contract_details_contract_year ON contract_year_details(contract_id, contract_year)")

        # Initialize standings for dynasties with games but missing standings
        self._initialize_standings_if_empty(conn)

        self.logger.info("All tables and indexes created successfully")
    
    def create_new_dynasty(self, dynasty_name: str, owner_name: str, team_id: int) -> str:
        """
        Create a new dynasty entry.
        
        Args:
            dynasty_name: Name of the dynasty
            owner_name: Name of the owner/player
            team_id: ID of the team (1-32)
            
        Returns:
            The generated dynasty_id
        """
        dynasty_id = str(uuid.uuid4())
        conn = sqlite3.connect(self.db_path)
        
        try:
            conn.execute('''
                INSERT INTO dynasties (dynasty_id, dynasty_name, owner_name, team_id)
                VALUES (?, ?, ?, ?)
            ''', (dynasty_id, dynasty_name, owner_name, team_id))
            
            conn.commit()
            self.logger.info(f"Created new dynasty: {dynasty_name} (ID: {dynasty_id})")
            
        except Exception as e:
            conn.rollback()
            self.logger.error(f"Error creating dynasty: {e}")
            raise
        finally:
            conn.close()
        
        return dynasty_id

    def ensure_dynasty_exists(
        self,
        dynasty_id: str,
        dynasty_name: Optional[str] = None,
        owner_name: Optional[str] = None,
        team_id: Optional[int] = None
    ) -> bool:
        """
        Ensure a dynasty record exists, creating it if necessary.

        This is useful for auto-creating dynasties when users start new simulations
        without explicitly creating a dynasty first.

        Args:
            dynasty_id: Dynasty identifier
            dynasty_name: Name of dynasty (defaults to dynasty_id)
            owner_name: Optional owner name
            team_id: Optional team ID (can be NULL for league-wide simulations)

        Returns:
            True if dynasty exists or was created, False on error
        """
        conn = sqlite3.connect(self.db_path)

        try:
            # Check if dynasty already exists
            cursor = conn.cursor()
            cursor.execute('SELECT dynasty_id FROM dynasties WHERE dynasty_id = ?', (dynasty_id,))
            exists = cursor.fetchone() is not None

            if exists:
                self.logger.debug(f"Dynasty already exists: {dynasty_id}")
                return True

            # Create new dynasty record
            if dynasty_name is None:
                dynasty_name = dynasty_id

            # Use team_id if provided, otherwise use 0 for league-wide simulations
            # (0 is a safe default that won't conflict with team IDs 1-32)
            if team_id is None:
                team_id = 0

            conn.execute('''
                INSERT INTO dynasties (dynasty_id, dynasty_name, owner_name, team_id)
                VALUES (?, ?, ?, ?)
            ''', (dynasty_id, dynasty_name, owner_name, team_id))

            conn.commit()
            self.logger.info(f"Auto-created dynasty: {dynasty_name} (ID: {dynasty_id})")
            return True

        except Exception as e:
            conn.rollback()
            self.logger.error(f"Error ensuring dynasty exists: {e}")
            return False
        finally:
            conn.close()

    def update_dynasty_team(self, dynasty_id: str, team_id: int) -> bool:
        """
        Update the team_id for an existing dynasty.

        Args:
            dynasty_id: Dynasty identifier to update
            team_id: New team ID (1-32)

        Returns:
            True if update successful, False otherwise
        """
        conn = sqlite3.connect(self.db_path)

        try:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE dynasties
                SET team_id = ?, last_played = CURRENT_TIMESTAMP
                WHERE dynasty_id = ?
            ''', (team_id, dynasty_id))

            affected_rows = cursor.rowcount
            conn.commit()

            if affected_rows > 0:
                self.logger.info(f"Updated dynasty {dynasty_id} to team_id {team_id}")
                return True
            else:
                self.logger.warning(f"No dynasty found with ID {dynasty_id}")
                return False

        except Exception as e:
            conn.rollback()
            self.logger.error(f"Error updating dynasty team: {e}")
            return False
        finally:
            conn.close()

    def _initialize_standings_if_empty(self, conn: sqlite3.Connection) -> None:
        """
        Initialize standings records for dynasties that have games but missing standings.

        This ensures all 32 NFL teams have standings entries for each season with games.
        Runs automatically on database connection to fix missing initialization data.

        Args:
            conn: Active database connection
        """
        try:
            # Find all dynasties that have games
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT dynasty_id FROM games")
            dynasties_with_games = [row[0] for row in cursor.fetchall()]

            if not dynasties_with_games:
                return  # No games yet, nothing to initialize

            # For each dynasty, get seasons with games
            for dynasty_id in dynasties_with_games:
                cursor.execute(
                    "SELECT DISTINCT season FROM games WHERE dynasty_id = ?",
                    (dynasty_id,)
                )
                seasons = [row[0] for row in cursor.fetchall()]

                # For each season, check if standings exist
                for season in seasons:
                    cursor.execute(
                        "SELECT COUNT(*) FROM standings WHERE dynasty_id = ? AND season = ?",
                        (dynasty_id, season)
                    )
                    existing_count = cursor.fetchone()[0]

                    # If missing standings (should be 32 teams)
                    if existing_count < 32:
                        # Get existing team IDs to avoid duplicates
                        cursor.execute(
                            "SELECT team_id FROM standings WHERE dynasty_id = ? AND season = ?",
                            (dynasty_id, season)
                        )
                        existing_teams = {row[0] for row in cursor.fetchall()}

                        # Insert missing teams (1-32)
                        for team_id in range(1, 33):
                            if team_id not in existing_teams:
                                cursor.execute('''
                                    INSERT INTO standings (
                                        dynasty_id, team_id, season,
                                        wins, losses, ties,
                                        division_wins, division_losses, division_ties,
                                        conference_wins, conference_losses, conference_ties,
                                        home_wins, home_losses, home_ties,
                                        away_wins, away_losses, away_ties,
                                        points_for, points_against, point_differential
                                    ) VALUES (?, ?, ?, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
                                ''', (dynasty_id, team_id, season))

                        conn.commit()

                        # Log initialization for debugging
                        teams_added = 32 - existing_count
                        if teams_added > 0:
                            self.logger.info(
                                f"Initialized {teams_added} missing standings records for "
                                f"dynasty '{dynasty_id}', season {season}"
                            )

        except Exception as e:
            self.logger.error(f"Error initializing standings: {e}")
            # Don't raise - this is a best-effort initialization

    def get_connection(self) -> sqlite3.Connection:
        """
        Get a database connection with schema initialized.

        Returns:
            SQLite connection object with tables created
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        conn.execute("PRAGMA foreign_keys=ON")

        # Ensure tables exist (idempotent - safe to call multiple times)
        self._create_tables(conn)

        return conn
    
    def execute_query(self, query: str, params: tuple = None) -> list:
        """
        Execute a SELECT query and return results.
        
        Args:
            query: SQL query to execute
            params: Query parameters
            
        Returns:
            List of query results
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            results = cursor.fetchall()
            return results
            
        finally:
            conn.close()
    
    def execute_update(self, query: str, params: tuple = None) -> int:
        """
        Execute an INSERT/UPDATE/DELETE query.
        
        Args:
            query: SQL query to execute
            params: Query parameters
            
        Returns:
            Number of affected rows
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            conn.commit()
            return cursor.rowcount
            
        except Exception as e:
            conn.rollback()
            self.logger.error(f"Error executing update: {e}")
            raise
        finally:
            conn.close()
    
    def get_active_dynasties(self) -> list:
        """
        Get all active dynasties.
        
        Returns:
            List of active dynasty records
        """
        query = '''
            SELECT dynasty_id, dynasty_name, owner_name, team_id, 
                   total_seasons, championships_won, last_played
            FROM dynasties
            WHERE is_active = TRUE
            ORDER BY last_played DESC
        '''
        return self.execute_query(query)
    
    def get_dynasty_info(self, dynasty_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific dynasty.
        
        Args:
            dynasty_id: ID of the dynasty
            
        Returns:
            Dynasty information or None if not found
        """
        query = '''
            SELECT * FROM dynasties WHERE dynasty_id = ?
        '''
        results = self.execute_query(query, (dynasty_id,))
        
        if results:
            # Convert Row to dictionary
            row = results[0]
            return dict(zip(row.keys(), row))
        
        return None