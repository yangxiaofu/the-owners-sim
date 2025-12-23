"""
Team Context Builder Service.

Builds rich team context for social media posts and other systems.
Aggregates team record, rankings, playoff position, season phase, and recent activity.
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional

from src.game_cycle.database.connection import GameCycleDatabase
from src.game_cycle.database.standings_api import StandingsAPI
from src.utils.team_utils import get_team_name


logger = logging.getLogger(__name__)


class PlayoffPosition(Enum):
    """Team's current playoff position/status."""
    CLINCHED = "clinched"  # Clinched playoff spot
    IN_HUNT = "in_hunt"  # In playoff contention
    ELIMINATED = "eliminated"  # Eliminated from playoffs
    LEADER = "leader"  # Division leader
    UNKNOWN = "unknown"  # Status unknown (early season)


class SeasonPhase(Enum):
    """Phase of the season based on week number."""
    EARLY = "early"  # Weeks 1-6
    MID = "mid"  # Weeks 7-12
    LATE = "late"  # Weeks 13-18
    PLAYOFFS = "playoffs"  # Postseason


@dataclass
class RecentActivity:
    """Recent team activity (trades, signings, cuts)."""
    trades: List[Dict]  # Recent trades (last 2 weeks)
    signings: List[Dict]  # Recent FA signings (last 2 weeks)
    cuts: List[Dict]  # Recent roster cuts (last 2 weeks)


@dataclass
class TeamContext:
    """
    Rich context about a team for social media generation.

    Contains:
    - Record and win percentage
    - Division and conference rankings
    - Playoff position/status
    - Current season phase
    - Recent transactions
    - Win/loss streak
    """
    team_id: int
    team_name: str
    season: int
    week: Optional[int]

    # Record
    wins: int
    losses: int
    ties: int
    win_pct: float

    # Rankings
    division_rank: int
    conference_rank: int

    # Playoff position
    playoff_position: PlayoffPosition

    # Season phase
    season_phase: SeasonPhase

    # Recent activity
    recent_trades: List[Dict]
    recent_signings: List[Dict]
    recent_cuts: List[Dict]

    # Streaks
    current_streak: int  # Positive = wins, negative = losses
    streak_type: str  # 'W' or 'L'

    def get_record_string(self) -> str:
        """Get record as string (e.g., '10-4-0', '8-8-1')."""
        return f"{self.wins}-{self.losses}-{self.ties}"

    def is_winning_record(self) -> bool:
        """Check if team has a winning record."""
        return self.win_pct > 0.500

    def is_playoff_team(self) -> bool:
        """Check if team is in playoff position."""
        return self.playoff_position in (PlayoffPosition.CLINCHED, PlayoffPosition.LEADER)

    def has_recent_activity(self) -> bool:
        """Check if team has any recent transactions."""
        return bool(self.recent_trades or self.recent_signings or self.recent_cuts)

    def get_streak_string(self) -> str:
        """Get streak as string (e.g., 'W3', 'L2')."""
        if self.current_streak == 0:
            return ""
        return f"{self.streak_type}{abs(self.current_streak)}"


