"""
Team Statistics Service for game_cycle.

Combines data from multiple API classes to provide comprehensive team statistics.
Service layer pattern - uses API classes, no direct SQL.
"""

from dataclasses import dataclass
from typing import Dict, List, Any, Optional
import logging


@dataclass
class TeamOverview:
    """Combined team statistics overview for a season."""

    team_id: int
    season: int

    # Record
    wins: int
    losses: int
    ties: int
    win_pct: float

    # Offensive stats
    total_yards: int
    passing_yards: int
    rushing_yards: int
    points_scored: int
    yards_per_game: float
    points_per_game: float

    # Defensive stats
    points_allowed: int
    yards_allowed: int
    sacks: float
    interceptions: int
    points_allowed_per_game: float

    # Turnovers
    turnovers: int
    turnovers_forced: int
    turnover_margin: int

    # Rankings (1-32, lower is better)
    offense_rank: int  # Based on total yards
    defense_rank: int  # Based on yards allowed
    points_rank: int  # Based on points scored

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'team_id': self.team_id,
            'season': self.season,
            'wins': self.wins,
            'losses': self.losses,
            'ties': self.ties,
            'win_pct': self.win_pct,
            'total_yards': self.total_yards,
            'passing_yards': self.passing_yards,
            'rushing_yards': self.rushing_yards,
            'points_scored': self.points_scored,
            'yards_per_game': self.yards_per_game,
            'points_per_game': self.points_per_game,
            'points_allowed': self.points_allowed,
            'yards_allowed': self.yards_allowed,
            'sacks': self.sacks,
            'interceptions': self.interceptions,
            'points_allowed_per_game': self.points_allowed_per_game,
            'turnovers': self.turnovers,
            'turnovers_forced': self.turnovers_forced,
            'turnover_margin': self.turnover_margin,
            'offense_rank': self.offense_rank,
            'defense_rank': self.defense_rank,
            'points_rank': self.points_rank,
        }


@dataclass
class LeagueRankings:
    """League-wide rankings for all stat categories."""

    season: int
    categories: Dict[str, List[Dict[str, Any]]]  # category -> [{rank, team_id, value}, ...]


