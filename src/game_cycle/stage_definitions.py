"""
Stage definitions for the game cycle system.

Defines all stages the simulation can be in, organized by season phase.
"""

from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional


class SeasonPhase(Enum):
    """High-level phase of the NFL season."""
    PRESEASON = auto()
    REGULAR_SEASON = auto()
    PLAYOFFS = auto()
    OFFSEASON = auto()


class StageType(Enum):
    """
    All possible stages in a season cycle.

    Stages are ordered - the simulation progresses through them sequentially.
    """
    # Preseason (DEPRECATED - use OFFSEASON_PRESEASON_W1/W2/W3 instead)
    # These stages are kept for backwards compatibility but should not be used.
    # The offseason preseason stages now handle both games and cuts.
    PRESEASON_WEEK_1 = auto()  # DEPRECATED
    PRESEASON_WEEK_2 = auto()  # DEPRECATED
    PRESEASON_WEEK_3 = auto()  # DEPRECATED

    # Regular Season - 18 weeks
    REGULAR_WEEK_1 = auto()
    REGULAR_WEEK_2 = auto()
    REGULAR_WEEK_3 = auto()
    REGULAR_WEEK_4 = auto()
    REGULAR_WEEK_5 = auto()
    REGULAR_WEEK_6 = auto()
    REGULAR_WEEK_7 = auto()
    REGULAR_WEEK_8 = auto()
    REGULAR_WEEK_9 = auto()
    REGULAR_WEEK_10 = auto()
    REGULAR_WEEK_11 = auto()
    REGULAR_WEEK_12 = auto()
    REGULAR_WEEK_13 = auto()
    REGULAR_WEEK_14 = auto()
    REGULAR_WEEK_15 = auto()
    REGULAR_WEEK_16 = auto()
    REGULAR_WEEK_17 = auto()
    REGULAR_WEEK_18 = auto()

    # Playoffs - 4 rounds
    WILD_CARD = auto()
    DIVISIONAL = auto()
    CONFERENCE_CHAMPIONSHIP = auto()
    SUPER_BOWL = auto()

    # Offseason phases (Madden-style)
    OFFSEASON_HONORS = auto()             # NFL Honors - Awards announced (Thursday before Super Bowl IRL)
    OFFSEASON_OWNER = auto()              # Owner review - keep/fire GM, HC decisions
    OFFSEASON_FRANCHISE_TAG = auto()      # Apply franchise/transition tags (before re-signing)
    OFFSEASON_RESIGNING = auto()          # Re-sign your own expiring players
    OFFSEASON_FREE_AGENCY = auto()        # Sign free agents from other teams
    OFFSEASON_TRADING = auto()            # Trade players and draft picks
    OFFSEASON_DRAFT = auto()              # NFL Draft (7 rounds)
    OFFSEASON_TRAINING_CAMP = auto()      # Training camp - player progression (90 players)
    OFFSEASON_PRESEASON_W1 = auto()       # Preseason Week 1 - full game simulation (no cuts)
    OFFSEASON_PRESEASON_W2 = auto()       # Preseason Week 2 - full game simulation (no cuts)
    OFFSEASON_PRESEASON_W3 = auto()       # Preseason Week 3 - full game simulation (no cuts)
    OFFSEASON_ROSTER_CUTS = auto()        # Final roster cuts (90 → 53)
    OFFSEASON_WAIVER_WIRE = auto()        # Process waiver claims for cut players

    @classmethod
    def get_phase(cls, stage: "StageType") -> SeasonPhase:
        """Get the season phase for a given stage."""
        # Check for offseason preseason weeks first (before generic PRESEASON check)
        if stage.name.startswith("OFFSEASON_PRESEASON"):
            return SeasonPhase.PRESEASON
        elif stage.name.startswith("PRESEASON"):
            return SeasonPhase.PRESEASON
        elif stage.name.startswith("REGULAR"):
            return SeasonPhase.REGULAR_SEASON
        elif stage in (cls.WILD_CARD, cls.DIVISIONAL,
                       cls.CONFERENCE_CHAMPIONSHIP, cls.SUPER_BOWL):
            return SeasonPhase.PLAYOFFS
        else:
            return SeasonPhase.OFFSEASON

    @classmethod
    def get_regular_season_week(cls, week_number: int) -> "StageType":
        """Get the stage for a regular season week (1-18)."""
        if not 1 <= week_number <= 18:
            raise ValueError(f"Week must be 1-18, got {week_number}")
        return cls[f"REGULAR_WEEK_{week_number}"]

    @classmethod
    def get_preseason_week(cls, week_number: int) -> "StageType":
        """Get the stage for a preseason week (1-3)."""
        if not 1 <= week_number <= 3:
            raise ValueError(f"Preseason week must be 1-3, got {week_number}")
        return cls[f"PRESEASON_WEEK_{week_number}"]


