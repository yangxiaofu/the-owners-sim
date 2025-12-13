"""Player persona types and dataclass for decision-making in FA/contracts."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Any


class PersonaType(Enum):
    """Player persona archetypes influencing FA/contract decisions."""

    RING_CHASER = "ring_chaser"  # Prioritizes contenders, takes less to win
    HOMETOWN_HERO = "hometown_hero"  # Prefers birthplace/college area, loyal to drafting team
    MONEY_FIRST = "money_first"  # Always follows highest offer
    BIG_MARKET = "big_market"  # Wants LA, NYC, Dallas - media exposure
    SMALL_MARKET = "small_market"  # Prefers quieter markets, less pressure
    LEGACY_BUILDER = "legacy_builder"  # Wants to stay with one team, be franchise icon
    COMPETITOR = "competitor"  # Wants playing time, avoids bench roles
    SYSTEM_FIT = "system_fit"  # Prioritizes schemes matching skills


@dataclass
class PlayerPersona:
    """Player personality influencing free agency and contract decisions.

    Follows the pattern established by GMArchetype in src/team_management/gm_archetype.py.
    All importance weights are on a 0-100 scale.
    """

    # Required fields
    player_id: int
    persona_type: PersonaType

    # Preference weights (0-100 scale)
    money_importance: int = 50
    winning_importance: int = 50
    location_importance: int = 50
    playing_time_importance: int = 50
    loyalty_importance: int = 50
    market_size_importance: int = 50
    coaching_fit_importance: int = 50
    relationships_importance: int = 50

    # Biographical data (for Hometown Hero)
    birthplace_state: Optional[str] = None
    college_state: Optional[str] = None
    drafting_team_id: Optional[int] = None

    # Career context (dynamically updated)
    career_earnings: int = 0
    championship_count: int = 0
    pro_bowl_count: int = 0

    def __post_init__(self):
        """Validate all fields after initialization."""
        # Normalize drafting_team_id: treat 0 as None (undrafted free agent)
        if self.drafting_team_id == 0:
            self.drafting_team_id = None

        self._validate()

    def _validate(self):
        """Ensure all values are within acceptable ranges."""
        # Validate importance weights (0-100)
        importance_fields = [
            "money_importance",
            "winning_importance",
            "location_importance",
            "playing_time_importance",
            "loyalty_importance",
            "market_size_importance",
            "coaching_fit_importance",
            "relationships_importance",
        ]
        for field_name in importance_fields:
            value = getattr(self, field_name)
            if not 0 <= value <= 100:
                raise ValueError(
                    f"{field_name} must be between 0 and 100, got {value}"
                )

        # Validate persona_type is enum
        if not isinstance(self.persona_type, PersonaType):
            raise TypeError(
                f"persona_type must be PersonaType enum, got {type(self.persona_type)}"
            )

        # Validate team_id if present (1-32, None/0 means undrafted)
        if self.drafting_team_id is not None:
            if not 1 <= self.drafting_team_id <= 32:
                raise ValueError(
                    f"drafting_team_id must be 1-32 or None for undrafted, got {self.drafting_team_id}"
                )

        # Validate non-negative career stats
        if self.career_earnings < 0:
            raise ValueError("career_earnings cannot be negative")
        if self.championship_count < 0:
            raise ValueError("championship_count cannot be negative")
        if self.pro_bowl_count < 0:
            raise ValueError("pro_bowl_count cannot be negative")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "player_id": self.player_id,
            "persona_type": self.persona_type.value,
            "money_importance": self.money_importance,
            "winning_importance": self.winning_importance,
            "location_importance": self.location_importance,
            "playing_time_importance": self.playing_time_importance,
            "loyalty_importance": self.loyalty_importance,
            "market_size_importance": self.market_size_importance,
            "coaching_fit_importance": self.coaching_fit_importance,
            "relationships_importance": self.relationships_importance,
            "birthplace_state": self.birthplace_state,
            "college_state": self.college_state,
            "drafting_team_id": self.drafting_team_id,
            "career_earnings": self.career_earnings,
            "championship_count": self.championship_count,
            "pro_bowl_count": self.pro_bowl_count,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PlayerPersona":
        """Create PlayerPersona from dictionary."""
        persona_type = data.get("persona_type")
        if isinstance(persona_type, str):
            persona_type = PersonaType(persona_type)

        return cls(
            player_id=data["player_id"],
            persona_type=persona_type,
            money_importance=data.get("money_importance", 50),
            winning_importance=data.get("winning_importance", 50),
            location_importance=data.get("location_importance", 50),
            playing_time_importance=data.get("playing_time_importance", 50),
            loyalty_importance=data.get("loyalty_importance", 50),
            market_size_importance=data.get("market_size_importance", 50),
            coaching_fit_importance=data.get("coaching_fit_importance", 50),
            relationships_importance=data.get("relationships_importance", 50),
            birthplace_state=data.get("birthplace_state"),
            college_state=data.get("college_state"),
            drafting_team_id=data.get("drafting_team_id"),
            career_earnings=data.get("career_earnings", 0),
            championship_count=data.get("championship_count", 0),
            pro_bowl_count=data.get("pro_bowl_count", 0),
        )

    @classmethod
    def from_db_row(cls, row: Dict[str, Any]) -> "PlayerPersona":
        """Create PlayerPersona from database row (sqlite3.Row or dict)."""
        # Handle sqlite3.Row by converting to dict if needed
        if hasattr(row, "keys"):
            row = dict(row)
        return cls.from_dict(row)

    def to_db_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database insertion."""
        return self.to_dict()

    @property
    def primary_preference(self) -> str:
        """Return the player's highest-weighted preference."""
        preferences = {
            "money": self.money_importance,
            "winning": self.winning_importance,
            "location": self.location_importance,
            "playing_time": self.playing_time_importance,
            "loyalty": self.loyalty_importance,
            "market_size": self.market_size_importance,
            "coaching_fit": self.coaching_fit_importance,
            "relationships": self.relationships_importance,
        }
        return max(preferences, key=preferences.get)