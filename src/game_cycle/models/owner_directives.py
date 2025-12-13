"""
Owner Directives - Persistent strategic guidance from Owner.

Unlike DraftDirection and FAGuidance (ephemeral), these are persisted
to the database and survive app restarts. They influence GM behavior
throughout the offseason stages.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class OwnerDirectives:
    """
    Owner's strategic directives for the upcoming season.

    Persisted to database via OwnerDirectivesAPI.
    Provides unified guidance that influences:
    - Draft: position priorities, prospect wishlist, strategy
    - Free Agency: philosophy, position priorities, player targets
    - Re-signing: budget allocation, priority players

    Attributes:
        dynasty_id: Dynasty identifier for isolation
        team_id: Team this directive applies to (1-32)
        season: Season year these directives apply to
        target_wins: Expected wins for the season (0-17)
        priority_positions: List of 1-5 positions to target in draft/FA
        fa_wishlist: List of FA player names to pursue
        draft_wishlist: List of draft prospect names to pursue
        draft_strategy: One of 'bpa', 'balanced', 'needs_based', 'position_focus'
        fa_philosophy: One of 'aggressive', 'balanced', 'conservative'
        max_contract_years: Max contract length allowed (1-5)
        max_guaranteed_percent: Max guaranteed money percent (0.0-1.0)
    """

    dynasty_id: str
    team_id: int
    season: int
    target_wins: Optional[int] = None
    priority_positions: List[str] = field(default_factory=list)
    fa_wishlist: List[str] = field(default_factory=list)
    draft_wishlist: List[str] = field(default_factory=list)
    draft_strategy: str = "balanced"
    fa_philosophy: str = "balanced"
    max_contract_years: int = 5
    max_guaranteed_percent: float = 0.75

    def __post_init__(self):
        """Validate directive values."""
        self._validate_team_id()
        self._validate_target_wins()
        self._validate_priority_positions()
        self._validate_strategies()
        self._validate_contract_params()

    def _validate_team_id(self):
        """Ensure team_id is valid (1-32)."""
        if not 1 <= self.team_id <= 32:
            raise ValueError(f"team_id must be 1-32, got {self.team_id}")

    def _validate_target_wins(self):
        """Ensure target_wins is valid if set."""
        if self.target_wins is not None:
            if not 0 <= self.target_wins <= 17:
                raise ValueError(
                    f"target_wins must be 0-17, got {self.target_wins}"
                )

    def _validate_priority_positions(self):
        """Ensure priority positions list is valid."""
        if len(self.priority_positions) > 5:
            raise ValueError(
                f"priority_positions max 5 items, got {len(self.priority_positions)}"
            )

    def _validate_strategies(self):
        """Ensure strategy values are valid."""
        valid_draft = {"bpa", "balanced", "needs_based", "position_focus"}
        if self.draft_strategy not in valid_draft:
            raise ValueError(
                f"draft_strategy must be one of {valid_draft}, got {self.draft_strategy}"
            )

        valid_fa = {"aggressive", "balanced", "conservative"}
        if self.fa_philosophy not in valid_fa:
            raise ValueError(
                f"fa_philosophy must be one of {valid_fa}, got {self.fa_philosophy}"
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

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage."""
        return {
            "dynasty_id": self.dynasty_id,
            "team_id": self.team_id,
            "season": self.season,
            "target_wins": self.target_wins,
            "priority_positions": self.priority_positions.copy(),
            "fa_wishlist": self.fa_wishlist.copy(),
            "draft_wishlist": self.draft_wishlist.copy(),
            "draft_strategy": self.draft_strategy,
            "fa_philosophy": self.fa_philosophy,
            "max_contract_years": self.max_contract_years,
            "max_guaranteed_percent": self.max_guaranteed_percent,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OwnerDirectives":
        """Create from dictionary (database row)."""
        return cls(
            dynasty_id=data["dynasty_id"],
            team_id=data["team_id"],
            season=data["season"],
            target_wins=data.get("target_wins"),
            priority_positions=data.get("priority_positions", []),
            fa_wishlist=data.get("fa_wishlist", []),
            draft_wishlist=data.get("draft_wishlist", []),
            draft_strategy=data.get("draft_strategy", "balanced"),
            fa_philosophy=data.get("fa_philosophy", "balanced"),
            max_contract_years=data.get("max_contract_years", 5),
            max_guaranteed_percent=data.get("max_guaranteed_percent", 0.75),
        )

    @classmethod
    def create_default(
        cls,
        dynasty_id: str,
        team_id: int,
        season: int
    ) -> "OwnerDirectives":
        """
        Create default directives (balanced approach, no constraints).

        Used when owner skips directive setting or for initialization.
        """
        return cls(
            dynasty_id=dynasty_id,
            team_id=team_id,
            season=season,
            target_wins=None,
            priority_positions=[],
            fa_wishlist=[],
            draft_wishlist=[],
            draft_strategy="balanced",
            fa_philosophy="balanced",
            max_contract_years=5,
            max_guaranteed_percent=0.75,
        )

    def to_draft_direction(self) -> "DraftDirection":
        """
        Convert to ephemeral DraftDirection for draft service.

        Returns:
            DraftDirection instance with owner's preferences
        """
        from .draft_direction import DraftDirection, DraftStrategy

        strategy_map = {
            "bpa": DraftStrategy.BEST_PLAYER_AVAILABLE,
            "balanced": DraftStrategy.BALANCED,
            "needs_based": DraftStrategy.NEEDS_BASED,
            "position_focus": DraftStrategy.POSITION_FOCUS,
        }

        return DraftDirection(
            strategy=strategy_map.get(self.draft_strategy, DraftStrategy.BALANCED),
            priority_positions=self.priority_positions.copy(),
            watchlist_prospect_ids=[],  # Names stored, IDs resolved at runtime
        )

    def to_fa_guidance(self) -> "FAGuidance":
        """
        Convert to ephemeral FAGuidance for FA service.

        Returns:
            FAGuidance instance with owner's preferences
        """
        from .fa_guidance import FAGuidance, FAPhilosophy

        philosophy_map = {
            "aggressive": FAPhilosophy.AGGRESSIVE,
            "balanced": FAPhilosophy.BALANCED,
            "conservative": FAPhilosophy.CONSERVATIVE,
        }

        return FAGuidance(
            philosophy=philosophy_map.get(self.fa_philosophy, FAPhilosophy.BALANCED),
            priority_positions=self.priority_positions[:3],  # FA allows max 3
            max_contract_years=self.max_contract_years,
            max_guaranteed_percent=self.max_guaranteed_percent,
        )

    def is_default(self) -> bool:
        """Check if this is default/unmodified directives."""
        return (
            self.target_wins is None
            and len(self.priority_positions) == 0
            and len(self.fa_wishlist) == 0
            and len(self.draft_wishlist) == 0
            and self.draft_strategy == "balanced"
            and self.fa_philosophy == "balanced"
            and self.max_contract_years == 5
            and self.max_guaranteed_percent == 0.75
        )
