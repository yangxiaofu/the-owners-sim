"""
GM Proposal - General Manager's free agent signing proposal for owner approval.

Part of Milestone 10: GM-Driven Free Agency with Owner Oversight.

Design:
- Ephemeral session data (created during wave execution)
- Contains all info needed for owner to make approval decision
- Includes GM's reasoning and archetype rationale
"""

from dataclasses import dataclass, field
from typing import Dict, Any
import uuid


@dataclass
class GMProposal:
    """
    GM's free agent signing proposal for owner approval.

    Generated during FA wave execution, presented to owner in real-time notification.
    Ephemeral (not persisted until owner approves/rejects).
    """

    # Unique identifier
    proposal_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    """Unique ID for tracking this proposal."""

    # Player information
    player_id: int = 0
    """Database ID of the player."""

    player_name: str = ""
    """Full name of the player."""

    position: str = ""
    """Player's position (e.g., WR, CB, OT)."""

    age: int = 0
    """Player's current age."""

    overall_rating: int = 0
    """Player's overall rating (0-100)."""

    tier: str = "Unknown"
    """Free agency tier (Elite, Quality, Depth)."""

    # Proposed contract terms
    aav: int = 0
    """Average annual value ($ per year)."""

    years: int = 1
    """Contract length in years."""

    guaranteed: int = 0
    """Total guaranteed money ($)."""

    signing_bonus: int = 0
    """Upfront signing bonus ($)."""

    # GM reasoning
    pitch: str = ""
    """
    GM's pitch to owner explaining why this signing makes sense.

    Example: "Elite WR1 to pair with our young QB. Fills critical need and gives us
    a top-tier receiving threat for our championship window."
    """

    archetype_rationale: str = ""
    """
    Explanation of how this proposal aligns with GM's archetype.

    Example: "My aggressive approach focuses on star talent. This player is worth
    the premium AAV given their elite production and scheme fit."
    """

    need_addressed: str = ""
    """
    Description of roster need this signing fills.

    Example: "WR1 starter (depth: 0, critical need)"
    """

    # Context for decision-making
    cap_impact: int = 0
    """Year 1 cap hit (AAV + signing bonus)."""

    remaining_cap_after: int = 0
    """Projected cap space remaining after this signing."""

    # Scoring breakdown (for transparency/debugging)
    score_breakdown: Dict[str, float] = field(default_factory=dict)
    """
    Breakdown of how GM scored this player.

    Example:
        {
            "base": 88.0,
            "archetype_fit": +12.0,
            "priority_bonus": +15.0,
            "age_fit": +5.0,
            "total": 120.0
        }
    """

    def __post_init__(self):
        """Validate proposal values."""
        self._validate_player_info()
        self._validate_contract_terms()
        self._validate_cap_values()

    def _validate_player_info(self):
        """Ensure player information is valid."""
        if self.player_id <= 0:
            raise ValueError(f"player_id must be positive, got {self.player_id}")

        if not self.player_name:
            raise ValueError("player_name cannot be empty")

        if not self.position:
            raise ValueError("position cannot be empty")

        if self.age < 21 or self.age > 45:
            raise ValueError(f"age must be 21-45, got {self.age}")

        if self.overall_rating < 0 or self.overall_rating > 100:
            raise ValueError(
                f"overall_rating must be 0-100, got {self.overall_rating}"
            )

    def _validate_contract_terms(self):
        """Ensure contract terms are valid."""
        if self.aav < 0:
            raise ValueError(f"aav must be non-negative, got {self.aav}")

        if self.years < 1 or self.years > 5:
            raise ValueError(f"years must be 1-5, got {self.years}")

        if self.guaranteed < 0:
            raise ValueError(f"guaranteed must be non-negative, got {self.guaranteed}")

        if self.signing_bonus < 0:
            raise ValueError(
                f"signing_bonus must be non-negative, got {self.signing_bonus}"
            )

        # Guaranteed can't exceed total contract value
        total_value = self.aav * self.years
        if self.guaranteed > total_value:
            raise ValueError(
                f"guaranteed ({self.guaranteed}) cannot exceed total value ({total_value})"
            )

    def _validate_cap_values(self):
        """Ensure cap impact values are valid."""
        if self.cap_impact < 0:
            raise ValueError(f"cap_impact must be non-negative, got {self.cap_impact}")

        if self.remaining_cap_after < 0:
            raise ValueError(
                f"remaining_cap_after must be non-negative, got {self.remaining_cap_after}"
            )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/serialization."""
        return {
            "proposal_id": self.proposal_id,
            "player_id": self.player_id,
            "player_name": self.player_name,
            "position": self.position,
            "age": self.age,
            "overall_rating": self.overall_rating,
            "tier": self.tier,
            "aav": self.aav,
            "years": self.years,
            "guaranteed": self.guaranteed,
            "signing_bonus": self.signing_bonus,
            "pitch": self.pitch,
            "archetype_rationale": self.archetype_rationale,
            "need_addressed": self.need_addressed,
            "cap_impact": self.cap_impact,
            "remaining_cap_after": self.remaining_cap_after,
            "score_breakdown": self.score_breakdown.copy(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GMProposal":
        """Create GMProposal from dictionary."""
        return cls(**data)

    def get_total_value(self) -> int:
        """Calculate total contract value."""
        return self.aav * self.years

    def get_guaranteed_percent(self) -> float:
        """Calculate % of contract that is guaranteed."""
        total_value = self.get_total_value()
        if total_value == 0:
            return 0.0
        return self.guaranteed / total_value

    def get_contract_summary(self) -> str:
        """
        Get human-readable contract summary.

        Example: "4 years, $60M ($15M AAV, $42M gtd, $12.6M bonus)"
        """
        return (
            f"{self.years} year{'s' if self.years > 1 else ''}, "
            f"${self.get_total_value():,} "
            f"(${self.aav:,} AAV, ${self.guaranteed:,} gtd, ${self.signing_bonus:,} bonus)"
        )

    def get_cap_impact_summary(self) -> str:
        """
        Get human-readable cap impact summary.

        Example: "Year 1 cap hit: $27.6M, Remaining cap: $17.4M"
        """
        return (
            f"Year 1 cap hit: ${self.cap_impact:,}, "
            f"Remaining cap: ${self.remaining_cap_after:,}"
        )

    def is_high_value_signing(self) -> bool:
        """
        Check if this is a high-value signing (AAV > $15M).

        Used to determine if owner should get extra warnings/confirmations.
        """
        return self.aav > 15_000_000

    def is_long_term_commitment(self) -> bool:
        """
        Check if this is a long-term commitment (4+ years).

        Used to determine if owner should get extra warnings/confirmations.
        """
        return self.years >= 4
