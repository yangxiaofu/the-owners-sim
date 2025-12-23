"""
OwnerInfluenceCalculator - Transparent owner influence calculation across all stages.

Makes trust_gm behavior and owner directive constraints explicit and testable.
Consolidates auto-approval logic and contract constraint application.
"""

from typing import Dict, Any
from ..models.owner_directives import OwnerDirectives
from ..stage_definitions import StageType


class OwnerInfluenceCalculator:
    """
    Calculate and apply owner influence on GM proposals.

    Provides:
    - Transparent trust_gm behavior
    - Contract constraint enforcement (max years, guaranteed %)
    - Position priority bonuses
    - Future: Per-stage owner control granularity
    """

    def should_auto_approve(
        self,
        directives: OwnerDirectives,
        stage_type: StageType
    ) -> bool:
        """
        Determine if proposals should auto-approve based on trust_gm.

        Currently all stages use same logic (trust_gm = auto-approve).
        Future: Could add per-stage overrides like "trust_gm_for_draft_only".

        Args:
            directives: Owner directives
            stage_type: Which stage is requesting approval

        Returns:
            True if proposals should be auto-approved
        """
        return directives.trust_gm

    def apply_contract_constraints(
        self,
        proposal_details: Dict[str, Any],
        directives: OwnerDirectives
    ) -> Dict[str, Any]:
        """
        Apply owner contract constraints to proposal details.

        Uses:
        - max_contract_years: Limit contract length (1-5 years)
        - max_guaranteed_percent: Limit guaranteed money (0.0-1.0)

        Args:
            proposal_details: Proposal details dict (will be modified)
            directives: Owner directives with constraints

        Returns:
            Modified proposal_details dict
        """
        details = proposal_details.copy()

        # Apply max contract years constraint
        if directives.max_contract_years is not None and directives.max_contract_years > 0:
            current_years = details.get("contract_years", 5)
            details["contract_years"] = min(current_years, directives.max_contract_years)

        # Apply max guaranteed percent constraint
        if directives.max_guaranteed_percent is not None and directives.max_guaranteed_percent > 0.0:
            total_value = details.get("total_value", 0)
            max_guaranteed = total_value * directives.max_guaranteed_percent
            current_guaranteed = details.get("guaranteed_money", 0)
            details["guaranteed_money"] = min(current_guaranteed, max_guaranteed)

        return details

    def calculate_position_priority_bonus(
        self,
        position: str,
        directives: OwnerDirectives
    ) -> float:
        """
        Calculate bonus for priority positions.

        Priority positions get diminishing bonuses based on rank:
        - 1st priority: +0.85 multiplier
        - 2nd priority: +0.70 multiplier
        - 3rd priority: +0.55 multiplier
        - 4th priority: +0.40 multiplier
        - 5th priority: +0.25 multiplier
        - Not priority: 0.0 (no bonus)

        Args:
            position: Player position (e.g., "QB", "WR")
            directives: Owner directives with priority_positions list

        Returns:
            Bonus multiplier (0.0-0.85)
        """
        if not directives.priority_positions:
            return 0.0

        if position not in directives.priority_positions:
            return 0.0

        # Get rank (0-indexed, then add 1 for 1-indexed)
        rank = directives.priority_positions.index(position) + 1

        # Calculate diminishing bonus
        # 1st: 1.0 - (1 * 0.15) = 0.85
        # 2nd: 1.0 - (2 * 0.15) = 0.70
        # 3rd: 1.0 - (3 * 0.15) = 0.55
        # etc.
        bonus = 1.0 - (rank * 0.15)
        return max(0.0, bonus)  # Never negative

    def is_player_protected(
        self,
        player_id: int,
        directives: OwnerDirectives
    ) -> bool:
        """
        Check if player is on the protected list.

        Protected players should not be:
        - Traded away
        - Cut from roster
        - Tagged with franchise tag (if owner prefers extension)

        Args:
            player_id: Player ID to check
            directives: Owner directives with protected_player_ids list

        Returns:
            True if player is protected
        """
        return player_id in directives.protected_player_ids

    def is_player_expendable(
        self,
        player_id: int,
        directives: OwnerDirectives
    ) -> bool:
        """
        Check if player is on the expendable list.

        Expendable players can be:
        - Traded away more aggressively
        - Cut from roster with lower threshold
        - Not prioritized for re-signing

        Args:
            player_id: Player ID to check
            directives: Owner directives with expendable_player_ids list

        Returns:
            True if player is expendable
        """
        return player_id in directives.expendable_player_ids

    def get_trust_gm_affected_stages(self) -> Dict[StageType, str]:
        """
        Map stages where trust_gm has effect with explanations.

        Used for UI documentation of owner control and debugging.

        Returns:
            Dict mapping StageType to explanation string
        """
        return {
            StageType.OFFSEASON_FRANCHISE_TAG: "Auto-approve franchise tag proposals",
            StageType.OFFSEASON_RESIGNING: "Auto-approve re-signing proposals",
            StageType.OFFSEASON_FREE_AGENCY: "Auto-approve free agent signing proposals",
            StageType.OFFSEASON_TRADING: "Auto-approve trade proposals",
            StageType.OFFSEASON_DRAFT: "Auto-approve draft pick proposals",
            StageType.OFFSEASON_PRESEASON_W1: "Auto-approve preseason week 1 cut proposals",
            StageType.OFFSEASON_PRESEASON_W2: "Auto-approve preseason week 2 cut proposals",
            StageType.OFFSEASON_PRESEASON_W3: "Auto-approve final roster cut proposals",
            StageType.OFFSEASON_WAIVER_WIRE: "Auto-approve waiver wire claim proposals",
        }

    def calculate_fa_offer_multiplier(
        self,
        base_value: int,
        directives: OwnerDirectives
    ) -> float:
        """
        Calculate offer multiplier based on FA philosophy.

        - Aggressive: 1.15x (overpay 15% to secure talent)
        - Balanced: 1.0x (market rate)
        - Conservative: 0.90x (underpay 10%, value signings only)

        Args:
            base_value: Base market value
            directives: Owner directives with fa_philosophy

        Returns:
            Multiplier to apply to base value
        """
        philosophy_multipliers = {
            "aggressive": 1.15,
            "balanced": 1.0,
            "conservative": 0.90,
        }
        return philosophy_multipliers.get(directives.fa_philosophy, 1.0)

    def should_pursue_fa_player(
        self,
        player_ovr: int,
        directives: OwnerDirectives
    ) -> bool:
        """
        Filter free agents by philosophy and overall rating.

        - Aggressive: Pursue players 70+ OVR (go after good players)
        - Balanced: Pursue players 75+ OVR (mid-tier or better)
        - Conservative: Pursue players 80+ OVR (only elite players)

        Args:
            player_ovr: Player overall rating
            directives: Owner directives with fa_philosophy

        Returns:
            True if player meets philosophy threshold
        """
        philosophy_thresholds = {
            "aggressive": 70,
            "balanced": 75,
            "conservative": 80,
        }
        threshold = philosophy_thresholds.get(directives.fa_philosophy, 75)
        return player_ovr >= threshold
