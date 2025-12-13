"""
Voter Archetypes for Awards Voting Simulation.

Defines voter types with different scoring preferences for NFL award voting.
Each archetype has unique weighting for stats, grades, and team success,
along with optional position biases.

Part of Milestone 10: Awards System, Tollgate 3.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Dict
import random

if TYPE_CHECKING:
    from .models import AwardScore


class VoterArchetype(Enum):
    """
    Types of voters in the award voting simulation.

    Distribution for 50 voters:
    - BALANCED: 20 voters (40%)
    - STATS_FOCUSED: 10 voters (20%)
    - ANALYTICS: 10 voters (20%)
    - NARRATIVE_DRIVEN: 5 voters (10%)
    - TRADITIONAL: 5 voters (10%)
    """
    BALANCED = "balanced"
    STATS_FOCUSED = "stats"
    ANALYTICS = "analytics"
    NARRATIVE_DRIVEN = "narrative"
    TRADITIONAL = "traditional"


# ============================================
# Archetype Configuration
# ============================================

# Weighting for each archetype: how they value stats vs grades vs team success
ARCHETYPE_WEIGHTS: Dict[VoterArchetype, Dict[str, float]] = {
    VoterArchetype.BALANCED: {
        'stat': 0.40,
        'grade': 0.40,
        'team': 0.20,
    },
    VoterArchetype.STATS_FOCUSED: {
        'stat': 0.60,
        'grade': 0.30,
        'team': 0.10,
    },
    VoterArchetype.ANALYTICS: {
        'stat': 0.20,
        'grade': 0.70,
        'team': 0.10,
    },
    VoterArchetype.NARRATIVE_DRIVEN: {
        'stat': 0.30,
        'grade': 0.30,
        'team': 0.40,
    },
    VoterArchetype.TRADITIONAL: {
        'stat': 0.40,
        'grade': 0.40,
        'team': 0.20,
    },
}


# Position bias for TRADITIONAL voters
# QB gets boost, skill position defenders get penalty
TRADITIONAL_POSITION_BIAS: Dict[str, float] = {
    # Offense - QB favoritism
    'QB': 1.20,      # +20% bonus
    'RB': 1.00,
    'FB': 0.90,
    'WR': 0.90,      # -10% penalty (modern game bias)
    'TE': 0.95,
    'LT': 0.85,
    'LG': 0.85,
    'C': 0.85,
    'RG': 0.85,
    'RT': 0.85,

    # Defense - pass rushers get less credit
    'LE': 0.90,      # -10% penalty
    'DT': 0.95,
    'RE': 0.90,
    'EDGE': 0.90,
    'LOLB': 0.95,
    'MLB': 1.00,
    'ROLB': 0.95,
    'CB': 0.90,
    'FS': 0.95,
    'SS': 0.95,

    # Special teams - rarely considered
    'K': 0.70,
    'P': 0.70,
    'LS': 0.50,
    'KR': 0.60,
    'PR': 0.60,
}

DEFAULT_POSITION_BIAS = 1.0


# Voter distribution for generating 50 voters
VOTER_DISTRIBUTION = [
    (VoterArchetype.BALANCED, 20),
    (VoterArchetype.STATS_FOCUSED, 10),
    (VoterArchetype.ANALYTICS, 10),
    (VoterArchetype.NARRATIVE_DRIVEN, 5),
    (VoterArchetype.TRADITIONAL, 5),
]


# ============================================
# Voter Profile
# ============================================

@dataclass
class VoterProfile:
    """
    Represents a single voter with preferences.

    Each voter has an archetype that determines how they weight
    different scoring components, plus individual variance to
    create realistic vote spread.

    Attributes:
        voter_id: Unique identifier for the voter
        archetype: The voter's scoring preference type
        variance: Random variance factor (0.05-0.15)
        position_bias: Position-specific multipliers (TRADITIONAL only)
    """
    voter_id: str
    archetype: VoterArchetype
    variance: float = 0.10
    position_bias: Dict[str, float] = field(default_factory=dict)

    def adjust_score(self, score: "AwardScore", rng: random.Random) -> float:
        """
        Adjust candidate score based on voter preferences.

        Takes the candidate's component scores and recalculates
        using this voter's archetype weighting, then applies
        position bias (if TRADITIONAL) and random variance.

        Args:
            score: AwardScore with stat/grade/team components
            rng: Random number generator for deterministic variance

        Returns:
            Adjusted score value used for this voter's ranking
        """
        weights = ARCHETYPE_WEIGHTS[self.archetype]

        # Recalculate weighted score using voter's preferences
        weighted = (
            score.stat_component * weights['stat'] +
            score.grade_component * weights['grade'] +
            score.team_success_component * weights['team']
        )

        # Apply position bias for TRADITIONAL voters
        if self.archetype == VoterArchetype.TRADITIONAL and self.position_bias:
            bias = self.position_bias.get(score.position, DEFAULT_POSITION_BIAS)
            weighted *= bias

        # Apply individual variance to create vote spread
        # Range: -variance to +variance (e.g., -10% to +10%)
        variance_factor = 1.0 + rng.uniform(-self.variance, self.variance)

        return weighted * variance_factor

    def get_weights(self) -> Dict[str, float]:
        """Get the weighting configuration for this voter's archetype."""
        return ARCHETYPE_WEIGHTS[self.archetype].copy()

    def __repr__(self) -> str:
        return (
            f"VoterProfile(id={self.voter_id}, "
            f"archetype={self.archetype.value}, "
            f"variance={self.variance:.2f})"
        )
