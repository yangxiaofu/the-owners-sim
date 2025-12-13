"""
Team Statistics API for game_cycle.

Handles team-level statistics aggregation from player_game_stats.
"""

from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any
import sqlite3


@dataclass
class TeamSeasonStats:
    """Represents a team's aggregated season statistics."""

    team_id: int
    season: int
    games_played: int

    # Offensive stats
    total_yards: int
    passing_yards: int
    rushing_yards: int
    first_downs: int  # Not tracked in mock mode, will be 0
    third_down_attempts: int  # Not tracked in mock mode
    third_down_conversions: int  # Not tracked in mock mode
    points_scored: int

    # Defensive stats (opponent's offense)
    points_allowed: int
    yards_allowed: int
    passing_yards_allowed: int
    rushing_yards_allowed: int
    sacks: float
    tackles_for_loss: int  # Not directly tracked
    interceptions: int
    passes_defended: int
    forced_fumbles: int
    fumbles_recovered: int
    defensive_tds: int  # Calculated from turnovers returned for TD

    # Special teams
    field_goals_made: int
    field_goals_attempted: int
    extra_points_made: int
    extra_points_attempted: int
    punt_return_yards: int  # Not tracked in mock mode
    punt_return_tds: int  # Not tracked in mock mode
    kick_return_yards: int  # Not tracked in mock mode
    kick_return_tds: int  # Not tracked in mock mode

    # Turnovers
    interceptions_thrown: int
    fumbles_lost: int
    turnovers: int
    turnovers_forced: int
    turnover_margin: int

    @property
    def yards_per_game(self) -> float:
        """Calculate yards per game."""
        return self.total_yards / self.games_played if self.games_played else 0.0

    @property
    def points_per_game(self) -> float:
        """Calculate points per game."""
        return self.points_scored / self.games_played if self.games_played else 0.0

    @property
    def points_allowed_per_game(self) -> float:
        """Calculate points allowed per game."""
        return self.points_allowed / self.games_played if self.games_played else 0.0

    @property
    def third_down_pct(self) -> float:
        """Calculate third down conversion percentage."""
        if self.third_down_attempts == 0:
            return 0.0
        return (self.third_down_conversions / self.third_down_attempts) * 100

    @property
    def field_goal_pct(self) -> float:
        """Calculate field goal percentage."""
        if self.field_goals_attempted == 0:
            return 0.0
        return (self.field_goals_made / self.field_goals_attempted) * 100

    @property
    def extra_point_pct(self) -> float:
        """Calculate extra point percentage."""
        if self.extra_points_attempted == 0:
            return 0.0
        return (self.extra_points_made / self.extra_points_attempted) * 100

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary including calculated properties."""
        result = asdict(self)
        result['yards_per_game'] = self.yards_per_game
        result['points_per_game'] = self.points_per_game
        result['points_allowed_per_game'] = self.points_allowed_per_game
        result['third_down_pct'] = self.third_down_pct
        result['field_goal_pct'] = self.field_goal_pct
        result['extra_point_pct'] = self.extra_point_pct
        return result


@dataclass
class TeamRanking:
    """Represents a team's ranking for a specific stat category."""

    rank: int
    team_id: int
    value: float


