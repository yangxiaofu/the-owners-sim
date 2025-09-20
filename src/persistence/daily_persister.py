"""
Daily Data Persister

Handles persisting daily simulation results from stores to database.
Simple, testable, and follows single responsibility principle.
"""

import logging
from datetime import date, datetime
from typing import Dict, List, Any, Optional
import json


class DailyDataPersister:
    """
    Takes data from stores and saves to database after each simulation day.
    
    Single Responsibility: Move data from in-memory stores to persistent database.
    """
    
    def __init__(self, store_manager, database_connection, dynasty_id: str):
        """
        Initialize the daily persister.
        
        Args:
            store_manager: StoreManager instance containing game data
            database_connection: DatabaseConnection instance for persistence
            dynasty_id: ID of the current dynasty being simulated
        """
        self.store_manager = store_manager
        self.db = database_connection
        self.dynasty_id = dynasty_id
        self.logger = logging.getLogger(__name__)
        
        # Track persistence statistics
        self.total_days_persisted = 0
        self.total_games_persisted = 0
        self.total_stats_persisted = 0
        
    def persist_day(self, day_result) -> bool:
        """
        Persist a day's simulation results to the database.
        
        Args:
            day_result: DaySimulationResult containing the day's events
            
        Returns:
            bool: True if persistence was successful, False otherwise
        """
        # Skip if no events were executed
        if day_result.events_executed == 0:
            self.logger.debug(f"No events on {day_result.date}, skipping persistence")
            return True  # Not a failure, just nothing to persist
        
        try:
            # Extract data from stores
            games = self._get_games_for_date(day_result.date)
            player_stats = self._get_player_stats_for_games(games)
            standings = self._get_current_standings()
            
            # Only persist if there's data to save
            if not games and not standings:
                self.logger.debug(f"No game data for {day_result.date}, skipping persistence")
                return True
            
            # Save to database in a single transaction
            success = self._save_to_database(
                day_result.date,
                games,
                player_stats,
                standings
            )
            
            # Clear stores only if persistence was successful
            if success:
                self._clear_stores_for_date(day_result.date)
                self.total_days_persisted += 1
                self.logger.info(f"Successfully persisted {day_result.date} to database")
            else:
                self.logger.error(f"Failed to persist {day_result.date}, keeping data in stores")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error during persistence for {day_result.date}: {e}", exc_info=True)
            return False
    
    def _get_games_for_date(self, target_date: date) -> Dict[str, Any]:
        """
        Extract games from store for the specified date.
        
        Args:
            target_date: Date to get games for
            
        Returns:
            Dictionary of game_id -> game_result
        """
        games = {}
        
        # Get all games from the store
        for game_id, game_result in self.store_manager.game_result_store.data.items():
            # Check if game was on this date (you might need to adjust this logic)
            # For now, we'll assume the game_id contains date info or check game_result.date
            # This is simplified - you may need to enhance based on your data structure
            games[game_id] = game_result
        
        return games
    
    def _get_player_stats_for_games(self, games: Dict[str, Any]) -> Dict[str, List]:
        """
        Extract player statistics for the given games.

        Args:
            games: Dictionary of games to get stats for

        Returns:
            Dictionary of game_id -> list of player stats
        """
        player_stats = {}

        for game_id in games.keys():
            # Get stats from player stats store
            if game_id in self.store_manager.player_stats_store.data:
                stats = self.store_manager.player_stats_store.data[game_id]

                # Convert from dictionary to list (PlayerStatsStore stores as dict)
                if isinstance(stats, dict):
                    # Convert {player_name: PlayerGameStats} to [PlayerGameStats, ...]
                    stats_list = list(stats.values())
                    player_stats[game_id] = stats_list
                else:
                    # Handle case where it's already a list
                    player_stats[game_id] = stats

        return player_stats
    
    def _get_current_standings(self) -> Dict[int, Any]:
        """
        Get current standings from the standings store.
        
        Returns:
            Dictionary of team_id -> standing record
        """
        # Get all standings data
        return dict(self.store_manager.standings_store.data)
    
    def _save_to_database(self,
                         target_date: date,
                         games: Dict[str, Any],
                         player_stats: Dict[str, List],
                         standings: Dict[int, Any]) -> bool:
        """
        Save all data to database in a single transaction.
        
        Args:
            target_date: Date being persisted
            games: Game results to save
            player_stats: Player statistics to save
            standings: Current standings to update
            
        Returns:
            bool: True if all saves were successful
        """
        conn = self.db.get_connection()
        
        try:
            # Start transaction
            conn.execute("BEGIN TRANSACTION")
            
            # Save games
            for game_id, game_result in games.items():
                self._save_game(conn, game_id, game_result)
                self.total_games_persisted += 1
            
            # Save player stats
            for game_id, stats_list in player_stats.items():
                # Get the game result for context (to extract team IDs)
                game_result = games.get(game_id)

                if hasattr(stats_list, '__iter__'):
                    for player_stat in stats_list:
                        self._save_player_stat(conn, game_id, player_stat, game_result)
                        self.total_stats_persisted += 1
            
            # Update standings
            for team_id, standing in standings.items():
                self._update_standing(conn, team_id, standing)
            
            # Commit transaction
            conn.execute("COMMIT")
            
            self.logger.debug(f"Persisted {len(games)} games, "
                            f"{sum(len(s) if hasattr(s, '__len__') else 1 for s in player_stats.values())} stats, "
                            f"{len(standings)} standings for {target_date}")
            
            return True
            
        except Exception as e:
            # Rollback on any error
            conn.execute("ROLLBACK")
            self.logger.error(f"Database transaction failed: {e}")
            raise
            
        finally:
            conn.close()
    
    def _save_game(self, conn, game_id: str, game_result) -> None:
        """Save a single game to the database."""
        # Extract season and week from game_id if possible
        # Format expected: "2024_week1_HOME_AWAY"
        parts = game_id.split('_')
        season = int(parts[0]) if parts and parts[0].isdigit() else 2024
        week_str = parts[1] if len(parts) > 1 else "week1"
        week = int(week_str.replace('week', '')) if 'week' in week_str else 1
        
        query = """
            INSERT OR REPLACE INTO games (
                game_id, dynasty_id, season, week,
                home_team_id, away_team_id,
                home_score, away_score,
                total_plays, game_duration_minutes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        params = (
            game_id,
            self.dynasty_id,
            season,
            week,
            game_result.home_team_id,
            game_result.away_team_id,
            game_result.home_score,
            game_result.away_score,
            getattr(game_result, 'total_plays', 0),
            getattr(game_result, 'game_duration_minutes', 0)
        )
        
        conn.execute(query, params)
    
    def _save_player_stat(self, conn, game_id: str, player_stat, game_result=None) -> None:
        """Save a single player's game statistics to the database."""
        query = """
            INSERT INTO player_game_stats (
                dynasty_id, game_id, player_id, player_name,
                team_id, position,
                passing_yards, passing_tds, passing_completions, passing_attempts,
                rushing_yards, rushing_tds, rushing_attempts,
                receiving_yards, receiving_tds, receptions, targets,
                tackles_total, sacks, interceptions,
                field_goals_made, field_goals_attempted,
                extra_points_made, extra_points_attempted
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        # Handle different stat object structures gracefully
        # Note: PlayerStats uses different field names than expected

        # Handle team_id - if None, try to infer from game context
        team_id = getattr(player_stat, 'team_id', None)
        if team_id is None and game_result:
            # For now, default to home team (could be enhanced with player name matching)
            team_id = getattr(game_result, 'home_team_id', 0)
        elif team_id is None:
            team_id = 0

        params = (
            self.dynasty_id,
            game_id,
            getattr(player_stat, 'player_id', 'unknown'),
            getattr(player_stat, 'player_name', 'Unknown Player'),
            team_id,
            getattr(player_stat, 'position', 'UNK'),
            getattr(player_stat, 'passing_yards', 0),
            # Fix: PlayerStats uses 'passing_touchdowns' not 'passing_tds'
            getattr(player_stat, 'passing_touchdowns', getattr(player_stat, 'passing_tds', 0)),
            getattr(player_stat, 'passing_completions', 0),
            getattr(player_stat, 'passing_attempts', 0),
            getattr(player_stat, 'rushing_yards', 0),
            # Fix: PlayerStats uses 'rushing_touchdowns' not 'rushing_tds'
            getattr(player_stat, 'rushing_touchdowns', getattr(player_stat, 'rushing_tds', 0)),
            getattr(player_stat, 'rushing_attempts', 0),
            getattr(player_stat, 'receiving_yards', 0),
            # Fix: PlayerStats uses 'receiving_tds' field name
            getattr(player_stat, 'receiving_tds', 0),
            getattr(player_stat, 'receptions', 0),
            getattr(player_stat, 'targets', 0),
            getattr(player_stat, 'tackles', 0),
            getattr(player_stat, 'sacks', 0),
            getattr(player_stat, 'interceptions', 0),
            getattr(player_stat, 'field_goals_made', 0),
            getattr(player_stat, 'field_goal_attempts', 0),
            getattr(player_stat, 'extra_points_made', 0),
            getattr(player_stat, 'extra_points_attempted', 0)
        )
        
        conn.execute(query, params)
    
    def _update_standing(self, conn, team_id: int, standing) -> None:
        """Update team standings in the database."""
        # Get season from standing or default to current
        season = getattr(standing, 'season', 2024)
        
        query = """
            INSERT OR REPLACE INTO standings (
                dynasty_id, team_id, season,
                wins, losses, ties,
                division_wins, division_losses,
                conference_wins, conference_losses,
                points_for, points_against,
                last_updated
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """
        
        params = (
            self.dynasty_id,
            team_id,
            season,
            getattr(standing, 'wins', 0),
            getattr(standing, 'losses', 0),
            getattr(standing, 'ties', 0),
            getattr(standing, 'division_wins', 0),
            getattr(standing, 'division_losses', 0),
            getattr(standing, 'conference_wins', 0),
            getattr(standing, 'conference_losses', 0),
            getattr(standing, 'points_for', 0),
            getattr(standing, 'points_against', 0)
        )
        
        conn.execute(query, params)
    
    def _clear_stores_for_date(self, target_date: date) -> None:
        """
        Clear store data for the specified date after successful persistence.
        
        Args:
            target_date: Date to clear data for
        """
        # For now, we'll clear all game data
        # In a more sophisticated implementation, you'd only clear games from this date
        
        # Clear game results
        games_to_remove = []
        for game_id in self.store_manager.game_result_store.data.keys():
            # You might want to check if game is from target_date
            games_to_remove.append(game_id)
        
        for game_id in games_to_remove:
            # Remove from game result store (this properly updates indices)
            self.store_manager.game_result_store.remove(game_id)

            # Remove from player stats store
            if game_id in self.store_manager.player_stats_store.data:
                del self.store_manager.player_stats_store.data[game_id]
        
        # Note: We don't clear standings as they represent current state
        
        self.logger.debug(f"Cleared {len(games_to_remove)} games from stores")
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get persistence statistics.
        
        Returns:
            Dictionary of persistence metrics
        """
        return {
            'dynasty_id': self.dynasty_id,
            'total_days_persisted': self.total_days_persisted,
            'total_games_persisted': self.total_games_persisted,
            'total_stats_persisted': self.total_stats_persisted
        }