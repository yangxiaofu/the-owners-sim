"""
Coach Roster Cuts Proposal Generator - Generates roster cut proposals from Head Coach perspective.

Part of Tollgate 10: Roster Cuts Integration.

Differs from GM generator by focusing on:
- Recent performance (play grades, injury history)
- Scheme fit (defensive/offensive system compatibility)
- Development trajectory (young talent with upside vs aging veterans)
- Special teams value
- Competitive/on-field factors rather than financial
- UDFA/Rookie status (UDFAs are first to be cut during preseason)
- Coach archetype influence (starter loyalty, rookie trust, etc.)

Uses performance-based scoring to identify cut candidates from the Head Coach's perspective,
complementing the GM's value-based analysis.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.utils.player_field_extractors import extract_primary_position, extract_overall_rating
from game_cycle.models.owner_directives import OwnerDirectives
from game_cycle.models.persistent_gm_proposal import (
    PersistentGMProposal,
    create_cut_details,
)
from game_cycle.models.proposal_enums import ProposalType, ProposalStatus

logger = logging.getLogger(__name__)


class CoachCutsProposalGenerator:
    """
    Generates roster cut proposals from Head Coach perspective.

    Focuses on on-field performance and competitive factors:
    - Priority tier (PERFORMANCE, DEPTH, AGE, ROTATION)
    - Cut score based on play grades, scheme fit, development, injury risk
    - Performance-based reasoning
    - Confidence from tier and score

    Differentiation from GM:
    - GM: Cap hit vs overall rating (financial)
    - Coach: Play grades vs scheme fit (competitive)
    """

    # Priority tiers for cut candidates (Coach perspective)
    TIER_PERFORMANCE = 1    # Poor grades, injury-prone, scheme mismatch
    TIER_DEPTH = 2          # Replaceable depth, no ST value
    TIER_AGE = 3            # Aging veterans past prime
    TIER_ROTATION = 4       # Rotation players, marginal fits

    # Scoring thresholds
    MIN_CUT_SCORE = 10.0              # Minimum score to propose cut
    LOW_PERFORMANCE_THRESHOLD = 65    # Play grade below this = poor performer
    HIGH_INJURY_RISK_THRESHOLD = 5    # Injury-prone rating above this = risky

    def __init__(
        self,
        db_path: str,
        dynasty_id: str,
        season: int,
        team_id: int,
        directives: OwnerDirectives,
        coach_archetype_key: Optional[str] = None,
        coach_traits: Optional[Dict[str, float]] = None,
    ):
        """
        Initialize the Coach cuts generator.

        Args:
            db_path: Path to database
            dynasty_id: Dynasty identifier
            season: Current season year
            team_id: User's team ID
            directives: Owner's strategic directives (still respected for protected players)
            coach_archetype_key: HC archetype key (e.g., "balanced", "aggressive", "conservative")
            coach_traits: Optional explicit traits dict, otherwise loaded from archetype
        """
        self._db_path = db_path
        self._dynasty_id = dynasty_id
        self._season = season
        self._team_id = team_id
        self._directives = directives
        self._cut_phase = "PRESEASON_W3"  # Track current cut phase for reasoning

        # Coach archetype influence
        self._archetype_key = coach_archetype_key or "balanced"
        self._coach_traits = coach_traits or self._load_archetype_traits()

    def _load_archetype_traits(self) -> Dict[str, float]:
        """
        Load coach traits from archetype config.

        Returns:
            Dict with starter_loyalty, rookie_trust, risk_tolerance, conservatism
        """
        try:
            from play_engine.play_calling.coach_archetype import load_coach_archetype
            archetype = load_coach_archetype(self._archetype_key)
            return {
                "starter_loyalty": getattr(archetype, "starter_loyalty", 0.5),
                "rookie_trust": getattr(archetype, "rookie_trust", 0.5),
                "risk_tolerance": getattr(archetype, "risk_tolerance", 0.5),
                "conservatism": getattr(archetype, "conservatism", 0.5),
            }
        except Exception as e:
            logger.warning(f"Failed to load coach archetype '{self._archetype_key}': {e}")
            # Default to balanced traits
            return {
                "starter_loyalty": 0.5,
                "rookie_trust": 0.5,
                "risk_tolerance": 0.5,
                "conservatism": 0.5,
            }

    def generate_proposals(
        self,
        roster: List[Dict],
        target_roster_size: int = 53,
        cut_phase: str = "PRESEASON_W3",
    ) -> List[PersistentGMProposal]:
        """
        Generate batch of cut proposals from Coach perspective.

        Args:
            roster: Full roster with ratings, contracts, performance data
            target_roster_size: Target roster size (53 for final, 75/80 for preseason)
            cut_phase: Cut phase identifier ("PRESEASON_W1", "PRESEASON_W2", "FINAL")

        Returns:
            List of PersistentGMProposal sorted by priority tier
        """
        # Store cut phase for reasoning methods
        self._cut_phase = cut_phase

        # Calculate cuts needed
        current_roster_size = len(roster)
        cuts_needed = current_roster_size - target_roster_size

        if cuts_needed <= 0:
            return []

        # Filter out protected players (still respect owner directives)
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

        # FALLBACK: If not enough candidates above threshold, add more from cuttable list
        # This ensures we always generate enough recommendations when cuts are needed
        if len(scored_candidates) < cuts_needed:
            # Get player IDs already scored
            already_scored_ids = {c["player"].get("player_id") for c in scored_candidates}

            # Score remaining players (even if below threshold)
            remaining = [
                p for p in cuttable
                if p.get("player_id") not in already_scored_ids
            ]

            for player in remaining:
                cut_score = self._score_cut_candidate(player)
                scored_candidates.append({
                    "player": player,
                    "cut_score": cut_score,
                })

            # Re-sort all candidates
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

            # Calculate cap impact (still included for owner's info)
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
        Score player for cut candidacy from Coach perspective (higher = more likely to cut).

        Factors:
        - UDFA/Rookie status (UDFAs are first to be cut - highest priority)
        - Overall rating (low OVR = cut, high OVR = protect)
        - Performance score (recent play grades - lower = cut)
        - Scheme fit (mismatch = cut)
        - Development trajectory (young with upside = keep, aging without room = cut)
        - Injury risk (injury-prone = cut)
        - Special teams value (good ST = keep)
        - Coach archetype influence

        Args:
            player: Player data dict

        Returns:
            Cut score (higher = more cut-worthy from performance standpoint)
        """
        age = player.get("age", 25)
        overall = extract_overall_rating(player, default=70)
        potential = player.get("potential", 70)
        position = player.get("position", "")
        contract_type = player.get("contract_type", "VETERAN")
        years_pro = player.get("years_pro", 5)  # Default to veteran

        # =================================================================
        # UDFA/ROOKIE PRIORITY - UDFAs should be cut first during preseason
        # =================================================================
        udfa_bonus = 0.0
        is_udfa = contract_type == "ROOKIE" and years_pro == 0

        if is_udfa:
            # Undrafted free agents - highest cut priority
            # They're competing for roster spots and haven't proven anything
            udfa_bonus = 40.0
        elif contract_type == "ROOKIE" and years_pro <= 1:
            # Recent draft picks still on rookie deals - slight cut preference
            udfa_bonus = 10.0

        # =================================================================
        # OVERALL RATING WEIGHT - Low OVR should be cut, high OVR protected
        # =================================================================
        if overall < 65:
            # Very low OVR players should be cut first
            low_ovr_penalty = (65 - overall) * 3.0  # +30 for 55 OVR, +15 for 60 OVR
        elif overall < 75:
            # Below average players
            low_ovr_penalty = (75 - overall) * 1.0  # +10 for 65 OVR, +5 for 70 OVR
        else:
            low_ovr_penalty = 0.0

        # High overall protection - good players should be kept
        if overall >= 80:
            high_ovr_protection = (overall - 80) * 5.0  # -15 for 83 OVR, -25 for 85 OVR
        else:
            high_ovr_protection = 0.0

        ovr_adjustment = low_ovr_penalty - high_ovr_protection

        # =================================================================
        # PERFORMANCE SCORE - Recent play grades
        # =================================================================
        season_grade = player.get("season_grade", overall)  # Use overall as fallback
        performance_score = max(0, 100 - season_grade)  # Lower grade = higher cut score

        # Scheme fit (position-specific)
        scheme_fit_score = self._calculate_scheme_fit(player)

        # =================================================================
        # DEVELOPMENT TRAJECTORY - Modified to NOT protect low-OVR UDFAs
        # =================================================================
        upside = potential - overall

        # Don't protect young players if they're UDFAs with low overall
        if age < 25 and upside > 10 and not is_udfa and overall >= 70:
            # Protect young DRAFTED talent with high upside (not UDFAs)
            development_adjustment = -30.0
        elif is_udfa and overall < 70:
            # UDFAs with low OVR need to prove themselves - cut priority
            development_adjustment = 20.0
        elif age > 30 and upside < 3:
            # Cut aging veterans at ceiling
            development_adjustment = 20.0
        elif age > 32:
            # Strong penalty for very old players
            development_adjustment = 15.0
        else:
            development_adjustment = 0.0

        # =================================================================
        # INJURY & SPECIAL TEAMS
        # =================================================================
        injury_prone_rating = player.get("injury_prone_rating", 0)  # 0-10 scale
        injury_score = injury_prone_rating * 5.0  # Higher rating = more cut-worthy

        st_ability = player.get("special_teams_ability", 0)  # 0-99 scale
        st_value = -10.0 if st_ability > 70 else 0.0  # Good ST = keep

        # =================================================================
        # DIRECTIVE ADJUSTMENTS
        # =================================================================
        directive_adjustments = 0.0
        player_id = player.get("player_id")
        if player_id and player_id in self._directives.expendable_player_ids:
            directive_adjustments += 20.0

        # Position priority (harder to cut priority positions)
        if position in self._directives.priority_positions:
            directive_adjustments -= 10.0

        # =================================================================
        # CALCULATE BASE SCORE
        # =================================================================
        base_score = (
            udfa_bonus +
            ovr_adjustment +
            performance_score +
            scheme_fit_score +
            development_adjustment +
            injury_score +
            st_value +
            directive_adjustments
        )

        # =================================================================
        # COACH ARCHETYPE ADJUSTMENTS
        # =================================================================
        archetype_adjustment = self._apply_archetype_adjustments(player, is_udfa)

        return base_score + archetype_adjustment

    def _apply_archetype_adjustments(self, player: Dict, is_udfa: bool) -> float:
        """
        Apply coach archetype-specific adjustments to cut score.

        Args:
            player: Player data dict
            is_udfa: Whether player is an undrafted free agent

        Returns:
            Archetype adjustment (positive = more likely to cut)
        """
        age = player.get("age", 25)
        overall = extract_overall_rating(player, default=70)
        years_pro = player.get("years_pro", 5)
        depth_position = player.get("depth_chart_position", 2)
        is_starter = depth_position == 1
        injury_prone = player.get("injury_prone_rating", 0)

        adjustment = 0.0

        # Starter loyalty: High loyalty = protect starters
        if is_starter and overall >= 75:
            loyalty_protection = self._coach_traits["starter_loyalty"] * 20.0  # 0-20 protection
            adjustment -= loyalty_protection

        # Rookie trust: High trust = protect young players (but not low-OVR UDFAs)
        if age < 25 and years_pro <= 2 and not (is_udfa and overall < 70):
            rookie_protection = self._coach_traits["rookie_trust"] * 15.0  # 0-15 protection
            adjustment -= rookie_protection

        # Conservatism: High conservatism = cut unproven UDFAs faster
        if is_udfa and overall < 70:
            conservatism_penalty = self._coach_traits["conservatism"] * 10.0  # 0-10 bonus to cut
            adjustment += conservatism_penalty

        # Risk tolerance: Low risk = cut injury-prone players faster
        if injury_prone > 5:
            risk_penalty = (1.0 - self._coach_traits["risk_tolerance"]) * 15.0  # 0-15 bonus to cut
            adjustment += risk_penalty

        return adjustment

    def _calculate_scheme_fit(self, player: Dict) -> float:
        """
        Assess how well player fits team's offensive/defensive scheme.

        In production, this would:
        1. Load team's defensive/offensive scheme from coaching staff
        2. Check position-specific scheme requirements
        3. Compare player attributes to scheme needs

        For now, simplified to basic position logic.

        Args:
            player: Player data dict

        Returns:
            Scheme fit score (higher = worse fit = more cuttable)
        """
        position = player.get("position", "")
        overall = extract_overall_rating(player, default=70)

        # Simplified scheme fit logic
        # In production, would check actual team scheme from coaching staff config

        # Example: If team runs 3-4 defense, OLBs with pass rush are valuable
        # If team runs 4-3 defense, coverage LBs are valuable
        # For now, just penalize below-average players at their position

        if overall < 70:
            # Below-average players don't fit any scheme well
            return 15.0

        # Neutral fit by default
        return 0.0

    def _get_priority_tier(self, player: Dict, cut_score: float) -> int:
        """
        Determine priority tier based on cut score and performance context.

        Args:
            player: Player data dict
            cut_score: Calculated cut score

        Returns:
            Priority tier (1=PERFORMANCE, 2=DEPTH, 3=AGE, 4=ROTATION)
        """
        age = player.get("age", 25)
        season_grade = player.get("season_grade", extract_overall_rating(player, default=70))
        injury_prone_rating = player.get("injury_prone_rating", 0)

        # TIER_PERFORMANCE: Poor grades + injury issues
        if season_grade < self.LOW_PERFORMANCE_THRESHOLD and injury_prone_rating > self.HIGH_INJURY_RISK_THRESHOLD:
            return self.TIER_PERFORMANCE

        # TIER_PERFORMANCE: Very poor performance
        if season_grade < 60:
            return self.TIER_PERFORMANCE

        # Check if expendable (performance-independent)
        player_id = player.get("player_id")
        if player_id and player_id in self._directives.expendable_player_ids:
            return self.TIER_DEPTH

        # TIER_AGE: Aging veterans past prime
        if age >= 32:
            return self.TIER_AGE

        # TIER_DEPTH: Replaceable depth (high cut score, not performance issue)
        if cut_score >= 25.0:
            return self.TIER_DEPTH

        # TIER_ROTATION: General optimization
        return self.TIER_ROTATION

    def _calculate_confidence(self, cut_score: float, tier: int) -> float:
        """
        Calculate confidence from cut score and tier.

        Higher scores = higher confidence.
        TIER_PERFORMANCE = 0.75-0.90
        TIER_DEPTH = 0.60-0.75
        TIER_AGE = 0.50-0.65
        TIER_ROTATION = 0.40-0.55

        Args:
            cut_score: Calculated cut score
            tier: Priority tier

        Returns:
            Confidence value between 0.40 and 0.90
        """
        # Base confidence from tier
        tier_base = {
            self.TIER_PERFORMANCE: 0.75,
            self.TIER_DEPTH: 0.60,
            self.TIER_AGE: 0.50,
            self.TIER_ROTATION: 0.40,
        }.get(tier, 0.40)

        # Bonus from cut score (higher score = more confident)
        score_bonus = max(0, (cut_score - 20) * 0.001)

        confidence = tier_base + score_bonus
        return min(0.90, max(0.40, confidence))

    def _generate_reasoning(
        self,
        player: Dict,
        cut_score: float,
        tier: int,
        cap_savings: int,
        dead_money: int,
    ) -> str:
        """
        Generate performance-based reasoning for the cut.

        Args:
            player: Player data dict
            cut_score: Calculated cut score
            tier: Priority tier
            cap_savings: Cap savings from cut (for owner's info)
            dead_money: Dead money impact (for owner's info)

        Returns:
            Human-readable reasoning string focused on performance
        """
        name = player.get("name", f"Player {player.get('player_id', '?')}")
        position = player.get("position", "")
        age = player.get("age", 0)
        overall = extract_overall_rating(player, default=0)
        season_grade = player.get("season_grade", overall)

        # Tier-specific reasoning templates
        if tier == self.TIER_PERFORMANCE:
            reasoning = self._performance_tier_reasoning(
                name, position, age, overall, season_grade
            )
        elif tier == self.TIER_DEPTH:
            reasoning = self._depth_tier_reasoning(
                name, position, age, overall
            )
        elif tier == self.TIER_AGE:
            reasoning = self._age_tier_reasoning(
                name, position, age, overall
            )
        else:  # TIER_ROTATION
            reasoning = self._rotation_tier_reasoning(
                name, position, age, overall
            )

        # Add score breakdown
        reasoning += f"\n\nPerformance Cut Score: {cut_score:.1f}"
        reasoning += f"\nCap Impact: ${cap_savings/1_000_000:.1f}M savings, ${dead_money/1_000_000:.1f}M dead money"
        reasoning += "\n(Financial impact for owner's consideration)"

        return reasoning

    def _get_phase_prefix(self) -> str:
        """
        Get phase-specific prefix for reasoning templates.

        Returns:
            Phase prefix string (e.g., "PRESEASON WEEK 1 CUT: ", "FINAL CUT: ", or "")
        """
        if self._cut_phase == "PRESEASON_W1":
            return "PRESEASON WEEK 1 CUT: "
        elif self._cut_phase == "PRESEASON_W2":
            return "PRESEASON WEEK 2 CUT: "
        elif self._cut_phase == "FINAL":
            return ""  # No prefix for final cuts (legacy behavior)
        else:
            return ""  # Unknown phase, no prefix

    def _performance_tier_reasoning(
        self, name: str, position: str, age: int, overall: int, season_grade: float
    ) -> str:
        """Generate TIER_PERFORMANCE reasoning."""
        # Add phase prefix
        phase_prefix = self._get_phase_prefix()

        reasoning = f"{phase_prefix}PERFORMANCE CONCERN: {name} ({position}, {age}yo, {overall} OVR)\n\n"
        reasoning += f"From a coaching perspective, {name} has not performed to the level we need. "
        if season_grade < 65:
            reasoning += f"Season grade of {season_grade:.1f} indicates significant on-field struggles. "
        reasoning += f"At {position}, we need reliable production. "
        reasoning += "This cut improves our overall roster quality and competitive readiness. "
        reasoning += "I recommend moving forward with younger or higher-performing options at this position."
        return reasoning

    def _depth_tier_reasoning(
        self, name: str, position: str, age: int, overall: int
    ) -> str:
        """Generate TIER_DEPTH reasoning."""
        # Add phase prefix
        phase_prefix = self._get_phase_prefix()

        reasoning = f"{phase_prefix}DEPTH CHART OPTIMIZATION: {name} ({position}, {age}yo, {overall} OVR)\n\n"
        reasoning += f"We have adequate depth at {position}. "
        reasoning += f"{name} is currently a backup/rotation player who can be replaced. "
        reasoning += "This move allows us to either promote younger talent from practice squad "
        reasoning += "or target specific skill sets in free agency. "
        reasoning += "From a competitive standpoint, this doesn't create a roster hole."
        return reasoning

    def _age_tier_reasoning(
        self, name: str, position: str, age: int, overall: int
    ) -> str:
        """Generate TIER_AGE reasoning."""
        # Add phase prefix
        phase_prefix = self._get_phase_prefix()

        reasoning = f"{phase_prefix}VETERAN ROSTER MANAGEMENT: {name} ({position}, {age}yo, {overall} OVR)\n\n"
        reasoning += f"At {age} years old, {name} is past his prime. "
        reasoning += "While he brings veteran experience, his physical tools have declined. "
        reasoning += f"At {position}, we need players who can contribute for multiple seasons. "
        reasoning += "This cut allows us to get younger and more athletic at the position. "
        reasoning += "From a development standpoint, giving reps to younger players benefits the team long-term."
        return reasoning

    def _rotation_tier_reasoning(
        self, name: str, position: str, age: int, overall: int
    ) -> str:
        """Generate TIER_ROTATION reasoning."""
        # Add phase prefix
        phase_prefix = self._get_phase_prefix()

        reasoning = f"{phase_prefix}ROSTER ROTATION ADJUSTMENT: {name} ({position}, {age}yo, {overall} OVR)\n\n"
        reasoning += f"{name} is a solid rotation player, but we're in a numbers game. "
        reasoning += "To get down to 53, we need to make difficult decisions. "
        reasoning += f"At {position}, we have multiple options who can fill this role. "
        reasoning += "This cut is more about roster composition than performance concerns. "
        reasoning += "If we had room, I'd keep him, but the numbers dictate otherwise."
        return reasoning

    def _is_star_player(self, player: Dict, all_league_players: Optional[List[Dict]] = None) -> bool:
        """
        Determine if player is a star (top 10 at their position league-wide).

        Args:
            player: Player data dict
            all_league_players: Optional list of all league players for comparison

        Returns:
            True if player is top 10 at position by overall rating
        """
        position = extract_primary_position(player.get("positions"))
        overall = extract_overall_rating(player, default=0)

        # Fallback: If no league data, use OVR >= 85 as star threshold
        if not all_league_players:
            return overall >= 85

        # Get all players at same position
        position_players = [
            p for p in all_league_players
            if extract_primary_position(p.get("positions")) == position
        ]

        # Sort by overall rating (descending)
        position_players.sort(key=lambda p: p.get("overall", 0), reverse=True)

        # Check if player is in top 10
        try:
            player_id = player.get("player_id")
            top_10_ids = [p.get("player_id") for p in position_players[:10]]
            return player_id in top_10_ids
        except (IndexError, TypeError):
            # Fallback if comparison fails
            return overall >= 85

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

        # Create details using helper
        details = create_cut_details(
            player_name=name,
            position=position,
            age=age,
            overall_rating=overall,
            cap_savings=cap_savings,
            dead_money=dead_money,
            replacement_options="Depth available at position for competitive continuity",
        )

        # Add execution fields
        details["player_id"] = player.get("player_id")
        details["use_june_1"] = False  # Default to regular cut

        # Add star detection and phase context
        details["is_star_cut"] = self._is_star_player(player)
        details["cut_phase"] = self._cut_phase

        # Calculate confidence
        confidence = self._calculate_confidence(cut_score, tier)

        # Map cut_phase to stage name (phase should be "PRESEASON_W1", "PRESEASON_W2", "PRESEASON_W3")
        stage = f"OFFSEASON_{self._cut_phase}"

        return PersistentGMProposal(
            dynasty_id=self._dynasty_id,
            team_id=self._team_id,
            season=self._season,
            stage=stage,
            proposal_type=ProposalType.CUT,
            subject_player_id=str(player.get("player_id", "")),
            details=details,
            gm_reasoning=reasoning,  # Using gm_reasoning field for Coach reasoning too
            confidence=confidence,
            priority=tier,  # Use tier directly as priority
            status=ProposalStatus.APPROVED,  # Default to approved - owner can reject
            created_at=datetime.now(),
        )