class TeamSeasonStatsAPI:
    """
    API for team season statistics operations.

    Aggregates player-level stats from player_game_stats into team totals.

    Handles:
    - Querying team season stats by dynasty/team/season
    - Calculating league-wide rankings (1-32)
    - Getting per-game team stats
    """

    def __init__(self, db_path: str):
        """
        Initialize with database path.

        Args:
            db_path: Path to SQLite database
        """
        self._db_path = db_path

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _query_one(self, sql: str, params: tuple = ()) -> Optional[sqlite3.Row]:
        """Execute query and return single row."""
        conn = self._get_connection()
        try:
            cursor = conn.execute(sql, params)
            return cursor.fetchone()
        finally:
            conn.close()

    def _query_all(self, sql: str, params: tuple = ()) -> list:
        """Execute query and return all rows."""
        conn = self._get_connection()
        try:
            cursor = conn.execute(sql, params)
            return cursor.fetchall()
        finally:
            conn.close()

    # -------------------- Query Methods --------------------

    def get_team_season_stats(
        self,
        dynasty_id: str,
        team_id: int,
        season: int,
        season_type: str = 'regular_season'
    ) -> Optional[TeamSeasonStats]:
        """
        Get aggregated season statistics for a single team.

        Args:
            dynasty_id: Dynasty identifier
            team_id: Team ID (1-32)
            season: Season year
            season_type: 'regular_season' or 'playoffs'

        Returns:
            TeamSeasonStats or None if no games played
        """
        # Get offensive stats (team's own players)
        offensive = self._get_offensive_stats(dynasty_id, team_id, season, season_type)
        if offensive is None:
            return None

        # Get defensive stats (opponent's players)
        defensive = self._get_defensive_stats(dynasty_id, team_id, season, season_type)

        # Get points scored/allowed from games table
        points = self._get_points_stats(dynasty_id, team_id, season, season_type)

        # Get turnover stats (team's own turnovers)
        turnovers_committed = self._get_turnovers_committed(
            dynasty_id, team_id, season, season_type
        )

        return TeamSeasonStats(
            team_id=team_id,
            season=season,
            games_played=offensive['games_played'],
            # Offensive
            total_yards=offensive['passing_yards'] + offensive['rushing_yards'],
            passing_yards=offensive['passing_yards'],
            rushing_yards=offensive['rushing_yards'],
            first_downs=0,  # Not tracked in mock mode
            third_down_attempts=0,
            third_down_conversions=0,
            points_scored=points['points_scored'],
            # Defensive
            points_allowed=points['points_allowed'],
            yards_allowed=defensive['yards_allowed'],
            passing_yards_allowed=defensive['passing_yards_allowed'],
            rushing_yards_allowed=defensive['rushing_yards_allowed'],
            sacks=offensive['sacks'],  # Defense sacks come from team's own defensive players
            tackles_for_loss=0,  # Not directly tracked
            interceptions=offensive['interceptions'],  # Team's defensive INTs
            passes_defended=offensive['passes_defended'],
            forced_fumbles=offensive['forced_fumbles'],
            fumbles_recovered=offensive['fumbles_recovered'],
            defensive_tds=0,  # Not tracked in mock mode
            # Special teams
            field_goals_made=offensive['field_goals_made'],
            field_goals_attempted=offensive['field_goals_attempted'],
            extra_points_made=offensive['extra_points_made'],
            extra_points_attempted=offensive['extra_points_attempted'],
            punt_return_yards=0,
            punt_return_tds=0,
            kick_return_yards=0,
            kick_return_tds=0,
            # Turnovers
            interceptions_thrown=turnovers_committed['interceptions_thrown'],
            fumbles_lost=turnovers_committed['fumbles_lost'],
            turnovers=turnovers_committed['turnovers'],
            turnovers_forced=offensive['interceptions'] + offensive['fumbles_recovered'],
            turnover_margin=(
                offensive['interceptions'] + offensive['fumbles_recovered'] -
                turnovers_committed['turnovers']
            ),
        )

    def get_all_teams_season_stats(
        self,
        dynasty_id: str,
        season: int,
        season_type: str = 'regular_season'
    ) -> List[TeamSeasonStats]:
        """
        Get season statistics for all 32 teams.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            season_type: 'regular_season' or 'playoffs'

        Returns:
            List of TeamSeasonStats for all teams with games played
        """
        # Get all teams that have played games
        teams_with_games = self._query_all(
            """SELECT DISTINCT team_id FROM player_game_stats pgs
               JOIN games g ON pgs.game_id = g.game_id AND pgs.dynasty_id = g.dynasty_id
               WHERE pgs.dynasty_id = ? AND g.season = ? AND pgs.season_type = ?""",
            (dynasty_id, season, season_type)
        )

        results = []
        for row in teams_with_games:
            stats = self.get_team_season_stats(
                dynasty_id, row['team_id'], season, season_type
            )
            if stats:
                results.append(stats)

        # Sort by total yards descending
        results.sort(key=lambda x: x.total_yards, reverse=True)
        return results

    def get_team_game_stats(
        self,
        dynasty_id: str,
        team_id: int,
        game_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get team statistics for a single game.

        Args:
            dynasty_id: Dynasty identifier
            team_id: Team ID (1-32)
            game_id: Game identifier

        Returns:
            Dict with team stats for that game, or None if not found
        """
        # Aggregate team's player stats for this game
        row = self._query_one(
            """SELECT
                   SUM(passing_yards) as passing_yards,
                   SUM(rushing_yards) as rushing_yards,
                   SUM(passing_tds) as passing_tds,
                   SUM(rushing_tds) as rushing_tds,
                   SUM(receiving_tds) as receiving_tds,
                   SUM(passing_interceptions) as interceptions_thrown,
                   SUM(rushing_fumbles) as fumbles_lost,
                   SUM(sacks) as sacks,
                   SUM(interceptions) as interceptions,
                   SUM(passes_defended) as passes_defended,
                   SUM(forced_fumbles) as forced_fumbles,
                   SUM(fumbles_recovered) as fumbles_recovered,
                   SUM(field_goals_made) as field_goals_made,
                   SUM(field_goals_attempted) as field_goals_attempted
               FROM player_game_stats
               WHERE dynasty_id = ? AND team_id = ? AND game_id = ?""",
            (dynasty_id, team_id, game_id)
        )

        if not row or row['passing_yards'] is None:
            return None

        return {
            'game_id': game_id,
            'team_id': team_id,
            'passing_yards': row['passing_yards'] or 0,
            'rushing_yards': row['rushing_yards'] or 0,
            'total_yards': (row['passing_yards'] or 0) + (row['rushing_yards'] or 0),
            'passing_tds': row['passing_tds'] or 0,
            'rushing_tds': row['rushing_tds'] or 0,
            'total_tds': (row['passing_tds'] or 0) + (row['rushing_tds'] or 0) + (row['receiving_tds'] or 0),
            'interceptions_thrown': row['interceptions_thrown'] or 0,
            'fumbles_lost': row['fumbles_lost'] or 0,
            'sacks': row['sacks'] or 0,
            'interceptions': row['interceptions'] or 0,
            'passes_defended': row['passes_defended'] or 0,
            'forced_fumbles': row['forced_fumbles'] or 0,
            'fumbles_recovered': row['fumbles_recovered'] or 0,
            'field_goals_made': row['field_goals_made'] or 0,
            'field_goals_attempted': row['field_goals_attempted'] or 0,
        }

    def calculate_rankings(
        self,
        dynasty_id: str,
        season: int,
        stat_category: str,
        ascending: bool = False,
        season_type: str = 'regular_season'
    ) -> List[TeamRanking]:
        """
        Calculate team rankings (1-32) for a specific stat category.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            stat_category: One of 'total_yards', 'passing_yards', 'rushing_yards',
                          'points_scored', 'points_allowed', 'yards_allowed',
                          'passing_yards_allowed', 'rushing_yards_allowed',
                          'sacks', 'interceptions', 'turnover_margin', 'field_goal_pct'
            ascending: If True, lower values rank higher (for defensive stats)
            season_type: 'regular_season' or 'playoffs'

        Returns:
            List of TeamRanking ordered by rank (1 = best)
        """
        all_stats = self.get_all_teams_season_stats(dynasty_id, season, season_type)

        if not all_stats:
            return []

        # Get the value for each team
        team_values = []
        for stats in all_stats:
            value = self._get_stat_value(stats, stat_category)
            team_values.append((stats.team_id, value))

        # Sort by value (ascending or descending based on stat type)
        team_values.sort(key=lambda x: x[1], reverse=not ascending)

        # Create rankings
        rankings = []
        for rank, (team_id, value) in enumerate(team_values, start=1):
            rankings.append(TeamRanking(rank=rank, team_id=team_id, value=value))

        return rankings

    # -------------------- Private Methods --------------------

    def _get_offensive_stats(
        self,
        dynasty_id: str,
        team_id: int,
        season: int,
        season_type: str
    ) -> Optional[Dict[str, Any]]:
        """Get aggregated offensive stats for a team."""
        row = self._query_one(
            """SELECT
                   COUNT(DISTINCT pgs.game_id) as games_played,
                   SUM(pgs.passing_yards) as passing_yards,
                   SUM(pgs.rushing_yards) as rushing_yards,
                   SUM(pgs.passing_tds) as passing_tds,
                   SUM(pgs.rushing_tds) as rushing_tds,
                   SUM(pgs.receiving_tds) as receiving_tds,
                   SUM(pgs.sacks) as sacks,
                   SUM(pgs.interceptions) as interceptions,
                   SUM(pgs.passes_defended) as passes_defended,
                   SUM(pgs.forced_fumbles) as forced_fumbles,
                   SUM(pgs.fumbles_recovered) as fumbles_recovered,
                   SUM(pgs.field_goals_made) as field_goals_made,
                   SUM(pgs.field_goals_attempted) as field_goals_attempted,
                   SUM(pgs.extra_points_made) as extra_points_made,
                   SUM(pgs.extra_points_attempted) as extra_points_attempted
               FROM player_game_stats pgs
               JOIN games g ON pgs.game_id = g.game_id AND pgs.dynasty_id = g.dynasty_id
               WHERE pgs.dynasty_id = ?
                 AND pgs.team_id = ?
                 AND g.season = ?
                 AND pgs.season_type = ?""",
            (dynasty_id, team_id, season, season_type)
        )

        if not row or row['games_played'] == 0:
            return None

        return {
            'games_played': row['games_played'],
            'passing_yards': row['passing_yards'] or 0,
            'rushing_yards': row['rushing_yards'] or 0,
            'passing_tds': row['passing_tds'] or 0,
            'rushing_tds': row['rushing_tds'] or 0,
            'receiving_tds': row['receiving_tds'] or 0,
            'sacks': row['sacks'] or 0,
            'interceptions': row['interceptions'] or 0,
            'passes_defended': row['passes_defended'] or 0,
            'forced_fumbles': row['forced_fumbles'] or 0,
            'fumbles_recovered': row['fumbles_recovered'] or 0,
            'field_goals_made': row['field_goals_made'] or 0,
            'field_goals_attempted': row['field_goals_attempted'] or 0,
            'extra_points_made': row['extra_points_made'] or 0,
            'extra_points_attempted': row['extra_points_attempted'] or 0,
        }

    def _get_defensive_stats(
        self,
        dynasty_id: str,
        team_id: int,
        season: int,
        season_type: str
    ) -> Dict[str, Any]:
        """
        Get defensive stats (opponent's offensive output against this team).

        This aggregates the offensive stats of opponent players in games
        where team_id was playing.
        """
        # Get opponent's offensive stats in games involving this team
        row = self._query_one(
            """SELECT
                   SUM(pgs.passing_yards) as passing_yards_allowed,
                   SUM(pgs.rushing_yards) as rushing_yards_allowed
               FROM player_game_stats pgs
               JOIN games g ON pgs.game_id = g.game_id AND pgs.dynasty_id = g.dynasty_id
               WHERE pgs.dynasty_id = ?
                 AND g.season = ?
                 AND pgs.season_type = ?
                 AND pgs.team_id != ?
                 AND (g.home_team_id = ? OR g.away_team_id = ?)""",
            (dynasty_id, season, season_type, team_id, team_id, team_id)
        )

        return {
            'yards_allowed': (row['passing_yards_allowed'] or 0) + (row['rushing_yards_allowed'] or 0),
            'passing_yards_allowed': row['passing_yards_allowed'] or 0,
            'rushing_yards_allowed': row['rushing_yards_allowed'] or 0,
        }

    def _get_points_stats(
        self,
        dynasty_id: str,
        team_id: int,
        season: int,
        season_type: str
    ) -> Dict[str, int]:
        """Get points scored and allowed from games table."""
        # Points when home
        home_row = self._query_one(
            """SELECT
                   SUM(home_score) as points_scored,
                   SUM(away_score) as points_allowed
               FROM games
               WHERE dynasty_id = ?
                 AND season = ?
                 AND season_type = ?
                 AND home_team_id = ?""",
            (dynasty_id, season, season_type, team_id)
        )

        # Points when away
        away_row = self._query_one(
            """SELECT
                   SUM(away_score) as points_scored,
                   SUM(home_score) as points_allowed
               FROM games
               WHERE dynasty_id = ?
                 AND season = ?
                 AND season_type = ?
                 AND away_team_id = ?""",
            (dynasty_id, season, season_type, team_id)
        )

        points_scored = (
            (home_row['points_scored'] or 0) +
            (away_row['points_scored'] or 0)
        )
        points_allowed = (
            (home_row['points_allowed'] or 0) +
            (away_row['points_allowed'] or 0)
        )

        return {
            'points_scored': points_scored,
            'points_allowed': points_allowed,
        }

    def _get_turnovers_committed(
        self,
        dynasty_id: str,
        team_id: int,
        season: int,
        season_type: str
    ) -> Dict[str, int]:
        """Get turnovers committed by team (INTs thrown + fumbles lost)."""
        row = self._query_one(
            """SELECT
                   SUM(pgs.passing_interceptions) as interceptions_thrown,
                   SUM(pgs.rushing_fumbles) as fumbles_lost
               FROM player_game_stats pgs
               JOIN games g ON pgs.game_id = g.game_id AND pgs.dynasty_id = g.dynasty_id
               WHERE pgs.dynasty_id = ?
                 AND pgs.team_id = ?
                 AND g.season = ?
                 AND pgs.season_type = ?""",
            (dynasty_id, team_id, season, season_type)
        )

        interceptions_thrown = row['interceptions_thrown'] or 0
        fumbles_lost = row['fumbles_lost'] or 0

        return {
            'interceptions_thrown': interceptions_thrown,
            'fumbles_lost': fumbles_lost,
            'turnovers': interceptions_thrown + fumbles_lost,
        }

    def _get_stat_value(self, stats: TeamSeasonStats, category: str) -> float:
        """Get the value for a specific stat category."""
        category_map = {
            'total_yards': stats.total_yards,
            'passing_yards': stats.passing_yards,
            'rushing_yards': stats.rushing_yards,
            'points_scored': stats.points_scored,
            'points_allowed': stats.points_allowed,
            'yards_allowed': stats.yards_allowed,
            'passing_yards_allowed': stats.passing_yards_allowed,
            'rushing_yards_allowed': stats.rushing_yards_allowed,
            'sacks': stats.sacks,
            'interceptions': stats.interceptions,
            'turnover_margin': stats.turnover_margin,
            'field_goal_pct': stats.field_goal_pct,
            'yards_per_game': stats.yards_per_game,
            'points_per_game': stats.points_per_game,
            'points_allowed_per_game': stats.points_allowed_per_game,
        }

        return category_map.get(category, 0)