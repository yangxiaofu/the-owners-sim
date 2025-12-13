"""
Service for managing rivalry intensity evolution.

Part of Milestone 11: Schedule & Rivalries, Tollgate 6.
Handles rivalry intensity updates after games, playoff rivalry creation,
and annual decay for inactive rivalries.
"""

import json
import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Optional, Tuple

from ..database.connection import GameCycleDatabase
from ..database.rivalry_api import RivalryAPI
from ..database.head_to_head_api import HeadToHeadAPI
from ..models.rivalry import Rivalry, RivalryType


class PlayoffRound(Enum):
    """Playoff round types for rivalry boost calculation."""
    WILD_CARD = "wild_card"
    DIVISIONAL = "divisional"
    CONFERENCE = "conference"
    SUPER_BOWL = "super_bowl"


@dataclass
class IntensityChange:
    """Result of intensity calculation after a game."""
    old_intensity: int
    new_intensity: int
    change_amount: int
    change_reason: str


class RivalryService:
    """
    Service for managing dynamic rivalry intensity evolution.

    Handles:
    - Intensity updates after regular season and playoff games
    - New rivalry creation from playoff meetings
    - Annual decay for inactive RECENT rivalries

    Intensity changes are based on game outcomes:
    - Close games increase intensity
    - Blowouts decrease intensity
    - Playoff games add significant boosts
    - OT games get special consideration
    """

    # Intensity change constants
    CLOSE_GAME_THRESHOLD = 7      # Within 7 points = close game
    VERY_CLOSE_THRESHOLD = 3      # Within 3 points = very close
    BLOWOUT_THRESHOLD = 20        # 20+ point margin = blowout

    CLOSE_GAME_BOOST = 4          # +4 for close games
    VERY_CLOSE_BOOST = 6          # +6 for very close games
    OVERTIME_BOOST = 7            # +7 for OT games
    BLOWOUT_PENALTY = -4          # -4 for blowouts

    # Playoff round intensity boosts
    PLAYOFF_BOOSTS = {
        PlayoffRound.WILD_CARD: 10,
        PlayoffRound.DIVISIONAL: 12,
        PlayoffRound.CONFERENCE: 15,
        PlayoffRound.SUPER_BOWL: 20,
    }

    # Decay constants
    DECAY_RATE = 10               # -10/year for RECENT without meetings
    MIN_INTENSITY = 20            # Below 20 = remove RECENT rivalry
    HISTORIC_MIN = 50             # HISTORIC never goes below 50
    DIVISION_MIN = 40             # DIVISION never goes below 40

    # New rivalry base intensities
    PLAYOFF_RIVALRY_BASE = 60     # Base for non-Super Bowl playoff rivalries
    SUPER_BOWL_RIVALRY_BASE = 70  # Base for Super Bowl rivalries

    def __init__(self, db: GameCycleDatabase):
        """
        Initialize service with database connection.

        Args:
            db: GameCycleDatabase instance
        """
        self._db = db
        self._rivalry_api = RivalryAPI(db)
        self._h2h_api = HeadToHeadAPI(db)
        self._logger = logging.getLogger(__name__)
        self._team_names = self._load_team_names()

    def _load_team_names(self) -> dict:
        """Load team names from teams.json for rivalry naming."""
        try:
            current_dir = Path(__file__).parent
            teams_path = current_dir.parent.parent / "data" / "teams.json"

            if teams_path.exists():
                with open(teams_path, 'r') as f:
                    data = json.load(f)
                    return {
                        int(team_id): team_data.get('full_name', f'Team {team_id}')
                        for team_id, team_data in data.get('teams', {}).items()
                    }
        except Exception as e:
            self._logger.warning(f"Failed to load team names: {e}")

        return {}

    def _get_team_name(self, team_id: int) -> str:
        """Get team name by ID."""
        return self._team_names.get(team_id, f"Team {team_id}")

    # -------------------- Main Public Methods --------------------

    def update_rivalry_after_game(
        self,
        dynasty_id: str,
        home_team_id: int,
        away_team_id: int,
        home_score: int,
        away_score: int,
        overtime_periods: int = 0,
        is_playoff: bool = False,
        playoff_round: Optional[PlayoffRound] = None,
    ) -> Optional[IntensityChange]:
        """
        Update rivalry intensity after a game.

        Args:
            dynasty_id: Dynasty identifier
            home_team_id: Home team ID
            away_team_id: Away team ID
            home_score: Home team final score
            away_score: Away team final score
            overtime_periods: Number of OT periods (0 = regulation)
            is_playoff: True if playoff game
            playoff_round: Playoff round if playoff game

        Returns:
            IntensityChange if rivalry exists, None otherwise
        """
        # Get existing rivalry
        rivalry = self._rivalry_api.get_rivalry_between_teams(
            dynasty_id, home_team_id, away_team_id
        )

        if rivalry is None:
            self._logger.debug(
                f"No rivalry between teams {home_team_id} and {away_team_id}"
            )
            return None

        # Calculate intensity change
        margin = abs(home_score - away_score)
        change = self._calculate_intensity_change(
            margin, overtime_periods, is_playoff, playoff_round
        )

        # Apply change with bounds checking
        old_intensity = rivalry.intensity
        new_intensity = self._apply_change(rivalry, change)

        # Update database if changed
        if new_intensity != old_intensity:
            self._rivalry_api.update_intensity(
                dynasty_id, rivalry.rivalry_id, new_intensity
            )
            self._logger.info(
                f"Updated rivalry '{rivalry.rivalry_name}': "
                f"{old_intensity} -> {new_intensity} ({change:+d})"
            )

        # Build change reason
        reason = self._get_change_reason(margin, overtime_periods, is_playoff, playoff_round)

        return IntensityChange(
            old_intensity=old_intensity,
            new_intensity=new_intensity,
            change_amount=new_intensity - old_intensity,
            change_reason=reason,
        )

    def create_playoff_rivalry(
        self,
        dynasty_id: str,
        team_a_id: int,
        team_b_id: int,
        playoff_round: PlayoffRound,
        season: int,
    ) -> Optional[Rivalry]:
        """
        Create a RECENT rivalry from a playoff meeting if none exists.

        Args:
            dynasty_id: Dynasty identifier
            team_a_id: First team ID
            team_b_id: Second team ID
            playoff_round: The playoff round of the meeting
            season: Current season year

        Returns:
            Newly created Rivalry, or None if rivalry already exists
        """
        # Check if rivalry already exists
        existing = self._rivalry_api.get_rivalry_between_teams(
            dynasty_id, team_a_id, team_b_id
        )

        if existing:
            self._logger.debug(
                f"Rivalry already exists between teams {team_a_id} and {team_b_id}"
            )
            return None

        # Determine base intensity
        if playoff_round == PlayoffRound.SUPER_BOWL:
            base_intensity = self.SUPER_BOWL_RIVALRY_BASE
        else:
            base_intensity = self.PLAYOFF_RIVALRY_BASE

        # Generate rivalry name
        rivalry_name = self._generate_playoff_rivalry_name(
            team_a_id, team_b_id, playoff_round, season
        )

        # Create the rivalry
        rivalry = Rivalry(
            team_a_id=min(team_a_id, team_b_id),
            team_b_id=max(team_a_id, team_b_id),
            rivalry_type=RivalryType.RECENT,
            rivalry_name=rivalry_name,
            intensity=base_intensity,
            is_protected=False,
        )

        try:
            rivalry_id = self._rivalry_api.create_rivalry(dynasty_id, rivalry)
            rivalry.rivalry_id = rivalry_id
            self._logger.info(
                f"Created playoff rivalry: {rivalry_name} (intensity: {base_intensity})"
            )
            return rivalry
        except ValueError as e:
            # Rivalry was created between check and insert (race condition)
            self._logger.warning(f"Failed to create rivalry: {e}")
            return None

    def decay_inactive_rivalries(
        self,
        dynasty_id: str,
        completed_season: int,
    ) -> List[Tuple[Rivalry, int, str]]:
        """
        Apply annual decay to RECENT rivalries that didn't have a meeting.

        Called during offseason after season ends.

        Args:
            dynasty_id: Dynasty identifier
            completed_season: The season that just completed

        Returns:
            List of (rivalry, new_intensity, status) tuples where:
            - status is 'decayed' or 'removed'
        """
        changes = []

        # Get all RECENT rivalries
        all_rivalries = self._rivalry_api.get_all_rivalries(
            dynasty_id, rivalry_type=RivalryType.RECENT
        )

        for rivalry in all_rivalries:
            # Check if teams met this season via H2H
            h2h = self._h2h_api.get_record(
                dynasty_id, rivalry.team_a_id, rivalry.team_b_id
            )

            if h2h and h2h.last_meeting_season == completed_season:
                # Teams met this year, no decay
                continue

            # Apply decay
            new_intensity = max(0, rivalry.intensity - self.DECAY_RATE)

            if new_intensity < self.MIN_INTENSITY:
                # Remove rivalry (too weak)
                self._rivalry_api.delete_rivalry(dynasty_id, rivalry.rivalry_id)
                changes.append((rivalry, 0, 'removed'))
                self._logger.info(
                    f"Removed inactive rivalry: {rivalry.rivalry_name} "
                    f"(intensity {rivalry.intensity} -> removed)"
                )
            else:
                self._rivalry_api.update_intensity(
                    dynasty_id, rivalry.rivalry_id, new_intensity
                )
                changes.append((rivalry, new_intensity, 'decayed'))
                self._logger.info(
                    f"Decayed rivalry: {rivalry.rivalry_name} "
                    f"({rivalry.intensity} -> {new_intensity})"
                )

        return changes

    # -------------------- Calculation Methods --------------------

    def _calculate_intensity_change(
        self,
        margin: int,
        overtime_periods: int,
        is_playoff: bool,
        playoff_round: Optional[PlayoffRound],
    ) -> int:
        """
        Calculate raw intensity change from game result.

        Args:
            margin: Score margin (absolute value)
            overtime_periods: Number of OT periods
            is_playoff: Whether this is a playoff game
            playoff_round: The playoff round if applicable

        Returns:
            Integer change to apply (can be negative)
        """
        change = 0

        # Base change from game competitiveness
        if overtime_periods > 0:
            # OT games are always exciting
            change += self.OVERTIME_BOOST
        elif margin <= self.VERY_CLOSE_THRESHOLD:
            # Very close game (0-3 points)
            change += self.VERY_CLOSE_BOOST
        elif margin <= self.CLOSE_GAME_THRESHOLD:
            # Close game (4-7 points)
            change += self.CLOSE_GAME_BOOST
        elif margin >= self.BLOWOUT_THRESHOLD:
            # Blowout (20+ points) - rivalry cools off
            change += self.BLOWOUT_PENALTY
        # Normal games (8-19 points) have no effect

        # Playoff boost (stacks with game competitiveness)
        if is_playoff and playoff_round:
            playoff_boost = self.PLAYOFF_BOOSTS.get(playoff_round, 10)
            change += playoff_boost

        return change

    def _apply_change(self, rivalry: Rivalry, change: int) -> int:
        """
        Apply intensity change with bounds based on rivalry type.

        Args:
            rivalry: The rivalry being updated
            change: The change amount (can be negative)

        Returns:
            New intensity value (bounded appropriately)
        """
        new_intensity = rivalry.intensity + change

        # Apply type-specific floors
        if rivalry.rivalry_type == RivalryType.HISTORIC:
            new_intensity = max(self.HISTORIC_MIN, new_intensity)
        elif rivalry.rivalry_type == RivalryType.DIVISION:
            new_intensity = max(self.DIVISION_MIN, new_intensity)
        else:
            # GEOGRAPHIC and RECENT can go lower
            new_intensity = max(1, new_intensity)

        # Cap at 100
        return min(100, new_intensity)

    def _get_change_reason(
        self,
        margin: int,
        overtime_periods: int,
        is_playoff: bool,
        playoff_round: Optional[PlayoffRound],
    ) -> str:
        """
        Generate human-readable reason for intensity change.

        Args:
            margin: Score margin
            overtime_periods: OT periods
            is_playoff: Whether playoff game
            playoff_round: Playoff round if applicable

        Returns:
            Description of why intensity changed
        """
        reasons = []

        if overtime_periods > 0:
            reasons.append(f"overtime game ({overtime_periods} OT)")
        elif margin <= self.VERY_CLOSE_THRESHOLD:
            reasons.append(f"very close game ({margin} pt margin)")
        elif margin <= self.CLOSE_GAME_THRESHOLD:
            reasons.append(f"close game ({margin} pt margin)")
        elif margin >= self.BLOWOUT_THRESHOLD:
            reasons.append(f"blowout ({margin} pt margin)")
        else:
            reasons.append(f"normal game ({margin} pt margin)")

        if is_playoff and playoff_round:
            round_name = playoff_round.value.replace('_', ' ').title()
            reasons.append(f"{round_name} playoff")

        return ", ".join(reasons)

    def _generate_playoff_rivalry_name(
        self,
        team_a_id: int,
        team_b_id: int,
        playoff_round: PlayoffRound,
        season: int,
    ) -> str:
        """
        Generate a name for a new playoff rivalry.

        Args:
            team_a_id: First team ID
            team_b_id: Second team ID
            playoff_round: The playoff round
            season: Season year

        Returns:
            Rivalry name string
        """
        team_a_name = self._get_team_name(team_a_id)
        team_b_name = self._get_team_name(team_b_id)

        # Extract city/nickname from full names
        # e.g., "Kansas City Chiefs" -> "Chiefs"
        team_a_short = team_a_name.split()[-1]
        team_b_short = team_b_name.split()[-1]

        round_labels = {
            PlayoffRound.SUPER_BOWL: "Super Bowl",
            PlayoffRound.CONFERENCE: "Conference Championship",
            PlayoffRound.DIVISIONAL: "Divisional Round",
            PlayoffRound.WILD_CARD: "Wild Card",
        }
        round_label = round_labels.get(playoff_round, "Playoff")

        return f"{season} {round_label} Rivalry: {team_a_short} vs {team_b_short}"

    # -------------------- Query Methods --------------------

    def get_intensity_change_for_game(
        self,
        margin: int,
        overtime_periods: int = 0,
        is_playoff: bool = False,
        playoff_round: Optional[PlayoffRound] = None,
    ) -> Tuple[int, str]:
        """
        Preview intensity change without updating database.

        Useful for testing and UI previews.

        Args:
            margin: Score margin
            overtime_periods: OT periods
            is_playoff: Whether playoff game
            playoff_round: Playoff round if applicable

        Returns:
            Tuple of (change_amount, reason_string)
        """
        change = self._calculate_intensity_change(
            margin, overtime_periods, is_playoff, playoff_round
        )
        reason = self._get_change_reason(
            margin, overtime_periods, is_playoff, playoff_round
        )
        return (change, reason)
