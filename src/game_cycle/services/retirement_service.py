"""
Retirement Service for Game Cycle.

Orchestrates player retirement processing during OFFSEASON_HONORS stage:
- Evaluates all players for retirement using RetirementDecisionEngine
- Generates career summaries using CareerSummaryGenerator
- Persists retirement records and career summaries to database
- Removes retired players from active rosters
- Generates retirement headlines for media coverage
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set
import json
import logging
import sqlite3

from src.game_cycle.database.connection import GameCycleDatabase
from src.game_cycle.database.retired_players_api import (
    RetiredPlayersAPI,
    RetiredPlayer,
    CareerSummary,
)
from src.game_cycle.services.retirement_decision_engine import (
    RetirementDecisionEngine,
    RetirementContext,
    RetirementReason,
)
from src.game_cycle.services.career_summary_generator import CareerSummaryGenerator


# ============================================
# Result Dataclasses
# ============================================

@dataclass
class RetirementResult:
    """Result of processing a single player retirement."""
    player_id: int
    player_name: str
    position: str
    age: int
    reason: str  # 'age_decline', 'injury', 'championship', 'released', etc.
    years_played: int
    final_team_id: int
    career_summary: CareerSummary
    is_notable: bool  # Pro Bowler, MVP, champion, etc.
    headline: str  # Generated headline for media

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'player_id': self.player_id,
            'player_name': self.player_name,
            'position': self.position,
            'age': self.age,
            'reason': self.reason,
            'years_played': self.years_played,
            'final_team_id': self.final_team_id,
            'career_summary': self.career_summary.to_dict(),
            'is_notable': self.is_notable,
            'headline': self.headline,
        }


@dataclass
class SeasonRetirementSummary:
    """Summary of all retirements for a season."""
    season: int
    total_retirements: int
    notable_retirements: List[RetirementResult] = field(default_factory=list)
    other_retirements: List[RetirementResult] = field(default_factory=list)
    user_team_retirements: List[RetirementResult] = field(default_factory=list)
    events: List[str] = field(default_factory=list)  # Event strings for handler

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'season': self.season,
            'total_retirements': self.total_retirements,
            'notable_retirements': [r.to_dict() for r in self.notable_retirements],
            'other_retirements': [r.to_dict() for r in self.other_retirements],
            'user_team_retirements': [r.to_dict() for r in self.user_team_retirements],
            'events': self.events,
        }


# ============================================
# Main Service Class
# ============================================

class RetirementService:
    """
    Service for processing player retirements at end of season.

    Integrates with:
    - RetirementDecisionEngine: Determines which players retire
    - CareerSummaryGenerator: Creates career retrospectives
    - RetiredPlayersAPI: Persists retirement data

    Called during OFFSEASON_HONORS stage after awards calculation.
    """

    def __init__(self, db_path: str, dynasty_id: str, season: int):
        """
        Initialize the retirement service.

        Args:
            db_path: Path to the game cycle database
            dynasty_id: Dynasty identifier for isolation
            season: Current season year (retirement season)
        """
        self._db_path = db_path
        self._dynasty_id = dynasty_id
        self._season = season
        self._logger = logging.getLogger(__name__)

        # Initialize dependent services
        self._decision_engine = RetirementDecisionEngine(db_path, dynasty_id, season)
        self._summary_generator = CareerSummaryGenerator(db_path, dynasty_id)

    # =========================================================================
    # Public API
    # =========================================================================

    def process_post_season_retirements(
        self,
        super_bowl_winner_team_id: Optional[int] = None,
        user_team_id: Optional[int] = None
    ) -> SeasonRetirementSummary:
        """
        Process all player retirements after season ends.

        Called during OFFSEASON_HONORS stage after awards calculation.

        Args:
            super_bowl_winner_team_id: Team that won Super Bowl (if any)
            user_team_id: User's team for filtering in results

        Returns:
            SeasonRetirementSummary with all retirement data
        """
        events = []
        notable_retirements = []
        other_retirements = []
        user_team_retirements = []

        # Get all active players
        all_players = self._get_all_active_players()
        events.append(f"Evaluating {len(all_players)} players for retirement")

        # Build retirement context
        context = self._build_retirement_context(super_bowl_winner_team_id)

        # Get players who will retire
        retiring_candidates = self._decision_engine.get_retiring_players(all_players, context)
        events.append(f"{len(retiring_candidates)} players decided to retire")

        # Process each retirement
        for candidate in retiring_candidates:
            try:
                # Find the player dict for this candidate
                player_dict = next(
                    (p for p in all_players if p['player_id'] == candidate.player_id),
                    None
                )
                if not player_dict:
                    self._logger.warning(
                        f"Could not find player dict for retiring player {candidate.player_id}"
                    )
                    continue

                # Process the retirement
                result = self._process_single_retirement(player_dict, candidate.reason)

                # Categorize the result
                if result.is_notable:
                    notable_retirements.append(result)
                    events.append(f"Notable retirement: {result.headline}")
                else:
                    other_retirements.append(result)

                # Track user team retirements
                if user_team_id and result.final_team_id == user_team_id:
                    user_team_retirements.append(result)

            except Exception as e:
                self._logger.error(
                    f"Error processing retirement for player {candidate.player_id}: {e}"
                )
                events.append(f"Error processing retirement: {str(e)}")

        return SeasonRetirementSummary(
            season=self._season,
            total_retirements=len(notable_retirements) + len(other_retirements),
            notable_retirements=notable_retirements,
            other_retirements=other_retirements,
            user_team_retirements=user_team_retirements,
            events=events,
        )

    def retirements_already_processed(self) -> bool:
        """
        Check if retirements have already been processed for this season.

        Used for idempotency - prevents duplicate processing on stage re-entry.

        Returns:
            True if retirements exist for this season
        """
        try:
            conn = sqlite3.connect(self._db_path)
            cursor = conn.cursor()
            cursor.execute(
                """SELECT COUNT(*) as count
                   FROM retired_players
                   WHERE dynasty_id = ? AND retirement_season = ?""",
                (self._dynasty_id, self._season)
            )
            row = cursor.fetchone()
            conn.close()
            return row[0] > 0 if row else False
        except Exception as e:
            self._logger.warning(f"Error checking retirement status: {e}")
            return False

    def get_season_retirements(self) -> List[Dict[str, Any]]:
        """
        Get all retirements for current season.

        Returns:
            List of retirement records as dictionaries
        """
        retirements = []
        try:
            conn = sqlite3.connect(self._db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT player_id, retirement_season, retirement_reason,
                       final_team_id, years_played, age_at_retirement,
                       one_day_contract_team_id
                FROM retired_players
                WHERE dynasty_id = ? AND retirement_season = ?
            """, (self._dynasty_id, self._season))
            rows = cursor.fetchall()
            conn.close()

            retirements = [dict(row) for row in rows]
        except Exception as e:
            self._logger.warning(f"Error getting season retirements: {e}")

        return retirements

    def get_player_career_summary(self, player_id: int) -> Optional[Dict[str, Any]]:
        """
        Get career summary for a retired player.

        Args:
            player_id: Player ID

        Returns:
            Career summary dictionary, or None if not found
        """
        try:
            conn = sqlite3.connect(self._db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT player_id, full_name, position,
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
                       career_approximate_value, hall_of_fame_score
                FROM career_summaries
                WHERE dynasty_id = ? AND player_id = ?
            """, (self._dynasty_id, player_id))
            row = cursor.fetchone()
            conn.close()

            if row:
                summary_dict = dict(row)
                # Parse JSON teams_played_for if stored as string
                if isinstance(summary_dict.get('teams_played_for'), str):
                    try:
                        summary_dict['teams_played_for'] = json.loads(summary_dict['teams_played_for'])
                    except json.JSONDecodeError:
                        summary_dict['teams_played_for'] = []
                return summary_dict
            return None
        except Exception as e:
            self._logger.warning(f"Error getting career summary: {e}")
            return None

    def process_one_day_contract(self, player_id: int, team_id: int) -> bool:
        """
        Process ceremonial one-day contract signing.

        Allows a retired player to officially retire with a specific team.

        Args:
            player_id: Player ID
            team_id: Team ID for ceremonial signing (1-32)

        Returns:
            True if successful, False if player not found
        """
        try:
            conn = sqlite3.connect(self._db_path)
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE retired_players
                SET one_day_contract_team_id = ?
                WHERE dynasty_id = ? AND player_id = ?
            """, (team_id, self._dynasty_id, player_id))
            rows_updated = cursor.rowcount
            conn.commit()
            conn.close()
            return rows_updated > 0
        except Exception as e:
            self._logger.warning(f"Error processing one-day contract: {e}")
            return False

    # =========================================================================
    # Internal Methods - Player Collection
    # =========================================================================

    def _get_all_active_players(self) -> List[Dict[str, Any]]:
        """
        Get all active players across all 32 teams plus free agents.

        Returns:
            List of player dictionaries with full player data
        """
        from src.database.player_roster_api import PlayerRosterAPI
        from src.database.connection import DatabaseConnection

        all_players = []

        try:
            db_conn = DatabaseConnection(self._db_path)
            roster_api = PlayerRosterAPI(self._db_path, db_conn)

            # Get players from all 32 teams
            for team_id in range(1, 33):
                try:
                    roster = roster_api.get_full_roster(self._dynasty_id, team_id)
                    all_players.extend(roster)
                except ValueError:
                    # Team may not have roster initialized
                    continue
                except Exception as e:
                    self._logger.debug(f"Error getting roster for team {team_id}: {e}")
                    continue

            # Add free agents
            try:
                free_agents = roster_api.get_free_agents(self._dynasty_id)
                all_players.extend(free_agents)
            except Exception as e:
                self._logger.debug(f"Error getting free agents: {e}")

        except Exception as e:
            self._logger.error(f"Error getting all players: {e}")

        return all_players

    # =========================================================================
    # Internal Methods - Context Building
    # =========================================================================

    def _build_retirement_context(
        self,
        super_bowl_winner_team_id: Optional[int]
    ) -> RetirementContext:
        """
        Build context for retirement decisions.

        Args:
            super_bowl_winner_team_id: Team that won Super Bowl

        Returns:
            RetirementContext with all relevant data
        """
        return RetirementContext(
            season=self._season,
            super_bowl_winner_team_id=super_bowl_winner_team_id,
            released_player_ids=self._get_released_player_ids(),
            career_ending_injury_ids=self._get_career_ending_injury_ids()
        )

    def _get_released_player_ids(self) -> Set[int]:
        """
        Get IDs of players who are free agents (released/unsigned).

        These players have higher retirement probability.

        Returns:
            Set of player IDs who are free agents
        """
        released_ids = set()
        try:
            conn = sqlite3.connect(self._db_path)
            cursor = conn.cursor()

            # Get players with team_id = 0 (free agents) who aren't already retired
            cursor.execute("""
                SELECT player_id
                FROM players
                WHERE dynasty_id = ? AND team_id = 0
                  AND player_id NOT IN (
                      SELECT player_id FROM retired_players WHERE dynasty_id = ?
                  )
            """, (self._dynasty_id, self._dynasty_id))

            rows = cursor.fetchall()
            conn.close()

            released_ids = {row[0] for row in rows}

        except Exception as e:
            self._logger.debug(f"Error getting released player IDs: {e}")

        return released_ids

    def _get_career_ending_injury_ids(self) -> Set[int]:
        """
        Get IDs of players with career-ending injuries.

        Returns:
            Set of player IDs with career-ending injuries
        """
        injury_ids = set()
        try:
            conn = sqlite3.connect(self._db_path)
            cursor = conn.cursor()

            # Check for career-ending injuries this season
            cursor.execute("""
                SELECT player_id
                FROM player_injuries
                WHERE dynasty_id = ? AND season = ? AND severity = 'career_ending'
            """, (self._dynasty_id, self._season))

            rows = cursor.fetchall()
            conn.close()

            injury_ids = {row[0] for row in rows}

        except Exception as e:
            self._logger.debug(f"Error getting career-ending injury IDs: {e}")

        return injury_ids

    # =========================================================================
    # Internal Methods - Single Retirement Processing
    # =========================================================================

    def _process_single_retirement(
        self,
        player_dict: Dict[str, Any],
        reason: RetirementReason
    ) -> RetirementResult:
        """
        Process retirement for a single player.

        Creates career summary, persists records, removes from roster.

        Args:
            player_dict: Player data dictionary
            reason: Retirement reason enum

        Returns:
            RetirementResult with all retirement data
        """
        player_id = player_dict['player_id']
        team_id = player_dict.get('team_id', 0)

        # Generate career summary
        career_summary = self._summary_generator.generate_career_summary(
            player_dict, self._season
        )

        # Calculate age and years played
        age = self._decision_engine._calculate_age(player_dict.get('birthdate'))
        years_played = player_dict.get('years_pro', 1) or 1

        # Create RetiredPlayer record
        retired_player = RetiredPlayer(
            player_id=player_id,
            retirement_season=self._season,
            retirement_reason=reason.value,
            final_team_id=team_id,
            years_played=years_played,
            age_at_retirement=age,
        )

        # Insert into database using direct sqlite3 to avoid migration issues
        try:
            conn = sqlite3.connect(self._db_path)
            cursor = conn.cursor()

            # Insert retired player record
            cursor.execute("""
                INSERT INTO retired_players
                (dynasty_id, player_id, retirement_season, retirement_reason,
                 final_team_id, years_played, age_at_retirement)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                self._dynasty_id,
                retired_player.player_id,
                retired_player.retirement_season,
                retired_player.retirement_reason,
                retired_player.final_team_id,
                retired_player.years_played,
                retired_player.age_at_retirement,
            ))

            # Insert career summary (matching CareerSummary dataclass schema)
            teams_json = json.dumps(career_summary.teams_played_for) if career_summary.teams_played_for else None
            cursor.execute("""
                INSERT INTO career_summaries
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
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                self._dynasty_id,
                career_summary.player_id,
                career_summary.full_name,
                career_summary.position,
                career_summary.draft_year,
                career_summary.draft_round,
                career_summary.draft_pick,
                career_summary.games_played,
                career_summary.games_started,
                career_summary.pass_yards,
                career_summary.pass_tds,
                career_summary.pass_ints,
                career_summary.rush_yards,
                career_summary.rush_tds,
                career_summary.receptions,
                career_summary.rec_yards,
                career_summary.rec_tds,
                career_summary.tackles,
                career_summary.sacks,
                career_summary.interceptions,
                career_summary.forced_fumbles,
                career_summary.fg_made,
                career_summary.fg_attempted,
                career_summary.pro_bowls,
                career_summary.all_pro_first_team,
                career_summary.all_pro_second_team,
                career_summary.mvp_awards,
                career_summary.super_bowl_wins,
                career_summary.super_bowl_mvps,
                teams_json,
                career_summary.primary_team_id,
                career_summary.career_approximate_value,
                career_summary.hall_of_fame_score,
            ))

            conn.commit()
            conn.close()
        except Exception as e:
            self._logger.error(f"Error inserting retirement records: {e}")
            raise

        # Remove from roster if on a team
        if team_id > 0:
            self._remove_player_from_roster(player_id, team_id)

        # Determine if notable and generate headline
        is_notable = self._is_notable_retirement(career_summary)
        player_name = self._get_player_name(player_dict)
        headline = self._generate_retirement_headline(
            player_name, career_summary.position, reason.value, career_summary
        )

        return RetirementResult(
            player_id=player_id,
            player_name=player_name,
            position=career_summary.position,
            age=age,
            reason=reason.value,
            years_played=years_played,
            final_team_id=team_id,
            career_summary=career_summary,
            is_notable=is_notable,
            headline=headline,
        )

    def _remove_player_from_roster(self, player_id: int, team_id: int) -> None:
        """
        Remove player from active roster.

        Sets team_id to 0 and removes from team_rosters table.

        Args:
            player_id: Player ID
            team_id: Current team ID
        """
        try:
            from src.database.player_roster_api import PlayerRosterAPI

            roster_api = PlayerRosterAPI(self._db_path)

            # Update player's team_id to 0 and remove from team_rosters
            roster_api.update_player_team(self._dynasty_id, player_id, 0)

            self._logger.debug(f"Removed player {player_id} from team {team_id}")

        except Exception as e:
            self._logger.warning(
                f"Error removing player {player_id} from roster: {e}"
            )

    # =========================================================================
    # Internal Methods - Notable & Headlines
    # =========================================================================

    def _is_notable_retirement(self, summary: CareerSummary) -> bool:
        """
        Determine if retirement is notable for headlines.

        Notable if any of:
        - MVP award winner
        - Super Bowl champion
        - 3+ Pro Bowls
        - Any All-Pro selection
        - HOF score >= 40

        Args:
            summary: Career summary

        Returns:
            True if notable retirement
        """
        return (
            summary.mvp_awards > 0 or
            summary.super_bowl_wins > 0 or
            summary.pro_bowls >= 3 or
            summary.all_pro_first_team > 0 or
            summary.all_pro_second_team > 0 or
            summary.hall_of_fame_score >= 40
        )

    def _generate_retirement_headline(
        self,
        player_name: str,
        position: str,
        reason: str,
        summary: CareerSummary
    ) -> str:
        """
        Generate headline for retirement announcement.

        Args:
            player_name: Player full name
            position: Position abbreviation
            reason: Retirement reason string
            summary: Career summary

        Returns:
            Headline string
        """
        # Hall of Famer level
        if summary.hall_of_fame_score >= 85:
            return f"Future Hall of Famer {player_name} announces retirement"

        # MVP winner
        if summary.mvp_awards > 0:
            if summary.mvp_awards > 1:
                return f"{summary.mvp_awards}x MVP {player_name} calls it a career"
            return f"MVP {player_name} calls it a career"

        # Super Bowl champion
        if summary.super_bowl_wins > 0:
            if summary.super_bowl_wins > 1:
                return f"{summary.super_bowl_wins}x Super Bowl champion {player_name} retires"
            return f"Super Bowl champion {player_name} retires"

        # Injury retirement
        if reason == 'injury':
            return f"{player_name} forced to retire due to injury"

        # Championship retirement (going out on top)
        if reason == 'championship':
            return f"{player_name} retires on top after championship season"

        # Pro Bowler
        if summary.pro_bowls >= 3:
            return f"{summary.pro_bowls}x Pro Bowler {player_name} announces retirement"

        # All-Pro
        if summary.all_pro_first_team > 0 or summary.all_pro_second_team > 0:
            total_all_pro = summary.all_pro_first_team + summary.all_pro_second_team
            return f"{total_all_pro}x All-Pro {player_name} announces retirement"

        # Default
        return f"{position} {player_name} announces retirement"

    def _get_player_name(self, player_dict: Dict[str, Any]) -> str:
        """Get formatted player name from player dict."""
        first = player_dict.get('first_name', '')
        last = player_dict.get('last_name', '')
        return f"{first} {last}".strip() or "Unknown Player"
