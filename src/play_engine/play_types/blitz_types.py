"""
Blitz package types and rusher assignment system.

This module defines named blitz packages with specific rusher configurations,
enabling dynamic pass rusher pools based on the actual defensive play call.

NFL Reality:
- 4-man rush: DEs + DTs only, ~5-6% sack rate
- 5-man blitz: +1 LB or DB, ~7-8% sack rate
- 6-man blitz: +2 rushers, ~9-10% sack rate
- Cover-0: All-out pressure, no safety help, ~12-15% sack rate

The key insight is that only players actually rushing should be sack-eligible.
LBs in coverage shouldn't get sacks, and blitzing DBs should be able to.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Set, Optional


class BlitzPackageType(Enum):
    """
    Named blitz packages with defined rusher configurations.

    Each package specifies who rushes and who covers, enabling
    realistic sack attribution based on the actual play call.
    """
    # Base rushes (no extra rushers beyond DL)
    FOUR_MAN_BASE = "four_man_base"          # Standard 4-man rush (DEs + DTs)
    THREE_MAN_RUSH = "three_man_rush"        # Prevent defense (drop 8 into coverage)

    # 5-man blitzes (1 extra rusher)
    MIKE_BLITZ = "mike_blitz"                # MLB/MIKE shoots gap
    SAM_BLITZ = "sam_blitz"                  # SAM LB blitzes
    WILL_BLITZ = "will_blitz"                # WILL LB blitzes
    OLB_BLITZ = "olb_blitz"                  # Generic OLB blitz
    A_GAP_BLITZ = "a_gap_blitz"              # MLB through A-gap (between C and G)

    # 6-man blitzes (2 extra rushers)
    DOUBLE_A_GAP = "double_a_gap"            # Both ILBs through A-gaps
    DOUBLE_LB = "double_lb"                  # Two LBs blitz
    LB_DB_COMBO = "lb_db_combo"              # 1 LB + 1 DB blitz

    # DB blitzes (safety or corner rushes)
    CORNER_BLITZ = "corner_blitz"            # CB rushes off the edge
    SAFETY_BLITZ = "safety_blitz"            # FS or SS rushes
    NICKEL_BLITZ = "nickel_blitz"            # Nickel CB rushes (slot defender)
    DOUBLE_SAFETY = "double_safety"          # Both safeties blitz (Cover-0 variant)

    # Exotic packages (complex schemes)
    ZONE_DOG = "zone_dog"                    # LBs blitz, DBs play zone behind
    FIRE_ZONE = "fire_zone"                  # 5-man rush with 3-deep zone
    COVER_0_BLITZ = "cover_0_blitz"          # All-out pressure, no safety help
    OVERLOAD_BLITZ = "overload_blitz"        # Multiple rushers to one side


@dataclass
class BlitzPackageDefinition:
    """
    Defines which positions rush in each blitz package.

    Attributes:
        package_type: The blitz package enum value
        base_rushers: Positions that always rush (typically DL)
        additional_rushers: Extra positions that blitz in this package
        num_rushers: Total number of pass rushers
        coverage_type: Type of coverage behind the blitz
        sack_rate_modifier: Multiplier on base sack rate (1.0 = no change)
        pressure_rate_modifier: Multiplier on base pressure rate
        risk_factor: How risky this blitz is (affects big play chance)
    """
    package_type: BlitzPackageType
    base_rushers: Set[str] = field(default_factory=set)
    additional_rushers: Set[str] = field(default_factory=set)
    num_rushers: int = 4
    coverage_type: str = "zone"
    sack_rate_modifier: float = 1.0
    pressure_rate_modifier: float = 1.0
    risk_factor: float = 0.0  # 0.0 = safe, 1.0 = high risk/high reward

    @property
    def all_rushers(self) -> Set[str]:
        """Get all positions that are rushing in this package."""
        return self.base_rushers | self.additional_rushers

    def is_db_blitz(self) -> bool:
        """Check if this package includes a blitzing DB."""
        db_positions = {"CB", "FS", "SS", "NCB", "CORNERBACK", "SAFETY"}
        return bool(self.additional_rushers & db_positions)


@dataclass
class RusherAssignments:
    """
    Tracks which players are rushing vs covering for a specific play.

    This is the key data structure that enables dynamic sack attribution.
    Only players in rushing_positions should be eligible for sacks.

    Attributes:
        blitz_package: The blitz package being run
        rushing_positions: Set of position strings that are pass rushing
        coverage_positions: Set of position strings in coverage
    """
    blitz_package: BlitzPackageType
    rushing_positions: Set[str] = field(default_factory=set)
    coverage_positions: Set[str] = field(default_factory=set)

    def is_position_rushing(self, position: str) -> bool:
        """
        Check if a position is rushing the passer.

        Normalizes position string for comparison (case-insensitive).
        Handles both enum-style (Position.DE) and string positions.

        Args:
            position: Position string to check (e.g., "DE", "defensive_end", "MLB")

        Returns:
            True if this position is rushing the passer
        """
        if position is None:
            return False

        # Normalize the position string
        pos_normalized = self._normalize_position(position)

        # Check if any rushing position matches
        for rushing_pos in self.rushing_positions:
            if self._normalize_position(rushing_pos) == pos_normalized:
                return True
        return False

    def _normalize_position(self, position: str) -> str:
        """
        Normalize position string for comparison.

        Handles various formats:
        - Enum values: Position.DE -> "DE"
        - Full names: "defensive_end" -> "DE"
        - Mixed case: "de", "De" -> "DE"
        """
        if position is None:
            return ""

        # Convert to string if it's an enum
        pos_str = str(position)

        # Handle enum format "Position.DE"
        if "." in pos_str:
            pos_str = pos_str.split(".")[-1]

        pos_upper = pos_str.upper()

        # Map full names to abbreviations
        position_map = {
            "DEFENSIVE_END": "DE",
            "DEFENSIVE_TACKLE": "DT",
            "NOSE_TACKLE": "NT",
            "OUTSIDE_LINEBACKER": "OLB",
            "INSIDE_LINEBACKER": "ILB",
            "MIDDLE_LINEBACKER": "MLB",
            "MIKE_LINEBACKER": "MIKE",
            "SAM_LINEBACKER": "SAM",
            "WILL_LINEBACKER": "WILL",
            "CORNERBACK": "CB",
            "FREE_SAFETY": "FS",
            "STRONG_SAFETY": "SS",
            "SAFETY": "SAFETY",  # Generic safety (covers both FS/SS when player data doesn't specify)
            "NICKEL_CORNERBACK": "NCB",
            "EDGE": "DE",  # EDGE maps to DE for comparison
            "LEO": "DE",   # LEO maps to DE
            # LB variations
            "LINEBACKER": "LB",
            "LB": "LB",
        }

        return position_map.get(pos_upper, pos_upper)


# Standard defensive positions for reference
ALL_DEFENSIVE_POSITIONS = {
    "DE", "DT", "NT",  # D-Line
    "OLB", "ILB", "MLB", "MIKE", "SAM", "WILL",  # Linebackers
    "CB", "FS", "SS", "NCB"  # Defensive backs
}

# D-Line positions (always rush in base defense)
DLINE_POSITIONS = {"DE", "DT", "NT"}

# Linebacker positions
LB_POSITIONS = {"OLB", "ILB", "MLB", "MIKE", "SAM", "WILL"}

# Defensive back positions
DB_POSITIONS = {"CB", "FS", "SS", "NCB"}


# ============================================================================
# BLITZ PACKAGE DEFINITIONS
# ============================================================================
# These define the exact rusher configuration for each package type.
# Modifiers are based on NFL averages:
# - More rushers = higher sack rate but weaker coverage
# - DB blitzes are high risk/high reward

BLITZ_PACKAGE_DEFINITIONS = {
    # ----- BASE RUSHES -----
    # Four-man rush has lower sack rate than blitzes - extra rushers come unblocked
    # NFL Reality: 4-man rush sack rate ~3-4%, blitz sack rate ~7-12%
    BlitzPackageType.FOUR_MAN_BASE: BlitzPackageDefinition(
        package_type=BlitzPackageType.FOUR_MAN_BASE,
        base_rushers={"DE", "DT"},
        additional_rushers=set(),
        num_rushers=4,
        coverage_type="zone",
        sack_rate_modifier=0.15,  # Was 0.25 - further reduced for NFL sack distribution
        pressure_rate_modifier=0.25,
        risk_factor=0.0
    ),

    BlitzPackageType.THREE_MAN_RUSH: BlitzPackageDefinition(
        package_type=BlitzPackageType.THREE_MAN_RUSH,
        base_rushers={"DE"},  # Only DEs rush, DT drops
        additional_rushers=set(),
        num_rushers=3,
        coverage_type="prevent",
        sack_rate_modifier=0.5,  # Very low sack rate
        pressure_rate_modifier=0.6,
        risk_factor=0.0  # Very safe
    ),

    # ----- 5-MAN BLITZES (1 extra rusher) -----
    # Modifiers increased significantly to shift sack distribution toward LBs/DBs
    # NFL Reality: Blitzes should produce 2-3x more sacks per play due to unblocked rushers
    BlitzPackageType.MIKE_BLITZ: BlitzPackageDefinition(
        package_type=BlitzPackageType.MIKE_BLITZ,
        base_rushers={"DE", "DT"},
        additional_rushers={"MLB", "MIKE", "ILB", "LB"},  # Added ILB, LB to cover all ILB position strings
        num_rushers=5,
        coverage_type="man",
        sack_rate_modifier=2.5,   # Was 1.3 - significantly increased
        pressure_rate_modifier=2.0,
        risk_factor=0.3
    ),

    BlitzPackageType.SAM_BLITZ: BlitzPackageDefinition(
        package_type=BlitzPackageType.SAM_BLITZ,
        base_rushers={"DE", "DT"},
        additional_rushers={"SAM", "OLB", "LB"},  # Added OLB, LB to cover generic linebackers
        num_rushers=5,
        coverage_type="man",
        sack_rate_modifier=2.4,   # Was 1.25
        pressure_rate_modifier=1.9,
        risk_factor=0.25
    ),

    BlitzPackageType.WILL_BLITZ: BlitzPackageDefinition(
        package_type=BlitzPackageType.WILL_BLITZ,
        base_rushers={"DE", "DT"},
        additional_rushers={"WILL", "OLB", "LB"},  # Added OLB, LB to cover generic linebackers
        num_rushers=5,
        coverage_type="man",
        sack_rate_modifier=2.4,   # Was 1.25
        pressure_rate_modifier=1.9,
        risk_factor=0.25
    ),

    BlitzPackageType.OLB_BLITZ: BlitzPackageDefinition(
        package_type=BlitzPackageType.OLB_BLITZ,
        base_rushers={"DE", "DT"},
        additional_rushers={"OLB", "LB"},  # Added LB to cover generic linebackers
        num_rushers=5,
        coverage_type="man",
        sack_rate_modifier=2.5,   # Was 1.3
        pressure_rate_modifier=2.0,
        risk_factor=0.25
    ),

    BlitzPackageType.A_GAP_BLITZ: BlitzPackageDefinition(
        package_type=BlitzPackageType.A_GAP_BLITZ,
        base_rushers={"DE", "DT"},
        additional_rushers={"MLB", "MIKE", "ILB", "LB"},  # Added LB to cover generic linebackers
        num_rushers=5,
        coverage_type="man",
        sack_rate_modifier=2.7,   # Was 1.35 - A-gap is quick to QB
        pressure_rate_modifier=2.2,
        risk_factor=0.35
    ),

    # ----- 6-MAN BLITZES (2 extra rushers) -----
    # 6-man blitzes bring even more pressure - very high sack rates
    BlitzPackageType.DOUBLE_A_GAP: BlitzPackageDefinition(
        package_type=BlitzPackageType.DOUBLE_A_GAP,
        base_rushers={"DE", "DT"},
        additional_rushers={"MLB", "MIKE", "ILB", "LB"},  # Both ILBs + generic LB
        num_rushers=6,
        coverage_type="man",
        sack_rate_modifier=3.0,   # Was 1.5 - 6-man rushes have very high sack rates
        pressure_rate_modifier=2.5,
        risk_factor=0.5
    ),

    BlitzPackageType.DOUBLE_LB: BlitzPackageDefinition(
        package_type=BlitzPackageType.DOUBLE_LB,
        base_rushers={"DE", "DT"},
        additional_rushers={"OLB", "MLB", "MIKE", "SAM", "WILL", "ILB", "LB"},  # All LB variants
        num_rushers=6,
        coverage_type="man",
        sack_rate_modifier=2.9,   # Was 1.45
        pressure_rate_modifier=2.4,
        risk_factor=0.45
    ),

    BlitzPackageType.LB_DB_COMBO: BlitzPackageDefinition(
        package_type=BlitzPackageType.LB_DB_COMBO,
        base_rushers={"DE", "DT"},
        additional_rushers={"OLB", "MLB", "LB", "SS", "FS", "SAFETY"},  # Added LB
        num_rushers=6,
        coverage_type="man",
        sack_rate_modifier=3.0,   # Was 1.5
        pressure_rate_modifier=2.5,
        risk_factor=0.55
    ),

    # ----- DB BLITZES -----
    # DB blitzes are exotic and usually come free - high sack rates
    BlitzPackageType.CORNER_BLITZ: BlitzPackageDefinition(
        package_type=BlitzPackageType.CORNER_BLITZ,
        base_rushers={"DE", "DT"},
        additional_rushers={"CB"},
        num_rushers=5,
        coverage_type="man",
        sack_rate_modifier=2.8,   # Was 1.4 - Corner comes unblocked
        pressure_rate_modifier=2.2,
        risk_factor=0.6  # High risk - leaves receiver open
    ),

    BlitzPackageType.SAFETY_BLITZ: BlitzPackageDefinition(
        package_type=BlitzPackageType.SAFETY_BLITZ,
        base_rushers={"DE", "DT"},
        additional_rushers={"SS", "FS", "SAFETY"},  # SAFETY covers generic "safety" position
        num_rushers=5,
        coverage_type="man",
        sack_rate_modifier=2.7,   # Was 1.35
        pressure_rate_modifier=2.2,
        risk_factor=0.5  # Less risky than corner blitz
    ),

    BlitzPackageType.NICKEL_BLITZ: BlitzPackageDefinition(
        package_type=BlitzPackageType.NICKEL_BLITZ,
        base_rushers={"DE", "DT"},
        additional_rushers={"NCB", "CB"},  # Nickel/slot CB
        num_rushers=5,
        coverage_type="man",
        sack_rate_modifier=2.7,   # Was 1.35
        pressure_rate_modifier=2.2,
        risk_factor=0.55
    ),

    BlitzPackageType.DOUBLE_SAFETY: BlitzPackageDefinition(
        package_type=BlitzPackageType.DOUBLE_SAFETY,
        base_rushers={"DE", "DT"},
        additional_rushers={"SS", "FS", "SAFETY"},
        num_rushers=6,
        coverage_type="man",
        sack_rate_modifier=3.2,   # Was 1.55 - double safety is very aggressive
        pressure_rate_modifier=2.6,
        risk_factor=0.7  # Very risky - no deep help
    ),

    # ----- EXOTIC PACKAGES -----
    # Zone blitzes bring creative pressure while maintaining zone coverage
    BlitzPackageType.ZONE_DOG: BlitzPackageDefinition(
        package_type=BlitzPackageType.ZONE_DOG,
        base_rushers={"DE", "DT"},
        additional_rushers={"OLB", "MLB", "MIKE", "LB"},  # Added LB for generic linebackers
        num_rushers=5,
        coverage_type="zone",  # Zone behind the blitz
        sack_rate_modifier=2.5,   # Was 1.3
        pressure_rate_modifier=2.0,
        risk_factor=0.35
    ),

    BlitzPackageType.FIRE_ZONE: BlitzPackageDefinition(
        package_type=BlitzPackageType.FIRE_ZONE,
        base_rushers={"DE", "DT"},
        additional_rushers={"OLB", "MLB", "LB"},  # Added LB for generic linebackers
        num_rushers=5,
        coverage_type="zone_3_deep",  # 3-deep zone coverage
        sack_rate_modifier=2.5,   # Was 1.3
        pressure_rate_modifier=2.0,
        risk_factor=0.3
    ),

    BlitzPackageType.COVER_0_BLITZ: BlitzPackageDefinition(
        package_type=BlitzPackageType.COVER_0_BLITZ,
        base_rushers={"DE", "DT"},
        additional_rushers={"OLB", "MLB", "LB", "SS", "SAFETY"},  # Added LB, 6-man rush
        num_rushers=6,
        coverage_type="man_no_help",  # Pure man, no safety help
        sack_rate_modifier=3.5,   # Was 1.6 - all-out blitz has highest sack rate
        pressure_rate_modifier=3.0,
        risk_factor=0.8  # Highest risk
    ),

    BlitzPackageType.OVERLOAD_BLITZ: BlitzPackageDefinition(
        package_type=BlitzPackageType.OVERLOAD_BLITZ,
        base_rushers={"DE", "DT"},
        additional_rushers={"OLB", "LB", "SS", "SAFETY"},  # Added LB, overload one side
        num_rushers=6,
        coverage_type="man",
        sack_rate_modifier=3.0,   # Was 1.5
        pressure_rate_modifier=2.5,
        risk_factor=0.6
    ),
}


def get_blitz_package_definition(package_type: BlitzPackageType) -> Optional[BlitzPackageDefinition]:
    """
    Get the definition for a blitz package type.

    Args:
        package_type: The blitz package enum value

    Returns:
        BlitzPackageDefinition or None if not found
    """
    return BLITZ_PACKAGE_DEFINITIONS.get(package_type)


def build_rusher_assignments(
    package_type: BlitzPackageType,
    formation: Optional[str] = None
) -> RusherAssignments:
    """
    Build rusher assignments from a blitz package type.

    Args:
        package_type: The blitz package to build assignments for
        formation: Optional defensive formation for adjustments

    Returns:
        RusherAssignments with rushing and coverage positions
    """
    pkg_def = get_blitz_package_definition(package_type)

    if not pkg_def:
        # Fallback to 4-man base
        pkg_def = BLITZ_PACKAGE_DEFINITIONS[BlitzPackageType.FOUR_MAN_BASE]

    rushing_positions = pkg_def.all_rushers

    # All other positions are in coverage
    coverage_positions = ALL_DEFENSIVE_POSITIONS - rushing_positions

    return RusherAssignments(
        blitz_package=package_type,
        rushing_positions=rushing_positions,
        coverage_positions=coverage_positions
    )
