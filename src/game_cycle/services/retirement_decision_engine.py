"""
Retirement Decision Engine for Game Cycle.

Calculates retirement probabilities for players based on:
- Position-specific retirement age thresholds
- Performance decline (OVR below threshold)
- Career-ending injuries
- Championship wins (going out on top)
- Being released/unsigned
- Career accomplishments (MVP + Super Bowl)
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Set, Optional, Any, Tuple
import logging
import random
import sqlite3
import json


# ============================================
# Constants - Position Retirement Thresholds
# ============================================

@dataclass(frozen=True)
class PositionRetirementThresholds:
    """Immutable retirement thresholds for a position group."""
    base_age: int           # Age when retirement probability starts
    decline_ovr: int        # OVR below which decline factor applies
    max_age: int            # Forced retirement age


POSITION_RETIREMENT_AGES: Dict[str, PositionRetirementThresholds] = {
    'QB': PositionRetirementThresholds(base_age=38, decline_ovr=70, max_age=45),
    'RB': PositionRetirementThresholds(base_age=30, decline_ovr=65, max_age=34),
    'FB': PositionRetirementThresholds(base_age=32, decline_ovr=60, max_age=36),
    'WR': PositionRetirementThresholds(base_age=33, decline_ovr=65, max_age=38),
    'TE': PositionRetirementThresholds(base_age=33, decline_ovr=65, max_age=38),
    'OL': PositionRetirementThresholds(base_age=34, decline_ovr=65, max_age=40),
    'DL': PositionRetirementThresholds(base_age=32, decline_ovr=65, max_age=38),
    'EDGE': PositionRetirementThresholds(base_age=32, decline_ovr=65, max_age=36),
    'LB': PositionRetirementThresholds(base_age=32, decline_ovr=65, max_age=36),
    'CB': PositionRetirementThresholds(base_age=32, decline_ovr=65, max_age=36),
    'S': PositionRetirementThresholds(base_age=33, decline_ovr=65, max_age=38),
    'K': PositionRetirementThresholds(base_age=40, decline_ovr=70, max_age=48),
    'P': PositionRetirementThresholds(base_age=38, decline_ovr=70, max_age=45),
}

# Default thresholds for unknown positions
DEFAULT_THRESHOLDS = PositionRetirementThresholds(base_age=33, decline_ovr=65, max_age=38)

# Position abbreviation to group mapping
POSITION_TO_GROUP: Dict[str, str] = {
    # Quarterback
    'QB': 'QB', 'QUARTERBACK': 'QB',
    # Running backs
    'RB': 'RB', 'HB': 'RB', 'RUNNING_BACK': 'RB', 'HALFBACK': 'RB',
    # Fullback
    'FB': 'FB', 'FULLBACK': 'FB',
    # Wide receiver
    'WR': 'WR', 'WIDE_RECEIVER': 'WR',
    # Tight end
    'TE': 'TE', 'TIGHT_END': 'TE',
    # Offensive line
    'LT': 'OL', 'LG': 'OL', 'C': 'OL', 'RG': 'OL', 'RT': 'OL',
    'OL': 'OL', 'OT': 'OL', 'OG': 'OL', 'CENTER': 'OL',
    'LEFT_TACKLE': 'OL', 'LEFT_GUARD': 'OL', 'RIGHT_TACKLE': 'OL', 'RIGHT_GUARD': 'OL',
    'OFFENSIVE_LINE': 'OL',
    # Defensive line
    'LE': 'DL', 'DT': 'DL', 'RE': 'DL', 'NT': 'DL',
    'DE': 'DL', 'DL': 'DL', 'NOSE_TACKLE': 'DL',
    'DEFENSIVE_END': 'DL', 'DEFENSIVE_TACKLE': 'DL', 'DEFENSIVE_LINE': 'DL',
    # Edge rusher
    'EDGE': 'EDGE',
    # Linebackers
    'LOLB': 'LB', 'MLB': 'LB', 'ROLB': 'LB', 'ILB': 'LB', 'OLB': 'LB', 'LB': 'LB',
    'LINEBACKER': 'LB', 'INSIDE_LINEBACKER': 'LB', 'OUTSIDE_LINEBACKER': 'LB',
    'MIKE_LINEBACKER': 'LB', 'WILL_LINEBACKER': 'LB', 'SAM_LINEBACKER': 'LB',
    # Cornerback
    'CB': 'CB', 'CORNERBACK': 'CB',
    # Safety
    'FS': 'S', 'SS': 'S', 'S': 'S', 'SAFETY': 'S',
    'FREE_SAFETY': 'S', 'STRONG_SAFETY': 'S',
    # Kicker
    'K': 'K', 'KICKER': 'K',
    # Punter
    'P': 'P', 'PUNTER': 'P',
    # Long snapper (grouped with OL)
    'LS': 'OL', 'LONG_SNAPPER': 'OL',
}


class RetirementReason(Enum):
    """Retirement reason categories (matches database enum)."""
    INJURY = 'injury'
    CHAMPIONSHIP = 'championship'
    RELEASED = 'released'
    AGE_DECLINE = 'age_decline'
    CONTRACT = 'contract'
    PERSONAL = 'personal'


# ============================================
# Dataclasses
# ============================================

@dataclass
class RetirementContext:
    """
    Context for retirement evaluation.

    Provides environmental data for the current season's retirement decisions.
    """
    season: int
    super_bowl_winner_team_id: Optional[int] = None
    released_player_ids: Set[int] = field(default_factory=set)
    career_ending_injury_ids: Set[int] = field(default_factory=set)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'season': self.season,
            'super_bowl_winner_team_id': self.super_bowl_winner_team_id,
            'released_player_ids': list(self.released_player_ids),
            'career_ending_injury_ids': list(self.career_ending_injury_ids),
        }


@dataclass
class RetirementCandidate:
    """
    Result of retirement evaluation for a single player.
    """
    player_id: int
    player_name: str
    position: str
    age: int
    team_id: int
    probability: float          # 0.0 to 1.0
    reason: RetirementReason
    will_retire: bool           # Result of probability roll
    ovr_current: int
    ovr_previous: Optional[int] = None
    career_stats_summary: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'player_id': self.player_id,
            'player_name': self.player_name,
            'position': self.position,
            'age': self.age,
            'team_id': self.team_id,
            'probability': self.probability,
            'reason': self.reason.value,
            'will_retire': self.will_retire,
            'ovr_current': self.ovr_current,
            'ovr_previous': self.ovr_previous,
            'career_stats_summary': self.career_stats_summary,
        }


# ============================================
# Main Engine Class
# ============================================

class RetirementDecisionEngine:
    """
    Engine for calculating player retirement probabilities.

    Evaluates retirement likelihood based on:
    - Position-specific age thresholds
    - Performance decline (OVR below threshold)
    - Career-ending injuries (95% probability)
    - Championship wins (going out on top)
    - Being released/unsigned
    - Career accomplishments (MVP + Super Bowl)
    """

    # Probability factor constants
    AGE_FACTOR_PER_YEAR = 0.15      # +15% per year past base retirement age
    DECLINE_FACTOR = 0.25           # +25% if OVR below position threshold
    CAREER_ENDING_INJURY = 0.95     # 95% if career-ending injury
    MULTI_SEASON_INJURY = 0.20      # +20% if 2+ seasons missed to injury
    CHAMPIONSHIP_FACTOR = 0.30      # +30% if just won first SB and age >= 33
    RELEASED_FACTOR = 0.40          # +40% if cut and unsigned
    ACCOMPLISHMENTS_FACTOR = 0.25   # +25% if MVP + SB win + age >= 35
    PERSONAL_FACTOR_MAX = 0.05      # +0-5% random if age >= 30
    MAX_PROBABILITY = 0.95          # Cap at 95%

    def __init__(
        self,
        db_path: str,
        dynasty_id: str,
        season: int
    ):
        """
        Initialize the retirement decision engine.

        Args:
            db_path: Path to the game cycle database
            dynasty_id: Dynasty identifier for isolation
            season: Current season year
        """
        self._db_path = db_path
        self._dynasty_id = dynasty_id
        self._season = season
        self._logger = logging.getLogger(__name__)

    # =========================================================================
    # Public API Methods
    # =========================================================================

    def calculate_retirement_probability(
        self,
        player_dict: Dict[str, Any],
        context: RetirementContext
    ) -> Tuple[float, RetirementReason]:
        """
        Calculate retirement probability for a single player.

        Args:
            player_dict: Player data dictionary with keys:
                - player_id: int
                - first_name, last_name: str
                - positions: List[str] or str (JSON)
                - attributes: Dict or str (JSON) with 'overall'
                - birthdate: str (YYYY-MM-DD)
                - team_id: int (0 = free agent)
            context: RetirementContext with season data

        Returns:
            Tuple of (probability: 0.0-1.0, reason: RetirementReason)
        """
        # Parse player data
        player_id = player_dict['player_id']
        position = self._get_primary_position(player_dict)
        age = self._calculate_age(player_dict.get('birthdate'))
        ovr = self._get_overall(player_dict)
        team_id = player_dict.get('team_id', 0)

        # Get position thresholds
        thresholds = self._get_position_thresholds(position)

        # Priority 1: Career-ending injury (highest priority)
        if player_id in context.career_ending_injury_ids:
            return (self.CAREER_ENDING_INJURY, RetirementReason.INJURY)

        # Priority 2: Check forced retirement (max age)
        if age >= thresholds.max_age:
            return (1.0, RetirementReason.AGE_DECLINE)

        # Accumulate probability factors
        probability = 0.0
        primary_reason = RetirementReason.AGE_DECLINE

        # Factor 1: Age past base retirement
        if age > thresholds.base_age:
            years_past = age - thresholds.base_age
            probability += years_past * self.AGE_FACTOR_PER_YEAR

        # Factor 2: Performance decline
        if ovr < thresholds.decline_ovr:
            probability += self.DECLINE_FACTOR

        # Factor 3: Multi-season injury history
        seasons_missed = self._get_seasons_missed_to_injury(player_id)
        if seasons_missed >= 2:
            probability += self.MULTI_SEASON_INJURY

        # Factor 4: Championship - going out on top
        if (context.super_bowl_winner_team_id and
            team_id == context.super_bowl_winner_team_id and
            age >= 33):
            career_sb_wins = self._get_career_super_bowl_wins(player_id, team_id)
            if career_sb_wins == 1:  # Just won FIRST Super Bowl
                probability += self.CHAMPIONSHIP_FACTOR
                primary_reason = RetirementReason.CHAMPIONSHIP

        # Factor 5: Released/unsigned
        if player_id in context.released_player_ids:
            probability += self.RELEASED_FACTOR
            primary_reason = RetirementReason.RELEASED

        # Factor 6: Career accomplishments (legacy complete)
        if age >= 35:
            mvp_count = self._get_mvp_count(player_id)
            sb_wins = self._get_career_super_bowl_wins(player_id, team_id)
            if mvp_count >= 1 and sb_wins >= 1:
                probability += self.ACCOMPLISHMENTS_FACTOR
                if primary_reason == RetirementReason.AGE_DECLINE:
                    primary_reason = RetirementReason.CHAMPIONSHIP

        # Factor 7: Random personal factor
        if age >= 30:
            probability += random.random() * self.PERSONAL_FACTOR_MAX

        # Cap at maximum
        probability = min(probability, self.MAX_PROBABILITY)

        return (probability, primary_reason)

    def should_retire(
        self,
        player_dict: Dict[str, Any],
        context: RetirementContext
    ) -> bool:
        """
        Determine if a player retires this season.

        Calculates probability and rolls dice.

        Args:
            player_dict: Player data dictionary
            context: RetirementContext

        Returns:
            True if player should retire
        """
        probability, _ = self.calculate_retirement_probability(player_dict, context)
        return random.random() < probability

    def evaluate_all_players(
        self,
        players: List[Dict[str, Any]],
        context: RetirementContext
    ) -> List[RetirementCandidate]:
        """
        Evaluate retirement for all provided players.

        Args:
            players: List of player data dictionaries
            context: RetirementContext with season data

        Returns:
            List of RetirementCandidate for all players
        """
        candidates = []

        for player in players:
            probability, reason = self.calculate_retirement_probability(player, context)
            will_retire = random.random() < probability

            player_name = self._get_player_name(player)
            position = self._get_primary_position(player)
            age = self._calculate_age(player.get('birthdate'))
            ovr = self._get_overall(player)
            ovr_previous = self._get_previous_overall(player['player_id'])

            candidate = RetirementCandidate(
                player_id=player['player_id'],
                player_name=player_name,
                position=position,
                age=age,
                team_id=player.get('team_id', 0),
                probability=probability,
                reason=reason,
                will_retire=will_retire,
                ovr_current=ovr,
                ovr_previous=ovr_previous,
                career_stats_summary=None,
            )
            candidates.append(candidate)

        return candidates

    def get_retiring_players(
        self,
        players: List[Dict[str, Any]],
        context: RetirementContext
    ) -> List[RetirementCandidate]:
        """
        Get only players who will retire this season.

        Args:
            players: List of player data dictionaries
            context: RetirementContext with season data

        Returns:
            List of RetirementCandidate for retiring players only
        """
        all_candidates = self.evaluate_all_players(players, context)
        return [c for c in all_candidates if c.will_retire]

    # =========================================================================
    # Private Helper Methods
    # =========================================================================

    def _get_position_thresholds(self, position: str) -> PositionRetirementThresholds:
        """Get retirement thresholds for a position."""
        pos_upper = position.upper().replace(' ', '_')
        group = POSITION_TO_GROUP.get(pos_upper)
        if group:
            return POSITION_RETIREMENT_AGES.get(group, DEFAULT_THRESHOLDS)
        return DEFAULT_THRESHOLDS

    def _get_primary_position(self, player_dict: Dict[str, Any]) -> str:
        """Extract primary position from player dict."""
        positions = player_dict.get('positions', [])

        # Handle JSON string
        if isinstance(positions, str):
            try:
                positions = json.loads(positions)
            except (json.JSONDecodeError, TypeError):
                positions = [positions]

        # Handle single position string
        if isinstance(positions, str):
            return positions.upper()

        # Return first position or default
        if positions and len(positions) > 0:
            pos = positions[0]
            if isinstance(pos, str):
                return pos.upper()
        return 'WR'  # Default fallback

    def _calculate_age(self, birthdate: Optional[str]) -> int:
        """Calculate age from birthdate string."""
        if not birthdate:
            return 25  # Default age if missing

        try:
            birth_year = int(birthdate.split('-')[0])
            return self._season - birth_year
        except (ValueError, IndexError, AttributeError):
            return 25

    def _get_overall(self, player_dict: Dict[str, Any]) -> int:
        """Extract overall rating from attributes."""
        attributes = player_dict.get('attributes', {})

        # Handle JSON string
        if isinstance(attributes, str):
            try:
                attributes = json.loads(attributes)
            except (json.JSONDecodeError, TypeError):
                return 70  # Default

        if isinstance(attributes, dict):
            return attributes.get('overall', 70)
        return 70

    def _get_player_name(self, player_dict: Dict[str, Any]) -> str:
        """Get formatted player name."""
        first = player_dict.get('first_name', '')
        last = player_dict.get('last_name', '')
        return f"{first} {last}".strip() or "Unknown Player"

    def _get_previous_overall(self, player_id: int) -> Optional[int]:
        """Get player's OVR from previous season via progression history."""
        try:
            conn = sqlite3.connect(self._db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT overall_before
                FROM player_progression_history
                WHERE dynasty_id = ? AND player_id = ? AND season = ?
                ORDER BY id DESC
                LIMIT 1
            """, (self._dynasty_id, player_id, self._season))

            row = cursor.fetchone()
            conn.close()

            if row:
                return row['overall_before']
            return None
        except Exception as e:
            self._logger.debug(f"Could not get previous OVR for player {player_id}: {e}")
            return None

    def _get_seasons_missed_to_injury(self, player_id: int) -> int:
        """Count seasons with season-ending injuries."""
        try:
            conn = sqlite3.connect(self._db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT COUNT(DISTINCT season) as count
                FROM player_injuries
                WHERE dynasty_id = ? AND player_id = ?
                  AND (severity = 'season_ending' OR severity = 'SEASON_ENDING')
            """, (self._dynasty_id, player_id))

            row = cursor.fetchone()
            conn.close()

            return row[0] if row else 0
        except Exception as e:
            self._logger.debug(f"Could not get injury history for player {player_id}: {e}")
            return 0

    def _get_career_super_bowl_wins(self, player_id: int, current_team_id: int) -> int:
        """
        Get count of Super Bowl wins for player.

        Note: This is a simplified implementation that checks team history.
        A more complete implementation would track player team history per season.
        """
        try:
            conn = sqlite3.connect(self._db_path)
            cursor = conn.cursor()

            # Check current team's Super Bowl wins
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM team_season_history
                WHERE dynasty_id = ? AND team_id = ? AND won_super_bowl = 1
            """, (self._dynasty_id, current_team_id))

            row = cursor.fetchone()
            conn.close()

            return row[0] if row else 0
        except Exception as e:
            self._logger.debug(f"Could not get SB wins for player {player_id}: {e}")
            return 0

    def _get_mvp_count(self, player_id: int) -> int:
        """Get count of MVP awards for player."""
        try:
            conn = sqlite3.connect(self._db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT COUNT(*) as count
                FROM award_winners
                WHERE dynasty_id = ? AND player_id = ?
                  AND award_id = 'mvp' AND is_winner = 1
            """, (self._dynasty_id, player_id))

            row = cursor.fetchone()
            conn.close()

            return row[0] if row else 0
        except Exception as e:
            self._logger.debug(f"Could not get MVP count for player {player_id}: {e}")
            return 0
