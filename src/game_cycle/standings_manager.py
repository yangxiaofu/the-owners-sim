"""
Standings manager for game_cycle.

Handles all standings-related operations: updates, queries, rankings.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any

from .database.connection import GameCycleDatabase


@dataclass
class TeamStanding:
    """Represents a team's current standing."""
    team_id: int
    team_name: str
    abbreviation: str
    conference: str
    division: str
    wins: int
    losses: int
    ties: int
    points_for: int
    points_against: int
    division_wins: int
    division_losses: int
    conference_wins: int
    conference_losses: int
    home_wins: int
    home_losses: int
    away_wins: int
    away_losses: int
    playoff_seed: Optional[int] = None

    @property
    def win_percentage(self) -> float:
        """Calculate win percentage."""
        total_games = self.wins + self.losses + self.ties
        if total_games == 0:
            return 0.0
        return (self.wins + 0.5 * self.ties) / total_games

    @property
    def point_differential(self) -> int:
        """Calculate point differential."""
        return self.points_for - self.points_against

    @property
    def record_str(self) -> str:
        """Format record as string (e.g., '10-5-1')."""
        if self.ties > 0:
            return f"{self.wins}-{self.losses}-{self.ties}"
        return f"{self.wins}-{self.losses}"

    @property
    def division_record_str(self) -> str:
        """Division record as string."""
        return f"{self.division_wins}-{self.division_losses}"


