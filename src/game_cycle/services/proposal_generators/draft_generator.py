"""
Draft Proposal Generator - Generates draft pick proposals based on owner directives.

Part of Tollgate 9: Draft Integration.

Uses existing DraftService evaluation logic, converts results
to PersistentGMProposal objects for owner approval workflow.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from utils.player_field_extractors import extract_primary_position, extract_overall_rating
from game_cycle.models.owner_directives import OwnerDirectives
from game_cycle.models.persistent_gm_proposal import (
    PersistentGMProposal,
    create_draft_pick_details,
)
from game_cycle.models.proposal_enums import ProposalType, ProposalStatus
from game_cycle.models.draft_direction import (
    DraftDirection,
    DraftStrategy,
    DraftDirectionResult,
)


class DraftProposalGenerator:
    """
    Generates draft pick proposals based on owner directives.

    Uses existing DraftService evaluation logic to evaluate all available
    prospects, then creates PersistentGMProposal objects with:
    - Recommended prospect (highest adjusted score)
    - 2-3 alternatives for owner consideration
    - Philosophy-based reasoning
    - Confidence from evaluation score

    Strategy mapping from team_philosophy (when draft_strategy not explicit):
    - WIN_NOW → NEEDS_BASED (60% need, 40% BPA)
    - MAINTAIN → BALANCED (50% need, 50% BPA)
    - REBUILD → BPA (40% need, 60% BPA)
    """

    # Draft grades based on value differential
    GRADE_THRESHOLDS = {
        "A+": 15,   # 15+ points above pick value
        "A": 10,    # 10-14 above
        "A-": 5,    # 5-9 above
        "B+": 0,    # Even value
        "B": -5,    # 0-4 below
        "B-": -10,  # 5-9 below
        "C+": -15,  # 10-14 below
        "C": -20,   # 15-19 below
        "D": -100,  # Significant reach
    }

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
            season: Current season year (draft year)
            team_id: User's team ID
            directives: Owner's strategic directives
        """
        self._db_path = db_path
        self._dynasty_id = dynasty_id
        self._season = season
        self._team_id = team_id
        self._directives = directives
        self._draft_service = None  # Lazy-loaded

    def _get_draft_service(self):
        """Lazy-load DraftService to avoid circular imports."""
        if self._draft_service is None:
            from game_cycle.services.draft_service import DraftService

            self._draft_service = DraftService(
                db_path=self._db_path,
                dynasty_id=self._dynasty_id,
                season=self._season,
            )
        return self._draft_service

    def generate_proposal_for_pick(
        self,
        pick_info: Dict[str, Any],
        available_prospects: List[Dict[str, Any]],
    ) -> PersistentGMProposal:
        """
        Generate a single proposal for the current pick.

        Args:
            pick_info: Current pick information (round, pick_in_round, overall, team_id)
            available_prospects: List of available prospects with ratings

        Returns:
            PersistentGMProposal with recommended prospect and alternatives
        """
        if not available_prospects:
            raise ValueError("No available prospects to draft")

        draft_service = self._get_draft_service()

        # Convert directives to draft direction
        draft_direction = self._get_draft_direction()

        # Get team needs
        team_needs = draft_service.analyze_team_needs(self._team_id)

        # Evaluate all prospects
        pick_position = pick_info.get("overall_pick", pick_info.get("overall", 1))
        evaluated = []

        for prospect in available_prospects:
            result = draft_service._evaluate_prospect_with_direction(
                prospect=prospect,
                team_needs=team_needs,
                pick_position=pick_position,
                direction=draft_direction,
            )
            evaluated.append({
                "prospect": prospect,
                "result": result,
            })

        # Sort by adjusted score (descending)
        evaluated.sort(key=lambda x: x["result"].adjusted_score, reverse=True)

        # Select top prospect
        top = evaluated[0]
        prospect = top["prospect"]
        result = top["result"]

        # Get alternatives (next 2-3 non-excluded)
        alternatives = self._get_alternatives(evaluated[1:], max_count=3)

        # Calculate draft grade
        draft_grade = self._calculate_draft_grade(prospect, pick_position)

        # Get need urgency for this position
        need_urgency = self._get_need_urgency(prospect["position"], team_needs)

        # Build score breakdown
        score_breakdown = {
            "base_score": result.original_score,
            "strategy_bonus": result.strategy_bonus,
            "position_bonus": result.position_bonus,
            "watchlist_bonus": result.watchlist_bonus,
            "reach_penalty": result.reach_penalty,
            "adjusted_score": result.adjusted_score,
        }

        # Create details
        details = create_draft_pick_details(
            round_num=pick_info.get("round_number", pick_info.get("round", 1)),
            pick=pick_info.get("pick_in_round", pick_info.get("pick", 1)),
            overall=pick_position,
            player_name=prospect.get("name", f"{prospect.get('first_name', '')} {prospect.get('last_name', '')}".strip()),
            position=prospect.get("position", ""),
            college=prospect.get("college", ""),
            projected_rating=extract_overall_rating(prospect, default=0),
            draft_grade=draft_grade,
            alternatives=[{
                "prospect_id": alt["prospect"]["prospect_id"],  # Use prospect_id not player_id
                "name": alt["prospect"].get("name", f"{alt['prospect'].get('first_name', '')} {alt['prospect'].get('last_name', '')}".strip()),
                "position": alt["prospect"].get("position", ""),
                "rating": extract_overall_rating(alt["prospect"], default=0),
                "college": alt["prospect"].get("college", ""),
            } for alt in alternatives],
        )

        # Add execution fields - use prospect_id (not player_id) from draft_prospects table
        details["prospect_id"] = prospect["prospect_id"]
        details["need_urgency"] = need_urgency
        details["score_breakdown"] = score_breakdown

        # Calculate confidence
        confidence = self._calculate_confidence(result.adjusted_score)

        # Generate reasoning
        reasoning = self._generate_reasoning(
            prospect=prospect,
            pick_info=pick_info,
            result=result,
            team_needs=team_needs,
            alternatives=alternatives,
        )

        return PersistentGMProposal(
            dynasty_id=self._dynasty_id,
            team_id=self._team_id,
            season=self._season,
            stage="OFFSEASON_DRAFT",
            proposal_type=ProposalType.DRAFT_PICK,
            subject_player_id=str(prospect["prospect_id"]),  # Use prospect_id not player_id
            details=details,
            gm_reasoning=reasoning,
            confidence=confidence,
            priority=self._pick_to_priority(pick_position),
            status=ProposalStatus.APPROVED,  # Default to approved - owner can reject
            created_at=datetime.now(),
        )

    def _get_draft_direction(self) -> DraftDirection:
        """
        Convert owner directives to draft direction.

        Uses explicit draft_strategy if set, otherwise derives from team_philosophy:
        - WIN_NOW → NEEDS_BASED (aggressive need filling)
        - MAINTAIN → BALANCED (default behavior)
        - REBUILD → BPA (best talent available)
        """
        # If draft_strategy is explicitly set and not default, use it
        if self._directives.draft_strategy != "balanced":
            return self._directives.to_draft_direction()

        # Otherwise, derive from team_philosophy
        philosophy = self._directives.team_philosophy

        if philosophy == "win_now":
            strategy = DraftStrategy.NEEDS_BASED
        elif philosophy == "rebuild":
            strategy = DraftStrategy.BEST_PLAYER_AVAILABLE
        else:  # maintain
            strategy = DraftStrategy.BALANCED

        return DraftDirection(
            strategy=strategy,
            priority_positions=self._directives.priority_positions.copy(),
            watchlist_prospect_ids=[],  # Resolved at runtime if needed
        )

    def _get_alternatives(
        self,
        remaining_evaluated: List[Dict],
        max_count: int = 3,
    ) -> List[Dict]:
        """
        Get top alternatives (excluding those with score -100).

        Args:
            remaining_evaluated: Evaluated prospects after top pick
            max_count: Maximum number of alternatives

        Returns:
            List of alternative prospect dicts
        """
        alternatives = []
        for item in remaining_evaluated:
            if item["result"].adjusted_score > -100:  # Not excluded
                alternatives.append(item)
                if len(alternatives) >= max_count:
                    break
        return alternatives

    def _calculate_draft_grade(
        self,
        prospect: Dict[str, Any],
        pick_position: int,
    ) -> str:
        """
        Calculate draft grade based on prospect value vs pick position.

        Uses projected pick range to determine value differential.

        Args:
            prospect: Prospect data dict
            pick_position: Overall pick number

        Returns:
            Draft grade string (A+, A, B+, etc.)
        """
        # Get projected pick range
        projected_min = prospect.get("projected_pick_min", pick_position)
        projected_max = prospect.get("projected_pick_max", pick_position)
        projected_avg = (projected_min + projected_max) / 2

        # Calculate value differential
        # Positive = picking earlier than projected (reaching)
        # Negative = picking later than projected (value)
        value_diff = projected_avg - pick_position

        # Map to grade
        for grade, threshold in self.GRADE_THRESHOLDS.items():
            if value_diff >= threshold:
                return grade
        return "F"

    def _get_need_urgency(
        self,
        position: str,
        team_needs: List[Dict[str, Any]],
    ) -> str:
        """
        Get need urgency label for a position.

        Args:
            position: Position code
            team_needs: List of team needs with urgency scores

        Returns:
            Urgency label (CRITICAL, HIGH, MEDIUM, LOW, NONE)
        """
        for need in team_needs:
            need_position = extract_primary_position(need.get("positions"))
            if need_position == position:
                urgency = need.get("urgency_score", 0)
                if urgency >= 5:
                    return "CRITICAL"
                elif urgency >= 4:
                    return "HIGH"
                elif urgency >= 3:
                    return "MEDIUM"
                elif urgency >= 2:
                    return "LOW"
        return "NONE"

    def _calculate_confidence(self, adjusted_score: float) -> float:
        """
        Calculate confidence from adjusted score.

        Higher scores = higher confidence.
        Score of 70 = 0.60 confidence
        Score of 85 = 0.75 confidence
        Score of 100 = 0.90 confidence (capped at 0.95)

        Args:
            adjusted_score: Prospect's adjusted evaluation score

        Returns:
            Confidence value between 0.5 and 0.95
        """
        # Base confidence starts at 0.5
        # Add 0.01 for each point above 60
        base = 0.5
        bonus = (adjusted_score - 60) * 0.01
        return min(0.95, max(0.5, base + bonus))

    def _generate_reasoning(
        self,
        prospect: Dict[str, Any],
        pick_info: Dict[str, Any],
        result: DraftDirectionResult,
        team_needs: List[Dict[str, Any]],
        alternatives: List[Dict],
    ) -> str:
        """
        Generate philosophy-specific reasoning for the pick.

        Args:
            prospect: Selected prospect data
            pick_info: Current pick info
            result: Evaluation result with scores
            team_needs: Team needs list
            alternatives: Alternative prospects

        Returns:
            Human-readable reasoning string
        """
        philosophy = self._directives.team_philosophy
        position = prospect.get("position", "")
        name = prospect.get("name", f"{prospect.get('first_name', '')} {prospect.get('last_name', '')}".strip())
        overall = extract_overall_rating(prospect, default=0)
        college = prospect.get("college", "Unknown")

        # Get position priority rank
        priority_rank = None
        if position in self._directives.priority_positions:
            priority_rank = self._directives.priority_positions.index(position) + 1

        # Get need urgency
        need_urgency = self._get_need_urgency(position, team_needs)

        # Base info
        pick_num = pick_info.get("overall_pick", pick_info.get("overall", 0))
        round_num = pick_info.get("round_number", pick_info.get("round", 1))

        # Build philosophy-specific reasoning
        if philosophy == "win_now":
            reasoning = self._win_now_reasoning(
                name, position, overall, college, need_urgency, priority_rank, result
            )
        elif philosophy == "rebuild":
            reasoning = self._rebuild_reasoning(
                name, position, overall, college, need_urgency, result
            )
        else:  # maintain
            reasoning = self._maintain_reasoning(
                name, position, overall, college, need_urgency, priority_rank, result
            )

        # Add evaluation breakdown
        reasoning += f"\n\nEvaluation: Base {result.original_score:.0f}"
        if result.strategy_bonus != 0:
            reasoning += f", Need bonus +{result.strategy_bonus:.0f}"
        if result.position_bonus != 0:
            reasoning += f", Priority bonus +{result.position_bonus:.0f}"
        if result.reach_penalty != 0:
            reasoning += f", Reach penalty {result.reach_penalty:.0f}"
        reasoning += f" = {result.adjusted_score:.0f} adjusted score."

        # Mention alternatives if any
        if alternatives:
            alt_names = [alt["prospect"].get("name", "?")[:20] for alt in alternatives[:2]]
            reasoning += f"\n\nAlternatives considered: {', '.join(alt_names)}"

        return reasoning

    def _win_now_reasoning(
        self,
        name: str,
        position: str,
        overall: int,
        college: str,
        need_urgency: str,
        priority_rank: Optional[int],
        result: DraftDirectionResult,
    ) -> str:
        """Generate WIN_NOW philosophy reasoning."""
        reasoning = f"WIN-NOW SELECTION: {name} ({position}, {overall} OVR) from {college}.\n\n"

        if need_urgency in ("CRITICAL", "HIGH"):
            reasoning += f"This addresses our {need_urgency} need at {position}. "
            reasoning += "With your championship window open, filling roster holes is paramount. "
        elif priority_rank:
            reasoning += f"{position} is your #{priority_rank} priority position. "
            reasoning += "This pick aligns directly with your stated needs. "
        else:
            reasoning += f"{name} represents the best immediate impact available. "
            reasoning += "Even without a pressing need, this talent level demands selection. "

        reasoning += f"\n\n{name} projects as a Day 1 contributor who can help us compete immediately."
        return reasoning

    def _rebuild_reasoning(
        self,
        name: str,
        position: str,
        overall: int,
        college: str,
        need_urgency: str,
        result: DraftDirectionResult,
    ) -> str:
        """Generate REBUILD philosophy reasoning."""
        reasoning = f"BEST PLAYER AVAILABLE: {name} ({position}, {overall} OVR) from {college}.\n\n"

        reasoning += f"Following your rebuild directive, we're prioritizing raw talent over immediate needs. "
        reasoning += f"{name} grades out as the top prospect on our board. "

        if need_urgency in ("CRITICAL", "HIGH"):
            reasoning += f"The fact that this also addresses a {need_urgency} need at {position} is a bonus. "
        else:
            reasoning += "Building a championship foundation requires accumulating talent regardless of position. "

        reasoning += f"\n\n{name} has the ceiling to become a cornerstone of our future contender."
        return reasoning

    def _maintain_reasoning(
        self,
        name: str,
        position: str,
        overall: int,
        college: str,
        need_urgency: str,
        priority_rank: Optional[int],
        result: DraftDirectionResult,
    ) -> str:
        """Generate MAINTAIN philosophy reasoning."""
        reasoning = f"BALANCED VALUE: {name} ({position}, {overall} OVR) from {college}.\n\n"

        reasoning += "Following your balanced approach, this pick weighs both talent and fit. "

        if need_urgency in ("CRITICAL", "HIGH"):
            reasoning += f"We have a {need_urgency} need at {position}, and {name} represents excellent value here. "
        elif priority_rank:
            reasoning += f"While {position} is your #{priority_rank} priority, we're not reaching - this is fair value. "
        else:
            reasoning += f"{name} offers the best combination of talent and roster fit available. "

        reasoning += f"\n\nThis selection maintains competitive balance while building for sustained success."
        return reasoning

    def _pick_to_priority(self, pick_position: int) -> int:
        """
        Convert pick position to priority value.

        Earlier picks get higher priority (lower number).
        Round 1 picks = priority 1
        Round 2 = priority 2, etc.

        Args:
            pick_position: Overall pick number (1-224)

        Returns:
            Priority value (1-7)
        """
        # Determine round from overall pick
        # Rounds are roughly 32 picks each
        round_num = (pick_position - 1) // 32 + 1
        return min(7, round_num)