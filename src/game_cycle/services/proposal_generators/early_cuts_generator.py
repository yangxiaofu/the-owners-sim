"""
Early Cuts Proposal Generator - GM analysis for pre-signing roster cuts.

Analyzes roster and cap situation to recommend cuts that:
1. Create cap space for re-signing/FA
2. Remove aging or underperforming players
3. Minimize dead money impact

Priority for cuts (higher = more likely to recommend):
- High salary, low dead money ratio
- Aging veterans past prime
- Low OVR relative to salary
- Positional depth (backups over starters)
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Set
import json
import logging

from src.utils.player_field_extractors import extract_overall_rating
from game_cycle.models.persistent_gm_proposal import PersistentGMProposal
from game_cycle.models.proposal_enums import ProposalType, ProposalStatus


class EarlyCutsProposalGenerator:
    """
    Generates cut proposals for pre-signing cap relief.

    Analyzes roster players and recommends cuts based on:
    - Cap savings vs dead money ratio
    - Player age and trajectory
    - Overall rating relative to position
    - Positional depth on roster
    """

    # Age thresholds
    VETERAN_AGE = 30
    AGING_VETERAN_AGE = 32

    # OVR thresholds
    ELITE_OVR = 85
    STARTER_OVR = 75
    BACKUP_OVR = 65

    # Dead money ratio threshold (dead_money / cap_savings)
    # Lower is better - means more savings relative to dead money
    GOOD_CUT_RATIO = 0.3  # 30% or less dead money
    OK_CUT_RATIO = 0.5    # 50% or less dead money

    def __init__(
        self,
        db_path: str,
        dynasty_id: str,
        season: int,
        team_id: int,
        cap_shortfall: int = 0,
    ):
        """
        Initialize the generator.

        Args:
            db_path: Path to database
            dynasty_id: Dynasty identifier
            season: Current season year
            team_id: Team ID
            cap_shortfall: How much cap space is needed (0 if not over cap)
        """
        self._db_path = db_path
        self._dynasty_id = dynasty_id
        self._season = season
        self._team_id = team_id
        self._cap_shortfall = cap_shortfall
        self._logger = logging.getLogger(__name__)

    def generate_proposals(
        self,
        roster_players: List[Dict[str, Any]],
        excluded_player_ids: Optional[Set[int]] = None,
    ) -> List[PersistentGMProposal]:
        """
        Generate cut proposals for roster players.

        Args:
            roster_players: List of player dicts with cap impact info
            excluded_player_ids: Players to exclude (e.g., in extension proposals)

        Returns:
            List of PersistentGMProposal for recommended cuts
        """
        if not roster_players:
            return []

        excluded = excluded_player_ids or set()
        proposals = []

        # Score each player for cut potential
        scored_players = []
        for player in roster_players:
            player_id = player.get("player_id")

            if player_id in excluded:
                continue

            score, reasoning = self._score_cut_candidate(player)
            if score > 0:
                scored_players.append({
                    "player": player,
                    "score": score,
                    "reasoning": reasoning,
                })

        # Sort by score descending (higher = better cut candidate)
        scored_players.sort(key=lambda x: x["score"], reverse=True)

        # If over cap, select enough cuts to reach compliance
        if self._cap_shortfall > 0:
            total_savings = 0
            for sp in scored_players:
                player = sp["player"]
                net_savings = player.get("net_change", 0)

                proposal = self._create_proposal(player, sp["reasoning"])
                proposals.append(proposal)

                total_savings += net_savings
                if total_savings >= self._cap_shortfall:
                    break
        else:
            # Not over cap - just recommend top cuts for cap flexibility
            # Limit to top 5 recommendations
            for sp in scored_players[:5]:
                player = sp["player"]
                proposal = self._create_proposal(player, sp["reasoning"])
                proposals.append(proposal)

        return proposals

    def _score_cut_candidate(self, player: Dict[str, Any]) -> tuple[float, str]:
        """
        Score a player as a cut candidate.

        Prioritizes:
        1. Expensive backups with low snap counts
        2. Players who missed significant games
        3. Overpaid players relative to production
        4. Favorable dead money ratio

        Args:
            player: Player dict with cap, attribute, and season stats info

        Returns:
            Tuple of (score, reasoning). Score > 0 means recommend cut.
        """
        score = 0.0
        reasons = []

        cap_savings = player.get("cap_savings", 0)
        dead_money = player.get("dead_money", 0)
        net_change = player.get("net_change", 0)
        age = player.get("age", 0)
        overall = extract_overall_rating(player, default=0)
        snaps = player.get("snaps", 0)
        games_played = player.get("games_played", 0)

        # Can't recommend if no savings
        if net_change <= 0:
            return 0, "No cap benefit"

        # ==== NEW: Production-based scoring ====
        # Uses absolute snap counts rather than salary ratios
        # (salary ratios unfairly penalize high-paid starters)

        # Low snap count = potential cut candidate
        # Starter threshold: ~800+ snaps (offense/defense plays ~1100 snaps/season)
        # Backup threshold: <400 snaps
        if snaps == 0 and cap_savings > 1_000_000:
            # Expensive player with no recorded snaps
            score += 35
            reasons.append("no recorded playing time")
        elif snaps > 0 and snaps < 300:
            # Very low snaps - deep backup or inactive
            if cap_savings > 2_000_000:
                score += 30
                reasons.append(f"expensive depth ({snaps} snaps)")
            else:
                score += 15
                reasons.append(f"limited snaps ({snaps})")
        elif snaps > 0 and snaps < 500:
            # Low snaps - rotational/backup player
            if cap_savings > 5_000_000:
                score += 25
                reasons.append(f"overpaid backup ({snaps} snaps)")
            elif cap_savings > 2_000_000:
                score += 15
                reasons.append("expensive rotational player")

        # Missed games penalty
        if games_played > 0 and games_played < 10:  # Played less than 10 of 17 games
            missed = 17 - games_played
            score += missed * 2  # 2 points per missed game
            reasons.append(f"missed {missed} games")
        elif games_played == 0 and cap_savings > 500_000:
            # Player didn't appear in any games
            score += 25
            reasons.append("did not play")

        # Protect productive starters (high snap count)
        if snaps >= 800:
            # Player is a clear starter - reduce cut score
            score -= 15
            if snaps >= 1000:
                score -= 10  # Extra protection for every-down players

        # ==== Original scoring (with reduced weights) ====

        # Dead money ratio scoring
        if cap_savings > 0:
            dead_ratio = dead_money / cap_savings
            if dead_ratio <= self.GOOD_CUT_RATIO:
                score += 20  # Reduced from 30
                reasons.append("minimal dead money")
            elif dead_ratio <= self.OK_CUT_RATIO:
                score += 10  # Reduced from 15
                reasons.append("acceptable dead money")
            else:
                score -= 15  # High dead money penalty

        # Net savings scoring (REDUCED weight - was 5, now 2)
        net_millions = net_change / 1_000_000
        score += net_millions * 2

        # Age scoring
        if age >= self.AGING_VETERAN_AGE:
            score += 15
            reasons.append(f"aging veteran ({age})")
        elif age >= self.VETERAN_AGE:
            score += 8
            reasons.append(f"veteran ({age})")

        # OVR scoring (inverse - lower OVR = better cut candidate)
        if overall < self.BACKUP_OVR:
            score += 10
            reasons.append(f"low rating ({overall} OVR)")
        elif overall < self.STARTER_OVR:
            score += 5
            reasons.append("depth player")
        elif overall >= self.ELITE_OVR:
            # Elite players still get a penalty, but production matters more now
            score -= 20
            if snaps > 800:  # Elite player who actually played
                score -= 15  # Additional protection
                reasons.append("elite contributor")

        # Value scoring: salary vs OVR
        if cap_savings > 0 and overall > 0:
            salary_per_ovr = cap_savings / overall
            if salary_per_ovr > 150_000:  # Overpaid threshold
                score += 10
                reasons.append("overpaid for rating")

        # Build reasoning string
        if not reasons:
            reasons.append("cap savings available")

        reasoning = ", ".join(reasons).capitalize()

        return score, reasoning

    def _create_proposal(
        self, player: Dict[str, Any], reasoning: str
    ) -> PersistentGMProposal:
        """Create a cut proposal for a player."""
        player_id = player.get("player_id")
        player_name = player.get("player_name", "Unknown")
        position = player.get("position", "")
        cap_savings = player.get("cap_savings", 0)
        dead_money = player.get("dead_money", 0)
        net_change = player.get("net_change", 0)

        details = {
            "player_id": player_id,
            "player_name": player_name,
            "position": position,
            "cap_savings": cap_savings,
            "dead_money": dead_money,
            "net_change": net_change,
            "age": player.get("age", 0),
            "overall": extract_overall_rating(player, default=0),
        }

        # Format reasoning with savings
        net_millions = net_change / 1_000_000
        full_reasoning = f"{reasoning} - saves ${net_millions:.1f}M net"

        return PersistentGMProposal(
            dynasty_id=self._dynasty_id,
            team_id=self._team_id,
            season=self._season,
            stage="OFFSEASON_RESIGNING",
            proposal_type=ProposalType.CUT,
            details=details,
            gm_reasoning=full_reasoning,
            subject_player_id=str(player_id),
            confidence=min(0.9, 0.5 + (net_millions * 0.1)),  # Higher savings = higher confidence
            priority=int(net_change // 100_000),  # Priority based on savings
            created_at=datetime.now(),
        )
