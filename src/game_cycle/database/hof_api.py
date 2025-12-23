"""
Hall of Fame API - Database operations for HOF inductees and voting history.

Handles database operations for the Hall of Fame system including:
- HOF inductee records with ceremony data
- Annual voting history with score breakdowns
- Statistics and queries for HOF data
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
import json
import logging

from .connection import GameCycleDatabase

logger = logging.getLogger(__name__)


# ============================================
# Dataclasses
# ============================================

@dataclass
class HOFInductee:
    """Represents a Hall of Fame inductee record."""
    player_id: int
    induction_season: int
    years_on_ballot: int
    is_first_ballot: bool
    vote_percentage: float
    player_name: str
    primary_position: str
    career_seasons: int
    final_team_id: int
    teams_played_for: List[str]
    super_bowl_wins: int = 0
    mvp_awards: int = 0
    all_pro_first_team: int = 0
    all_pro_second_team: int = 0
    pro_bowl_selections: int = 0
    career_stats: Dict[str, Any] = field(default_factory=dict)
    hof_score: int = 0
    presenter_name: Optional[str] = None
    presenter_relationship: Optional[str] = None
    speech_highlights: Optional[Dict[str, str]] = None
    created_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'player_id': self.player_id,
            'induction_season': self.induction_season,
            'years_on_ballot': self.years_on_ballot,
            'is_first_ballot': self.is_first_ballot,
            'vote_percentage': self.vote_percentage,
            'player_name': self.player_name,
            'primary_position': self.primary_position,
            'career_seasons': self.career_seasons,
            'final_team_id': self.final_team_id,
            'teams_played_for': self.teams_played_for,
            'super_bowl_wins': self.super_bowl_wins,
            'mvp_awards': self.mvp_awards,
            'all_pro_first_team': self.all_pro_first_team,
            'all_pro_second_team': self.all_pro_second_team,
            'pro_bowl_selections': self.pro_bowl_selections,
            'career_stats': self.career_stats,
            'hof_score': self.hof_score,
            'presenter_name': self.presenter_name,
            'presenter_relationship': self.presenter_relationship,
            'speech_highlights': self.speech_highlights,
            'created_at': self.created_at,
        }


@dataclass
class HOFVotingResult:
    """Represents a voting result for a HOF candidate."""
    player_id: int
    voting_season: int
    player_name: str
    primary_position: str
    retirement_season: int
    years_on_ballot: int
    vote_percentage: float
    votes_received: int
    total_voters: int
    was_inducted: bool
    is_first_ballot: bool
    removed_from_ballot: bool
    hof_score: int
    score_breakdown: Optional[Dict[str, Any]] = None
    created_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'player_id': self.player_id,
            'voting_season': self.voting_season,
            'player_name': self.player_name,
            'primary_position': self.primary_position,
            'retirement_season': self.retirement_season,
            'years_on_ballot': self.years_on_ballot,
            'vote_percentage': self.vote_percentage,
            'votes_received': self.votes_received,
            'total_voters': self.total_voters,
            'was_inducted': self.was_inducted,
            'is_first_ballot': self.is_first_ballot,
            'removed_from_ballot': self.removed_from_ballot,
            'hof_score': self.hof_score,
            'score_breakdown': self.score_breakdown,
            'created_at': self.created_at,
        }


# ============================================
# HOFAPI Class
# ============================================

class HOFAPI:
    """
    API for Hall of Fame database operations.

    Handles:
    - HOF inductee records with ceremony data
    - Annual voting history tracking
    - Statistics and queries for HOF data

    All operations are dynasty-isolated.
    """

    def __init__(self, db: GameCycleDatabase, dynasty_id: str):
        """
        Initialize with database connection and dynasty ID.

        Args:
            db: GameCycleDatabase instance
            dynasty_id: Dynasty identifier for isolation
        """
        self.db = db
        self.dynasty_id = dynasty_id

    # ============================================
    # HOF Inductee Operations
    # ============================================

    def add_inductee(
        self,
        player_id: int,
        induction_season: int,
        years_on_ballot: int,
        vote_percentage: float,
        player_data: Dict[str, Any],
        ceremony_data: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Add new HOF inductee.

        Args:
            player_id: Player ID
            induction_season: Season of induction
            years_on_ballot: Years player was on ballot before induction
            vote_percentage: Vote percentage (0.0-1.0)
            player_data: Dict with player info (name, position, stats, achievements)
            ceremony_data: Optional dict with ceremony info (presenter, speech)

        Returns:
            Row ID of inserted record

        Raises:
            sqlite3.IntegrityError: If player already inducted
        """
        is_first_ballot = 1 if years_on_ballot == 1 else 0
        ceremony_data = ceremony_data or {}

        # Serialize JSON fields
        teams_json = json.dumps(player_data.get('teams_played_for', []))
        stats_json = json.dumps(player_data.get('career_stats', {}))
        speech_json = json.dumps(ceremony_data.get('speech_highlights')) if ceremony_data.get('speech_highlights') else None

        cursor = self.db.execute(
            """INSERT INTO hall_of_fame
               (dynasty_id, player_id, induction_season, years_on_ballot,
                is_first_ballot, vote_percentage, player_name, primary_position,
                career_seasons, final_team_id, teams_played_for,
                super_bowl_wins, mvp_awards, all_pro_first_team, all_pro_second_team,
                pro_bowl_selections, career_stats, hof_score,
                presenter_name, presenter_relationship, speech_highlights)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                self.dynasty_id,
                player_id,
                induction_season,
                years_on_ballot,
                is_first_ballot,
                vote_percentage,
                player_data.get('player_name', ''),
                player_data.get('primary_position', ''),
                player_data.get('career_seasons', 0),
                player_data.get('final_team_id', 0),
                teams_json,
                player_data.get('super_bowl_wins', 0),
                player_data.get('mvp_awards', 0),
                player_data.get('all_pro_first_team', 0),
                player_data.get('all_pro_second_team', 0),
                player_data.get('pro_bowl_selections', 0),
                stats_json,
                player_data.get('hof_score', 0),
                ceremony_data.get('presenter_name'),
                ceremony_data.get('presenter_relationship'),
                speech_json
            )
        )
        return cursor.lastrowid

    def get_inductee(self, player_id: int) -> Optional[Dict[str, Any]]:
        """
        Get HOF inductee by player ID.

        Args:
            player_id: Player ID

        Returns:
            Dictionary with inductee data, or None if not found
        """
        row = self.db.query_one(
            """SELECT player_id, induction_season, years_on_ballot, is_first_ballot,
                      vote_percentage, player_name, primary_position, career_seasons,
                      final_team_id, teams_played_for, super_bowl_wins, mvp_awards,
                      all_pro_first_team, all_pro_second_team, pro_bowl_selections,
                      career_stats, hof_score, presenter_name, presenter_relationship,
                      speech_highlights, created_at
               FROM hall_of_fame
               WHERE dynasty_id = ? AND player_id = ?""",
            (self.dynasty_id, player_id)
        )
        if not row:
            return None

        return self._row_to_dict(row)

    def get_all_inductees(
        self,
        position_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all HOF members.

        Args:
            position_filter: Optional position to filter by

        Returns:
            List of inductee dicts sorted by induction_season DESC, hof_score DESC
        """
        if position_filter:
            rows = self.db.query_all(
                """SELECT player_id, induction_season, years_on_ballot, is_first_ballot,
                          vote_percentage, player_name, primary_position, career_seasons,
                          final_team_id, teams_played_for, super_bowl_wins, mvp_awards,
                          all_pro_first_team, all_pro_second_team, pro_bowl_selections,
                          career_stats, hof_score, presenter_name, presenter_relationship,
                          speech_highlights, created_at
                   FROM hall_of_fame
                   WHERE dynasty_id = ? AND primary_position = ?
                   ORDER BY induction_season DESC, hof_score DESC""",
                (self.dynasty_id, position_filter)
            )
        else:
            rows = self.db.query_all(
                """SELECT player_id, induction_season, years_on_ballot, is_first_ballot,
                          vote_percentage, player_name, primary_position, career_seasons,
                          final_team_id, teams_played_for, super_bowl_wins, mvp_awards,
                          all_pro_first_team, all_pro_second_team, pro_bowl_selections,
                          career_stats, hof_score, presenter_name, presenter_relationship,
                          speech_highlights, created_at
                   FROM hall_of_fame
                   WHERE dynasty_id = ?
                   ORDER BY induction_season DESC, hof_score DESC""",
                (self.dynasty_id,)
            )

        return [self._row_to_dict(row) for row in rows]

    def get_inductees_by_season(self, season: int) -> List[Dict[str, Any]]:
        """
        Get HOF class for a specific induction year.

        Args:
            season: Induction season year

        Returns:
            List of inductee dicts sorted by hof_score DESC
        """
        rows = self.db.query_all(
            """SELECT player_id, induction_season, years_on_ballot, is_first_ballot,
                      vote_percentage, player_name, primary_position, career_seasons,
                      final_team_id, teams_played_for, super_bowl_wins, mvp_awards,
                      all_pro_first_team, all_pro_second_team, pro_bowl_selections,
                      career_stats, hof_score, presenter_name, presenter_relationship,
                      speech_highlights, created_at
               FROM hall_of_fame
               WHERE dynasty_id = ? AND induction_season = ?
               ORDER BY hof_score DESC""",
            (self.dynasty_id, season)
        )

        return [self._row_to_dict(row) for row in rows]

    def get_team_inductees(self, team_name: str) -> List[Dict[str, Any]]:
        """
        Get all inductees who played for a team.

        Args:
            team_name: Team name to search for in teams_played_for JSON

        Returns:
            List of inductee dicts who played for the team
        """
        # Use JSON search - SQLite stores JSON as text
        rows = self.db.query_all(
            """SELECT player_id, induction_season, years_on_ballot, is_first_ballot,
                      vote_percentage, player_name, primary_position, career_seasons,
                      final_team_id, teams_played_for, super_bowl_wins, mvp_awards,
                      all_pro_first_team, all_pro_second_team, pro_bowl_selections,
                      career_stats, hof_score, presenter_name, presenter_relationship,
                      speech_highlights, created_at
               FROM hall_of_fame
               WHERE dynasty_id = ? AND teams_played_for LIKE ?
               ORDER BY induction_season DESC""",
            (self.dynasty_id, f'%"{team_name}"%')
        )

        return [self._row_to_dict(row) for row in rows]

    def is_inducted(self, player_id: int) -> bool:
        """
        Check if player is already in HOF.

        Args:
            player_id: Player ID

        Returns:
            True if player is inducted
        """
        row = self.db.query_one(
            """SELECT COUNT(*) as count
               FROM hall_of_fame
               WHERE dynasty_id = ? AND player_id = ?""",
            (self.dynasty_id, player_id)
        )
        return row is not None and row['count'] > 0

    def get_inductee_count(self) -> int:
        """
        Get total HOF members in dynasty.

        Returns:
            Count of HOF members
        """
        row = self.db.query_one(
            """SELECT COUNT(*) as count
               FROM hall_of_fame
               WHERE dynasty_id = ?""",
            (self.dynasty_id,)
        )
        return row['count'] if row else 0

    # ============================================
    # Voting History Operations
    # ============================================

    def save_voting_result(
        self,
        voting_season: int,
        player_id: int,
        player_name: str,
        position: str,
        retirement_season: int,
        years_on_ballot: int,
        vote_percentage: float,
        votes_received: int,
        total_voters: int,
        was_inducted: bool,
        is_first_ballot: bool,
        removed_from_ballot: bool,
        hof_score: int,
        score_breakdown: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Save voting result for a candidate.

        Args:
            voting_season: Season of voting
            player_id: Player ID
            player_name: Player name
            position: Primary position
            retirement_season: Season player retired
            years_on_ballot: Years on ballot including this one
            vote_percentage: Vote percentage (0.0-1.0)
            votes_received: Number of votes received
            total_voters: Total number of voters
            was_inducted: Whether player was inducted
            is_first_ballot: Whether this is first ballot induction
            removed_from_ballot: Whether player was removed from ballot
            hof_score: HOF score
            score_breakdown: Optional score breakdown dict

        Returns:
            Row ID of inserted record
        """
        breakdown_json = json.dumps(score_breakdown) if score_breakdown else None

        cursor = self.db.execute(
            """INSERT INTO hof_voting_history
               (dynasty_id, voting_season, player_id, player_name, primary_position,
                retirement_season, years_on_ballot, vote_percentage, votes_received,
                total_voters, was_inducted, is_first_ballot, removed_from_ballot,
                hof_score, score_breakdown)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                self.dynasty_id,
                voting_season,
                player_id,
                player_name,
                position,
                retirement_season,
                years_on_ballot,
                vote_percentage,
                votes_received,
                total_voters,
                1 if was_inducted else 0,
                1 if is_first_ballot else 0,
                1 if removed_from_ballot else 0,
                hof_score,
                breakdown_json
            )
        )
        return cursor.lastrowid

    def get_voting_history_by_season(self, season: int) -> List[Dict[str, Any]]:
        """
        Get all voting results for a season.

        Args:
            season: Voting season year

        Returns:
            List of voting result dicts sorted by vote_percentage DESC
        """
        rows = self.db.query_all(
            """SELECT player_id, voting_season, player_name, primary_position,
                      retirement_season, years_on_ballot, vote_percentage,
                      votes_received, total_voters, was_inducted, is_first_ballot,
                      removed_from_ballot, hof_score, score_breakdown, created_at
               FROM hof_voting_history
               WHERE dynasty_id = ? AND voting_season = ?
               ORDER BY vote_percentage DESC""",
            (self.dynasty_id, season)
        )

        return [self._voting_row_to_dict(row) for row in rows]

    def get_player_voting_history(self, player_id: int) -> List[Dict[str, Any]]:
        """
        Get complete voting history for a player.

        Args:
            player_id: Player ID

        Returns:
            List of voting result dicts sorted by voting_season ASC
        """
        rows = self.db.query_all(
            """SELECT player_id, voting_season, player_name, primary_position,
                      retirement_season, years_on_ballot, vote_percentage,
                      votes_received, total_voters, was_inducted, is_first_ballot,
                      removed_from_ballot, hof_score, score_breakdown, created_at
               FROM hof_voting_history
               WHERE dynasty_id = ? AND player_id = ?
               ORDER BY voting_season ASC""",
            (self.dynasty_id, player_id)
        )

        return [self._voting_row_to_dict(row) for row in rows]

    def get_years_on_ballot(self, player_id: int) -> int:
        """
        Get how many years a player has been on ballot.

        Args:
            player_id: Player ID

        Returns:
            Number of years on ballot (0 if never on ballot)
        """
        row = self.db.query_one(
            """SELECT MAX(years_on_ballot) as max_years
               FROM hof_voting_history
               WHERE dynasty_id = ? AND player_id = ?""",
            (self.dynasty_id, player_id)
        )
        return row['max_years'] if row and row['max_years'] else 0

    def was_removed_from_ballot(self, player_id: int) -> bool:
        """
        Check if player was removed from ballot.

        Args:
            player_id: Player ID

        Returns:
            True if player was removed from ballot
        """
        row = self.db.query_one(
            """SELECT removed_from_ballot
               FROM hof_voting_history
               WHERE dynasty_id = ? AND player_id = ?
               ORDER BY voting_season DESC
               LIMIT 1""",
            (self.dynasty_id, player_id)
        )
        return row is not None and row['removed_from_ballot'] == 1

    # ============================================
    # Statistics
    # ============================================

    def get_hof_stats(self) -> Dict[str, Any]:
        """
        Get HOF statistics for dynasty.

        Returns:
            Dictionary with HOF statistics
        """
        # Total members
        total = self.get_inductee_count()

        # First ballot count
        fb_row = self.db.query_one(
            """SELECT COUNT(*) as count
               FROM hall_of_fame
               WHERE dynasty_id = ? AND is_first_ballot = 1""",
            (self.dynasty_id,)
        )
        first_ballot_count = fb_row['count'] if fb_row else 0

        # Average wait years
        avg_row = self.db.query_one(
            """SELECT AVG(years_on_ballot) as avg_wait
               FROM hall_of_fame
               WHERE dynasty_id = ?""",
            (self.dynasty_id,)
        )
        avg_wait = avg_row['avg_wait'] if avg_row and avg_row['avg_wait'] else 0.0

        # By position
        pos_rows = self.db.query_all(
            """SELECT primary_position, COUNT(*) as count
               FROM hall_of_fame
               WHERE dynasty_id = ?
               GROUP BY primary_position
               ORDER BY count DESC""",
            (self.dynasty_id,)
        )
        by_position = {row['primary_position']: row['count'] for row in pos_rows}

        return {
            'total_members': total,
            'first_ballot_count': first_ballot_count,
            'first_ballot_percentage': (first_ballot_count / total * 100) if total > 0 else 0.0,
            'by_position': by_position,
            'average_wait_years': round(avg_wait, 2),
        }

    # ============================================
    # Helper Methods
    # ============================================

    def _row_to_dict(self, row) -> Dict[str, Any]:
        """
        Convert database row to dictionary with JSON parsing.

        Args:
            row: SQLite row object

        Returns:
            Dictionary with parsed JSON fields
        """
        # Parse JSON fields
        teams_played_for = []
        if row['teams_played_for']:
            try:
                teams_played_for = json.loads(row['teams_played_for'])
            except (json.JSONDecodeError, TypeError):
                logger.warning(f"Failed to parse teams_played_for for player {row['player_id']}")

        career_stats = {}
        if row['career_stats']:
            try:
                career_stats = json.loads(row['career_stats'])
            except (json.JSONDecodeError, TypeError):
                logger.warning(f"Failed to parse career_stats for player {row['player_id']}")

        speech_highlights = None
        if row['speech_highlights']:
            try:
                speech_highlights = json.loads(row['speech_highlights'])
            except (json.JSONDecodeError, TypeError):
                logger.warning(f"Failed to parse speech_highlights for player {row['player_id']}")

        return {
            'player_id': row['player_id'],
            'induction_season': row['induction_season'],
            'years_on_ballot': row['years_on_ballot'],
            'is_first_ballot': bool(row['is_first_ballot']),
            'vote_percentage': row['vote_percentage'],
            'player_name': row['player_name'],
            'primary_position': row['primary_position'],
            'career_seasons': row['career_seasons'],
            'final_team_id': row['final_team_id'],
            'teams_played_for': teams_played_for,
            'super_bowl_wins': row['super_bowl_wins'],
            'mvp_awards': row['mvp_awards'],
            'all_pro_first_team': row['all_pro_first_team'],
            'all_pro_second_team': row['all_pro_second_team'],
            'pro_bowl_selections': row['pro_bowl_selections'],
            'career_stats': career_stats,
            'hof_score': row['hof_score'],
            'presenter_name': row['presenter_name'],
            'presenter_relationship': row['presenter_relationship'],
            'speech_highlights': speech_highlights,
            'created_at': row['created_at'],
        }

    def _voting_row_to_dict(self, row) -> Dict[str, Any]:
        """
        Convert voting history row to dictionary.

        Args:
            row: SQLite row object

        Returns:
            Dictionary with parsed JSON fields
        """
        score_breakdown = None
        if row['score_breakdown']:
            try:
                score_breakdown = json.loads(row['score_breakdown'])
            except (json.JSONDecodeError, TypeError):
                logger.warning(f"Failed to parse score_breakdown for player {row['player_id']}")

        return {
            'player_id': row['player_id'],
            'voting_season': row['voting_season'],
            'player_name': row['player_name'],
            'primary_position': row['primary_position'],
            'retirement_season': row['retirement_season'],
            'years_on_ballot': row['years_on_ballot'],
            'vote_percentage': row['vote_percentage'],
            'votes_received': row['votes_received'],
            'total_voters': row['total_voters'],
            'was_inducted': bool(row['was_inducted']),
            'is_first_ballot': bool(row['is_first_ballot']),
            'removed_from_ballot': bool(row['removed_from_ballot']),
            'hof_score': row['hof_score'],
            'score_breakdown': score_breakdown,
            'created_at': row['created_at'],
        }
