"""
Position-specific injury risk profiles.

Based on NFL injury data:
- RBs: ~8.2 injuries per 1000 snaps (highest)
- WRs: ~6.8 injuries per 1000 snaps
- QBs: ~3.2 injuries per 1000 snaps (lowest skill position)
- K/P: ~1.5 injuries per 1000 snaps (lowest overall)
"""

from typing import Dict

from src.game_cycle.models.injury_models import (
    InjuryRisk,
    InjuryType,
    BodyPart
)


# All 25 positions with risk profiles
POSITION_INJURY_RISKS: Dict[str, InjuryRisk] = {
    # =========================================================================
    # Offensive Skill Positions
    # =========================================================================
    'QB': InjuryRisk(
        position='QB',
        base_injury_chance=0.032,  # 3.2% per game
        high_risk_body_parts=[BodyPart.SHOULDER, BodyPart.KNEE, BodyPart.ANKLE],
        common_injuries=[
            InjuryType.SHOULDER_SPRAIN,
            InjuryType.ANKLE_SPRAIN,
            InjuryType.CONCUSSION,
            InjuryType.HAND_FRACTURE,
        ]
    ),
    'RB': InjuryRisk(
        position='RB',
        base_injury_chance=0.082,  # 8.2% per game (highest)
        high_risk_body_parts=[BodyPart.KNEE, BodyPart.ANKLE, BodyPart.THIGH],
        common_injuries=[
            InjuryType.HAMSTRING_STRAIN,
            InjuryType.ANKLE_SPRAIN,
            InjuryType.KNEE_SPRAIN,
            InjuryType.ACL_TEAR,
        ]
    ),
    'FB': InjuryRisk(
        position='FB',
        base_injury_chance=0.065,
        high_risk_body_parts=[BodyPart.KNEE, BodyPart.SHOULDER, BodyPart.RIBS],
        common_injuries=[
            InjuryType.KNEE_SPRAIN,
            InjuryType.SHOULDER_SPRAIN,
            InjuryType.RIB_CONTUSION,
        ]
    ),
    'WR': InjuryRisk(
        position='WR',
        base_injury_chance=0.068,
        high_risk_body_parts=[BodyPart.THIGH, BodyPart.ANKLE, BodyPart.SHOULDER],
        common_injuries=[
            InjuryType.HAMSTRING_STRAIN,
            InjuryType.ANKLE_SPRAIN,
            InjuryType.GROIN_STRAIN,
            InjuryType.SHOULDER_SPRAIN,
        ]
    ),
    'TE': InjuryRisk(
        position='TE',
        base_injury_chance=0.071,
        high_risk_body_parts=[BodyPart.KNEE, BodyPart.ANKLE, BodyPart.HEAD],
        common_injuries=[
            InjuryType.KNEE_SPRAIN,
            InjuryType.ANKLE_SPRAIN,
            InjuryType.CONCUSSION,
            InjuryType.HAMSTRING_STRAIN,
        ]
    ),

    # =========================================================================
    # Offensive Line
    # =========================================================================
    'LT': InjuryRisk(
        position='LT',
        base_injury_chance=0.045,
        high_risk_body_parts=[BodyPart.KNEE, BodyPart.ANKLE, BodyPart.BACK],
        common_injuries=[
            InjuryType.KNEE_SPRAIN,
            InjuryType.ANKLE_SPRAIN,
            InjuryType.BACK_STRAIN,
            InjuryType.SHOULDER_SPRAIN,
        ]
    ),
    'LG': InjuryRisk(
        position='LG',
        base_injury_chance=0.045,
        high_risk_body_parts=[BodyPart.KNEE, BodyPart.ANKLE, BodyPart.BACK],
        common_injuries=[
            InjuryType.KNEE_SPRAIN,
            InjuryType.ANKLE_SPRAIN,
            InjuryType.BACK_STRAIN,
            InjuryType.SHOULDER_SPRAIN,
        ]
    ),
    'C': InjuryRisk(
        position='C',
        base_injury_chance=0.042,
        high_risk_body_parts=[BodyPart.KNEE, BodyPart.ANKLE, BodyPart.HAND],
        common_injuries=[
            InjuryType.KNEE_SPRAIN,
            InjuryType.ANKLE_SPRAIN,
            InjuryType.HAND_FRACTURE,
        ]
    ),
    'RG': InjuryRisk(
        position='RG',
        base_injury_chance=0.045,
        high_risk_body_parts=[BodyPart.KNEE, BodyPart.ANKLE, BodyPart.BACK],
        common_injuries=[
            InjuryType.KNEE_SPRAIN,
            InjuryType.ANKLE_SPRAIN,
            InjuryType.BACK_STRAIN,
            InjuryType.SHOULDER_SPRAIN,
        ]
    ),
    'RT': InjuryRisk(
        position='RT',
        base_injury_chance=0.045,
        high_risk_body_parts=[BodyPart.KNEE, BodyPart.ANKLE, BodyPart.BACK],
        common_injuries=[
            InjuryType.KNEE_SPRAIN,
            InjuryType.ANKLE_SPRAIN,
            InjuryType.BACK_STRAIN,
            InjuryType.SHOULDER_SPRAIN,
        ]
    ),

    # =========================================================================
    # Defensive Line
    # =========================================================================
    'LE': InjuryRisk(
        position='LE',
        base_injury_chance=0.052,
        high_risk_body_parts=[BodyPart.KNEE, BodyPart.SHOULDER, BodyPart.BACK],
        common_injuries=[
            InjuryType.KNEE_SPRAIN,
            InjuryType.SHOULDER_SPRAIN,
            InjuryType.BACK_STRAIN,
        ]
    ),
    'DT': InjuryRisk(
        position='DT',
        base_injury_chance=0.048,
        high_risk_body_parts=[BodyPart.KNEE, BodyPart.ANKLE, BodyPart.SHOULDER],
        common_injuries=[
            InjuryType.KNEE_SPRAIN,
            InjuryType.ANKLE_SPRAIN,
            InjuryType.SHOULDER_SPRAIN,
        ]
    ),
    'RE': InjuryRisk(
        position='RE',
        base_injury_chance=0.052,
        high_risk_body_parts=[BodyPart.KNEE, BodyPart.SHOULDER, BodyPart.BACK],
        common_injuries=[
            InjuryType.KNEE_SPRAIN,
            InjuryType.SHOULDER_SPRAIN,
            InjuryType.BACK_STRAIN,
        ]
    ),
    'EDGE': InjuryRisk(
        position='EDGE',
        base_injury_chance=0.055,
        high_risk_body_parts=[BodyPart.KNEE, BodyPart.ANKLE, BodyPart.SHOULDER],
        common_injuries=[
            InjuryType.KNEE_SPRAIN,
            InjuryType.ANKLE_SPRAIN,
            InjuryType.HAMSTRING_STRAIN,
        ]
    ),

    # =========================================================================
    # Linebackers
    # =========================================================================
    'LOLB': InjuryRisk(
        position='LOLB',
        base_injury_chance=0.061,
        high_risk_body_parts=[BodyPart.KNEE, BodyPart.THIGH, BodyPart.ANKLE],
        common_injuries=[
            InjuryType.HAMSTRING_STRAIN,
            InjuryType.KNEE_SPRAIN,
            InjuryType.ANKLE_SPRAIN,
            InjuryType.GROIN_STRAIN,
        ]
    ),
    'MLB': InjuryRisk(
        position='MLB',
        base_injury_chance=0.058,
        high_risk_body_parts=[BodyPart.KNEE, BodyPart.SHOULDER, BodyPart.HEAD],
        common_injuries=[
            InjuryType.KNEE_SPRAIN,
            InjuryType.CONCUSSION,
            InjuryType.SHOULDER_SPRAIN,
            InjuryType.ANKLE_SPRAIN,
        ]
    ),
    'ROLB': InjuryRisk(
        position='ROLB',
        base_injury_chance=0.061,
        high_risk_body_parts=[BodyPart.KNEE, BodyPart.THIGH, BodyPart.ANKLE],
        common_injuries=[
            InjuryType.HAMSTRING_STRAIN,
            InjuryType.KNEE_SPRAIN,
            InjuryType.ANKLE_SPRAIN,
            InjuryType.GROIN_STRAIN,
        ]
    ),

    # =========================================================================
    # Defensive Backs
    # =========================================================================
    'CB': InjuryRisk(
        position='CB',
        base_injury_chance=0.065,
        high_risk_body_parts=[BodyPart.THIGH, BodyPart.HIP, BodyPart.ANKLE],
        common_injuries=[
            InjuryType.HAMSTRING_STRAIN,
            InjuryType.GROIN_STRAIN,
            InjuryType.ANKLE_SPRAIN,
        ]
    ),
    'FS': InjuryRisk(
        position='FS',
        base_injury_chance=0.058,
        high_risk_body_parts=[BodyPart.SHOULDER, BodyPart.KNEE, BodyPart.ANKLE],
        common_injuries=[
            InjuryType.SHOULDER_SPRAIN,
            InjuryType.ANKLE_SPRAIN,
            InjuryType.CONCUSSION,
        ]
    ),
    'SS': InjuryRisk(
        position='SS',
        base_injury_chance=0.060,
        high_risk_body_parts=[BodyPart.SHOULDER, BodyPart.KNEE, BodyPart.HEAD],
        common_injuries=[
            InjuryType.SHOULDER_SPRAIN,
            InjuryType.CONCUSSION,
            InjuryType.KNEE_SPRAIN,
        ]
    ),

    # =========================================================================
    # Special Teams
    # =========================================================================
    'K': InjuryRisk(
        position='K',
        base_injury_chance=0.015,  # Very low
        high_risk_body_parts=[BodyPart.THIGH, BodyPart.HIP],
        common_injuries=[
            InjuryType.GROIN_STRAIN,
            InjuryType.QUAD_STRAIN,
        ]
    ),
    'P': InjuryRisk(
        position='P',
        base_injury_chance=0.015,  # Very low
        high_risk_body_parts=[BodyPart.THIGH, BodyPart.HIP],
        common_injuries=[
            InjuryType.GROIN_STRAIN,
            InjuryType.QUAD_STRAIN,
        ]
    ),
    'LS': InjuryRisk(
        position='LS',
        base_injury_chance=0.012,  # Lowest
        high_risk_body_parts=[BodyPart.SHOULDER, BodyPart.BACK],
        common_injuries=[
            InjuryType.SHOULDER_SPRAIN,
            InjuryType.BACK_STRAIN,
        ]
    ),

    # =========================================================================
    # Returners (high risk on special teams plays)
    # =========================================================================
    'KR': InjuryRisk(
        position='KR',
        base_injury_chance=0.075,  # High due to full-speed collisions
        high_risk_body_parts=[BodyPart.KNEE, BodyPart.ANKLE, BodyPart.HEAD],
        common_injuries=[
            InjuryType.ANKLE_SPRAIN,
            InjuryType.KNEE_SPRAIN,
            InjuryType.CONCUSSION,
            InjuryType.HAMSTRING_STRAIN,
        ]
    ),
    'PR': InjuryRisk(
        position='PR',
        base_injury_chance=0.070,  # High due to full-speed collisions
        high_risk_body_parts=[BodyPart.KNEE, BodyPart.ANKLE, BodyPart.SHOULDER],
        common_injuries=[
            InjuryType.ANKLE_SPRAIN,
            InjuryType.KNEE_SPRAIN,
            InjuryType.HAMSTRING_STRAIN,
            InjuryType.SHOULDER_SPRAIN,
        ]
    ),
}


def get_risk_profile(position: str) -> InjuryRisk:
    """
    Get injury risk profile for a position.

    Args:
        position: Position abbreviation (e.g., 'QB', 'RB')

    Returns:
        InjuryRisk profile for the position, or default profile if unknown
    """
    return POSITION_INJURY_RISKS.get(
        position.upper(),
        InjuryRisk(
            position=position,
            base_injury_chance=0.05,  # Default 5%
            high_risk_body_parts=[BodyPart.KNEE, BodyPart.ANKLE],
            common_injuries=[
                InjuryType.ANKLE_SPRAIN,
                InjuryType.KNEE_SPRAIN,
            ]
        )
    )
