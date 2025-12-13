"""
Box Scores API for game_cycle.

Handles insertion and retrieval of box score data for games.
Box scores aggregate team-level stats per game.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any
import sqlite3


@dataclass
class BoxScore:
    """
    Represents a team's box score for a single game.

    Contains quarter-by-quarter scoring and team stat totals.
    """
    game_id: str
    team_id: int
    dynasty_id: str

    # Quarter scores
    q1_score: int = 0
    q2_score: int = 0
    q3_score: int = 0
    q4_score: int = 0
    ot_score: int = 0

    # Team totals
    first_downs: int = 0
    third_down_att: int = 0
    third_down_conv: int = 0
    fourth_down_att: int = 0
    fourth_down_conv: int = 0

    total_yards: int = 0
    passing_yards: int = 0
    rushing_yards: int = 0

    turnovers: int = 0
    penalties: int = 0
    penalty_yards: int = 0

    time_of_possession: Optional[int] = None  # in seconds

    # Timeout tracking
    team_timeouts_remaining: int = 3     # Timeouts at end of game (0-3)
    team_timeouts_used_h1: int = 0       # Timeouts used in first half (0-3)
    team_timeouts_used_h2: int = 0       # Timeouts used in second half (0-3)

    @property
    def total_score(self) -> int:
        """Calculate total score from quarter scores."""
        return self.q1_score + self.q2_score + self.q3_score + self.q4_score + self.ot_score

    @property
    def third_down_pct(self) -> float:
        """Calculate third down conversion percentage."""
        if self.third_down_att == 0:
            return 0.0
        return self.third_down_conv / self.third_down_att

    @property
    def fourth_down_pct(self) -> float:
        """Calculate fourth down conversion percentage."""
        if self.fourth_down_att == 0:
            return 0.0
        return self.fourth_down_conv / self.fourth_down_att

    @property
    def time_of_possession_str(self) -> str:
        """Format time of possession as MM:SS."""
        if self.time_of_possession is None:
            return "N/A"
        minutes = self.time_of_possession // 60
        seconds = self.time_of_possession % 60
        return f"{minutes}:{seconds:02d}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "game_id": self.game_id,
            "team_id": self.team_id,
            "dynasty_id": self.dynasty_id,
            "q1_score": self.q1_score,
            "q2_score": self.q2_score,
            "q3_score": self.q3_score,
            "q4_score": self.q4_score,
            "ot_score": self.ot_score,
            "total_score": self.total_score,
            "first_downs": self.first_downs,
            "third_down_att": self.third_down_att,
            "third_down_conv": self.third_down_conv,
            "third_down_pct": self.third_down_pct,
            "fourth_down_att": self.fourth_down_att,
            "fourth_down_conv": self.fourth_down_conv,
            "fourth_down_pct": self.fourth_down_pct,
            "total_yards": self.total_yards,
            "passing_yards": self.passing_yards,
            "rushing_yards": self.rushing_yards,
            "turnovers": self.turnovers,
            "penalties": self.penalties,
            "penalty_yards": self.penalty_yards,
            "time_of_possession": self.time_of_possession,
            "time_of_possession_str": self.time_of_possession_str,
        }


class BoxScoresAPI:
    """
    API for box score operations in game_cycle.

    Handles:
    - Inserting box scores after game simulation
    - Retrieving box scores for games
    - Aggregating player stats into team box scores
    """

    def __init__(self, db_path: str):
        """
        Initialize with database path.

        Args:
            db_path: Path to the database file
        """
        self.db_path = db_path

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory."""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _execute(self, sql: str, params: tuple = ()) -> None:
        """Execute a SQL statement."""
        with self._get_connection() as conn:
            conn.execute(sql, params)
            conn.commit()

    def _query_one(self, sql: str, params: tuple = ()) -> Optional[sqlite3.Row]:
        """Execute query and return single row."""
        with self._get_connection() as conn:
            cursor = conn.execute(sql, params)
            return cursor.fetchone()

    def _query_all(self, sql: str, params: tuple = ()) -> List[sqlite3.Row]:
        """Execute query and return all rows."""
        with self._get_connection() as conn:
            cursor = conn.execute(sql, params)
            return cursor.fetchall()

    # -------------------- Insert Methods --------------------

    def insert_box_score(self, box_score: BoxScore) -> bool:
        """
        Insert a box score into the database.

        Uses INSERT OR REPLACE to handle re-simulation of games.

        Args:
            box_score: BoxScore dataclass instance

        Returns:
            True if successful
        """
        sql = """
            INSERT OR REPLACE INTO box_scores (
                dynasty_id, game_id, team_id,
                q1_score, q2_score, q3_score, q4_score, ot_score,
                first_downs, third_down_att, third_down_conv,
                fourth_down_att, fourth_down_conv,
                total_yards, passing_yards, rushing_yards,
                turnovers, penalties, penalty_yards,
                time_of_possession,
                team_timeouts_remaining, team_timeouts_used_h1, team_timeouts_used_h2
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        self._execute(sql, (
            box_score.dynasty_id,
            box_score.game_id,
            box_score.team_id,
            box_score.q1_score,
            box_score.q2_score,
            box_score.q3_score,
            box_score.q4_score,
            box_score.ot_score,
            box_score.first_downs,
            box_score.third_down_att,
            box_score.third_down_conv,
            box_score.fourth_down_att,
            box_score.fourth_down_conv,
            box_score.total_yards,
            box_score.passing_yards,
            box_score.rushing_yards,
            box_score.turnovers,
            box_score.penalties,
            box_score.penalty_yards,
            box_score.time_of_possession,
            box_score.team_timeouts_remaining,
            box_score.team_timeouts_used_h1,
            box_score.team_timeouts_used_h2,
        ))
        return True

    def insert_game_box_scores(
        self,
        dynasty_id: str,
        game_id: str,
        home_team_id: int,
        away_team_id: int,
        home_box: Dict[str, Any],
        away_box: Dict[str, Any]
    ) -> bool:
        """
        Insert box scores for both teams in a game.

        Convenience method to insert both home and away box scores at once.

        Args:
            dynasty_id: Dynasty identifier
            game_id: Game identifier
            home_team_id: Home team ID
            away_team_id: Away team ID
            home_box: Dict with home team stats
            away_box: Dict with away team stats

        Returns:
            True if both inserts successful
        """
        home_score = BoxScore(
            game_id=game_id,
            team_id=home_team_id,
            dynasty_id=dynasty_id,
            **self._normalize_box_dict(home_box)
        )
        away_score = BoxScore(
            game_id=game_id,
            team_id=away_team_id,
            dynasty_id=dynasty_id,
            **self._normalize_box_dict(away_box)
        )

        self.insert_box_score(home_score)
        self.insert_box_score(away_score)
        return True

    def _normalize_box_dict(self, box_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize box score dictionary to match BoxScore dataclass fields.

        Handles missing keys by providing defaults.
        """
        return {
            "q1_score": box_dict.get("q1_score", 0),
            "q2_score": box_dict.get("q2_score", 0),
            "q3_score": box_dict.get("q3_score", 0),
            "q4_score": box_dict.get("q4_score", 0),
            "ot_score": box_dict.get("ot_score", 0),
            "first_downs": box_dict.get("first_downs", 0),
            "third_down_att": box_dict.get("third_down_att", 0),
            "third_down_conv": box_dict.get("third_down_conv", 0),
            "fourth_down_att": box_dict.get("fourth_down_att", 0),
            "fourth_down_conv": box_dict.get("fourth_down_conv", 0),
            "total_yards": box_dict.get("total_yards", 0),
            "passing_yards": box_dict.get("passing_yards", 0),
            "rushing_yards": box_dict.get("rushing_yards", 0),
            "turnovers": box_dict.get("turnovers", 0),
            "penalties": box_dict.get("penalties", 0),
            "penalty_yards": box_dict.get("penalty_yards", 0),
            "time_of_possession": box_dict.get("time_of_possession"),
            "team_timeouts_remaining": box_dict.get("team_timeouts_remaining", 3),
            "team_timeouts_used_h1": box_dict.get("team_timeouts_used_h1", 0),
            "team_timeouts_used_h2": box_dict.get("team_timeouts_used_h2", 0),
        }

    # -------------------- Query Methods --------------------

    def get_box_score(
        self,
        dynasty_id: str,
        game_id: str,
        team_id: int
    ) -> Optional[BoxScore]:
        """
        Get box score for a specific team in a game.

        Args:
            dynasty_id: Dynasty identifier
            game_id: Game identifier
            team_id: Team ID

        Returns:
            BoxScore if found, None otherwise
        """
        row = self._query_one(
            """
            SELECT game_id, team_id, dynasty_id,
                   q1_score, q2_score, q3_score, q4_score, ot_score,
                   first_downs, third_down_att, third_down_conv,
                   fourth_down_att, fourth_down_conv,
                   total_yards, passing_yards, rushing_yards,
                   turnovers, penalties, penalty_yards,
                   time_of_possession
            FROM box_scores
            WHERE dynasty_id = ? AND game_id = ? AND team_id = ?
            """,
            (dynasty_id, game_id, team_id)
        )
        return self._row_to_box_score(row) if row else None

    def get_game_box_scores(
        self,
        dynasty_id: str,
        game_id: str
    ) -> List[BoxScore]:
        """
        Get both box scores for a game.

        Args:
            dynasty_id: Dynasty identifier
            game_id: Game identifier

        Returns:
            List of BoxScore (typically 2 - home and away)
        """
        rows = self._query_all(
            """
            SELECT game_id, team_id, dynasty_id,
                   q1_score, q2_score, q3_score, q4_score, ot_score,
                   first_downs, third_down_att, third_down_conv,
                   fourth_down_att, fourth_down_conv,
                   total_yards, passing_yards, rushing_yards,
                   turnovers, penalties, penalty_yards,
                   time_of_possession
            FROM box_scores
            WHERE dynasty_id = ? AND game_id = ?
            """,
            (dynasty_id, game_id)
        )
        return [self._row_to_box_score(row) for row in rows]

    def get_team_box_scores(
        self,
        dynasty_id: str,
        team_id: int,
        season: Optional[int] = None,
        limit: int = 20
    ) -> List[BoxScore]:
        """
        Get box scores for a team across games.

        Args:
            dynasty_id: Dynasty identifier
            team_id: Team ID
            season: Optional season filter (requires join with games table)
            limit: Maximum number of box scores to return

        Returns:
            List of BoxScore ordered by game
        """
        if season is not None:
            rows = self._query_all(
                """
                SELECT bs.game_id, bs.team_id, bs.dynasty_id,
                       bs.q1_score, bs.q2_score, bs.q3_score, bs.q4_score, bs.ot_score,
                       bs.first_downs, bs.third_down_att, bs.third_down_conv,
                       bs.fourth_down_att, bs.fourth_down_conv,
                       bs.total_yards, bs.passing_yards, bs.rushing_yards,
                       bs.turnovers, bs.penalties, bs.penalty_yards,
                       bs.time_of_possession
                FROM box_scores bs
                JOIN games g ON bs.game_id = g.game_id AND bs.dynasty_id = g.dynasty_id
                WHERE bs.dynasty_id = ? AND bs.team_id = ? AND g.season = ?
                ORDER BY g.week ASC
                LIMIT ?
                """,
                (dynasty_id, team_id, season, limit)
            )
        else:
            rows = self._query_all(
                """
                SELECT game_id, team_id, dynasty_id,
                       q1_score, q2_score, q3_score, q4_score, ot_score,
                       first_downs, third_down_att, third_down_conv,
                       fourth_down_att, fourth_down_conv,
                       total_yards, passing_yards, rushing_yards,
                       turnovers, penalties, penalty_yards,
                       time_of_possession
                FROM box_scores
                WHERE dynasty_id = ? AND team_id = ?
                ORDER BY game_id
                LIMIT ?
                """,
                (dynasty_id, team_id, limit)
            )
        return [self._row_to_box_score(row) for row in rows]

    # -------------------- Aggregation Methods --------------------

    def calculate_from_player_stats(
        self,
        dynasty_id: str,
        game_id: str,
        team_id: int
    ) -> BoxScore:
        """
        Calculate box score by aggregating player_game_stats.

        Used when box score not explicitly saved, computes:
        - total_yards, passing_yards, rushing_yards from player stats
        - turnovers from interceptions + fumbles

        Note: Quarter scores, first downs, conversion stats not available
        from player stats alone and will be zero.

        Args:
            dynasty_id: Dynasty identifier
            game_id: Game identifier
            team_id: Team ID

        Returns:
            BoxScore with aggregated stats
        """
        row = self._query_one(
            """
            SELECT
                COALESCE(SUM(passing_yards), 0) AS passing_yards,
                COALESCE(SUM(rushing_yards), 0) AS rushing_yards,
                COALESCE(SUM(receiving_yards), 0) AS receiving_yards,
                COALESCE(SUM(passing_interceptions), 0) AS interceptions_thrown,
                COALESCE(SUM(rushing_fumbles), 0) AS fumbles
            FROM player_game_stats
            WHERE dynasty_id = ? AND game_id = ? AND team_id = ?
            """,
            (dynasty_id, game_id, team_id)
        )

        if not row:
            return BoxScore(
                game_id=game_id,
                team_id=team_id,
                dynasty_id=dynasty_id
            )

        passing_yards = row['passing_yards'] or 0
        rushing_yards = row['rushing_yards'] or 0
        # Note: receiving_yards are included in passing_yards for team totals
        total_yards = passing_yards + rushing_yards
        turnovers = (row['interceptions_thrown'] or 0) + (row['fumbles'] or 0)

        return BoxScore(
            game_id=game_id,
            team_id=team_id,
            dynasty_id=dynasty_id,
            total_yards=total_yards,
            passing_yards=passing_yards,
            rushing_yards=rushing_yards,
            turnovers=turnovers
        )

    def get_or_calculate_box_score(
        self,
        dynasty_id: str,
        game_id: str,
        team_id: int
    ) -> BoxScore:
        """
        Get box score from table, or calculate from player stats if not found.

        Provides fallback for games where box_scores wasn't populated.

        Args:
            dynasty_id: Dynasty identifier
            game_id: Game identifier
            team_id: Team ID

        Returns:
            BoxScore from table or calculated from player stats
        """
        box_score = self.get_box_score(dynasty_id, game_id, team_id)
        if box_score:
            return box_score
        return self.calculate_from_player_stats(dynasty_id, game_id, team_id)

    @staticmethod
    def aggregate_from_player_stats(
        player_stats: List[Dict[str, Any]],
        team_id: int
    ) -> Dict[str, Any]:
        """
        Aggregate in-memory player stats into box score dict.

        Pure calculation - no database access. Used by handlers after
        game simulation to build box score data for persistence.

        Args:
            player_stats: List of player stat dicts from simulation
            team_id: Team to aggregate stats for

        Returns:
            Dict with box score fields ready for insert_game_box_scores()
        """
        # Filter stats for this team
        team_stats = [s for s in player_stats if s.get('team_id') == team_id]

        # Aggregate offensive stats
        passing_yards = sum(s.get('passing_yards', 0) or 0 for s in team_stats)
        rushing_yards = sum(s.get('rushing_yards', 0) or 0 for s in team_stats)
        total_yards = passing_yards + rushing_yards

        # Turnovers: interceptions thrown + fumbles lost
        interceptions = sum(s.get('passing_interceptions', 0) or 0 for s in team_stats)
        fumbles = sum(s.get('rushing_fumbles', 0) or 0 for s in team_stats)
        turnovers = interceptions + fumbles

        return {
            'total_yards': total_yards,
            'passing_yards': passing_yards,
            'rushing_yards': rushing_yards,
            'turnovers': turnovers,
            # Fields not available from player stats (leave as defaults)
            'first_downs': 0,
            'third_down_att': 0,
            'third_down_conv': 0,
            'fourth_down_att': 0,
            'fourth_down_conv': 0,
            'penalties': 0,
            'penalty_yards': 0,
            'time_of_possession': None,
            'q1_score': 0,
            'q2_score': 0,
            'q3_score': 0,
            'q4_score': 0,
            'ot_score': 0,
        }

    # -------------------- Private Methods --------------------

    def _row_to_box_score(self, row: sqlite3.Row) -> BoxScore:
        """Convert database row to BoxScore dataclass."""
        # Backwards compatibility: check if timeout fields exist in row
        row_keys = row.keys()

        return BoxScore(
            game_id=row['game_id'],
            team_id=row['team_id'],
            dynasty_id=row['dynasty_id'],
            q1_score=row['q1_score'] or 0,
            q2_score=row['q2_score'] or 0,
            q3_score=row['q3_score'] or 0,
            q4_score=row['q4_score'] or 0,
            ot_score=row['ot_score'] or 0,
            first_downs=row['first_downs'] or 0,
            third_down_att=row['third_down_att'] or 0,
            third_down_conv=row['third_down_conv'] or 0,
            fourth_down_att=row['fourth_down_att'] or 0,
            fourth_down_conv=row['fourth_down_conv'] or 0,
            total_yards=row['total_yards'] or 0,
            passing_yards=row['passing_yards'] or 0,
            rushing_yards=row['rushing_yards'] or 0,
            turnovers=row['turnovers'] or 0,
            penalties=row['penalties'] or 0,
            penalty_yards=row['penalty_yards'] or 0,
            time_of_possession=row['time_of_possession'],
            team_timeouts_remaining=row['team_timeouts_remaining'] if 'team_timeouts_remaining' in row_keys else 3,
            team_timeouts_used_h1=row['team_timeouts_used_h1'] if 'team_timeouts_used_h1' in row_keys else 0,
            team_timeouts_used_h2=row['team_timeouts_used_h2'] if 'team_timeouts_used_h2' in row_keys else 0,
        )