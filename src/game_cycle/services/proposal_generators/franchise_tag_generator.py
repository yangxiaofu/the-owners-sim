"""
Franchise Tag Proposal Generator - GM analysis for tag recommendations.

Part of Tollgate 5: Franchise Tag Integration.

Analyzes expiring contracts and owner directives to generate a tag proposal.
Returns None if no tag is recommended.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from utils.player_field_extractors import extract_overall_rating
from game_cycle.models.owner_directives import OwnerDirectives
from game_cycle.models.persistent_gm_proposal import (
    PersistentGMProposal,
    create_franchise_tag_details,
)
from game_cycle.models.proposal_enums import ProposalType, ProposalStatus
from game_cycle.services.franchise_tag_service import FranchiseTagService


class FranchiseTagProposalGenerator:
    """
    Generates franchise tag proposal based on owner directives.

    Analyzes expiring contracts, scores candidates using directive-weighted
    formula, and generates human-readable reasoning.

    Returns None if:
    - Team already used tag
    - No expiring contracts
    - Best candidate scores below threshold
    - Cap situation prohibits tag
    """

    # Position value multipliers (premium positions worth more)
    POSITION_VALUE = {
        "QB": 2.0,
        "EDGE": 1.8,
        "DE": 1.8,
        "LT": 1.8,
        "RT": 1.7,
        "WR": 1.5,
        "CB": 1.5,
        "C": 1.4,
        "LB": 1.3,
        "MLB": 1.3,
        "LOLB": 1.3,
        "ROLB": 1.3,
        "S": 1.3,
        "FS": 1.3,
        "SS": 1.3,
        "TE": 1.2,
        "LG": 1.2,
        "RG": 1.2,
        "DT": 1.1,
        "RB": 1.0,
        "FB": 0.9,
        "K": 0.8,
        "P": 0.8,
        "LS": 0.7,
    }

    # Scoring thresholds
    MIN_SCORE_THRESHOLD = 60

    def __init__(
        self,
        db_path: str,
        dynasty_id: str,
        season: int,
        team_id: int,
        directives: OwnerDirectives,
    ):
        """
        Initialize the generator.

        Args:
            db_path: Path to game cycle database
            dynasty_id: Dynasty identifier
            season: Current season year
            team_id: User's team ID
            directives: Owner's strategic directives
        """
        self._db_path = db_path
        self._dynasty_id = dynasty_id
        self._season = season
        self._team_id = team_id
        self._directives = directives

        # Initialize underlying service
        self._tag_service = FranchiseTagService(db_path, dynasty_id, season)

    def generate_proposal(self) -> Optional[PersistentGMProposal]:
        """
        Analyze expiring contracts and generate tag proposal if warranted.

        Returns:
            PersistentGMProposal if tag recommended, None otherwise
        """
        # Check if team already used tag
        if self._tag_service.has_team_used_tag(self._team_id):
            return None

        # Get taggable players
        candidates = self._tag_service.get_taggable_players(self._team_id)
        if not candidates:
            return None

        # Score all candidates
        scored = [(player, self._score_candidate(player)) for player in candidates]
        scored.sort(key=lambda x: x[1], reverse=True)

        # Check if best candidate meets threshold
        best_player, best_score = scored[0]
        if best_score < self.MIN_SCORE_THRESHOLD:
            return None

        # Create proposal
        return self._create_proposal(best_player, best_score)

    def _score_candidate(self, player: Dict[str, Any]) -> float:
        """
        Score a tag candidate using directive-weighted formula.

        Scoring factors:
        - Base: player overall rating (0-100)
        - Position value multiplier (0.7-2.0)
        - Age adjustments (-15 to +10)
        - Priority position bonus (+7 to +15)
        - Protected player bonus (+25)
        - Expendable player penalty (-30)
        - Philosophy bonus/penalty (-10 to +10)
        - Budget stance penalty (-15 to +5)

        Args:
            player: Player dict from FranchiseTagService

        Returns:
            Float score (higher = better candidate)
        """
        overall = extract_overall_rating(player, default=0)
        position = player.get("position", "")
        age = player.get("age", 30)
        player_id = player.get("player_id")

        # Base score with position multiplier
        position_mult = self.POSITION_VALUE.get(position, 1.0)
        score = overall * position_mult

        # Age adjustments
        if age <= 26:
            score += 10  # Young prime player
        elif age <= 30:
            score += 5  # In prime
        elif age <= 32:
            score -= 5  # Entering decline
        else:
            score -= 15  # Veteran risk

        # Priority position bonus (15, 13, 11, 9, 7 based on rank)
        priority_positions = self._directives.priority_positions
        if position in priority_positions:
            priority_index = priority_positions.index(position)
            score += 15 - (priority_index * 2)

        # Protected player bonus
        if player_id in self._directives.protected_player_ids:
            score += 25

        # Expendable player penalty
        if player_id in self._directives.expendable_player_ids:
            score -= 30

        # Philosophy adjustments
        philosophy = self._directives.team_philosophy
        if philosophy == "win_now":
            score += 10  # Win-now values keeping core together
        elif philosophy == "rebuild":
            if age >= 28:
                score -= 10  # Rebuilding doesn't want to lock up veterans
            else:
                score += 5  # But young stars are building blocks

        # Budget stance adjustments
        budget = self._directives.budget_stance
        if budget == "aggressive":
            score += 5  # Willing to spend on talent
        elif budget == "conservative":
            score -= 15  # Reluctant to spend on expensive tag
            # Additional penalty for premium (expensive) positions
            if position in ["QB", "EDGE", "DE", "WR"]:
                score -= 10

        return max(0, score)  # Floor at 0

    def _create_proposal(
        self, player: Dict[str, Any], score: float
    ) -> PersistentGMProposal:
        """
        Create a PersistentGMProposal for the tag candidate.

        Args:
            player: Best candidate player dict
            score: Candidate's score

        Returns:
            PersistentGMProposal object
        """
        # Determine tag type (exclusive for protected/premium, non-exclusive otherwise)
        player_id = player.get("player_id")
        position = player.get("position", "")

        is_protected = player_id in self._directives.protected_player_ids
        is_premium = position in ["QB", "EDGE", "DE", "LT", "WR"]

        if is_protected or (is_premium and self._directives.team_philosophy == "win_now"):
            tag_type = "exclusive"
        else:
            tag_type = "non_exclusive"

        # Get tag cost
        tag_amount = player.get("franchise_tag_cost", 0)
        cap_impact = tag_amount  # 1-year deal, so cap impact = tag amount

        # Generate reasoning
        reasoning = self._generate_reasoning(player, score, cap_impact)

        # Calculate confidence from score (60-150 range maps to 0.5-0.95)
        confidence = min(0.95, max(0.5, 0.5 + (score - 60) / 200))

        # Create proposal
        details = create_franchise_tag_details(
            player_name=player.get("name", "Unknown"),
            position=position,
            tag_type=tag_type,
            tag_amount=tag_amount,
            cap_impact=cap_impact,
        )

        return PersistentGMProposal(
            dynasty_id=self._dynasty_id,
            team_id=self._team_id,
            season=self._season,
            stage="OFFSEASON_FRANCHISE_TAG",
            proposal_type=ProposalType.FRANCHISE_TAG,
            subject_player_id=str(player_id),
            details=details,
            gm_reasoning=reasoning,
            confidence=confidence,
            priority=100,  # High priority - single proposal per stage
            status=ProposalStatus.APPROVED,  # Default to approved - owner can reject
            created_at=datetime.now(),
        )

    def _generate_reasoning(
        self, player: Dict[str, Any], score: float, cap_impact: int
    ) -> str:
        """
        Generate human-readable reasoning for the tag proposal.

        Uses template-based reasoning that incorporates directive context.

        Args:
            player: Candidate player dict
            score: Candidate's score
            cap_impact: Cap space impact of tag

        Returns:
            Reasoning string
        """
        name = player.get("name", "Unknown")
        position = player.get("position", "")
        age = player.get("age", 0)
        overall = extract_overall_rating(player, default=0)
        player_id = player.get("player_id")

        philosophy = self._directives.team_philosophy
        budget = self._directives.budget_stance
        is_protected = player_id in self._directives.protected_player_ids
        is_priority = position in self._directives.priority_positions

        # Format tag amount
        tag_amount_str = f"${cap_impact / 1_000_000:.1f}M"

        # Select template based on context
        if philosophy == "win_now" and overall >= 80:
            return (
                f"{name} is a {position} entering free agency at age {age}. "
                f"At {overall} OVR, he's one of our most valuable players. "
                f"The franchise tag costs {tag_amount_str}, but preserves our ability "
                f"to negotiate long-term or trade him at the deadline. Given your "
                f"Win-Now directive, keeping our core together is essential for "
                f"a championship run."
            )

        if philosophy == "win_now" and is_protected:
            return (
                f"You've identified {name} as a protected player. At {age} years old "
                f"with {overall} OVR, losing him to free agency would set us back "
                f"significantly. The franchise tag ({tag_amount_str}) ensures we "
                f"control his future while pursuing your championship goals."
            )

        if philosophy == "rebuild" and age >= 27 and overall >= 75:
            return (
                f"{name} ({position}, {overall} OVR) has trade value as a veteran performer. "
                f"Tagging him at {tag_amount_str} lets us shop him before the deadline. "
                f"If we can't find a favorable deal, we can negotiate an extension or "
                f"let him walk next year. This aligns with our rebuilding approach while "
                f"preserving options."
            )

        if philosophy == "rebuild" and age <= 26 and overall >= 75:
            return (
                f"Even in a rebuild, {name} is worth keeping. At just {age} years old "
                f"with {overall} OVR at {position}, he's a building block for our future. "
                f"The franchise tag ({tag_amount_str}) secures him while we develop "
                f"around him."
            )

        if philosophy == "maintain" and is_priority:
            return (
                f"{name} plays {position}, one of your identified position priorities. "
                f"At {overall} OVR and {age} years old, he fills a key need. The franchise "
                f"tag costs {tag_amount_str} and gives us time to negotiate a fair extension."
            )

        # Default template
        return (
            f"{name} ({position}, {age} yo, {overall} OVR) is our top franchise tag "
            f"candidate. The franchise tag at {tag_amount_str} prevents him from testing "
            f"free agency while we work on long-term plans."
        )
