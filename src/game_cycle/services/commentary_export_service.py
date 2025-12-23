"""
Commentary Export Service for AI Tools

Exports current league context as JSON for feeding into AI commentary tools.

Includes:
- Current standings and playoff picture
- Power rankings with narrative blurbs
- Statistical leaders (top 10 per category)
- Upcoming games and recent results
- User team matchup preview with H2H history
- Team performance trends

Part of Game Cycle services layer.
"""

import json
import logging
import sqlite3
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.game_cycle.database.connection import GameCycleDatabase
from src.game_cycle.database.standings_api import StandingsAPI, TeamStanding
from src.game_cycle.database.schedule_api import ScheduleAPI, ScheduledGame
from src.game_cycle.database.box_scores_api import BoxScoresAPI
from src.game_cycle.database.player_stats_api import PlayerSeasonStatsAPI
from src.game_cycle.database.team_stats_api import TeamSeasonStatsAPI
from src.game_cycle.database.head_to_head_api import HeadToHeadAPI
from src.game_cycle.services.power_rankings_service import PowerRankingsService

logger = logging.getLogger(__name__)


@dataclass
class CommentaryExportResult:
    """Result metadata for commentary export."""
    dynasty_id: str
    season: int
    week: int
    stage_type: str
    export_timestamp: str
    file_path: str
    file_size_bytes: int
    success: bool = True
    error_message: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


