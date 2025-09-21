"""
Player Statistics Extractor

Extracts comprehensive player statistics from game results including
comprehensive offensive line statistics, traditional stats, and performance metrics.
"""

from typing import List, Dict, Any
import logging

from .base_extractor import BaseExtractor
from ..models.extraction_context import ExtractionContext, PlayerExtractionContext

# Import PlayerStats from the play engine
try:
    from ...play_engine.simulation.stats import PlayerStats
except ImportError:
    try:
        from play_engine.simulation.stats import PlayerStats
    except ImportError:
        # Fallback - define a minimal PlayerStats interface
        class PlayerStats:
            def __init__(self):
                pass


class PlayerStatistic:
    """
    Extracted player statistic object.

    Normalized representation of player statistics extracted from game results.
    """

    def __init__(self, player_id: str, player_name: str, team_id: int, position: str):
        self.player_id = player_id
        self.player_name = player_name
        self.team_id = team_id
        self.position = position

        # Traditional statistics
        self.passing_yards = 0
        self.passing_tds = 0
        self.passing_attempts = 0
        self.passing_completions = 0
        self.passing_interceptions = 0
        self.passing_sacks = 0
        self.passing_sack_yards = 0
        self.passing_rating = 0.0

        self.rushing_yards = 0
        self.rushing_tds = 0
        self.rushing_attempts = 0
        self.rushing_long = 0
        self.rushing_fumbles = 0

        self.receiving_yards = 0
        self.receiving_tds = 0
        self.receptions = 0
        self.targets = 0
        self.receiving_long = 0
        self.receiving_drops = 0

        self.tackles_total = 0
        self.tackles_solo = 0
        self.tackles_assist = 0
        self.sacks = 0.0
        self.interceptions = 0
        self.forced_fumbles = 0
        self.fumbles_recovered = 0
        self.passes_defended = 0

        self.field_goals_made = 0
        self.field_goals_attempted = 0
        self.extra_points_made = 0
        self.extra_points_attempted = 0
        self.punts = 0
        self.punt_yards = 0

        # Comprehensive Offensive Line statistics
        self.pancakes = 0
        self.sacks_allowed = 0
        self.hurries_allowed = 0
        self.pressures_allowed = 0
        self.run_blocking_grade = 0.0
        self.pass_blocking_efficiency = 0.0
        self.missed_assignments = 0
        self.holding_penalties = 0
        self.false_start_penalties = 0
        self.downfield_blocks = 0
        self.double_team_blocks = 0
        self.chip_blocks = 0

        # Performance metrics
        self.fantasy_points = 0.0
        self.snap_counts_offense = 0
        self.snap_counts_defense = 0
        self.snap_counts_special_teams = 0

    def is_offensive_lineman(self) -> bool:
        """Check if this player is an offensive lineman."""
        o_line_positions = ['left_tackle', 'left_guard', 'center', 'right_guard', 'right_tackle']
        return self.position.lower() in o_line_positions

    def has_comprehensive_o_line_stats(self) -> bool:
        """Check if this player has comprehensive O-line statistics."""
        return (self.pancakes > 0 or self.sacks_allowed > 0 or
                self.hurries_allowed > 0 or self.pressures_allowed > 0 or
                self.run_blocking_grade > 0 or self.pass_blocking_efficiency > 0)


