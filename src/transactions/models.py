"""
Trade Value Calculator Data Models

Defines data structures for draft picks, trade assets, and complete trade proposals.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, List


@dataclass
class DraftPick:
    """Represents a tradeable NFL draft pick"""

    round: int  # 1-7
    year: int   # Draft year (current or future)
    original_team_id: int  # Team that originally owned this pick
    current_team_id: int   # Team that currently owns it

    # For value calculation
    overall_pick_projected: Optional[int] = None  # 1-262 based on standings
    projected_range_min: Optional[int] = None     # Uncertainty range
    projected_range_max: Optional[int] = None

    # Metadata
    is_compensatory: bool = False
    is_conditional: bool = False  # Future enhancement

    def __post_init__(self):
        """Validate pick data"""
        if not 1 <= self.round <= 7:
            raise ValueError(f"Round must be 1-7, got {self.round}")

        if self.overall_pick_projected:
            if not 1 <= self.overall_pick_projected <= 262:
                raise ValueError(
                    f"Overall pick must be 1-262, got {self.overall_pick_projected}"
                )

    def estimate_overall_pick(self, team_wins: int, team_losses: int) -> int:
        """
        Estimate overall pick number based on team record.

        Args:
            team_wins: Current wins
            team_losses: Current losses

        Returns:
            Estimated overall pick number (1-262)
        """
        # Calculate draft position within round based on record
        # Worst record = pick 1, best record = pick 32
        total_games = team_wins + team_losses
        win_percentage = team_wins / total_games if total_games > 0 else 0.5

        # Position in round (1-32, worst team = 1, best team = 32)
        # Inverse win percentage so 0% wins = pick 1, 100% wins = pick 32
        position_in_round = int(win_percentage * 31) + 1
        position_in_round = max(1, min(32, position_in_round))

        # Calculate overall pick
        overall = (self.round - 1) * 32 + position_in_round

        self.overall_pick_projected = overall

        # Set uncertainty range (±3 picks for current year, ±10 for future)
        years_out = self.year - 2025  # Assuming 2025 is current
        uncertainty = 3 if years_out == 0 else 10
        self.projected_range_min = max(1, overall - uncertainty)
        self.projected_range_max = min(262, overall + uncertainty)

        return overall

    def __str__(self) -> str:
        """Human-readable representation"""
        year_suffix = f" ({self.year})" if self.year else ""
        if self.overall_pick_projected:
            return f"Round {self.round} Pick #{self.overall_pick_projected}{year_suffix}"
        else:
            return f"Round {self.round}{year_suffix}"


class AssetType(Enum):
    """Type of trade asset"""
    PLAYER = "PLAYER"
    DRAFT_PICK = "DRAFT_PICK"


@dataclass
class TradeAsset:
    """Union type for players or draft picks in trades"""

    asset_type: AssetType

    # Player data (populated if asset_type == PLAYER)
    player_id: Optional[int] = None
    player_name: Optional[str] = None
    position: Optional[str] = None
    overall_rating: Optional[int] = None
    age: Optional[int] = None
    years_pro: Optional[int] = None
    contract_years_remaining: Optional[int] = None
    annual_cap_hit: Optional[int] = None
    total_remaining_guaranteed: Optional[int] = None

    # Pick data (populated if asset_type == DRAFT_PICK)
    draft_pick: Optional[DraftPick] = None

    # Calculated trade value (in arbitrary units)
    trade_value: float = 0.0

    # Context for valuation
    acquiring_team_id: Optional[int] = None  # Team receiving this asset

    def __post_init__(self):
        """Validate asset data"""
        if self.asset_type == AssetType.PLAYER:
            if not self.player_id and not self.player_name:
                raise ValueError("Player assets must have player_id or player_name")
        elif self.asset_type == AssetType.DRAFT_PICK:
            # Allow draft pick assets without draft_pick if trade_value is provided
            # (for testing and manual value specification)
            if not self.draft_pick and self.trade_value == 0.0:
                raise ValueError("Draft pick assets must have draft_pick or trade_value")

    def __str__(self) -> str:
        """Human-readable representation"""
        if self.asset_type == AssetType.PLAYER:
            name = self.player_name or f"Player #{self.player_id}"
            details = []
            if self.position:
                details.append(self.position.upper())
            if self.overall_rating:
                details.append(f"{self.overall_rating} OVR")
            if self.age:
                details.append(f"Age {self.age}")

            detail_str = ", ".join(details) if details else "Unknown"
            return f"{name} ({detail_str})"
        else:
            return str(self.draft_pick)


class FairnessRating(Enum):
    """Trade fairness evaluation"""
    VERY_FAIR = "VERY_FAIR"              # 0.95-1.05
    FAIR = "FAIR"                        # 0.80-0.95 or 1.05-1.20
    SLIGHTLY_UNFAIR = "SLIGHTLY_UNFAIR"  # 0.70-0.80 or 1.20-1.30
    VERY_UNFAIR = "VERY_UNFAIR"          # <0.70 or >1.30


class TradeDecisionType(Enum):
    """GM's decision on a trade proposal"""
    ACCEPT = "ACCEPT"              # Accept trade as-is
    REJECT = "REJECT"              # Reject trade outright
    COUNTER_OFFER = "COUNTER_OFFER"  # Make counter-proposal


