"""
HOF Eligibility Service - Determine which retired players are eligible for HOF voting.

Wraps existing APIs (RetiredPlayersAPI, HOFAPI, career_summaries) to:
1. Filter players by 5-year waiting period (already in DB)
2. Exclude already-inducted players
3. Exclude players removed from ballot
4. Enforce 20-year ballot limit
5. Enrich candidates with career summary data
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum
import json
import logging

from game_cycle.database.hof_api import HOFAPI
from game_cycle.database.connection import GameCycleDatabase

logger = logging.getLogger(__name__)


# ============================================
# Enums and Dataclasses
# ============================================

class EligibilityStatus(Enum):
    """Why a player is or isn't eligible for HOF voting."""
    ELIGIBLE = "ELIGIBLE"
    TOO_RECENT = "TOO_RECENT"                   # Retired < 5 seasons ago
    ALREADY_INDUCTED = "ALREADY_INDUCTED"       # Already in HOF
    REMOVED_FROM_BALLOT = "REMOVED_FROM_BALLOT" # <5% votes or 20-year limit
    NOT_RETIRED = "NOT_RETIRED"                 # Player not in retired_players
    NO_CAREER_SUMMARY = "NO_CAREER_SUMMARY"     # Missing career summary data


@dataclass
class HOFCandidate:
    """A player eligible for HOF consideration this year."""
    player_id: int
    player_name: str
    primary_position: str

    # Retirement info
    retirement_season: int
    years_on_ballot: int  # 1 = first year eligible

    # Career summary
    career_seasons: int
    teams_played_for: List[str]
    final_team_id: int

    # Achievements (from career_summaries)
    super_bowl_wins: int
    mvp_awards: int
    all_pro_first_team: int
    all_pro_second_team: int
    pro_bowl_selections: int

    # Stats (position-specific dict)
    career_stats: Dict[str, Any] = field(default_factory=dict)

    # Pre-computed HOF score
    hof_score: int = 0

    # Eligibility
    eligibility_status: EligibilityStatus = EligibilityStatus.ELIGIBLE
    is_first_ballot: bool = False  # years_on_ballot == 1

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'player_id': self.player_id,
            'player_name': self.player_name,
            'primary_position': self.primary_position,
            'retirement_season': self.retirement_season,
            'years_on_ballot': self.years_on_ballot,
            'career_seasons': self.career_seasons,
            'teams_played_for': self.teams_played_for,
            'final_team_id': self.final_team_id,
            'super_bowl_wins': self.super_bowl_wins,
            'mvp_awards': self.mvp_awards,
            'all_pro_first_team': self.all_pro_first_team,
            'all_pro_second_team': self.all_pro_second_team,
            'pro_bowl_selections': self.pro_bowl_selections,
            'career_stats': self.career_stats,
            'hof_score': self.hof_score,
            'eligibility_status': self.eligibility_status.value,
            'is_first_ballot': self.is_first_ballot,
        }


# ============================================
# HOFEligibilityService Class
# ============================================

