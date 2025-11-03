"""
Event-Level Persister

Handles immediate persistence of individual simulation events to database.
Ensures real-time updates for standings and game results during bulk simulations.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional

# Use GameResult from the preserved game simulation event
from game_management.game_simulation_event import GameResult
from team_management.players.player import Position


class EventLevelPersister:
    """
    Persists individual event results immediately to database.

    This replaces the problematic day-level batching that caused standings
    to not update during bulk simulations. Each event is committed immediately
    so standings are visible in real-time regardless of simulation mode.
    """

    def __init__(self, database_connection, dynasty_id: str):
        """
        Initialize the event-level persister.

        Args:
            database_connection: DatabaseConnection instance for immediate persistence
            dynasty_id: ID of the current dynasty being simulated
        """
        self.db = database_connection
        self.dynasty_id = dynasty_id
        self.logger = logging.getLogger(__name__)

        # Track persistence statistics
        self.total_events_persisted = 0
        self.total_games_persisted = 0
        self.total_admin_events_persisted = 0

    def persist_event(self, event_result: SimulationResult) -> bool:
        """
        Immediately persist a single event result to the database.

        This is the core method that ensures real-time database updates.
        Each event is committed immediately so data is visible right away.

        Args:
            event_result: SimulationResult from event.simulate()

        Returns:
            bool: True if persistence was successful, False otherwise
        """
        if not event_result.success:
            self.logger.debug(f"Skipping persistence for failed event: {event_result.event_name}")
            return True  # Not a persistence failure

        try:
            # Route to appropriate persistence method based on event type
            if event_result.event_type == EventType.GAME:
                success = self._persist_game_event(event_result)
                if success:
                    self.total_games_persisted += 1
            elif event_result.event_type == EventType.ADMINISTRATIVE:
                success = self._persist_administrative_event(event_result)
                if success:
                    self.total_admin_events_persisted += 1
            else:
                # Handle other event types as needed
                success = self._persist_generic_event(event_result)

            if success:
                self.total_events_persisted += 1
                self.logger.debug(f"Successfully persisted event: {event_result.event_name}")
            else:
                self.logger.error(f"Failed to persist event: {event_result.event_name}")

            return success

        except Exception as e:
            self.logger.error(f"Error persisting event {event_result.event_name}: {e}", exc_info=True)
            return False

    def _persist_game_event(self, event_result: SimulationResult) -> bool:
        """
        Persist a game event with immediate standings update.

        This is the critical method that fixes the bulk simulation standings issue.
        Game results and standings are committed immediately.

        Args:
            event_result: Game simulation result

        Returns:
            bool: True if persistence was successful
        """
        conn = self.db.get_connection()

        try:
            # Start transaction for this single event
            conn.execute("BEGIN TRANSACTION")

            # Extract game data from event result metadata
            game_data = self._extract_game_data(event_result)
            if not game_data:
                self.logger.warning(f"No game data found in event: {event_result.event_name}")
                conn.execute("ROLLBACK")
                return False

            # Save game result
            game_id = self._save_game_result(conn, game_data, event_result)

            # Save player statistics if available
            if 'player_stats' in event_result.metadata:
                self._save_player_statistics(conn, game_id, event_result.metadata['player_stats'])

            # Update team standings immediately
            self._update_team_standings(conn, game_data)

            # CRITICAL: Immediate commit for real-time visibility
            conn.execute("COMMIT")

            self.logger.info(f"Game persisted with immediate commit: {event_result.event_name}")
            return True

        except Exception as e:
            # Rollback on any error
            conn.execute("ROLLBACK")
            self.logger.error(f"Game persistence transaction failed: {e}")
            raise

        finally:
            conn.close()

    def _extract_game_data(self, event_result: SimulationResult) -> Optional[Dict[str, Any]]:
        """
        Extract game data from event result metadata.

        Args:
            event_result: Game simulation result

        Returns:
            Dictionary with game data or None if not found
        """
        if not event_result.metadata:
            return None

        # Extract key game information
        game_data = {}

        # Required fields
        required_fields = ['away_team_id', 'home_team_id', 'away_score', 'home_score']
        for field in required_fields:
            if field not in event_result.metadata:
                self.logger.warning(f"Missing required game field: {field}")
                return None
            game_data[field] = event_result.metadata[field]

        # Optional fields
        optional_fields = ['winning_team_id', 'season_type', 'week', 'overtime', 'final_score']
        for field in optional_fields:
            if field in event_result.metadata:
                game_data[field] = event_result.metadata[field]

        # Add event context
        game_data['game_date'] = event_result.date
        game_data['dynasty_id'] = self.dynasty_id

        return game_data

    def _save_game_result(self, conn, game_data: Dict[str, Any], event_result: SimulationResult) -> str:
        """
        Save game result to database.

        Args:
            conn: Database connection
            game_data: Extracted game data
            event_result: Full event result

        Returns:
            str: Generated game_id
        """
        # Generate game ID
        game_id = f"{self.dynasty_id}_{game_data['game_date'].strftime('%Y%m%d')}_{game_data['away_team_id']}_{game_data['home_team_id']}"

        # Insert game result - use 'games' table to match database schema
        conn.execute("""
            INSERT OR REPLACE INTO games (
                game_id, dynasty_id, season, week, game_type,
                away_team_id, home_team_id, away_score, home_score,
                total_plays, game_duration_minutes, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            game_id,
            self.dynasty_id,
            2024,  # TODO: Extract from dynasty context
            game_data.get('week', 0),
            game_data.get('season_type', 'regular'),
            game_data['away_team_id'],
            game_data['home_team_id'],
            game_data['away_score'],
            game_data['home_score'],
            0,  # total_plays - not available in event metadata
            int(game_data.get('duration_hours', 3) * 60),  # convert hours to minutes
            datetime.now().isoformat()
        ))

        return game_id

    def _save_player_statistics(self, conn, game_id: str, player_stats: Dict[str, Any]):
        """
        Save player statistics to database.

        Args:
            conn: Database connection
            game_id: Game identifier
            player_stats: Player statistics data (dict of player_id -> stats)
        """
        self.logger.debug(f"Saving player stats for game {game_id}")

        if not player_stats:
            self.logger.debug("No player stats to save")
            return

        # Iterate through each player's stats
        for player_key, player_stat in player_stats.items():
            try:
                self._save_single_player_stat(conn, game_id, player_stat)
            except Exception as e:
                self.logger.error(f"Error saving stats for player {player_key}: {e}")

    def _save_single_player_stat(self, conn, game_id: str, player_stat):
        """
        Save a single player's game statistics to the database.

        Args:
            conn: Database connection
            game_id: Game identifier
            player_stat: PlayerGameStats object with game statistics
        """
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

        # Handle PlayerGameStats objects with attribute access
        # Convert short position names to full names for database consistency
        position = self._convert_position_name(getattr(player_stat, 'position', 'UNK'))

        params = (
            self.dynasty_id,
            game_id,
            getattr(player_stat, 'player_id', 'unknown'),
            getattr(player_stat, 'player_name', 'Unknown Player'),
            getattr(player_stat, 'team_id', 0),
            position,
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
            getattr(player_stat, 'extra_points_attempted', 0)
        )

        conn.execute(query, params)
        self.logger.debug(f"Saved stats for player {getattr(player_stat, 'player_name', 'Unknown')}")

    def _convert_position_name(self, position: str) -> str:
        """
        Convert short position names to full position names for database consistency.
        Uses the Position class to maintain consistency with the rest of the codebase.

        Args:
            position: Short position name (e.g., 'QB', 'RB') or full name

        Returns:
            str: Full position name (e.g., 'quarterback', 'running_back')
        """
        # Create reverse mapping from Position class constants
        position_map = {
            'QB': Position.QB,
            'RB': Position.RB,
            'FB': Position.FB,
            'WR': Position.WR,
            'TE': Position.TE,
            'LT': Position.LT,
            'LG': Position.LG,
            'C': Position.C,
            'RG': Position.RG,
            'RT': Position.RT,
            'DE': Position.DE,
            'DT': Position.DT,
            'NT': Position.NT,
            'LEO': Position.LEO,
            'MIKE': Position.MIKE,
            'SAM': Position.SAM,
            'WILL': Position.WILL,
            'ILB': Position.ILB,
            'OLB': Position.OLB,
            'CB': Position.CB,
            'NCB': Position.NCB,
            'FS': Position.FS,
            'SS': Position.SS,
            'K': Position.K,
            'P': Position.P,
            'LS': Position.LS,
            'H': Position.H,
            'KR': Position.KR,
            'PR': Position.PR
        }

        # Return mapped position or original if no mapping found
        # This handles both short names (QB) and already-converted full names
        return position_map.get(position, position)

    def _update_team_standings(self, conn, game_data: Dict[str, Any]):
        """
        Update team standings based on game result.

        This is the critical method that ensures standings update immediately
        after each game, fixing the bulk simulation visibility issue.

        Args:
            conn: Database connection
            game_data: Game result data (must include season_type for proper isolation)
        """
        away_team_id = game_data['away_team_id']
        home_team_id = game_data['home_team_id']
        away_score = game_data['away_score']
        home_score = game_data['home_score']
        winning_team_id = game_data.get('winning_team_id')
        season_type = game_data.get('season_type', 'regular_season')

        # Determine win/loss/tie
        if away_score > home_score:
            # Away team wins
            self._update_team_record(conn, away_team_id, wins=1, season_type=season_type)
            self._update_team_record(conn, home_team_id, losses=1, season_type=season_type)
        elif home_score > away_score:
            # Home team wins
            self._update_team_record(conn, home_team_id, wins=1, season_type=season_type)
            self._update_team_record(conn, away_team_id, losses=1, season_type=season_type)
        else:
            # Tie game
            self._update_team_record(conn, away_team_id, ties=1, season_type=season_type)
            self._update_team_record(conn, home_team_id, ties=1, season_type=season_type)

        # Update points for/against
        self._update_team_points(conn, away_team_id, points_for=away_score, points_against=home_score, season_type=season_type)
        self._update_team_points(conn, home_team_id, points_for=home_score, points_against=away_score, season_type=season_type)

        self.logger.debug(f"Updated standings for teams {away_team_id} and {home_team_id} (season_type={season_type})")

    def _update_team_record(self, conn, team_id: int, wins: int = 0, losses: int = 0, ties: int = 0, season_type: str = "regular_season"):
        """
        Update team win/loss/tie record for a specific season type.

        Args:
            conn: Database connection
            team_id: Team identifier
            wins: Number of wins to add
            losses: Number of losses to add
            ties: Number of ties to add
            season_type: "preseason", "regular_season", or "playoffs" (default: "regular_season")
        """
        conn.execute("""
            INSERT OR IGNORE INTO standings (dynasty_id, team_id, season, season_type, wins, losses, ties, points_for, points_against)
            VALUES (?, ?, ?, ?, 0, 0, 0, 0, 0)
        """, (self.dynasty_id, team_id, 2024, season_type))

        conn.execute("""
            UPDATE standings
            SET wins = wins + ?, losses = losses + ?, ties = ties + ?
            WHERE dynasty_id = ? AND team_id = ? AND season = ? AND season_type = ?
        """, (wins, losses, ties, self.dynasty_id, team_id, 2024, season_type))

    def _update_team_points(self, conn, team_id: int, points_for: int = 0, points_against: int = 0, season_type: str = "regular_season"):
        """
        Update team points for/against for a specific season type.

        Args:
            conn: Database connection
            team_id: Team identifier
            points_for: Points scored by this team
            points_against: Points scored against this team
            season_type: "preseason", "regular_season", or "playoffs" (default: "regular_season")
        """
        conn.execute("""
            UPDATE standings
            SET points_for = points_for + ?, points_against = points_against + ?
            WHERE dynasty_id = ? AND team_id = ? AND season = ? AND season_type = ?
        """, (points_for, points_against, self.dynasty_id, team_id, 2024, season_type))

    def _persist_administrative_event(self, event_result: SimulationResult) -> bool:
        """
        Persist administrative events (playoff seeding, etc.).

        Args:
            event_result: Administrative event result

        Returns:
            bool: True if persistence was successful
        """
        # Administrative events might not need immediate persistence
        # but we can log them for completeness
        self.logger.info(f"Administrative event completed: {event_result.event_name}")

        # Could save to admin_events table if needed
        return True

    def _persist_generic_event(self, event_result: SimulationResult) -> bool:
        """
        Persist other types of events.

        Args:
            event_result: Generic event result

        Returns:
            bool: True if persistence was successful
        """
        self.logger.debug(f"Generic event completed: {event_result.event_name}")
        return True

    def get_statistics(self) -> Dict[str, int]:
        """
        Get persistence statistics.

        Returns:
            Dictionary with persistence statistics
        """
        return {
            'total_events_persisted': self.total_events_persisted,
            'total_games_persisted': self.total_games_persisted,
            'total_admin_events_persisted': self.total_admin_events_persisted
        }