@dataclass
class TradeProposal:
    """Complete trade package with valuation and validation"""

    # Team 1 (proposing team)
    team1_id: int
    team1_assets: List[TradeAsset]
    team1_total_value: float

    # Team 2 (receiving proposal)
    team2_id: int
    team2_assets: List[TradeAsset]
    team2_total_value: float

    # Fairness evaluation
    value_ratio: float  # team2_total / team1_total (1.0 = perfectly fair)
    fairness_rating: FairnessRating

    # Validation flags
    passes_cap_validation: bool = False
    passes_roster_validation: bool = False

    # Cap space after trade
    team1_cap_space_after: Optional[int] = None
    team2_cap_space_after: Optional[int] = None

    # Metadata
    proposed_date: Optional[str] = None
    initiating_team_id: Optional[int] = None

    @classmethod
    def calculate_fairness(cls, ratio: float) -> FairnessRating:
        """
        Determine fairness rating from value ratio.

        Args:
            ratio: team2_total_value / team1_total_value

        Returns:
            FairnessRating enum value
        """
        if 0.95 <= ratio <= 1.05:
            return FairnessRating.VERY_FAIR
        elif 0.80 <= ratio <= 1.20:
            return FairnessRating.FAIR
        elif 0.70 <= ratio <= 1.30:
            return FairnessRating.SLIGHTLY_UNFAIR
        else:
            return FairnessRating.VERY_UNFAIR

    def is_acceptable(self) -> bool:
        """
        Check if trade is acceptable (fair enough to execute).

        Returns:
            True if trade is VERY_FAIR or FAIR
        """
        return self.fairness_rating in [FairnessRating.VERY_FAIR, FairnessRating.FAIR]

    def get_summary(self) -> str:
        """
        Get human-readable trade summary.

        Returns:
            Multi-line string with trade details
        """
        team1_assets_str = ", ".join(str(a) for a in self.team1_assets)
        team2_assets_str = ", ".join(str(a) for a in self.team2_assets)

        summary_lines = [
            "TRADE PROPOSAL:",
            f"Team {self.team1_id} sends: {team1_assets_str}",
            f"  Total Value: {self.team1_total_value:.1f} units",
            f"Team {self.team2_id} sends: {team2_assets_str}",
            f"  Total Value: {self.team2_total_value:.1f} units",
            f"",
            f"Value Ratio: {self.value_ratio:.3f} ({self.fairness_rating.value})",
            f"Acceptable: {'✓ YES' if self.is_acceptable() else '✗ NO'}",
        ]

        return "\n".join(summary_lines)

    def get_value_difference(self) -> float:
        """
        Calculate absolute value difference between teams.

        Returns:
            Positive float representing value gap
        """
        return abs(self.team1_total_value - self.team2_total_value)

    def get_winning_team(self) -> Optional[int]:
        """
        Determine which team gets better value (if unfair).

        Returns:
            Team ID of "winning" team, or None if fair
        """
        if self.is_acceptable():
            return None

        if self.team1_total_value > self.team2_total_value:
            return self.team1_id
        else:
            return self.team2_id