class TeamStatsService:
    """
    Service for team statistics operations.

    Combines data from:
    - TeamSeasonStatsAPI: Season stat aggregations and rankings
    - BoxScoresAPI: Game-level team stats
    - StandingsAPI: Win/loss records

    Uses API classes only - no direct SQL queries.
    """

    # Stat categories with display names and sort order
    STAT_CATEGORIES = {
        # Offense (higher is better)
        'total_yards': {'name': 'Total Yards', 'ascending': False},
        'passing_yards': {'name': 'Passing Yards', 'ascending': False},
        'rushing_yards': {'name': 'Rushing Yards', 'ascending': False},
        'points_scored': {'name': 'Points Scored', 'ascending': False},

        # Defense (lower is better for some)
        'points_allowed': {'name': 'Points Allowed', 'ascending': True},
        'yards_allowed': {'name': 'Yards Allowed', 'ascending': True},
        'sacks': {'name': 'Sacks', 'ascending': False},
        'interceptions': {'name': 'Interceptions', 'ascending': False},

        # Turnovers
        'turnover_margin': {'name': 'Turnover Margin', 'ascending': False},
    }

    def __init__(
        self,
        db_path: str,
        dynasty_id: str,
        season: int
    ):
        """
        Initialize the team stats service.

        Args:
            db_path: Path to the database
            dynasty_id: Dynasty identifier
            season: Current season year
        """
        self._db_path = db_path
        self._dynasty_id = dynasty_id
        self._season = season
        self._logger = logging.getLogger(__name__)

        # Lazy-loaded API instances
        self._team_stats_api = None
        self._box_scores_api = None
        self._standings_api = None

    def _get_team_stats_api(self):
        """Lazy-load TeamSeasonStatsAPI."""
        if self._team_stats_api is None:
            from ..database.team_stats_api import TeamSeasonStatsAPI
            self._team_stats_api = TeamSeasonStatsAPI(self._db_path)
        return self._team_stats_api

    def _get_box_scores_api(self):
        """Lazy-load BoxScoresAPI."""
        if self._box_scores_api is None:
            from ..database.box_scores_api import BoxScoresAPI
            self._box_scores_api = BoxScoresAPI(self._db_path)
        return self._box_scores_api

    def _get_standings_api(self):
        """Lazy-load StandingsAPI."""
        if self._standings_api is None:
            from ..database.standings_api import StandingsAPI
            from ..database.connection import GameCycleDatabase
            db = GameCycleDatabase(self._db_path)
            self._standings_api = StandingsAPI(db)
        return self._standings_api

    # -------------------- Public Methods --------------------

    def get_team_overview(
        self,
        team_id: int,
        season: Optional[int] = None
    ) -> Optional[TeamOverview]:
        """
        Get comprehensive team overview combining stats and standings.

        Args:
            team_id: Team ID (1-32)
            season: Season year (defaults to service's season)

        Returns:
            TeamOverview with stats, record, and rankings
        """
        season = season or self._season

        # Get season stats
        stats_api = self._get_team_stats_api()
        stats = stats_api.get_team_season_stats(self._dynasty_id, team_id, season)

        if not stats:
            self._logger.debug(f"No stats found for team {team_id} in season {season}")
            return None

        # Get standings for record
        standings_api = self._get_standings_api()
        standing = standings_api.get_team_standing(self._dynasty_id, season, team_id)

        wins = standing.wins if standing else 0
        losses = standing.losses if standing else 0
        ties = standing.ties if standing else 0

        total_games = wins + losses + ties
        win_pct = wins / total_games if total_games > 0 else 0.0

        # Get rankings
        offense_rank = self._get_rank_for_team(team_id, season, 'total_yards')
        defense_rank = self._get_rank_for_team(team_id, season, 'yards_allowed')
        points_rank = self._get_rank_for_team(team_id, season, 'points_scored')

        return TeamOverview(
            team_id=team_id,
            season=season,
            wins=wins,
            losses=losses,
            ties=ties,
            win_pct=win_pct,
            total_yards=stats.total_yards,
            passing_yards=stats.passing_yards,
            rushing_yards=stats.rushing_yards,
            points_scored=stats.points_scored,
            yards_per_game=stats.yards_per_game,
            points_per_game=stats.points_per_game,
            points_allowed=stats.points_allowed,
            yards_allowed=stats.yards_allowed,
            sacks=stats.sacks,
            interceptions=stats.interceptions,
            points_allowed_per_game=stats.points_allowed_per_game,
            turnovers=stats.turnovers,
            turnovers_forced=stats.turnovers_forced,
            turnover_margin=stats.turnover_margin,
            offense_rank=offense_rank,
            defense_rank=defense_rank,
            points_rank=points_rank,
        )

    def get_league_rankings(
        self,
        season: Optional[int] = None,
        categories: Optional[List[str]] = None
    ) -> LeagueRankings:
        """
        Get league-wide rankings for all or specified stat categories.

        Args:
            season: Season year (defaults to service's season)
            categories: List of category keys to include (defaults to all)

        Returns:
            LeagueRankings with all teams ranked 1-32 per category
        """
        season = season or self._season
        categories = categories or list(self.STAT_CATEGORIES.keys())

        stats_api = self._get_team_stats_api()
        result_categories = {}

        for category in categories:
            if category not in self.STAT_CATEGORIES:
                continue

            config = self.STAT_CATEGORIES[category]
            rankings = stats_api.calculate_rankings(
                self._dynasty_id,
                season,
                category,
                ascending=config['ascending']
            )

            result_categories[category] = [
                {
                    'rank': r.rank,
                    'team_id': r.team_id,
                    'value': r.value,
                    'display_name': config['name'],
                }
                for r in rankings
            ]

        return LeagueRankings(season=season, categories=result_categories)

    def get_team_comparison(
        self,
        team1_id: int,
        team2_id: int,
        season: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get head-to-head comparison between two teams.

        Args:
            team1_id: First team ID
            team2_id: Second team ID
            season: Season year (defaults to service's season)

        Returns:
            Dict with both teams' stats side-by-side
        """
        season = season or self._season

        team1_overview = self.get_team_overview(team1_id, season)
        team2_overview = self.get_team_overview(team2_id, season)

        if not team1_overview or not team2_overview:
            return {
                'season': season,
                'team1': team1_overview.to_dict() if team1_overview else None,
                'team2': team2_overview.to_dict() if team2_overview else None,
                'comparison': None,
            }

        # Build comparison showing which team is better in each category
        comparison = {}
        comparisons = [
            ('total_yards', False),  # Higher is better
            ('passing_yards', False),
            ('rushing_yards', False),
            ('points_scored', False),
            ('points_allowed', True),  # Lower is better
            ('yards_allowed', True),
            ('sacks', False),
            ('interceptions', False),
            ('turnover_margin', False),
        ]

        for stat, lower_is_better in comparisons:
            val1 = getattr(team1_overview, stat)
            val2 = getattr(team2_overview, stat)

            if lower_is_better:
                advantage = team1_id if val1 < val2 else (team2_id if val2 < val1 else 0)
            else:
                advantage = team1_id if val1 > val2 else (team2_id if val2 > val1 else 0)

            comparison[stat] = {
                'team1_value': val1,
                'team2_value': val2,
                'advantage': advantage,  # 0 means tie
            }

        return {
            'season': season,
            'team1': team1_overview.to_dict(),
            'team2': team2_overview.to_dict(),
            'comparison': comparison,
        }

    def get_team_box_scores(
        self,
        team_id: int,
        season: Optional[int] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get game-by-game box scores for a team.

        Args:
            team_id: Team ID
            season: Season year (defaults to service's season)
            limit: Maximum number of games to return

        Returns:
            List of box score dicts ordered by week
        """
        season = season or self._season

        box_api = self._get_box_scores_api()
        box_scores = box_api.get_team_box_scores(
            self._dynasty_id, team_id, season=season, limit=limit
        )

        return [bs.to_dict() for bs in box_scores]

    # -------------------- Private Methods --------------------

    def _get_rank_for_team(
        self,
        team_id: int,
        season: int,
        stat_category: str
    ) -> int:
        """
        Get a team's rank for a specific stat category.

        Args:
            team_id: Team ID
            season: Season year
            stat_category: Stat category key

        Returns:
            Rank (1-32), or 0 if not found
        """
        config = self.STAT_CATEGORIES.get(stat_category, {})
        ascending = config.get('ascending', False)

        stats_api = self._get_team_stats_api()
        rankings = stats_api.calculate_rankings(
            self._dynasty_id,
            season,
            stat_category,
            ascending=ascending
        )

        for r in rankings:
            if r.team_id == team_id:
                return r.rank

        return 0