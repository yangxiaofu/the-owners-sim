"""
Trade Proposal Generator - Generate trade proposals based on owner directives.

Part of Tollgate 8: Trade Integration.

Analyzes owner's strategic directives and generates PersistentGMProposal objects
for trades that align with the team's philosophy and goals.

Trade Strategy by Philosophy:
- WIN_NOW: Acquire talent at priority positions, trade picks/young depth
- REBUILD: Acquire draft picks/young players, trade expensive veterans
- MAINTAIN: Balanced value upgrades

Priority Tiers:
- TIER 1: Shop expendable players (always active)
- TIER 2: Acquire at priority positions (win_now)
- TIER 3: Value upgrades (maintain)
- TIER 4: Acquire draft picks (rebuild)
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple
import json
import logging
import re

from src.utils.player_field_extractors import extract_overall_rating
from game_cycle.models.owner_directives import OwnerDirectives
try:
    from utils.team_utils import get_team_name as get_team_name_util
except ImportError:
    from src.utils.team_utils import get_team_name as get_team_name_util
from constants.position_abbreviations import get_position_abbreviation
from game_cycle.models.persistent_gm_proposal import (
    PersistentGMProposal,
    create_trade_details,
)
from game_cycle.models.proposal_enums import ProposalType, ProposalStatus
from game_cycle.services.trade_service import TradeService
from transactions.models import TradeDecisionType


class TradeProposalGenerator:
    """
    Generate trade proposals based on owner directives.

    Respects:
    - Protected players (NEVER trade)
    - Expendable players (actively shop)
    - Priority positions (target acquisitions)
    - Team philosophy (strategy approach)

    Max proposals by philosophy:
    - WIN_NOW: 5 proposals (aggressive acquisition)
    - MAINTAIN: 3 proposals (balanced approach)
    - REBUILD: 4 proposals (picks and prospects)
    """

    # Priority tiers (lower = higher priority)
    TIER_EXPENDABLE_SHOPPING = 1
    TIER_PRIORITY_POSITION = 2
    TIER_VALUE_UPGRADE = 3
    TIER_PICK_ACQUISITION = 4

    # Proposal limits by philosophy
    PHILOSOPHY_LIMITS = {
        "win_now": 5,
        "maintain": 3,
        "rebuild": 4,
    }

    # Minimum overall ratings for acquisition targets
    MIN_OVERALL_WIN_NOW = 78
    MIN_OVERALL_MAINTAIN = 75
    MIN_OVERALL_REBUILD_YOUNG = 72

    # Age thresholds
    MAX_AGE_WIN_NOW = 32  # Still productive veterans
    MAX_AGE_REBUILD_YOUNG = 26  # Young players with upside
    MIN_AGE_VETERAN = 28  # Veteran to trade away in rebuild

    # Untouchable player thresholds (v1.2 - trade realism)
    UNTOUCHABLE_ELITE_MIN_OVR = 90  # Elite players at this OVR are untouchable
    UNTOUCHABLE_ELITE_MAX_AGE = 29  # Under 30 for elite untouchable
    UNTOUCHABLE_QB_MIN_OVR = 85  # Franchise QBs at this OVR are untouchable
    UNTOUCHABLE_QB_MAX_AGE = 31  # Under 32 for franchise QB untouchable

    # Default priority positions when none specified (v1.2 - trade realism)
    DEFAULT_WIN_NOW_POSITIONS = ["EDGE", "CB", "WR", "OT", "DT"]
    """Premium impact positions for Win-Now teams to target in trades."""

    # Cap-related thresholds
    MIN_CAP_HIT_FOR_TRADE = 2_000_000  # Minimum cap hit to consider trading
    MIN_MEANINGFUL_CAP_SAVINGS = 1_000_000  # Minimum savings worth pursuing
    CAP_SAFETY_BUFFER = 5_000_000  # Buffer for cap validation

    # Player value thresholds
    HIGH_VALUE_PLAYER_OVR = 82  # Players we want to keep (don't trade away)

    # Trade value thresholds
    # Don't propose trades where we lose more than this amount of value
    MAX_ACCEPTABLE_VALUE_LOSS = 500_000  # $500K maximum loss
    # Minimum value ratio (our_value / their_value) to propose trade
    MIN_ACCEPTABLE_VALUE_RATIO = 0.85  # Accept slight overpays for desired targets

    # Team iteration
    ALL_TEAM_IDS = range(1, 33)

    # v1.3 Stats Weighting: League averages for relative performance calculation
    # Based on realistic NFL starter averages per 17-game season
    LEAGUE_AVERAGES = {
        "QB": {"passing_yards": 4000, "passing_tds": 25},
        "RB": {"rushing_yards": 800, "rushing_tds": 6},
        "WR": {"receiving_yards": 700, "receiving_tds": 5},
        "TE": {"receiving_yards": 500, "receiving_tds": 4},
        "EDGE": {"sacks": 6.0, "tackles_total": 40},
        "DE": {"sacks": 6.0, "tackles_total": 40},
        "DT": {"sacks": 2.0, "tackles_total": 35},
        "LB": {"tackles_total": 80, "sacks": 2.0},
        "MLB": {"tackles_total": 100, "sacks": 1.0},
        "CB": {"interceptions": 2, "passes_defended": 8},
        "S": {"tackles_total": 60, "interceptions": 1.5},
        "FS": {"tackles_total": 50, "interceptions": 2},
        "SS": {"tackles_total": 70, "interceptions": 1},
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
        Initialize the trade proposal generator.

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
        self._logger = logging.getLogger(__name__)

        # Lazy-loaded
        self._trade_service: Optional[TradeService] = None

        # Performance optimization: cache team assets upfront
        self._players_cache: Dict[int, List[Dict[str, Any]]] = {}
        self._picks_cache: Dict[int, List[Dict[str, Any]]] = {}
        self._stats_cache: Dict[int, Dict[str, Any]] = {}  # player_id -> stats
        self._stats_api = None  # Lazy-loaded

    def _get_stats_api(self):
        """Lazy-load the PlayerSeasonStatsAPI."""
        if self._stats_api is None:
            from game_cycle.database.player_stats_api import PlayerSeasonStatsAPI
            self._stats_api = PlayerSeasonStatsAPI(self._db_path)
        return self._stats_api

    def _get_player_stats(self, player_id: int, team_id: int) -> Optional[Dict[str, Any]]:
        """
        Get player's previous season stats (cached).

        Args:
            player_id: Player ID
            team_id: Team ID the player was on

        Returns:
            Stats dict or None if not found
        """
        if player_id in self._stats_cache:
            return self._stats_cache[player_id]

        try:
            # Get previous season stats (trade value based on recent performance)
            prev_season = self._season - 1
            stats_api = self._get_stats_api()
            team_stats = stats_api.get_team_player_stats(
                dynasty_id=self._dynasty_id,
                team_id=team_id,
                season=prev_season,
                season_type='regular_season'
            )
            player_stats = team_stats.get(player_id)
            self._stats_cache[player_id] = player_stats
            return player_stats
        except Exception as e:
            self._logger.debug(f"Could not fetch stats for player {player_id}: {e}")
            return None

    def _get_stats_modifier(self, player: Dict) -> float:
        """
        Calculate stats-based value modifier (0.8 to 1.2).

        v1.3: Uses relative performance vs position-group average.
        Players who outperformed get a value boost, underperformers get penalized.

        Args:
            player: Player dict with player_id, position, team_id

        Returns:
            Modifier between 0.8 (poor stats) and 1.2 (elite stats)
        """
        position = self._normalize_position(player.get("position"))
        player_id = player.get("player_id")
        team_id = player.get("team_id", self._team_id)

        # Get player's previous season stats
        stats = self._get_player_stats(player_id, team_id)
        if not stats or stats.get("games_played", 0) < 4:
            return 1.0  # Not enough data, use neutral modifier

        # Get league averages for this position
        league_avg = self.LEAGUE_AVERAGES.get(position, {})
        if not league_avg:
            return 1.0  # No benchmarks for this position

        # Calculate relative performance based on position
        relative = 1.0

        if position == "QB":
            avg_yards = league_avg.get("passing_yards", 4000)
            if avg_yards > 0:
                relative = stats.get("passing_yards", 0) / avg_yards

        elif position == "RB":
            avg_yards = league_avg.get("rushing_yards", 800)
            if avg_yards > 0:
                relative = stats.get("rushing_yards", 0) / avg_yards

        elif position in ["WR", "TE"]:
            avg_yards = league_avg.get("receiving_yards", 600)
            if avg_yards > 0:
                relative = stats.get("receiving_yards", 0) / avg_yards

        elif position in ["EDGE", "DE"]:
            avg_sacks = league_avg.get("sacks", 6.0)
            if avg_sacks > 0:
                relative = stats.get("sacks", 0) / avg_sacks

        elif position in ["DT"]:
            avg_sacks = league_avg.get("sacks", 2.0)
            avg_tackles = league_avg.get("tackles_total", 35)
            if avg_sacks > 0 and avg_tackles > 0:
                sack_rel = stats.get("sacks", 0) / avg_sacks
                tackle_rel = stats.get("tackles_total", 0) / avg_tackles
                relative = (sack_rel + tackle_rel) / 2

        elif position in ["LB", "MLB", "MIKE", "WILL", "SAM"]:
            avg_tackles = league_avg.get("tackles_total", 80)
            if avg_tackles > 0:
                relative = stats.get("tackles_total", 0) / avg_tackles

        elif position in ["CB"]:
            avg_ints = league_avg.get("interceptions", 2)
            avg_pd = league_avg.get("passes_defended", 8)
            if (avg_ints + avg_pd) > 0:
                coverage = stats.get("interceptions", 0) + stats.get("passes_defended", 0)
                relative = coverage / (avg_ints + avg_pd)

        elif position in ["S", "FS", "SS"]:
            avg_tackles = league_avg.get("tackles_total", 60)
            avg_ints = league_avg.get("interceptions", 1.5)
            if avg_tackles > 0:
                tackle_rel = stats.get("tackles_total", 0) / avg_tackles
                int_rel = stats.get("interceptions", 0) / max(avg_ints, 0.5)
                relative = (tackle_rel * 0.6) + (int_rel * 0.4)

        # Calculate modifier: 0.8 base + 0.4 scaled by relative (capped at 1.5x)
        # 0x relative → 0.8, 1x relative → 1.0, 1.5x+ relative → 1.2
        clamped_relative = min(relative, 1.5)
        modifier = 0.8 + (0.4 * clamped_relative / 1.5)

        self._logger.debug(
            f"Stats modifier for {player.get('name', 'Unknown')} ({position}): "
            f"relative={relative:.2f}, modifier={modifier:.2f}"
        )

        return modifier

    def _get_trade_service(self) -> TradeService:
        """Get or create TradeService instance."""
        if self._trade_service is None:
            self._trade_service = TradeService(
                db_path=self._db_path,
                dynasty_id=self._dynasty_id,
                season=self._season
            )
        return self._trade_service

    @property
    def _protected_set(self) -> Set[int]:
        """Cached set of protected player IDs."""
        if not hasattr(self, '_cached_protected_set'):
            self._cached_protected_set = set(self._directives.protected_player_ids)
        return self._cached_protected_set

    def _normalize_position(self, raw_position: Any) -> str:
        """
        Normalize position to uppercase abbreviation.

        Handles various formats:
        - JSON array string: '["edge"]' -> 'EDGE'
        - Full name: 'cornerback' -> 'CB'
        - Already abbreviation: 'CB' -> 'CB'

        Returns:
            Uppercase position abbreviation, or empty string if invalid
        """
        if not raw_position:
            return ""

        pos_str = str(raw_position)

        # Handle JSON array format: '["edge"]' or '["wide_receiver", "kick_returner"]'
        if pos_str.startswith("["):
            try:
                positions = json.loads(pos_str)
                if positions and isinstance(positions, list):
                    pos_str = positions[0]  # Take primary position
            except (json.JSONDecodeError, TypeError):
                return ""

        # Convert to abbreviation using the position mapping
        pos_str = pos_str.lower().strip()
        return get_position_abbreviation(pos_str).upper()

    def _get_team_players(self, team_id: int) -> List[Dict[str, Any]]:
        """
        Get tradeable players for a team (with lazy caching).

        Performance optimization: Each team's data is loaded once and cached
        for reuse across multiple proposal generation methods.
        """
        if team_id not in self._players_cache:
            self._players_cache[team_id] = self._get_trade_service().get_tradeable_players(team_id)
        return self._players_cache[team_id]

    def _get_team_picks(self, team_id: int) -> List[Dict[str, Any]]:
        """
        Get tradeable picks for a team (with lazy caching).

        Performance optimization: Each team's data is loaded once and cached
        for reuse across multiple proposal generation methods.
        """
        if team_id not in self._picks_cache:
            self._picks_cache[team_id] = self._get_trade_service().get_tradeable_picks(team_id)
        return self._picks_cache[team_id]

    # =========================================================================
    # Roster Analysis (v1.3 - Variety Fix)
    # =========================================================================

    # Position importance weights for prioritizing needs
    POSITION_WEIGHTS = {
        "QB": 2.0,    # Franchise QB most valuable
        "EDGE": 1.5,  # Premium pass rushers
        "CB": 1.3,    # Premium corners
        "OT": 1.2,    # Protect the QB
        "WR": 1.1,    # Playmakers
        "DT": 1.0,
        "LB": 0.9,
        "S": 0.9,
        "TE": 0.8,
        "RB": 0.7,    # Replaceable position
    }

    # Starter OVR thresholds - below this = need
    POSITION_THRESHOLDS = {
        "QB": 80, "EDGE": 78, "CB": 77, "WR": 76, "OT": 76,
        "DT": 76, "LB": 75, "S": 75, "TE": 74, "RB": 73,
    }

    def _analyze_roster_needs(self) -> List[Dict[str, Any]]:
        """
        Analyze our roster to find positions needing upgrades.

        Compares best player at each position against thresholds to
        identify gaps. Each team gets different needs based on their
        specific roster composition.

        Returns:
            List of need dicts sorted by priority_score (highest first):
            {position, current_ovr, threshold, gap, priority_score}
        """
        our_players = self._get_team_players(self._team_id)

        # Find starter (highest OVR) at each position
        starters_by_pos: Dict[str, Dict[str, Any]] = {}
        for player in our_players:
            pos = self._normalize_position(player.get("position"))
            if not pos:
                continue

            ovr = extract_overall_rating(player, default=0)
            if pos not in starters_by_pos or ovr > starters_by_pos[pos]["ovr"]:
                starters_by_pos[pos] = {"ovr": ovr, "player": player}

        # Calculate needs - positions where starter is below threshold
        needs = []
        for pos, threshold in self.POSITION_THRESHOLDS.items():
            starter = starters_by_pos.get(pos, {"ovr": 60})
            gap = threshold - starter["ovr"]

            if gap > 0:  # Below threshold = need
                weight = self.POSITION_WEIGHTS.get(pos, 1.0)
                needs.append({
                    "position": pos,
                    "current_ovr": starter["ovr"],
                    "threshold": threshold,
                    "gap": gap,
                    "priority_score": gap * weight,
                })

        # Sort by priority score (biggest gaps at premium positions first)
        needs.sort(key=lambda n: n["priority_score"], reverse=True)

        self._logger.debug(
            f"Roster needs for team {self._team_id}: "
            f"{[f'{n['position']}({n['current_ovr']}/{n['threshold']})' for n in needs[:5]]}"
        )

        return needs[:5]  # Top 5 needs

    def _find_targets_for_need(
        self,
        need: Dict[str, Any],
        min_improvement: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Find players that would improve a specific roster weakness.

        Unlike _find_best_target_at_position (which returns THE best player
        league-wide), this returns candidates that provide meaningful
        upgrades over our current starter.

        v1.3: Uses deterministic shuffling based on team_id to ensure
        different teams get different candidate orderings, creating
        variety in trade targets.

        Args:
            need: From _analyze_roster_needs() with position, current_ovr
            min_improvement: Minimum OVR improvement required (default 3)

        Returns:
            List of up to 5 candidate players that improve our weakness
        """
        position = need["position"]
        current_ovr = need["current_ovr"]
        min_target_ovr = current_ovr + min_improvement

        candidates = []
        for team_id in self.ALL_TEAM_IDS:
            if team_id == self._team_id:
                continue

            for player in self._get_team_players(team_id):
                # Skip untouchable players
                if self._is_untouchable(player):
                    continue

                player_pos = self._normalize_position(player.get("position"))
                player_ovr = extract_overall_rating(player, default=0)
                player_age = player.get("age", 99)

                # Must match position, be high enough OVR, and not too old
                if (
                    player_pos == position
                    and player_ovr >= min_target_ovr
                    and player_age <= self.MAX_AGE_WIN_NOW
                ):
                    candidates.append({
                        **player,
                        "team_id": team_id,
                        "team_name": self._get_team_name(team_id),
                        "improvement": player_ovr - current_ovr,
                    })

        # v1.3: Deterministic shuffle based on team_id for variety
        # This ensures different teams prioritize different candidates
        # while remaining reproducible for testing
        if candidates:
            # Sort primarily by improvement, but use team_id as tiebreaker
            # Different teams will prefer different players with same improvement
            candidates.sort(
                key=lambda c: (
                    -c["improvement"],  # Higher improvement first
                    (c["player_id"] + self._team_id) % 100,  # Team-specific ordering
                )
            )

        self._logger.debug(
            f"Found {len(candidates)} candidates for {position} need "
            f"(current: {current_ovr}, min target: {min_target_ovr})"
        )

        return candidates[:5]

    def generate_proposals(self) -> List[PersistentGMProposal]:
        """
        Generate trade proposals based on owner directives.

        Flow:
        1. Shop expendable players to find interested teams
        2. Based on philosophy:
           - WIN_NOW: Target acquisitions at priority positions
           - REBUILD: Trade veterans for picks
           - MAINTAIN: Find value upgrades

        Returns:
            List of PersistentGMProposal objects sorted by priority
        """
        proposals: List[PersistentGMProposal] = []
        philosophy = self._directives.team_philosophy

        self._logger.info(
            f"Generating trade proposals for team {self._team_id} "
            f"with {philosophy} philosophy"
        )

        # TIER 1: Shop expendable players (always active)
        if self._directives.expendable_player_ids:
            expendable_proposals = self._shop_expendable_players()
            proposals.extend(expendable_proposals)
            self._logger.debug(
                f"Generated {len(expendable_proposals)} expendable player proposals"
            )

        # Philosophy-specific proposals
        if philosophy == "win_now":
            # TIER 2: Acquire at priority positions
            # v1.2 Trade Realism: Use default positions if none specified
            acquisition_proposals = self._find_acquisition_targets()
            proposals.extend(acquisition_proposals)
            self._logger.debug(
                f"Generated {len(acquisition_proposals)} acquisition proposals"
            )

        elif philosophy == "rebuild":
            # TIER 4: Trade veterans for picks
            rebuild_proposals = self._generate_rebuild_trades()
            proposals.extend(rebuild_proposals)
            self._logger.debug(
                f"Generated {len(rebuild_proposals)} rebuild proposals"
            )

        elif philosophy == "maintain":
            # TIER 3: Value upgrades
            value_proposals = self._find_value_upgrades()
            proposals.extend(value_proposals)
            self._logger.debug(
                f"Generated {len(value_proposals)} value upgrade proposals"
            )

        # Sort by priority (lower = higher) and limit
        proposals.sort(key=lambda p: (p.priority, -p.confidence))
        max_proposals = self.PHILOSOPHY_LIMITS.get(philosophy, 3)
        limited = proposals[:max_proposals]

        self._logger.info(
            f"Returning {len(limited)} trade proposals "
            f"(from {len(proposals)} generated)"
        )

        return limited

    # =========================================================================
    # Expendable Player Shopping (TIER 1)
    # =========================================================================

    def _shop_expendable_players(self) -> List[PersistentGMProposal]:
        """
        Shop expendable players to all other teams.

        For each expendable player:
        1. Get their trade value
        2. Offer to all 31 other teams
        3. Find best offer using evaluate_ai_trade
        4. Create proposal if interested team found

        Returns:
            List of proposals for expendable player trades
        """
        proposals: List[PersistentGMProposal] = []

        # Get our tradeable players (from cache)
        our_players = self._get_team_players(self._team_id)
        player_lookup = {p["player_id"]: p for p in our_players}

        # Get our picks for package construction (from cache)
        our_picks = self._get_team_picks(self._team_id)

        for player_id in self._directives.expendable_player_ids:
            player = player_lookup.get(player_id)
            if not player:
                self._logger.debug(
                    f"Expendable player {player_id} not found on roster"
                )
                continue

            # Try to find interested team
            best_offer = self._find_best_trade_partner_for_player(
                player, our_picks
            )

            if best_offer:
                proposal = self._create_trade_proposal(
                    trade_partner_id=best_offer["partner_id"],
                    trade_partner_name=best_offer["partner_name"],
                    sending_players=[player],
                    sending_picks=best_offer.get("our_picks", []),
                    receiving_players=best_offer.get("their_players", []),
                    receiving_picks=best_offer.get("their_picks", []),
                    tier=self.TIER_EXPENDABLE_SHOPPING,
                    confidence=best_offer["confidence"],
                    reasoning=self._generate_expendable_reasoning(
                        player, best_offer
                    ),
                )
                proposals.append(proposal)

        return proposals

    def _find_best_trade_partner_for_player(
        self,
        player: Dict[str, Any],
        our_picks: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """
        Find the best trade partner for a player we're shopping.

        Args:
            player: Player dict we're trying to trade
            our_picks: Our available draft picks

        Returns:
            Dict with partner info and trade details, or None if no takers
        """
        trade_service = self._get_trade_service()
        best_offer: Optional[Dict[str, Any]] = None
        best_confidence = 0.0

        # Try all other teams
        for other_team_id in self.ALL_TEAM_IDS:
            if other_team_id == self._team_id:
                continue

            try:
                # Create simple 1-for-pick proposal (use cache)
                their_picks = self._get_team_picks(other_team_id)
                if not their_picks:
                    continue

                # Find a reasonable pick to request
                target_pick = self._find_fair_pick_for_player(
                    player, their_picks
                )
                if not target_pick:
                    continue

                # Create and evaluate proposal
                proposal = trade_service.propose_trade(
                    team1_id=self._team_id,
                    team1_player_ids=[player["player_id"]],
                    team2_id=other_team_id,
                    team2_player_ids=[],
                    team1_pick_ids=[],
                    team2_pick_ids=[target_pick["id"]],
                )

                # Have AI team evaluate
                decision = trade_service.evaluate_ai_trade(
                    proposal=proposal,
                    ai_team_id=other_team_id,
                    is_offseason=True,
                )

                if decision.decision == TradeDecisionType.ACCEPT:
                    if decision.confidence > best_confidence:
                        team_name = self._get_team_name(other_team_id)
                        best_offer = {
                            "partner_id": other_team_id,
                            "partner_name": team_name,
                            "their_picks": [target_pick],
                            "their_players": [],
                            "our_picks": [],
                            "confidence": decision.confidence,
                            "value_ratio": proposal.value_ratio,
                        }
                        best_confidence = decision.confidence

            except Exception as e:
                self._logger.debug(
                    f"Error evaluating trade with team {other_team_id}: {e}"
                )
                continue

        return best_offer

    def _find_fair_pick_for_player(
        self,
        player: Dict[str, Any],
        available_picks: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """
        Find a pick that roughly matches the player's age-depreciated value.

        v1.3: Applies age depreciation - older players command lower picks.

        Effective OVR = OVR × age_factor:
        - 90+ effective: Round 1
        - 82-89 effective: Round 2
        - 75-81 effective: Round 3-4
        - 68-74 effective: Round 5-6
        - Below 68: Round 7

        Args:
            player: Player being traded
            available_picks: List of available picks

        Returns:
            Best matching pick or None
        """
        ovr = extract_overall_rating(player, default=70)
        age = player.get("age", 27)

        # Apply age depreciation for pick targeting
        # More gradual than value depreciation to keep trades viable
        def age_factor(age: int) -> float:
            if age <= 27:
                return 1.0
            elif age == 28:
                return 0.95
            elif age == 29:
                return 0.90
            elif age == 30:
                return 0.85
            elif age == 31:
                return 0.75  # Still productive, ~3rd round value
            elif age == 32:
                return 0.65
            elif age == 33:
                return 0.55
            elif age == 34:
                return 0.45
            else:  # 35+
                return 0.35  # Minimal trade value but still tradeable

        # Calculate effective OVR (depreciated)
        effective_ovr = ovr * age_factor(age)

        # Determine target round based on effective OVR
        # Examples:
        # - 88 OVR × 0.35 (age 35) = 31 → 5th-6th round (not 1st!)
        # - 88 OVR × 0.75 (age 31) = 66 → 4th round
        # - 88 OVR × 1.0 (age 25) = 88 → 2nd round
        # - 92 OVR × 1.0 (age 26) = 92 → 1st round
        if effective_ovr >= 90:
            target_rounds = [1]
        elif effective_ovr >= 82:
            target_rounds = [2]
        elif effective_ovr >= 75:
            target_rounds = [3]
        elif effective_ovr >= 68:
            target_rounds = [4]
        elif effective_ovr >= 55:
            target_rounds = [5, 6]
        else:
            target_rounds = [7]

        # Find best matching pick
        for round_num in target_rounds:
            for pick in available_picks:
                if pick.get("round") == round_num:
                    return pick

        # Fallback to any pick in nearby rounds
        for round_num in target_rounds:
            # Try one round higher if not found
            for pick in available_picks:
                if pick.get("round") == round_num + 1:
                    return pick

        return available_picks[0] if available_picks else None

    # =========================================================================
    # WIN_NOW: Acquisition Targets (TIER 2)
    # =========================================================================

    def _find_acquisition_targets(self) -> List[PersistentGMProposal]:
        """
        Find players at priority positions to acquire (WIN_NOW mode).

        v1.3: Uses roster-based needs analysis to ensure each team targets
        different players based on their specific roster gaps, not just
        the league's "best available" player.

        Flow:
        1. Analyze our roster to find weak positions
        2. For each need, find multiple candidate upgrades
        3. Try to construct packages for candidates until successful

        Returns:
            List of acquisition proposals
        """
        proposals: List[PersistentGMProposal] = []

        # Get our assets for package construction (from cache)
        our_players = self._get_team_players(self._team_id)
        our_picks = self._get_team_picks(self._team_id)

        # Filter out protected players from our tradeable assets
        our_tradeable = [
            p for p in our_players
            if p["player_id"] not in self._protected_set
        ]

        # v1.3 Roster-based needs: Analyze our roster gaps
        roster_needs = self._analyze_roster_needs()

        if not roster_needs:
            self._logger.debug(f"Team {self._team_id} has no roster needs")
            return proposals

        # For each need, find candidates that improve our weakness
        for need in roster_needs[:3]:  # Top 3 needs
            candidates = self._find_targets_for_need(need, min_improvement=3)

            if not candidates:
                self._logger.debug(
                    f"No candidates found for {need['position']} need"
                )
                continue

            # Try each candidate until we find one we can trade for
            for target in candidates:
                package = self._construct_acquisition_package(
                    target=target,
                    our_players=our_tradeable,
                    our_picks=our_picks,
                )

                if package:
                    proposal = self._create_trade_proposal(
                        trade_partner_id=target["team_id"],
                        trade_partner_name=target["team_name"],
                        sending_players=package["players"],
                        sending_picks=package["picks"],
                        receiving_players=[target],
                        receiving_picks=[],
                        tier=self.TIER_PRIORITY_POSITION,
                        confidence=package["confidence"],
                        reasoning=self._generate_acquisition_reasoning(
                            target, need["position"]
                        ),
                    )
                    proposals.append(proposal)
                    break  # Found trade for this need, move to next

        return proposals

    def _find_best_target_at_position(
        self,
        position: str,
        min_overall: int,
        max_age: int,
    ) -> Optional[Dict[str, Any]]:
        """
        Find the best available player at a position across the league.

        Args:
            position: Position to target
            min_overall: Minimum overall rating
            max_age: Maximum age

        Returns:
            Best target dict with team info, or None
        """
        best_target: Optional[Dict[str, Any]] = None
        best_ovr = min_overall - 1

        for team_id in self.ALL_TEAM_IDS:
            if team_id == self._team_id:
                continue

            # Use cache for team players
            players = self._get_team_players(team_id)
            for player in players:
                # Skip untouchable players (v1.2 - trade realism)
                if self._is_untouchable(player):
                    continue

                # Normalize position for comparison (handles JSON array format)
                player_pos = self._normalize_position(player.get("position"))
                target_pos = position.upper()

                if (
                    player_pos == target_pos
                    and extract_overall_rating(player, default=0) >= min_overall
                    and player.get("age", 99) <= max_age
                    and extract_overall_rating(player, default=0) > best_ovr
                ):
                    best_target = player.copy()
                    best_target["team_id"] = team_id
                    best_target["team_name"] = self._get_team_name(team_id)
                    best_ovr = extract_overall_rating(player, default=0)

        return best_target

    def _construct_acquisition_package(
        self,
        target: Dict[str, Any],
        our_players: List[Dict[str, Any]],
        our_picks: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """
        Construct a trade package to acquire a target player.

        Tries to match target value with combination of players and picks.

        Args:
            target: Player we want to acquire
            our_players: Our available players
            our_picks: Our available picks

        Returns:
            Package dict with players, picks, and confidence, or None
        """
        trade_service = self._get_trade_service()
        target_team_id = target["team_id"]

        # Simple approach: try pick + depth player
        for pick in our_picks:
            for player in our_players:
                if player["player_id"] in self._protected_set:
                    continue

                # Skip high-value players (we want to keep them)
                if extract_overall_rating(player, default=0) >= self.HIGH_VALUE_PLAYER_OVR:
                    continue

                try:
                    proposal = trade_service.propose_trade(
                        team1_id=self._team_id,
                        team1_player_ids=[player["player_id"]],
                        team2_id=target_team_id,
                        team2_player_ids=[target["player_id"]],
                        team1_pick_ids=[pick["id"]],
                        team2_pick_ids=[],
                    )

                    decision = trade_service.evaluate_ai_trade(
                        proposal=proposal,
                        ai_team_id=target_team_id,
                        is_offseason=True,
                    )

                    if decision.decision == TradeDecisionType.ACCEPT:
                        # v1.2 Trade Realism: Validate cap space before accepting
                        cap_impact = (
                            target.get("cap_hit", 0) - player.get("cap_hit", 0)
                        )
                        if cap_impact > 0 and not self._validate_cap_space(cap_impact):
                            self._logger.debug(
                                f"Skipping trade: can't afford cap impact ${cap_impact:,}"
                            )
                            continue

                        return {
                            "players": [player],
                            "picks": [pick],
                            "confidence": decision.confidence,
                        }

                except Exception as e:
                    self._logger.debug(f"Package construction failed: {e}")
                    continue

        return None

    # =========================================================================
    # REBUILD: Trade Veterans for Picks (TIER 4)
    # =========================================================================

    def _generate_rebuild_trades(self) -> List[PersistentGMProposal]:
        """
        Generate trades to acquire draft picks (REBUILD mode).

        Identifies expensive veterans (not protected) and shops them
        to contending teams for draft capital.

        Returns:
            List of rebuild trade proposals
        """
        proposals: List[PersistentGMProposal] = []
        expendable_set = set(self._directives.expendable_player_ids)

        # Use cache for our players
        our_players = self._get_team_players(self._team_id)

        # Find veterans to shop (not protected, not already expendable)
        veterans = [
            p for p in our_players
            if (
                p.get("age", 0) >= self.MIN_AGE_VETERAN
                and p["player_id"] not in self._protected_set
                and p["player_id"] not in expendable_set
                and extract_overall_rating(p, default=0) >= 75  # Still valuable
            )
        ]

        # Sort by cap hit (trade most expensive first)
        veterans.sort(key=lambda p: p.get("cap_hit", 0), reverse=True)

        for veteran in veterans[:3]:  # Limit to top 3 cap hits
            best_offer = self._find_best_trade_partner_for_player(
                veteran, []  # No picks to add, we want picks back
            )

            if best_offer:
                proposal = self._create_trade_proposal(
                    trade_partner_id=best_offer["partner_id"],
                    trade_partner_name=best_offer["partner_name"],
                    sending_players=[veteran],
                    sending_picks=[],
                    receiving_players=[],
                    receiving_picks=best_offer.get("their_picks", []),
                    tier=self.TIER_PICK_ACQUISITION,
                    confidence=best_offer["confidence"],
                    reasoning=self._generate_rebuild_reasoning(
                        veteran, best_offer
                    ),
                )
                proposals.append(proposal)

        return proposals

    # =========================================================================
    # MAINTAIN: Value Upgrades (TIER 3)
    # =========================================================================

    def _find_value_upgrades(self) -> List[PersistentGMProposal]:
        """
        Find value upgrade trades (MAINTAIN mode).

        Look for slightly better players at positions where we have depth.

        Returns:
            List of value upgrade proposals
        """
        proposals: List[PersistentGMProposal] = []

        # Use cache for our players and picks
        our_players = self._get_team_players(self._team_id)
        our_picks = self._get_team_picks(self._team_id)

        # Find positions where we have multiple players
        position_players: Dict[str, List[Dict]] = {}
        for player in our_players:
            pos = player.get("position", "Unknown")
            if pos not in position_players:
                position_players[pos] = []
            position_players[pos].append(player)

        # For positions with depth, try to upgrade
        for position, players in position_players.items():
            if len(players) < 2:
                continue

            # Sort by overall, trade away lower-rated player
            players.sort(
                key=lambda p: extract_overall_rating(p, default=0), reverse=True
            )
            trade_candidate = players[-1]  # Lowest rated

            if trade_candidate["player_id"] in self._protected_set:
                continue

            # Find upgrade target
            target = self._find_best_target_at_position(
                position=position,
                min_overall=extract_overall_rating(trade_candidate, default=0) + 3,
                max_age=30,
            )

            if target:
                package = self._construct_acquisition_package(
                    target=target,
                    our_players=[trade_candidate],
                    our_picks=our_picks,
                )

                if package:
                    proposal = self._create_trade_proposal(
                        trade_partner_id=target["team_id"],
                        trade_partner_name=target["team_name"],
                        sending_players=package["players"],
                        sending_picks=package["picks"],
                        receiving_players=[target],
                        receiving_picks=[],
                        tier=self.TIER_VALUE_UPGRADE,
                        confidence=package["confidence"],
                        reasoning=self._generate_upgrade_reasoning(
                            trade_candidate, target
                        ),
                    )
                    proposals.append(proposal)
                    break  # One upgrade per run

        return proposals

    # =========================================================================
    # Proposal Creation
    # =========================================================================

    def _create_trade_proposal(
        self,
        trade_partner_id: int,
        trade_partner_name: str,
        sending_players: List[Dict[str, Any]],
        sending_picks: List[Dict[str, Any]],
        receiving_players: List[Dict[str, Any]],
        receiving_picks: List[Dict[str, Any]],
        tier: int,
        confidence: float,
        reasoning: str,
    ) -> PersistentGMProposal:
        """
        Create a PersistentGMProposal for a trade.

        Args:
            trade_partner_id: Trading partner team ID
            trade_partner_name: Trading partner team name
            sending_players: Players we're sending
            sending_picks: Picks we're sending
            receiving_players: Players we're receiving
            receiving_picks: Picks we're receiving
            tier: Priority tier
            confidence: GM confidence (0.5-0.95)
            reasoning: GM explanation

        Returns:
            PersistentGMProposal ready for database storage
        """
        # Build asset lists for UI display using helper methods
        sending = [self._build_player_asset(p) for p in sending_players]
        sending.extend([self._build_pick_asset(p) for p in sending_picks])
        sending_player_ids = [p["player_id"] for p in sending_players]
        sending_pick_ids = [p["id"] for p in sending_picks]

        receiving = [self._build_player_asset(p) for p in receiving_players]
        receiving.extend([self._build_pick_asset(p) for p in receiving_picks])
        receiving_player_ids = [p["player_id"] for p in receiving_players]
        receiving_pick_ids = [p["id"] for p in receiving_picks]

        # Calculate value differential and cap impact
        value_differential = self._calculate_value_differential(
            sending_players, sending_picks,
            receiving_players, receiving_picks
        )
        cap_impact = self._calculate_cap_impact(
            sending_players, receiving_players
        )

        # Create details with execution fields
        details = create_trade_details(
            trade_partner=trade_partner_name,
            sending=sending,
            receiving=receiving,
            value_differential=value_differential,
            cap_impact=cap_impact,
        )

        # Add execution fields for later trade execution
        details["trade_partner_id"] = trade_partner_id
        details["sending_player_ids"] = sending_player_ids
        details["sending_pick_ids"] = sending_pick_ids
        details["receiving_player_ids"] = receiving_player_ids
        details["receiving_pick_ids"] = receiving_pick_ids

        # Constrain confidence
        confidence = min(0.95, max(0.5, confidence))

        return PersistentGMProposal(
            dynasty_id=self._dynasty_id,
            team_id=self._team_id,
            season=self._season,
            stage="OFFSEASON_TRADING",
            proposal_type=ProposalType.TRADE,
            subject_player_id=None,  # Trades don't have single subject
            details=details,
            gm_reasoning=reasoning,
            confidence=confidence,
            priority=tier,
            status=ProposalStatus.APPROVED,  # Default to approved - owner can reject
            created_at=datetime.now(),
        )

    # =========================================================================
    # Reasoning Generation
    # =========================================================================

    def _generate_expendable_reasoning(
        self,
        player: Dict[str, Any],
        offer: Dict[str, Any],
    ) -> str:
        """Generate reasoning for expendable player trade."""
        name = player.get("name", "Unknown")
        partner = offer.get("partner_name", "Unknown")
        pick_info = ""
        if offer.get("their_picks"):
            pick = offer["their_picks"][0]
            pick_info = f"a Round {pick.get('round', '?')} pick"

        return (
            f"Per owner directive, {name} has been made available for trade. "
            f"The {partner} have expressed interest and would offer {pick_info}. "
            f"This move clears roster space and adds future draft capital."
        )

    def _generate_acquisition_reasoning(
        self,
        target: Dict[str, Any],
        position: str,
    ) -> str:
        """Generate reasoning for WIN_NOW acquisition."""
        name = target.get("name", "Unknown")
        ovr = extract_overall_rating(target, default=0)
        team = target.get("team_name", "Unknown")

        return (
            f"Championship-caliber addition at priority position {position}. "
            f"{name} ({ovr} OVR) from the {team} fits our win-now window. "
            f"This addresses a key need identified in owner directives."
        )

    def _generate_rebuild_reasoning(
        self,
        veteran: Dict[str, Any],
        offer: Dict[str, Any],
    ) -> str:
        """Generate reasoning for REBUILD veteran trade."""
        name = veteran.get("name", "Unknown")
        age = veteran.get("age", 0)
        cap_hit = veteran.get("cap_hit", 0)
        partner = offer.get("partner_name", "Unknown")

        return (
            f"Trading {name} (age {age}, ${cap_hit:,} cap hit) to the {partner} "
            f"for draft capital. This accelerates our rebuild by clearing "
            f"cap space and adding picks for future development."
        )

    def _generate_upgrade_reasoning(
        self,
        current: Dict[str, Any],
        target: Dict[str, Any],
    ) -> str:
        """Generate reasoning for MAINTAIN value upgrade."""
        current_name = current.get("name", "Unknown")
        current_ovr = extract_overall_rating(current, default=0)
        target_name = target.get("name", "Unknown")
        target_ovr = extract_overall_rating(target, default=0)
        position = self._parse_position(target.get("position", ""))

        return (
            f"Value upgrade at {position}: acquiring {target_name} ({target_ovr} OVR) "
            f"while trading {current_name} ({current_ovr} OVR). "
            f"Maintains roster balance while improving at a position of depth."
        )

    # =========================================================================
    # Cap-Clearing Trades (for Free Agency Cap Space)
    # =========================================================================

    def generate_cap_clearing_trades(
        self,
        min_cap_to_clear: Optional[int] = None,
        max_proposals: int = 5
    ) -> List[PersistentGMProposal]:
        """
        Generate trade proposals aimed at clearing cap space.

        Strategy:
        1. Identify high-cap-hit players (not protected)
        2. Find trade partners willing to accept them
        3. Optimize for positive cap savings (outgoing_cap > incoming_cap)
        4. Return sorted by cap savings (highest first)

        Returns ANY cap-clearing trade, even if partial.

        Args:
            min_cap_to_clear: Minimum cap savings target (optional, for logging)
            max_proposals: Maximum trades to return (default 5)

        Returns:
            List of trade proposals sorted by cap savings (highest first)
        """
        proposals: List[PersistentGMProposal] = []
        trade_service = self._get_trade_service()

        self._logger.info(
            f"Generating cap-clearing trades for team {self._team_id} "
            f"(target: ${min_cap_to_clear:,})" if min_cap_to_clear else
            f"Generating cap-clearing trades for team {self._team_id}"
        )

        # Get our tradeable players
        our_players = trade_service.get_tradeable_players(self._team_id)

        # Filter for players with meaningful cap hits
        # and exclude protected players
        cap_candidates = [
            p for p in our_players
            if p.get("cap_hit", 0) >= self.MIN_CAP_HIT_FOR_TRADE
            and p["player_id"] not in self._directives.protected_player_ids
        ]

        # Sort by cap hit (highest first)
        cap_candidates.sort(key=lambda p: p.get("cap_hit", 0), reverse=True)

        self._logger.debug(
            f"Found {len(cap_candidates)} cap-clearing candidates "
            f"(top cap hit: ${cap_candidates[0].get('cap_hit', 0):,})" if cap_candidates
            else "No cap-clearing candidates found"
        )

        # Try to find cap-clearing trade for each candidate
        for player in cap_candidates[:10]:  # Check top 10 cap hits
            best_trade = self._find_cap_clearing_trade_for_player(player)
            if best_trade:
                proposals.append(best_trade)
                self._logger.debug(
                    f"Found cap-clearing trade for {player.get('name', 'Unknown')}: "
                    f"${best_trade.details.get('cap_impact', 0):,} savings"
                )

        # Sort by cap savings (highest first)
        proposals.sort(
            key=lambda p: p.details.get("cap_impact", 0),
            reverse=True
        )

        # Limit results
        limited = proposals[:max_proposals]

        self._logger.info(
            f"Returning {len(limited)} cap-clearing trade proposals "
            f"(from {len(proposals)} found)"
        )

        return limited

    def _find_cap_clearing_trade_for_player(
        self,
        player: Dict[str, Any]
    ) -> Optional[PersistentGMProposal]:
        """
        Find best cap-clearing trade for a specific player.

        Tries multiple package types:
        1. Player-for-pick (clears full cap hit)
        2. Player-for-cheaper-player (partial cap clearing)
        3. Player + pick for cheaper player (incentivize trade partner)

        Args:
            player: Player dict we're trying to trade away

        Returns:
            Best cap-clearing proposal, or None if no trades accepted
        """
        trade_service = self._get_trade_service()
        our_picks = trade_service.get_tradeable_picks(self._team_id)

        best_proposal = None
        best_cap_savings = 0

        player_cap = player.get("cap_hit", 0)
        player_name = player.get("name", "Unknown")

        # Try all other teams as partners
        for partner_team_id in self.ALL_TEAM_IDS:
            if partner_team_id == self._team_id:
                continue

            # Strategy 1: Player for pick (max cap savings)
            if our_picks:
                their_picks = trade_service.get_tradeable_picks(partner_team_id)
                if their_picks:
                    # Try for a fair pick trade
                    target_pick = self._find_fair_pick_for_player(player, their_picks)
                    if target_pick:
                        proposal = self._evaluate_cap_clearing_proposal(
                            our_players=[player],
                            our_picks=[],
                            their_players=[],
                            their_picks=[target_pick],
                            partner_team_id=partner_team_id
                        )

                        if proposal:
                            cap_impact = proposal.details.get("cap_impact", 0)
                            if cap_impact > best_cap_savings:
                                best_proposal = proposal
                                best_cap_savings = cap_impact

            # Strategy 2: Player for cheaper player (partial cap savings)
            their_players = trade_service.get_tradeable_players(partner_team_id)
            for their_player in their_players:
                their_cap = their_player.get("cap_hit", 0)

                # Only consider if cap savings
                if their_cap >= player_cap:
                    continue

                cap_savings = player_cap - their_cap

                # Only worth it if meaningful savings
                if cap_savings < self.MIN_MEANINGFUL_CAP_SAVINGS:
                    continue

                proposal = self._evaluate_cap_clearing_proposal(
                    our_players=[player],
                    our_picks=[],
                    their_players=[their_player],
                    their_picks=[],
                    partner_team_id=partner_team_id
                )

                if proposal:
                    cap_impact = proposal.details.get("cap_impact", 0)
                    if cap_impact > best_cap_savings:
                        best_proposal = proposal
                        best_cap_savings = cap_impact

        if best_proposal:
            self._logger.debug(
                f"Best cap-clearing trade for {player_name}: "
                f"${best_cap_savings:,} savings with team {best_proposal.details.get('trade_partner', 'Unknown')}"
            )

        return best_proposal

    def _evaluate_cap_clearing_proposal(
        self,
        our_players: List[Dict],
        our_picks: List[Dict],
        their_players: List[Dict],
        their_picks: List[Dict],
        partner_team_id: int
    ) -> Optional[PersistentGMProposal]:
        """
        Evaluate if trade partner would accept, and create proposal if so.

        Args:
            our_players: Players we're sending
            our_picks: Picks we're sending
            their_players: Players we're receiving
            their_picks: Picks we're receiving
            partner_team_id: Trade partner team ID

        Returns:
            PersistentGMProposal if accepted, None if rejected
        """
        trade_service = self._get_trade_service()

        # Build player IDs
        our_player_ids = [p["player_id"] for p in our_players]
        their_player_ids = [p["player_id"] for p in their_players]
        our_pick_ids = [p.get("id") for p in our_picks]
        their_pick_ids = [p.get("id") for p in their_picks]

        try:
            # Create proposal
            proposal = trade_service.propose_trade(
                team1_id=self._team_id,
                team1_player_ids=our_player_ids,
                team2_id=partner_team_id,
                team2_player_ids=their_player_ids,
                team1_pick_ids=our_pick_ids,
                team2_pick_ids=their_pick_ids
            )

            # Evaluate with AI
            decision = trade_service.evaluate_ai_trade(
                proposal=proposal,
                ai_team_id=partner_team_id,
                is_offseason=True
            )

            # Only return if accepted
            if decision.decision != TradeDecisionType.ACCEPT:
                return None

            # Calculate cap impact
            cap_impact = self._calculate_cap_impact(our_players, their_players)

            # Only accept if positive cap savings
            if cap_impact <= 0:
                return None

            # Get partner name
            partner_name = self._get_team_name(partner_team_id)

            # Create PersistentGMProposal
            return self._create_trade_proposal(
                trade_partner_id=partner_team_id,
                trade_partner_name=partner_name,
                sending_players=our_players,
                sending_picks=our_picks,
                receiving_players=their_players,
                receiving_picks=their_picks,
                tier=self.TIER_EXPENDABLE_SHOPPING,  # High priority
                confidence=decision.confidence,
                reasoning=self._generate_cap_clearing_reasoning(
                    our_players, their_players, cap_impact
                )
            )

        except Exception as e:
            self._logger.warning(
                f"Error evaluating cap-clearing proposal: {e}"
            )
            return None

    def _generate_cap_clearing_reasoning(
        self,
        our_players: List[Dict],
        their_players: List[Dict],
        cap_savings: int
    ) -> str:
        """Generate GM reasoning for cap-clearing trade."""
        if len(our_players) == 1 and len(their_players) == 0:
            # Player-for-pick
            player_name = our_players[0].get("name", "Unknown")
            return (
                f"Trading {player_name} clears ${cap_savings:,} in cap space. "
                f"This gives us the flexibility needed to pursue free agent targets."
            )
        elif len(our_players) == 1 and len(their_players) == 1:
            # Player swap
            our_name = our_players[0].get("name", "Unknown")
            their_name = their_players[0].get("name", "Unknown")
            return (
                f"Swapping {our_name} for {their_name} saves ${cap_savings:,} while "
                f"maintaining roster depth. This creates the cap room we need for key signings."
            )
        else:
            # Complex trade
            return (
                f"This trade clears ${cap_savings:,} in cap space through strategic "
                f"asset management, allowing us to pursue key free agent signings."
            )

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _build_player_asset(self, player: Dict[str, Any]) -> Dict[str, Any]:
        """Build a player asset dict for proposal display."""
        return {
            "type": "player",
            "name": player.get("name", "Unknown"),
            "position": self._parse_position(player.get("position", "")),
            "overall": extract_overall_rating(player, default=0),
            "age": player.get("age", 0),
            "cap_hit": player.get("cap_hit", 0),
        }

    def _build_pick_asset(self, pick: Dict[str, Any]) -> Dict[str, Any]:
        """Build a pick asset dict for proposal display."""
        round_num = pick.get("round", 0)
        season = pick.get("season", self._season)
        return {
            "type": "pick",
            "name": f"{season} Round {round_num}",
            "round": round_num,
            "season": season,
        }

    def _validate_cap_space(self, cap_impact: int) -> bool:
        """
        Check if team can afford the cap impact of a trade (v1.2 - trade realism).

        Validates that acquiring players won't put the team over the cap.
        Uses a $5M buffer to ensure we don't cut it too close.

        Args:
            cap_impact: Net cap change (positive = cap increase, negative = savings)

        Returns:
            True if team can afford the trade, False otherwise
        """
        # If we're saving cap space (negative impact), always valid
        if cap_impact <= 0:
            return True

        try:
            from game_cycle.services.cap_helper import CapHelper
            cap_helper = CapHelper(self._db_path, self._dynasty_id, self._season)
            cap_data = cap_helper.get_cap_summary(self._team_id)
            available_space = cap_data.get("cap_space", 0)

            # Need at least the cap impact + safety buffer
            can_afford = available_space >= (cap_impact + self.CAP_SAFETY_BUFFER)

            if not can_afford:
                self._logger.debug(
                    f"Cap validation failed: need ${(cap_impact + self.CAP_SAFETY_BUFFER):,}, "
                    f"have ${available_space:,}"
                )

            return can_afford

        except Exception as e:
            self._logger.warning(f"Cap validation error: {e}")
            # If we can't validate cap, be conservative and allow trade
            # (better to let it through than block valid trades)
            return True

    def _is_untouchable(self, player: Dict[str, Any]) -> bool:
        """
        Check if a player should be considered untouchable in trades.

        Untouchable criteria (v1.2 - trade realism):
        1. Franchise QB: 85+ OVR and under 32 years old
        2. Elite player: 90+ OVR and under 30 years old
        3. Protected by owner directive

        This prevents unrealistic trades like "Lamar Jackson for a 1st round pick"
        or "Myles Garrett for a mid-round pick + depth player".

        Args:
            player: Player dict with overall_rating, age, position

        Returns:
            True if player should never be trade target
        """
        overall = extract_overall_rating(player, default=0)
        age = player.get("age", 99)
        position = player.get("position", "").upper()

        # Normalize position (handle JSON array format)
        if position.startswith("["):
            try:
                positions = json.loads(position)
                position = positions[0].upper() if positions else ""
            except (json.JSONDecodeError, IndexError):
                pass

        # 1. Franchise QB under 32 is untouchable
        if position == "QB":
            if overall >= self.UNTOUCHABLE_QB_MIN_OVR and age <= self.UNTOUCHABLE_QB_MAX_AGE:
                self._logger.debug(
                    f"Player {player.get('name', 'Unknown')} is untouchable "
                    f"(franchise QB: {overall} OVR, age {age})"
                )
                return True

        # 2. Elite players (90+) under 30 are untouchable
        if overall >= self.UNTOUCHABLE_ELITE_MIN_OVR and age <= self.UNTOUCHABLE_ELITE_MAX_AGE:
            self._logger.debug(
                f"Player {player.get('name', 'Unknown')} is untouchable "
                f"(elite player: {overall} OVR, age {age})"
            )
            return True

        # 3. Protected by owner directive (check player_id)
        player_id = player.get("player_id")
        if player_id and player_id in self._directives.protected_player_ids:
            self._logger.debug(
                f"Player {player.get('name', 'Unknown')} is untouchable "
                f"(owner protected)"
            )
            return True

        return False

    def _calculate_value_differential(
        self,
        sending_players: List[Dict],
        sending_picks: List[Dict],
        receiving_players: List[Dict],
        receiving_picks: List[Dict],
    ) -> int:
        """
        Calculate rough value differential (positive = good for us).

        v1.3: Includes age depreciation - older players are worth less
        because they have fewer remaining productive years.

        NFL Reality Check:
        - 1st round pick = young player with franchise potential
        - 35-year-old 88 OVR = declining veteran, worth 4th-5th round
        - 25-year-old 88 OVR = prime player, worth 1st-2nd round
        """
        def age_factor(age: int) -> float:
            """
            Age depreciation factor (1.0 = prime, 0.0 = worthless).

            Peak value at 25-27, declining after 28.
            - Age 25-27: 1.0 (prime)
            - Age 28: 0.9
            - Age 29: 0.8
            - Age 30: 0.65
            - Age 31: 0.5
            - Age 32: 0.4
            - Age 33: 0.3
            - Age 34+: 0.2 (minimal trade value)
            """
            if age <= 27:
                return 1.0
            elif age == 28:
                return 0.9
            elif age == 29:
                return 0.8
            elif age == 30:
                return 0.65
            elif age == 31:
                return 0.5
            elif age == 32:
                return 0.4
            elif age == 33:
                return 0.3
            else:  # 34+
                return 0.2

        def player_value(p: Dict) -> int:
            # Base value scales with OVR: (OVR - 70) * $100K
            # 80 OVR = $1M, 85 OVR = $1.5M, 90 OVR = $2M
            base_value = (extract_overall_rating(p, default=70) - 70) * 100_000

            # Apply age depreciation
            age = p.get("age", 27)  # Default to prime age if unknown
            depreciation = age_factor(age)

            # v1.3: Apply stats modifier (0.8 to 1.2 based on performance)
            stats_mod = self._get_stats_modifier(p)

            return int(base_value * depreciation * stats_mod)

        def pick_value(p: Dict) -> int:
            # Pick values calibrated to match player values more realistically
            # 1st round pick = ~85 OVR young player ($1.5M value)
            # This makes sense: 85 OVR × age_factor(22) = $1.5M
            round_values = {
                1: 1_500_000,  # Top picks worth as much as solid starters
                2: 800_000,    # 2nd rounders still valuable
                3: 400_000,
                4: 200_000,
                5: 100_000,
                6: 50_000,
                7: 25_000,
            }
            return round_values.get(p.get("round", 7), 25_000)

        sending_value = sum(player_value(p) for p in sending_players)
        sending_value += sum(pick_value(p) for p in sending_picks)

        receiving_value = sum(player_value(p) for p in receiving_players)
        receiving_value += sum(pick_value(p) for p in receiving_picks)

        return receiving_value - sending_value

    def _calculate_cap_impact(
        self,
        sending_players: List[Dict],
        receiving_players: List[Dict],
    ) -> int:
        """Calculate cap impact (positive = cap savings)."""
        outgoing_cap = sum(p.get("cap_hit", 0) for p in sending_players)
        incoming_cap = sum(p.get("cap_hit", 0) for p in receiving_players)
        return outgoing_cap - incoming_cap

    def _get_team_name(self, team_id: int) -> str:
        """Get team name using cached team utility."""
        return get_team_name_util(team_id, self._dynasty_id, self._db_path)

    def _parse_position(self, position_data: Any) -> str:
        """
        Parse position data which may be stored in various formats.

        Args:
            position_data: Position as string, JSON string, or list

        Returns:
            Clean position string (e.g., "CB" instead of '["cornerback"]')
        """
        if isinstance(position_data, list):
            # Already a list, return first element
            position = position_data[0] if position_data else ""
        elif isinstance(position_data, str):
            if position_data.startswith("["):
                # JSON array string like '["cornerback"]'
                try:
                    positions = json.loads(position_data)
                    position = positions[0] if positions else ""
                except (json.JSONDecodeError, IndexError):
                    position = position_data
            else:
                position = position_data
        else:
            position = str(position_data) if position_data else ""

        # Convert to abbreviation for consistent display
        return get_position_abbreviation(position)
