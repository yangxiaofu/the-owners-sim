"""
HOF Voting Engine - Simulate annual Hall of Fame voting process.

Takes eligible candidates and simulates realistic voting with:
- Vote percentage based on HOF score
- Max 5 inductees per year
- 80% threshold for induction
- Ballot removal for <5% votes or 20-year limit
- Class strength affecting borderline candidates
"""

from dataclasses import dataclass, field
from typing import List, Optional, TYPE_CHECKING
import random
import logging

from game_cycle.database.hof_api import HOFVotingResult
from game_cycle.services.hof_scoring_engine import HOFScoringEngine, HOFScoreBreakdown

if TYPE_CHECKING:
    from game_cycle.services.hof_eligibility_service import HOFCandidate

logger = logging.getLogger(__name__)


# ============================================
# Dataclasses
# ============================================

@dataclass
class HOFVotingSession:
    """
    Complete results of annual HOF voting.

    Contains lists of inductees, non-inductees, and removed candidates,
    plus metadata about the voting session.
    """
    dynasty_id: str
    voting_season: int

    # Results by category
    inductees: List[HOFVotingResult] = field(default_factory=list)
    non_inductees: List[HOFVotingResult] = field(default_factory=list)
    removed_from_ballot: List[HOFVotingResult] = field(default_factory=list)

    # Session metadata
    total_candidates: int = 0
    total_voters: int = 48
    class_strength: float = 0.5  # 0.0-1.0, higher = stronger class

    @property
    def all_results(self) -> List[HOFVotingResult]:
        """Get all voting results combined."""
        return self.inductees + self.non_inductees + self.removed_from_ballot

    def to_dict(self):
        """Convert to dictionary for serialization."""
        return {
            'dynasty_id': self.dynasty_id,
            'voting_season': self.voting_season,
            'inductees': [r.to_dict() for r in self.inductees],
            'non_inductees': [r.to_dict() for r in self.non_inductees],
            'removed_from_ballot': [r.to_dict() for r in self.removed_from_ballot],
            'total_candidates': self.total_candidates,
            'total_voters': self.total_voters,
            'class_strength': self.class_strength,
        }


# ============================================
# HOFVotingEngine Class
# ============================================

