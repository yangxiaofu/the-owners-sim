"""
Trade Evaluator

Evaluates trade proposals from a specific GM's perspective, combining objective
trade values with personality-driven modifiers to make accept/reject/counter decisions.
"""

from typing import List, Tuple

from team_management.gm_archetype import GMArchetype
from transactions.personality_modifiers import PersonalityModifiers, TeamContext
from transactions.models import (
    TradeProposal,
    TradeAsset,
    TradeDecision,
    TradeDecisionType,
    AssetType
)
from transactions.trade_value_calculator import TradeValueCalculator


class TradeEvaluator:
    """
    Evaluates trade proposals from a specific GM's perspective.

    Combines objective trade values (from TradeValueCalculator) with
    personality modifiers (from PersonalityModifiers) to determine whether
    to accept, reject, or counter a trade proposal.

    The evaluator is stateless - create one instance per GM/team context,
    then call evaluate_proposal() as many times as needed.
    """

    # Decision thresholds
    COUNTER_WINDOW = 0.05  # Within 5% of threshold = counter territory

    def __init__(
        self,
        gm_archetype: GMArchetype,
        team_context: TeamContext,
        trade_value_calculator: TradeValueCalculator
    ):
        """
        Initialize evaluator for specific GM and team context.

        Args:
            gm_archetype: GM personality traits (0.0-1.0 scales)
            team_context: Current team situation (record, cap, needs, etc.)
            trade_value_calculator: Calculator for objective asset values
        """
        self.gm = gm_archetype
        self.team_context = team_context
        self.calculator = trade_value_calculator

    def evaluate_proposal(
        self,
        proposal: TradeProposal,
        from_perspective_of: int
    ) -> TradeDecision:
        """
        Evaluate trade proposal and return decision with reasoning.

        Args:
            proposal: Complete trade proposal with all assets
            from_perspective_of: Team ID making the evaluation (team1 or team2)

        Returns:
            TradeDecision with decision type, confidence, and reasoning

        Raises:
            ValueError: If from_perspective_of not in proposal teams,
                       or if assets lack trade_value
        """
        # Validate input
        self._validate_proposal(proposal, from_perspective_of)

        # Step 1: Determine which side we're evaluating from
        if from_perspective_of == proposal.team1_id:
            acquiring_assets = proposal.team2_assets  # What we GET
            giving_assets = proposal.team1_assets     # What we GIVE
        else:
            acquiring_assets = proposal.team1_assets
            giving_assets = proposal.team2_assets

        # Step 2: Calculate perceived values with personality modifiers
        acquiring_perceived_values, acquiring_total = self._calculate_perceived_values(
            acquiring_assets, is_acquiring=True
        )
        giving_perceived_values, giving_total = self._calculate_perceived_values(
            giving_assets, is_acquiring=False
        )

        # Step 3: Calculate perceived value ratio
        if giving_total == 0:
            raise ValueError("Cannot evaluate trade with zero giving value")

        perceived_ratio = acquiring_total / giving_total
        objective_ratio = proposal.value_ratio

        # Step 4: Get acceptance threshold for this GM
        min_threshold, max_threshold = PersonalityModifiers.calculate_acceptance_threshold(
            self.gm, self.team_context
        )

        # Step 5: Determine decision type
        decision_type = self._determine_decision_type(
            perceived_ratio, min_threshold, max_threshold
        )

        # Step 6: Calculate confidence score
        confidence = self._calculate_confidence(
            perceived_ratio, min_threshold, max_threshold, decision_type
        )

        # Step 7: Generate reasoning
        reasoning = self._generate_reasoning(
            decision_type,
            perceived_ratio,
            objective_ratio,
            min_threshold,
            max_threshold,
            acquiring_assets,
            giving_assets
        )

        # Step 8: Construct TradeDecision
        return TradeDecision(
            decision=decision_type,
            reasoning=reasoning,
            confidence=confidence,
            original_proposal=proposal,
            counter_offer=None,  # Not implemented in Week 2
            deciding_team_id=from_perspective_of,
            deciding_gm_name=self.gm.name,
            perceived_value_ratio=perceived_ratio,
            objective_value_ratio=objective_ratio
        )

    def _calculate_perceived_values(
        self,
        assets: List[TradeAsset],
        is_acquiring: bool
    ) -> Tuple[List[float], float]:
        """
        Calculate perceived values for list of assets with personality modifiers.

        Args:
            assets: List of trade assets (players or picks)
            is_acquiring: True if acquiring these assets, False if giving away

        Returns:
            Tuple of (list of perceived values, total perceived value)
        """
        perceived_values = []

        for asset in assets:
            # Get objective value (should be pre-populated)
            objective_value = asset.trade_value

            # Apply personality modifier
            modifier = PersonalityModifiers.calculate_total_modifier(
                asset=asset,
                gm=self.gm,
                team_context=self.team_context,
                is_acquiring=is_acquiring
            )

            perceived_value = objective_value * modifier
            perceived_values.append(perceived_value)

        total = sum(perceived_values)
        return perceived_values, total

    def _determine_decision_type(
        self,
        perceived_ratio: float,
        min_threshold: float,
        max_threshold: float
    ) -> TradeDecisionType:
        """
        Determine decision type based on perceived ratio vs acceptance thresholds.

        Decision Rules:
        - ACCEPT: perceived_ratio within [min_threshold, max_threshold]
        - COUNTER: perceived_ratio within 5% of either threshold
        - REJECT: perceived_ratio outside acceptable range by >5%

        Examples:
        - min=0.80, max=1.20, ratio=0.95 → ACCEPT (within range)
        - min=0.80, max=1.20, ratio=0.78 → COUNTER (within 5% of 0.80)
        - min=0.80, max=1.20, ratio=1.22 → COUNTER (within 5% of 1.20)
        - min=0.80, max=1.20, ratio=0.65 → REJECT (too far below)
        - min=0.80, max=1.20, ratio=1.40 → REJECT (too far above)

        Args:
            perceived_ratio: Ratio of acquiring value / giving value
            min_threshold: Minimum acceptable ratio
            max_threshold: Maximum acceptable ratio

        Returns:
            TradeDecisionType (ACCEPT, REJECT, or COUNTER_OFFER)
        """
        # Check if within acceptable range
        if min_threshold <= perceived_ratio <= max_threshold:
            return TradeDecisionType.ACCEPT

        # Check if close to acceptable range (counter territory)
        if (abs(perceived_ratio - min_threshold) <= self.COUNTER_WINDOW or
            abs(perceived_ratio - max_threshold) <= self.COUNTER_WINDOW):
            return TradeDecisionType.COUNTER_OFFER

        # Otherwise reject
        return TradeDecisionType.REJECT

    def _calculate_confidence(
        self,
        perceived_ratio: float,
        min_threshold: float,
        max_threshold: float,
        decision: TradeDecisionType
    ) -> float:
        """
        Calculate confidence score (0.0-1.0) for decision.

        Confidence scoring:

        ACCEPT decisions:
        - 0.9-1.0: Ratio very close to 1.0 (perfect fairness)
        - 0.7-0.9: Ratio within middle 60% of acceptable range
        - 0.5-0.7: Ratio near edges of acceptable range

        REJECT decisions:
        - 0.9-1.0: Ratio very far from acceptable range (>30% away)
        - 0.7-0.9: Ratio moderately far from range (10-30% away)
        - 0.5-0.7: Ratio just outside range (5-10% away)

        COUNTER decisions:
        - Always 0.5 (inherently borderline/uncertain)

        Args:
            perceived_ratio: Ratio of acquiring value / giving value
            min_threshold: Minimum acceptable ratio
            max_threshold: Maximum acceptable ratio
            decision: The decision type determined

        Returns:
            Confidence score between 0.0 and 1.0
        """
        if decision == TradeDecisionType.ACCEPT:
            # Distance from perfect fairness (1.0)
            distance_from_perfect = abs(perceived_ratio - 1.0)

            # Perfect trade (ratio ~1.0) = very high confidence
            if distance_from_perfect <= 0.05:
                return 0.95

            # Within acceptable range = moderate-high confidence
            # Map distance to confidence: closer to 1.0 = higher confidence
            range_width = max_threshold - min_threshold
            distance_from_center = abs(perceived_ratio - 1.0)
            normalized_distance = distance_from_center / (range_width / 2)

            confidence = 0.95 - (normalized_distance * 0.45)  # 0.95 to 0.50
            return max(0.50, min(0.95, confidence))

        elif decision == TradeDecisionType.REJECT:
            # Distance from nearest threshold
            distance_to_min = abs(perceived_ratio - min_threshold)
            distance_to_max = abs(perceived_ratio - max_threshold)
            distance_from_range = min(distance_to_min, distance_to_max)

            # Very far from acceptable = very high confidence in rejection
            if distance_from_range > 0.30:
                return 0.95
            elif distance_from_range > 0.20:
                return 0.85
            elif distance_from_range > 0.10:
                return 0.75
            else:
                return 0.65

        else:  # COUNTER_OFFER
            # Counter-offers are inherently uncertain (borderline decisions)
            return 0.50

    def _generate_reasoning(
        self,
        decision: TradeDecisionType,
        perceived_ratio: float,
        objective_ratio: float,
        min_threshold: float,
        max_threshold: float,
        acquiring_assets: List[TradeAsset],
        giving_assets: List[TradeAsset]
    ) -> str:
        """
        Generate human-readable reasoning for decision.

        Reasoning structure:
        1. Perceived value comparison vs objective value
        2. Key personality adjustments that drove the decision
        3. Threshold comparison outcome
        4. (For COUNTER) Suggested adjustment direction

        Args:
            decision: The decision type
            perceived_ratio: Ratio after personality modifiers
            objective_ratio: Ratio before personality modifiers
            min_threshold: Minimum acceptable ratio
            max_threshold: Maximum acceptable ratio
            acquiring_assets: Assets being acquired
            giving_assets: Assets being given away

        Returns:
            Multi-sentence reasoning string
        """
        parts = []

        # Part 1: Value ratio assessment
        if perceived_ratio < 0.95:
            value_desc = f"advantage to us (ratio: {perceived_ratio:.2f})"
        elif perceived_ratio > 1.15:
            value_desc = f"significant disadvantage (ratio: {perceived_ratio:.2f})"
        elif perceived_ratio > 1.05:
            value_desc = f"slight disadvantage (ratio: {perceived_ratio:.2f})"
        else:
            value_desc = f"roughly even value (ratio: {perceived_ratio:.2f})"

        parts.append(f"Trade offers perceived value ratio showing {value_desc}.")

        # Part 2: Personality adjustment explanation (if significant)
        personality_adjustment = perceived_ratio / objective_ratio if objective_ratio != 0 else 1.0
        if abs(personality_adjustment - 1.0) > 0.15:
            # Identify dominant trait modifiers
            key_traits = self._identify_key_traits_affecting_trade(
                acquiring_assets, giving_assets
            )
            if key_traits:
                parts.append(
                    f"GM personality adjustments ({', '.join(key_traits)}) create "
                    f"{personality_adjustment:.2f}x modifier from objective value."
                )

        # Part 3: Threshold comparison and decision
        if decision == TradeDecisionType.ACCEPT:
            parts.append(
                f"Deal falls within our acceptable range of "
                f"{min_threshold:.2f}-{max_threshold:.2f}. We accept."
            )
        elif decision == TradeDecisionType.REJECT:
            if perceived_ratio < min_threshold:
                parts.append(
                    f"Deal is below our minimum threshold of {min_threshold:.2f}. "
                    f"We reject as insufficient value."
                )
            else:
                parts.append(
                    f"Deal exceeds our maximum threshold of {max_threshold:.2f}. "
                    f"We reject as too expensive."
                )
        else:  # COUNTER
            parts.append(
                f"Deal is just outside our acceptable range of "
                f"{min_threshold:.2f}-{max_threshold:.2f}. Open to counter-offer."
            )

        return " ".join(parts)

    def _identify_key_traits_affecting_trade(
        self,
        acquiring_assets: List[TradeAsset],
        giving_assets: List[TradeAsset]
    ) -> List[str]:
        """
        Identify which GM traits most affected this trade evaluation.

        Returns list of trait names (e.g., ['draft_pick_value', 'win_now_mentality'])
        Limited to top 2 traits for readability.

        Logic:
        - Check asset types: Draft picks → draft_pick_value trait
        - Check player ages: Young players → risk_tolerance, veteran_preference
        - Check player ratings: Elite players → star_chasing
        - Check contracts: Expensive → cap_management
        - Check team context: Contender → win_now_mentality, deadline_activity

        Args:
            acquiring_assets: Assets being acquired
            giving_assets: Assets being given away

        Returns:
            List of trait names (max 2)
        """
        key_traits = []
        all_assets = acquiring_assets + giving_assets

        # Check for draft picks
        has_picks = any(a.asset_type == AssetType.DRAFT_PICK for a in all_assets)
        if has_picks and abs(self.gm.draft_pick_value - 0.5) > 0.2:
            key_traits.append('draft_pick_value')

        # Check for elite players
        has_elite = any(
            a.overall_rating and a.overall_rating >= 90
            for a in all_assets
            if a.asset_type == AssetType.PLAYER
        )
        if has_elite and self.gm.star_chasing > 0.6:
            key_traits.append('star_chasing')

        # Check for expensive contracts
        has_expensive = any(
            a.annual_cap_hit and a.annual_cap_hit > 20_000_000
            for a in all_assets
            if a.asset_type == AssetType.PLAYER
        )
        if has_expensive and abs(self.gm.cap_management - 0.5) > 0.2:
            key_traits.append('cap_management')

        # Check for young/old players
        has_young = any(
            a.age and a.age < 25
            for a in all_assets
            if a.asset_type == AssetType.PLAYER
        )
        if has_young and abs(self.gm.risk_tolerance - 0.5) > 0.2:
            key_traits.append('risk_tolerance')

        # Check for win-now context
        if self.team_context.is_playoff_contender and self.gm.win_now_mentality > 0.6:
            key_traits.append('win_now_mentality')

        # Check for deadline context
        if self.team_context.is_deadline and self.gm.deadline_activity > 0.6:
            key_traits.append('deadline_activity')

        return key_traits[:2]  # Limit to top 2 traits for readability

    def _validate_proposal(
        self,
        proposal: TradeProposal,
        from_perspective_of: int
    ) -> None:
        """
        Validate proposal and perspective inputs.

        Args:
            proposal: Trade proposal to validate
            from_perspective_of: Team ID making the evaluation

        Raises:
            ValueError: If validation fails
        """
        # Validate perspective team_id
        if from_perspective_of not in [proposal.team1_id, proposal.team2_id]:
            raise ValueError(
                f"from_perspective_of must be team1_id ({proposal.team1_id}) "
                f"or team2_id ({proposal.team2_id}), got {from_perspective_of}"
            )

        # Validate all assets have trade_value populated
        all_assets = proposal.team1_assets + proposal.team2_assets
        for asset in all_assets:
            if asset.trade_value == 0.0:
                raise ValueError(
                    f"Asset {asset} has no trade_value. "
                    "Call TradeValueCalculator.evaluate_trade() first to populate values."
                )
