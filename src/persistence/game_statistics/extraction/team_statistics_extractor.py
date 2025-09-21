"""
Team Statistics Extractor

Extracts team-level aggregate statistics from game results.
"""

from typing import List, Dict, Any
import logging

from .base_extractor import BaseExtractor
from ..models.extraction_context import ExtractionContext


class TeamStatistic:
    """
    Extracted team statistic object.

    Aggregated team-level statistics for a single game.
    """

    def __init__(self, team_id: int):
        self.team_id = team_id

        # Offensive totals
        self.total_yards = 0
        self.passing_yards = 0
        self.rushing_yards = 0
        self.first_downs = 0
        self.third_down_conversions = 0
        self.third_down_attempts = 0
        self.red_zone_conversions = 0
        self.red_zone_attempts = 0

        # Turnovers
        self.turnovers = 0
        self.interceptions_thrown = 0
        self.fumbles_lost = 0

        # Defensive totals
        self.sacks = 0.0
        self.tackles_for_loss = 0
        self.interceptions = 0
        self.forced_fumbles = 0
        self.passes_defended = 0

        # Special teams
        self.field_goals_made = 0
        self.field_goals_attempted = 0
        self.punts = 0
        self.punt_average = 0.0

        # Game flow
        self.time_of_possession_seconds = 0
        self.penalties = 0
        self.penalty_yards = 0


