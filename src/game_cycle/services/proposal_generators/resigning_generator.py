"""
Re-signing Proposal Generator - GM analysis for contract extension recommendations.

Part of Tollgate 6: Re-signing Integration.

Analyzes expiring contracts and owner directives to generate prioritized
extension proposals with budget-adjusted offers.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from src.utils.player_field_extractors import extract_overall_rating
from game_cycle.models.owner_directives import OwnerDirectives
from game_cycle.models.persistent_gm_proposal import (
    PersistentGMProposal,
    create_extension_details,
)
from game_cycle.models.proposal_enums import ProposalType, ProposalStatus


class ResigningProposalGenerator:
    """
    Generates extension proposals for expiring contracts.

    Prioritizes based on owner directives and player value.
    Calculates market-adjusted offers based on budget stance.

    Priority tiers (lower number = higher priority):
    - Tier 1: Protected players
    - Tier 2: Position priorities
    - Tier 3: High-value players (80+ OVR)
    - Tier 4: Solid starters (70-79 OVR)
    - Tier 5: Depth players (<70 OVR)

    Excludes expendable players from proposals.
    """

    # Priority tiers
    TIER_PROTECTED = 1
    TIER_PRIORITY_POS = 2
    TIER_HIGH_VALUE = 3
    TIER_SOLID = 4
    TIER_DEPTH = 5

    # Budget stance multipliers
    BUDGET_MULTIPLIERS = {
        "aggressive": 1.08,  # +8% above market
        "moderate": 1.00,    # Market value
        "conservative": 0.92,  # -8% below market
    }

    # Minimum overall for depth player extension
    MIN_DEPTH_OVERALL = 65

    def __init__(
        self,
        db_path: str,
        dynasty_id: str,
        season: int,
        team_id: int,
        directives: OwnerDirectives,
        cap_space: int = 0,
        gm_archetype: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize the generator.

        Args:
            db_path: Path to database
            dynasty_id: Dynasty identifier
            season: Current season year
            team_id: User's team ID
            directives: Owner's strategic directives
            cap_space: Available cap space in dollars (for cap-aware recommendations)
            gm_archetype: GM personality traits (affects cap utilization)
        """
        self._db_path = db_path
        self._dynasty_id = dynasty_id
        self._season = season
        self._team_id = team_id
        self._directives = directives
        self._cap_space = cap_space
        self._gm_archetype = gm_archetype or {}

    def _get_cap_utilization(self) -> float:
        """
        Determine what percentage of cap space GM will use for re-signing.

        Based on GM archetype cap_management trait:
        - High cap_management (0.8-1.0): Conservative, use 60-70% of cap
        - Medium cap_management (0.4-0.7): Moderate, use 70-85% of cap
        - Low cap_management (0.0-0.3): Aggressive, use 85-100% of cap

        Returns:
            Float between 0.0 and 1.0 representing cap utilization percentage
        """
        cap_mgmt = self._gm_archetype.get("cap_management", 0.5)

        if cap_mgmt >= 0.8:
            return 0.65  # Conservative
        elif cap_mgmt >= 0.4:
            return 0.77  # Moderate
        else:
            return 0.92  # Aggressive

    def generate_proposals(
        self, expiring_players: List[Dict[str, Any]]
    ) -> List[PersistentGMProposal]:
        """
        Generate extension proposals for all eligible expiring contracts.

        Args:
            expiring_players: List of player dicts from _get_expiring_contracts()

        Returns:
            List of PersistentGMProposal objects, sorted by priority
        """
        if not expiring_players:
            return []

        proposals = []

        for player in expiring_players:
            player_id = player.get("player_id")

            # Skip expendable players
            if player_id in self._directives.expendable_player_ids:
                continue

            tier = self._get_priority_tier(player)

            # Skip low-value depth players
            if tier == self.TIER_DEPTH and not self._should_propose_depth(player):
                continue

            offer = self._calculate_offer(player)
            reasoning = self._generate_reasoning(player, offer, tier)
            proposal = self._create_proposal(player, offer, reasoning, tier)
            proposals.append(proposal)

        # Sort by tier (ascending), then by AAV (descending for importance)
        proposals.sort(
            key=lambda p: (
                p.priority,
                -p.details.get("proposed_contract", {}).get("aav", 0)
            )
        )

        return proposals

    def generate_all_player_recommendations(
        self, expiring_players: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Generate recommendations for ALL expiring players (cap-aware).

        Unlike generate_proposals() which only returns players GM recommends,
        this method returns ALL players with a gm_recommends flag. This enables
        a unified UI where the owner can see all expiring contracts and override
        GM decisions.

        Cap-aware logic:
        - Calculates remaining budget based on cap_space and GM archetype
        - Recommends players in priority order until budget exhausted
        - Players that can't be afforded get gm_recommends=False with reasoning

        Args:
            expiring_players: List of player dicts from _get_expiring_contracts()

        Returns:
            List of dicts with:
            - All original player data
            - gm_recommends: bool (True = GM recommends extension)
            - proposed_contract: dict with aav, years, total, guaranteed
            - gm_reasoning: str explaining recommendation or why not
            - priority_tier: int (1-5, lower = higher priority)
        """
        if not expiring_players:
            return []

        # Calculate remaining budget based on cap space and GM personality
        cap_utilization = self._get_cap_utilization()
        remaining_budget = int(self._cap_space * cap_utilization) if self._cap_space > 0 else 0

        recommendations = []

        # Sort players by priority tier, then by overall (descending)
        sorted_players = sorted(
            expiring_players,
            key=lambda p: (self._get_priority_tier(p), -extract_overall_rating(p, default=0))
        )

        for player in sorted_players:
            player_id = player.get("player_id")
            tier = self._get_priority_tier(player)

            # Check if owner marked as expendable
            is_expendable = player_id in self._directives.expendable_player_ids

            if is_expendable:
                # Owner marked as expendable - don't recommend
                recommendations.append({
                    **player,
                    "gm_recommends": False,
                    "proposed_contract": None,
                    "gm_reasoning": "Owner directive: marked expendable",
                    "priority_tier": tier,
                })
                continue

            # Calculate offer for this player
            offer = self._calculate_offer(player)
            aav = offer.get("aav", 0)

            # Determine if GM should recommend based on cap and tier
            can_afford = aav <= remaining_budget
            is_worth_extending = tier <= self.TIER_SOLID or (
                tier == self.TIER_DEPTH and self._should_propose_depth(player)
            )

            if can_afford and is_worth_extending:
                # Recommend extension and deduct from budget
                remaining_budget -= aav
                reasoning = self._generate_reasoning(player, offer, tier)
                recommendations.append({
                    **player,
                    "gm_recommends": True,
                    "proposed_contract": {
                        "years": offer.get("years", 1),
                        "total": offer.get("total", 0),
                        "guaranteed": offer.get("guaranteed", 0),
                        "aav": aav,
                    },
                    "gm_reasoning": reasoning,
                    "priority_tier": tier,
                })
            else:
                # Don't recommend - explain why
                reason = self._generate_skip_reasoning(
                    player, offer, tier,
                    over_budget=not can_afford,
                    low_value=not is_worth_extending
                )
                recommendations.append({
                    **player,
                    "gm_recommends": False,
                    "proposed_contract": {
                        "years": offer.get("years", 1),
                        "total": offer.get("total", 0),
                        "guaranteed": offer.get("guaranteed", 0),
                        "aav": aav,
                    },
                    "gm_reasoning": reason,
                    "priority_tier": tier,
                })

        return recommendations

    def _generate_skip_reasoning(
        self,
        player: Dict[str, Any],
        offer: Dict[str, Any],
        tier: int,
        over_budget: bool = False,
        low_value: bool = False,
    ) -> str:
        """
        Generate reasoning for why GM does not recommend extending a player.

        Args:
            player: Player dict
            offer: Calculated offer dict
            tier: Priority tier
            over_budget: True if player's AAV exceeds remaining budget
            low_value: True if player is low priority (depth/rebuild)

        Returns:
            Human-readable reasoning string
        """
        name = player.get("name", "Unknown")
        position = player.get("position", "")
        overall = extract_overall_rating(player, default=0)
        age = player.get("age", 25)
        aav = offer.get("aav", 0)

        aav_str = f"${aav / 1_000_000:.1f}M"

        if over_budget and low_value:
            return (
                f"{name} ({position}, {overall} OVR) doesn't fit our cap situation "
                f"and is below our re-signing threshold. Market value: {aav_str}/yr."
            )

        if over_budget:
            if tier <= self.TIER_PRIORITY_POS:
                return (
                    f"{name} ({position}, {overall} OVR) is a priority player, but "
                    f"at {aav_str}/yr we can't fit him under the cap. Consider "
                    f"restructuring other contracts to make room."
                )
            return (
                f"{name} ({position}, {overall} OVR) has market value of {aav_str}/yr, "
                f"but we've prioritized higher-value players with our cap space."
            )

        if low_value:
            if age >= 30:
                return (
                    f"{name} ({position}, {overall} OVR) is {age} years old and declining. "
                    f"Better to address this position in free agency or the draft."
                )
            if overall < self.MIN_DEPTH_OVERALL:
                return (
                    f"{name} ({position}, {overall} OVR) is below our re-signing threshold. "
                    f"We can find comparable value in free agency."
                )
            if self._directives.team_philosophy == "rebuild":
                return (
                    f"{name} ({position}, {overall} OVR) doesn't fit our rebuilding "
                    f"timeline. We should prioritize younger players or draft picks."
                )

        # Generic fallback
        return (
            f"{name} ({position}, {overall} OVR) is not recommended for extension. "
            f"Market value: {aav_str}/yr."
        )

    def _get_priority_tier(self, player: Dict[str, Any]) -> int:
        """
        Determine priority tier based on directive.

        Args:
            player: Player dict with player_id, position, overall

        Returns:
            Tier number (1 = highest priority)
        """
        player_id = player.get("player_id")
        position = player.get("position", "")
        overall = extract_overall_rating(player, default=0)

        if player_id in self._directives.protected_player_ids:
            return self.TIER_PROTECTED

        if position in self._directives.priority_positions:
            return self.TIER_PRIORITY_POS

        if overall >= 80:
            return self.TIER_HIGH_VALUE

        if overall >= 70:
            return self.TIER_SOLID

        return self.TIER_DEPTH

    def _should_propose_depth(self, player: Dict[str, Any]) -> bool:
        """
        Determine if a depth player should get an extension proposal.

        Depth players (Tier 5) are only proposed if:
        - Overall >= MIN_DEPTH_OVERALL (65)
        - Philosophy is not 'rebuild'

        Args:
            player: Player dict

        Returns:
            True if should propose extension
        """
        overall = extract_overall_rating(player, default=0)

        if overall < self.MIN_DEPTH_OVERALL:
            return False

        if self._directives.team_philosophy == "rebuild":
            return False

        return True

    def _calculate_offer(self, player: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate contract offer based on market value and budget stance.

        Args:
            player: Player dict with position, overall, age, years_pro

        Returns:
            Offer dict with years, total, guaranteed, aav, signing_bonus
        """
        from offseason.market_value_calculator import MarketValueCalculator

        market_calc = MarketValueCalculator()
        market = market_calc.calculate_player_value(
            position=player.get("position", ""),
            overall=extract_overall_rating(player, default=70),
            age=player.get("age", 25),
            years_pro=player.get("years_pro", 3),
        )

        # Get budget multiplier
        budget = self._directives.budget_stance
        multiplier = self.BUDGET_MULTIPLIERS.get(budget, 1.0)

        # Apply directive constraints
        years = min(market["years"], self._directives.max_contract_years)

        # Calculate guaranteed percentage, respecting directive limit
        market_guaranteed_pct = (
            market["guaranteed"] / market["total_value"]
            if market["total_value"] > 0
            else 0.5
        )
        guaranteed_pct = min(
            market_guaranteed_pct,
            self._directives.max_guaranteed_percent,
        )

        # Calculate values with budget adjustment
        total = int(market["total_value"] * multiplier * 1_000_000)
        guaranteed = int(total * guaranteed_pct)
        aav = total // years if years > 0 else total
        signing_bonus = int(market["signing_bonus"] * multiplier * 1_000_000)

        return {
            "years": years,
            "total": total,
            "guaranteed": guaranteed,
            "aav": aav,
            "signing_bonus": signing_bonus,
            "market_aav": int(market["aav"] * 1_000_000),  # Store for comparison
        }

    def _generate_reasoning(
        self, player: Dict[str, Any], offer: Dict[str, Any], tier: int
    ) -> str:
        """
        Generate contextual reasoning based on tier and directive.

        Args:
            player: Player dict
            offer: Calculated offer dict
            tier: Priority tier

        Returns:
            Human-readable reasoning string
        """
        name = player.get("name", "Unknown")
        position = player.get("position", "")
        overall = extract_overall_rating(player, default=0)
        age = player.get("age", 25)
        aav = offer.get("aav", 0)
        years = offer.get("years", 1)
        market_aav = offer.get("market_aav", aav)

        philosophy = self._directives.team_philosophy
        budget = self._directives.budget_stance

        # Format AAV
        aav_str = f"${aav / 1_000_000:.1f}M"
        market_aav_str = f"${market_aav / 1_000_000:.1f}M"

        # Premium/discount description
        if budget == "aggressive":
            budget_desc = f"an 8% premium ({aav_str}/yr vs {market_aav_str} market)"
        elif budget == "conservative":
            budget_desc = f"an 8% discount ({aav_str}/yr vs {market_aav_str} market)"
        else:
            budget_desc = f"market value ({aav_str}/yr)"

        # Select template based on tier and philosophy
        if tier == self.TIER_PROTECTED:
            if philosophy == "win_now":
                return (
                    f"{name} is a protected player entering free agency at age {age}. "
                    f"At {overall} OVR, he's core to your championship push. "
                    f"I'm proposing {years} years at {budget_desc} to lock him up "
                    f"through your contention window."
                )
            else:
                return (
                    f"You've identified {name} as a protected player. At {age} years old "
                    f"with {overall} OVR at {position}, losing him would be a significant setback. "
                    f"I'm proposing {years} years at {budget_desc}."
                )

        if tier == self.TIER_PRIORITY_POS:
            priority_rank = self._directives.priority_positions.index(position) + 1
            return (
                f"{name} plays {position}, your #{priority_rank} position priority. "
                f"At {overall} OVR and {age} years old, he fills a key need. "
                f"I'm proposing {years} years at {budget_desc}."
            )

        if tier == self.TIER_HIGH_VALUE:
            if philosophy == "win_now":
                return (
                    f"{name} ({position}, {overall} OVR) is a high-value player "
                    f"entering free agency. Given your Win-Now philosophy, "
                    f"I'm proposing {years} years at {budget_desc} to keep him."
                )
            elif philosophy == "rebuild" and age >= 28:
                return (
                    f"{name} ({position}, {overall} OVR, {age} yo) has value, but given "
                    f"your rebuilding philosophy, we might prefer to see his market value "
                    f"in free agency. Still, I'm offering {years} years at {budget_desc} "
                    f"as a starting point for negotiation."
                )
            else:
                return (
                    f"{name} ({position}, {overall} OVR) is a valuable contributor. "
                    f"At {age} years old, he has productive years ahead. "
                    f"I'm proposing {years} years at {budget_desc}."
                )

        if tier == self.TIER_SOLID:
            return (
                f"{name} ({position}, {overall} OVR) is a solid starter. "
                f"At {age} years old, he provides roster stability. "
                f"I'm proposing {years} years at {budget_desc}."
            )

        # TIER_DEPTH
        return (
            f"{name} ({position}, {overall} OVR) provides depth at {age} years old. "
            f"I'm proposing {years} years at {budget_desc} to maintain roster flexibility."
        )

    def _create_proposal(
        self,
        player: Dict[str, Any],
        offer: Dict[str, Any],
        reasoning: str,
        tier: int,
    ) -> PersistentGMProposal:
        """
        Create a PersistentGMProposal for the extension.

        Args:
            player: Player dict
            offer: Calculated offer dict
            reasoning: GM reasoning string
            tier: Priority tier

        Returns:
            PersistentGMProposal object
        """
        player_id = player.get("player_id")
        name = player.get("name", "Unknown")
        position = player.get("position", "")

        # Build current contract info
        current_contract = {
            "years": player.get("years_remaining", 1),
            "total": player.get("salary", 0) * player.get("years_remaining", 1),
            "aav": player.get("salary", 0),
        }

        # Build proposed contract info
        proposed_contract = {
            "years": offer.get("years", 1),
            "total": offer.get("total", 0),
            "guaranteed": offer.get("guaranteed", 0),
            "aav": offer.get("aav", 0),
        }

        # Market comparison text
        market_aav = offer.get("market_aav", offer.get("aav", 0))
        aav = offer.get("aav", 0)
        if aav > market_aav:
            pct = ((aav - market_aav) / market_aav * 100) if market_aav > 0 else 0
            market_comparison = f"{pct:.0f}% above market AAV of ${market_aav / 1e6:.1f}M"
        elif aav < market_aav:
            pct = ((market_aav - aav) / market_aav * 100) if market_aav > 0 else 0
            market_comparison = f"{pct:.0f}% below market AAV of ${market_aav / 1e6:.1f}M"
        else:
            market_comparison = f"At market AAV of ${market_aav / 1e6:.1f}M"

        # Get player attributes for proposal details
        overall = extract_overall_rating(player, default=70)
        age = player.get("age", 25)

        # Create details using helper
        details = create_extension_details(
            player_name=name,
            position=position,
            age=age,
            overall=overall,
            current_contract=current_contract,
            proposed_contract=proposed_contract,
            market_comparison=market_comparison,
        )

        # Calculate confidence from tier and overall
        # Higher tier = lower priority but still confident
        # High overall = more confident
        base_confidence = 0.7
        tier_bonus = (5 - tier) * 0.05  # Tier 1 = +0.20, Tier 5 = +0.00
        overall_bonus = (overall - 70) * 0.005  # 80 OVR = +0.05, 90 OVR = +0.10
        confidence = min(0.95, max(0.5, base_confidence + tier_bonus + overall_bonus))

        return PersistentGMProposal(
            dynasty_id=self._dynasty_id,
            team_id=self._team_id,
            season=self._season,
            stage="OFFSEASON_RESIGNING",
            proposal_type=ProposalType.EXTENSION,
            subject_player_id=str(player_id),
            details=details,
            gm_reasoning=reasoning,
            confidence=confidence,
            priority=tier,  # Use tier as priority (lower = higher priority)
            status=ProposalStatus.APPROVED,  # Default to approved - owner can reject
            created_at=datetime.now(),
        )