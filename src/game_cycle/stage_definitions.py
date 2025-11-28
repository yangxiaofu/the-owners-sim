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
    # Preseason (optional - can be skipped)
    PRESEASON_WEEK_1 = auto()
    PRESEASON_WEEK_2 = auto()
    PRESEASON_WEEK_3 = auto()

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
    OFFSEASON_FRANCHISE_TAG = auto()      # Apply franchise/transition tags (before re-signing)
    OFFSEASON_RESIGNING = auto()          # Re-sign your own expiring players
    OFFSEASON_FREE_AGENCY = auto()        # Sign free agents from other teams
    OFFSEASON_DRAFT = auto()              # NFL Draft (7 rounds)
    OFFSEASON_ROSTER_CUTS = auto()        # Cut roster from 90 to 53
    OFFSEASON_WAIVER_WIRE = auto()        # Process waiver claims for cut players
    OFFSEASON_TRAINING_CAMP = auto()      # Finalize depth charts
    OFFSEASON_PRESEASON = auto()          # Exhibition games (optional)

    @classmethod
    def get_phase(cls, stage: "StageType") -> SeasonPhase:
        """Get the season phase for a given stage."""
        if stage.name.startswith("PRESEASON"):
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
            return 1
        elif self.stage_type == StageType.DIVISIONAL:
            return 2
        elif self.stage_type == StageType.CONFERENCE_CHAMPIONSHIP:
            return 3
        elif self.stage_type == StageType.SUPER_BOWL:
            return 4
        elif name.startswith("OFFSEASON_"):
            # Map offseason stages to sequential numbers
            offseason_order = [
                "OFFSEASON_FRANCHISE_TAG", "OFFSEASON_RESIGNING", "OFFSEASON_FREE_AGENCY",
                "OFFSEASON_DRAFT", "OFFSEASON_ROSTER_CUTS", "OFFSEASON_WAIVER_WIRE",
                "OFFSEASON_TRAINING_CAMP", "OFFSEASON_PRESEASON"
            ]
            if name in offseason_order:
                return offseason_order.index(name) + 1
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

        When transitioning from OFFSEASON_PRESEASON (last stage) back to PRESEASON_WEEK_1
        (first stage), the season year is incremented to start a new season.
        """
        stages = list(StageType)
        current_index = stages.index(self.stage_type)

        if current_index >= len(stages) - 1:
            # Last stage (OFFSEASON_PRESEASON) - loop back to start new season
            next_type = stages[0]  # PRESEASON_WEEK_1
            return Stage(
                stage_type=next_type,
                season_year=self.season_year + 1,  # Increment year for new season
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

# Stages that have games
GAME_STAGES = (
    [StageType.get_preseason_week(w) for w in range(1, 4)] +
    [StageType.get_regular_season_week(w) for w in range(1, 19)] +
    [StageType.WILD_CARD, StageType.DIVISIONAL,
     StageType.CONFERENCE_CHAMPIONSHIP, StageType.SUPER_BOWL]
)

# Offseason stages in order
OFFSEASON_STAGES = [
    StageType.OFFSEASON_FRANCHISE_TAG,
    StageType.OFFSEASON_RESIGNING,
    StageType.OFFSEASON_FREE_AGENCY,
    StageType.OFFSEASON_DRAFT,
    StageType.OFFSEASON_ROSTER_CUTS,
    StageType.OFFSEASON_WAIVER_WIRE,
    StageType.OFFSEASON_TRAINING_CAMP,
    StageType.OFFSEASON_PRESEASON,
]