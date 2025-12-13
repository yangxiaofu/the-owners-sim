"""
Voting Simulation Engine for NFL Awards.

Simulates 50 media voters selecting award winners using a
10-5-3-2-1 point allocation system. Each voter has an archetype
that influences how they weight different performance metrics.

Part of Milestone 10: Awards System, Tollgate 3.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import random

from .models import AwardScore
from .voter_archetypes import (
    VoterArchetype,
    VoterProfile,
    TRADITIONAL_POSITION_BIAS,
    VOTER_DISTRIBUTION,
)

logger = logging.getLogger(__name__)


# ============================================
# Voting Constants
# ============================================

# Point allocation for rankings (NFL-style voting)
POINTS_BY_RANK: Dict[int, int] = {
    1: 10,  # First place
    2: 5,   # Second place
    3: 3,   # Third place
    4: 2,   # Fourth place
    5: 1,   # Fifth place
}

# Default number of voters
DEFAULT_NUM_VOTERS = 50

# Maximum possible points (50 voters x 10 points each)
MAX_POINTS = DEFAULT_NUM_VOTERS * POINTS_BY_RANK[1]  # 500


# ============================================
# Voting Result
# ============================================

@dataclass
class VotingResult:
    """
    Result of voting for a single candidate.

    Contains the final vote tallies including points, vote share,
    and breakdown by ranking position.

    Attributes:
        player_id: The player's unique identifier
        player_name: Display name
        team_id: Team ID (1-32)
        position: Player's position
        total_points: Weighted points from all voters
        vote_share: Percentage of maximum points (0.0-1.0)
        first_place_votes: Count of first-place votes received
        second_place_votes: Count of second-place votes
        third_place_votes: Count of third-place votes
        fourth_place_votes: Count of fourth-place votes
        fifth_place_votes: Count of fifth-place votes
        raw_score: Original score from award criteria (pre-voting)
    """
    player_id: int
    player_name: str
    team_id: int
    position: str
    total_points: int = 0
    vote_share: float = 0.0
    first_place_votes: int = 0
    second_place_votes: int = 0
    third_place_votes: int = 0
    fourth_place_votes: int = 0
    fifth_place_votes: int = 0
    raw_score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'player_id': self.player_id,
            'player_name': self.player_name,
            'team_id': self.team_id,
            'position': self.position,
            'total_points': self.total_points,
            'vote_share': self.vote_share,
            'first_place_votes': self.first_place_votes,
            'second_place_votes': self.second_place_votes,
            'third_place_votes': self.third_place_votes,
            'fourth_place_votes': self.fourth_place_votes,
            'fifth_place_votes': self.fifth_place_votes,
            'raw_score': self.raw_score,
        }

    @property
    def total_votes_received(self) -> int:
        """Total number of voters who ranked this candidate."""
        return (
            self.first_place_votes +
            self.second_place_votes +
            self.third_place_votes +
            self.fourth_place_votes +
            self.fifth_place_votes
        )

    @property
    def is_unanimous(self) -> bool:
        """Check if this was a unanimous first-place selection."""
        return self.first_place_votes == DEFAULT_NUM_VOTERS

    def __repr__(self) -> str:
        return (
            f"VotingResult({self.player_name}, "
            f"points={self.total_points}, "
            f"share={self.vote_share:.1%}, "
            f"1st={self.first_place_votes})"
        )


# ============================================
# Voting Engine
# ============================================

class VotingEngine:
    """
    Simulates 50 media voters for award selection.

    Uses archetype-based scoring with variance to create
    realistic voting patterns. Each voter independently
    ranks their top 5 candidates, with points allocated
    using a 10-5-3-2-1 system.

    Typical Results:
    - Landslide winner: 450+ points (90%+ vote share)
    - Clear winner: 350-450 points (70-90%)
    - Contested: 250-350 points (50-70%)
    - Close race: <250 points (<50%)

    Usage:
        engine = VotingEngine(seed=42)  # Deterministic for testing
        results = engine.conduct_voting("mvp", candidates)
        winner = results[0]  # Highest vote-getter
    """

    def __init__(self, num_voters: int = DEFAULT_NUM_VOTERS, seed: Optional[int] = None):
        """
        Initialize the voting engine.

        Args:
            num_voters: Number of voters to simulate (default 50)
            seed: Optional random seed for deterministic results
        """
        self.num_voters = num_voters
        self.seed = seed
        self.rng = random.Random(seed)
        self.voters = self._generate_voters()
        self._max_points = num_voters * POINTS_BY_RANK[1]

    def _generate_voters(self) -> List[VoterProfile]:
        """
        Generate voters with archetype distribution.

        Uses the standard distribution:
        - 20 BALANCED (40%)
        - 10 STATS_FOCUSED (20%)
        - 10 ANALYTICS (20%)
        - 5 NARRATIVE_DRIVEN (10%)
        - 5 TRADITIONAL (10%)

        Each voter gets a random variance factor (0.05-0.15).

        Returns:
            List of VoterProfile instances
        """
        voters: List[VoterProfile] = []
        voter_num = 0

        # Scale distribution if num_voters differs from 50
        scale = self.num_voters / DEFAULT_NUM_VOTERS

        for archetype, base_count in VOTER_DISTRIBUTION:
            count = max(1, int(base_count * scale))

            for _ in range(count):
                voter_num += 1

                # Random variance between 5% and 15%
                variance = self.rng.uniform(0.05, 0.15)

                # Position bias only for TRADITIONAL voters
                position_bias = (
                    TRADITIONAL_POSITION_BIAS.copy()
                    if archetype == VoterArchetype.TRADITIONAL
                    else {}
                )

                voters.append(VoterProfile(
                    voter_id=f"voter_{voter_num:02d}",
                    archetype=archetype,
                    variance=variance,
                    position_bias=position_bias,
                ))

        # If scaling caused us to go over, trim
        # If under, the last archetype gets extras
        while len(voters) > self.num_voters:
            voters.pop()
        while len(voters) < self.num_voters:
            voter_num += 1
            voters.append(VoterProfile(
                voter_id=f"voter_{voter_num:02d}",
                archetype=VoterArchetype.BALANCED,
                variance=self.rng.uniform(0.05, 0.15),
                position_bias={},
            ))

        return voters

    def conduct_voting(
        self,
        award_id: str,
        candidates: List[AwardScore]
    ) -> List[VotingResult]:
        """
        Conduct voting for an award.

        Each voter scores all candidates through their archetype lens,
        then ranks their top 5. Points are awarded using the
        10-5-3-2-1 system.

        Args:
            award_id: The award being voted on (for logging)
            candidates: List of AwardScore from criteria calculation

        Returns:
            List of VotingResult sorted by total_points descending
        """
        if not candidates:
            logger.warning(f"No candidates provided for {award_id} voting")
            return []

        logger.info(
            f"Conducting {award_id} voting with {len(candidates)} candidates "
            f"and {self.num_voters} voters"
        )

        # Initialize results dict keyed by player_id
        results: Dict[int, VotingResult] = {}
        for c in candidates:
            results[c.player_id] = VotingResult(
                player_id=c.player_id,
                player_name=c.player_name,
                team_id=c.team_id,
                position=c.position,
                raw_score=c.final_score,
            )

        # Each voter ranks candidates
        for voter in self.voters:
            self._process_voter_ballot(voter, candidates, results)

        # Calculate vote share for each candidate
        for result in results.values():
            result.vote_share = result.total_points / self._max_points

        # Sort by (points, 1st votes, 2nd votes, raw_score) descending
        sorted_results = self._sort_results(list(results.values()))

        # Log results summary
        if sorted_results:
            winner = sorted_results[0]
            logger.info(
                f"{award_id} winner: {winner.player_name} "
                f"({winner.total_points} pts, {winner.vote_share:.1%}, "
                f"{winner.first_place_votes} 1st-place votes)"
            )

        return sorted_results

    def _process_voter_ballot(
        self,
        voter: VoterProfile,
        candidates: List[AwardScore],
        results: Dict[int, VotingResult]
    ) -> None:
        """
        Process a single voter's ballot.

        Scores all candidates through this voter's lens,
        then awards points to the top 5.

        Args:
            voter: The voter casting their ballot
            candidates: All award candidates
            results: Results dict to update (mutated in place)
        """
        # Score all candidates through this voter's preferences
        scored: List[tuple[int, float]] = [
            (c.player_id, voter.adjust_score(c, self.rng))
            for c in candidates
        ]

        # Sort by adjusted score descending
        scored.sort(key=lambda x: x[1], reverse=True)

        # Award points to top 5 (or fewer if not enough candidates)
        for rank, (player_id, _score) in enumerate(scored[:5], start=1):
            result = results[player_id]
            result.total_points += POINTS_BY_RANK[rank]

            # Track vote breakdown
            if rank == 1:
                result.first_place_votes += 1
            elif rank == 2:
                result.second_place_votes += 1
            elif rank == 3:
                result.third_place_votes += 1
            elif rank == 4:
                result.fourth_place_votes += 1
            elif rank == 5:
                result.fifth_place_votes += 1

    def _sort_results(self, results: List[VotingResult]) -> List[VotingResult]:
        """
        Sort voting results with tiebreaker logic.

        Tiebreaker order:
        1. Total points (primary)
        2. First-place votes
        3. Second-place votes
        4. Raw score (original criteria score)

        Args:
            results: Unsorted voting results

        Returns:
            Sorted list (highest first)
        """
        return sorted(
            results,
            key=lambda r: (
                r.total_points,
                r.first_place_votes,
                r.second_place_votes,
                r.raw_score,
            ),
            reverse=True,
        )

    def get_voter_breakdown(self) -> Dict[str, int]:
        """
        Get breakdown of voter archetypes.

        Returns:
            Dict mapping archetype name to count
        """
        breakdown: Dict[str, int] = {}
        for voter in self.voters:
            key = voter.archetype.value
            breakdown[key] = breakdown.get(key, 0) + 1
        return breakdown

    def reset_seed(self, seed: Optional[int] = None) -> None:
        """
        Reset the random seed and regenerate voters.

        Useful for running multiple deterministic simulations.

        Args:
            seed: New seed (or None for random)
        """
        self.seed = seed
        self.rng = random.Random(seed)
        self.voters = self._generate_voters()

    def __repr__(self) -> str:
        return (
            f"VotingEngine(num_voters={self.num_voters}, "
            f"seed={self.seed})"
        )
