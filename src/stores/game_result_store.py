"""
Game Result Store

Specialized store for GameResult entities with team and week-based indexing.
"""

from typing import Dict, List, Optional, Any, Set
from datetime import datetime
from collections import defaultdict

from .base_store import BaseStore
from shared.game_result import GameResult
# Game result types removed with simulation system - will need to be recreated if needed
# from simulation.results.game_result import PlayerGameStats, TeamGameStats

try:
    from database.connection import DatabaseConnection
except ImportError:
    DatabaseConnection = None


class GameResultStore(BaseStore[GameResult]):
    """
    Store for game results with rich querying capabilities.

    Provides indexed access by team, week, and date for efficient retrieval
    of game results during processing and analysis.
    """

    def __init__(self, database_path: str = "data/database/nfl_simulation.db"):
        """Initialize game result store with indices."""
        super().__init__("game_results")

        # Database connection for persistence
        self.db_connection = DatabaseConnection(database_path) if DatabaseConnection else None
        self.dynasty_id: Optional[str] = None
        self.current_season: Optional[int] = None

        # Indices for efficient querying
        self.by_team: Dict[int, List[str]] = defaultdict(list)  # team_id -> [game_ids]
        self.by_week: Dict[int, List[str]] = defaultdict(list)  # week -> [game_ids]
        self.by_date: Dict[str, List[str]] = defaultdict(list)  # date_str -> [game_ids]
        self.by_matchup: Dict[str, str] = {}  # "team1_team2_week" -> game_id

    def set_dynasty_context(self, dynasty_id: str, season: int) -> None:
        """
        Set dynasty and season context for database persistence.
        
        Args:
            dynasty_id: Dynasty identifier
            season: Season year
        """
        self.dynasty_id = dynasty_id
        self.current_season = season

    def add(self, key: str, item: GameResult) -> None:
        """
        Add a game result to the store.

        Args:
            key: Unique game identifier (e.g., "2024_week1_DAL_NYG")
            item: GameResult object
        """
        if self.is_locked():
            self.logger.warning(f"Cannot add to locked store {self.store_name}")
            return

        # Store the result
        self.data[key] = item

        # Update indices
        self._index_game(key, item)

        # Immediate database persistence
        self._persist_to_database(key, item)

        # Update metadata
        self._update_metadata()
        self._log_transaction('add', key, True, {
            'home_team': item.home_team_id,
            'away_team': item.away_team_id,
            'week': item.week
        })

        self.logger.info(f"Added game result: {key}")

    def get(self, key: str) -> Optional[GameResult]:
        """
        Get a game result by its unique identifier.

        Args:
            key: Unique game identifier

        Returns:
            GameResult if found, None otherwise
        """
        return self.data.get(key)

    def get_all(self) -> Dict[str, GameResult]:
        """
        Get all game results.

        Returns:
            Dictionary of all game results
        """
        return self.data.copy()

    def remove(self, key: str) -> bool:
        """
        Remove a game result from the store and update all indices.

        Args:
            key: Unique game identifier to remove

        Returns:
            True if the game was removed, False if it didn't exist
        """
        if self.is_locked():
            self.logger.warning(f"Cannot remove from locked store {self.store_name}")
            return False

        if key not in self.data:
            return False

        # Get the game result before removing it
        result = self.data[key]

        # Remove from main data
        del self.data[key]

        # Remove from indices
        self._remove_from_indices(key, result)

        # Update metadata
        self._update_metadata()
        self._log_transaction('remove', key, True, {
            'home_team': result.home_team.team_id,
            'away_team': result.away_team.team_id,
            'week': result.week
        })

        self.logger.info(f"Removed game result: {key}")
        return True

    def clear(self) -> None:
        """Clear all game results and indices."""
        if self.is_locked():
            self.logger.warning(f"Cannot clear locked store {self.store_name}")
            return

        self.data.clear()
        self.by_team.clear()
        self.by_week.clear()
        self.by_date.clear()
        self.by_matchup.clear()

        self.metadata.last_cleared = datetime.now()
        self._update_metadata()
        self._log_transaction('clear', None, True)

        self.logger.info("Cleared all game results")

    def validate(self) -> bool:
        """
        Validate game result data consistency.

        Returns:
            True if all data is valid, False otherwise
        """
        try:
            # Check that all indexed games exist in main data
            all_indexed_ids = set()

            for game_ids in self.by_team.values():
                all_indexed_ids.update(game_ids)

            for game_ids in self.by_week.values():
                all_indexed_ids.update(game_ids)

            if all_indexed_ids != set(self.data.keys()):
                self.logger.error("Index mismatch with stored data")
                return False

            # Validate each game result
            for game_id, result in self.data.items():
                if not self._validate_game_result(result):
                    self.logger.error(f"Invalid game result: {game_id}")
                    return False

            return True

        except Exception as e:
            self.logger.error(f"Validation error: {e}")
            return False

    # REMOVED: get_by_team(), get_by_week(), get_by_date() methods
    # Use DatabaseAPI.get_game_results() instead for all retrieval operations

    # REMOVED: get_latest_results() method - use DatabaseAPI instead
    
    def _get_latest_results_removed(self, limit: int = 10) -> List[GameResult]:
        """
        Get the most recent game results.

        Args:
            limit: Maximum number of results to return

        Returns:
            List of most recent game results
        """
        # Sort by date and return latest
        sorted_results = sorted(
            self.data.values(),
            key=lambda r: r.date,
            reverse=True
        )
        return sorted_results[:limit]

    def get_team_record(self, team_id: int) -> Dict[str, int]:
        """
        Calculate a team's win-loss record from stored games.

        Args:
            team_id: Team identifier

        Returns:
            Dictionary with wins, losses, ties
        """
        record = {'wins': 0, 'losses': 0, 'ties': 0}

        for result in self.get_by_team(team_id):
            if result.home_score > result.away_score:
                # Home team won
                if result.home_team.team_id == team_id:
                    record['wins'] += 1
                else:
                    record['losses'] += 1
            elif result.away_score > result.home_score:
                # Away team won
                if result.away_team.team_id == team_id:
                    record['wins'] += 1
                else:
                    record['losses'] += 1
            else:
                # Tie
                record['ties'] += 1

        return record

    def get_head_to_head(self, team1_id: int, team2_id: int) -> List[GameResult]:
        """
        Get all games between two specific teams.

        Args:
            team1_id: First team identifier
            team2_id: Second team identifier

        Returns:
            List of game results between the two teams
        """
        team1_games = set(self.by_team.get(team1_id, []))
        team2_games = set(self.by_team.get(team2_id, []))
        common_games = team1_games.intersection(team2_games)

        return [self.data[gid] for gid in common_games if gid in self.data]

    def get_player_stats_from_games(self, player_name: str) -> List[Any]:
        """
        Extract all stats for a specific player across all games.

        Args:
            player_name: Name of the player

        Returns:
            List of player's game statistics
        """
        player_stats = []

        for result in self.data.values():
            for stats in result.player_stats:
                if stats.player_name == player_name:
                    player_stats.append(stats)

        return player_stats

    def _index_game(self, game_id: str, result: GameResult) -> None:
        """
        Update indices for a game result.

        Args:
            game_id: Unique game identifier
            result: GameResult to index
        """
        # Index by teams
        self.by_team[result.home_team.team_id].append(game_id)
        self.by_team[result.away_team.team_id].append(game_id)

        # Index by week
        self.by_week[result.week].append(game_id)

        # Index by date
        date_str = result.date.date().isoformat()
        self.by_date[date_str].append(game_id)

        # Index by matchup
        teams = sorted([result.home_team.team_id, result.away_team.team_id])
        matchup_key = f"{teams[0]}_{teams[1]}_week{result.week}"
        self.by_matchup[matchup_key] = game_id

    def _remove_from_indices(self, game_id: str, result: GameResult) -> None:
        """
        Remove a game from all indices.

        Args:
            game_id: Unique game identifier to remove
            result: GameResult being removed
        """
        # Remove from team indices
        if result.home_team.team_id in self.by_team:
            if game_id in self.by_team[result.home_team.team_id]:
                self.by_team[result.home_team.team_id].remove(game_id)

        if result.away_team.team_id in self.by_team:
            if game_id in self.by_team[result.away_team.team_id]:
                self.by_team[result.away_team.team_id].remove(game_id)

        # Remove from week index
        if result.week in self.by_week:
            if game_id in self.by_week[result.week]:
                self.by_week[result.week].remove(game_id)

        # Remove from date index
        date_str = result.date.date().isoformat()
        if date_str in self.by_date:
            if game_id in self.by_date[date_str]:
                self.by_date[date_str].remove(game_id)

        # Remove from matchup index
        teams = sorted([result.home_team.team_id, result.away_team.team_id])
        matchup_key = f"{teams[0]}_{teams[1]}_week{result.week}"
        if matchup_key in self.by_matchup and self.by_matchup[matchup_key] == game_id:
            del self.by_matchup[matchup_key]

    def _validate_game_result(self, result: GameResult) -> bool:
        """
        Validate a single game result.

        Args:
            result: GameResult to validate

        Returns:
            True if valid, False otherwise
        """
        # Basic validation rules
        if result.home_team.team_id == result.away_team.team_id:
            return False

        if result.home_score < 0 or result.away_score < 0:
            return False

        if result.total_plays < 0:
            return False

        if result.week < 0 or result.week > 22:  # Preseason through Super Bowl
            return False

        return True

    def _serialize_data(self) -> Dict[str, Any]:
        """
        Serialize game results for persistence.

        Returns:
            Serializable dictionary of game results
        """
        serialized = {}

        for game_id, result in self.data.items():
            serialized[game_id] = {
                'home_team_id': result.home_team.team_id,
                'away_team_id': result.away_team.team_id,
                'home_score': result.home_score,
                'away_score': result.away_score,
                'week': result.week,
                'season_type': result.season_type,
                'date': result.date.isoformat(),
                'total_plays': result.total_plays,
                'total_drives': result.total_drives,
                'game_duration_minutes': result.game_duration_minutes,
                'overtime_periods': result.overtime_periods,
                'weather_conditions': result.weather_conditions,
                # Add more fields as needed for persistence
            }

        return serialized

    def get_week_summary(self, week: int) -> Dict[str, Any]:
        """
        Get a summary of all games in a specific week.

        Args:
            week: Week number

        Returns:
            Summary statistics for the week
        """
        week_games = self.get_by_week(week)

        if not week_games:
            return {'week': week, 'games_played': 0}

        total_points = 0
        total_plays = 0
        upsets = 0  # Games where lower-ranked team won (would need rankings)
        overtime_games = 0
        blowouts = 0  # Games decided by 20+ points

        for game in week_games:
            total_points += game.home_score + game.away_score
            total_plays += game.total_plays

            if game.overtime_periods > 0:
                overtime_games += 1

            score_diff = abs(game.home_score - game.away_score)
            if score_diff >= 20:
                blowouts += 1

        return {
            'week': week,
            'games_played': len(week_games),
            'total_points': total_points,
            'avg_points_per_game': total_points / len(week_games) if week_games else 0,
            'total_plays': total_plays,
            'avg_plays_per_game': total_plays / len(week_games) if week_games else 0,
            'overtime_games': overtime_games,
            'blowouts': blowouts
        }

    def _persist_to_database(self, game_id: str, result: GameResult) -> None:
        """
        Persist game result to database immediately.
        
        Args:
            game_id: Game identifier
            result: Game result data
        """
        if not self.db_connection or not self.dynasty_id or not self.current_season:
            self.logger.warning("Database persistence not available - missing connection or context")
            return
        
        try:
            # Convert game date to milliseconds timestamp for database
            game_date_ms = None
            if result.date:
                if hasattr(result.date, 'timestamp'):
                    # datetime object
                    game_date_ms = int(result.date.timestamp() * 1000)
                elif hasattr(result.date, 'to_python_date'):
                    # Date object with to_python_date method
                    from datetime import datetime
                    py_date = result.date.to_python_date()
                    game_date_ms = int(datetime.combine(py_date, datetime.min.time()).timestamp() * 1000)

            query = '''
                INSERT OR REPLACE INTO games (
                    game_id, dynasty_id, season, week, game_type,
                    home_team_id, away_team_id, home_score, away_score,
                    total_plays, total_yards_home, total_yards_away,
                    turnovers_home, turnovers_away,
                    time_of_possession_home, time_of_possession_away,
                    game_duration_minutes, overtime_periods,
                    game_date, weather_conditions, attendance, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            '''

            params = (
                game_id, self.dynasty_id, self.current_season, result.week,
                result.season_type, result.home_team.team_id, result.away_team.team_id,
                result.home_score, result.away_score, result.total_plays,
                getattr(result.home_team_stats, 'total_yards', 0) if result.home_team_stats else 0,
                getattr(result.away_team_stats, 'total_yards', 0) if result.away_team_stats else 0,
                getattr(result.home_team_stats, 'turnovers', 0) if result.home_team_stats else 0,
                getattr(result.away_team_stats, 'turnovers', 0) if result.away_team_stats else 0,
                getattr(result.home_team_stats, 'time_of_possession', 0) if result.home_team_stats else 0,
                getattr(result.away_team_stats, 'time_of_possession', 0) if result.away_team_stats else 0,
                result.game_duration_minutes, result.overtime_periods,
                game_date_ms, result.weather_conditions, 0  # attendance - placeholder
            )
            
            self.db_connection.execute_update(query, params)
            self.logger.debug(f"Persisted game result: {game_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to persist game result {game_id}: {e}")