class PlayerStatisticsExtractor(BaseExtractor):
    """
    Extracts comprehensive player statistics from game results.

    Specializes in extracting all player statistics including the new
    comprehensive offensive line statistics with proper attribution.
    """

    def __init__(self, logger: logging.Logger = None):
        """
        Initialize the player statistics extractor.

        Args:
            logger: Optional logger for debugging
        """
        super().__init__(logger)

    def extract_player_statistics(self, game_result: Any, context: ExtractionContext) -> List[PlayerStatistic]:
        """
        Extract comprehensive player statistics from game result.

        Main public method that orchestrates the extraction of all player statistics.

        Args:
            game_result: Game simulation result from FullGameSimulator
            context: Extraction context with game metadata

        Returns:
            List of PlayerStatistic objects with comprehensive statistics
        """
        return self.safe_extract(game_result, context)

    def extract(self, game_result: Any, context: ExtractionContext) -> List[PlayerStatistic]:
        """
        Extract player statistics implementation.

        Args:
            game_result: Game simulation result
            context: Extraction context

        Returns:
            List of PlayerStatistic objects
        """
        player_statistics = []

        # Extract player stats dictionary from game result
        player_stats_dict = self.extract_player_stats_dict(game_result)

        if not player_stats_dict:
            self.logger.warning("No player statistics found in game result")
            return []

        self.logger.debug(f"Extracting statistics for {len(player_stats_dict)} players")

        # Process each player's statistics
        for player_name, player_stats in player_stats_dict.items():
            try:
                player_stat = self._extract_single_player_stats(
                    player_name, player_stats, context
                )
                if player_stat:
                    player_statistics.append(player_stat)

            except Exception as e:
                self.logger.error(f"Error extracting stats for player {player_name}: {e}")
                continue

        self.logger.info(f"Successfully extracted statistics for {len(player_statistics)} players")
        return player_statistics

    def _extract_single_player_stats(self, player_name: str, player_stats: Any,
                                   context: ExtractionContext) -> PlayerStatistic:
        """
        Extract statistics for a single player.

        Args:
            player_name: Name of the player
            player_stats: Player statistics object (PlayerStats or dict)
            context: Extraction context

        Returns:
            PlayerStatistic object or None if extraction fails
        """
        # Extract basic player information
        player_id = self._extract_player_id(player_name, player_stats)
        team_id = self._extract_team_id(player_stats, context)
        position = self._extract_position(player_stats)

        if team_id is None:
            self.logger.warning(f"Could not determine team for player {player_name}")
            return None

        # Create player statistic object
        player_stat = PlayerStatistic(player_id, player_name, team_id, position)

        # Create player-specific extraction context
        player_context = PlayerExtractionContext(
            player_id=player_id,
            player_name=player_name,
            team_id=team_id,
            position=position,
            game_context=context
        )

        # Extract all statistics categories
        self._extract_passing_stats(player_stats, player_stat)
        self._extract_rushing_stats(player_stats, player_stat)
        self._extract_receiving_stats(player_stats, player_stat)
        self._extract_defensive_stats(player_stats, player_stat)
        self._extract_special_teams_stats(player_stats, player_stat)
        self._extract_comprehensive_oline_stats(player_stats, player_stat, player_context)
        self._extract_performance_metrics(player_stats, player_stat)

        return player_stat

    def _extract_player_id(self, player_name: str, player_stats: Any) -> str:
        """Extract player ID, generating one if not available."""
        player_id = self.get_safe_attribute(player_stats, 'player_id')
        if player_id:
            return str(player_id)

        # Generate player ID from name if not available
        return f"player_{player_name.lower().replace(' ', '_')}"

    def _extract_team_id(self, player_stats: Any, context: ExtractionContext) -> int:
        """Extract team ID for the player."""
        team_id = self.get_safe_attribute(player_stats, 'team_id')
        if team_id is not None:
            return int(team_id)

        # If team_id not in player_stats, we can't determine which team
        # This might happen in some game result formats
        self.logger.warning("Could not determine team_id from player stats")
        return None

    def _extract_position(self, player_stats: Any) -> str:
        """Extract player position."""
        position = self.get_safe_attribute(player_stats, 'position', 'unknown')
        return str(position).lower()

    def _extract_passing_stats(self, player_stats: Any, player_stat: PlayerStatistic) -> None:
        """Extract passing statistics."""
        player_stat.passing_yards = self.get_safe_attribute(player_stats, 'passing_yards', 0)
        player_stat.passing_tds = self.get_safe_attribute(player_stats, 'passing_tds', 0)
        player_stat.passing_attempts = self.get_safe_attribute(player_stats, 'passing_attempts', 0)
        player_stat.passing_completions = self.get_safe_attribute(player_stats, 'passing_completions', 0)
        player_stat.passing_interceptions = self.get_safe_attribute(player_stats, 'passing_interceptions', 0)
        player_stat.passing_sacks = self.get_safe_attribute(player_stats, 'passing_sacks', 0)
        player_stat.passing_sack_yards = self.get_safe_attribute(player_stats, 'passing_sack_yards', 0)
        player_stat.passing_rating = self.get_safe_attribute(player_stats, 'passing_rating', 0.0)

    def _extract_rushing_stats(self, player_stats: Any, player_stat: PlayerStatistic) -> None:
        """Extract rushing statistics."""
        player_stat.rushing_yards = self.get_safe_attribute(player_stats, 'rushing_yards', 0)
        player_stat.rushing_tds = self.get_safe_attribute(player_stats, 'rushing_tds', 0)
        player_stat.rushing_attempts = self.get_safe_attribute(player_stats, 'rushing_attempts', 0)
        player_stat.rushing_long = self.get_safe_attribute(player_stats, 'rushing_long', 0)
        player_stat.rushing_fumbles = self.get_safe_attribute(player_stats, 'rushing_fumbles', 0)

    def _extract_receiving_stats(self, player_stats: Any, player_stat: PlayerStatistic) -> None:
        """Extract receiving statistics."""
        player_stat.receiving_yards = self.get_safe_attribute(player_stats, 'receiving_yards', 0)
        player_stat.receiving_tds = self.get_safe_attribute(player_stats, 'receiving_tds', 0)
        player_stat.receptions = self.get_safe_attribute(player_stats, 'receptions', 0)
        player_stat.targets = self.get_safe_attribute(player_stats, 'targets', 0)
        player_stat.receiving_long = self.get_safe_attribute(player_stats, 'receiving_long', 0)
        player_stat.receiving_drops = self.get_safe_attribute(player_stats, 'receiving_drops', 0)

    def _extract_defensive_stats(self, player_stats: Any, player_stat: PlayerStatistic) -> None:
        """Extract defensive statistics."""
        # Handle both 'tackles' and 'tackles_total' field names
        tackles = self.get_safe_attribute(player_stats, 'tackles', 0)
        if tackles == 0:
            tackles = self.get_safe_attribute(player_stats, 'tackles_total', 0)
        player_stat.tackles_total = tackles

        player_stat.tackles_solo = self.get_safe_attribute(player_stats, 'tackles_solo', 0)
        player_stat.tackles_assist = self.get_safe_attribute(player_stats, 'tackles_assist', 0)
        player_stat.sacks = self.get_safe_attribute(player_stats, 'sacks', 0.0)
        player_stat.interceptions = self.get_safe_attribute(player_stats, 'interceptions', 0)
        player_stat.forced_fumbles = self.get_safe_attribute(player_stats, 'forced_fumbles', 0)
        player_stat.fumbles_recovered = self.get_safe_attribute(player_stats, 'fumbles_recovered', 0)
        player_stat.passes_defended = self.get_safe_attribute(player_stats, 'passes_defended', 0)

    def _extract_special_teams_stats(self, player_stats: Any, player_stat: PlayerStatistic) -> None:
        """Extract special teams statistics."""
        player_stat.field_goals_made = self.get_safe_attribute(player_stats, 'field_goals_made', 0)
        player_stat.field_goals_attempted = self.get_safe_attribute(player_stats, 'field_goals_attempted', 0)
        player_stat.extra_points_made = self.get_safe_attribute(player_stats, 'extra_points_made', 0)
        player_stat.extra_points_attempted = self.get_safe_attribute(player_stats, 'extra_points_attempted', 0)
        player_stat.punts = self.get_safe_attribute(player_stats, 'punts', 0)
        player_stat.punt_yards = self.get_safe_attribute(player_stats, 'punt_yards', 0)

    def _extract_comprehensive_oline_stats(self, player_stats: Any, player_stat: PlayerStatistic,
                                         player_context: PlayerExtractionContext) -> None:
        """
        Extract comprehensive offensive line statistics.

        This is the core method for extracting the new O-line statistics
        that were recently implemented in the simulation engine.
        """
        # Only extract O-line stats if enabled and relevant for this player
        if not player_context.should_extract_o_line_stats():
            return

        # Extract comprehensive O-line statistics
        player_stat.pancakes = self.get_safe_attribute(player_stats, 'pancakes', 0)
        player_stat.sacks_allowed = self.get_safe_attribute(player_stats, 'sacks_allowed', 0)
        player_stat.hurries_allowed = self.get_safe_attribute(player_stats, 'hurries_allowed', 0)
        player_stat.pressures_allowed = self.get_safe_attribute(player_stats, 'pressures_allowed', 0)

        # Blocking grades (0-100 scale)
        player_stat.run_blocking_grade = self.get_safe_attribute(player_stats, 'run_blocking_grade', 0.0)
        player_stat.pass_blocking_efficiency = self.get_safe_attribute(player_stats, 'pass_blocking_efficiency', 0.0)

        # Assignments and penalties
        player_stat.missed_assignments = self.get_safe_attribute(player_stats, 'missed_assignments', 0)
        player_stat.holding_penalties = self.get_safe_attribute(player_stats, 'holding_penalties', 0)
        player_stat.false_start_penalties = self.get_safe_attribute(player_stats, 'false_start_penalties', 0)

        # Advanced blocking statistics
        player_stat.downfield_blocks = self.get_safe_attribute(player_stats, 'downfield_blocks', 0)
        player_stat.double_team_blocks = self.get_safe_attribute(player_stats, 'double_team_blocks', 0)
        player_stat.chip_blocks = self.get_safe_attribute(player_stats, 'chip_blocks', 0)

        # Log O-line stats extraction for debugging
        if player_stat.has_comprehensive_o_line_stats():
            self.logger.debug(f"Extracted O-line stats for {player_stat.player_name}: "
                            f"pancakes={player_stat.pancakes}, sacks_allowed={player_stat.sacks_allowed}, "
                            f"run_grade={player_stat.run_blocking_grade:.1f}, "
                            f"pass_eff={player_stat.pass_blocking_efficiency:.1f}")

    def _extract_performance_metrics(self, player_stats: Any, player_stat: PlayerStatistic) -> None:
        """Extract performance metrics and snap counts."""
        player_stat.fantasy_points = self.get_safe_attribute(player_stats, 'fantasy_points', 0.0)

        # Snap counts - try multiple field names
        player_stat.snap_counts_offense = self.get_safe_attribute(player_stats, 'offensive_snaps', 0)
        if player_stat.snap_counts_offense == 0:
            player_stat.snap_counts_offense = self.get_safe_attribute(player_stats, 'snap_counts_offense', 0)

        player_stat.snap_counts_defense = self.get_safe_attribute(player_stats, 'defensive_snaps', 0)
        if player_stat.snap_counts_defense == 0:
            player_stat.snap_counts_defense = self.get_safe_attribute(player_stats, 'snap_counts_defense', 0)

        player_stat.snap_counts_special_teams = self.get_safe_attribute(player_stats, 'special_teams_snaps', 0)
        if player_stat.snap_counts_special_teams == 0:
            player_stat.snap_counts_special_teams = self.get_safe_attribute(player_stats, 'snap_counts_special_teams', 0)

    def validate_game_result(self, game_result: Any) -> bool:
        """
        Validate game result for player statistics extraction.

        Enhanced validation specific to player statistics requirements.
        """
        if not super().validate_game_result(game_result):
            return False

        # Check for player statistics
        player_stats_dict = self.extract_player_stats_dict(game_result)
        if not player_stats_dict:
            self.logger.warning("No player statistics found in game result")
            return False

        return True