class TeamContextBuilder:
    """
    Builds rich team context for social media posts.

    Uses StandingsAPI and database queries to aggregate:
    - Team record and rankings
    - Playoff position
    - Season phase
    - Recent transactions (last 2 weeks)
    - Win/loss streaks
    """

    def __init__(self, db: GameCycleDatabase):
        """
        Initialize the context builder.

        Args:
            db: GameCycleDatabase instance
        """
        self.db = db
        self.standings_api = StandingsAPI(db)
        self._teams_json = self._load_teams_json()

    def build_context(
        self,
        dynasty_id: str,
        season: int,
        team_id: int,
        week: Optional[int] = None
    ) -> TeamContext:
        """
        Build complete team context.

        Args:
            dynasty_id: Dynasty identifier
            season: Current season
            team_id: Team ID (1-32)
            week: Current week (1-18), None for offseason/playoffs

        Returns:
            TeamContext with all fields populated

        Raises:
            ValueError: If team_id is invalid or standings not found
        """
        logger.debug(f"Building context for team {team_id}, season {season}, week {week}")

        # Get team standing
        standing = self.standings_api.get_team_standing(
            dynasty_id=dynasty_id,
            season=season,
            team_id=team_id
        )

        if not standing:
            raise ValueError(
                f"No standings found for team {team_id} in season {season}"
            )

        # Get team name
        team_name = get_team_name(team_id)

        # Calculate rankings
        division_rank = self._calculate_division_rank(dynasty_id, season, team_id)
        conference_rank = self._calculate_conference_rank(dynasty_id, season, team_id)

        # Determine playoff position
        playoff_position = self._determine_playoff_position(
            standing=standing,
            division_rank=division_rank,
            conference_rank=conference_rank,
            week=week
        )

        # Determine season phase
        season_phase = self._determine_season_phase(week)

        # Get recent activity (last 2 weeks)
        recent_activity = self._get_recent_activity(dynasty_id, season, team_id, week)

        # Calculate streak
        current_streak, streak_type = self._calculate_streak(dynasty_id, season, team_id)

        return TeamContext(
            team_id=team_id,
            team_name=team_name,
            season=season,
            week=week,
            wins=standing.wins,
            losses=standing.losses,
            ties=standing.ties,
            win_pct=standing.win_percentage,
            division_rank=division_rank,
            conference_rank=conference_rank,
            playoff_position=playoff_position,
            season_phase=season_phase,
            recent_trades=recent_activity.trades,
            recent_signings=recent_activity.signings,
            recent_cuts=recent_activity.cuts,
            current_streak=current_streak,
            streak_type=streak_type
        )

    # =========================================================================
    # Rankings Calculation
    # =========================================================================

    def _calculate_division_rank(
        self,
        dynasty_id: str,
        season: int,
        team_id: int
    ) -> int:
        """
        Calculate team's rank within their division.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            team_id: Team ID

        Returns:
            Division rank (1-4)
        """
        # Get team's division
        division = self._get_team_division(team_id)
        if not division:
            logger.warning(f"Could not determine division for team {team_id}")
            return 1

        # Get all teams in division
        division_team_ids = self._get_division_teams(division['conference'], division['division'])

        # Get standings for all division teams
        division_standings = []
        for div_team_id in division_team_ids:
            standing = self.standings_api.get_team_standing(
                dynasty_id=dynasty_id,
                season=season,
                team_id=div_team_id
            )
            if standing:
                division_standings.append(standing)

        # Sort by win percentage (descending)
        division_standings.sort(
            key=lambda s: (s.win_percentage, s.wins, s.point_differential),
            reverse=True
        )

        # Find team's rank
        for rank, standing in enumerate(division_standings, start=1):
            if standing.team_id == team_id:
                return rank

        return 1  # Default to 1st if not found

    def _calculate_conference_rank(
        self,
        dynasty_id: str,
        season: int,
        team_id: int
    ) -> int:
        """
        Calculate team's rank within their conference.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            team_id: Team ID

        Returns:
            Conference rank (1-16)
        """
        # Get team's conference
        team_info = self._get_team_info(team_id)
        if not team_info:
            logger.warning(f"Could not determine conference for team {team_id}")
            return 1

        conference = team_info.get('conference', 'AFC')

        # Get all teams in conference
        from src.constants.team_ids import TeamIDs
        conference_team_ids = TeamIDs.get_conference_teams(conference)

        # Get standings for all conference teams
        conference_standings = []
        for conf_team_id in conference_team_ids:
            standing = self.standings_api.get_team_standing(
                dynasty_id=dynasty_id,
                season=season,
                team_id=conf_team_id
            )
            if standing:
                conference_standings.append(standing)

        # Sort by win percentage (descending)
        conference_standings.sort(
            key=lambda s: (s.win_percentage, s.wins, s.point_differential),
            reverse=True
        )

        # Find team's rank
        for rank, standing in enumerate(conference_standings, start=1):
            if standing.team_id == team_id:
                return rank

        return 1  # Default to 1st if not found

    # =========================================================================
    # Playoff Position
    # =========================================================================

    def _determine_playoff_position(
        self,
        standing,
        division_rank: int,
        conference_rank: int,
        week: Optional[int]
    ) -> PlayoffPosition:
        """
        Determine team's playoff position/status.

        Args:
            standing: TeamStanding object
            division_rank: Team's division rank
            conference_rank: Team's conference rank
            week: Current week (None for playoffs/offseason)

        Returns:
            PlayoffPosition enum value
        """
        # Playoffs or offseason - use playoff_seed if set
        if week is None:
            if standing.playoff_seed and standing.playoff_seed <= 7:
                return PlayoffPosition.CLINCHED
            return PlayoffPosition.UNKNOWN

        # Early season (weeks 1-6) - too early to tell
        if week <= 6:
            if division_rank == 1:
                return PlayoffPosition.LEADER
            return PlayoffPosition.UNKNOWN

        # Mid-late season - determine based on standings
        # Division leaders automatically in
        if division_rank == 1:
            if week >= 15 and standing.win_percentage >= 0.750:
                return PlayoffPosition.CLINCHED
            return PlayoffPosition.LEADER

        # Top 7 in conference are playoff teams
        if conference_rank <= 7:
            if week >= 15 and conference_rank <= 4:
                return PlayoffPosition.CLINCHED
            return PlayoffPosition.IN_HUNT

        # Eliminated if mathematically out (simplified heuristic)
        if week >= 15 and standing.win_percentage < 0.350:
            return PlayoffPosition.ELIMINATED

        # Week 17-18: stricter elimination
        if week >= 17 and conference_rank > 10:
            return PlayoffPosition.ELIMINATED

        return PlayoffPosition.IN_HUNT

    # =========================================================================
    # Season Phase
    # =========================================================================

    def _determine_season_phase(self, week: Optional[int]) -> SeasonPhase:
        """
        Determine current season phase based on week.

        Args:
            week: Current week (1-18), None for playoffs/offseason

        Returns:
            SeasonPhase enum value
        """
        if week is None:
            return SeasonPhase.PLAYOFFS

        if week <= 6:
            return SeasonPhase.EARLY
        elif week <= 12:
            return SeasonPhase.MID
        else:
            return SeasonPhase.LATE

    # =========================================================================
    # Recent Activity
    # =========================================================================

    def _get_recent_activity(
        self,
        dynasty_id: str,
        season: int,
        team_id: int,
        week: Optional[int]
    ) -> RecentActivity:
        """
        Get recent team activity (last 2 weeks).

        Queries player_transactions table for:
        - Trades (TRADE)
        - Signings (FA_SIGNING, WAIVER_CLAIM)
        - Cuts (ROSTER_CUT, WAIVER)

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            team_id: Team ID
            week: Current week (used to calculate cutoff date)

        Returns:
            RecentActivity with trades, signings, and cuts
        """
        # Calculate cutoff date (2 weeks ago)
        cutoff_date = self._get_cutoff_date(days_ago=14)

        # Query recent transactions
        trades = self._query_transactions(
            dynasty_id, season, team_id, cutoff_date, transaction_types=['TRADE']
        )
        signings = self._query_transactions(
            dynasty_id, season, team_id, cutoff_date,
            transaction_types=['FA_SIGNING', 'WAIVER_CLAIM', 'RESIGNING']
        )
        cuts = self._query_transactions(
            dynasty_id, season, team_id, cutoff_date,
            transaction_types=['ROSTER_CUT', 'WAIVER', 'RELEASE']
        )

        return RecentActivity(trades=trades, signings=signings, cuts=cuts)

    def _query_transactions(
        self,
        dynasty_id: str,
        season: int,
        team_id: int,
        cutoff_date: str,
        transaction_types: List[str]
    ) -> List[Dict]:
        """
        Query player_transactions table.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            team_id: Team ID
            cutoff_date: ISO date string (transactions after this date)
            transaction_types: List of transaction types to query

        Returns:
            List of transaction dicts
        """
        query = """
            SELECT
                id,
                transaction_type,
                player_id,
                first_name,
                last_name,
                position,
                from_team_id,
                to_team_id,
                transaction_date,
                details
            FROM player_transactions
            WHERE dynasty_id = ?
                AND season = ?
                AND (from_team_id = ? OR to_team_id = ?)
                AND transaction_date >= ?
                AND transaction_type IN ({})
            ORDER BY transaction_date DESC
            LIMIT 10
        """.format(','.join('?' * len(transaction_types)))

        params = [dynasty_id, season, team_id, team_id, cutoff_date] + transaction_types

        try:
            rows = self.db.query_all(query, tuple(params))
            transactions = []
            for row in rows:
                # Parse details JSON if present
                details = {}
                if row['details']:
                    try:
                        details = json.loads(row['details'])
                    except json.JSONDecodeError:
                        pass

                transactions.append({
                    'id': row['id'],
                    'type': row['transaction_type'],
                    'player_id': row['player_id'],
                    'player_name': f"{row['first_name']} {row['last_name']}",
                    'position': row['position'],
                    'from_team_id': row['from_team_id'],
                    'to_team_id': row['to_team_id'],
                    'date': row['transaction_date'],
                    'details': details
                })
            return transactions

        except Exception as e:
            logger.warning(f"Error querying transactions: {e}")
            return []

    def _get_cutoff_date(self, days_ago: int) -> str:
        """
        Get cutoff date for recent activity queries.

        Args:
            days_ago: Number of days in the past

        Returns:
            ISO date string (YYYY-MM-DD)
        """
        cutoff = datetime.now() - timedelta(days=days_ago)
        return cutoff.strftime('%Y-%m-%d')

    # =========================================================================
    # Streak Calculation
    # =========================================================================

    def _calculate_streak(
        self,
        dynasty_id: str,
        season: int,
        team_id: int
    ) -> tuple[int, str]:
        """
        Calculate team's current win/loss streak.

        Queries games table to find most recent games and count consecutive
        wins or losses.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            team_id: Team ID

        Returns:
            Tuple of (streak_count, streak_type)
            - streak_count: Positive int (number of games in streak)
            - streak_type: 'W' for wins, 'L' for losses
        """
        query = """
            SELECT
                week,
                home_team_id,
                away_team_id,
                home_score,
                away_score
            FROM games
            WHERE dynasty_id = ?
                AND season = ?
                AND (home_team_id = ? OR away_team_id = ?)
                AND season_type = 'regular_season'
            ORDER BY week DESC
            LIMIT 10
        """

        try:
            rows = self.db.query_all(query, (dynasty_id, season, team_id, team_id))

            if not rows:
                return 0, 'W'

            # Build list of results (True = win, False = loss)
            results = []
            for row in rows:
                is_home = row['home_team_id'] == team_id
                home_score = row['home_score']
                away_score = row['away_score']

                if is_home:
                    won = home_score > away_score
                else:
                    won = away_score > home_score

                results.append(won)

            # Count streak from most recent game
            if not results:
                return 0, 'W'

            current_result = results[0]
            streak_count = 1

            for result in results[1:]:
                if result == current_result:
                    streak_count += 1
                else:
                    break

            streak_type = 'W' if current_result else 'L'

            return streak_count, streak_type

        except Exception as e:
            logger.warning(f"Error calculating streak: {e}")
            return 0, 'W'

    # =========================================================================
    # Team Info Helpers
    # =========================================================================

    def _load_teams_json(self) -> Dict:
        """Load teams.json data for conference/division lookups."""
        try:
            import os
            current_dir = os.path.dirname(__file__)
            json_path = os.path.join(current_dir, "..", "..", "data", "teams.json")
            json_path = os.path.normpath(json_path)

            if not os.path.exists(json_path):
                logger.warning(f"teams.json not found at {json_path}")
                return {}

            with open(json_path, 'r') as f:
                data = json.load(f)
            return data.get('teams', {})

        except Exception as e:
            logger.warning(f"Error loading teams.json: {e}")
            return {}

    def _get_team_info(self, team_id: int) -> Optional[Dict]:
        """Get team info from teams.json."""
        return self._teams_json.get(str(team_id))

    def _get_team_division(self, team_id: int) -> Optional[Dict]:
        """Get team's conference and division."""
        team_info = self._get_team_info(team_id)
        if not team_info:
            return None

        return {
            'conference': team_info.get('conference', 'AFC'),
            'division': team_info.get('division', 'East')
        }

    def _get_division_teams(self, conference: str, division: str) -> List[int]:
        """Get all team IDs in a specific division."""
        from src.constants.team_ids import TeamIDs

        division_key = f"{conference.upper()}_{division.upper()}"
        return TeamIDs.get_division_teams(division_key)
