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
                team_id INTEGER NOT NULL,
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
                game_type TEXT DEFAULT 'regular',  -- regular, playoff, super_bowl
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
        
        # Create indexes for performance
        conn.execute("CREATE INDEX IF NOT EXISTS idx_games_dynasty_season ON games(dynasty_id, season, week)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_games_teams ON games(home_team_id, away_team_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_player_stats_dynasty ON player_game_stats(dynasty_id, game_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_player_stats_player ON player_game_stats(player_id, dynasty_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_standings_dynasty ON standings(dynasty_id, season)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_standings_team ON standings(team_id, season)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_schedules_dynasty ON schedules(dynasty_id, season, week)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_schedules_teams ON schedules(home_team_id, away_team_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_dynasty_seasons ON dynasty_seasons(dynasty_id, season)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_box_scores ON box_scores(dynasty_id, game_id)")
        
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
    
    def get_connection(self) -> sqlite3.Connection:
        """
        Get a database connection.
        
        Returns:
            SQLite connection object
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        conn.execute("PRAGMA foreign_keys=ON")
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