@dataclass
class Stage:
    """
    Represents the current stage in the game cycle.

    Attributes:
        stage_type: The type of stage (week, playoff round, offseason phase)
        season_year: The NFL season year (e.g., 2025 for 2025-26 season)
        completed: Whether this stage has been fully simulated
    """
    stage_type: StageType
    season_year: int
    completed: bool = False

    @property
    def phase(self) -> SeasonPhase:
        """Get the season phase for this stage."""
        return StageType.get_phase(self.stage_type)

    @property
    def week_number(self) -> Optional[int]:
        """
        Get the week number for this stage, if applicable.

        Returns:
            Week number (1-18 for regular season, 1-3 for preseason, 1-4 for playoffs/offseason)
            or None if not applicable.
        """
        name = self.stage_type.name
        if name.startswith("REGULAR_WEEK_"):
            return int(name.replace("REGULAR_WEEK_", ""))
        elif name.startswith("PRESEASON_WEEK_"):
            return int(name.replace("PRESEASON_WEEK_", ""))
        elif self.stage_type == StageType.WILD_CARD:
            return 19  # Database week for Wild Card (matches playoffs.py _round_to_week)
        elif self.stage_type == StageType.DIVISIONAL:
            return 20  # Database week for Divisional
        elif self.stage_type == StageType.CONFERENCE_CHAMPIONSHIP:
            return 21  # Database week for Conference Championship
        elif self.stage_type == StageType.SUPER_BOWL:
            return 22  # Database week for Super Bowl
        elif name.startswith("OFFSEASON_"):
            # Map offseason stages to database week numbers (matches offseason.py social post generation)
            offseason_week_map = {
                "OFFSEASON_HONORS": 23,            # Awards ceremony (week 23)
                "OFFSEASON_OWNER": 23,             # Owner review (no social posts, use same as honors)
                "OFFSEASON_FRANCHISE_TAG": 24,     # Franchise tags
                "OFFSEASON_RESIGNING": 24,         # Re-signing (same week as tags)
                "OFFSEASON_FREE_AGENCY": 25,       # Free agency
                "OFFSEASON_TRADING": 26,           # Trading period
                "OFFSEASON_DRAFT": 27,             # NFL Draft
                "OFFSEASON_TRAINING_CAMP": 27,     # Training camp (no social posts, use draft week)
                "OFFSEASON_PRESEASON_W1": 27,      # Preseason W1 (no posts yet, use draft week)
                "OFFSEASON_PRESEASON_W2": 28,      # Preseason W2 (no posts yet, use cuts week)
                "OFFSEASON_PRESEASON_W3": 28,      # Preseason W3 (games only)
                "OFFSEASON_ROSTER_CUTS": 28,       # Final roster cuts (same week as W3)
                "OFFSEASON_WAIVER_WIRE": 29,       # Waiver wire claims
            }
            return offseason_week_map.get(name)
        return None

    @property
    def display_name(self) -> str:
        """Human-readable name for this stage."""
        name = self.stage_type.name

        if name.startswith("REGULAR_WEEK_"):
            week = name.replace("REGULAR_WEEK_", "")
            return f"Week {week}"
        elif name.startswith("PRESEASON_WEEK_"):
            week = name.replace("PRESEASON_WEEK_", "")
            return f"Preseason Week {week}"
        elif name.startswith("OFFSEASON_PRESEASON_W"):
            # OFFSEASON_PRESEASON_W1 -> "Preseason Week 1"
            # OFFSEASON_PRESEASON_W3 -> "Preseason Week 3"
            week = name.replace("OFFSEASON_PRESEASON_W", "")
            return f"Preseason Week {week}"
        elif name.startswith("OFFSEASON_"):
            # Convert OFFSEASON_FREE_AGENCY -> "Free Agency"
            phase_name = name.replace("OFFSEASON_", "").replace("_", " ").title()
            return phase_name
        else:
            # WILD_CARD -> "Wild Card"
            return name.replace("_", " ").title()

    def next_stage(self) -> Optional["Stage"]:
        """
        Get the next stage in the cycle.

        Note: This method only determines the NEXT stage type, not the season year.
        The season year is managed by StageController as the SSOT (Single Source of Truth).
        StageController.advance_to_next_stage() will override the season_year from the SSOT
        when appropriate (e.g., when transitioning to a new season).

        Special cases:
        - After OFFSEASON_WAIVER_WIRE: Loop back to REGULAR_WEEK_1
          (season increment handled by StageController, not here)
        - Skip deprecated PRESEASON_WEEK_* stages
        """
        stages = list(StageType)
        current_index = stages.index(self.stage_type)

        if current_index >= len(stages) - 1:
            # Last stage (OFFSEASON_WAIVER_WIRE) - loop back to start new season
            # Skip deprecated PRESEASON_WEEK_* stages, go directly to REGULAR_WEEK_1
            # NOTE: Season year will be overridden by StageController from SSOT
            next_type = StageType.REGULAR_WEEK_1
            return Stage(
                stage_type=next_type,
                season_year=self.season_year,  # Placeholder, controller will override
                completed=False
            )

        # Normal progression to next stage
        next_type = stages[current_index + 1]

        return Stage(
            stage_type=next_type,
            season_year=self.season_year,  # Keep same year within season
            completed=False
        )


