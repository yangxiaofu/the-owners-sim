"""
Injury system models and enumerations.

Defines injury types, body parts, severity levels, and core dataclasses
for tracking player injuries and IR status.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


class InjuryType(Enum):
    """All trackable injury types."""
    # Head/Neck (2)
    CONCUSSION = "concussion"
    NECK_STRAIN = "neck_strain"

    # Upper Body (4)
    SHOULDER_SPRAIN = "shoulder_sprain"
    ROTATOR_CUFF = "rotator_cuff"
    ELBOW_SPRAIN = "elbow_sprain"
    HAND_FRACTURE = "hand_fracture"

    # Core/Torso (3)
    RIB_CONTUSION = "rib_contusion"
    OBLIQUE_STRAIN = "oblique_strain"
    BACK_STRAIN = "back_strain"

    # Lower Body (11)
    HIP_POINTER = "hip_pointer"
    HAMSTRING_STRAIN = "hamstring_strain"
    GROIN_STRAIN = "groin_strain"
    QUAD_STRAIN = "quad_strain"
    KNEE_SPRAIN = "knee_sprain"
    ACL_TEAR = "acl_tear"
    MCL_SPRAIN = "mcl_sprain"
    CALF_STRAIN = "calf_strain"
    ANKLE_SPRAIN = "ankle_sprain"
    ACHILLES_TEAR = "achilles_tear"
    FOOT_FRACTURE = "foot_fracture"


class InjurySeverity(Enum):
    """Injury severity classification."""
    MINOR = "minor"               # 1-2 weeks
    MODERATE = "moderate"         # 3-4 weeks
    SEVERE = "severe"             # 5-8 weeks
    SEASON_ENDING = "season_ending"  # 10+ weeks / out for season


class BodyPart(Enum):
    """Body parts that can be injured."""
    HEAD = "head"
    NECK = "neck"
    SHOULDER = "shoulder"
    ARM = "arm"
    ELBOW = "elbow"
    HAND = "hand"
    RIBS = "ribs"
    BACK = "back"
    CORE = "core"
    HIP = "hip"
    THIGH = "thigh"
    KNEE = "knee"
    LOWER_LEG = "lower_leg"
    ANKLE = "ankle"
    FOOT = "foot"


# Map injury types to their affected body parts
INJURY_TYPE_TO_BODY_PART: Dict[InjuryType, BodyPart] = {
    InjuryType.CONCUSSION: BodyPart.HEAD,
    InjuryType.NECK_STRAIN: BodyPart.NECK,
    InjuryType.SHOULDER_SPRAIN: BodyPart.SHOULDER,
    InjuryType.ROTATOR_CUFF: BodyPart.SHOULDER,
    InjuryType.ELBOW_SPRAIN: BodyPart.ELBOW,
    InjuryType.HAND_FRACTURE: BodyPart.HAND,
    InjuryType.RIB_CONTUSION: BodyPart.RIBS,
    InjuryType.OBLIQUE_STRAIN: BodyPart.CORE,
    InjuryType.BACK_STRAIN: BodyPart.BACK,
    InjuryType.HIP_POINTER: BodyPart.HIP,
    InjuryType.HAMSTRING_STRAIN: BodyPart.THIGH,
    InjuryType.GROIN_STRAIN: BodyPart.HIP,
    InjuryType.QUAD_STRAIN: BodyPart.THIGH,
    InjuryType.KNEE_SPRAIN: BodyPart.KNEE,
    InjuryType.ACL_TEAR: BodyPart.KNEE,
    InjuryType.MCL_SPRAIN: BodyPart.KNEE,
    InjuryType.CALF_STRAIN: BodyPart.LOWER_LEG,
    InjuryType.ANKLE_SPRAIN: BodyPart.ANKLE,
    InjuryType.ACHILLES_TEAR: BodyPart.ANKLE,
    InjuryType.FOOT_FRACTURE: BodyPart.FOOT,
}


# Typical weeks out by severity
INJURY_SEVERITY_WEEKS: Dict[InjurySeverity, tuple] = {
    InjurySeverity.MINOR: (1, 2),
    InjurySeverity.MODERATE: (3, 4),
    InjurySeverity.SEVERE: (5, 8),
    InjurySeverity.SEASON_ENDING: (10, 18),
}


# Injury type to typical severity (some injuries are always severe)
INJURY_TYPE_SEVERITY_RANGE: Dict[InjuryType, List[InjurySeverity]] = {
    InjuryType.CONCUSSION: [InjurySeverity.MINOR, InjurySeverity.MODERATE],
    InjuryType.NECK_STRAIN: [InjurySeverity.MINOR, InjurySeverity.MODERATE],
    InjuryType.SHOULDER_SPRAIN: [InjurySeverity.MINOR, InjurySeverity.MODERATE, InjurySeverity.SEVERE],
    InjuryType.ROTATOR_CUFF: [InjurySeverity.SEVERE, InjurySeverity.SEASON_ENDING],
    InjuryType.ELBOW_SPRAIN: [InjurySeverity.MINOR, InjurySeverity.MODERATE],
    InjuryType.HAND_FRACTURE: [InjurySeverity.MODERATE, InjurySeverity.SEVERE],
    InjuryType.RIB_CONTUSION: [InjurySeverity.MINOR, InjurySeverity.MODERATE],
    InjuryType.OBLIQUE_STRAIN: [InjurySeverity.MINOR, InjurySeverity.MODERATE],
    InjuryType.BACK_STRAIN: [InjurySeverity.MINOR, InjurySeverity.MODERATE, InjurySeverity.SEVERE],
    InjuryType.HIP_POINTER: [InjurySeverity.MINOR, InjurySeverity.MODERATE],
    InjuryType.HAMSTRING_STRAIN: [InjurySeverity.MINOR, InjurySeverity.MODERATE, InjurySeverity.SEVERE],
    InjuryType.GROIN_STRAIN: [InjurySeverity.MINOR, InjurySeverity.MODERATE],
    InjuryType.QUAD_STRAIN: [InjurySeverity.MINOR, InjurySeverity.MODERATE],
    InjuryType.KNEE_SPRAIN: [InjurySeverity.MODERATE, InjurySeverity.SEVERE],
    InjuryType.ACL_TEAR: [InjurySeverity.SEASON_ENDING],  # Always season-ending
    InjuryType.MCL_SPRAIN: [InjurySeverity.MODERATE, InjurySeverity.SEVERE],
    InjuryType.CALF_STRAIN: [InjurySeverity.MINOR, InjurySeverity.MODERATE],
    InjuryType.ANKLE_SPRAIN: [InjurySeverity.MINOR, InjurySeverity.MODERATE, InjurySeverity.SEVERE],
    InjuryType.ACHILLES_TEAR: [InjurySeverity.SEASON_ENDING],  # Always season-ending
    InjuryType.FOOT_FRACTURE: [InjurySeverity.SEVERE, InjurySeverity.SEASON_ENDING],
}


@dataclass
class Injury:
    """
    Represents a player injury.

    Can be created from database row or manually constructed.
    """
    player_id: int
    player_name: str
    team_id: int
    injury_type: InjuryType
    body_part: BodyPart
    severity: InjurySeverity
    weeks_out: int
    week_occurred: int
    season: int
    occurred_during: str  # 'game' or 'practice'
    injury_id: Optional[int] = None
    game_id: Optional[str] = None
    play_description: Optional[str] = None
    is_active: bool = True
    on_ir: bool = False
    ir_placement_date: Optional[str] = None
    ir_return_date: Optional[str] = None

    @classmethod
    def from_db_row(cls, row: Dict[str, Any]) -> 'Injury':
        """
        Create Injury from database row dict.

        Args:
            row: Database row as dict with injury columns

        Returns:
            Injury instance
        """
        return cls(
            injury_id=row.get('injury_id'),
            player_id=row['player_id'],
            player_name=row.get('player_name', 'Unknown'),
            team_id=row.get('team_id', 0),
            injury_type=InjuryType(row['injury_type']),
            body_part=BodyPart(row['body_part']),
            severity=InjurySeverity(row['severity']),
            weeks_out=row['estimated_weeks_out'],
            week_occurred=row['week_occurred'],
            season=row['season'],
            occurred_during=row['occurred_during'],
            game_id=row.get('game_id'),
            play_description=row.get('play_description'),
            is_active=bool(row.get('is_active', 1)),
            on_ir=bool(row.get('ir_placement_date')),
            ir_placement_date=row.get('ir_placement_date'),
            ir_return_date=row.get('ir_return_date'),
        )

    def to_db_dict(self) -> Dict[str, Any]:
        """
        Convert to dict for database insertion.

        Returns:
            Dict with database column names and values
        """
        return {
            'player_id': self.player_id,
            'injury_type': self.injury_type.value,
            'body_part': self.body_part.value,
            'severity': self.severity.value,
            'estimated_weeks_out': self.weeks_out,
            'week_occurred': self.week_occurred,
            'season': self.season,
            'occurred_during': self.occurred_during,
            'game_id': self.game_id,
            'play_description': self.play_description,
            'is_active': 1 if self.is_active else 0,
            'ir_placement_date': self.ir_placement_date,
            'ir_return_date': self.ir_return_date,
        }

    @property
    def display_name(self) -> str:
        """Human-readable injury name."""
        return self.injury_type.value.replace('_', ' ').title()

    @property
    def estimated_return_week(self) -> int:
        """Calculate expected return week."""
        return self.week_occurred + self.weeks_out

    @property
    def severity_display(self) -> str:
        """Human-readable severity."""
        return self.severity.value.replace('_', ' ').title()

    def __str__(self) -> str:
        """String representation for logging/display."""
        return f"{self.player_name}: {self.display_name} ({self.severity_display}) - {self.weeks_out} weeks"


@dataclass
class InjuryRisk:
    """
    Position-specific injury risk profile.

    Used by injury probability calculations in Tollgate 2.
    """
    position: str
    base_injury_chance: float  # Per game (0.0-1.0)
    high_risk_body_parts: List[BodyPart] = field(default_factory=list)
    common_injuries: List[InjuryType] = field(default_factory=list)

    def get_injury_probability(self, durability: int) -> float:
        """
        Calculate injury probability adjusted by durability.

        Args:
            durability: Player's durability rating (0-100)

        Returns:
            Adjusted injury probability (0.0-1.0)
        """
        # Higher durability = lower injury chance
        # Durability 100 = 50% reduction, Durability 0 = 50% increase
        durability_modifier = 1.0 - ((durability - 50) / 100)
        return self.base_injury_chance * durability_modifier


# Default injury risk profiles by position (to be expanded in Tollgate 2)
DEFAULT_INJURY_RISKS: Dict[str, InjuryRisk] = {
    'RB': InjuryRisk(
        position='RB',
        base_injury_chance=0.08,  # 8% per game
        high_risk_body_parts=[BodyPart.KNEE, BodyPart.ANKLE, BodyPart.THIGH],
        common_injuries=[
            InjuryType.HAMSTRING_STRAIN,
            InjuryType.ANKLE_SPRAIN,
            InjuryType.KNEE_SPRAIN,
            InjuryType.ACL_TEAR,
        ]
    ),
    'WR': InjuryRisk(
        position='WR',
        base_injury_chance=0.06,
        high_risk_body_parts=[BodyPart.ANKLE, BodyPart.THIGH, BodyPart.SHOULDER],
        common_injuries=[
            InjuryType.HAMSTRING_STRAIN,
            InjuryType.ANKLE_SPRAIN,
            InjuryType.SHOULDER_SPRAIN,
        ]
    ),
    'QB': InjuryRisk(
        position='QB',
        base_injury_chance=0.04,
        high_risk_body_parts=[BodyPart.SHOULDER, BodyPart.KNEE, BodyPart.ANKLE],
        common_injuries=[
            InjuryType.ANKLE_SPRAIN,
            InjuryType.SHOULDER_SPRAIN,
            InjuryType.CONCUSSION,
        ]
    ),
}
