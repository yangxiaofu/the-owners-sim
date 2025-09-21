"""
Database Mapper

Maps extracted statistics to database format using configurable field mappings.
"""

from typing import List, Dict, Any
import logging

from .field_mapping_registry import FieldMappingRegistry
from ..models.database_record import PlayerGameStatsRecord, TeamGameStatsRecord, GameContextRecord
from ..models.extraction_context import ExtractionContext
from ..extraction.player_statistics_extractor import PlayerStatistic
from ..extraction.team_statistics_extractor import TeamStatistic
from ..extraction.game_metadata_extractor import GameMetadata


class DatabaseMapper:
    """
    Maps extracted statistics to database format using configurable mappings.
    """

    def __init__(self, field_mapping_registry: FieldMappingRegistry, logger: logging.Logger = None):
        """
        Initialize the database mapper.

        Args:
            field_mapping_registry: Registry for field mappings
            logger: Optional logger for debugging
        """
        self.field_registry = field_mapping_registry
        self.logger = logger or logging.getLogger(__name__)

    def map_player_statistics(self, player_stats: List[PlayerStatistic],
                             context: ExtractionContext) -> List[PlayerGameStatsRecord]:
        """
        Map player statistics to database records.

        Args:
            player_stats: List of extracted player statistics
            context: Extraction context

        Returns:
            List of PlayerGameStatsRecord objects
        """
        records = []

        for player_stat in player_stats:
            try:
                record = self._map_single_player_stat(player_stat, context)
                records.append(record)
            except Exception as e:
                self.logger.error(f"Error mapping player {player_stat.player_name}: {e}")
                continue

        self.logger.debug(f"Mapped {len(records)} player statistics to database records")
        return records

    def _map_single_player_stat(self, player_stat: PlayerStatistic,
                               context: ExtractionContext) -> PlayerGameStatsRecord:
        """
        Map a single player statistic to database record.

        Args:
            player_stat: Extracted player statistic
            context: Extraction context

        Returns:
            PlayerGameStatsRecord object
        """
        # Map all fields using the field registry
        mapped_fields = {}

        # Core fields (always present)
        mapped_fields.update({
            'dynasty_id': context.dynasty_id,
            'game_id': context.game_id,
            'player_id': player_stat.player_id,
            'player_name': player_stat.player_name,
            'team_id': player_stat.team_id,
            'position': player_stat.position,
        })

        # Map statistical fields
        stat_fields = [
            # Passing
            'passing_yards', 'passing_tds', 'passing_attempts', 'passing_completions',
            'passing_interceptions', 'passing_sacks', 'passing_sack_yards', 'passing_rating',

            # Rushing
            'rushing_yards', 'rushing_tds', 'rushing_attempts', 'rushing_long', 'rushing_fumbles',

            # Receiving
            'receiving_yards', 'receiving_tds', 'receptions', 'targets',
            'receiving_long', 'receiving_drops',

            # Defensive
            'tackles_total', 'tackles_solo', 'tackles_assist', 'sacks', 'interceptions',
            'forced_fumbles', 'fumbles_recovered', 'passes_defended',

            # Special teams
            'field_goals_made', 'field_goals_attempted', 'extra_points_made',
            'extra_points_attempted', 'punts', 'punt_yards',

            # Comprehensive O-line stats
            'pancakes', 'sacks_allowed', 'hurries_allowed', 'pressures_allowed',
            'run_blocking_grade', 'pass_blocking_efficiency', 'missed_assignments',
            'holding_penalties', 'false_start_penalties', 'downfield_blocks',
            'double_team_blocks', 'chip_blocks',

            # Performance
            'fantasy_points', 'snap_counts_offense', 'snap_counts_defense', 'snap_counts_special_teams'
        ]

        for field_name in stat_fields:
            source_value = getattr(player_stat, field_name, None)
            if source_value is not None:
                db_field_name = self.field_registry.get_db_field_name('player_stats', field_name)
                mapped_fields[db_field_name] = source_value

        # Create and return the database record
        return PlayerGameStatsRecord(**mapped_fields)

    def map_team_statistics(self, team_stats: List[TeamStatistic],
                           context: ExtractionContext) -> List[TeamGameStatsRecord]:
        """
        Map team statistics to database records.

        Args:
            team_stats: List of extracted team statistics
            context: Extraction context

        Returns:
            List of TeamGameStatsRecord objects
        """
        records = []

        for team_stat in team_stats:
            try:
                record = self._map_single_team_stat(team_stat, context)
                records.append(record)
            except Exception as e:
                self.logger.error(f"Error mapping team {team_stat.team_id}: {e}")
                continue

        return records

    def _map_single_team_stat(self, team_stat: TeamStatistic,
                             context: ExtractionContext) -> TeamGameStatsRecord:
        """
        Map a single team statistic to database record.

        Args:
            team_stat: Extracted team statistic
            context: Extraction context

        Returns:
            TeamGameStatsRecord object
        """
        return TeamGameStatsRecord(
            dynasty_id=context.dynasty_id,
            game_id=context.game_id,
            team_id=team_stat.team_id,
            total_yards=team_stat.total_yards,
            passing_yards=team_stat.passing_yards,
            rushing_yards=team_stat.rushing_yards,
            first_downs=team_stat.first_downs,
            third_down_conversions=team_stat.third_down_conversions,
            third_down_attempts=team_stat.third_down_attempts,
            red_zone_conversions=team_stat.red_zone_conversions,
            red_zone_attempts=team_stat.red_zone_attempts,
            turnovers=team_stat.turnovers,
            interceptions_thrown=team_stat.interceptions_thrown,
            fumbles_lost=team_stat.fumbles_lost,
            sacks=team_stat.sacks,
            tackles_for_loss=team_stat.tackles_for_loss,
            interceptions=team_stat.interceptions,
            forced_fumbles=team_stat.forced_fumbles,
            passes_defended=team_stat.passes_defended,
            field_goals_made=team_stat.field_goals_made,
            field_goals_attempted=team_stat.field_goals_attempted,
            punts=team_stat.punts,
            punt_average=team_stat.punt_average,
            time_of_possession_seconds=team_stat.time_of_possession_seconds,
            penalties=team_stat.penalties,
            penalty_yards=team_stat.penalty_yards
        )

    def map_game_metadata(self, game_metadata: GameMetadata,
                         context: ExtractionContext) -> GameContextRecord:
        """
        Map game metadata to database record.

        Args:
            game_metadata: Extracted game metadata
            context: Extraction context

        Returns:
            GameContextRecord object
        """
        return GameContextRecord(
            dynasty_id=context.dynasty_id,
            game_id=context.game_id,
            away_team_id=context.away_team_id,
            home_team_id=context.home_team_id,
            game_date=context.game_date,
            week=context.week,
            season_type=context.season_type,
            away_score=game_metadata.away_score,
            home_score=game_metadata.home_score,
            winning_team_id=game_metadata.winning_team_id,
            total_plays=game_metadata.total_plays,
            game_duration_minutes=game_metadata.game_duration_minutes,
            created_at=game_metadata.created_at
        )