# Ordered list of all stages for iteration
ALL_STAGES = list(StageType)

# Stages that have games (includes offseason preseason weeks)
GAME_STAGES = (
    [StageType.get_regular_season_week(w) for w in range(1, 19)] +
    [StageType.WILD_CARD, StageType.DIVISIONAL,
     StageType.CONFERENCE_CHAMPIONSHIP, StageType.SUPER_BOWL] +
    [StageType.OFFSEASON_PRESEASON_W1, StageType.OFFSEASON_PRESEASON_W2,
     StageType.OFFSEASON_PRESEASON_W3]
)

# Offseason stages in order
OFFSEASON_STAGES = [
    StageType.OFFSEASON_HONORS,           # NFL Honors - Awards ceremony
    StageType.OFFSEASON_OWNER,            # Owner review - keep/fire GM, HC
    StageType.OFFSEASON_FRANCHISE_TAG,
    StageType.OFFSEASON_RESIGNING,
    StageType.OFFSEASON_FREE_AGENCY,
    StageType.OFFSEASON_TRADING,
    StageType.OFFSEASON_DRAFT,
    StageType.OFFSEASON_TRAINING_CAMP,    # Training camp - player progression (90 players)
    StageType.OFFSEASON_PRESEASON_W1,     # Preseason Week 1 - game simulation (no cuts)
    StageType.OFFSEASON_PRESEASON_W2,     # Preseason Week 2 - game simulation (no cuts)
    StageType.OFFSEASON_PRESEASON_W3,     # Preseason Week 3 - game simulation (no cuts)
    StageType.OFFSEASON_ROSTER_CUTS,      # Final roster cuts (90 → 53)
    StageType.OFFSEASON_WAIVER_WIRE,      # Process waiver claims for cut players
]

# Offseason stages that require user interaction (don't auto-advance)
INTERACTIVE_OFFSEASON_STAGES = frozenset({
    StageType.OFFSEASON_HONORS,
    StageType.OFFSEASON_OWNER,
    StageType.OFFSEASON_FRANCHISE_TAG,
    StageType.OFFSEASON_RESIGNING,
    StageType.OFFSEASON_FREE_AGENCY,
    StageType.OFFSEASON_TRADING,
    StageType.OFFSEASON_DRAFT,
    StageType.OFFSEASON_PRESEASON_W1,
    StageType.OFFSEASON_PRESEASON_W2,
    StageType.OFFSEASON_PRESEASON_W3,
    StageType.OFFSEASON_ROSTER_CUTS,
    StageType.OFFSEASON_WAIVER_WIRE,
})

# Roster limits for each preseason phase (Modern NFL 2024+ style - single cutdown)
# Note: No incremental cuts after W1/W2, only final cut to 53 after W3
ROSTER_LIMITS = {
    "TRAINING_CAMP": 90,
    "PRESEASON_W1": 90,  # No cuts after Week 1
    "PRESEASON_W2": 90,  # No cuts after Week 2
    "PRESEASON_W3": 53,  # Final cuts after Week 3 (90 → 53)
}