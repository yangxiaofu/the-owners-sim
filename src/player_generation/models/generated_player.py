"""Complete generated player with all metadata."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import date


@dataclass
class ScoutingReport:
    """Scouting evaluation of a player."""
    scouted_overall: int
    true_overall: int
    error_margin: int
    confidence: str  # "high", "medium", "low"
    strengths: List[str]
    weaknesses: List[str]
    comparison: str  # "Plays like [NFL Player]"
    scouting_grade: str  # "A+", "A", "B+", etc.

    @staticmethod
    def get_grade_from_overall(overall: int) -> str:
        """Convert overall to scouting grade.

        Args:
            overall: Overall rating

        Returns:
            Scouting grade string
        """
        if overall >= 90:
            return "A+"
        if overall >= 85:
            return "A"
        if overall >= 80:
            return "A-"
        if overall >= 75:
            return "B+"
        if overall >= 70:
            return "B"
        if overall >= 65:
            return "B-"
        if overall >= 60:
            return "C+"
        return "C"


@dataclass
class PlayerBackground:
    """Player background information."""
    college: str
    hometown: str
    home_state: str

    # Combine stats (if applicable)
    forty_yard_dash: Optional[float] = None
    bench_press: Optional[int] = None
    vertical_jump: Optional[float] = None
    broad_jump: Optional[int] = None
    three_cone: Optional[float] = None
    shuttle: Optional[float] = None

    # College production
    college_games_played: Optional[int] = None
    college_stats: Dict[str, float] = field(default_factory=dict)


@dataclass
class DevelopmentProfile:
    """Player development trajectory."""
    current_age: int
    peak_age_min: int
    peak_age_max: int
    development_curve: str  # "early", "normal", "late"
    growth_rate: float  # Points per year during growth phase
    decline_rate: float  # Points per year during decline phase

    def is_in_growth_phase(self) -> bool:
        """Check if player is still developing.

        Returns:
            True if in growth phase
        """
        return self.current_age < self.peak_age_min

    def is_in_peak_phase(self) -> bool:
        """Check if player is in peak years.

        Returns:
            True if in peak phase
        """
        return self.peak_age_min <= self.current_age <= self.peak_age_max

    def is_in_decline_phase(self) -> bool:
        """Check if player is declining.

        Returns:
            True if in decline phase
        """
        return self.current_age > self.peak_age_max


@dataclass
class GeneratedPlayer:
    """Complete generated player with all metadata."""

    # Core identity
    player_id: str
    name: str
    position: str
    age: int
    jersey_number: Optional[int] = None

    # Attributes
    true_ratings: Dict[str, int] = field(default_factory=dict)
    scouted_ratings: Dict[str, int] = field(default_factory=dict)

    # Overall ratings
    true_overall: int = 0
    scouted_overall: int = 0
    potential: int = 0  # Maximum achievable rating (ceiling)

    # Metadata
    archetype_id: str = ""
    generation_context: str = ""

    # Optional components
    scouting_report: Optional[ScoutingReport] = None
    background: Optional[PlayerBackground] = None
    development: Optional[DevelopmentProfile] = None
    traits: List[str] = field(default_factory=list)

    # Dynasty tracking
    dynasty_id: str = "default"
    draft_class_id: Optional[str] = None
    draft_round: Optional[int] = None
    draft_pick: Optional[int] = None

    def to_player_dict(self) -> Dict:
        """Convert to Player class compatible dictionary.

        Returns:
            Dictionary compatible with Player class
        """
        return {
            "name": self.name,
            "number": self.jersey_number or 0,
            "primary_position": self.position,
            "ratings": self.true_ratings,
            "age": self.age,
            "traits": self.traits
        }

    def get_display_overall(self) -> int:
        """Get overall rating for display (scouted if available).

        Returns:
            Overall rating to display
        """
        return self.scouted_overall if self.scouted_overall > 0 else self.true_overall