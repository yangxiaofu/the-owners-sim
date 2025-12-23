"""Configuration for player generation contexts."""

from enum import Enum
from dataclasses import dataclass
from typing import Optional


class GenerationContext(Enum):
    """Context for player generation."""
    NFL_DRAFT = "nfl_draft"
    UDFA = "udfa"
    INTERNATIONAL_CFL = "international_cfl"
    INTERNATIONAL_XFL = "international_xfl"
    INTERNATIONAL_EUROPE = "international_europe"
    CUSTOM = "custom"


@dataclass
class GenerationConfig:
    """Configuration for player generation."""

    # Core settings
    context: GenerationContext
    position: Optional[str] = None
    archetype_id: Optional[str] = None

    # Draft-specific
    draft_round: Optional[int] = None
    draft_pick: Optional[int] = None
    draft_year: Optional[int] = None

    # Talent modifiers
    overall_min: int = 40
    overall_max: int = 99
    talent_modifier: float = 1.0  # Multiplier for attribute ranges

    # Scouting
    enable_scouting_error: bool = True
    scouting_confidence: Optional[str] = None  # "high", "medium", "low"

    # Development
    age: Optional[int] = None
    development_override: Optional[str] = None  # Override development curve

    # Dynasty
    dynasty_id: str = "default"
    class_id: Optional[str] = None  # For tracking draft class

    def get_overall_range(self) -> tuple[int, int]:
        """Calculate overall range based on context and round.

        Calibrated against actual NFL rosters:
        - League mean: 77, median: 76
        - Only 3.4% of NFL players are 90+ overall
        - Top rookies (Hutchinson, Daniels) are 89-90 - exceptional outliers
        - Most rookies need 2-4 years to reach elite status

        Returns:
            Tuple of (min_overall, max_overall)
        """
        if self.context == GenerationContext.NFL_DRAFT and self.draft_round:
            # Draft round affects overall range
            # Calibrated so rookies need development to become elite
            ranges = {
                1: (70, 86),  # First round: future stars, rare elite (max matches Hutchinson/Daniels)
                2: (67, 80),  # Second round: solid starters
                3: (64, 77),  # Third round: good depth
                4: (61, 74),  # Fourth round: rotational players
                5: (58, 71),  # Fifth round: backups
                6: (55, 68),  # Sixth round: depth
                7: (52, 65),  # Seventh round: projects
            }
            min_val, max_val = ranges.get(self.draft_round, (52, 65))

        elif self.context == GenerationContext.UDFA:
            min_val, max_val = 50, 68  # UDFA ceiling

        elif self.context in [GenerationContext.INTERNATIONAL_CFL,
                               GenerationContext.INTERNATIONAL_XFL]:
            min_val, max_val = 55, 75  # International range

        else:
            min_val, max_val = self.overall_min, self.overall_max

        return min_val, max_val

    def get_scouting_error_margin(self) -> int:
        """Get scouting error margin based on confidence.

        Returns:
            Error margin in rating points
        """
        if not self.enable_scouting_error:
            return 0

        margins = {
            "high": 3,
            "medium": 7,
            "low": 12,
            None: 7  # default
        }
        return margins.get(self.scouting_confidence, 7)