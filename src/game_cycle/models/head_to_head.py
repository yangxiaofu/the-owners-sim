"""
Head-to-head history tracking for teams.

Part of Milestone 11: Schedule & Rivalries, Tollgate 2.
Tracks all-time records between any two teams for rivalry context.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class HeadToHeadRecord:
    """
    Represents the all-time record between two NFL teams.

    Enforces team_a_id < team_b_id for consistent lookup ordering.
    Statistics are tracked from team_a's perspective (team_a_wins = team_a beat team_b).

    Attributes:
        team_a_id: Lower team ID (1-32), enforced by validation
        team_b_id: Higher team ID (1-32)
        team_a_wins: Number of games team_a has won against team_b
        team_b_wins: Number of games team_b has won against team_a
        ties: Number of ties between the teams
        team_a_home_wins: Wins by team_a when hosting team_b
        team_a_away_wins: Wins by team_a when visiting team_b
        last_meeting_season: Season of most recent game
        last_meeting_winner: team_id of winner (or None for tie)
        current_streak_team: team_id currently on winning streak (or None)
        current_streak_count: Games in current streak
        playoff_meetings: Total playoff games between teams
        playoff_team_a_wins: Playoff wins by team_a
        playoff_team_b_wins: Playoff wins by team_b
        record_id: Optional database ID (None for new records)
        created_at: Timestamp when record was created
        updated_at: Timestamp when record was last updated
    """
    team_a_id: int
    team_b_id: int
    team_a_wins: int = 0
    team_b_wins: int = 0
    ties: int = 0
    team_a_home_wins: int = 0
    team_a_away_wins: int = 0
    last_meeting_season: Optional[int] = None
    last_meeting_winner: Optional[int] = None
    current_streak_team: Optional[int] = None
    current_streak_count: int = 0
    playoff_meetings: int = 0
    playoff_team_a_wins: int = 0
    playoff_team_b_wins: int = 0
    record_id: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def __post_init__(self):
        """Validate record data after initialization."""
        self._validate_team_ids()
        self._validate_counts()

    def _validate_team_ids(self):
        """Ensure team IDs are valid and properly ordered."""
        if not isinstance(self.team_a_id, int) or not isinstance(self.team_b_id, int):
            raise ValueError("team_a_id and team_b_id must be integers")

        if not (1 <= self.team_a_id <= 32):
            raise ValueError(f"team_a_id must be 1-32, got {self.team_a_id}")
        if not (1 <= self.team_b_id <= 32):
            raise ValueError(f"team_b_id must be 1-32, got {self.team_b_id}")
        if self.team_a_id == self.team_b_id:
            raise ValueError("team_a_id and team_b_id must be different")

        # Auto-swap to enforce team_a_id < team_b_id ordering
        if self.team_a_id > self.team_b_id:
            self.team_a_id, self.team_b_id = self.team_b_id, self.team_a_id

    def _validate_counts(self):
        """Ensure all counts are non-negative."""
        count_fields = [
            ('team_a_wins', self.team_a_wins),
            ('team_b_wins', self.team_b_wins),
            ('ties', self.ties),
            ('team_a_home_wins', self.team_a_home_wins),
            ('team_a_away_wins', self.team_a_away_wins),
            ('current_streak_count', self.current_streak_count),
            ('playoff_meetings', self.playoff_meetings),
            ('playoff_team_a_wins', self.playoff_team_a_wins),
            ('playoff_team_b_wins', self.playoff_team_b_wins),
        ]
        for field_name, value in count_fields:
            if value < 0:
                raise ValueError(f"{field_name} cannot be negative, got {value}")

    @classmethod
    def from_db_row(cls, row) -> 'HeadToHeadRecord':
        """
        Create HeadToHeadRecord from database row.

        Args:
            row: Database row (sqlite3.Row or dict)

        Returns:
            HeadToHeadRecord instance
        """
        # Convert sqlite3.Row to dict if needed
        data = dict(row) if hasattr(row, 'keys') else row
        return cls(
            record_id=data.get('record_id'),
            team_a_id=data['team_a_id'],
            team_b_id=data['team_b_id'],
            team_a_wins=data.get('team_a_wins', 0),
            team_b_wins=data.get('team_b_wins', 0),
            ties=data.get('ties', 0),
            team_a_home_wins=data.get('team_a_home_wins', 0),
            team_a_away_wins=data.get('team_a_away_wins', 0),
            last_meeting_season=data.get('last_meeting_season'),
            last_meeting_winner=data.get('last_meeting_winner'),
            current_streak_team=data.get('current_streak_team'),
            current_streak_count=data.get('current_streak_count', 0),
            playoff_meetings=data.get('playoff_meetings', 0),
            playoff_team_a_wins=data.get('playoff_team_a_wins', 0),
            playoff_team_b_wins=data.get('playoff_team_b_wins', 0),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at'),
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dict for serialization/logging.

        Returns:
            Dict with all record data
        """
        return {
            'record_id': self.record_id,
            'team_a_id': self.team_a_id,
            'team_b_id': self.team_b_id,
            'team_a_wins': self.team_a_wins,
            'team_b_wins': self.team_b_wins,
            'ties': self.ties,
            'team_a_home_wins': self.team_a_home_wins,
            'team_a_away_wins': self.team_a_away_wins,
            'last_meeting_season': self.last_meeting_season,
            'last_meeting_winner': self.last_meeting_winner,
            'current_streak_team': self.current_streak_team,
            'current_streak_count': self.current_streak_count,
            'playoff_meetings': self.playoff_meetings,
            'playoff_team_a_wins': self.playoff_team_a_wins,
            'playoff_team_b_wins': self.playoff_team_b_wins,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }

    # -------------------- Computed Properties --------------------

    @property
    def total_games(self) -> int:
        """Total regular season games played between teams."""
        return self.team_a_wins + self.team_b_wins + self.ties

    @property
    def total_playoff_games(self) -> int:
        """Total playoff games played between teams."""
        return self.playoff_meetings

    @property
    def total_all_games(self) -> int:
        """Total games including playoffs."""
        return self.total_games + self.playoff_meetings

    def get_record_for_team(self, team_id: int) -> str:
        """
        Get formatted record string from a team's perspective.

        Args:
            team_id: Team to get record for

        Returns:
            Record string like "10-5-1"

        Raises:
            ValueError: If team_id not in this matchup
        """
        if team_id == self.team_a_id:
            return f"{self.team_a_wins}-{self.team_b_wins}-{self.ties}"
        elif team_id == self.team_b_id:
            return f"{self.team_b_wins}-{self.team_a_wins}-{self.ties}"
        else:
            raise ValueError(f"Team {team_id} not in this matchup")

    def get_wins_for_team(self, team_id: int) -> int:
        """
        Get total regular season wins for a specific team.

        Args:
            team_id: Team to get wins for

        Returns:
            Number of wins

        Raises:
            ValueError: If team_id not in this matchup
        """
        if team_id == self.team_a_id:
            return self.team_a_wins
        elif team_id == self.team_b_id:
            return self.team_b_wins
        else:
            raise ValueError(f"Team {team_id} not in this matchup")

    def get_losses_for_team(self, team_id: int) -> int:
        """
        Get total regular season losses for a specific team.

        Args:
            team_id: Team to get losses for

        Returns:
            Number of losses

        Raises:
            ValueError: If team_id not in this matchup
        """
        if team_id == self.team_a_id:
            return self.team_b_wins
        elif team_id == self.team_b_id:
            return self.team_a_wins
        else:
            raise ValueError(f"Team {team_id} not in this matchup")

    def get_playoff_record_for_team(self, team_id: int) -> str:
        """
        Get formatted playoff record string from a team's perspective.

        Args:
            team_id: Team to get record for

        Returns:
            Record string like "3-2" (no ties in playoffs)

        Raises:
            ValueError: If team_id not in this matchup
        """
        if team_id == self.team_a_id:
            return f"{self.playoff_team_a_wins}-{self.playoff_team_b_wins}"
        elif team_id == self.team_b_id:
            return f"{self.playoff_team_b_wins}-{self.playoff_team_a_wins}"
        else:
            raise ValueError(f"Team {team_id} not in this matchup")

    @property
    def series_leader(self) -> Optional[int]:
        """
        Team currently leading the all-time series.

        Returns:
            team_id of leader, or None if series is tied
        """
        if self.team_a_wins > self.team_b_wins:
            return self.team_a_id
        elif self.team_b_wins > self.team_a_wins:
            return self.team_b_id
        return None

    @property
    def series_margin(self) -> int:
        """Difference in wins between teams (absolute value)."""
        return abs(self.team_a_wins - self.team_b_wins)

    @property
    def streak_description(self) -> str:
        """
        Human-readable streak description.

        Returns:
            String like "Team 5: W3" or "No current streak"
        """
        if self.current_streak_team is None or self.current_streak_count == 0:
            return "No current streak"
        return f"Team {self.current_streak_team}: W{self.current_streak_count}"

    def involves_team(self, team_id: int) -> bool:
        """
        Check if this record involves a specific team.

        Args:
            team_id: Team ID to check (1-32)

        Returns:
            True if team is part of this matchup
        """
        return team_id == self.team_a_id or team_id == self.team_b_id

    def get_opponent(self, team_id: int) -> Optional[int]:
        """
        Get the opponent team ID for a given team in this matchup.

        Args:
            team_id: Team ID to find opponent for

        Returns:
            Opponent team ID, or None if team not in matchup
        """
        if team_id == self.team_a_id:
            return self.team_b_id
        elif team_id == self.team_b_id:
            return self.team_a_id
        return None

    def __str__(self) -> str:
        """String representation for logging/display."""
        return (
            f"Head-to-Head: Team {self.team_a_id} vs Team {self.team_b_id} "
            f"({self.team_a_wins}-{self.team_b_wins}-{self.ties})"
        )