@dataclass
class TradeDecision:
    """
    GM's decision on a trade proposal with reasoning and optional counter-offer.

    Represents the output of AI trade decision-making logic, including
    the decision type (accept/reject/counter), confidence level, and
    human-readable reasoning.
    """

    # Decision outcome
    decision: TradeDecisionType

    # Human-readable explanation
    reasoning: str

    # Confidence level (0.0-1.0)
    # 0.0-0.3: Low confidence (borderline decision)
    # 0.3-0.7: Moderate confidence
    # 0.7-1.0: High confidence (clear decision)
    confidence: float

    # Original proposal being evaluated
    original_proposal: TradeProposal

    # Counter-offer (populated if decision == COUNTER_OFFER)
    counter_offer: Optional[TradeProposal] = None

    # GM making the decision
    deciding_team_id: Optional[int] = None
    deciding_gm_name: Optional[str] = None

    # Value analysis
    perceived_value_ratio: Optional[float] = None  # After personality modifiers
    objective_value_ratio: Optional[float] = None  # Before modifiers

    def __post_init__(self):
        """Validate decision data"""
        # Validate confidence
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be 0.0-1.0, got {self.confidence}")

        # Validate counter-offer presence
        # Note: counter_offer can be None for COUNTER_OFFER decisions (not yet implemented)
        # Future enhancement will populate counter_offer for COUNTER_OFFER decisions
        if self.decision != TradeDecisionType.COUNTER_OFFER and self.counter_offer:
            raise ValueError(f"Non-COUNTER_OFFER decision should not have counter_offer")

    def is_accepted(self) -> bool:
        """Check if trade was accepted"""
        return self.decision == TradeDecisionType.ACCEPT

    def is_rejected(self) -> bool:
        """Check if trade was rejected"""
        return self.decision == TradeDecisionType.REJECT

    def is_counter(self) -> bool:
        """Check if GM made counter-offer"""
        return self.decision == TradeDecisionType.COUNTER_OFFER

    def get_summary(self) -> str:
        """
        Get human-readable decision summary.

        Returns:
            Multi-line string with decision details
        """
        lines = [
            f"TRADE DECISION: {self.decision.value}",
            f"Confidence: {self.confidence:.1%}",
            f"",
            f"REASONING:",
            f"{self.reasoning}",
        ]

        if self.perceived_value_ratio and self.objective_value_ratio:
            lines.extend([
                f"",
                f"VALUE ANALYSIS:",
                f"  Objective Ratio: {self.objective_value_ratio:.3f}",
                f"  Perceived Ratio: {self.perceived_value_ratio:.3f}",
                f"  Personality Adjustment: {(self.perceived_value_ratio / self.objective_value_ratio):.2f}x"
            ])

        if self.counter_offer:
            lines.extend([
                f"",
                f"COUNTER-OFFER:",
                self.counter_offer.get_summary()
            ])

        return "\n".join(lines)


class NegotiationStalemate(Exception):
    """
    Raised when trade negotiation cannot proceed.

    This exception is raised when:
    - No viable counter-offer can be generated
    - Asset pool is exhausted
    - Value gap cannot be bridged with available assets
    """
    pass


@dataclass
class NegotiationResult:
    """
    Result of multi-round trade negotiation between two teams.

    Represents the outcome of a complete negotiation session, including
    whether agreement was reached, the final proposal, number of rounds,
    and complete negotiation history.
    """

    # Outcome
    success: bool  # True if negotiation ended in accepted proposal

    # Final state
    final_proposal: Optional[TradeProposal]  # Last proposal (None if failed early)
    rounds_taken: int  # Number of negotiation rounds completed

    # Termination information
    termination_reason: str  # "ACCEPTED", "MAX_ROUNDS", "STALEMATE", "REJECTED"

    # History
    history: List[TradeProposal]  # All proposals in chronological order

    # Final decisions (if available)
    final_decision_team1: Optional[TradeDecision] = None
    final_decision_team2: Optional[TradeDecision] = None

    def get_summary(self) -> str:
        """
        Get human-readable negotiation summary.

        Returns:
            Multi-line string with negotiation outcome and statistics
        """
        lines = [
            f"NEGOTIATION RESULT:",
            f"Success: {'✓ YES' if self.success else '✗ NO'}",
            f"Rounds: {self.rounds_taken}",
            f"Termination: {self.termination_reason}",
            f""
        ]

        if self.final_proposal:
            lines.extend([
                f"FINAL PROPOSAL:",
                self.final_proposal.get_summary()
            ])

        if self.history:
            lines.extend([
                f"",
                f"NEGOTIATION HISTORY ({len(self.history)} proposals):"
            ])
            for i, proposal in enumerate(self.history):
                lines.append(f"  Round {i}: Ratio {proposal.value_ratio:.3f}")

        return "\n".join(lines)
