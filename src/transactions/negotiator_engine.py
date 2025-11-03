"""
Negotiator Engine

Generates counter-offers for trade proposals and manages multi-round negotiations
between teams. Combines objective trade values with GM personality traits to create
realistic counter-offers that bridge value gaps while respecting team needs and
personality constraints.
"""

from typing import List, Tuple, Optional

from team_management.gm_archetype import GMArchetype
from transactions.personality_modifiers import PersonalityModifiers, TeamContext
from transactions.models import (
    TradeProposal,
    TradeAsset,
    TradeDecision,
    TradeDecisionType,
    AssetType,
    FairnessRating,
    NegotiationResult,
    NegotiationStalemate
)
from transactions.trade_value_calculator import TradeValueCalculator


class NegotiatorEngine:
    """
    Multi-round trade negotiation engine.

    Generates counter-offers when TradeEvaluator returns COUNTER_OFFER decisions.
    Manages negotiation rounds, prevents infinite loops, and tracks negotiation
    history for convergence analysis.

    The engine uses a hybrid counter-offer strategy:
    1. Calculate target value ratio within GM's acceptance threshold
    2. Identify value gap that needs to be bridged
    3. Select assets from pool to add to proposal
    4. Apply personality filters (draft focus, win-now, cap management)
    5. Validate fairness and construct counter-proposal

    Usage:
        negotiator = NegotiatorEngine(gm_archetype, team_context, calculator, asset_pool)
        counter = negotiator.generate_counter_offer(proposal, decision)
    """

    # Configuration constants
    MAX_ROUNDS = 4  # Initial proposal + 3 counters
    MIN_PROGRESS_RATIO = 0.05  # Require 5% gap reduction per round
    COUNTER_WINDOW_SHRINK = 0.8  # Shrink tolerance each round
    MIN_ASSET_VALUE = 10.0  # Filter out insignificant assets
    MAX_ASSETS_PER_COUNTER = 3  # Maximum assets to add in single counter

    def __init__(
        self,
        gm_archetype: GMArchetype,
        team_context: TeamContext,
        trade_value_calculator: TradeValueCalculator,
        asset_pool: Optional[List[TradeAsset]] = None
    ):
        """
        Initialize negotiator for specific GM and team context.

        Args:
            gm_archetype: GM personality traits (0.0-1.0 scales)
            team_context: Current team situation (record, cap, needs, etc.)
            trade_value_calculator: Calculator for objective asset values
            asset_pool: Available assets this GM can offer in counters (optional)

        Note:
            If asset_pool is None, counter-offer generation will fail with
            NegotiationStalemate. Provide a pool of tradeable assets to enable
            counter-offers.
        """
        self.gm = gm_archetype
        self.team_context = team_context
        self.calculator = trade_value_calculator
        self.asset_pool = asset_pool or []

    def generate_counter_offer(
        self,
        original_proposal: TradeProposal,
        decision: TradeDecision,
        negotiation_history: Optional[List[TradeProposal]] = None
    ) -> TradeProposal:
        """
        Generate single counter-offer to bridge value gap.

        Analyzes the original proposal and creates a counter-offer that brings
        the trade value ratio within the GM's acceptance threshold. Uses
        personality traits to select appropriate assets to add.

        Args:
            original_proposal: Proposal being countered
            decision: TradeDecision from TradeEvaluator with perceived_ratio, etc.
            negotiation_history: Previous proposals (for duplicate detection)

        Returns:
            Counter-proposal with adjusted assets to meet threshold

        Raises:
            ValueError: If original_proposal lacks trade_value data or if
                       decision is not a COUNTER_OFFER type
            NegotiationStalemate: If no viable counter can be generated
                                 (empty asset pool, extreme gap, etc.)

        Example:
            Original: Team A gives 80 OVR LB (250 value) → Team B gives 2nd pick (150)
            Ratio: 0.60 (below 0.80 threshold)
            Counter: Team A gives 80 OVR LB (250) → Team B gives 2nd + 4th picks (225)
            New Ratio: 0.90 (within 0.80-1.20 range)
        """
        # Validate inputs
        self._validate_counter_inputs(original_proposal, decision)

        # Get negotiation history for duplicate detection
        history = negotiation_history or []

        # Step 1: Determine which side we're evaluating from
        deciding_team_id = decision.deciding_team_id
        if deciding_team_id == original_proposal.team1_id:
            our_assets = original_proposal.team1_assets
            their_assets = original_proposal.team2_assets
            our_total = original_proposal.team1_total_value
            their_total = original_proposal.team2_total_value
        else:
            our_assets = original_proposal.team2_assets
            their_assets = original_proposal.team1_assets
            our_total = original_proposal.team2_total_value
            their_total = original_proposal.team1_total_value

        # Step 2: Calculate target ratio and value gap
        perceived_ratio = decision.perceived_value_ratio
        min_threshold, max_threshold = PersonalityModifiers.calculate_acceptance_threshold(
            self.gm, self.team_context
        )

        target_ratio = self._calculate_target_ratio(
            perceived_ratio, min_threshold, max_threshold
        )

        # Step 3: Determine what adjustment is needed
        # Perceived ratio = acquiring_total / giving_total
        # If ratio too low (< min_threshold), we need more value coming in
        # If ratio too high (> max_threshold), we need to give more value
        if perceived_ratio < min_threshold:
            # We're giving too much, need more value back
            # Calculate: how much more value do we need to receive?
            required_acquiring_total = our_total * target_ratio
            value_gap = required_acquiring_total - their_total

            # Edge Case 3: Check for extreme value gaps
            self._validate_value_gap(value_gap, our_total)

            # We need to ADD assets to their side (what we're receiving)
            assets_to_add = self._select_assets_to_add(
                value_gap=value_gap,
                is_acquiring=True  # Adding to what we receive
            )

            # Construct counter with additional assets on their side
            if deciding_team_id == original_proposal.team1_id:
                counter_team1_assets = list(our_assets)
                counter_team2_assets = list(their_assets) + assets_to_add
            else:
                counter_team1_assets = list(their_assets) + assets_to_add
                counter_team2_assets = list(our_assets)

        else:  # perceived_ratio > max_threshold
            # We're getting too much, need to give more
            # Calculate: how much more value do we need to give?
            required_giving_total = their_total / target_ratio
            value_gap = required_giving_total - our_total

            # Edge Case 3: Check for extreme value gaps
            self._validate_value_gap(value_gap, our_total)

            # We need to ADD assets to our side (what we're giving)
            assets_to_add = self._select_assets_to_add(
                value_gap=value_gap,
                is_acquiring=False  # Adding to what we give
            )

            # Construct counter with additional assets on our side
            if deciding_team_id == original_proposal.team1_id:
                counter_team1_assets = list(our_assets) + assets_to_add
                counter_team2_assets = list(their_assets)
            else:
                counter_team1_assets = list(their_assets)
                counter_team2_assets = list(our_assets) + assets_to_add

        # Step 4: Calculate values for counter-proposal
        counter_team1_total = sum(asset.trade_value for asset in counter_team1_assets)
        counter_team2_total = sum(asset.trade_value for asset in counter_team2_assets)

        if counter_team1_total == 0:
            raise NegotiationStalemate("Counter-proposal team1 total value is zero")

        counter_ratio = counter_team2_total / counter_team1_total

        # Step 5: Determine fairness rating
        counter_fairness = TradeProposal.calculate_fairness(counter_ratio)

        # Step 6: Construct counter-proposal
        counter_proposal = TradeProposal(
            team1_id=original_proposal.team1_id,
            team1_assets=counter_team1_assets,
            team1_total_value=counter_team1_total,
            team2_id=original_proposal.team2_id,
            team2_assets=counter_team2_assets,
            team2_total_value=counter_team2_total,
            value_ratio=counter_ratio,
            fairness_rating=counter_fairness,
            passes_cap_validation=False,  # Not validated yet
            passes_roster_validation=False,
            initiating_team_id=deciding_team_id  # Counter from evaluating team
        )

        # Step 7: Validate cap space constraints (Edge Case 4)
        self._validate_cap_space(assets_to_add, deciding_team_id)

        # Step 8: Check for duplicate (prevent infinite loops)
        if self._is_duplicate_proposal(counter_proposal, history):
            raise NegotiationStalemate("Counter-proposal is duplicate of previous proposal")

        return counter_proposal

    def _calculate_target_ratio(
        self,
        perceived_ratio: float,
        min_threshold: float,
        max_threshold: float
    ) -> float:
        """
        Calculate target value ratio for counter-offer.

        Aims for just inside the acceptance threshold to maximize chances
        of acceptance while minimizing concessions.

        Args:
            perceived_ratio: Current perceived value ratio
            min_threshold: Minimum acceptable ratio for this GM
            max_threshold: Maximum acceptable ratio for this GM

        Returns:
            Target ratio for counter-offer (slightly inside threshold)

        Examples:
            - perceived_ratio=0.75, min=0.80 → target=0.83 (min + 0.03)
            - perceived_ratio=1.25, max=1.20 → target=1.17 (max - 0.03)
        """
        if perceived_ratio < min_threshold:
            # Too low, target just above minimum
            return min_threshold + 0.03
        else:
            # Too high, target just below maximum
            return max_threshold - 0.03

    def _validate_value_gap(self, value_gap: float, reference_value: float) -> None:
        """
        Validate that value gap can be realistically bridged.

        Edge case handling for extreme value gaps that cannot be bridged
        with available assets.

        Args:
            value_gap: Required value to add (in trade units)
            reference_value: Reference value for proportionality check (current total)

        Raises:
            NegotiationStalemate: If value gap is too large or invalid

        Examples:
            - value_gap=500, reference=100 → raises (5x gap is extreme)
            - value_gap=50, reference=100 → passes (0.5x gap is reasonable)
        """
        # Edge Case 3a: Negative value gaps (should not happen)
        if value_gap < 0:
            raise NegotiationStalemate(
                f"Invalid negative value gap: {value_gap:.1f}"
            )

        # Edge Case 3b: Very small value gaps (less than MIN_ASSET_VALUE)
        if value_gap < self.MIN_ASSET_VALUE:
            raise NegotiationStalemate(
                f"Value gap too small to bridge with meaningful assets "
                f"({value_gap:.1f} < {self.MIN_ASSET_VALUE})"
            )

        # Edge Case 3c: Extreme value gaps (>3x current proposal value)
        # If gap is more than 3x the current value, it's likely unbridgeable
        if value_gap > reference_value * 3.0:
            raise NegotiationStalemate(
                f"Value gap too large to bridge ({value_gap:.1f} > 3x reference {reference_value:.1f})"
            )

        # Edge Case 3d: Check if asset pool has sufficient total value
        if self.asset_pool:
            pool_total_value = sum(a.trade_value for a in self.asset_pool)
            if pool_total_value < value_gap * 0.5:
                raise NegotiationStalemate(
                    f"Asset pool insufficient to bridge gap "
                    f"(pool: {pool_total_value:.1f}, gap: {value_gap:.1f})"
                )

    def _validate_cap_space(
        self,
        assets_to_add: List[TradeAsset],
        deciding_team_id: int
    ) -> None:
        """
        Validate that adding assets doesn't exceed cap space.

        Edge case handling for cap-constrained teams that cannot afford
        to add expensive player contracts.

        Args:
            assets_to_add: Assets being added to counter-offer
            deciding_team_id: Team ID making the counter-offer

        Raises:
            NegotiationStalemate: If counter-offer would exceed cap space

        Note:
            Only validates if team_context has cap_space_available attribute.
            Draft picks have no cap impact.
        """
        # Edge Case 4: Cap space validation
        if not hasattr(self.team_context, 'cap_space_available'):
            return  # No cap data available, skip validation

        cap_space = self.team_context.cap_space_available
        if cap_space is None:
            return  # No cap constraint

        # Calculate total cap hit from added player assets
        total_cap_hit = 0
        for asset in assets_to_add:
            if asset.asset_type == AssetType.PLAYER and asset.annual_cap_hit:
                total_cap_hit += asset.annual_cap_hit

        # Check if cap hit exceeds available space
        # Allow 10% buffer for minor accounting differences
        if total_cap_hit > cap_space * 1.1:
            raise NegotiationStalemate(
                f"Counter-offer exceeds cap space "
                f"(required: ${total_cap_hit:,}, available: ${cap_space:,})"
            )

    def _select_assets_to_add(
        self,
        value_gap: float,
        is_acquiring: bool
    ) -> List[TradeAsset]:
        """
        Select assets from pool to bridge value gap.

        Uses a greedy algorithm to select 1-3 assets that collectively
        bridge the value gap. Applies personality filters to prefer
        certain asset types (picks vs players, veterans vs youth, etc.).

        Args:
            value_gap: Amount of trade value needed (in trade units)
            is_acquiring: True if adding to what we receive, False if adding to what we give

        Returns:
            List of 1-3 TradeAsset objects to add to proposal

        Raises:
            NegotiationStalemate: If asset pool is empty or no suitable assets found

        Note:
            Day 5: Now includes personality-driven asset selection filters.
        """
        # Validate asset pool
        if not self.asset_pool:
            raise NegotiationStalemate("Asset pool is empty, cannot generate counter-offer")

        # Filter out insignificant assets
        viable_assets = [
            asset for asset in self.asset_pool
            if asset.trade_value >= self.MIN_ASSET_VALUE
        ]

        if not viable_assets:
            raise NegotiationStalemate("No viable assets in pool (all below minimum value)")

        # Apply personality filters
        viable_assets = self._apply_personality_filters(viable_assets, is_acquiring)

        if not viable_assets:
            raise NegotiationStalemate("No assets pass personality filters")

        # Calculate preference scores for each asset
        scored_assets = [
            (asset, self._calculate_asset_preference_score(asset))
            for asset in viable_assets
        ]

        # Sort by preference score (higher = more preferred)
        scored_assets.sort(key=lambda x: x[1], reverse=True)

        # Strategy: Greedily select assets that bridge gap, preferring high-scored assets
        selected_assets = []
        remaining_gap = value_gap

        for asset, score in scored_assets:
            if len(selected_assets) >= self.MAX_ASSETS_PER_COUNTER:
                break

            # Add asset if it helps close the gap
            if asset.trade_value <= remaining_gap * 1.5:  # Allow up to 50% overshoot
                selected_assets.append(asset)
                remaining_gap -= asset.trade_value

                # Check if we've bridged enough of the gap
                if remaining_gap <= value_gap * 0.2:  # Within 20% of target
                    break

        if not selected_assets:
            # Fallback: Take highest-scored asset
            highest_scored = scored_assets[0][0]
            selected_assets = [highest_scored]

        # Check if we actually bridged meaningful gap
        total_added_value = sum(a.trade_value for a in selected_assets)
        if total_added_value < value_gap * 0.3:  # Added less than 30% of needed value
            raise NegotiationStalemate(
                f"Could not bridge value gap of {value_gap:.1f} with available assets "
                f"(best attempt: {total_added_value:.1f})"
            )

        return selected_assets

    def _apply_personality_filters(
        self,
        assets: List[TradeAsset],
        is_acquiring: bool
    ) -> List[TradeAsset]:
        """
        Apply GM personality filters to asset pool.

        Filters out assets that don't match GM's personality traits:
        - Cap-conscious GMs exclude expensive contracts
        - Win-now GMs exclude young/unproven players
        - Conservative GMs may have additional restrictions

        Args:
            assets: List of assets to filter
            is_acquiring: True if acquiring these assets, False if giving

        Returns:
            Filtered list of assets that match GM personality
        """
        filtered = list(assets)

        # Filter 1: Cap management (exclude expensive contracts if cap-conscious)
        if self.gm.cap_management > 0.7:
            # Cap-conscious GMs avoid expensive contracts
            filtered = [
                a for a in filtered
                if a.asset_type == AssetType.DRAFT_PICK or
                   (a.annual_cap_hit is not None and a.annual_cap_hit <= 15_000_000)
            ]

        # Filter 2: Win-now mentality (exclude young/unproven if win-now)
        if self.gm.win_now_mentality > 0.7 and is_acquiring:
            # Win-now GMs only want proven veterans (age 25-32, or picks)
            filtered = [
                a for a in filtered
                if a.asset_type == AssetType.DRAFT_PICK or
                   (a.age is not None and 25 <= a.age <= 32)
            ]

        # Filter 3: Risk tolerance (conservative GMs avoid young players)
        if self.gm.risk_tolerance < 0.3 and is_acquiring:
            # Conservative GMs avoid risky young players
            filtered = [
                a for a in filtered
                if a.asset_type == AssetType.DRAFT_PICK or
                   (a.age is not None and a.age >= 25)
            ]

        return filtered

    def _calculate_asset_preference_score(self, asset: TradeAsset) -> float:
        """
        Calculate preference score for asset based on GM personality.

        Higher scores indicate stronger preference for this asset.
        Base score = 1.0, personality traits apply multipliers.

        Args:
            asset: Asset to score

        Returns:
            Preference score (0.5 - 2.0 range typically)
        """
        score = 1.0

        # Draft pick value preference
        if asset.asset_type == AssetType.DRAFT_PICK:
            # GMs who value picks highly give them higher scores
            if self.gm.draft_pick_value > 0.7:
                score *= 2.0  # Strong preference for picks
            elif self.gm.draft_pick_value < 0.3:
                score *= 0.5  # Weak preference for picks
        else:
            # Player-specific scoring
            # Star chasing (prefer elite players)
            if self.gm.star_chasing > 0.6 and asset.overall_rating and asset.overall_rating >= 88:
                score *= 1.5  # Prefer elite players

            # Veteran preference
            if asset.age:
                if self.gm.veteran_preference > 0.7 and asset.age >= 28:
                    score *= 1.3  # Prefer veterans
                elif self.gm.veteran_preference < 0.3 and asset.age <= 24:
                    score *= 1.3  # Prefer young players

            # Premium position focus
            if self.gm.premium_position_focus > 0.6:
                premium_positions = ["quarterback", "edge_rusher", "left_tackle", "cornerback"]
                if asset.position in premium_positions:
                    score *= 1.2  # Slight preference for premium positions

            # Team needs (if this position is a top need)
            if asset.position in self.team_context.top_needs:
                score *= 1.3  # Prefer assets that fill team needs

        return score

    def _is_duplicate_proposal(
        self,
        new_proposal: TradeProposal,
        history: List[TradeProposal]
    ) -> bool:
        """
        Check if proposal is duplicate of any previous proposal.

        Compares asset lists to detect if we're ping-ponging between
        identical offers (which would indicate a negotiation loop).

        Args:
            new_proposal: Proposed counter-offer
            history: List of previous proposals in negotiation

        Returns:
            True if new_proposal is duplicate of any in history
        """
        for past_proposal in history:
            if self._proposals_are_equivalent(new_proposal, past_proposal):
                return True
        return False

    def _proposals_are_equivalent(
        self,
        proposal1: TradeProposal,
        proposal2: TradeProposal
    ) -> bool:
        """
        Check if two proposals have identical assets.

        Args:
            proposal1: First proposal
            proposal2: Second proposal

        Returns:
            True if proposals have same assets on both sides
        """
        # Check team IDs match
        if (proposal1.team1_id != proposal2.team1_id or
            proposal1.team2_id != proposal2.team2_id):
            return False

        # Check asset counts match
        if (len(proposal1.team1_assets) != len(proposal2.team1_assets) or
            len(proposal1.team2_assets) != len(proposal2.team2_assets)):
            return False

        # Check team1 assets match (by player_id or draft pick details)
        team1_ids_1 = self._get_asset_identifiers(proposal1.team1_assets)
        team1_ids_2 = self._get_asset_identifiers(proposal2.team1_assets)
        if team1_ids_1 != team1_ids_2:
            return False

        # Check team2 assets match
        team2_ids_1 = self._get_asset_identifiers(proposal1.team2_assets)
        team2_ids_2 = self._get_asset_identifiers(proposal2.team2_assets)
        if team2_ids_1 != team2_ids_2:
            return False

        return True

    def _get_asset_identifiers(self, assets: List[TradeAsset]) -> set:
        """
        Get set of unique identifiers for assets.

        Args:
            assets: List of trade assets

        Returns:
            Set of tuples identifying each asset
        """
        identifiers = set()
        for asset in assets:
            if asset.asset_type == AssetType.PLAYER:
                identifiers.add(("PLAYER", asset.player_id))
            else:  # DRAFT_PICK
                identifiers.add((
                    "PICK",
                    asset.draft_pick.round,
                    asset.draft_pick.year,
                    asset.draft_pick.original_team_id
                ))
        return identifiers

    def _validate_counter_inputs(
        self,
        proposal: TradeProposal,
        decision: TradeDecision
    ) -> None:
        """
        Validate inputs for counter-offer generation.

        Args:
            proposal: Trade proposal to counter
            decision: Trade decision from evaluator

        Raises:
            ValueError: If inputs are invalid
            NegotiationStalemate: If counter-offer cannot be generated
        """
        # Check decision type
        if decision.decision != TradeDecisionType.COUNTER_OFFER:
            raise ValueError(
                f"Cannot generate counter-offer for {decision.decision.value} decision. "
                "Only COUNTER_OFFER decisions can have counters generated."
            )

        # Edge Case 1: Check for numerical stability (avoid division by zero)
        if proposal.team1_total_value <= 0 or proposal.team2_total_value <= 0:
            raise NegotiationStalemate(
                f"Cannot counter proposal with zero or negative values "
                f"(team1: {proposal.team1_total_value}, team2: {proposal.team2_total_value})"
            )

        # Edge Case 2: Verify perceived_value_ratio is present
        if decision.perceived_value_ratio is None:
            raise ValueError(
                "TradeDecision must have perceived_value_ratio for counter generation"
            )

        # Check all assets have trade_value
        all_assets = proposal.team1_assets + proposal.team2_assets
        for asset in all_assets:
            if asset.trade_value == 0.0:
                raise ValueError(
                    f"Asset {asset} has no trade_value. "
                    "Call TradeValueCalculator.evaluate_trade() first."
                )

        # Check decision has required fields
        if decision.perceived_value_ratio is None:
            raise ValueError("TradeDecision must have perceived_value_ratio populated")

        if decision.deciding_team_id is None:
            raise ValueError("TradeDecision must have deciding_team_id populated")

        if decision.deciding_team_id not in [proposal.team1_id, proposal.team2_id]:
            raise ValueError(
                f"deciding_team_id {decision.deciding_team_id} not in proposal teams "
                f"({proposal.team1_id}, {proposal.team2_id})"
            )

    def negotiate_until_convergence(
        self,
        initial_proposal: TradeProposal,
        team1_gm: GMArchetype,
        team1_context: TeamContext,
        team1_asset_pool: List[TradeAsset],
        team2_gm: GMArchetype,
        team2_context: TeamContext,
        team2_asset_pool: List[TradeAsset]
    ) -> NegotiationResult:
        """
        Run full multi-round negotiation between two teams.

        Alternates between teams evaluating and generating counter-offers until:
        - One team accepts the proposal (success)
        - Either team explicitly rejects (failure)
        - Maximum rounds reached (failure)
        - Stalemate detected - no progress being made (failure)

        Args:
            initial_proposal: Starting trade proposal
            team1_gm: Team 1's GM archetype
            team1_context: Team 1's context (record, cap, needs)
            team1_asset_pool: Assets team 1 can offer in counters
            team2_gm: Team 2's GM archetype
            team2_context: Team 2's context
            team2_asset_pool: Assets team 2 can offer in counters

        Returns:
            NegotiationResult with outcome, final proposal, and history

        Example:
            result = negotiator.negotiate_until_convergence(
                initial_proposal,
                lions_gm, lions_context, lions_assets,
                eagles_gm, eagles_context, eagles_assets
            )
            if result.success:
                execute_trade(result.final_proposal)
        """
        # Import TradeEvaluator here to avoid circular import
        from transactions.trade_evaluator import TradeEvaluator

        # Create evaluators and negotiators for both teams
        team1_evaluator = TradeEvaluator(team1_gm, team1_context, self.calculator)
        team2_evaluator = TradeEvaluator(team2_gm, team2_context, self.calculator)

        team1_negotiator = NegotiatorEngine(team1_gm, team1_context, self.calculator, team1_asset_pool)
        team2_negotiator = NegotiatorEngine(team2_gm, team2_context, self.calculator, team2_asset_pool)

        # Initialize negotiation state
        current_proposal = initial_proposal
        history = [initial_proposal]
        round_number = 0
        last_decision_team1 = None
        last_decision_team2 = None

        # Negotiation loop
        while round_number < self.MAX_ROUNDS:
            round_number += 1

            # Team 1 evaluates current proposal
            decision_team1 = team1_evaluator.evaluate_proposal(
                current_proposal,
                from_perspective_of=initial_proposal.team1_id
            )

            # Team 2 evaluates current proposal
            decision_team2 = team2_evaluator.evaluate_proposal(
                current_proposal,
                from_perspective_of=initial_proposal.team2_id
            )

            # Store decisions for final result
            last_decision_team1 = decision_team1
            last_decision_team2 = decision_team2

            # Check for mutual acceptance
            if decision_team1.is_accepted() and decision_team2.is_accepted():
                return NegotiationResult(
                    success=True,
                    final_proposal=current_proposal,
                    rounds_taken=round_number,
                    termination_reason="ACCEPTED",
                    history=history,
                    final_decision_team1=decision_team1,
                    final_decision_team2=decision_team2
                )

            # Check for explicit rejection from either team
            if decision_team1.is_rejected():
                return NegotiationResult(
                    success=False,
                    final_proposal=current_proposal,
                    rounds_taken=round_number,
                    termination_reason="REJECTED_TEAM1",
                    history=history,
                    final_decision_team1=decision_team1,
                    final_decision_team2=decision_team2
                )

            if decision_team2.is_rejected():
                return NegotiationResult(
                    success=False,
                    final_proposal=current_proposal,
                    rounds_taken=round_number,
                    termination_reason="REJECTED_TEAM2",
                    history=history,
                    final_decision_team1=decision_team1,
                    final_decision_team2=decision_team2
                )

            # One team accepts, one wants counter - accept wins
            if decision_team1.is_accepted() or decision_team2.is_accepted():
                return NegotiationResult(
                    success=True,
                    final_proposal=current_proposal,
                    rounds_taken=round_number,
                    termination_reason="ACCEPTED",
                    history=history,
                    final_decision_team1=decision_team1,
                    final_decision_team2=decision_team2
                )

            # Both teams want counter-offers - generate counter from team that's more unhappy
            # Priority: team with worse perceived ratio generates counter
            if decision_team1.is_counter() and decision_team2.is_counter():
                # Determine which team is more dissatisfied (further from 1.0 ratio)
                team1_dissatisfaction = abs(decision_team1.perceived_value_ratio - 1.0)
                team2_dissatisfaction = abs(decision_team2.perceived_value_ratio - 1.0)

                if team1_dissatisfaction >= team2_dissatisfaction:
                    # Team 1 generates counter
                    countering_team = "team1"
                    try:
                        counter_proposal = team1_negotiator.generate_counter_offer(
                            current_proposal, decision_team1, history
                        )
                    except NegotiationStalemate:
                        return NegotiationResult(
                            success=False,
                            final_proposal=current_proposal,
                            rounds_taken=round_number,
                            termination_reason="STALEMATE",
                            history=history,
                            final_decision_team1=decision_team1,
                            final_decision_team2=decision_team2
                        )
                else:
                    # Team 2 generates counter
                    countering_team = "team2"
                    try:
                        counter_proposal = team2_negotiator.generate_counter_offer(
                            current_proposal, decision_team2, history
                        )
                    except NegotiationStalemate:
                        return NegotiationResult(
                            success=False,
                            final_proposal=current_proposal,
                            rounds_taken=round_number,
                            termination_reason="STALEMATE",
                            history=history,
                            final_decision_team1=decision_team1,
                            final_decision_team2=decision_team2
                        )

            elif decision_team1.is_counter():
                # Only team 1 wants counter
                countering_team = "team1"
                try:
                    counter_proposal = team1_negotiator.generate_counter_offer(
                        current_proposal, decision_team1, history
                    )
                except NegotiationStalemate:
                    return NegotiationResult(
                        success=False,
                        final_proposal=current_proposal,
                        rounds_taken=round_number,
                        termination_reason="STALEMATE",
                        history=history,
                        final_decision_team1=decision_team1,
                        final_decision_team2=decision_team2
                    )

            elif decision_team2.is_counter():
                # Only team 2 wants counter
                countering_team = "team2"
                try:
                    counter_proposal = team2_negotiator.generate_counter_offer(
                        current_proposal, decision_team2, history
                    )
                except NegotiationStalemate:
                    return NegotiationResult(
                        success=False,
                        final_proposal=current_proposal,
                        rounds_taken=round_number,
                        termination_reason="STALEMATE",
                        history=history,
                        final_decision_team1=decision_team1,
                        final_decision_team2=decision_team2
                    )

            else:
                # Neither team wants counter (shouldn't happen, but handle gracefully)
                return NegotiationResult(
                    success=False,
                    final_proposal=current_proposal,
                    rounds_taken=round_number,
                    termination_reason="NO_COUNTER",
                    history=history,
                    final_decision_team1=decision_team1,
                    final_decision_team2=decision_team2
                )

            # Check for stalemate (no progress being made)
            if self._detect_stalemate(history, counter_proposal):
                return NegotiationResult(
                    success=False,
                    final_proposal=current_proposal,
                    rounds_taken=round_number,
                    termination_reason="STALEMATE",
                    history=history,
                    final_decision_team1=decision_team1,
                    final_decision_team2=decision_team2
                )

            # Move to next round with counter-proposal
            current_proposal = counter_proposal
            history.append(counter_proposal)

        # Max rounds reached
        return NegotiationResult(
            success=False,
            final_proposal=current_proposal,
            rounds_taken=round_number,
            termination_reason="MAX_ROUNDS",
            history=history,
            final_decision_team1=last_decision_team1,
            final_decision_team2=last_decision_team2
        )

    def _detect_stalemate(
        self,
        history: List[TradeProposal],
        new_proposal: TradeProposal
    ) -> bool:
        """
        Detect if negotiation has stalled (no meaningful progress).

        A stalemate is detected when:
        - Value gap is not shrinking by at least MIN_PROGRESS_RATIO (5%) per round
        - Last 2 proposals have very similar value ratios (oscillating)

        Args:
            history: List of previous proposals
            new_proposal: Latest counter-proposal

        Returns:
            True if stalemate detected, False otherwise
        """
        # Need at least 2 previous proposals to detect stalemate
        if len(history) < 2:
            return False

        # Get last proposal's ratio
        last_proposal = history[-1]
        last_ratio = last_proposal.value_ratio

        # Get second-to-last proposal's ratio
        second_last_proposal = history[-2]
        second_last_ratio = second_last_proposal.value_ratio

        new_ratio = new_proposal.value_ratio

        # Check 1: Is value gap shrinking toward 1.0?
        last_gap = abs(last_ratio - 1.0)
        new_gap = abs(new_ratio - 1.0)

        # If gap not shrinking by at least 5%, it's a stalemate
        if new_gap >= last_gap * (1.0 - self.MIN_PROGRESS_RATIO):
            return True  # No meaningful progress

        # Check 2: Are we oscillating between similar ratios?
        # If new ratio is very close to second-to-last ratio, we're ping-ponging
        ratio_similarity = abs(new_ratio - second_last_ratio)
        if ratio_similarity < 0.02:  # Within 2% of old ratio
            return True  # Oscillating, not converging

        return False
