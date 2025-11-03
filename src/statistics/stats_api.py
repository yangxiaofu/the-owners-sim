"""
Main Statistics API for The Owner's Sim

Central entry point for all statistical queries.
Provides leader queries, player queries, team queries, and rankings.
"""
from typing import List, Dict, Any, Optional
from database.api import DatabaseAPI
from statistics.leaderboards import LeaderboardBuilder
from statistics.models import (
    PassingStats,
    RushingStats,
    ReceivingStats,
    DefensiveStats,
    SpecialTeamsStats,
    TeamStats,
)
from statistics.aggregations import (
    aggregate_team_stats,
    aggregate_all_teams,
    calculate_league_averages,
    compare_teams,
)
from statistics.filters import StatFilters
from statistics.rankings import (
    calculate_rankings,
    calculate_conference_rankings,
    calculate_division_rankings,
    add_all_rankings,
    get_percentile,
)


class StatsAPI:
    """
    Main Statistics API - Single entry point for all statistical queries.

    Architecture: UI → StatsAPI → DatabaseAPI → SQLite

    This is the primary interface for all statistical operations. UI controllers
    should NEVER access DatabaseAPI directly for stats - always use StatsAPI.
    """

    def __init__(self, db_path: str, dynasty_id: str):
        """
        Initialize Statistics API.

        Args:
            db_path: Path to SQLite database
            dynasty_id: Dynasty identifier for data isolation
        """
        self.db_path = db_path
        self.dynasty_id = dynasty_id
        self.db_api = DatabaseAPI(db_path)
        self.leaderboard_builder = LeaderboardBuilder(self.db_api)
        self._cache = {}  # Simple cache for expensive queries

    # === LEADER QUERIES (10 methods) ===

    def get_passing_leaders(
        self,
        season: int,
        limit: int = 25,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[PassingStats]:
        """
        Get passing leaders with calculated passer rating and rankings.

        Args:
            season: Season year
            limit: Number of leaders to return (default 25)
            filters: Optional filters:
                - 'conference': 'AFC' or 'NFC'
                - 'division': 'East', 'North', 'South', 'West'
                - 'min_attempts': Minimum pass attempts (e.g., 100)

        Returns:
            List of PassingStats with passer rating, rankings, etc.

        Example:
            api = StatsAPI('nfl.db', 'my_dynasty')
            leaders = api.get_passing_leaders(2025, limit=10, filters={'conference': 'AFC'})
        """
        return self.leaderboard_builder.build_passing_leaderboard(
            self.dynasty_id, season, limit, filters
        )

    def get_rushing_leaders(
        self,
        season: int,
        limit: int = 25,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[RushingStats]:
        """
        Get rushing leaders with yards per carry.

        Args:
            season: Season year
            limit: Number of leaders to return (default 25)
            filters: Optional filters (conference, division, min_attempts)

        Returns:
            List of RushingStats with calculated metrics
        """
        return self.leaderboard_builder.build_rushing_leaderboard(
            self.dynasty_id, season, limit, filters
        )

    def get_receiving_leaders(
        self,
        season: int,
        limit: int = 25,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[ReceivingStats]:
        """
        Get receiving leaders with catch rate, YPR, YPT.

        Args:
            season: Season year
            limit: Number of leaders to return (default 25)
            filters: Optional filters (conference, division, min_targets)

        Returns:
            List of ReceivingStats with calculated metrics
        """
        return self.leaderboard_builder.build_receiving_leaderboard(
            self.dynasty_id, season, limit, filters
        )

    def get_defensive_leaders(
        self,
        season: int,
        stat_category: str,  # 'tackles_total', 'sacks', 'interceptions'
        limit: int = 25,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[DefensiveStats]:
        """
        Get defensive leaders for specific stat category.

        Args:
            season: Season year
            stat_category: 'tackles_total', 'sacks', or 'interceptions'
            limit: Number of leaders to return (default 25)
            filters: Optional filters (conference, division)

        Returns:
            List of DefensiveStats sorted by stat_category
        """
        return self.leaderboard_builder.build_defensive_leaderboard(
            self.dynasty_id, season, stat_category, limit, filters
        )

    def get_special_teams_leaders(
        self,
        season: int,
        limit: int = 25,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[SpecialTeamsStats]:
        """
        Get special teams leaders (kickers).

        Args:
            season: Season year
            limit: Number of leaders to return (default 25)
            filters: Optional filters (conference, division, min_attempts)

        Returns:
            List of SpecialTeamsStats with FG%, XP%
        """
        return self.leaderboard_builder.build_special_teams_leaderboard(
            self.dynasty_id, season, limit, filters
        )

    def get_all_purpose_leaders(
        self,
        season: int,
        positions: List[str],  # ['RB', 'WR', 'TE']
        limit: int = 25,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all-purpose yards leaders (rushing + receiving + returns).

        Args:
            season: Season year
            positions: Positions to include (typically ['RB', 'WR', 'TE'])
            limit: Number of leaders
            filters: Optional filters

        Returns:
            List of player stats with combined all-purpose yards
        """
        # Get raw data from database
        raw_stats = self._get_all_player_stats(season)

        # Filter to specified positions
        ap_stats = StatFilters.filter_by_position(raw_stats, positions)

        # Apply additional filters if provided
        if filters:
            if 'conference' in filters:
                ap_stats = StatFilters.filter_by_conference(ap_stats, filters['conference'])
            if 'division' in filters:
                ap_stats = StatFilters.filter_by_division(ap_stats, filters['division'])

        # Calculate all-purpose yards
        for stat in ap_stats:
            stat['all_purpose_yards'] = (
                stat.get('rushing_yards', 0) +
                stat.get('receiving_yards', 0)
                # TODO: Add return yards when available
            )
            stat['yards_per_game'] = (
                stat.get('all_purpose_yards', 0) / stat.get('games', 1)
                if stat.get('games', 0) > 0 else 0.0
            )

        # Add rankings
        ap_stats = add_all_rankings(ap_stats, 'all_purpose_yards', ascending=False)

        # Sort and limit
        ap_stats.sort(key=lambda x: x.get('all_purpose_yards', 0), reverse=True)
        ap_stats = ap_stats[:limit]

        return ap_stats

    # === INDIVIDUAL PLAYER QUERIES (5 methods) ===

    def get_player_season_stats(
        self,
        player_id: str,
        season: int
    ) -> Dict[str, Any]:
        """
        Get complete season statistics for a player.

        Args:
            player_id: Player identifier
            season: Season year

        Returns:
            Dict with all stats and calculated metrics
        """
        # Get all stats for season
        all_stats = self._get_all_player_stats(season)

        # Find player
        player_stats = [s for s in all_stats if s['player_id'] == player_id]

        if not player_stats:
            return {}

        # Return first match (should be unique)
        stat = player_stats[0]

        # Add calculated metrics based on position
        if stat.get('position') == 'QB':
            stat['passer_rating'] = self._calculate_passer_rating(
                stat.get('passing_completions', 0),
                stat.get('passing_attempts', 0),
                stat.get('passing_yards', 0),
                stat.get('passing_touchdowns', 0),
                stat.get('passing_interceptions', 0)
            )
            stat['completion_pct'] = (
                (stat.get('passing_completions', 0) / stat.get('passing_attempts', 1)) * 100
                if stat.get('passing_attempts', 0) > 0 else 0.0
            )

        return stat

    def get_player_career_stats(self, player_id: str) -> Dict[str, Any]:
        """
        Get career totals across all seasons.

        Queries player_season_stats table for fast aggregation of career totals.
        This works with archived data - seasons beyond retention window are
        included via their summaries.

        Args:
            player_id: Player identifier

        Returns:
            Dict with career totals including:
            - seasons_played: Number of seasons
            - games_played: Total games across all seasons
            - career_passing_yards: Total passing yards
            - career_rushing_yards: Total rushing yards
            - career_receiving_yards: Total receiving yards
            - (and all other career totals)

        Example:
            >>> stats_api = StatsAPI(dynasty_id="my_dynasty")
            >>> career = stats_api.get_player_career_stats("QB_KC_001")
            >>> print(f"{career['seasons_played']} seasons, {career['career_passing_yards']} yards")
        """
        query = """
            SELECT
                COUNT(DISTINCT season) as seasons_played,
                SUM(games_played) as games_played,

                -- Career passing totals
                SUM(passing_yards) as career_passing_yards,
                SUM(passing_tds) as career_passing_tds,
                SUM(passing_completions) as career_passing_completions,
                SUM(passing_attempts) as career_passing_attempts,
                SUM(passing_interceptions) as career_interceptions,

                -- Career rushing totals
                SUM(rushing_yards) as career_rushing_yards,
                SUM(rushing_tds) as career_rushing_tds,
                SUM(rushing_attempts) as career_rushing_attempts,

                -- Career receiving totals
                SUM(receiving_yards) as career_receiving_yards,
                SUM(receiving_tds) as career_receiving_tds,
                SUM(receptions) as career_receptions,
                SUM(targets) as career_targets,

                -- Career defense totals
                SUM(tackles_total) as career_tackles,
                SUM(sacks) as career_sacks,
                SUM(interceptions) as career_interceptions_def,
                SUM(forced_fumbles) as career_forced_fumbles,

                -- Career special teams totals
                SUM(field_goals_made) as career_field_goals_made,
                SUM(field_goals_attempted) as career_field_goals_attempted,
                SUM(extra_points_made) as career_extra_points_made,
                SUM(extra_points_attempted) as career_extra_points_attempted,

                -- First and last season
                MIN(season) as rookie_season,
                MAX(season) as last_season

            FROM player_season_stats
            WHERE player_id = ? AND dynasty_id = ?
        """

        result = self.database_api.execute_query(query, (player_id, self.dynasty_id))

        if result and result[0]['seasons_played'] > 0:
            return dict(result[0])

        # Player not found or no seasons played
        return {
            'seasons_played': 0,
            'games_played': 0,
            'career_passing_yards': 0,
            'career_rushing_yards': 0,
            'career_receiving_yards': 0
        }

    def get_player_season_history(
        self,
        player_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get season-by-season breakdown for a player.

        Returns list of all seasons with stats and awards. Works with
        archived data - includes seasons beyond retention window.

        Args:
            player_id: Player identifier

        Returns:
            List of dicts with season stats, sorted by season (oldest first)

        Example:
            >>> stats_api = StatsAPI(dynasty_id="my_dynasty")
            >>> history = stats_api.get_player_season_history("QB_KC_001")
            >>> for season in history:
            ...     print(f"{season['season']}: {season['passing_yards']} yards")
        """
        query = """
            SELECT
                season,
                team_id,
                position,
                games_played,
                passing_yards,
                passing_tds,
                passing_attempts,
                passer_rating,
                rushing_yards,
                rushing_tds,
                rushing_attempts,
                yards_per_carry,
                receiving_yards,
                receiving_tds,
                receptions,
                catch_rate,
                tackles_total,
                sacks,
                interceptions,
                field_goals_made,
                field_goals_attempted
            FROM player_season_stats
            WHERE player_id = ? AND dynasty_id = ?
            ORDER BY season ASC
        """

        result = self.database_api.execute_query(query, (player_id, self.dynasty_id))

        return [dict(row) for row in result] if result else []

    def get_player_game_log(
        self,
        player_id: str,
        season: int,
        season_type: str = "regular_season"
    ) -> List[Dict[str, Any]]:
        """
        Get game-by-game stats for a player.

        NOTE: Only available for seasons within the retention window.
        Archived seasons (beyond retention) only have season summaries.

        Args:
            player_id: Player identifier
            season: Season year
            season_type: "preseason", "regular_season", or "playoffs" (default: "regular_season")

        Returns:
            List of game stats (empty if season is archived)
        """
        query = """
            SELECT
                pgs.game_id,
                g.game_date,
                g.week,
                pgs.passing_yards,
                pgs.passing_tds,
                pgs.rushing_yards,
                pgs.rushing_tds,
                pgs.receiving_yards,
                pgs.receiving_tds,
                pgs.tackles_total,
                pgs.sacks,
                pgs.interceptions
            FROM player_game_stats pgs
            JOIN games g ON pgs.game_id = g.game_id AND pgs.dynasty_id = g.dynasty_id
            WHERE pgs.player_id = ? AND pgs.dynasty_id = ? AND g.season = ? AND pgs.season_type = ?
            ORDER BY g.game_date ASC
        """

        result = self.database_api.execute_query(query, (player_id, self.dynasty_id, season, season_type))

        return [dict(row) for row in result] if result else []

    def get_player_splits(
        self,
        player_id: str,
        season: int,
        split_type: str  # 'home_away', 'by_opponent', 'by_week'
    ) -> Dict[str, Any]:
        """
        Get advanced splits for a player (future).

        Args:
            player_id: Player identifier
            season: Season year
            split_type: Type of split

        Returns:
            Dict with split stats
        """
        raise NotImplementedError("Player splits coming in future update")

    def get_player_rank(
        self,
        player_id: str,
        season: int,
        stat_category: str
    ) -> Dict[str, Any]:
        """
        Get player's rank in a specific stat category.

        Args:
            player_id: Player identifier
            season: Season year
            stat_category: Stat to rank by (e.g., 'passing_yards', 'rushing_yards')

        Returns:
            {
                'player_id': str,
                'stat_value': int,
                'league_rank': int,
                'conference_rank': int,
                'division_rank': int,
                'percentile': float
            }
        """
        # Get all stats
        all_stats = self._get_all_player_stats(season)

        # Find player
        player_stat = next((s for s in all_stats if s['player_id'] == player_id), None)

        if not player_stat:
            return {}

        # Add rankings
        all_stats = add_all_rankings(all_stats, stat_category, ascending=False)

        # Find player again (now with rankings)
        player_stat = next((s for s in all_stats if s['player_id'] == player_id), None)

        # Calculate percentile
        all_values = [s.get(stat_category, 0) for s in all_stats]
        percentile = get_percentile(player_stat.get(stat_category, 0), all_values)

        return {
            'player_id': player_id,
            'stat_value': player_stat.get(stat_category, 0),
            'league_rank': player_stat.get('league_rank'),
            'conference_rank': player_stat.get('conference_rank'),
            'division_rank': player_stat.get('division_rank'),
            'percentile': percentile,
        }

    # === TEAM QUERIES (5 methods) ===

    def get_team_stats(self, team_id: int, season: int) -> TeamStats:
        """
        Get aggregated team stats with rankings.

        Args:
            team_id: Team identifier (1-32)
            season: Season year

        Returns:
            TeamStats dataclass with aggregated stats
        """
        # Get all player stats
        all_stats = self._get_all_player_stats(season)

        # Aggregate for this team
        team_agg = aggregate_team_stats(all_stats, team_id)

        # Get all team stats for rankings
        all_team_stats = aggregate_all_teams(all_stats)

        # Calculate offensive ranking (by total passing + rushing yards)
        for t in all_team_stats:
            t['offensive_yards'] = t['total_passing_yards'] + t['total_rushing_yards']

        all_team_stats.sort(key=lambda x: x['offensive_yards'], reverse=True)
        offensive_rank = next((i + 1 for i, t in enumerate(all_team_stats) if t['team_id'] == team_id), None)

        # Calculate defensive ranking (by points allowed - would need defensive stats)
        # For now, set to None
        defensive_rank = None

        return TeamStats(
            team_id=team_id,
            season=season,
            dynasty_id=self.dynasty_id,
            total_passing_yards=team_agg['total_passing_yards'],
            total_rushing_yards=team_agg['total_rushing_yards'],
            total_points=team_agg['total_points_scored'],
            total_points_allowed=0,  # TODO: Add when defensive team stats available
            total_yards_allowed=0,  # TODO: Add when defensive team stats available
            offensive_rank=offensive_rank,
            defensive_rank=defensive_rank,
        )

    def get_team_rankings(
        self,
        team_id: int,
        season: int
    ) -> Dict[str, int]:
        """
        Get team rankings in all categories.

        Args:
            team_id: Team identifier
            season: Season year

        Returns:
            {
                'offensive_rank': int,
                'defensive_rank': int,
                'passing_rank': int,
                'rushing_rank': int,
            }
        """
        # Get all player stats
        all_stats = self._get_all_player_stats(season)

        # Aggregate all teams
        all_team_stats = aggregate_all_teams(all_stats)

        # Calculate rankings for different categories
        rankings = {}

        # Passing rank
        all_team_stats_sorted = sorted(all_team_stats, key=lambda x: x['total_passing_yards'], reverse=True)
        rankings['passing_rank'] = next((i + 1 for i, t in enumerate(all_team_stats_sorted) if t['team_id'] == team_id), None)

        # Rushing rank
        all_team_stats_sorted = sorted(all_team_stats, key=lambda x: x['total_rushing_yards'], reverse=True)
        rankings['rushing_rank'] = next((i + 1 for i, t in enumerate(all_team_stats_sorted) if t['team_id'] == team_id), None)

        # Offensive rank (total yards)
        for t in all_team_stats:
            t['offensive_yards'] = t['total_passing_yards'] + t['total_rushing_yards']
        all_team_stats_sorted = sorted(all_team_stats, key=lambda x: x['offensive_yards'], reverse=True)
        rankings['offensive_rank'] = next((i + 1 for i, t in enumerate(all_team_stats_sorted) if t['team_id'] == team_id), None)

        # Defensive rank (TODO: implement when defensive stats available)
        rankings['defensive_rank'] = None

        return rankings

    def get_all_team_stats(self, season: int) -> List[TeamStats]:
        """
        Get stats for all 32 teams.

        Args:
            season: Season year

        Returns:
            List of TeamStats for all teams
        """
        # Get all player stats
        all_stats = self._get_all_player_stats(season)

        # Aggregate all teams
        all_team_aggs = aggregate_all_teams(all_stats)

        # Convert to TeamStats dataclass
        return [
            TeamStats(
                team_id=t['team_id'],
                season=season,
                dynasty_id=self.dynasty_id,
                total_passing_yards=t['total_passing_yards'],
                total_rushing_yards=t['total_rushing_yards'],
                total_points=t['total_points_scored'],
                total_points_allowed=0,  # TODO
                total_yards_allowed=0,  # TODO
            )
            for t in all_team_aggs
        ]

    def compare_teams(
        self,
        team_id_1: int,
        team_id_2: int,
        season: int
    ) -> Dict[str, Any]:
        """
        Compare two teams statistically.

        Args:
            team_id_1: First team ID
            team_id_2: Second team ID
            season: Season year

        Returns:
            Dict with comparison data
        """
        # Get all player stats
        all_stats = self._get_all_player_stats(season)

        # Use aggregations module to compare
        return compare_teams(all_stats, team_id_1, team_id_2)

    def get_league_averages(self, season: int) -> Dict[str, float]:
        """
        Get league-wide statistical averages.

        Args:
            season: Season year

        Returns:
            Dict with league averages
        """
        # Get all player stats
        all_stats = self._get_all_player_stats(season)

        # Use aggregations module to calculate
        return calculate_league_averages(all_stats)

    def get_offensive_leaders(
        self,
        season: int,
        limit: int = 25,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get top offensive players (combined passing + rushing + receiving yards).

        Args:
            season: Season year
            limit: Number of leaders to return
            filters: Optional filters

        Returns:
            List of offensive leaders with total yards
        """
        # Get all player stats
        all_stats = self._get_all_player_stats(season)

        # Apply filters if provided
        if filters:
            if 'conference' in filters:
                all_stats = StatFilters.filter_by_conference(all_stats, filters['conference'])
            if 'division' in filters:
                all_stats = StatFilters.filter_by_division(all_stats, filters['division'])

        # Calculate total offensive yards
        for stat in all_stats:
            stat['total_offensive_yards'] = (
                stat.get('passing_yards', 0) +
                stat.get('rushing_yards', 0) +
                stat.get('receiving_yards', 0)
            )

        # Filter to players with offensive production
        all_stats = [s for s in all_stats if s.get('total_offensive_yards', 0) > 0]

        # Sort and limit
        all_stats.sort(key=lambda x: x.get('total_offensive_yards', 0), reverse=True)
        return all_stats[:limit]

    def get_touchdown_leaders(
        self,
        season: int,
        limit: int = 25,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get touchdown leaders (combined passing + rushing + receiving TDs).

        Args:
            season: Season year
            limit: Number of leaders to return
            filters: Optional filters

        Returns:
            List of touchdown leaders
        """
        # Get all player stats
        all_stats = self._get_all_player_stats(season)

        # Apply filters if provided
        if filters:
            if 'conference' in filters:
                all_stats = StatFilters.filter_by_conference(all_stats, filters['conference'])
            if 'division' in filters:
                all_stats = StatFilters.filter_by_division(all_stats, filters['division'])

        # Calculate total touchdowns
        for stat in all_stats:
            stat['total_touchdowns'] = (
                stat.get('passing_touchdowns', 0) +
                stat.get('rushing_touchdowns', 0) +
                stat.get('receiving_touchdowns', 0)
            )

        # Filter to players with TDs
        all_stats = [s for s in all_stats if s.get('total_touchdowns', 0) > 0]

        # Sort and limit
        all_stats.sort(key=lambda x: x.get('total_touchdowns', 0), reverse=True)
        return all_stats[:limit]

    def get_team_offensive_stats(
        self,
        team_id: int,
        season: int
    ) -> Dict[str, Any]:
        """
        Get detailed offensive stats for a team.

        Args:
            team_id: Team identifier
            season: Season year

        Returns:
            Dict with offensive stats breakdown
        """
        # Get all player stats
        all_stats = self._get_all_player_stats(season)

        # Aggregate for this team
        team_agg = aggregate_team_stats(all_stats, team_id)

        return team_agg

    def get_team_defensive_stats(
        self,
        team_id: int,
        season: int
    ) -> Dict[str, Any]:
        """
        Get defensive stats for a team.

        Args:
            team_id: Team identifier
            season: Season year

        Returns:
            Dict with defensive stats
        """
        # TODO: Implement when defensive team stats are available
        return {
            'team_id': team_id,
            'total_sacks': 0,
            'total_interceptions': 0,
            'total_tackles': 0,
        }

    def get_position_leaders(
        self,
        season: int,
        position: str,
        stat_category: str,
        limit: int = 25
    ) -> List[Dict[str, Any]]:
        """
        Get leaders for a specific position and stat category.

        Args:
            season: Season year
            position: Position filter (e.g., 'QB', 'RB', 'WR')
            stat_category: Stat to rank by
            limit: Number of leaders to return

        Returns:
            List of position leaders
        """
        # Get all player stats
        all_stats = self._get_all_player_stats(season)

        # Filter to position
        pos_stats = StatFilters.filter_by_position(all_stats, [position])

        # Filter to players with this stat
        pos_stats = [s for s in pos_stats if s.get(stat_category, 0) > 0]

        # Sort and limit
        pos_stats.sort(key=lambda x: x.get(stat_category, 0), reverse=True)
        return pos_stats[:limit]

    # === RANKING QUERIES (2 methods) ===

    def get_stat_rankings(
        self,
        season: int,
        stat_category: str,
        position: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get complete league rankings for any stat.

        Args:
            season: Season year
            stat_category: Stat to rank by (e.g., 'passing_yards', 'rushing_yards')
            position: Optional position filter

        Returns:
            List of all players ranked by stat
        """
        # Get all player stats
        all_stats = self._get_all_player_stats(season)

        # Filter by position if provided
        if position:
            all_stats = StatFilters.filter_by_position(all_stats, [position])

        # Add rankings
        all_stats = add_all_rankings(all_stats, stat_category, ascending=False)

        # Sort by league rank
        all_stats.sort(key=lambda x: x.get('league_rank', 999))

        return all_stats

    def get_conference_rankings(
        self,
        season: int,
        stat_category: str
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get AFC and NFC rankings separately.

        Args:
            season: Season year
            stat_category: Stat to rank by

        Returns:
            {
                'AFC': [...],
                'NFC': [...]
            }
        """
        # Get all player stats
        all_stats = self._get_all_player_stats(season)

        # Split by conference
        afc_stats = StatFilters.filter_by_conference(all_stats, 'AFC')
        nfc_stats = StatFilters.filter_by_conference(all_stats, 'NFC')

        # Add rankings for each conference
        afc_stats = calculate_rankings(afc_stats, stat_category, ascending=False)
        nfc_stats = calculate_rankings(nfc_stats, stat_category, ascending=False)

        return {
            'AFC': afc_stats,
            'NFC': nfc_stats,
        }

    # === ADVANCED QUERIES (2 methods - future) ===

    def get_red_zone_stats(
        self,
        season: int,
        limit: int = 25
    ) -> List[Dict[str, Any]]:
        """Get red zone performance stats (future implementation)"""
        raise NotImplementedError("Red zone stats coming in future update")

    def get_fourth_quarter_stats(
        self,
        season: int,
        limit: int = 25
    ) -> List[Dict[str, Any]]:
        """Get fourth quarter/clutch stats (future implementation)"""
        raise NotImplementedError("Fourth quarter stats coming in future update")

    # === PRIVATE HELPER METHODS ===

    def _get_all_player_stats(self, season: int, season_type: str = "regular_season") -> List[Dict[str, Any]]:
        """
        Get all player stats for a season from database.

        Args:
            season: Season year to filter stats
            season_type: "preseason", "regular_season", or "playoffs" (default: "regular_season")

        Returns:
            List of player stat dictionaries with season-filtered stats
        """
        # Query database for all player game stats
        # IMPORTANT: Must JOIN with games table to filter by season
        # Also filter by season_type to separate preseason/regular/playoffs
        query = '''
            SELECT
                pgs.player_id,
                pgs.player_name,
                pgs.team_id,
                pgs.position,
                COUNT(DISTINCT pgs.game_id) as games,
                SUM(pgs.passing_yards) as passing_yards,
                SUM(pgs.passing_tds) as passing_touchdowns,
                SUM(pgs.passing_completions) as passing_completions,
                SUM(pgs.passing_attempts) as passing_attempts,
                SUM(pgs.passing_interceptions) as passing_interceptions,
                SUM(pgs.rushing_yards) as rushing_yards,
                SUM(pgs.rushing_tds) as rushing_touchdowns,
                SUM(pgs.rushing_attempts) as rushing_attempts,
                SUM(pgs.receiving_yards) as receiving_yards,
                SUM(pgs.receiving_tds) as receiving_touchdowns,
                SUM(pgs.receptions) as receptions,
                SUM(pgs.targets) as targets,
                SUM(pgs.tackles_total) as tackles_total,
                SUM(pgs.sacks) as sacks,
                SUM(pgs.interceptions) as interceptions,
                SUM(pgs.field_goals_made) as field_goals_made,
                SUM(pgs.field_goals_attempted) as field_goals_attempted,
                SUM(pgs.extra_points_made) as extra_points_made,
                SUM(pgs.extra_points_attempted) as extra_points_attempted
            FROM player_game_stats pgs
            JOIN games g ON pgs.game_id = g.game_id AND pgs.dynasty_id = g.dynasty_id
            WHERE pgs.dynasty_id = ?
                AND g.season = ?
                AND pgs.season_type = ?
            GROUP BY pgs.player_id, pgs.player_name, pgs.team_id, pgs.position
        '''

        results = self.db_api.db_connection.execute_query(query, (self.dynasty_id, season, season_type))

        # Already converted to list of dicts by execute_query()
        return results

    def _calculate_passer_rating(
        self,
        completions: int,
        attempts: int,
        yards: int,
        touchdowns: int,
        interceptions: int
    ) -> float:
        """
        Calculate NFL passer rating.

        Formula:
            a = ((completions / attempts) - 0.3) * 5
            b = ((yards / attempts) - 3) * 0.25
            c = (touchdowns / attempts) * 20
            d = 2.375 - ((interceptions / attempts) * 25)

            rating = ((a + b + c + d) / 6) * 100

        Returns:
            Passer rating (0.0 to 158.3)
        """
        if attempts == 0:
            return 0.0

        # Component A: Completion percentage
        a = ((completions / attempts) - 0.3) * 5
        a = max(0, min(2.375, a))  # Clamp to [0, 2.375]

        # Component B: Yards per attempt
        b = ((yards / attempts) - 3) * 0.25
        b = max(0, min(2.375, b))

        # Component C: Touchdown percentage
        c = (touchdowns / attempts) * 20
        c = max(0, min(2.375, c))

        # Component D: Interception percentage
        d = 2.375 - ((interceptions / attempts) * 25)
        d = max(0, min(2.375, d))

        # Final rating
        rating = ((a + b + c + d) / 6) * 100

        return rating
