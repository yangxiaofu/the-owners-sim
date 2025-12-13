"""
FA Guidance - Owner's strategic direction for free agency.

Part of Milestone 10: GM-Driven Free Agency with Owner Oversight.

Design:
- Ephemeral context (passed UI → Handler → Service)
- Not persisted to database (cleared after FA completion)
- Similar pattern to DraftDirection from Milestone 09
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List


class FAPhilosophy(Enum):
    """Owner's free agency philosophy/approach."""

    AGGRESSIVE = "aggressive"  # Chase stars, spend freely, high guarantees
    BALANCED = "balanced"      # Best value, mix of tiers, controlled spending
    CONSERVATIVE = "conservative"  # Low-risk depth, short contracts, cap discipline


@dataclass
class FAGuidance:
    """
    Owner's strategic guidance for free agency.

    Ephemeral context - passed UI → Handler → Service.
    Not persisted to database (cleared after FA completion).

    Similar to DraftDirection, this provides GM with owner's strategic intent
    without micromanaging individual player decisions.
    """

    philosophy: FAPhilosophy = FAPhilosophy.BALANCED
    """
    Overall free agency approach.

    - AGGRESSIVE: GM should pursue elite players, offer top market AAV
    - BALANCED: GM should find best value across tiers
    - CONSERVATIVE: GM should focus on depth, avoid expensive risks
    """

    budget_by_position_group: Dict[str, int] = field(default_factory=dict)
    """
    Maximum spending allocation by position group ($ amount).

    Example:
        {
            "QB": 40_000_000,
            "OL": 30_000_000,
            "DL": 25_000_000,
            "Secondary": 20_000_000,
            "Skill": 15_000_000,
            "Special Teams": 5_000_000
        }

    If empty, GM has full discretion within total cap space.
    """

    priority_positions: List[str] = field(default_factory=list)
    """
    1-3 positions to prioritize in free agency.

    GM proposal engine gives +15 bonus to players at these positions.

    Example: ["WR", "CB", "OT"]
    """

    max_contract_years: int = 5
    """
    Maximum contract length owner is comfortable with.

    Range: 1-5 years
    Default: 5 (GM has full flexibility)
    """

    max_guaranteed_percent: float = 0.75
    """
    Maximum % of total contract value that can be guaranteed.

    Range: 0.0-1.0 (0% to 100%)
    Default: 0.75 (75% max guaranteed)

    Example:
        - 0.50 = Conservative (max 50% guaranteed)
        - 0.75 = Balanced (max 75% guaranteed)
        - 1.00 = Aggressive (fully guaranteed contracts allowed)
    """

    def __post_init__(self):
        """Validate guidance values."""
        self._validate_philosophy()
        self._validate_budgets()
        self._validate_priorities()
        self._validate_contract_params()

    def _validate_philosophy(self):
        """Ensure philosophy is valid FAPhilosophy enum."""
        if not isinstance(self.philosophy, FAPhilosophy):
            raise ValueError(
                f"philosophy must be FAPhilosophy enum, got {type(self.philosophy)}"
            )

    def _validate_budgets(self):
        """Ensure budget values are non-negative."""
        for position_group, budget in self.budget_by_position_group.items():
            if budget < 0:
                raise ValueError(
                    f"Budget for {position_group} must be non-negative, got {budget}"
                )

    def _validate_priorities(self):
        """Ensure priority positions list is 0-3 items."""
        if len(self.priority_positions) > 3:
            raise ValueError(
                f"priority_positions must have max 3 items, got {len(self.priority_positions)}"
            )

    def _validate_contract_params(self):
        """Ensure contract parameters are within valid ranges."""
        if not 1 <= self.max_contract_years <= 5:
            raise ValueError(
                f"max_contract_years must be 1-5, got {self.max_contract_years}"
            )

        if not 0.0 <= self.max_guaranteed_percent <= 1.0:
            raise ValueError(
                f"max_guaranteed_percent must be 0.0-1.0, got {self.max_guaranteed_percent}"
            )

    def to_dict(self) -> Dict:
        """Convert to dictionary for logging/debugging."""
        return {
            "philosophy": self.philosophy.value,
            "budget_by_position_group": self.budget_by_position_group.copy(),
            "priority_positions": self.priority_positions.copy(),
            "max_contract_years": self.max_contract_years,
            "max_guaranteed_percent": self.max_guaranteed_percent,
        }

    @classmethod
    def create_default(cls) -> "FAGuidance":
        """
        Create default guidance (balanced approach, no constraints).

        Used when owner skips guidance dialog or for testing.
        """
        return cls(
            philosophy=FAPhilosophy.BALANCED,
            budget_by_position_group={},  # No budget constraints
            priority_positions=[],  # No position priorities
            max_contract_years=5,  # Full flexibility
            max_guaranteed_percent=0.75,  # Balanced guarantees
        )

    def is_default(self) -> bool:
        """Check if this is default/unmodified guidance."""
        return (
            self.philosophy == FAPhilosophy.BALANCED
            and len(self.budget_by_position_group) == 0
            and len(self.priority_positions) == 0
            and self.max_contract_years == 5
            and self.max_guaranteed_percent == 0.75
        )