class StandingsManager:
    """
    Manages team standings for the game cycle.

    Handles:
    - Updating standings after games
    - Querying standings by division/conference
    - Ranking teams for playoffs
    """

    def __init__(self, db: GameCycleDatabase):
        """
        Initialize with database connection.

        Args:
            db: GameCycleDatabase instance
        """
        self.db = db

    def update_from_game(
        self,
        home_team_id: int,
        away_team_id: int,
        home_score: int,
        away_score: int,
        is_divisional: bool = False,
        is_conference: bool = False
    ) -> None:
        """
        Update standings based on game result.

        Args:
            home_team_id: Home team ID
            away_team_id: Away team ID
            home_score: Home team final score
            away_score: Away team final score
            is_divisional: True if divisional game
            is_conference: True if conference game
        """
        # Determine winner
        if home_score > away_score:
            self._record_win(home_team_id, is_home=True, is_divisional=is_divisional, is_conference=is_conference)
            self._record_loss(away_team_id, is_home=False, is_divisional=is_divisional, is_conference=is_conference)
        elif away_score > home_score:
            self._record_win(away_team_id, is_home=False, is_divisional=is_divisional, is_conference=is_conference)
            self._record_loss(home_team_id, is_home=True, is_divisional=is_divisional, is_conference=is_conference)
        else:
            # Tie (rare in NFL but possible in regular season)
            self._record_tie(home_team_id, is_home=True, is_divisional=is_divisional, is_conference=is_conference)
            self._record_tie(away_team_id, is_home=False, is_divisional=is_divisional, is_conference=is_conference)

        # Update points
        self._update_points(home_team_id, home_score, away_score)
        self._update_points(away_team_id, away_score, home_score)

    def _record_win(
        self,
        team_id: int,
        is_home: bool,
        is_divisional: bool,
        is_conference: bool
    ) -> None:
        """Record a win for a team."""
        updates = ["wins = wins + 1"]

        if is_home:
            updates.append("home_wins = home_wins + 1")
        else:
            updates.append("away_wins = away_wins + 1")

        if is_divisional:
            updates.append("division_wins = division_wins + 1")

        if is_conference:
            updates.append("conference_wins = conference_wins + 1")

        sql = f"UPDATE standings SET {', '.join(updates)} WHERE team_id = ?"
        self.db.execute(sql, (team_id,))

    def _record_loss(
        self,
        team_id: int,
        is_home: bool,
        is_divisional: bool,
        is_conference: bool
    ) -> None:
        """Record a loss for a team."""
        updates = ["losses = losses + 1"]

        if is_home:
            updates.append("home_losses = home_losses + 1")
        else:
            updates.append("away_losses = away_losses + 1")

        if is_divisional:
            updates.append("division_losses = division_losses + 1")

        if is_conference:
            updates.append("conference_losses = conference_losses + 1")

        sql = f"UPDATE standings SET {', '.join(updates)} WHERE team_id = ?"
        self.db.execute(sql, (team_id,))

    def _record_tie(
        self,
        team_id: int,
        is_home: bool,
        is_divisional: bool,
        is_conference: bool
    ) -> None:
        """Record a tie for a team."""
        updates = ["ties = ties + 1"]
        sql = f"UPDATE standings SET {', '.join(updates)} WHERE team_id = ?"
        self.db.execute(sql, (team_id,))

    def _update_points(self, team_id: int, points_for: int, points_against: int) -> None:
        """Update points for/against for a team."""
        self.db.execute(
            """UPDATE standings
               SET points_for = points_for + ?,
                   points_against = points_against + ?
               WHERE team_id = ?""",
            (points_for, points_against, team_id)
        )

    def get_standings(self) -> List[TeamStanding]:
        """
        Get all standings sorted by win percentage.

        Returns:
            List of TeamStanding sorted by record
        """
        rows = self.db.query_all(
            """SELECT s.*, t.name as team_name, t.abbreviation, t.conference, t.division
               FROM standings s
               JOIN teams t ON s.team_id = t.team_id
               ORDER BY
                   (s.wins + 0.5 * s.ties) / NULLIF(s.wins + s.losses + s.ties, 0) DESC,
                   s.wins DESC,
                   (s.points_for - s.points_against) DESC,
                   s.points_for DESC"""
        )
        return [self._row_to_standing(row) for row in rows]

    def get_division_standings(self, conference: str, division: str) -> List[TeamStanding]:
        """
        Get standings for a specific division.

        Args:
            conference: 'AFC' or 'NFC'
            division: 'North', 'South', 'East', or 'West'

        Returns:
            List of TeamStanding for that division, sorted by record
        """
        rows = self.db.query_all(
            """SELECT s.*, t.name as team_name, t.abbreviation, t.conference, t.division
               FROM standings s
               JOIN teams t ON s.team_id = t.team_id
               WHERE t.conference = ? AND t.division = ?
               ORDER BY
                   (s.wins + 0.5 * s.ties) / NULLIF(s.wins + s.losses + s.ties, 0) DESC,
                   s.division_wins DESC,
                   (s.points_for - s.points_against) DESC""",
            (conference, division)
        )
        return [self._row_to_standing(row) for row in rows]

    def get_conference_standings(self, conference: str) -> List[TeamStanding]:
        """
        Get standings for a conference.

        Args:
            conference: 'AFC' or 'NFC'

        Returns:
            List of TeamStanding for that conference, sorted by record
        """
        rows = self.db.query_all(
            """SELECT s.*, t.name as team_name, t.abbreviation, t.conference, t.division
               FROM standings s
               JOIN teams t ON s.team_id = t.team_id
               WHERE t.conference = ?
               ORDER BY
                   (s.wins + 0.5 * s.ties) / NULLIF(s.wins + s.losses + s.ties, 0) DESC,
                   s.wins DESC,
                   (s.points_for - s.points_against) DESC""",
            (conference,)
        )
        return [self._row_to_standing(row) for row in rows]

    def get_team_standing(self, team_id: int) -> Optional[TeamStanding]:
        """Get standing for a specific team."""
        row = self.db.query_one(
            """SELECT s.*, t.name as team_name, t.abbreviation, t.conference, t.division
               FROM standings s
               JOIN teams t ON s.team_id = t.team_id
               WHERE s.team_id = ?""",
            (team_id,)
        )
        return self._row_to_standing(row) if row else None

    def set_playoff_seed(self, team_id: int, seed: int) -> None:
        """Set playoff seed for a team."""
        self.db.execute(
            "UPDATE standings SET playoff_seed = ? WHERE team_id = ?",
            (seed, team_id)
        )

    def reset_standings(self) -> None:
        """Reset all standings to 0-0-0."""
        self.db.execute(
            """UPDATE standings SET
               wins = 0, losses = 0, ties = 0,
               points_for = 0, points_against = 0,
               division_wins = 0, division_losses = 0,
               conference_wins = 0, conference_losses = 0,
               home_wins = 0, home_losses = 0,
               away_wins = 0, away_losses = 0,
               playoff_seed = NULL"""
        )

    def _row_to_standing(self, row) -> TeamStanding:
        """Convert database row to TeamStanding."""
        return TeamStanding(
            team_id=row['team_id'],
            team_name=row['team_name'],
            abbreviation=row['abbreviation'],
            conference=row['conference'],
            division=row['division'],
            wins=row['wins'],
            losses=row['losses'],
            ties=row['ties'],
            points_for=row['points_for'],
            points_against=row['points_against'],
            division_wins=row['division_wins'],
            division_losses=row['division_losses'],
            conference_wins=row['conference_wins'],
            conference_losses=row['conference_losses'],
            home_wins=row['home_wins'],
            home_losses=row['home_losses'],
            away_wins=row['away_wins'],
            away_losses=row['away_losses'],
            playoff_seed=row['playoff_seed']
        )