class HOFEligibilityService:
    """
    Determines HOF eligibility for retired players.

    Eligibility Rules:
    1. Must be retired for 5+ complete seasons (handled by retired_players table)
    2. Not already inducted into HOF
    3. Not removed from ballot (below 5% votes or 20-year limit)
    4. Max 20 years on ballot before automatic removal
    """

    WAITING_PERIOD = 5   # Years after retirement (already enforced in DB)
    MAX_BALLOT_YEARS = 20

    def __init__(self, db: GameCycleDatabase, dynasty_id: str):
        """
        Initialize with database connection and dynasty ID.

        Args:
            db: GameCycleDatabase instance
            dynasty_id: Dynasty identifier for isolation
        """
        self.db = db
        self.dynasty_id = dynasty_id
        self.hof_api = HOFAPI(db, dynasty_id)

    def get_eligible_candidates(
        self,
        current_season: int
    ) -> List[HOFCandidate]:
        """
        Get all players eligible for HOF voting this season.

        Flow:
        1. Query retired_players where hall_of_fame_eligible_season <= current_season
        2. Filter out already inducted (via HOFAPI)
        3. Filter out removed from ballot (via HOFAPI)
        4. Check 20-year ballot limit
        5. Enrich with career_summaries data
        6. Return sorted by hof_score DESC

        Args:
            current_season: Current season year

        Returns:
            List of HOFCandidate sorted by hof_score descending
        """
        # Step 1: Get all retired players who are eligible (5-year wait already in DB)
        eligible_records = self._get_all_eligible_retired(current_season)

        candidates = []
        for record in eligible_records:
            player_id = record['player_id']

            # Step 2: Filter out already inducted
            if self.hof_api.is_inducted(player_id):
                continue

            # Step 3: Filter out removed from ballot
            if self.hof_api.was_removed_from_ballot(player_id):
                continue

            # Step 4: Check 20-year limit
            years_on_ballot = self._calculate_years_on_ballot(
                record['hall_of_fame_eligible_season'],
                current_season
            )
            if years_on_ballot > self.MAX_BALLOT_YEARS:
                continue

            # Step 5: Enrich with career summary
            career_summary = self._get_career_summary(player_id)
            if not career_summary:
                # No career summary = no HOF consideration
                logger.debug(f"No career summary for player {player_id}, skipping HOF consideration")
                continue

            # Step 6: Build candidate
            candidate = self._build_candidate(
                record, career_summary, years_on_ballot
            )
            candidates.append(candidate)

        # Sort by HOF score descending
        candidates.sort(key=lambda c: c.hof_score, reverse=True)
        return candidates

    def get_first_ballot_candidates(
        self,
        current_season: int
    ) -> List[HOFCandidate]:
        """
        Get only first-ballot eligible candidates (first year of eligibility).

        Args:
            current_season: Current season year

        Returns:
            List of HOFCandidate in their first year of eligibility
        """
        all_candidates = self.get_eligible_candidates(current_season)
        return [c for c in all_candidates if c.is_first_ballot]

    def check_eligibility(
        self,
        player_id: int,
        current_season: int
    ) -> EligibilityStatus:
        """
        Check eligibility status for a specific player.

        Args:
            player_id: Player ID to check
            current_season: Current season year

        Returns:
            EligibilityStatus indicating why player is or isn't eligible
        """
        # Check if player is retired
        retired_record = self._get_retired_player(player_id)
        if not retired_record:
            return EligibilityStatus.NOT_RETIRED

        # Check 5-year waiting period
        eligible_season = retired_record.get('hall_of_fame_eligible_season')
        if eligible_season is None or eligible_season > current_season:
            return EligibilityStatus.TOO_RECENT

        # Check if already inducted
        if self.hof_api.is_inducted(player_id):
            return EligibilityStatus.ALREADY_INDUCTED

        # Check if removed from ballot
        if self.hof_api.was_removed_from_ballot(player_id):
            return EligibilityStatus.REMOVED_FROM_BALLOT

        # Check 20-year limit
        years_on_ballot = self._calculate_years_on_ballot(eligible_season, current_season)
        if years_on_ballot > self.MAX_BALLOT_YEARS:
            return EligibilityStatus.REMOVED_FROM_BALLOT

        # Check for career summary
        career_summary = self._get_career_summary(player_id)
        if not career_summary:
            return EligibilityStatus.NO_CAREER_SUMMARY

        return EligibilityStatus.ELIGIBLE

    def get_candidate(
        self,
        player_id: int,
        current_season: int
    ) -> Optional[HOFCandidate]:
        """
        Get HOFCandidate for a specific player if eligible.

        Args:
            player_id: Player ID
            current_season: Current season year

        Returns:
            HOFCandidate if eligible, None otherwise
        """
        status = self.check_eligibility(player_id, current_season)
        if status != EligibilityStatus.ELIGIBLE:
            return None

        retired_record = self._get_retired_player(player_id)
        career_summary = self._get_career_summary(player_id)

        years_on_ballot = self._calculate_years_on_ballot(
            retired_record['hall_of_fame_eligible_season'],
            current_season
        )

        return self._build_candidate(retired_record, career_summary, years_on_ballot)

    # ============================================
    # Private Helper Methods
    # ============================================

    def _get_all_eligible_retired(self, current_season: int) -> List[Dict[str, Any]]:
        """
        Get all retired players eligible for HOF (not just this year's class).

        Players become eligible 5 years after retirement. Once eligible, they
        remain on the ballot until inducted, removed, or 20-year limit.

        Args:
            current_season: Current season year

        Returns:
            List of retired player records
        """
        rows = self.db.query_all(
            """SELECT player_id, retirement_season, final_team_id,
                      years_played, hall_of_fame_eligible_season,
                      one_day_contract_team_id
               FROM retired_players
               WHERE dynasty_id = ?
                 AND hall_of_fame_eligible_season <= ?
               ORDER BY hall_of_fame_eligible_season ASC""",
            (self.dynasty_id, current_season)
        )
        return [dict(row) for row in rows]

    def _get_retired_player(self, player_id: int) -> Optional[Dict[str, Any]]:
        """
        Get retired player record.

        Args:
            player_id: Player ID

        Returns:
            Retired player dict or None
        """
        row = self.db.query_one(
            """SELECT player_id, retirement_season, final_team_id,
                      years_played, hall_of_fame_eligible_season,
                      one_day_contract_team_id
               FROM retired_players
               WHERE dynasty_id = ? AND player_id = ?""",
            (self.dynasty_id, player_id)
        )
        return dict(row) if row else None

    def _get_career_summary(self, player_id: int) -> Optional[Dict[str, Any]]:
        """
        Get career summary with achievements and HOF score.

        Args:
            player_id: Player ID

        Returns:
            Career summary dict or None
        """
        row = self.db.query_one(
            """SELECT player_name, primary_position, career_seasons,
                      teams_played_for, primary_team_id,
                      pro_bowls, all_pro_first_team, all_pro_second_team,
                      mvp_awards, super_bowl_wins, super_bowl_mvps,
                      hall_of_fame_score,
                      pass_yards, pass_tds, rush_yards, rush_tds,
                      receptions, rec_yards, rec_tds,
                      tackles, sacks, interceptions,
                      fg_made, fg_attempted
               FROM career_summaries
               WHERE dynasty_id = ? AND player_id = ?""",
            (self.dynasty_id, player_id)
        )
        return dict(row) if row else None

    def _calculate_years_on_ballot(
        self,
        eligible_season: int,
        current_season: int
    ) -> int:
        """
        Calculate how many years player has been on ballot.

        Args:
            eligible_season: First season player was eligible
            current_season: Current season year

        Returns:
            Years on ballot (1 = first year)
        """
        return current_season - eligible_season + 1

    def _build_candidate(
        self,
        retired_record: Dict[str, Any],
        career_summary: Dict[str, Any],
        years_on_ballot: int
    ) -> HOFCandidate:
        """
        Build HOFCandidate from database records.

        Args:
            retired_record: Dict from retired_players table
            career_summary: Dict from career_summaries table
            years_on_ballot: Calculated years on ballot

        Returns:
            HOFCandidate dataclass instance
        """
        # Parse teams_played_for JSON
        teams_played_for = []
        if career_summary.get('teams_played_for'):
            try:
                teams_raw = career_summary['teams_played_for']
                if isinstance(teams_raw, str):
                    teams_played_for = json.loads(teams_raw)
                elif isinstance(teams_raw, list):
                    teams_played_for = teams_raw
            except (json.JSONDecodeError, TypeError):
                logger.warning(f"Failed to parse teams_played_for for player {retired_record['player_id']}")

        # Build position-specific career stats
        career_stats = self._build_career_stats(career_summary)

        return HOFCandidate(
            player_id=retired_record['player_id'],
            player_name=career_summary.get('player_name', 'Unknown'),
            primary_position=career_summary.get('primary_position', 'Unknown'),
            retirement_season=retired_record['retirement_season'],
            years_on_ballot=years_on_ballot,
            career_seasons=career_summary.get('career_seasons', 0),
            teams_played_for=teams_played_for,
            final_team_id=retired_record['final_team_id'],
            super_bowl_wins=career_summary.get('super_bowl_wins', 0),
            mvp_awards=career_summary.get('mvp_awards', 0),
            all_pro_first_team=career_summary.get('all_pro_first_team', 0),
            all_pro_second_team=career_summary.get('all_pro_second_team', 0),
            pro_bowl_selections=career_summary.get('pro_bowls', 0),
            career_stats=career_stats,
            hof_score=career_summary.get('hall_of_fame_score', 0),
            eligibility_status=EligibilityStatus.ELIGIBLE,
            is_first_ballot=(years_on_ballot == 1),
        )

    def _build_career_stats(self, career_summary: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build position-specific career stats dict.

        Args:
            career_summary: Dict from career_summaries table

        Returns:
            Dict with relevant career stats for the position
        """
        position = career_summary.get('primary_position', '')

        # Base stats included for all positions
        stats = {}

        # Passing stats (QB)
        if position in ('QB',) or career_summary.get('pass_yards', 0) > 0:
            stats['pass_yards'] = career_summary.get('pass_yards', 0)
            stats['pass_tds'] = career_summary.get('pass_tds', 0)

        # Rushing stats (RB, FB, QB)
        if position in ('RB', 'FB', 'QB') or career_summary.get('rush_yards', 0) > 0:
            stats['rush_yards'] = career_summary.get('rush_yards', 0)
            stats['rush_tds'] = career_summary.get('rush_tds', 0)

        # Receiving stats (WR, TE, RB)
        if position in ('WR', 'TE', 'RB') or career_summary.get('rec_yards', 0) > 0:
            stats['receptions'] = career_summary.get('receptions', 0)
            stats['rec_yards'] = career_summary.get('rec_yards', 0)
            stats['rec_tds'] = career_summary.get('rec_tds', 0)

        # Defensive stats
        if position in ('EDGE', 'DT', 'DE', 'LE', 'RE', 'LOLB', 'ROLB', 'MLB', 'CB', 'FS', 'SS'):
            stats['tackles'] = career_summary.get('tackles', 0)
            stats['sacks'] = career_summary.get('sacks', 0)
            stats['interceptions'] = career_summary.get('interceptions', 0)

        # Kicking stats
        if position in ('K', 'P'):
            stats['fg_made'] = career_summary.get('fg_made', 0)
            stats['fg_attempted'] = career_summary.get('fg_attempted', 0)

        return stats
