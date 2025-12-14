"""
Waiver Wire Proposal Generator - Generates waiver claim proposals based on owner directives.

Part of Tollgate 11: Waiver Wire Integration.

Uses existing WaiverService logic, converts results
to PersistentGMProposal objects for owner approval workflow.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from game_cycle.models.owner_directives import OwnerDirectives
from game_cycle.models.persistent_gm_proposal import (
    PersistentGMProposal,
    create_waiver_claim_details,
)
from game_cycle.models.proposal_enums import ProposalType, ProposalStatus


class WaiverProposalGenerator:
    """
    Generates waiver claim proposals based on owner directives.

    Uses existing WaiverService evaluation logic to identify claimable players,
    then creates PersistentGMProposal objects with:
    - Priority tier (TIER_HIGH_PRIORITY, TIER_MEDIUM_PRIORITY, TIER_LOW_PRIORITY)
    - Claim score based on quality, position need, success probability
    - Philosophy-based reasoning
    - Confidence from tier and success probability

    Philosophy mapping:
    - WIN_NOW → Claim proven veterans (age 26-30) who can contribute immediately
    - MAINTAIN → Balanced approach (all ages, OVR 70+)
    - REBUILD → Young upside players (age <27, OVR 65+) for future
    """

    # Priority tiers for waiver claims
    TIER_HIGH_PRIORITY = 1      # High need position + quality player + good claim chance
    TIER_MEDIUM_PRIORITY = 2    # Position need OR quality player + decent claim chance
    TIER_LOW_PRIORITY = 3       # Speculative claim or low success probability

    # Quality thresholds by budget approach
    QUALITY_THRESHOLDS = {
        "aggressive": 75,    # Only elite players
        "moderate": 70,      # Quality starters
        "conservative": 65,  # Any upgrade
    }

    # Minimum claim success probability to propose
    MIN_CLAIM_PROBABILITY = 0.20  # 20% chance or better

    # Maximum proposals to generate
    MAX_PROPOSALS = 5

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
            db_path: Path to database
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
        self._waiver_service = None  # Lazy-loaded
        self._team_priority = None   # Cached

    def _get_waiver_service(self):
        """Lazy-load WaiverService to avoid circular imports."""
        if self._waiver_service is None:
            from game_cycle.services.waiver_service import WaiverService

            self._waiver_service = WaiverService(
                db_path=self._db_path,
                dynasty_id=self._dynasty_id,
                season=self._season,
            )
        return self._waiver_service

    def _get_team_priority(self) -> int:
        """Get and cache team's waiver priority."""
        if self._team_priority is None:
            self._team_priority = self._get_waiver_service().get_team_priority(self._team_id)
        return self._team_priority

    def generate_proposals(
        self,
        available_players: List[Dict],
    ) -> List[PersistentGMProposal]:
        """
        Generate batch of waiver claim proposals.

        Args:
            available_players: List of players on waivers with details

        Returns:
            List of PersistentGMProposal sorted by priority tier
        """
        if not available_players:
            return []

        # Filter by quality threshold
        quality_threshold = self.QUALITY_THRESHOLDS.get(
            self._directives.budget_stance, 70
        )
        quality_players = [
            p for p in available_players
            if p.get("overall", 0) >= quality_threshold
        ]

        if not quality_players:
            return []

        # Score all candidates
        scored_candidates = []
        for player in quality_players:
            claim_score = self._score_claim_candidate(player)
            if claim_score >= 0:  # Any positive score is worth considering
                scored_candidates.append({
                    "player": player,
                    "claim_score": claim_score,
                })

        # Sort by claim score (descending - highest score = best claim)
        scored_candidates.sort(key=lambda x: x["claim_score"], reverse=True)

        # Select top N (limit to MAX_PROPOSALS)
        top_candidates = scored_candidates[:self.MAX_PROPOSALS]

        # Create proposals
        proposals = []
        for item in top_candidates:
            player = item["player"]
            claim_score = item["claim_score"]

            # Calculate claim success probability
            success_prob = self._calculate_claim_success_probability(player)

            # Skip if success probability too low
            if success_prob < self.MIN_CLAIM_PROBABILITY:
                continue

            # Get tier
            tier = self._get_priority_tier(player, claim_score, success_prob)

            # Generate reasoning
            reasoning = self._generate_reasoning(
                player=player,
                claim_score=claim_score,
                tier=tier,
                success_prob=success_prob,
            )

            # Create proposal
            proposal = self._create_proposal(
                player=player,
                claim_score=claim_score,
                tier=tier,
                reasoning=reasoning,
                success_prob=success_prob,
            )

            proposals.append(proposal)

        # Sort by priority tier (ascending - lower tier = higher priority)
        proposals.sort(key=lambda p: p.priority)

        return proposals

    def _score_claim_candidate(self, player: Dict) -> float:
        """
        Score player for waiver claim candidacy (higher = better claim).

        Factors:
        - Player quality (overall rating)
        - Position need (priority positions get bonus)
        - Age fit (philosophy-based)
        - Claim success probability
        - Directive adjustments

        Args:
            player: Player data dict

        Returns:
            Claim score (higher = more valuable claim)
        """
        overall = player.get("overall", 0)
        age = player.get("age", 25)
        position = player.get("position", "")

        # Base score from quality (0-100 range)
        quality_score = overall * 1.0

        # Position need bonus
        position_bonus = 0.0
        if position in self._directives.priority_positions:
            # Higher bonus for higher priority (first position = +20, second = +15, etc.)
            priority_rank = self._directives.priority_positions.index(position)
            position_bonus = 20.0 - (priority_rank * 5.0)
            position_bonus = max(0.0, position_bonus)  # Don't go negative

        # Philosophy-based age adjustments
        philosophy = self._directives.team_philosophy
        age_adjustment = 0.0

        if philosophy == "win_now":
            # WIN_NOW: Prefer proven veterans (26-30)
            if 26 <= age <= 30:
                age_adjustment = 15.0
            elif age > 30:
                age_adjustment = -10.0  # Too old
            elif age < 24:
                age_adjustment = -5.0   # Too young/unproven
        elif philosophy == "rebuild":
            # REBUILD: Young players with upside
            if age < 27:
                age_adjustment = 15.0
            elif age >= 30:
                age_adjustment = -15.0  # Doesn't fit timeline
        else:  # maintain
            # MAINTAIN: Balanced, slight preference for prime years
            if 25 <= age <= 29:
                age_adjustment = 10.0

        # Claim success probability factor
        success_prob = self._calculate_claim_success_probability(player)
        prob_adjustment = success_prob * 20.0  # Up to +20 for guaranteed claim

        # Budget stance adjustments
        if self._directives.budget_stance == "aggressive":
            # Aggressive: only claim elite players
            if overall < 75:
                quality_score *= 0.5  # Penalize non-elite
        elif self._directives.budget_stance == "conservative":
            # Conservative: value any upgrade
            quality_score *= 1.1  # Small bonus for being conservative

        total_score = (
            quality_score +
            position_bonus +
            age_adjustment +
            prob_adjustment
        )

        return total_score

    def _calculate_claim_success_probability(self, player: Dict) -> float:
        """
        Calculate probability of successfully claiming this player.

        Factors:
        - Team's waiver priority (1 = 100%, 32 = ~10%)
        - Player quality (better players = more competition)

        Args:
            player: Player data dict

        Returns:
            Probability between 0.0 and 1.0
        """
        team_priority = self._get_team_priority()
        overall = player.get("overall", 70)

        # Base probability from priority
        # Priority 1 = 95%, Priority 16 = 50%, Priority 32 = 10%
        base_prob = max(0.10, 1.0 - ((team_priority - 1) / 31) * 0.85)

        # Adjust for player quality (elite players = more competition)
        if overall >= 80:
            # Elite player - expect 5-10 teams to claim
            competition_factor = 0.3  # 30% of base probability
        elif overall >= 75:
            # Quality starter - expect 3-5 teams to claim
            competition_factor = 0.5  # 50% of base probability
        elif overall >= 70:
            # Solid depth - expect 1-3 teams to claim
            competition_factor = 0.7  # 70% of base probability
        else:
            # Low competition
            competition_factor = 0.9  # 90% of base probability

        return base_prob * competition_factor

    def _get_priority_tier(self, player: Dict, claim_score: float, success_prob: float) -> int:
        """
        Determine priority tier based on claim score and context.

        Args:
            player: Player data dict
            claim_score: Calculated claim score
            success_prob: Claim success probability

        Returns:
            Priority tier (1=HIGH, 2=MEDIUM, 3=LOW)
        """
        position = player.get("position", "")
        overall = player.get("overall", 70)

        # TIER_HIGH_PRIORITY: Top 2 priority positions + quality + good chance
        if position in self._directives.priority_positions[:2]:  # Top 2 positions
            if overall >= 75 and success_prob >= 0.5:
                return self.TIER_HIGH_PRIORITY

        # TIER_MEDIUM_PRIORITY: Position need OR quality + decent chance
        if position in self._directives.priority_positions:
            if success_prob >= 0.3:
                return self.TIER_MEDIUM_PRIORITY

        if overall >= 75 and success_prob >= 0.4:
            return self.TIER_MEDIUM_PRIORITY

        # TIER_LOW_PRIORITY: Everything else
        return self.TIER_LOW_PRIORITY

    def _calculate_confidence(self, claim_score: float, tier: int, success_prob: float) -> float:
        """
        Calculate confidence from claim score, tier, and success probability.

        Higher scores + higher tiers + higher success prob = higher confidence.
        TIER_HIGH_PRIORITY = 0.75-0.90
        TIER_MEDIUM_PRIORITY = 0.60-0.75
        TIER_LOW_PRIORITY = 0.50-0.65

        Args:
            claim_score: Calculated claim score
            tier: Priority tier
            success_prob: Claim success probability

        Returns:
            Confidence value between 0.5 and 0.90
        """
        # Base confidence from tier
        tier_base = {
            self.TIER_HIGH_PRIORITY: 0.75,
            self.TIER_MEDIUM_PRIORITY: 0.60,
            self.TIER_LOW_PRIORITY: 0.50,
        }.get(tier, 0.50)

        # Bonus from success probability
        prob_bonus = success_prob * 0.10  # Up to +10% for guaranteed claim

        # Bonus from claim score (normalized)
        score_bonus = min(0.05, (claim_score / 100) * 0.05)

        confidence = tier_base + prob_bonus + score_bonus
        return min(0.90, max(0.50, confidence))

    def _generate_reasoning(
        self,
        player: Dict,
        claim_score: float,
        tier: int,
        success_prob: float,
    ) -> str:
        """
        Generate philosophy-specific reasoning for the waiver claim.

        Args:
            player: Player data dict
            claim_score: Calculated claim score
            tier: Priority tier
            success_prob: Claim success probability

        Returns:
            Human-readable reasoning string
        """
        name = player.get("name", f"Player {player.get('player_id', '?')}")
        position = player.get("position", "")
        age = player.get("age", 0)
        overall = player.get("overall", 0)
        team_priority = self._get_team_priority()

        philosophy = self._directives.team_philosophy

        # Tier-specific reasoning templates
        if tier == self.TIER_HIGH_PRIORITY:
            reasoning = self._high_priority_reasoning(
                name, position, age, overall, success_prob, team_priority
            )
        elif tier == self.TIER_MEDIUM_PRIORITY:
            if philosophy == "win_now":
                reasoning = self._win_now_claim_reasoning(
                    name, position, age, overall, success_prob, team_priority
                )
            elif philosophy == "rebuild":
                reasoning = self._rebuild_claim_reasoning(
                    name, position, age, overall, success_prob, team_priority
                )
            else:  # maintain
                reasoning = self._maintain_claim_reasoning(
                    name, position, age, overall, success_prob, team_priority
                )
        else:  # TIER_LOW_PRIORITY
            reasoning = self._low_priority_reasoning(
                name, position, age, overall, success_prob, team_priority
            )

        # Add score breakdown
        reasoning += f"\n\nClaim Score: {claim_score:.1f}"
        reasoning += f"\nWaiver Priority: #{team_priority} (Success Probability: {success_prob*100:.0f}%)"

        # Add position need level
        if position in self._directives.priority_positions[:2]:
            need_level = "HIGH"
        elif position in self._directives.priority_positions:
            need_level = "MEDIUM"
        else:
            need_level = "LOW"
        reasoning += f"\nPosition Need: {need_level}"

        return reasoning

    def _high_priority_reasoning(
        self, name: str, position: str, age: int, overall: int,
        success_prob: float, team_priority: int
    ) -> str:
        """Generate HIGH_PRIORITY tier reasoning."""
        reasoning = f"HIGH PRIORITY CLAIM: {name} ({position}, {age}yo, {overall} OVR)\n\n"
        reasoning += f"{name} addresses a critical need at {position} and represents "
        reasoning += f"an immediate roster upgrade. At {overall} overall, this is a quality starter "
        reasoning += f"who can contribute right away. "
        reasoning += f"With our #{team_priority} waiver priority, we have a {success_prob*100:.0f}% "
        reasoning += f"chance to land this player. This is a strong value claim that fits our needs."
        return reasoning

    def _win_now_claim_reasoning(
        self, name: str, position: str, age: int, overall: int,
        success_prob: float, team_priority: int
    ) -> str:
        """Generate WIN_NOW philosophy claim reasoning."""
        reasoning = f"WIN-NOW WAIVER CLAIM: {name} ({position}, {age}yo, {overall} OVR)\n\n"
        reasoning += "Following your championship window directive, we're targeting proven veterans "
        reasoning += f"who can contribute immediately. {name} at {age} years old is in "
        reasoning += f"{'prime years' if 26 <= age <= 30 else 'their career peak'} and brings "
        reasoning += f"{overall} overall rating to our roster. "
        reasoning += f"Our #{team_priority} waiver priority gives us a {success_prob*100:.0f}% chance. "
        reasoning += "This claim supports our push for a title run."
        return reasoning

    def _rebuild_claim_reasoning(
        self, name: str, position: str, age: int, overall: int,
        success_prob: float, team_priority: int
    ) -> str:
        """Generate REBUILD philosophy claim reasoning."""
        reasoning = f"REBUILD WAIVER CLAIM: {name} ({position}, {age}yo, {overall} OVR)\n\n"
        reasoning += "Following your rebuild directive, we're prioritizing young talent with upside. "
        reasoning += f"{name} at {age} years old fits our timeline for contention and shows "
        reasoning += f"promising development at {overall} overall. "
        reasoning += f"With #{team_priority} waiver priority ({success_prob*100:.0f}% success rate), "
        reasoning += "this is a smart claim that builds for the future without sacrificing draft capital."
        return reasoning

    def _maintain_claim_reasoning(
        self, name: str, position: str, age: int, overall: int,
        success_prob: float, team_priority: int
    ) -> str:
        """Generate MAINTAIN philosophy claim reasoning."""
        reasoning = f"BALANCED WAIVER CLAIM: {name} ({position}, {age}yo, {overall} OVR)\n\n"
        reasoning += "Following your balanced approach, this claim provides solid roster depth "
        reasoning += f"without overcommitting resources. {name} grades at {overall} overall and "
        reasoning += f"offers {'proven production' if age >= 27 else 'upside potential'} at {position}. "
        reasoning += f"Our #{team_priority} waiver priority provides {success_prob*100:.0f}% success chance. "
        reasoning += "This is a value claim that maintains roster competitiveness."
        return reasoning

    def _low_priority_reasoning(
        self, name: str, position: str, age: int, overall: int,
        success_prob: float, team_priority: int
    ) -> str:
        """Generate LOW_PRIORITY tier reasoning."""
        reasoning = f"SPECULATIVE CLAIM: {name} ({position}, {age}yo, {overall} OVR)\n\n"
        reasoning += f"This is a low-risk waiver claim with {success_prob*100:.0f}% success probability "
        reasoning += f"at our #{team_priority} priority. {name} provides depth at {position} "
        reasoning += f"and may develop into a contributor. While not a critical need, "
        reasoning += "this claim adds roster flexibility at minimal cost."
        return reasoning

    def _create_proposal(
        self,
        player: Dict,
        claim_score: float,
        tier: int,
        reasoning: str,
        success_prob: float,
    ) -> PersistentGMProposal:
        """
        Create PersistentGMProposal using create_waiver_claim_details.

        Args:
            player: Player data dict
            claim_score: Calculated claim score
            tier: Priority tier
            reasoning: Generated reasoning
            success_prob: Claim success probability

        Returns:
            PersistentGMProposal for this waiver claim
        """
        name = player.get("name", f"Player {player.get('player_id', '?')}")
        position = player.get("position", "")
        age = player.get("age", 0)
        overall = player.get("overall", 0)
        waiver_priority = self._get_team_priority()

        # Estimate contract remaining (simplified - actual values from player contract)
        # Most waiver players are on rookie deals or cheap veteran contracts
        contract_remaining = {
            "years": player.get("contract_years_left", 1),
            "total": player.get("contract_value_left", 1_000_000),
        }

        # Create details using helper
        details = create_waiver_claim_details(
            player_name=name,
            position=position,
            age=age,
            overall_rating=overall,
            waiver_priority=waiver_priority,
            contract_remaining=contract_remaining,
        )

        # Add execution fields
        details["player_id"] = player.get("player_id")
        details["success_probability"] = success_prob
        details["claim_score"] = claim_score

        # Calculate confidence
        confidence = self._calculate_confidence(claim_score, tier, success_prob)

        return PersistentGMProposal(
            dynasty_id=self._dynasty_id,
            team_id=self._team_id,
            season=self._season,
            stage="OFFSEASON_WAIVER_WIRE",
            proposal_type=ProposalType.WAIVER_CLAIM,
            subject_player_id=str(player.get("player_id", "")),
            details=details,
            gm_reasoning=reasoning,
            confidence=confidence,
            priority=tier,  # Use tier directly as priority
            status=ProposalStatus.PENDING,
            created_at=datetime.now(),
        )