class TeamStatisticsExtractor(BaseExtractor):
    """
    Extracts team-level aggregate statistics from game results.
    """

    def __init__(self, logger: logging.Logger = None):
        """
        Initialize the team statistics extractor.

        Args:
            logger: Optional logger for debugging
        """
        super().__init__(logger)

    def extract_team_statistics(self, game_result: Any, context: ExtractionContext) -> List[TeamStatistic]:
        """
        Extract team statistics from game result.

        Args:
            game_result: Game simulation result
            context: Extraction context

        Returns:
            List of TeamStatistic objects (one per team)
        """
        return self.safe_extract(game_result, context)

    def extract(self, game_result: Any, context: ExtractionContext) -> List[TeamStatistic]:
        """
        Extract team statistics implementation.

        Args:
            game_result: Game simulation result
            context: Extraction context

        Returns:
            List of TeamStatistic objects
        """
        team_statistics = []

        # Extract statistics for both teams
        for team_id in context.get_team_ids():
            try:
                team_stat = self._extract_single_team_stats(game_result, team_id, context)
                if team_stat:
                    team_statistics.append(team_stat)
            except Exception as e:
                self.logger.error(f"Error extracting team stats for team {team_id}: {e}")
                continue

        return team_statistics

    def _extract_single_team_stats(self, game_result: Any, team_id: int,
                                 context: ExtractionContext) -> TeamStatistic:
        """
        Extract statistics for a single team.

        Args:
            game_result: Game simulation result
            team_id: Team to extract statistics for
            context: Extraction context

        Returns:
            TeamStatistic object
        """
        team_stat = TeamStatistic(team_id)

        # Try to get team statistics from multiple possible locations
        team_stats_dict = self._get_team_stats_dict(game_result)

        if team_stats_dict and team_id in team_stats_dict:
            # Extract from direct team stats
            self._extract_from_team_stats_dict(team_stats_dict[team_id], team_stat)
        else:
            # Aggregate from player statistics
            self._aggregate_from_player_stats(game_result, team_id, team_stat, context)

        return team_stat

    def _get_team_stats_dict(self, game_result: Any) -> Dict[int, Any]:
        """
        Extract team statistics dictionary from game result.

        Args:
            game_result: Game simulation result

        Returns:
            Dictionary mapping team IDs to team stats
        """
        possible_paths = [
            'final_statistics.team_statistics',
            'team_statistics',
            'stats.teams',
            'team_stats'
        ]

        for path in possible_paths:
            team_stats = self.get_nested_attribute(game_result, path)
            if team_stats and isinstance(team_stats, dict):
                return team_stats

        return {}

    def _extract_from_team_stats_dict(self, team_stats: Any, team_stat: TeamStatistic) -> None:
        """
        Extract team statistics from team stats dictionary.

        Args:
            team_stats: Team statistics object
            team_stat: TeamStatistic to populate
        """
        # Offensive totals
        team_stat.total_yards = self.get_safe_attribute(team_stats, 'total_yards', 0)
        team_stat.passing_yards = self.get_safe_attribute(team_stats, 'passing_yards', 0)
        team_stat.rushing_yards = self.get_safe_attribute(team_stats, 'rushing_yards', 0)
        team_stat.first_downs = self.get_safe_attribute(team_stats, 'first_downs', 0)

        # Turnovers
        team_stat.turnovers = self.get_safe_attribute(team_stats, 'turnovers', 0)
        team_stat.interceptions_thrown = self.get_safe_attribute(team_stats, 'interceptions_thrown', 0)
        team_stat.fumbles_lost = self.get_safe_attribute(team_stats, 'fumbles_lost', 0)

        # Defensive
        team_stat.sacks = self.get_safe_attribute(team_stats, 'sacks', 0.0)
        team_stat.tackles_for_loss = self.get_safe_attribute(team_stats, 'tackles_for_loss', 0)
        team_stat.interceptions = self.get_safe_attribute(team_stats, 'interceptions', 0)
        team_stat.forced_fumbles = self.get_safe_attribute(team_stats, 'forced_fumbles', 0)
        team_stat.passes_defended = self.get_safe_attribute(team_stats, 'passes_defended', 0)

        # Special teams
        team_stat.field_goals_made = self.get_safe_attribute(team_stats, 'field_goals_made', 0)
        team_stat.field_goals_attempted = self.get_safe_attribute(team_stats, 'field_goals_attempted', 0)

        # Penalties
        team_stat.penalties = self.get_safe_attribute(team_stats, 'penalties', 0)
        team_stat.penalty_yards = self.get_safe_attribute(team_stats, 'penalty_yards', 0)

    def _aggregate_from_player_stats(self, game_result: Any, team_id: int,
                                   team_stat: TeamStatistic, context: ExtractionContext) -> None:
        """
        Aggregate team statistics from individual player statistics.

        Args:
            game_result: Game simulation result
            team_id: Team to aggregate for
            team_stat: TeamStatistic to populate
            context: Extraction context
        """
        player_stats_dict = self.extract_player_stats_dict(game_result)

        for player_name, player_stats in player_stats_dict.items():
            player_team_id = self.get_safe_attribute(player_stats, 'team_id')

            if player_team_id == team_id:
                self._aggregate_player_to_team(player_stats, team_stat)

    def _aggregate_player_to_team(self, player_stats: Any, team_stat: TeamStatistic) -> None:
        """
        Aggregate individual player stats into team totals.

        Args:
            player_stats: Individual player statistics
            team_stat: TeamStatistic to update
        """
        # Offensive aggregation
        team_stat.passing_yards += self.get_safe_attribute(player_stats, 'passing_yards', 0)
        team_stat.rushing_yards += self.get_safe_attribute(player_stats, 'rushing_yards', 0)
        team_stat.receiving_yards += self.get_safe_attribute(player_stats, 'receiving_yards', 0)

        # Defensive aggregation
        team_stat.sacks += self.get_safe_attribute(player_stats, 'sacks', 0.0)
        team_stat.interceptions += self.get_safe_attribute(player_stats, 'interceptions', 0)
        team_stat.forced_fumbles += self.get_safe_attribute(player_stats, 'forced_fumbles', 0)
        team_stat.passes_defended += self.get_safe_attribute(player_stats, 'passes_defended', 0)

        # Special teams aggregation
        team_stat.field_goals_made += self.get_safe_attribute(player_stats, 'field_goals_made', 0)
        team_stat.field_goals_attempted += self.get_safe_attribute(player_stats, 'field_goals_attempted', 0)

        # Calculate total yards
        team_stat.total_yards = team_stat.passing_yards + team_stat.rushing_yards