class HOFVotingEngine:
    """
    Simulates Hall of Fame voting process.

    Voting Rules:
    - 80% vote threshold required for induction
    - Maximum 5 inductees per year (if >5 qualify, take top 5 by vote %)
    - First-ballot = inducted in first year of eligibility
    - Candidates with <5% votes removed from ballot
    - 20-year maximum on ballot

    Voting Simulation:
    - Higher HOF scores = higher vote percentages
    - First-ballot locks (85+ score) get 90-99% votes
    - Strong candidates (70-84) get 70-89% votes
    - Borderline candidates (55-69) fluctuate 40-75%
    - Long shots (40-54) get 10-45%
    - Class strength affects borderline candidates
    """

    # Voting thresholds
    INDUCTION_THRESHOLD = 0.80      # 80% to get in
    MAX_INDUCTEES_PER_YEAR = 5
    MIN_VOTE_TO_STAY = 0.05         # 5% minimum to remain on ballot
    MAX_YEARS_ON_BALLOT = 20

    # Voter count (matches real HOF selection committee size)
    TOTAL_VOTERS = 48

    # Random variance range for vote simulation
    VOTE_VARIANCE = 0.05  # ±5%

    def __init__(self, seed: Optional[int] = None):
        """
        Initialize voting engine.

        Args:
            seed: Optional random seed for reproducible results
        """
        self.scoring_engine = HOFScoringEngine()
        if seed is not None:
            random.seed(seed)

    def conduct_voting(
        self,
        dynasty_id: str,
        voting_season: int,
        candidates: List["HOFCandidate"]
    ) -> HOFVotingSession:
        """
        Conduct annual HOF voting for all eligible candidates.

        Args:
            dynasty_id: Dynasty identifier
            voting_season: Current season year
            candidates: List of eligible HOFCandidate objects

        Returns:
            HOFVotingSession with complete voting results
        """
        if not candidates:
            return HOFVotingSession(
                dynasty_id=dynasty_id,
                voting_season=voting_season,
                total_candidates=0,
                total_voters=self.TOTAL_VOTERS,
            )

        # Calculate class strength (affects borderline candidates)
        class_strength = self._calculate_class_strength(candidates)

        # Simulate votes for each candidate
        voting_results: List[tuple] = []  # (vote_pct, HOFVotingResult)
        for candidate in candidates:
            # Get score breakdown for this candidate
            breakdown = self.scoring_engine.calculate_from_candidate(candidate)

            # Simulate vote percentage
            vote_pct = self._simulate_vote_percentage(
                hof_score=breakdown.total_score,
                years_on_ballot=candidate.years_on_ballot,
                is_first_ballot=candidate.is_first_ballot,
                class_strength=class_strength
            )

            # Calculate actual votes
            votes_received = int(round(vote_pct * self.TOTAL_VOTERS))
            votes_received = max(0, min(self.TOTAL_VOTERS, votes_received))

            # Recalculate percentage from actual votes for consistency
            actual_pct = votes_received / self.TOTAL_VOTERS

            # Check if should be removed from ballot
            removed = self._should_remove_from_ballot(
                vote_percentage=actual_pct,
                years_on_ballot=candidate.years_on_ballot
            )

            # Determine induction status (will be refined after sorting)
            result = HOFVotingResult(
                player_id=candidate.player_id,
                voting_season=voting_season,
                player_name=candidate.player_name,
                primary_position=candidate.primary_position,
                retirement_season=candidate.retirement_season,
                years_on_ballot=candidate.years_on_ballot,
                vote_percentage=actual_pct,
                votes_received=votes_received,
                total_voters=self.TOTAL_VOTERS,
                was_inducted=False,  # Set later
                is_first_ballot=candidate.is_first_ballot,
                removed_from_ballot=removed,
                hof_score=breakdown.total_score,
                score_breakdown=breakdown.to_dict(),
            )

            voting_results.append((actual_pct, result))

        # Sort by vote percentage descending
        voting_results.sort(key=lambda x: x[0], reverse=True)

        # Determine inductees (max 5, must exceed threshold, not removed)
        inductees: List[HOFVotingResult] = []
        non_inductees: List[HOFVotingResult] = []
        removed_from_ballot: List[HOFVotingResult] = []

        for vote_pct, result in voting_results:
            if result.removed_from_ballot:
                # Removed from ballot - cannot be inducted
                removed_from_ballot.append(result)
            elif (vote_pct >= self.INDUCTION_THRESHOLD and
                  len(inductees) < self.MAX_INDUCTEES_PER_YEAR):
                # Inducted!
                result.was_inducted = True
                inductees.append(result)
            else:
                # Not inducted this year
                non_inductees.append(result)

        return HOFVotingSession(
            dynasty_id=dynasty_id,
            voting_season=voting_season,
            inductees=inductees,
            non_inductees=non_inductees,
            removed_from_ballot=removed_from_ballot,
            total_candidates=len(candidates),
            total_voters=self.TOTAL_VOTERS,
            class_strength=class_strength,
        )

    def _calculate_class_strength(
        self,
        candidates: List["HOFCandidate"]
    ) -> float:
        """
        Calculate how strong the overall class is.

        Strong class = multiple first-ballot candidates = harder for borderline.
        Weak class = fewer top candidates = more room for borderline inductees.

        Args:
            candidates: List of HOFCandidate objects

        Returns:
            Class strength (0.0-1.0), where 1.0 is strongest
        """
        if not candidates:
            return 0.5

        # Count candidates in each tier
        first_ballot_count = 0
        strong_count = 0

        for candidate in candidates:
            breakdown = self.scoring_engine.calculate_from_candidate(candidate)
            score = breakdown.total_score

            if score >= 85:
                first_ballot_count += 1
            elif score >= 70:
                strong_count += 1

        # Class strength formula:
        # - 0 first-ballot = weak (0.3)
        # - 1-2 first-ballot = normal (0.5)
        # - 3+ first-ballot = strong (0.7)
        # - Plus adjustment for strong candidates

        if first_ballot_count >= 3:
            base_strength = 0.7
        elif first_ballot_count >= 1:
            base_strength = 0.5
        else:
            base_strength = 0.3

        # Adjust for strong candidates
        strong_adjustment = min(0.15, strong_count * 0.03)

        return min(1.0, base_strength + strong_adjustment)

    def _simulate_vote_percentage(
        self,
        hof_score: int,
        years_on_ballot: int,
        is_first_ballot: bool,
        class_strength: float
    ) -> float:
        """
        Simulate vote percentage for a candidate.

        Base formula maps HOF score to expected vote range, then applies
        modifiers for years on ballot, first-ballot status, and class strength.

        Args:
            hof_score: HOF score (0-100)
            years_on_ballot: Years on ballot including this one
            is_first_ballot: Whether this is first year on ballot
            class_strength: Overall class strength (0.0-1.0)

        Returns:
            Simulated vote percentage (0.0-1.0)
        """
        # Base vote percentage from HOF score
        base_pct = self._score_to_base_vote(hof_score)

        # Modifier: First-ballot bonus
        first_ballot_bonus = 0.0
        if is_first_ballot and hof_score >= 70:
            # Strong first-ballot candidates get a boost
            first_ballot_bonus = 0.05 if hof_score >= 85 else 0.03

        # Modifier: Years on ballot (building support or fatigue)
        years_modifier = self._years_on_ballot_modifier(years_on_ballot, hof_score)

        # Modifier: Class strength (strong class = harder for borderline)
        class_modifier = 0.0
        if 50 <= hof_score < 75:  # Only affects borderline candidates
            # Stronger class reduces vote share for borderline
            class_modifier = (0.5 - class_strength) * 0.10  # ±5%

        # Apply modifiers
        final_pct = base_pct + first_ballot_bonus + years_modifier + class_modifier

        # Add random variance
        variance = random.uniform(-self.VOTE_VARIANCE, self.VOTE_VARIANCE)
        final_pct += variance

        # Clamp to valid range
        return max(0.01, min(0.99, final_pct))

    def _score_to_base_vote(self, hof_score: int) -> float:
        """
        Convert HOF score to base vote percentage.

        Score Ranges -> Vote Ranges:
        - 85-100 (First-ballot lock): 90-99%
        - 70-84 (Strong): 70-89%
        - 55-69 (Borderline): 40-75%
        - 40-54 (Long shot): 10-45%
        - 0-39 (Not HOF): 1-15%

        Args:
            hof_score: HOF score (0-100)

        Returns:
            Base vote percentage (0.0-1.0)
        """
        if hof_score >= 85:
            # First-ballot lock: 90-99% (linear from 85->90% to 100->99%)
            return 0.90 + (hof_score - 85) * 0.006
        elif hof_score >= 70:
            # Strong: 70-89% (linear from 70->70% to 84->89%)
            return 0.70 + (hof_score - 70) * 0.0135
        elif hof_score >= 55:
            # Borderline: 40-75% (linear from 55->40% to 69->75%)
            return 0.40 + (hof_score - 55) * 0.025
        elif hof_score >= 40:
            # Long shot: 10-45% (linear from 40->10% to 54->45%)
            return 0.10 + (hof_score - 40) * 0.025
        else:
            # Not HOF caliber: 1-15% (linear from 0->1% to 39->15%)
            return 0.01 + (hof_score / 39) * 0.14

    def _years_on_ballot_modifier(
        self,
        years_on_ballot: int,
        hof_score: int
    ) -> float:
        """
        Calculate modifier based on years on ballot.

        - Years 2-10: +1-2% per year (building support)
        - Years 11-15: No change (plateau)
        - Years 16-20: -1% per year (voter fatigue)

        Stronger candidates get more support building.

        Args:
            years_on_ballot: Current year on ballot
            hof_score: HOF score

        Returns:
            Vote percentage modifier
        """
        if years_on_ballot <= 1:
            return 0.0

        # Building support phase (years 2-10)
        if years_on_ballot <= 10:
            # Stronger candidates get more support per year
            per_year_boost = 0.02 if hof_score >= 60 else 0.01
            return (years_on_ballot - 1) * per_year_boost

        # Plateau phase (years 11-15)
        if years_on_ballot <= 15:
            # Maintain max support from building phase
            per_year_boost = 0.02 if hof_score >= 60 else 0.01
            return 9 * per_year_boost

        # Voter fatigue phase (years 16-20)
        # Start declining from plateau
        base_support = 0.18 if hof_score >= 60 else 0.09  # Max from building
        fatigue_penalty = (years_on_ballot - 15) * 0.01
        return base_support - fatigue_penalty

    def _should_remove_from_ballot(
        self,
        vote_percentage: float,
        years_on_ballot: int
    ) -> bool:
        """
        Determine if candidate should be removed from ballot.

        Removal conditions:
        - Vote percentage < 5%
        - Years on ballot > 20

        Args:
            vote_percentage: Vote percentage received
            years_on_ballot: Current year on ballot

        Returns:
            True if should be removed
        """
        if vote_percentage < self.MIN_VOTE_TO_STAY:
            return True

        if years_on_ballot >= self.MAX_YEARS_ON_BALLOT:
            return True

        return False

    def simulate_single_candidate(
        self,
        candidate: "HOFCandidate",
        class_strength: float = 0.5
    ) -> tuple:
        """
        Simulate voting for a single candidate (for testing/preview).

        Args:
            candidate: HOFCandidate to simulate
            class_strength: Assumed class strength

        Returns:
            Tuple of (vote_percentage, would_be_inducted, score_breakdown)
        """
        breakdown = self.scoring_engine.calculate_from_candidate(candidate)

        vote_pct = self._simulate_vote_percentage(
            hof_score=breakdown.total_score,
            years_on_ballot=candidate.years_on_ballot,
            is_first_ballot=candidate.is_first_ballot,
            class_strength=class_strength
        )

        would_be_inducted = vote_pct >= self.INDUCTION_THRESHOLD

        return (vote_pct, would_be_inducted, breakdown)