class CommentaryExportService:
    """
    Service for exporting current league context as JSON for AI commentary tools.

    Aggregates data from multiple database APIs into a comprehensive JSON export
    that can be fed into AI tools for generating commentary, analysis, and insights.

    Features:
    - Current week standings and playoff picture
    - Power rankings with blurbs
    - Statistical leaders (top 10 per category)
    - Upcoming games and recent results
    - User team matchup preview with H2H history
    - Team performance trends

    Directory Structure:
        data/exports/{dynasty_id}/
            week_{week}/
                commentary_context.json  # Main export
                metadata.json             # Export metadata
    """

    # Stat categories to export (category_name, position_filter, sql_column)
    STAT_CATEGORIES = [
        ('passing_yards', ['QB'], 'passing_yards'),
        ('passing_tds', ['QB'], 'passing_tds'),
        ('rushing_yards', ['RB', 'FB', 'QB'], 'rushing_yards'),
        ('rushing_tds', ['RB', 'FB', 'QB'], 'rushing_tds'),
        ('receiving_yards', ['WR', 'TE', 'RB'], 'receiving_yards'),
        ('receiving_tds', ['WR', 'TE', 'RB'], 'receiving_tds'),
        ('receptions', ['WR', 'TE', 'RB'], 'receptions'),
        ('sacks', ['LE', 'RE', 'DT', 'LOLB', 'ROLB', 'MLB', 'EDGE'], 'sacks'),
        ('interceptions', ['CB', 'FS', 'SS', 'LOLB', 'ROLB', 'MLB'], 'interceptions'),
        ('tackles_total', ['CB', 'FS', 'SS', 'LOLB', 'ROLB', 'MLB', 'LE', 'RE', 'DT'], 'tackles_total'),
    ]

    # Division mappings
    DIVISIONS = {
        'AFC East': [1, 2, 3, 4],      # Bills, Dolphins, Patriots, Jets
        'AFC North': [5, 6, 7, 8],     # Ravens, Bengals, Browns, Steelers
        'AFC South': [9, 10, 11, 12],  # Texans, Colts, Jaguars, Titans
        'AFC West': [13, 14, 15, 16],  # Broncos, Chiefs, Raiders, Chargers
        'NFC East': [17, 18, 19, 20],  # Cowboys, Giants, Eagles, Commanders
        'NFC North': [21, 22, 23, 24], # Bears, Lions, Packers, Vikings
        'NFC South': [25, 26, 27, 28], # Falcons, Panthers, Saints, Buccaneers
        'NFC West': [29, 30, 31, 32],  # Cardinals, Rams, 49ers, Seahawks
    }

    def __init__(self, db_path: str, exports_root: Optional[str] = None):
        """
        Initialize the export service.

        Args:
            db_path: Path to the game_cycle database
            exports_root: Root directory for exports (default: data/exports)
        """
        self.db_path = db_path

        if exports_root:
            self.exports_root = Path(exports_root)
        else:
            # Default to data/exports relative to database location
            self.exports_root = Path(db_path).parent.parent.parent / "exports"

        # Lazy-loaded APIs (initialized on first use)
        self._db = None
        self._standings_api = None
        self._schedule_api = None
        self._box_scores_api = None
        self._player_stats_api = None
        self._team_stats_api = None
        self._power_rankings_service = None
        self._h2h_api = None

        # Team data cache
        self._teams_data = None

    # ==================== Lazy Loading Properties ====================

    @property
    def db(self) -> GameCycleDatabase:
        """Lazy-load database connection."""
        if self._db is None:
            self._db = GameCycleDatabase(self.db_path)
        return self._db

    @property
    def standings_api(self) -> StandingsAPI:
        """Lazy-load StandingsAPI."""
        if self._standings_api is None:
            self._standings_api = StandingsAPI(self.db)
        return self._standings_api

    @property
    def schedule_api(self) -> ScheduleAPI:
        """Lazy-load ScheduleAPI."""
        if self._schedule_api is None:
            self._schedule_api = ScheduleAPI(self.db)
        return self._schedule_api

    @property
    def box_scores_api(self) -> BoxScoresAPI:
        """Lazy-load BoxScoresAPI."""
        if self._box_scores_api is None:
            self._box_scores_api = BoxScoresAPI(self.db_path)
        return self._box_scores_api

    @property
    def player_stats_api(self) -> PlayerSeasonStatsAPI:
        """Lazy-load PlayerSeasonStatsAPI."""
        if self._player_stats_api is None:
            self._player_stats_api = PlayerSeasonStatsAPI(self.db_path)
        return self._player_stats_api

    @property
    def team_stats_api(self) -> TeamSeasonStatsAPI:
        """Lazy-load TeamSeasonStatsAPI."""
        if self._team_stats_api is None:
            self._team_stats_api = TeamSeasonStatsAPI(self.db_path)
        return self._team_stats_api

    @property
    def h2h_api(self) -> HeadToHeadAPI:
        """Lazy-load HeadToHeadAPI."""
        if self._h2h_api is None:
            self._h2h_api = HeadToHeadAPI(self.db)
        return self._h2h_api

    # ==================== Team Info Helper ====================

    def _load_teams_data(self) -> Dict[int, Dict[str, Any]]:
        """Load team information from JSON."""
        if self._teams_data is not None:
            return self._teams_data

        teams_file = Path(__file__).parent.parent.parent / "data" / "teams.json"
        try:
            with open(teams_file) as f:
                data = json.load(f)
                # Convert string keys to int
                self._teams_data = {int(k): v for k, v in data.get("teams", {}).items()}
                return self._teams_data
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.warning(f"Could not load teams.json: {e}")
            self._teams_data = {}
            return self._teams_data

    def _get_team_info(self, team_id: int) -> Dict[str, str]:
        """
        Get team metadata.

        Args:
            team_id: Team ID (1-32)

        Returns:
            Dict with team_id, city, nickname, full_name, abbreviation
        """
        teams_data = self._load_teams_data()
        team = teams_data.get(team_id, {})
        return {
            'team_id': team_id,
            'city': team.get('city', 'Unknown'),
            'nickname': team.get('nickname', f'Team {team_id}'),
            'full_name': team.get('full_name', f'Team {team_id}'),
            'abbreviation': team.get('abbreviation', f'T{team_id:02d}')
        }

    # ==================== File Management ====================

    def _get_export_dir(self, dynasty_id: str, week: int) -> Path:
        """
        Get the export directory for a dynasty/week.

        Args:
            dynasty_id: Dynasty identifier
            week: Week number

        Returns:
            Path to export directory
        """
        return self.exports_root / dynasty_id / f"week_{week}"

    def _write_export(self, export_dir: Path, context: dict) -> Path:
        """
        Write JSON export to file.

        Args:
            export_dir: Directory to write to
            context: Full context dict

        Returns:
            Path to written commentary_context.json file
        """
        export_dir.mkdir(parents=True, exist_ok=True)

        # Write main context
        context_path = export_dir / "commentary_context.json"
        with open(context_path, 'w', encoding='utf-8') as f:
            json.dump(context, f, indent=2, ensure_ascii=False)

        # Write metadata
        metadata = {
            "export_version": "1.0",
            "export_timestamp": context['metadata']['export_timestamp'],
            "dynasty_id": context['metadata']['dynasty_id'],
            "season": context['metadata']['season'],
            "week": context['metadata']['week'],
            "file_size_bytes": context_path.stat().st_size
        }

        metadata_path = export_dir / "metadata.json"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)

        logger.info(f"Exported commentary context to {context_path}")
        return context_path

    # ==================== Data Aggregation Methods ====================

    def _aggregate_standings(self, dynasty_id: str, season: int) -> Dict[str, List[Dict]]:
        """
        Aggregate standings organized by division.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year

        Returns:
            Dict with division names as keys, list of team standings as values
        """
        try:
            all_standings = self.standings_api.get_standings(dynasty_id, season)

            # Organize by division
            standings_by_division = {}

            for division_name, team_ids in self.DIVISIONS.items():
                division_standings = []

                for team_id in team_ids:
                    # Find this team's standing
                    standing = next((s for s in all_standings if s.team_id == team_id), None)
                    if standing:
                        team_info = self._get_team_info(team_id)
                        division_standings.append({
                            'team_id': team_id,
                            'team_name': team_info['full_name'],
                            'city': team_info['city'],
                            'abbreviation': team_info['abbreviation'],
                            'wins': standing.wins,
                            'losses': standing.losses,
                            'ties': standing.ties,
                            'win_pct': round(standing.win_percentage, 3),
                            'points_for': standing.points_for,
                            'points_against': standing.points_against,
                            'point_differential': standing.point_differential,
                            'division_record': f"{standing.division_wins}-{standing.division_losses}",
                            'conference_record': f"{standing.conference_wins}-{standing.conference_losses}"
                        })

                # Sort by wins (descending), then by point differential
                division_standings.sort(key=lambda x: (x['wins'], x['point_differential']), reverse=True)
                standings_by_division[division_name] = division_standings

            return standings_by_division

        except Exception as e:
            logger.warning(f"Failed to aggregate standings: {e}")
            return {}

    def _build_playoff_picture(self, standings_by_division: Dict[str, List[Dict]]) -> Dict[str, Dict]:
        """
        Determine current playoff seeding and bubble teams.

        Args:
            standings_by_division: Standings organized by division

        Returns:
            Dict with 'afc' and 'nfc' playoff pictures
        """
        try:
            playoff_picture = {'afc': {}, 'nfc': {}}

            # Get all AFC and NFC teams
            afc_teams = []
            nfc_teams = []

            for division_name, teams in standings_by_division.items():
                if 'AFC' in division_name:
                    afc_teams.extend(teams)
                else:
                    nfc_teams.extend(teams)

            # Sort by wins, then point differential
            afc_teams.sort(key=lambda x: (x['wins'], x['point_differential']), reverse=True)
            nfc_teams.sort(key=lambda x: (x['wins'], x['point_differential']), reverse=True)

            # Top 7 are in playoffs, next 5 are bubble
            for conference, teams in [('afc', afc_teams), ('nfc', nfc_teams)]:
                in_playoffs = []
                for i, team in enumerate(teams[:7], start=1):
                    in_playoffs.append({
                        'seed': i,
                        'team_id': team['team_id'],
                        'team_name': team['team_name'],
                        'record': f"{team['wins']}-{team['losses']}" + (f"-{team['ties']}" if team['ties'] > 0 else "")
                    })

                on_bubble = []
                for team in teams[7:12]:
                    games_back = teams[6]['wins'] - team['wins'] if len(teams) > 7 else 0
                    on_bubble.append({
                        'team_id': team['team_id'],
                        'team_name': team['team_name'],
                        'record': f"{team['wins']}-{team['losses']}" + (f"-{team['ties']}" if team['ties'] > 0 else ""),
                        'games_back': games_back
                    })

                playoff_picture[conference] = {
                    'in_playoffs': in_playoffs,
                    'on_bubble': on_bubble
                }

            return playoff_picture

        except Exception as e:
            logger.warning(f"Failed to build playoff picture: {e}")
            return {'afc': {'in_playoffs': [], 'on_bubble': []}, 'nfc': {'in_playoffs': [], 'on_bubble': []}}

    def _get_power_rankings(self, dynasty_id: str, season: int, week: int) -> List[Dict]:
        """
        Get current week's power rankings.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            week: Week number

        Returns:
            List of power ranking dicts
        """
        try:
            # Initialize power rankings service
            if self._power_rankings_service is None:
                self._power_rankings_service = PowerRankingsService(self.db_path, dynasty_id, season)

            rankings = self._power_rankings_service.get_rankings(week)

            result = []
            for ranking in rankings:
                team_info = self._get_team_info(ranking.team_id)

                # Calculate trend arrow
                trend = "—"
                if ranking.previous_rank:
                    movement = ranking.previous_rank - ranking.rank
                    if movement > 0:
                        trend = f"↑{movement}"
                    elif movement < 0:
                        trend = f"↓{abs(movement)}"

                result.append({
                    'rank': ranking.rank,
                    'team_id': ranking.team_id,
                    'team_name': team_info['full_name'],
                    'tier': ranking.tier,
                    'trend': trend,
                    'blurb': ranking.blurb
                })

            return result

        except Exception as e:
            logger.warning(f"Failed to get power rankings: {e}")
            return []

    def _query_stat_leaders(
        self,
        dynasty_id: str,
        season: int,
        category: str,
        position_filters: List[str],
        limit: int = 10
    ) -> List[Dict]:
        """
        Query top N players for a stat category.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            category: Stat column name (e.g., 'passing_yards')
            position_filters: List of position names to filter (e.g., ['QB'])
            limit: Number of leaders to return

        Returns:
            List of player stat leader dicts
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row

            # Build position filter clause
            position_clause = ""
            if position_filters:
                # Map position abbreviations to full names used in database
                position_map = {
                    'QB': 'quarterback', 'RB': 'running back', 'FB': 'fullback',
                    'WR': 'wide receiver', 'TE': 'tight end',
                    'LE': 'left end', 'RE': 'right end', 'DT': 'defensive tackle',
                    'LOLB': 'left outside linebacker', 'MLB': 'middle linebacker',
                    'ROLB': 'right outside linebacker', 'CB': 'cornerback',
                    'FS': 'free safety', 'SS': 'strong safety', 'EDGE': 'edge'
                }

                full_positions = [position_map.get(p, p.lower()) for p in position_filters]
                placeholders = ','.join(['?' for _ in full_positions])
                position_clause = f"AND pgs.position IN ({placeholders})"

            query = f"""
                SELECT
                    pgs.player_id,
                    pgs.player_name,
                    pgs.team_id,
                    pgs.position,
                    SUM(pgs.{category}) as stat_value,
                    COUNT(DISTINCT pgs.game_id) as games_played
                FROM player_game_stats pgs
                INNER JOIN games g ON pgs.game_id = g.game_id AND pgs.dynasty_id = g.dynasty_id
                WHERE pgs.dynasty_id = ?
                    AND g.season = ?
                    AND pgs.season_type = 'regular_season'
                    {position_clause}
                GROUP BY pgs.player_id, pgs.player_name, pgs.team_id, pgs.position
                HAVING SUM(pgs.{category}) > 0
                ORDER BY stat_value DESC
                LIMIT ?
            """

            # Build params
            params = [dynasty_id, season]
            if position_filters:
                params.extend(full_positions)
            params.append(limit)

            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            conn.close()

            leaders = []
            for i, row in enumerate(rows, start=1):
                team_info = self._get_team_info(row['team_id'])
                leaders.append({
                    'rank': i,
                    'player_id': row['player_id'],
                    'player_name': row['player_name'],
                    'team_id': row['team_id'],
                    'team_name': team_info['full_name'],
                    'position': row['position'],
                    'value': row['stat_value'],
                    'games_played': row['games_played']
                })

            return leaders

        except Exception as e:
            logger.warning(f"Failed to query stat leaders for {category}: {e}")
            return []

    def _get_stat_leaders(self, dynasty_id: str, season: int) -> Dict[str, List[Dict]]:
        """
        Get top 10 leaders in each statistical category.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year

        Returns:
            Dict with category names as keys, list of leaders as values
        """
        stat_leaders = {}

        for category_name, position_filters, sql_column in self.STAT_CATEGORIES:
            leaders = self._query_stat_leaders(
                dynasty_id, season, sql_column, position_filters, limit=10
            )
            if leaders:
                stat_leaders[category_name] = leaders

        return stat_leaders

    # ==================== Schedule & Games Methods ====================

    def _get_upcoming_games(
        self,
        dynasty_id: str,
        season: int,
        week: int
    ) -> Dict[str, List[Dict]]:
        """
        Get current week's scheduled games.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            week: Current week number

        Returns:
            Dict with week key and list of upcoming games
        """
        try:
            # Get games for current week
            games = self.schedule_api.get_games_by_week(dynasty_id, season, week)

            upcoming = []
            for game in games:
                if not game.is_played:
                    away_info = self._get_team_info(game.away_team_id)
                    home_info = self._get_team_info(game.home_team_id)

                    # Get records from standings
                    standings = self.standings_api.get_standings(dynasty_id, season)
                    away_standing = next((s for s in standings if s.team_id == game.away_team_id), None)
                    home_standing = next((s for s in standings if s.team_id == game.home_team_id), None)

                    upcoming.append({
                        'game_id': game.id,
                        'away_team': {
                            'id': game.away_team_id,
                            'name': away_info['full_name'],
                            'record': f"{away_standing.wins}-{away_standing.losses}" if away_standing else "0-0"
                        },
                        'home_team': {
                            'id': game.home_team_id,
                            'name': home_info['full_name'],
                            'record': f"{home_standing.wins}-{home_standing.losses}" if home_standing else "0-0"
                        },
                        'is_divisional': game.is_divisional,
                        'is_conference': game.is_conference
                    })

            return {f"week_{week}": upcoming}

        except Exception as e:
            logger.warning(f"Failed to get upcoming games: {e}")
            return {}

    def _get_recent_results(
        self,
        dynasty_id: str,
        season: int,
        week: int
    ) -> Dict[str, List[Dict]]:
        """
        Get previous week's completed games with scores.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            week: Current week number

        Returns:
            Dict with previous week key and list of results
        """
        if week <= 1:
            return {}  # No recent results for Week 1

        try:
            # Get games from previous week
            prev_week = week - 1
            games = self.schedule_api.get_games_by_week(dynasty_id, season, prev_week)

            results = []
            for game in games:
                if game.is_played and game.home_score is not None and game.away_score is not None:
                    away_info = self._get_team_info(game.away_team_id)
                    home_info = self._get_team_info(game.home_team_id)

                    results.append({
                        'game_id': game.id,
                        'away_team': {
                            'id': game.away_team_id,
                            'name': away_info['full_name'],
                            'score': game.away_score
                        },
                        'home_team': {
                            'id': game.home_team_id,
                            'name': home_info['full_name'],
                            'score': game.home_score
                        },
                        'is_divisional': game.is_divisional
                    })

            return {f"week_{prev_week}": results}

        except Exception as e:
            logger.warning(f"Failed to get recent results: {e}")
            return {}

    # ==================== User Team Focus Methods ====================

    def _build_user_team_focus(
        self,
        dynasty_id: str,
        season: int,
        week: int,
        user_team_id: int,
        context: Dict
    ) -> Dict:
        """
        Build detailed user team context with matchup preview.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            week: Current week number
            user_team_id: User's team ID
            context: Full context dict (for accessing power rankings, etc.)

        Returns:
            Dict with current_week_game, last_week_result, team_stats
        """
        focus = {}

        # Get current week's game
        current_game = self._get_user_team_game(dynasty_id, season, week, user_team_id)
        if current_game:
            focus['current_week_game'] = current_game
        else:
            focus['current_week_game'] = {'status': 'BYE_WEEK', 'message': 'Team has a bye week'}

        # Get last week's result
        last_week = self._get_last_week_result(dynasty_id, season, week, user_team_id)
        if last_week:
            focus['last_week_result'] = last_week

        # Get team stats
        focus['team_stats'] = self._get_user_team_stats(dynasty_id, season, user_team_id)

        return focus

    def _get_user_team_game(
        self,
        dynasty_id: str,
        season: int,
        week: int,
        user_team_id: int
    ) -> Optional[Dict]:
        """Find user's team game for current week."""
        try:
            games = self.schedule_api.get_games_by_week(dynasty_id, season, week)

            for game in games:
                if game.home_team_id == user_team_id or game.away_team_id == user_team_id:
                    if not game.is_played:
                        # Found user's upcoming game
                        opponent_id = game.away_team_id if game.home_team_id == user_team_id else game.home_team_id
                        location = 'home' if game.home_team_id == user_team_id else 'away'

                        # Get opponent analysis
                        opponent = self._analyze_opponent(dynasty_id, season, week, opponent_id)

                        # Get H2H history
                        h2h = self._get_matchup_history(dynasty_id, user_team_id, opponent_id)

                        return {
                            'game_id': game.id,
                            'week': week,
                            'opponent': opponent,
                            'location': location,
                            'matchup_history': h2h
                        }

            return None  # No game found (bye week)

        except Exception as e:
            logger.warning(f"Failed to get user team game: {e}")
            return None

    def _analyze_opponent(
        self,
        dynasty_id: str,
        season: int,
        week: int,
        opponent_id: int
    ) -> Dict:
        """Build opponent profile for matchup preview."""
        try:
            opponent_info = self._get_team_info(opponent_id)

            # Get opponent's record
            standings = self.standings_api.get_standings(dynasty_id, season)
            opp_standing = next((s for s in standings if s.team_id == opponent_id), None)

            # Get opponent's stats
            opp_stats = self.team_stats_api.get_team_season_stats(dynasty_id, opponent_id, season)

            # Get last 5 games record
            last_5 = self._get_last_n_games_record(dynasty_id, season, opponent_id, 5)

            return {
                'team_id': opponent_id,
                'team_name': opponent_info['full_name'],
                'record': f"{opp_standing.wins}-{opp_standing.losses}" if opp_standing else "0-0",
                'last_5_games': last_5,
                'points_per_game': round(opp_stats.points_per_game, 1) if opp_stats else 0,
                'points_allowed_per_game': round(opp_stats.points_allowed_per_game, 1) if opp_stats else 0,
            }

        except Exception as e:
            logger.warning(f"Failed to analyze opponent: {e}")
            return {}

    def _get_matchup_history(
        self,
        dynasty_id: str,
        user_team_id: int,
        opponent_id: int
    ) -> Dict:
        """Retrieve H2H history between teams."""
        try:
            record = self.h2h_api.get_record(dynasty_id, user_team_id, opponent_id)

            if record:
                user_wins = record.team_a_wins if record.team_a_id == user_team_id else record.team_b_wins
                opp_wins = record.team_b_wins if record.team_a_id == user_team_id else record.team_a_wins

                return {
                    'all_time': {
                        'wins': user_wins,
                        'losses': opp_wins,
                        'last_meeting_season': record.last_meeting_season
                    }
                }

            return {'all_time': {'wins': 0, 'losses': 0, 'last_meeting_season': None}}

        except Exception as e:
            logger.warning(f"Failed to get matchup history: {e}")
            return {}

    def _get_last_week_result(
        self,
        dynasty_id: str,
        season: int,
        week: int,
        user_team_id: int
    ) -> Optional[Dict]:
        """Get user's previous game result."""
        if week <= 1:
            return None  # No previous week

        try:
            prev_week = week - 1
            games = self.schedule_api.get_games_by_week(dynasty_id, season, prev_week)

            for game in games:
                if game.is_played and (game.home_team_id == user_team_id or game.away_team_id == user_team_id):
                    is_home = game.home_team_id == user_team_id
                    user_score = game.home_score if is_home else game.away_score
                    opp_score = game.away_score if is_home else game.home_score
                    opponent_id = game.away_team_id if is_home else game.home_team_id

                    opp_info = self._get_team_info(opponent_id)
                    result = 'W' if user_score > opp_score else ('L' if opp_score > user_score else 'T')

                    # Get box scores for key stats
                    box_scores = self.box_scores_api.get_game_box_scores(dynasty_id, game.id)
                    user_box = next((b for b in box_scores if b.team_id == user_team_id), None)
                    opp_box = next((b for b in box_scores if b.team_id == opponent_id), None)

                    key_stats = {}
                    if user_box and opp_box:
                        key_stats = {
                            'total_yards': {'user': user_box.total_yards, 'opponent': opp_box.total_yards},
                            'turnovers': {
                                'user': user_box.turnovers_lost,
                                'opponent': opp_box.turnovers_lost
                            }
                        }

                    return {
                        'game_id': game.id,
                        'week': prev_week,
                        'opponent': {'id': opponent_id, 'name': opp_info['full_name'], 'score': opp_score},
                        'user_team_score': user_score,
                        'result': result,
                        'key_stats': key_stats
                    }

            return None

        except Exception as e:
            logger.warning(f"Failed to get last week result: {e}")
            return None

    def _get_user_team_stats(
        self,
        dynasty_id: str,
        season: int,
        user_team_id: int
    ) -> Dict:
        """Get user team's season stats."""
        try:
            stats = self.team_stats_api.get_team_season_stats(dynasty_id, user_team_id, season)

            # Get current streak
            streak = self._get_current_streak(dynasty_id, season, user_team_id)

            return {
                'season_stats': {
                    'total_yards_per_game': round(stats.yards_per_game, 1) if stats else 0,
                    'points_per_game': round(stats.points_per_game, 1) if stats else 0,
                    'points_allowed_per_game': round(stats.points_allowed_per_game, 1) if stats else 0,
                    'turnover_margin': stats.turnover_margin if stats else 0,
                },
                'streak': streak
            }

        except Exception as e:
            logger.warning(f"Failed to get user team stats: {e}")
            return {}

    # ==================== Team Trends Methods ====================

    def _calculate_team_trends(
        self,
        dynasty_id: str,
        season: int,
        week: int
    ) -> List[Dict]:
        """Calculate recent performance trends for all teams."""
        try:
            standings = self.standings_api.get_standings(dynasty_id, season)
            trends = []

            for standing in standings:
                last_5 = self._get_last_n_games_record(dynasty_id, season, standing.team_id, 5)
                team_info = self._get_team_info(standing.team_id)

                # Determine trend (hot/cold/neutral)
                wins_in_5 = int(last_5.split('-')[0]) if last_5 else 0
                trend = 'hot' if wins_in_5 >= 4 else ('cold' if wins_in_5 <= 1 else 'neutral')

                trends.append({
                    'team_id': standing.team_id,
                    'team_name': team_info['full_name'],
                    'trend': trend,
                    'last_5': last_5
                })

            return trends

        except Exception as e:
            logger.warning(f"Failed to calculate team trends: {e}")
            return []

    # ==================== Helper Methods ====================

    def _get_last_n_games_record(
        self,
        dynasty_id: str,
        season: int,
        team_id: int,
        n: int
    ) -> str:
        """Get team's record in last N games."""
        try:
            box_scores = self.box_scores_api.get_team_box_scores(
                dynasty_id=dynasty_id,
                team_id=team_id,
                season=season,
                limit=n
            )

            wins = 0
            losses = 0

            for box in box_scores:
                game_boxes = self.box_scores_api.get_game_box_scores(dynasty_id, box.game_id)
                our_score = box.total_score
                opp_score = next((b.total_score for b in game_boxes if b.team_id != team_id), 0)

                if our_score > opp_score:
                    wins += 1
                elif opp_score > our_score:
                    losses += 1

            return f"{wins}-{losses}"

        except Exception as e:
            logger.warning(f"Failed to get last {n} games record: {e}")
            return "0-0"

    def _get_current_streak(
        self,
        dynasty_id: str,
        season: int,
        team_id: int
    ) -> Dict:
        """Get team's current win/loss streak."""
        try:
            box_scores = self.box_scores_api.get_team_box_scores(
                dynasty_id=dynasty_id,
                team_id=team_id,
                season=season,
                limit=10
            )

            if not box_scores:
                return {'type': None, 'count': 0}

            streak_type = None
            streak_count = 0

            for box in box_scores:
                game_boxes = self.box_scores_api.get_game_box_scores(dynasty_id, box.game_id)
                our_score = box.total_score
                opp_score = next((b.total_score for b in game_boxes if b.team_id != team_id), 0)

                result = 'W' if our_score > opp_score else ('L' if opp_score > our_score else 'T')

                if streak_type is None:
                    streak_type = result
                    streak_count = 1
                elif result == streak_type:
                    streak_count += 1
                else:
                    break

            return {'type': streak_type, 'count': streak_count}

        except Exception as e:
            logger.warning(f"Failed to get current streak: {e}")
            return {'type': None, 'count': 0}

    # ==================== Main Export Method ====================

    def export_commentary_context(
        self,
        dynasty_id: str,
        season: int,
        week: int,
        stage_type: str,
        user_team_id: int
    ) -> CommentaryExportResult:
        """
        Export current week's league context to JSON.

        Args:
            dynasty_id: Dynasty identifier
            season: Current season year
            week: Current week number (1-18 regular, 1-4 playoffs)
            stage_type: StageType name (e.g., "REGULAR_WEEK_8")
            user_team_id: User's team ID (1-32)

        Returns:
            CommentaryExportResult with export details
        """
        result = CommentaryExportResult(
            dynasty_id=dynasty_id,
            season=season,
            week=week,
            stage_type=stage_type,
            export_timestamp=datetime.now().isoformat(),
            file_path="",
            file_size_bytes=0
        )

        try:
            logger.info(f"Exporting commentary context for {dynasty_id}, Week {week}")

            # Get user team info
            user_team_info = self._get_team_info(user_team_id)

            # Build context dict
            context = {
                'metadata': {
                    'dynasty_id': dynasty_id,
                    'season': season,
                    'week': week,
                    'stage_type': stage_type,
                    'export_timestamp': result.export_timestamp,
                    'user_team_id': user_team_id,
                    'user_team_name': user_team_info['full_name']
                },
                'standings': {},
                'playoff_picture': {},
                'power_rankings': [],
                'stat_leaders': {},
                'upcoming_games': {},
                'recent_results': {},
                'user_team_focus': {},
                'team_trends': []
            }

            # Populate all sections
            context['standings'] = self._aggregate_standings(dynasty_id, season)
            context['playoff_picture'] = self._build_playoff_picture(context['standings'])
            context['power_rankings'] = self._get_power_rankings(dynasty_id, season, week)
            context['stat_leaders'] = self._get_stat_leaders(dynasty_id, season)
            context['upcoming_games'] = self._get_upcoming_games(dynasty_id, season, week)
            context['recent_results'] = self._get_recent_results(dynasty_id, season, week)
            context['user_team_focus'] = self._build_user_team_focus(
                dynasty_id, season, week, user_team_id, context
            )
            context['team_trends'] = self._calculate_team_trends(dynasty_id, season, week)

            # Write export to file
            export_dir = self._get_export_dir(dynasty_id, week)
            file_path = self._write_export(export_dir, context)

            # Update result
            result.file_path = str(file_path)
            result.file_size_bytes = file_path.stat().st_size
            result.success = True

            logger.info(f"Export complete: {result.file_size_bytes / 1024:.1f} KB")

        except Exception as e:
            logger.error(f"Export failed: {e}", exc_info=True)
            result.success = False
            result.error_message = str(e)

        return result
