"""
Database Demo Persister

Concrete implementation of DemoPersister using SQLite database.
Reuses existing database connection and schema from main codebase.
"""

import time
from datetime import datetime
from typing import List, Dict, Any, Optional

from .base_demo_persister import DemoPersister
from .persistence_result import PersistenceResult, PersistenceStatus

try:
    from database.connection import DatabaseConnection
except ImportError:
    from ...database.connection import DatabaseConnection


class DatabaseDemoPersister(DemoPersister):
    """
    Database persistence strategy for demo applications.

    Uses SQLite with transaction support for atomic operations.
    Reuses existing database schema and connection infrastructure.
    """

    def __init__(self, database_path: str, logger: Optional[Any] = None):
        """
        Initialize database persister.

        Args:
            database_path: Path to SQLite database file
            logger: Optional logger
        """
        super().__init__(logger)
        self.database_path = database_path
        self.db_connection = DatabaseConnection(database_path)
        self._connection = None
        self._transaction_active = False

        # Statistics tracking
        self.total_games_persisted = 0
        self.total_player_stats_persisted = 0
        self.total_standings_updates = 0

        # Ensure schema exists (DatabaseConnection auto-creates tables in __init__)
        # This just verifies the connection is established and tables are ready
        try:
            conn = self.db_connection.get_connection()
            conn.close()
        except Exception as e:
            self.logger.error(f"Failed to verify database schema: {e}")
            raise

        self.logger.info(f"DatabaseDemoPersister initialized: {database_path}")

    def persist_game_result(
        self,
        game_id: str,
        game_data: Dict[str, Any],
        dynasty_id: str = "default"
    ) -> PersistenceResult:
        """
        Persist game result to database.

        Args:
            game_id: Unique game identifier
            game_data: Game result data
            dynasty_id: Dynasty context

        Returns:
            PersistenceResult with operation outcome
        """
        start_time = time.time()
        result = PersistenceResult(
            status=PersistenceStatus.SUCCESS,
            transaction_id=f"game_{game_id}"
        )

        # Validate game data
        validation_errors = self.validate_game_data(game_data)
        if validation_errors:
            result.status = PersistenceStatus.FAILURE
            for error in validation_errors:
                result.add_error(error)
            return result

        try:
            conn = self._get_connection()

            # Insert game record
            query = """
                INSERT OR REPLACE INTO games (
                    game_id, dynasty_id, season, week, game_type,
                    away_team_id, home_team_id, away_score, home_score,
                    total_plays, game_duration_minutes, overtime_periods, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """

            params = (
                game_id,
                dynasty_id,
                game_data.get('season', 2024),
                game_data.get('week', 0),
                game_data.get('season_type', 'regular_season'),
                game_data['away_team_id'],
                game_data['home_team_id'],
                game_data['away_score'],
                game_data['home_score'],
                game_data.get('total_plays', 0),
                game_data.get('game_duration_minutes', 180),
                game_data.get('overtime_periods', 0),
                datetime.now().isoformat()
            )

            conn.execute(query, params)
            result.records_persisted = 1
            self.total_games_persisted += 1

            self.logger.debug(f"Persisted game result: {game_id}")

        except Exception as e:
            result.status = PersistenceStatus.FAILURE
            result.add_error(f"Database error persisting game: {str(e)}")
            self.logger.error(f"Error persisting game {game_id}: {e}", exc_info=True)

        finally:
            result.processing_time_ms = (time.time() - start_time) * 1000
            if not self._transaction_active:
                self._close_connection()

        return result

    def persist_player_stats(
        self,
        game_id: str,
        player_stats: List[Any],
        dynasty_id: str = "default"
    ) -> PersistenceResult:
        """
        Persist player statistics to database.

        Args:
            game_id: Game identifier
            player_stats: List of player statistics
            dynasty_id: Dynasty context

        Returns:
            PersistenceResult with operation outcome
        """
        start_time = time.time()
        result = PersistenceResult(
            status=PersistenceStatus.SUCCESS,
            transaction_id=f"player_stats_{game_id}"
        )

        if not player_stats:
            result.add_warning("No player stats to persist")
            return result

        try:
            conn = self._get_connection()

            query = """
                INSERT INTO player_game_stats (
                    dynasty_id, game_id, player_id, player_name,
                    team_id, position,
                    passing_yards, passing_tds, passing_completions, passing_attempts,
                    rushing_yards, rushing_tds, rushing_attempts,
                    receiving_yards, receiving_tds, receptions, targets,
                    tackles_total, sacks, interceptions,
                    field_goals_made, field_goals_attempted,
                    extra_points_made, extra_points_attempted,
                    offensive_snaps, defensive_snaps, total_snaps
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """

            persisted_count = 0
            failed_count = 0

            for player_stat in player_stats:
                try:
                    params = (
                        dynasty_id,
                        game_id,
                        getattr(player_stat, 'player_id', 'unknown'),
                        getattr(player_stat, 'player_name', 'Unknown Player'),
                        getattr(player_stat, 'team_id', 0),
                        getattr(player_stat, 'position', 'UNK'),
                        getattr(player_stat, 'passing_yards', 0),
                        getattr(player_stat, 'passing_tds', 0),
                        getattr(player_stat, 'passing_completions', 0),
                        getattr(player_stat, 'passing_attempts', 0),
                        getattr(player_stat, 'rushing_yards', 0),
                        getattr(player_stat, 'rushing_tds', 0),
                        getattr(player_stat, 'rushing_attempts', 0),
                        getattr(player_stat, 'receiving_yards', 0),
                        getattr(player_stat, 'receiving_tds', 0),
                        getattr(player_stat, 'receptions', 0),
                        getattr(player_stat, 'targets', 0),
                        getattr(player_stat, 'tackles', 0),
                        getattr(player_stat, 'sacks', 0),
                        getattr(player_stat, 'interceptions', 0),
                        getattr(player_stat, 'field_goals_made', 0),
                        getattr(player_stat, 'field_goals_attempted', 0),
                        getattr(player_stat, 'extra_points_made', 0),
                        getattr(player_stat, 'extra_points_attempted', 0),
                        getattr(player_stat, 'offensive_snaps', 0),
                        getattr(player_stat, 'defensive_snaps', 0),
                        getattr(player_stat, 'total_snaps', 0)
                    )

                    conn.execute(query, params)
                    persisted_count += 1

                except Exception as e:
                    failed_count += 1
                    result.add_error(f"Failed to persist player {getattr(player_stat, 'player_name', 'unknown')}: {str(e)}")

            result.records_persisted = persisted_count
            result.records_failed = failed_count
            self.total_player_stats_persisted += persisted_count

            if failed_count > 0:
                result.status = PersistenceStatus.PARTIAL_SUCCESS

            self.logger.debug(f"Persisted {persisted_count} player stats for game {game_id}")

        except Exception as e:
            result.status = PersistenceStatus.FAILURE
            result.add_error(f"Database error persisting player stats: {str(e)}")
            self.logger.error(f"Error persisting player stats for {game_id}: {e}", exc_info=True)

        finally:
            result.processing_time_ms = (time.time() - start_time) * 1000
            if not self._transaction_active:
                self._close_connection()

        return result

    def persist_team_stats(
        self,
        game_id: str,
        home_stats: Dict[str, Any],
        away_stats: Dict[str, Any],
        dynasty_id: str = "default"
    ) -> PersistenceResult:
        """
        Persist team statistics to database.

        Note: Current schema doesn't have dedicated team_stats table.
        This is a placeholder for future team-level statistics.

        Args:
            game_id: Game identifier
            home_stats: Home team statistics
            away_stats: Away team statistics
            dynasty_id: Dynasty context

        Returns:
            PersistenceResult with operation outcome
        """
        start_time = time.time()
        result = PersistenceResult(
            status=PersistenceStatus.SUCCESS,
            transaction_id=f"team_stats_{game_id}"
        )

        # Currently we don't have a team_stats table
        # Team statistics are aggregated from player stats
        result.add_warning("Team stats persistence not implemented (aggregate from player stats)")
        result.add_metadata("home_stats", home_stats)
        result.add_metadata("away_stats", away_stats)

        result.processing_time_ms = (time.time() - start_time) * 1000
        return result

    def update_standings(
        self,
        home_team_id: int,
        away_team_id: int,
        home_score: int,
        away_score: int,
        dynasty_id: str = "default",
        season: int = 2024
    ) -> PersistenceResult:
        """
        Update team standings based on game result.

        Args:
            home_team_id: Home team identifier
            away_team_id: Away team identifier
            home_score: Home team score
            away_score: Away team score
            dynasty_id: Dynasty context
            season: Season year

        Returns:
            PersistenceResult with operation outcome
        """
        start_time = time.time()
        result = PersistenceResult(
            status=PersistenceStatus.SUCCESS,
            transaction_id=f"standings_{home_team_id}_{away_team_id}"
        )

        try:
            conn = self._get_connection()

            # Ensure both teams have standings records
            for team_id in [home_team_id, away_team_id]:
                conn.execute("""
                    INSERT OR IGNORE INTO standings (
                        dynasty_id, team_id, season, wins, losses, ties,
                        points_for, points_against, division_wins, division_losses,
                        conference_wins, conference_losses, home_wins, home_losses,
                        away_wins, away_losses
                    ) VALUES (?, ?, ?, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
                """, (dynasty_id, team_id, season))

            # Determine winner and update records
            if home_score > away_score:
                # Home team wins
                self._update_team_record(conn, home_team_id, dynasty_id, season, wins=1, home_wins=1)
                self._update_team_record(conn, away_team_id, dynasty_id, season, losses=1, away_losses=1)
            elif away_score > home_score:
                # Away team wins
                self._update_team_record(conn, away_team_id, dynasty_id, season, wins=1, away_wins=1)
                self._update_team_record(conn, home_team_id, dynasty_id, season, losses=1, home_losses=1)
            else:
                # Tie
                self._update_team_record(conn, home_team_id, dynasty_id, season, ties=1)
                self._update_team_record(conn, away_team_id, dynasty_id, season, ties=1)

            # Update points for/against
            self._update_team_points(conn, home_team_id, dynasty_id, season, home_score, away_score)
            self._update_team_points(conn, away_team_id, dynasty_id, season, away_score, home_score)

            result.records_persisted = 2  # Both teams updated
            self.total_standings_updates += 2

            self.logger.debug(f"Updated standings for teams {home_team_id} and {away_team_id}")

        except Exception as e:
            result.status = PersistenceStatus.FAILURE
            result.add_error(f"Database error updating standings: {str(e)}")
            self.logger.error(f"Error updating standings: {e}", exc_info=True)

        finally:
            result.processing_time_ms = (time.time() - start_time) * 1000
            if not self._transaction_active:
                self._close_connection()

        return result

    def begin_transaction(self) -> bool:
        """Begin a database transaction"""
        try:
            if self._transaction_active:
                self.logger.warning("Transaction already active")
                return False

            self._connection = self.db_connection.get_connection()
            self._connection.execute("BEGIN TRANSACTION")
            self._transaction_active = True
            self.logger.debug("Transaction started")
            return True

        except Exception as e:
            self.logger.error(f"Error starting transaction: {e}")
            return False

    def commit_transaction(self) -> bool:
        """Commit the current transaction"""
        try:
            if not self._transaction_active:
                self.logger.warning("No active transaction to commit")
                return False

            self._connection.execute("COMMIT")
            self._transaction_active = False
            self.logger.debug("Transaction committed")
            self._close_connection()
            return True

        except Exception as e:
            self.logger.error(f"Error committing transaction: {e}")
            self.rollback_transaction()
            return False

    def rollback_transaction(self) -> bool:
        """Rollback the current transaction"""
        try:
            if not self._transaction_active:
                self.logger.warning("No active transaction to rollback")
                return False

            self._connection.execute("ROLLBACK")
            self._transaction_active = False
            self.logger.info("Transaction rolled back")
            self._close_connection()
            return True

        except Exception as e:
            self.logger.error(f"Error rolling back transaction: {e}")
            return False

    def get_statistics(self) -> Dict[str, Any]:
        """Get persistence statistics"""
        return {
            'total_games_persisted': self.total_games_persisted,
            'total_player_stats_persisted': self.total_player_stats_persisted,
            'total_standings_updates': self.total_standings_updates,
            'database_path': self.database_path,
            'transaction_active': self._transaction_active
        }

    def _get_connection(self):
        """Get database connection (reuse if transaction active)"""
        if self._transaction_active and self._connection:
            return self._connection
        return self.db_connection.get_connection()

    def _close_connection(self):
        """Close database connection if not in transaction"""
        if not self._transaction_active and self._connection:
            try:
                self._connection.close()
                self._connection = None
            except:
                pass

    def _update_team_record(
        self,
        conn,
        team_id: int,
        dynasty_id: str,
        season: int,
        wins: int = 0,
        losses: int = 0,
        ties: int = 0,
        home_wins: int = 0,
        home_losses: int = 0,
        away_wins: int = 0,
        away_losses: int = 0
    ):
        """Update team win/loss record"""
        conn.execute("""
            UPDATE standings
            SET wins = wins + ?,
                losses = losses + ?,
                ties = ties + ?,
                home_wins = home_wins + ?,
                home_losses = home_losses + ?,
                away_wins = away_wins + ?,
                away_losses = away_losses + ?
            WHERE dynasty_id = ? AND team_id = ? AND season = ?
        """, (wins, losses, ties, home_wins, home_losses, away_wins, away_losses,
              dynasty_id, team_id, season))

    def _update_team_points(
        self,
        conn,
        team_id: int,
        dynasty_id: str,
        season: int,
        points_for: int,
        points_against: int
    ):
        """Update team points for/against"""
        conn.execute("""
            UPDATE standings
            SET points_for = points_for + ?,
                points_against = points_against + ?
            WHERE dynasty_id = ? AND team_id = ? AND season = ?
        """, (points_for, points_against, dynasty_id, team_id, season))

    def __str__(self) -> str:
        """String representation"""
        return f"DatabaseDemoPersister(db='{self.database_path}')"
