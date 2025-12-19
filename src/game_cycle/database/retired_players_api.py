"""
Retired Players API - Database operations for player retirements and career summaries.

Handles database operations for the retirement system including:
- Retired player records with retirement reasons
- Career summaries with lifetime statistics
- Hall of Fame eligibility tracking
- One-day contract ceremonies
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any
import json
import logging

from .connection import GameCycleDatabase

logger = logging.getLogger(__name__)


# ============================================
# Dataclasses
# ============================================

@dataclass
class RetiredPlayer:
    """Represents a retired player record."""
    player_id: int
    retirement_season: int
    retirement_reason: str
    final_team_id: int
    years_played: int
    age_at_retirement: int
    one_day_contract_team_id: Optional[int] = None
    hall_of_fame_eligible_season: Optional[int] = None
    created_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'player_id': self.player_id,
            'retirement_season': self.retirement_season,
            'retirement_reason': self.retirement_reason,
            'final_team_id': self.final_team_id,
            'years_played': self.years_played,
            'age_at_retirement': self.age_at_retirement,
            'one_day_contract_team_id': self.one_day_contract_team_id,
            'hall_of_fame_eligible_season': self.hall_of_fame_eligible_season,
            'created_at': self.created_at,
        }


@dataclass
class CareerSummary:
    """Represents a complete career summary for a retired player."""
    player_id: int
    full_name: str
    position: str
    # Draft info
    draft_year: Optional[int] = None
    draft_round: Optional[int] = None
    draft_pick: Optional[int] = None
    # Career totals
    games_played: int = 0
    games_started: int = 0
    # Passing
    pass_yards: int = 0
    pass_tds: int = 0
    pass_ints: int = 0
    # Rushing
    rush_yards: int = 0
    rush_tds: int = 0
    # Receiving
    receptions: int = 0
    rec_yards: int = 0
    rec_tds: int = 0
    # Defense
    tackles: int = 0
    sacks: float = 0.0
    interceptions: int = 0
    forced_fumbles: int = 0
    # Kicking
    fg_made: int = 0
    fg_attempted: int = 0
    # Accomplishments
    pro_bowls: int = 0
    all_pro_first_team: int = 0
    all_pro_second_team: int = 0
    mvp_awards: int = 0
    super_bowl_wins: int = 0
    super_bowl_mvps: int = 0
    # Teams
    teams_played_for: Optional[List[int]] = None
    primary_team_id: Optional[int] = None
    # Calculated
    career_approximate_value: int = 0
    hall_of_fame_score: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'player_id': self.player_id,
            'full_name': self.full_name,
            'position': self.position,
            'draft_year': self.draft_year,
            'draft_round': self.draft_round,
            'draft_pick': self.draft_pick,
            'games_played': self.games_played,
            'games_started': self.games_started,
            'pass_yards': self.pass_yards,
            'pass_tds': self.pass_tds,
            'pass_ints': self.pass_ints,
            'rush_yards': self.rush_yards,
            'rush_tds': self.rush_tds,
            'receptions': self.receptions,
            'rec_yards': self.rec_yards,
            'rec_tds': self.rec_tds,
            'tackles': self.tackles,
            'sacks': self.sacks,
            'interceptions': self.interceptions,
            'forced_fumbles': self.forced_fumbles,
            'fg_made': self.fg_made,
            'fg_attempted': self.fg_attempted,
            'pro_bowls': self.pro_bowls,
            'all_pro_first_team': self.all_pro_first_team,
            'all_pro_second_team': self.all_pro_second_team,
            'mvp_awards': self.mvp_awards,
            'super_bowl_wins': self.super_bowl_wins,
            'super_bowl_mvps': self.super_bowl_mvps,
            'teams_played_for': self.teams_played_for,
            'primary_team_id': self.primary_team_id,
            'career_approximate_value': self.career_approximate_value,
            'hall_of_fame_score': self.hall_of_fame_score,
        }


# ============================================
# RetiredPlayersAPI Class
# ============================================

class RetiredPlayersAPI:
    """
    API for Retired Players database operations.

    Handles:
    - Retired player records with retirement metadata
    - Career summaries with lifetime statistics
    - Hall of Fame eligibility tracking
    - One-day contract ceremonies
    """

    def __init__(self, db: GameCycleDatabase):
        """
        Initialize with database connection.

        Args:
            db: GameCycleDatabase instance
        """
        self.db = db

    # ============================================
    # Retired Players - CRUD Methods
    # ============================================

    def insert_retired_player(
        self,
        dynasty_id: str,
        player: RetiredPlayer
    ) -> int:
        """
        Insert a retired player record.

        Args:
            dynasty_id: Dynasty identifier
            player: RetiredPlayer dataclass

        Returns:
            Row ID of inserted record
        """
        # Calculate HOF eligibility (retirement + 5 years)
        hof_eligible_season = player.retirement_season + 5

        cursor = self.db.execute(
            """INSERT INTO retired_players
               (dynasty_id, player_id, retirement_season, retirement_reason,
                final_team_id, years_played, age_at_retirement,
                one_day_contract_team_id, hall_of_fame_eligible_season)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                dynasty_id,
                player.player_id,
                player.retirement_season,
                player.retirement_reason,
                player.final_team_id,
                player.years_played,
                player.age_at_retirement,
                player.one_day_contract_team_id,
                hof_eligible_season
            )
        )
        return cursor.lastrowid

    def get_retired_player(
        self,
        dynasty_id: str,
        player_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Get retired player record.

        Args:
            dynasty_id: Dynasty identifier
            player_id: Player ID

        Returns:
            Dictionary with retirement data, or None if not found
        """
        row = self.db.query_one(
            """SELECT dynasty_id, player_id, retirement_season, retirement_reason,
                      final_team_id, years_played, age_at_retirement,
                      one_day_contract_team_id, hall_of_fame_eligible_season,
                      created_at
               FROM retired_players
               WHERE dynasty_id = ? AND player_id = ?""",
            (dynasty_id, player_id)
        )
        if not row:
            return None

        return {
            'dynasty_id': row['dynasty_id'],
            'player_id': row['player_id'],
            'retirement_season': row['retirement_season'],
            'retirement_reason': row['retirement_reason'],
            'final_team_id': row['final_team_id'],
            'years_played': row['years_played'],
            'age_at_retirement': row['age_at_retirement'],
            'one_day_contract_team_id': row['one_day_contract_team_id'],
            'hall_of_fame_eligible_season': row['hall_of_fame_eligible_season'],
            'created_at': row['created_at'],
        }

    def get_retirements_by_season(
        self,
        dynasty_id: str,
        season: int
    ) -> List[Dict[str, Any]]:
        """
        Get all retirements for a specific season.

        Args:
            dynasty_id: Dynasty identifier
            season: Season year

        Returns:
            List of retirement records sorted by player_id
        """
        rows = self.db.query_all(
            """SELECT dynasty_id, player_id, retirement_season, retirement_reason,
                      final_team_id, years_played, age_at_retirement,
                      one_day_contract_team_id, hall_of_fame_eligible_season,
                      created_at
               FROM retired_players
               WHERE dynasty_id = ? AND retirement_season = ?
               ORDER BY player_id""",
            (dynasty_id, season)
        )

        return [{
            'dynasty_id': row['dynasty_id'],
            'player_id': row['player_id'],
            'retirement_season': row['retirement_season'],
            'retirement_reason': row['retirement_reason'],
            'final_team_id': row['final_team_id'],
            'years_played': row['years_played'],
            'age_at_retirement': row['age_at_retirement'],
            'one_day_contract_team_id': row['one_day_contract_team_id'],
            'hall_of_fame_eligible_season': row['hall_of_fame_eligible_season'],
            'created_at': row['created_at'],
        } for row in rows]

    def get_retirements_by_team(
        self,
        dynasty_id: str,
        team_id: int
    ) -> List[Dict[str, Any]]:
        """
        Get all retirements where player's final team was the specified team.

        Args:
            dynasty_id: Dynasty identifier
            team_id: Team ID (1-32)

        Returns:
            List of retirement records sorted by retirement_season DESC
        """
        rows = self.db.query_all(
            """SELECT dynasty_id, player_id, retirement_season, retirement_reason,
                      final_team_id, years_played, age_at_retirement,
                      one_day_contract_team_id, hall_of_fame_eligible_season,
                      created_at
               FROM retired_players
               WHERE dynasty_id = ? AND final_team_id = ?
               ORDER BY retirement_season DESC""",
            (dynasty_id, team_id)
        )

        return [{
            'dynasty_id': row['dynasty_id'],
            'player_id': row['player_id'],
            'retirement_season': row['retirement_season'],
            'retirement_reason': row['retirement_reason'],
            'final_team_id': row['final_team_id'],
            'years_played': row['years_played'],
            'age_at_retirement': row['age_at_retirement'],
            'one_day_contract_team_id': row['one_day_contract_team_id'],
            'hall_of_fame_eligible_season': row['hall_of_fame_eligible_season'],
            'created_at': row['created_at'],
        } for row in rows]

    def get_hof_eligible_players(
        self,
        dynasty_id: str,
        season: int
    ) -> List[Dict[str, Any]]:
        """
        Get all players eligible for Hall of Fame in specified season.

        Args:
            dynasty_id: Dynasty identifier
            season: Current season year

        Returns:
            List of retirement records eligible for HOF this season
        """
        rows = self.db.query_all(
            """SELECT dynasty_id, player_id, retirement_season, retirement_reason,
                      final_team_id, years_played, age_at_retirement,
                      one_day_contract_team_id, hall_of_fame_eligible_season,
                      created_at
               FROM retired_players
               WHERE dynasty_id = ? AND hall_of_fame_eligible_season = ?
               ORDER BY player_id""",
            (dynasty_id, season)
        )

        return [{
            'dynasty_id': row['dynasty_id'],
            'player_id': row['player_id'],
            'retirement_season': row['retirement_season'],
            'retirement_reason': row['retirement_reason'],
            'final_team_id': row['final_team_id'],
            'years_played': row['years_played'],
            'age_at_retirement': row['age_at_retirement'],
            'one_day_contract_team_id': row['one_day_contract_team_id'],
            'hall_of_fame_eligible_season': row['hall_of_fame_eligible_season'],
            'created_at': row['created_at'],
        } for row in rows]

    def update_one_day_contract(
        self,
        dynasty_id: str,
        player_id: int,
        team_id: int
    ) -> bool:
        """
        Update retired player with one-day contract team.

        Args:
            dynasty_id: Dynasty identifier
            player_id: Player ID
            team_id: Team ID for ceremonial signing (1-32)

        Returns:
            True if successful, False if player not found
        """
        cursor = self.db.execute(
            """UPDATE retired_players
               SET one_day_contract_team_id = ?
               WHERE dynasty_id = ? AND player_id = ?""",
            (team_id, dynasty_id, player_id)
        )
        return cursor.rowcount > 0

    def is_player_retired(
        self,
        dynasty_id: str,
        player_id: int
    ) -> bool:
        """
        Check if a player is retired.

        Args:
            dynasty_id: Dynasty identifier
            player_id: Player ID

        Returns:
            True if player is retired
        """
        row = self.db.query_one(
            """SELECT COUNT(*) as count
               FROM retired_players
               WHERE dynasty_id = ? AND player_id = ?""",
            (dynasty_id, player_id)
        )
        return row is not None and row['count'] > 0

    def delete_retired_player(
        self,
        dynasty_id: str,
        player_id: int
    ) -> int:
        """
        Delete a retired player record.

        Args:
            dynasty_id: Dynasty identifier
            player_id: Player ID

        Returns:
            Number of records deleted (0 or 1)
        """
        cursor = self.db.execute(
            """DELETE FROM retired_players
               WHERE dynasty_id = ? AND player_id = ?""",
            (dynasty_id, player_id)
        )
        return cursor.rowcount

    # ============================================
    # Career Summaries - CRUD Methods
    # ============================================

    def insert_career_summary(
        self,
        dynasty_id: str,
        summary: CareerSummary
    ) -> int:
        """
        Insert a career summary record.

        Args:
            dynasty_id: Dynasty identifier
            summary: CareerSummary dataclass

        Returns:
            Row ID of inserted record
        """
        # Serialize teams_played_for list to JSON
        teams_json = json.dumps(summary.teams_played_for) if summary.teams_played_for else None

        cursor = self.db.execute(
            """INSERT INTO career_summaries
               (dynasty_id, player_id, full_name, position,
                draft_year, draft_round, draft_pick,
                games_played, games_started,
                pass_yards, pass_tds, pass_ints,
                rush_yards, rush_tds,
                receptions, rec_yards, rec_tds,
                tackles, sacks, interceptions, forced_fumbles,
                fg_made, fg_attempted,
                pro_bowls, all_pro_first_team, all_pro_second_team,
                mvp_awards, super_bowl_wins, super_bowl_mvps,
                teams_played_for, primary_team_id,
                career_approximate_value, hall_of_fame_score)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                dynasty_id,
                summary.player_id,
                summary.full_name,
                summary.position,
                summary.draft_year,
                summary.draft_round,
                summary.draft_pick,
                summary.games_played,
                summary.games_started,
                summary.pass_yards,
                summary.pass_tds,
                summary.pass_ints,
                summary.rush_yards,
                summary.rush_tds,
                summary.receptions,
                summary.rec_yards,
                summary.rec_tds,
                summary.tackles,
                summary.sacks,
                summary.interceptions,
                summary.forced_fumbles,
                summary.fg_made,
                summary.fg_attempted,
                summary.pro_bowls,
                summary.all_pro_first_team,
                summary.all_pro_second_team,
                summary.mvp_awards,
                summary.super_bowl_wins,
                summary.super_bowl_mvps,
                teams_json,
                summary.primary_team_id,
                summary.career_approximate_value,
                summary.hall_of_fame_score
            )
        )
        return cursor.lastrowid

    def get_career_summary(
        self,
        dynasty_id: str,
        player_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Get career summary for a retired player.

        Args:
            dynasty_id: Dynasty identifier
            player_id: Player ID

        Returns:
            Dictionary with career summary data, or None if not found
        """
        row = self.db.query_one(
            """SELECT dynasty_id, player_id, full_name, position,
                      draft_year, draft_round, draft_pick,
                      games_played, games_started,
                      pass_yards, pass_tds, pass_ints,
                      rush_yards, rush_tds,
                      receptions, rec_yards, rec_tds,
                      tackles, sacks, interceptions, forced_fumbles,
                      fg_made, fg_attempted,
                      pro_bowls, all_pro_first_team, all_pro_second_team,
                      mvp_awards, super_bowl_wins, super_bowl_mvps,
                      teams_played_for, primary_team_id,
                      career_approximate_value, hall_of_fame_score,
                      created_at
               FROM career_summaries
               WHERE dynasty_id = ? AND player_id = ?""",
            (dynasty_id, player_id)
        )
        if not row:
            return None

        # Deserialize teams_played_for JSON
        teams_played_for = None
        if row['teams_played_for']:
            try:
                teams_played_for = json.loads(row['teams_played_for'])
            except (json.JSONDecodeError, TypeError):
                logger.warning(f"Failed to parse teams_played_for for player {player_id}")

        return {
            'dynasty_id': row['dynasty_id'],
            'player_id': row['player_id'],
            'full_name': row['full_name'],
            'position': row['position'],
            'draft_year': row['draft_year'],
            'draft_round': row['draft_round'],
            'draft_pick': row['draft_pick'],
            'games_played': row['games_played'],
            'games_started': row['games_started'],
            'pass_yards': row['pass_yards'],
            'pass_tds': row['pass_tds'],
            'pass_ints': row['pass_ints'],
            'rush_yards': row['rush_yards'],
            'rush_tds': row['rush_tds'],
            'receptions': row['receptions'],
            'rec_yards': row['rec_yards'],
            'rec_tds': row['rec_tds'],
            'tackles': row['tackles'],
            'sacks': row['sacks'],
            'interceptions': row['interceptions'],
            'forced_fumbles': row['forced_fumbles'],
            'fg_made': row['fg_made'],
            'fg_attempted': row['fg_attempted'],
            'pro_bowls': row['pro_bowls'],
            'all_pro_first_team': row['all_pro_first_team'],
            'all_pro_second_team': row['all_pro_second_team'],
            'mvp_awards': row['mvp_awards'],
            'super_bowl_wins': row['super_bowl_wins'],
            'super_bowl_mvps': row['super_bowl_mvps'],
            'teams_played_for': teams_played_for,
            'primary_team_id': row['primary_team_id'],
            'career_approximate_value': row['career_approximate_value'],
            'hall_of_fame_score': row['hall_of_fame_score'],
            'created_at': row['created_at'],
        }

    def get_top_careers_by_position(
        self,
        dynasty_id: str,
        position: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get top career summaries for a position by HOF score.

        Args:
            dynasty_id: Dynasty identifier
            position: Position abbreviation (QB, RB, etc.)
            limit: Maximum number of results (default 10)

        Returns:
            List of career summaries sorted by HOF score descending
        """
        rows = self.db.query_all(
            """SELECT dynasty_id, player_id, full_name, position,
                      draft_year, draft_round, draft_pick,
                      games_played, games_started,
                      pass_yards, pass_tds, pass_ints,
                      rush_yards, rush_tds,
                      receptions, rec_yards, rec_tds,
                      tackles, sacks, interceptions, forced_fumbles,
                      fg_made, fg_attempted,
                      pro_bowls, all_pro_first_team, all_pro_second_team,
                      mvp_awards, super_bowl_wins, super_bowl_mvps,
                      teams_played_for, primary_team_id,
                      career_approximate_value, hall_of_fame_score,
                      created_at
               FROM career_summaries
               WHERE dynasty_id = ? AND position = ?
               ORDER BY hall_of_fame_score DESC
               LIMIT ?""",
            (dynasty_id, position, limit)
        )

        results = []
        for row in rows:
            # Deserialize teams_played_for JSON
            teams_played_for = None
            if row['teams_played_for']:
                try:
                    teams_played_for = json.loads(row['teams_played_for'])
                except (json.JSONDecodeError, TypeError):
                    pass

            results.append({
                'dynasty_id': row['dynasty_id'],
                'player_id': row['player_id'],
                'full_name': row['full_name'],
                'position': row['position'],
                'draft_year': row['draft_year'],
                'draft_round': row['draft_round'],
                'draft_pick': row['draft_pick'],
                'games_played': row['games_played'],
                'games_started': row['games_started'],
                'pass_yards': row['pass_yards'],
                'pass_tds': row['pass_tds'],
                'pass_ints': row['pass_ints'],
                'rush_yards': row['rush_yards'],
                'rush_tds': row['rush_tds'],
                'receptions': row['receptions'],
                'rec_yards': row['rec_yards'],
                'rec_tds': row['rec_tds'],
                'tackles': row['tackles'],
                'sacks': row['sacks'],
                'interceptions': row['interceptions'],
                'forced_fumbles': row['forced_fumbles'],
                'fg_made': row['fg_made'],
                'fg_attempted': row['fg_attempted'],
                'pro_bowls': row['pro_bowls'],
                'all_pro_first_team': row['all_pro_first_team'],
                'all_pro_second_team': row['all_pro_second_team'],
                'mvp_awards': row['mvp_awards'],
                'super_bowl_wins': row['super_bowl_wins'],
                'super_bowl_mvps': row['super_bowl_mvps'],
                'teams_played_for': teams_played_for,
                'primary_team_id': row['primary_team_id'],
                'career_approximate_value': row['career_approximate_value'],
                'hall_of_fame_score': row['hall_of_fame_score'],
                'created_at': row['created_at'],
            })

        return results

    def get_hof_candidates(
        self,
        dynasty_id: str,
        min_score: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get all career summaries with HOF score above threshold.

        Args:
            dynasty_id: Dynasty identifier
            min_score: Minimum HOF score (default 50)

        Returns:
            List of career summaries sorted by HOF score descending
        """
        rows = self.db.query_all(
            """SELECT dynasty_id, player_id, full_name, position,
                      draft_year, draft_round, draft_pick,
                      games_played, games_started,
                      pass_yards, pass_tds, pass_ints,
                      rush_yards, rush_tds,
                      receptions, rec_yards, rec_tds,
                      tackles, sacks, interceptions, forced_fumbles,
                      fg_made, fg_attempted,
                      pro_bowls, all_pro_first_team, all_pro_second_team,
                      mvp_awards, super_bowl_wins, super_bowl_mvps,
                      teams_played_for, primary_team_id,
                      career_approximate_value, hall_of_fame_score,
                      created_at
               FROM career_summaries
               WHERE dynasty_id = ? AND hall_of_fame_score >= ?
               ORDER BY hall_of_fame_score DESC""",
            (dynasty_id, min_score)
        )

        results = []
        for row in rows:
            # Deserialize teams_played_for JSON
            teams_played_for = None
            if row['teams_played_for']:
                try:
                    teams_played_for = json.loads(row['teams_played_for'])
                except (json.JSONDecodeError, TypeError):
                    pass

            results.append({
                'dynasty_id': row['dynasty_id'],
                'player_id': row['player_id'],
                'full_name': row['full_name'],
                'position': row['position'],
                'draft_year': row['draft_year'],
                'draft_round': row['draft_round'],
                'draft_pick': row['draft_pick'],
                'games_played': row['games_played'],
                'games_started': row['games_started'],
                'pass_yards': row['pass_yards'],
                'pass_tds': row['pass_tds'],
                'pass_ints': row['pass_ints'],
                'rush_yards': row['rush_yards'],
                'rush_tds': row['rush_tds'],
                'receptions': row['receptions'],
                'rec_yards': row['rec_yards'],
                'rec_tds': row['rec_tds'],
                'tackles': row['tackles'],
                'sacks': row['sacks'],
                'interceptions': row['interceptions'],
                'forced_fumbles': row['forced_fumbles'],
                'fg_made': row['fg_made'],
                'fg_attempted': row['fg_attempted'],
                'pro_bowls': row['pro_bowls'],
                'all_pro_first_team': row['all_pro_first_team'],
                'all_pro_second_team': row['all_pro_second_team'],
                'mvp_awards': row['mvp_awards'],
                'super_bowl_wins': row['super_bowl_wins'],
                'super_bowl_mvps': row['super_bowl_mvps'],
                'teams_played_for': teams_played_for,
                'primary_team_id': row['primary_team_id'],
                'career_approximate_value': row['career_approximate_value'],
                'hall_of_fame_score': row['hall_of_fame_score'],
                'created_at': row['created_at'],
            })

        return results

    def update_hof_score(
        self,
        dynasty_id: str,
        player_id: int,
        score: int
    ) -> bool:
        """
        Update Hall of Fame score for a career summary.

        Args:
            dynasty_id: Dynasty identifier
            player_id: Player ID
            score: New HOF score (0-100)

        Returns:
            True if successful, False if player not found
        """
        cursor = self.db.execute(
            """UPDATE career_summaries
               SET hall_of_fame_score = ?
               WHERE dynasty_id = ? AND player_id = ?""",
            (score, dynasty_id, player_id)
        )
        return cursor.rowcount > 0

    # ============================================
    # Helper Methods
    # ============================================

    def _row_to_retired_player(self, row) -> RetiredPlayer:
        """
        Convert database row to RetiredPlayer dataclass.

        Args:
            row: SQLite row object

        Returns:
            RetiredPlayer instance
        """
        return RetiredPlayer(
            player_id=row['player_id'],
            retirement_season=row['retirement_season'],
            retirement_reason=row['retirement_reason'],
            final_team_id=row['final_team_id'],
            years_played=row['years_played'],
            age_at_retirement=row['age_at_retirement'],
            one_day_contract_team_id=row['one_day_contract_team_id'],
            hall_of_fame_eligible_season=row['hall_of_fame_eligible_season'],
            created_at=row['created_at'],
        )

    def _row_to_career_summary(self, row) -> CareerSummary:
        """
        Convert database row to CareerSummary dataclass.

        Args:
            row: SQLite row object

        Returns:
            CareerSummary instance
        """
        # Deserialize teams_played_for JSON
        teams_played_for = None
        if row['teams_played_for']:
            try:
                teams_played_for = json.loads(row['teams_played_for'])
            except (json.JSONDecodeError, TypeError):
                logger.warning(f"Failed to parse teams_played_for for player {row['player_id']}")

        return CareerSummary(
            player_id=row['player_id'],
            full_name=row['full_name'],
            position=row['position'],
            draft_year=row['draft_year'],
            draft_round=row['draft_round'],
            draft_pick=row['draft_pick'],
            games_played=row['games_played'],
            games_started=row['games_started'],
            pass_yards=row['pass_yards'],
            pass_tds=row['pass_tds'],
            pass_ints=row['pass_ints'],
            rush_yards=row['rush_yards'],
            rush_tds=row['rush_tds'],
            receptions=row['receptions'],
            rec_yards=row['rec_yards'],
            rec_tds=row['rec_tds'],
            tackles=row['tackles'],
            sacks=row['sacks'],
            interceptions=row['interceptions'],
            forced_fumbles=row['forced_fumbles'],
            fg_made=row['fg_made'],
            fg_attempted=row['fg_attempted'],
            pro_bowls=row['pro_bowls'],
            all_pro_first_team=row['all_pro_first_team'],
            all_pro_second_team=row['all_pro_second_team'],
            mvp_awards=row['mvp_awards'],
            super_bowl_wins=row['super_bowl_wins'],
            super_bowl_mvps=row['super_bowl_mvps'],
            teams_played_for=teams_played_for,
            primary_team_id=row['primary_team_id'],
            career_approximate_value=row['career_approximate_value'],
            hall_of_fame_score=row['hall_of_fame_score'],
        )
