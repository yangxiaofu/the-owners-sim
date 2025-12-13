"""
Staff Member - GM and Head Coach representations.

Combines archetype traits with procedurally generated identity.
Used for hire/fire functionality in Owner Review stage.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from enum import Enum
import uuid


class StaffType(Enum):
    """Type of staff member."""
    GM = "GM"
    HEAD_COACH = "HC"


@dataclass
class StaffMember:
    """
    Represents a GM or Head Coach with identity and traits.

    Combines:
    - Procedurally generated identity (name, history)
    - Base archetype (from JSON config)
    - Custom trait variations (random noise around archetype baseline)

    Attributes:
        staff_id: UUID identifier for this staff member
        staff_type: Whether this is a GM or HC
        name: Full name (e.g., "John Smith")
        archetype_key: Key into config JSON (e.g., "balanced", "win_now")
        custom_traits: Dict of trait variations (+/- from archetype baseline)
        history: Generated background story (1-2 sentences)
        hire_season: Season this staff member was hired
    """

    staff_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    staff_type: StaffType = StaffType.GM
    name: str = ""
    archetype_key: str = "balanced"
    custom_traits: Dict[str, float] = field(default_factory=dict)
    history: str = ""
    hire_season: int = 2025

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage."""
        return {
            "staff_id": self.staff_id,
            "staff_type": self.staff_type.value,
            "name": self.name,
            "archetype_key": self.archetype_key,
            "custom_traits": self.custom_traits.copy(),
            "history": self.history,
            "hire_season": self.hire_season,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StaffMember":
        """Create from dictionary."""
        staff_type_str = data.get("staff_type", "GM")
        if isinstance(staff_type_str, StaffType):
            staff_type = staff_type_str
        else:
            staff_type = StaffType(staff_type_str)

        return cls(
            staff_id=data.get("staff_id", str(uuid.uuid4())),
            staff_type=staff_type,
            name=data.get("name", ""),
            archetype_key=data.get("archetype_key", "balanced"),
            custom_traits=data.get("custom_traits", {}),
            history=data.get("history", ""),
            hire_season=data.get("hire_season", 2025),
        )

    def get_effective_trait(self, trait_name: str, base_value: float) -> float:
        """
        Get trait value with custom override applied.

        Custom traits store deltas, so we add them to the base value.

        Args:
            trait_name: Name of the trait
            base_value: Archetype baseline value for this trait

        Returns:
            Effective trait value (clamped to 0.0-1.0)
        """
        if trait_name in self.custom_traits:
            # Custom traits store the final value, not delta
            return self.custom_traits[trait_name]
        return base_value

    def get_tenure(self, current_season: int) -> int:
        """
        Get number of seasons this staff member has been with the team.

        Args:
            current_season: Current season year

        Returns:
            Number of seasons (minimum 1)
        """
        return max(1, current_season - self.hire_season + 1)

    def get_archetype_display_name(self) -> str:
        """
        Get human-readable archetype name.

        Returns:
            Formatted archetype name (e.g., "Win Now" instead of "win_now")
        """
        return self.archetype_key.replace("_", " ").title()

    def __str__(self) -> str:
        """String representation for debugging."""
        return (
            f"{self.staff_type.value} {self.name} "
            f"({self.get_archetype_display_name()}, hired {self.hire_season})"
        )


@dataclass
class StaffCandidate(StaffMember):
    """
    A candidate for hire (extends StaffMember with selection state).

    Used during the hire process when owner fires GM/HC and must
    select from generated candidates.

    Attributes:
        is_selected: True if user has selected this candidate
        candidate_rank: Display ordering (1-5)
    """

    is_selected: bool = False
    candidate_rank: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary including candidate fields."""
        data = super().to_dict()
        data["is_selected"] = self.is_selected
        data["candidate_rank"] = self.candidate_rank
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StaffCandidate":
        """Create from dictionary."""
        staff_type_str = data.get("staff_type", "GM")
        if isinstance(staff_type_str, StaffType):
            staff_type = staff_type_str
        else:
            staff_type = StaffType(staff_type_str)

        return cls(
            staff_id=data.get("staff_id", str(uuid.uuid4())),
            staff_type=staff_type,
            name=data.get("name", ""),
            archetype_key=data.get("archetype_key", "balanced"),
            custom_traits=data.get("custom_traits", {}),
            history=data.get("history", ""),
            hire_season=data.get("hire_season", 2025),
            is_selected=data.get("is_selected", False),
            candidate_rank=data.get("candidate_rank", 0),
        )


def create_default_gm(dynasty_id: str, season: int) -> StaffMember:
    """
    Create default GM for new dynasties.

    Args:
        dynasty_id: Dynasty identifier (unused but for consistency)
        season: Current season

    Returns:
        Default balanced GM
    """
    return StaffMember(
        staff_id=str(uuid.uuid4()),
        staff_type=StaffType.GM,
        name="Default GM",
        archetype_key="balanced",
        custom_traits={},
        history="Experienced front office executive with a balanced approach to roster building.",
        hire_season=season,
    )


def create_default_hc(dynasty_id: str, season: int) -> StaffMember:
    """
    Create default Head Coach for new dynasties.

    Args:
        dynasty_id: Dynasty identifier (unused but for consistency)
        season: Current season

    Returns:
        Default balanced HC
    """
    return StaffMember(
        staff_id=str(uuid.uuid4()),
        staff_type=StaffType.HEAD_COACH,
        name="Default HC",
        archetype_key="balanced",
        custom_traits={},
        history="Veteran coaching background with experience at multiple NFL stops.",
        hire_season=season,
    )
