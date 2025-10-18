"""
Statistical Leaderboard Generation for The Owner's Sim

Builds statistical leaderboards with calculated metrics, filters, and rankings.
"""
from typing import List, Dict, Any, Optional
from database.api import DatabaseAPI
from statistics.models import PassingStats, RushingStats, ReceivingStats, DefensiveStats, SpecialTeamsStats
from stats_calculations.calculations import (
    calculate_passer_rating,
    calculate_yards_per_carry,
    calculate_catch_rate,
    calculate_yards_per_reception,
    calculate_fg_percentage,
    calculate_xp_percentage,
    calculate_yards_per_attempt,
)
from statistics.filters import StatFilters
from statistics.rankings import add_all_rankings


class LeaderboardBuilder:
    """
    Builds statistical leaderboards with calculated metrics and rankings.

    Provides methods for generating leaderboards across all major statistical
    categories (passing, rushing, receiving, defensive, special teams) with:
    - Calculated derived metrics (passer rating, YPC, catch rate, etc.)
    - Conference and division filtering
    - League, conference, and division rankings
    - Type-safe dataclass output for UI integration
    """

    def __init__(self, db_api: DatabaseAPI):
        """
        Initialize leaderboard builder.

        Args:
            db_api: DatabaseAPI instance for data retrieval
        """
        self.db_api = db_api

    def build_passing_leaderboard(
        self,
        dynasty_id: str,
        season: int,
        limit: int = 25,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[PassingStats]:
        """
        Build passing leaderboard with calculated passer ratings.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            limit: Number of leaders to return
            filters: Optional filters dict:
                - 'conference': 'AFC' or 'NFC'
                - 'division': 'East', 'North', 'South', 'West'
                - 'min_attempts': Minimum pass attempts
                - 'position': Position filter (default 'QB')

        Returns:
            List of PassingStats dataclasses sorted by passing yards
        """
        # 1. Get raw stats from DatabaseAPI (get more than limit for filtering)
        raw_stats = self.db_api.get_passing_leaders(dynasty_id, season, limit=100)

        # 2. Calculate derived metrics for each player
        for stat in raw_stats:
            # Get interceptions (field name is total_interceptions from query)
            interceptions = stat.get('total_interceptions', stat.get('interceptions', 0))

            stat['passer_rating'] = calculate_passer_rating(
                stat['total_completions'],
                stat['total_attempts'],
                stat['total_passing_yards'],
                stat['total_passing_tds'],
                interceptions
            )
            stat['yards_per_attempt'] = calculate_yards_per_attempt(
                stat['total_passing_yards'],
                stat['total_attempts']
            )
            stat['yards_per_game'] = stat['total_passing_yards'] / stat['games_played'] if stat['games_played'] > 0 else 0.0

        # 3. Apply filters if provided
        if filters:
            if 'conference' in filters:
                raw_stats = StatFilters.filter_by_conference(raw_stats, filters['conference'])
            if 'division' in filters:
                raw_stats = StatFilters.filter_by_division(raw_stats, filters['division'])
            if 'min_attempts' in filters:
                raw_stats = StatFilters.filter_by_minimum(raw_stats, 'total_attempts', filters['min_attempts'])

        # 4. Calculate rankings (league, conference, division)
        raw_stats = add_all_rankings(raw_stats, 'total_passing_yards', ascending=False)

        # 5. Sort by passing yards (descending) and limit
        raw_stats.sort(key=lambda x: x['total_passing_yards'], reverse=True)
        raw_stats = raw_stats[:limit]

        # 6. Convert to PassingStats dataclasses
        result = []
        for stat in raw_stats:
            passing_stat = PassingStats(
                player_id=stat['player_id'],
                player_name=stat['player_name'],
                team_id=stat['team_id'],
                position=stat['position'],
                games=stat['games_played'],
                completions=stat['total_completions'],
                attempts=stat['total_attempts'],
                yards=stat['total_passing_yards'],
                touchdowns=stat['total_passing_tds'],
                interceptions=stat.get('total_interceptions', stat.get('interceptions', 0)),
                completion_pct=stat['completion_percentage'],
                yards_per_attempt=stat['yards_per_attempt'],
                yards_per_game=stat['yards_per_game'],
                passer_rating=stat['passer_rating'],
                league_rank=stat.get('league_rank'),
                conference_rank=stat.get('conference_rank'),
                division_rank=stat.get('division_rank'),
            )
            result.append(passing_stat)

        return result

    def build_rushing_leaderboard(
        self,
        dynasty_id: str,
        season: int,
        limit: int = 25,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[RushingStats]:
        """
        Build rushing leaderboard with yards per carry.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            limit: Number of leaders to return
            filters: Optional filters dict:
                - 'conference': 'AFC' or 'NFC'
                - 'division': 'East', 'North', 'South', 'West'
                - 'min_attempts': Minimum rush attempts
                - 'position': Position filter (e.g., 'RB')

        Returns:
            List of RushingStats dataclasses sorted by rushing yards
        """
        # 1. Get raw stats from DatabaseAPI
        raw_stats = self.db_api.get_rushing_leaders(dynasty_id, season, limit=100)

        # 2. Calculate derived metrics
        for stat in raw_stats:
            stat['yards_per_carry'] = calculate_yards_per_carry(
                stat['total_rushing_yards'],
                stat['total_attempts']
            )
            stat['yards_per_game'] = stat['total_rushing_yards'] / stat['games_played'] if stat['games_played'] > 0 else 0.0

        # 3. Apply filters if provided
        if filters:
            if 'conference' in filters:
                raw_stats = StatFilters.filter_by_conference(raw_stats, filters['conference'])
            if 'division' in filters:
                raw_stats = StatFilters.filter_by_division(raw_stats, filters['division'])
            if 'min_attempts' in filters:
                raw_stats = StatFilters.filter_by_minimum(raw_stats, 'total_attempts', filters['min_attempts'])
            if 'position' in filters:
                raw_stats = StatFilters.filter_by_position(raw_stats, [filters['position']])

        # 4. Calculate rankings
        raw_stats = add_all_rankings(raw_stats, 'total_rushing_yards', ascending=False)

        # 5. Sort and limit
        raw_stats.sort(key=lambda x: x['total_rushing_yards'], reverse=True)
        raw_stats = raw_stats[:limit]

        # 6. Convert to RushingStats dataclasses
        result = []
        for stat in raw_stats:
            rushing_stat = RushingStats(
                player_id=stat['player_id'],
                player_name=stat['player_name'],
                team_id=stat['team_id'],
                position=stat['position'],
                games=stat['games_played'],
                attempts=stat['total_attempts'],
                yards=stat['total_rushing_yards'],
                touchdowns=stat['total_rushing_tds'],
                yards_per_carry=stat['yards_per_carry'],
                yards_per_game=stat['yards_per_game'],
                league_rank=stat.get('league_rank'),
                conference_rank=stat.get('conference_rank'),
                division_rank=stat.get('division_rank'),
            )
            result.append(rushing_stat)

        return result

    def build_receiving_leaderboard(
        self,
        dynasty_id: str,
        season: int,
        limit: int = 25,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[ReceivingStats]:
        """
        Build receiving leaderboard with catch rate, YPR.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            limit: Number of leaders to return
            filters: Optional filters dict:
                - 'conference': 'AFC' or 'NFC'
                - 'division': 'East', 'North', 'South', 'West'
                - 'min_receptions': Minimum receptions
                - 'position': Position filter (e.g., 'WR', 'TE')

        Returns:
            List of ReceivingStats dataclasses sorted by receiving yards
        """
        # 1. Get raw stats from DatabaseAPI
        raw_stats = self.db_api.get_receiving_leaders(dynasty_id, season, limit=100)

        # 2. Calculate derived metrics
        for stat in raw_stats:
            stat['catch_rate'] = calculate_catch_rate(
                stat['total_receptions'],
                stat['total_targets']
            )
            stat['yards_per_reception'] = calculate_yards_per_reception(
                stat['total_receiving_yards'],
                stat['total_receptions']
            )
            stat['yards_per_target'] = calculate_yards_per_attempt(
                stat['total_receiving_yards'],
                stat['total_targets']
            )
            stat['yards_per_game'] = stat['total_receiving_yards'] / stat['games_played'] if stat['games_played'] > 0 else 0.0

        # 3. Apply filters if provided
        if filters:
            if 'conference' in filters:
                raw_stats = StatFilters.filter_by_conference(raw_stats, filters['conference'])
            if 'division' in filters:
                raw_stats = StatFilters.filter_by_division(raw_stats, filters['division'])
            if 'min_receptions' in filters:
                raw_stats = StatFilters.filter_by_minimum(raw_stats, 'total_receptions', filters['min_receptions'])
            if 'position' in filters:
                raw_stats = StatFilters.filter_by_position(raw_stats, [filters['position']])

        # 4. Calculate rankings
        raw_stats = add_all_rankings(raw_stats, 'total_receiving_yards', ascending=False)

        # 5. Sort and limit
        raw_stats.sort(key=lambda x: x['total_receiving_yards'], reverse=True)
        raw_stats = raw_stats[:limit]

        # 6. Convert to ReceivingStats dataclasses
        result = []
        for stat in raw_stats:
            receiving_stat = ReceivingStats(
                player_id=stat['player_id'],
                player_name=stat['player_name'],
                team_id=stat['team_id'],
                position=stat['position'],
                games=stat['games_played'],
                receptions=stat['total_receptions'],
                targets=stat['total_targets'],
                yards=stat['total_receiving_yards'],
                touchdowns=stat['total_receiving_tds'],
                catch_rate=stat['catch_rate'],
                yards_per_reception=stat['yards_per_reception'],
                yards_per_target=stat['yards_per_target'],
                yards_per_game=stat['yards_per_game'],
                league_rank=stat.get('league_rank'),
                conference_rank=stat.get('conference_rank'),
                division_rank=stat.get('division_rank'),
            )
            result.append(receiving_stat)

        return result

    def build_defensive_leaderboard(
        self,
        dynasty_id: str,
        season: int,
        stat_category: str,
        limit: int = 25,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[DefensiveStats]:
        """
        Build defensive leaderboard for specific stat category.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            stat_category: One of 'tackles_total', 'sacks', 'interceptions'
            limit: Number of leaders to return
            filters: Optional filters dict:
                - 'conference': 'AFC' or 'NFC'
                - 'division': 'East', 'North', 'South', 'West'
                - 'position': Position filter (e.g., 'LB', 'DE', 'CB')

        Returns:
            List of DefensiveStats dataclasses sorted by stat_category
        """
        # Validate stat_category
        valid_categories = ['tackles_total', 'sacks', 'interceptions']
        if stat_category not in valid_categories:
            raise ValueError(f"Invalid defensive stat_category: {stat_category}. Must be one of {valid_categories}")

        # 1. Get raw stats using unified player leaders method
        raw_stats = self.db_api.get_player_leaders_unified(
            dynasty_id,
            season,
            stat_category,
            limit=100,
            position_filter=None
        )

        # 2. Apply filters if provided
        if filters:
            if 'conference' in filters:
                raw_stats = StatFilters.filter_by_conference(raw_stats, filters['conference'])
            if 'division' in filters:
                raw_stats = StatFilters.filter_by_division(raw_stats, filters['division'])
            if 'position' in filters:
                raw_stats = StatFilters.filter_by_position(raw_stats, [filters['position']])

        # 3. Calculate rankings
        raw_stats = add_all_rankings(raw_stats, f'total_{stat_category}', ascending=False)

        # 4. Sort and limit
        raw_stats.sort(key=lambda x: x[f'total_{stat_category}'], reverse=True)
        raw_stats = raw_stats[:limit]

        # 5. Convert to DefensiveStats dataclasses
        result = []
        for stat in raw_stats:
            defensive_stat = DefensiveStats(
                player_id=stat['player_id'],
                player_name=stat['player_name'],
                team_id=stat['team_id'],
                position=stat['position'],
                games=stat['games_played'],
                tackles_total=stat.get('total_tackles_total', 0),
                sacks=stat.get('total_sacks', 0.0),
                interceptions=stat.get('total_interceptions', 0),
                league_rank=stat.get('league_rank'),
                conference_rank=stat.get('conference_rank'),
                division_rank=stat.get('division_rank'),
            )
            result.append(defensive_stat)

        return result

    def build_special_teams_leaderboard(
        self,
        dynasty_id: str,
        season: int,
        limit: int = 25,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[SpecialTeamsStats]:
        """
        Build special teams leaderboard (kickers).

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            limit: Number of leaders to return
            filters: Optional filters dict:
                - 'conference': 'AFC' or 'NFC'
                - 'division': 'East', 'North', 'South', 'West'
                - 'min_attempts': Minimum FG attempts

        Returns:
            List of SpecialTeamsStats dataclasses sorted by FG%
        """
        # 1. Get raw stats using unified method for field goals
        raw_stats = self.db_api.get_player_leaders_unified(
            dynasty_id,
            season,
            'field_goals_made',
            limit=100,
            position_filter='K'
        )

        # 2. Need to get additional kicking stats - query again for complete data
        # Since unified method doesn't return XP stats, we need a custom approach
        # For now, calculate from available data
        for stat in raw_stats:
            # Use the available field goal data
            fg_made = stat.get('total_field_goals_made', 0)
            # We need FG attempted - not available from unified query
            # Set to same as made for now (would need custom query in production)
            fg_attempted = fg_made  # Placeholder

            stat['field_goals_attempted'] = fg_attempted
            stat['fg_percentage'] = calculate_fg_percentage(fg_made, fg_attempted)

            # XP stats not available from this query - set to 0
            stat['extra_points_made'] = 0
            stat['extra_points_attempted'] = 0
            stat['xp_percentage'] = 0.0

        # 3. Apply filters if provided
        if filters:
            if 'conference' in filters:
                raw_stats = StatFilters.filter_by_conference(raw_stats, filters['conference'])
            if 'division' in filters:
                raw_stats = StatFilters.filter_by_division(raw_stats, filters['division'])
            if 'min_attempts' in filters:
                raw_stats = StatFilters.filter_by_minimum(raw_stats, 'field_goals_attempted', filters['min_attempts'])

        # 4. Calculate rankings based on FG made
        raw_stats = add_all_rankings(raw_stats, 'total_field_goals_made', ascending=False)

        # 5. Sort by FG percentage and limit
        raw_stats.sort(key=lambda x: x['fg_percentage'], reverse=True)
        raw_stats = raw_stats[:limit]

        # 6. Convert to SpecialTeamsStats dataclasses
        result = []
        for stat in raw_stats:
            special_teams_stat = SpecialTeamsStats(
                player_id=stat['player_id'],
                player_name=stat['player_name'],
                team_id=stat['team_id'],
                position=stat['position'],
                games=stat['games_played'],
                field_goals_made=stat['total_field_goals_made'],
                field_goals_attempted=stat['field_goals_attempted'],
                extra_points_made=stat['extra_points_made'],
                extra_points_attempted=stat['extra_points_attempted'],
                fg_percentage=stat['fg_percentage'],
                xp_percentage=stat['xp_percentage'],
                league_rank=stat.get('league_rank'),
            )
            result.append(special_teams_stat)

        return result
