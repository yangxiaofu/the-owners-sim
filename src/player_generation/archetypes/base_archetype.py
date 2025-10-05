"""Base archetype definition for player generation."""

from dataclasses import dataclass
from typing import Dict, List, Optional
from enum import Enum


class Position(Enum):
    """NFL positions."""
    QB = "QB"
    RB = "RB"
    FB = "FB"
    WR = "WR"
    TE = "TE"
    OT = "OT"
    OG = "OG"
    C = "C"
    DT = "DT"
    DE = "DE"
    EDGE = "EDGE"
    LB = "LB"
    MLB = "MLB"
    OLB = "OLB"
    CB = "CB"
    S = "S"
    SS = "SS"
    FS = "FS"
    K = "K"
    P = "P"
    LS = "LS"
    # Generic positions
    OL = "OL"
    DL = "DL"


@dataclass
class AttributeRange:
    """Range for attribute generation."""
    min: int
    max: int
    mean: int
    std_dev: int

    def validate(self) -> bool:
        """Ensure range is valid.

        Returns:
            True if range is valid, False otherwise
        """
        return (40 <= self.min <= self.max <= 99 and
                self.min <= self.mean <= self.max)


@dataclass
class PlayerArchetype:
    """Base archetype definition for player generation."""

    # Identity
    archetype_id: str
    position: Position
    name: str
    description: str

    # Attribute ranges
    physical_attributes: Dict[str, AttributeRange]
    mental_attributes: Dict[str, AttributeRange]
    position_attributes: Dict[str, AttributeRange]

    # Constraints
    overall_range: AttributeRange
    frequency: float  # 0.0-1.0 (how common this archetype is)

    # Development
    peak_age_range: tuple[int, int]  # (min, max) peak age
    development_curve: str  # "early", "normal", "late"

    def validate(self) -> tuple[bool, Optional[str]]:
        """Validate archetype configuration.

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check all ranges
        for attr_dict in [self.physical_attributes, self.mental_attributes,
                          self.position_attributes]:
            for name, range_obj in attr_dict.items():
                if not range_obj.validate():
                    return False, f"Invalid range for {name}"

        # Check overall range
        if not self.overall_range.validate():
            return False, "Invalid overall range"

        # Check frequency
        if not 0 <= self.frequency <= 1:
            return False, f"Invalid frequency: {self.frequency}"

        # Check peak age
        if not 20 <= self.peak_age_range[0] <= self.peak_age_range[1] <= 35:
            return False, f"Invalid peak age range: {self.peak_age_range}"

        # Check development curve
        if self.development_curve not in ["early", "normal", "late"]:
            return False, f"Invalid development curve: {self.development_curve}"

        return True, None

    def get_attribute_names(self) -> List[str]:
        """Get all attribute names for this archetype.

        Returns:
            List of all attribute names
        """
        all_attrs = []
        all_attrs.extend(self.physical_attributes.keys())
        all_attrs.extend(self.mental_attributes.keys())
        all_attrs.extend(self.position_attributes.keys())
        return all_attrs