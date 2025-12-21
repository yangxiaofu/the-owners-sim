"""
Roster Cuts Proposal Generator - Generates roster cut proposals to reach 53-man roster.

Part of Tollgate 10: Roster Cuts Integration.

Uses existing RosterCutsService logic, converts results
to PersistentGMProposal objects for owner approval workflow.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from utils.player_field_extractors import extract_overall_rating
from game_cycle.models.owner_directives import OwnerDirectives
from game_cycle.models.persistent_gm_proposal import (
    PersistentGMProposal,
    create_cut_details,
)
from game_cycle.models.proposal_enums import ProposalType, ProposalStatus


class RosterCutsProposalGenerator:
    """
    Generates roster cut proposals based on owner directives.

    Uses existing RosterCutsService evaluation logic to identify cut candidates,
    then creates PersistentGMProposal objects with:
    - Priority tier (MUST_CUT, PHILOSOPHY, DEPTH, CAP_RELIEF)
    - Cut score based on cap hit, overall rating, age, dead money ratio
    - Philosophy-based reasoning
    - Confidence from tier and score

    Philosophy mapping:
    - WIN_NOW → Keep young talent (age < 27), cut expensive depth
    - MAINTAIN → Balance dead money vs cap savings
    - REBUILD → Cut expensive veterans (age 30+), preserve young players
    """

    # Priority tiers for cut candidates
    TIER_MUST_CUT = 1        # Excessive cap hit + low value (>$5M cap hit, <65 OVR)
    TIER_PHILOSOPHY = 2       # Philosophy-aligned cuts
    TIER_DEPTH = 3           # Replacement available at position
    TIER_CAP_RELIEF = 4      # General cap optimization

    # Scoring thresholds
    MIN_CUT_SCORE = 10.0          # Minimum score to propose cut
    HIGH_CAP_HIT_THRESHOLD = 5_000_000  # $5M+ considered high
    LOW_OVERALL_THRESHOLD = 65    # Below this considered low value

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
        self._cuts_service = None  # Lazy-loaded

    def _get_cuts_service(self):
        """Lazy-load RosterCutsService to avoid circular imports."""
        if self._cuts_service is None:
            from game_cycle.services.roster_cuts_service import RosterCutsService

            self._cuts_service = RosterCutsService(
                db_path=self._db_path,
                dynasty_id=self._dynasty_id,
                season=self._season,
            )
        return self._cuts_service

    def generate_proposals(
        self,
        roster: List[Dict],
        cuts_needed: int,
    ) -> List[PersistentGMProposal]:
        """
        Generate batch of cut proposals.

        Args:
            roster: Full roster with ratings, contracts, value scores
            cuts_needed: Number of cuts needed to reach 53-man roster

        Returns:
            List of PersistentGMProposal sorted by priority tier
        """
        if cuts_needed <= 0:
            return []

        # Filter out protected players
        protected_ids = set(self._directives.protected_player_ids)
        cuttable = [
            p for p in roster
            if p.get("player_id") not in protected_ids
        ]

        if not cuttable:
            raise ValueError("No cuttable players available (all protected)")

        # Score all candidates
        scored_candidates = []
        for player in cuttable:
            cut_score = self._score_cut_candidate(player)
            if cut_score >= self.MIN_CUT_SCORE:
                scored_candidates.append({
                    "player": player,
                    "cut_score": cut_score,
                })

        # Sort by cut score (descending - highest score = most cut-worthy)
        scored_candidates.sort(key=lambda x: x["cut_score"], reverse=True)

        # Select top N
        top_candidates = scored_candidates[:cuts_needed]

        # Create proposals
        proposals = []
        for item in top_candidates:
            player = item["player"]
            cut_score = item["cut_score"]

            # Get tier
            tier = self._get_priority_tier(player, cut_score)

            # Calculate cap impact
            cap_hit = player.get("cap_hit", 0)
            dead_money = player.get("dead_money", 0)
            cap_savings = max(0, cap_hit - dead_money)

            # Generate reasoning
            reasoning = self._generate_reasoning(
                player=player,
                cut_score=cut_score,
                tier=tier,
                cap_savings=cap_savings,
                dead_money=dead_money,
            )

            # Create proposal
            proposal = self._create_proposal(
                player=player,
                cut_score=cut_score,
                tier=tier,
                reasoning=reasoning,
            )

            proposals.append(proposal)

        # Sort by priority tier (ascending - lower tier = higher priority)
        proposals.sort(key=lambda p: p.priority)

        return proposals

    def _score_cut_candidate(self, player: Dict) -> float:
        """
        Score player for cut candidacy (higher = more likely to cut).

        Factors:
        - Cap hit (higher = cut)
        - Overall rating (lower = cut)
        - Age (older = cut)
        - Dead money ratio (higher ratio = avoid cut)
        - Directive adjustments (protected, expendable, priority pos, philosophy)

        Args:
            player: Player data dict

        Returns:
            Cut score (higher = more cut-worthy)
        """
        cap_hit = player.get("cap_hit", 0)
        overall = extract_overall_rating(player, default=70)
        age = player.get("age", 25)
        dead_money = player.get("dead_money", 0)
        position = player.get("position", "")

        # Base score
        cap_hit_score = (cap_hit / 1_000_000) * 0.5  # Higher cap = cut
        overall_score = (70 - overall) * 1.0         # Lower overall = cut

        # Age penalty (accelerates after 30)
        if age >= 30:
            age_penalty = (age - 30) * 2.0
        else:
            age_penalty = 0.0

        # Dead money penalty (avoid high dead money cuts)
        if cap_hit > 0:
            dead_money_ratio = dead_money / cap_hit
            dead_money_penalty = dead_money_ratio * 15.0  # Penalize high dead money
        else:
            dead_money_penalty = 0.0

        base_score = (
            cap_hit_score +
            overall_score +
            age_penalty -
            dead_money_penalty
        )

        # Directive adjustments
        adjustments = 0.0

        # Expendable players get major bonus
        player_id = player.get("player_id")
        if player_id and player_id in self._directives.expendable_player_ids:
            adjustments += 20.0

        # Priority positions get penalty (harder to cut)
        if position in self._directives.priority_positions:
            adjustments -= 10.0

        # Philosophy-based adjustments
        philosophy = self._directives.team_philosophy

        if philosophy == "win_now":
            # Keep young talent, cut expensive depth
            if age < 27:
                adjustments -= 15.0
        elif philosophy == "rebuild":
            # Cut expensive veterans, keep young players
            if age >= 30:
                adjustments += 10.0
            if age < 27:
                adjustments -= 15.0

        # Budget-based adjustments
        if self._directives.budget_stance == "conservative":
            # Conservative budgets prioritize cap savings
            cap_savings = max(0, cap_hit - dead_money)
            if cap_savings > 2_000_000:
                adjustments += 5.0

        return base_score + adjustments

    def _get_priority_tier(self, player: Dict, cut_score: float) -> int:
        """
        Determine priority tier based on cut score and context.

        Args:
            player: Player data dict
            cut_score: Calculated cut score

        Returns:
            Priority tier (1=MUST_CUT, 2=PHILOSOPHY, 3=DEPTH, 4=CAP_RELIEF)
        """
        cap_hit = player.get("cap_hit", 0)
        overall = extract_overall_rating(player, default=70)
        age = player.get("age", 25)

        # TIER_MUST_CUT: High cap hit + low value
        if cap_hit > self.HIGH_CAP_HIT_THRESHOLD and overall < self.LOW_OVERALL_THRESHOLD:
            return self.TIER_MUST_CUT

        # TIER_PHILOSOPHY: Philosophy-aligned cuts
        philosophy = self._directives.team_philosophy
        if philosophy == "rebuild" and age >= 30:
            return self.TIER_PHILOSOPHY
        if philosophy == "win_now" and age >= 32:
            return self.TIER_PHILOSOPHY

        # Check if expendable
        player_id = player.get("player_id")
        if player_id and player_id in self._directives.expendable_player_ids:
            return self.TIER_PHILOSOPHY

        # TIER_DEPTH: Replacement available (high cut score, not must-cut)
        if cut_score >= 25.0:
            return self.TIER_DEPTH

        # TIER_CAP_RELIEF: General optimization
        return self.TIER_CAP_RELIEF

    def _calculate_confidence(self, cut_score: float, tier: int) -> float:
        """
        Calculate confidence from cut score and tier.

        Higher scores = higher confidence.
        TIER_MUST_CUT = 0.85-0.95
        TIER_PHILOSOPHY = 0.70-0.85
        TIER_DEPTH = 0.60-0.75
        TIER_CAP_RELIEF = 0.50-0.65

        Args:
            cut_score: Calculated cut score
            tier: Priority tier

        Returns:
            Confidence value between 0.5 and 0.95
        """
        # Base confidence from tier
        tier_base = {
            self.TIER_MUST_CUT: 0.85,
            self.TIER_PHILOSOPHY: 0.70,
            self.TIER_DEPTH: 0.60,
            self.TIER_CAP_RELIEF: 0.50,
        }.get(tier, 0.50)

        # Bonus from cut score (higher score = more confident)
        # Add 0.001 per point above 20
        score_bonus = max(0, (cut_score - 20) * 0.001)

        confidence = tier_base + score_bonus
        return min(0.95, max(0.50, confidence))

    def _generate_reasoning(
        self,
        player: Dict,
        cut_score: float,
        tier: int,
        cap_savings: int,
        dead_money: int,
    ) -> str:
        """
        Generate philosophy-specific reasoning for the cut.

        Args:
            player: Player data dict
            cut_score: Calculated cut score
            tier: Priority tier
            cap_savings: Cap savings from cut
            dead_money: Dead money impact

        Returns:
            Human-readable reasoning string
        """
        name = player.get("name", f"Player {player.get('player_id', '?')}")
        position = player.get("position", "")
        age = player.get("age", 0)
        overall = extract_overall_rating(player, default=0)
        cap_hit = player.get("cap_hit", 0)

        philosophy = self._directives.team_philosophy

        # Get replacement description
        replacement_desc = self._get_replacement_description(player, [])

        # Tier-specific reasoning templates
        if tier == self.TIER_MUST_CUT:
            reasoning = self._must_cut_reasoning(
                name, position, age, overall, cap_hit, cap_savings, dead_money
            )
        elif tier == self.TIER_PHILOSOPHY:
            if philosophy == "win_now":
                reasoning = self._win_now_cut_reasoning(
                    name, position, age, overall, cap_savings, dead_money
                )
            elif philosophy == "rebuild":
                reasoning = self._rebuild_cut_reasoning(
                    name, position, age, overall, cap_savings, dead_money
                )
            else:  # maintain
                reasoning = self._maintain_cut_reasoning(
                    name, position, age, overall, cap_savings, dead_money
                )
        elif tier == self.TIER_DEPTH:
            reasoning = self._depth_cut_reasoning(
                name, position, age, overall, cap_savings, dead_money, replacement_desc
            )
        else:  # TIER_CAP_RELIEF
            reasoning = self._cap_relief_reasoning(
                name, position, age, overall, cap_savings, dead_money
            )

        # Add score breakdown
        reasoning += f"\n\nCut Score: {cut_score:.1f}"
        reasoning += f"\nCap Impact: ${cap_savings/1_000_000:.1f}M savings, ${dead_money/1_000_000:.1f}M dead money"

        return reasoning

    def _must_cut_reasoning(
        self, name: str, position: str, age: int, overall: int,
        cap_hit: int, cap_savings: int, dead_money: int
    ) -> str:
        """Generate MUST_CUT tier reasoning."""
        reasoning = f"CRITICAL CAP RELIEF: {name} ({position}, {age}yo, {overall} OVR)\n\n"
        reasoning += f"This is a must-cut for cap management. {name} carries a ${cap_hit/1_000_000:.1f}M cap hit "
        reasoning += f"but grades at only {overall} overall. "
        reasoning += f"Cutting saves ${cap_savings/1_000_000:.1f}M against ${dead_money/1_000_000:.1f}M in dead money. "
        reasoning += "The value vs cost ratio is unsustainable."
        return reasoning

    def _win_now_cut_reasoning(
        self, name: str, position: str, age: int, overall: int,
        cap_savings: int, dead_money: int
    ) -> str:
        """Generate WIN_NOW philosophy cut reasoning."""
        reasoning = f"WIN-NOW DEPTH OPTIMIZATION: {name} ({position}, {age}yo, {overall} OVR)\n\n"
        reasoning += "Following your championship window directive, we're optimizing the roster for immediate impact. "
        reasoning += f"{name} represents expensive depth that doesn't contribute to our title run. "
        reasoning += f"Cutting saves ${cap_savings/1_000_000:.1f}M that can be redirected to frontline talent. "
        if dead_money > 0:
            reasoning += f"Dead money of ${dead_money/1_000_000:.1f}M is an acceptable cost for roster flexibility."
        return reasoning

    def _rebuild_cut_reasoning(
        self, name: str, position: str, age: int, overall: int,
        cap_savings: int, dead_money: int
    ) -> str:
        """Generate REBUILD philosophy cut reasoning."""
        reasoning = f"REBUILD VETERAN RELEASE: {name} ({position}, {age}yo, {overall} OVR)\n\n"
        reasoning += "Following your rebuild directive, we're prioritizing young talent and future assets. "
        reasoning += f"{name} at {age} years old doesn't fit our timeline for contention. "
        reasoning += f"Cutting saves ${cap_savings/1_000_000:.1f}M in cap space for future investments. "
        if dead_money > 0:
            reasoning += f"Absorbing ${dead_money/1_000_000:.1f}M in dead money now clears the books faster."
        return reasoning

    def _maintain_cut_reasoning(
        self, name: str, position: str, age: int, overall: int,
        cap_savings: int, dead_money: int
    ) -> str:
        """Generate MAINTAIN philosophy cut reasoning."""
        reasoning = f"BALANCED ROSTER OPTIMIZATION: {name} ({position}, {age}yo, {overall} OVR)\n\n"
        reasoning += "Following your balanced approach, this cut weighs both cap efficiency and roster depth. "
        reasoning += f"{name} saves ${cap_savings/1_000_000:.1f}M against ${dead_money/1_000_000:.1f}M in dead money. "
        ratio = cap_savings / max(1, dead_money)
        if ratio >= 2.0:
            reasoning += "The savings-to-dead money ratio strongly favors this cut."
        else:
            reasoning += "While the ratio is modest, the overall roster balance benefits from this move."
        return reasoning

    def _depth_cut_reasoning(
        self, name: str, position: str, age: int, overall: int,
        cap_savings: int, dead_money: int, replacement_desc: str
    ) -> str:
        """Generate DEPTH tier cut reasoning."""
        reasoning = f"DEPTH CHART ADJUSTMENT: {name} ({position}, {age}yo, {overall} OVR)\n\n"
        reasoning += f"We have adequate depth at {position}. {replacement_desc}. "
        reasoning += f"Cutting {name} saves ${cap_savings/1_000_000:.1f}M in cap space "
        reasoning += f"with ${dead_money/1_000_000:.1f}M in dead money. "
        reasoning += "This move optimizes our depth chart without creating roster holes."
        return reasoning

    def _cap_relief_reasoning(
        self, name: str, position: str, age: int, overall: int,
        cap_savings: int, dead_money: int
    ) -> str:
        """Generate CAP_RELIEF tier cut reasoning."""
        reasoning = f"CAP SPACE OPTIMIZATION: {name} ({position}, {age}yo, {overall} OVR)\n\n"
        reasoning += f"Cutting {name} provides ${cap_savings/1_000_000:.1f}M in cap relief "
        reasoning += f"against ${dead_money/1_000_000:.1f}M in dead money. "
        reasoning += "While not a critical move, this cut improves our overall cap flexibility "
        reasoning += "and creates roster flexibility for future acquisitions."
        return reasoning

    def _get_replacement_description(self, player: Dict, roster: List[Dict]) -> str:
        """
        Describe available replacements at position.

        Args:
            player: Player being cut
            roster: Full roster list (empty for now - placeholder)

        Returns:
            Description string like "3 backups at CB (Smith 68, Jones 67, Brown 65)"
        """
        # Simplified for now - just mention depth exists
        # In future could analyze actual roster depth
        position = player.get("position", "")
        return f"Multiple players available at {position} to fill the depth chart"

    def _create_proposal(
        self,
        player: Dict,
        cut_score: float,
        tier: int,
        reasoning: str,
    ) -> PersistentGMProposal:
        """
        Create PersistentGMProposal using create_cut_details.

        Args:
            player: Player data dict
            cut_score: Calculated cut score
            tier: Priority tier
            reasoning: Generated reasoning

        Returns:
            PersistentGMProposal for this cut
        """
        name = player.get("name", f"Player {player.get('player_id', '?')}")
        position = player.get("position", "")
        age = player.get("age", 0)
        overall = extract_overall_rating(player, default=0)
        cap_hit = player.get("cap_hit", 0)
        dead_money = player.get("dead_money", 0)
        cap_savings = max(0, cap_hit - dead_money)

        # Get replacement description
        replacement_desc = self._get_replacement_description(player, [])

        # Create details using helper
        details = create_cut_details(
            player_name=name,
            position=position,
            age=age,
            overall_rating=overall,
            cap_savings=cap_savings,
            dead_money=dead_money,
            replacement_options=replacement_desc,
        )

        # Add execution fields
        details["player_id"] = player.get("player_id")
        details["use_june_1"] = False  # Default to regular cut

        # Calculate confidence
        confidence = self._calculate_confidence(cut_score, tier)

        return PersistentGMProposal(
            dynasty_id=self._dynasty_id,
            team_id=self._team_id,
            season=self._season,
            stage="OFFSEASON_ROSTER_CUTS",
            proposal_type=ProposalType.CUT,
            subject_player_id=str(player.get("player_id", "")),
            details=details,
            gm_reasoning=reasoning,
            confidence=confidence,
            priority=tier,  # Use tier directly as priority
            status=ProposalStatus.APPROVED,  # Default to approved - owner can reject
            created_at=datetime.now(),
        )
