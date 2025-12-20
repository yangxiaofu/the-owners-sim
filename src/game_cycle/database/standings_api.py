"""
Standings API for game_cycle.

Handles all standings-related database operations.
"""

from dataclasses import dataclass
from typing import List, Optional

from .connection import GameCycleDatabase


@dataclass
class TeamStanding:
    """Represents a team's standing record."""
    team_id: int
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


class StandingsAPI:
    """
    API for standings operations in game_cycle.

    Handles:
    - Querying standings by dynasty/season
    - Updating standings after games
    - Getting standings by team/division/conference
    """

    def __init__(self, db: GameCycleDatabase):
        """
        Initialize with database connection.

        Args:
            db: GameCycleDatabase instance
        """
        self.db = db

    # -------------------- Query Methods --------------------

    def get_standings(
        self,
        dynasty_id: str,
        season: int,
        season_type: str = 'regular_season'
    ) -> List[TeamStanding]:
        """
        Get all standings for a dynasty/season, sorted by win percentage.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            season_type: 'regular_season' or 'preseason'

        Returns:
            List of TeamStanding sorted by record
        """
        rows = self.db.query_all(
            """SELECT team_id, wins, losses, ties, points_for, points_against,
                      division_wins, division_losses, conference_wins, conference_losses,
                      home_wins, home_losses, away_wins, away_losses, playoff_seed
               FROM standings
               WHERE dynasty_id = ? AND season = ? AND season_type = ?
               ORDER BY
                   (wins + 0.5 * ties) / NULLIF(wins + losses + ties, 0) DESC,
                   wins DESC,
                   (points_for - points_against) DESC""",
            (dynasty_id, season, season_type)
        )
        return [self._row_to_standing(row) for row in rows]

    def get_team_standing(
        self,
        dynasty_id: str,
        season: int,
        team_id: int,
        season_type: str = 'regular_season'
    ) -> Optional[TeamStanding]:
        """Get standing for a specific team."""
        row = self.db.query_one(
            """SELECT team_id, wins, losses, ties, points_for, points_against,
                      division_wins, division_losses, conference_wins, conference_losses,
                      home_wins, home_losses, away_wins, away_losses, playoff_seed
               FROM standings
               WHERE dynasty_id = ? AND season = ? AND team_id = ? AND season_type = ?""",
            (dynasty_id, season, team_id, season_type)
        )
        return self._row_to_standing(row) if row else None

    # -------------------- Update Methods --------------------

    def update_from_game(
        self,
        dynasty_id: str,
        season: int,
        home_team_id: int,
        away_team_id: int,
        home_score: int,
        away_score: int,
        is_divisional: bool = False,
        is_conference: bool = False,
        season_type: str = 'regular_season'
    ) -> None:
        """
        Update standings based on game result.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            home_team_id: Home team ID
            away_team_id: Away team ID
            home_score: Home team final score
            away_score: Away team final score
            is_divisional: True if divisional game
            is_conference: True if conference game
            season_type: 'regular_season' or 'preseason'
        """
        # Determine winner
        if home_score > away_score:
            self._record_win(dynasty_id, season, home_team_id, is_home=True,
                           is_divisional=is_divisional, is_conference=is_conference,
                           season_type=season_type)
            self._record_loss(dynasty_id, season, away_team_id, is_home=False,
                            is_divisional=is_divisional, is_conference=is_conference,
                            season_type=season_type)
        elif away_score > home_score:
            self._record_win(dynasty_id, season, away_team_id, is_home=False,
                           is_divisional=is_divisional, is_conference=is_conference,
                           season_type=season_type)
            self._record_loss(dynasty_id, season, home_team_id, is_home=True,
                            is_divisional=is_divisional, is_conference=is_conference,
                            season_type=season_type)
        else:
            # Tie (rare in NFL but possible in regular season)
            self._record_tie(dynasty_id, season, home_team_id, season_type=season_type)
            self._record_tie(dynasty_id, season, away_team_id, season_type=season_type)

        # Update points
        self._update_points(dynasty_id, season, home_team_id, home_score, away_score, season_type)
        self._update_points(dynasty_id, season, away_team_id, away_score, home_score, season_type)

    def set_playoff_seed(
        self,
        dynasty_id: str,
        season: int,
        team_id: int,
        seed: int,
        season_type: str = 'regular_season'
    ) -> None:
        """Set playoff seed for a team."""
        self.db.execute(
            """UPDATE standings
               SET playoff_seed = ?
               WHERE dynasty_id = ? AND season = ? AND team_id = ? AND season_type = ?""",
            (seed, dynasty_id, season, team_id, season_type)
        )

    def reset_standings(
        self,
        dynasty_id: str,
        season: int,
        season_type: str = 'regular_season'
    ) -> None:
        """Reset all standings to 0-0-0 for a dynasty/season."""
        self.db.execute(
            """UPDATE standings SET
               wins = 0, losses = 0, ties = 0,
               points_for = 0, points_against = 0,
               division_wins = 0, division_losses = 0,
               conference_wins = 0, conference_losses = 0,
               home_wins = 0, home_losses = 0,
               away_wins = 0, away_losses = 0,
               playoff_seed = NULL
               WHERE dynasty_id = ? AND season = ? AND season_type = ?""",
            (dynasty_id, season, season_type)
        )

    def initialize_season_standings(
        self,
        dynasty_id: str,
        season: int,
        placeholder: bool = False,
        season_type: str = 'regular_season'
    ) -> int:
        """
        Initialize standings for all 32 teams for a season.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year
            placeholder: If True, generates random win/loss records. If False, all 0-0.
            season_type: 'regular_season' or 'preseason'

        Returns:
            Number of team standings created
        """
        import random

        # Check if standings already exist for this dynasty/season
        existing = self.db.query_one(
            """SELECT COUNT(*) as count FROM standings
               WHERE dynasty_id = ? AND season = ? AND season_type = ?""",
            (dynasty_id, season, season_type)
        )

        if existing and existing['count'] > 0:
            # Standings already exist, don't recreate
            return 0

        created_count = 0

        # Insert standings for all 32 teams (team_ids 1-32)
        for team_id in range(1, 33):
            if placeholder:
                # Generate random record for placeholder data
                # NFL regular season is 17 games, so wins + losses should equal 17
                wins = random.randint(0, 17)
                losses = 17 - wins
                ties = 0  # Ties are rare, omit for simplicity in placeholders

                # Generate realistic point totals
                # NFL teams typically score 300-500 points per season
                points_for = random.randint(250, 500)
                points_against = random.randint(250, 500)

                # Generate divisional/conference records proportionally
                # Assume 6 divisional games, 10 conference games (including divisional)
                div_games = 6
                div_wins = random.randint(0, min(wins, div_games))
                div_losses = min(div_games - div_wins, losses)

                conf_games = 10
                conf_wins = random.randint(div_wins, min(wins, conf_games))
                conf_losses = min(conf_games - conf_wins, losses)

                # Split home/away roughly evenly (8-9 home, 8-9 away)
                home_games = 9 if team_id % 2 == 0 else 8
                home_wins = random.randint(0, min(wins, home_games))
                home_losses = min(home_games - home_wins, losses)

                away_wins = wins - home_wins
                away_losses = losses - home_losses
            else:
                # Create fresh 0-0 records
                wins = losses = ties = 0
                points_for = points_against = 0
                div_wins = div_losses = 0
                conf_wins = conf_losses = 0
                home_wins = home_losses = 0
                away_wins = away_losses = 0

            # Insert the standing record
            self.db.execute(
                """INSERT INTO standings (
                    dynasty_id, team_id, season, season_type,
                    wins, losses, ties,
                    points_for, points_against,
                    division_wins, division_losses, division_ties,
                    conference_wins, conference_losses, conference_ties,
                    home_wins, home_losses, home_ties,
                    away_wins, away_losses, away_ties,
                    playoff_seed, point_differential,
                    made_playoffs, made_wild_card, won_wild_card,
                    won_division_round, won_conference, won_super_bowl
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    dynasty_id, team_id, season, season_type,
                    wins, losses, ties,
                    points_for, points_against,
                    div_wins, div_losses, 0,  # division_ties
                    conf_wins, conf_losses, 0,  # conference_ties
                    home_wins, home_losses, 0,  # home_ties
                    away_wins, away_losses, 0,  # away_ties
                    None,  # playoff_seed
                    points_for - points_against,  # point_differential
                    False, False, False,  # made_playoffs, made_wild_card, won_wild_card
                    False, False, False   # won_division_round, won_conference, won_super_bowl
                )
            )
            created_count += 1

        return created_count

    # -------------------- Private Methods --------------------

    def _record_win(
        self,
        dynasty_id: str,
        season: int,
        team_id: int,
        is_home: bool,
        is_divisional: bool,
        is_conference: bool,
        season_type: str
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

        sql = f"""UPDATE standings SET {', '.join(updates)}
                  WHERE dynasty_id = ? AND season = ? AND team_id = ? AND season_type = ?"""
        self.db.execute(sql, (dynasty_id, season, team_id, season_type))

    def _record_loss(
        self,
        dynasty_id: str,
        season: int,
        team_id: int,
        is_home: bool,
        is_divisional: bool,
        is_conference: bool,
        season_type: str
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

        sql = f"""UPDATE standings SET {', '.join(updates)}
                  WHERE dynasty_id = ? AND season = ? AND team_id = ? AND season_type = ?"""
        self.db.execute(sql, (dynasty_id, season, team_id, season_type))

    def _record_tie(
        self,
        dynasty_id: str,
        season: int,
        team_id: int,
        season_type: str
    ) -> None:
        """Record a tie for a team."""
        self.db.execute(
            """UPDATE standings SET ties = ties + 1
               WHERE dynasty_id = ? AND season = ? AND team_id = ? AND season_type = ?""",
            (dynasty_id, season, team_id, season_type)
        )

    def _update_points(
        self,
        dynasty_id: str,
        season: int,
        team_id: int,
        points_for: int,
        points_against: int,
        season_type: str
    ) -> None:
        """Update points for/against for a team."""
        self.db.execute(
            """UPDATE standings
               SET points_for = points_for + ?,
                   points_against = points_against + ?
               WHERE dynasty_id = ? AND season = ? AND team_id = ? AND season_type = ?""",
            (points_for, points_against, dynasty_id, season, team_id, season_type)
        )

    def _row_to_standing(self, row) -> TeamStanding:
        """Convert database row to TeamStanding."""
        return TeamStanding(
            team_id=row['team_id'],
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