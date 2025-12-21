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

from utils.player_field_extractors import extract_overall_rating
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

    def _get_trade_service(self) -> TradeService:
        """Get or create TradeService instance."""
        if self._trade_service is None:
            self._trade_service = TradeService(
                db_path=self._db_path,
                dynasty_id=self._dynasty_id,
                season=self._season
            )
        return self._trade_service

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
            if self._directives.priority_positions:
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
        trade_service = self._get_trade_service()

        # Get our tradeable players
        our_players = trade_service.get_tradeable_players(self._team_id)
        player_lookup = {p["player_id"]: p for p in our_players}

        # Get our picks for package construction
        our_picks = trade_service.get_tradeable_picks(self._team_id)

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
        for other_team_id in range(1, 33):
            if other_team_id == self._team_id:
                continue

            try:
                # Create simple 1-for-pick proposal
                their_picks = trade_service.get_tradeable_picks(other_team_id)
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
        Find a pick that roughly matches the player's value.

        Simple heuristic based on overall rating:
        - 85+ OVR: Round 1-2
        - 80-84 OVR: Round 2-3
        - 75-79 OVR: Round 3-4
        - Below 75: Round 5-7

        Args:
            player: Player being traded
            available_picks: List of available picks

        Returns:
            Best matching pick or None
        """
        ovr = extract_overall_rating(player, default=70)

        # Determine target round based on overall
        if ovr >= 85:
            target_rounds = [1, 2]
        elif ovr >= 80:
            target_rounds = [2, 3]
        elif ovr >= 75:
            target_rounds = [3, 4]
        else:
            target_rounds = [5, 6, 7]

        # Find best matching pick
        for round_num in target_rounds:
            for pick in available_picks:
                if pick.get("round") == round_num:
                    return pick

        # Fallback to any pick
        return available_picks[0] if available_picks else None

    # =========================================================================
    # WIN_NOW: Acquisition Targets (TIER 2)
    # =========================================================================

    def _find_acquisition_targets(self) -> List[PersistentGMProposal]:
        """
        Find players at priority positions to acquire (WIN_NOW mode).

        Targets high-OVR players at positions the owner wants to improve.

        Returns:
            List of acquisition proposals
        """
        proposals: List[PersistentGMProposal] = []
        trade_service = self._get_trade_service()
        protected_set = set(self._directives.protected_player_ids)

        # Get our assets for package construction
        our_players = trade_service.get_tradeable_players(self._team_id)
        our_picks = trade_service.get_tradeable_picks(self._team_id)

        # Filter out protected players from our tradeable assets
        our_tradeable = [
            p for p in our_players
            if p["player_id"] not in protected_set
        ]

        for position in self._directives.priority_positions[:3]:  # Top 3
            target = self._find_best_target_at_position(
                position=position,
                min_overall=self.MIN_OVERALL_WIN_NOW,
                max_age=self.MAX_AGE_WIN_NOW,
            )

            if not target:
                continue

            # Try to construct a fair package
            package = self._construct_acquisition_package(
                target=target,
                our_players=our_tradeable,
                our_picks=our_picks,
                protected_set=protected_set,
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
                        target, position
                    ),
                )
                proposals.append(proposal)

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
        trade_service = self._get_trade_service()
        best_target: Optional[Dict[str, Any]] = None
        best_ovr = min_overall - 1

        for team_id in range(1, 33):
            if team_id == self._team_id:
                continue

            players = trade_service.get_tradeable_players(team_id)
            for player in players:
                if (
                    player.get("position") == position
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
        protected_set: Set[int],
    ) -> Optional[Dict[str, Any]]:
        """
        Construct a trade package to acquire a target player.

        Tries to match target value with combination of players and picks.

        Args:
            target: Player we want to acquire
            our_players: Our available players
            our_picks: Our available picks
            protected_set: Set of protected player IDs

        Returns:
            Package dict with players, picks, and confidence, or None
        """
        trade_service = self._get_trade_service()
        target_team_id = target["team_id"]

        # Simple approach: try pick + depth player
        for pick in our_picks:
            for player in our_players:
                if player["player_id"] in protected_set:
                    continue

                # Skip high-value players (we want to keep them)
                if extract_overall_rating(player, default=0) >= 82:
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
        trade_service = self._get_trade_service()
        protected_set = set(self._directives.protected_player_ids)
        expendable_set = set(self._directives.expendable_player_ids)

        our_players = trade_service.get_tradeable_players(self._team_id)

        # Find veterans to shop (not protected, not already expendable)
        veterans = [
            p for p in our_players
            if (
                p.get("age", 0) >= self.MIN_AGE_VETERAN
                and p["player_id"] not in protected_set
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
        trade_service = self._get_trade_service()
        protected_set = set(self._directives.protected_player_ids)

        our_players = trade_service.get_tradeable_players(self._team_id)
        our_picks = trade_service.get_tradeable_picks(self._team_id)

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

            if trade_candidate["player_id"] in protected_set:
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
                    protected_set=protected_set,
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
        # Build asset lists for UI display
        sending = []
        sending_player_ids = []
        sending_pick_ids = []

        for player in sending_players:
            sending.append({
                "type": "player",
                "name": player.get("name", "Unknown"),
                "position": self._parse_position(player.get("position", "")),
                "overall": extract_overall_rating(player, default=0),
            })
            sending_player_ids.append(player["player_id"])

        for pick in sending_picks:
            round_num = pick.get("round", 0)
            season = pick.get("season", self._season)
            sending.append({
                "type": "pick",
                "name": f"{season} Round {round_num}",
                "round": round_num,
                "season": season,
            })
            sending_pick_ids.append(pick["id"])

        receiving = []
        receiving_player_ids = []
        receiving_pick_ids = []

        for player in receiving_players:
            receiving.append({
                "type": "player",
                "name": player.get("name", "Unknown"),
                "position": self._parse_position(player.get("position", "")),
                "overall": extract_overall_rating(player, default=0),
            })
            receiving_player_ids.append(player["player_id"])

        for pick in receiving_picks:
            round_num = pick.get("round", 0)
            season = pick.get("season", self._season)
            receiving.append({
                "type": "pick",
                "name": f"{season} Round {round_num}",
                "round": round_num,
                "season": season,
            })
            receiving_pick_ids.append(pick["id"])

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

        # Filter for players with meaningful cap hits (>$2M)
        # and exclude protected players
        cap_candidates = [
            p for p in our_players
            if p.get("cap_hit", 0) >= 2_000_000
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
        for partner_team_id in range(1, 33):
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

                # Only worth it if meaningful savings (>$1M)
                if cap_savings < 1_000_000:
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

    def _find_fair_pick_for_player(
        self,
        player: Dict[str, Any],
        their_picks: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Find a fair draft pick to trade for a player.

        Simple heuristic based on overall rating:
        - 85+ OVR: 1st or 2nd round pick
        - 75-84 OVR: 3rd or 4th round pick
        - 65-74 OVR: 5th+ round pick

        Args:
            player: Player we're trading
            their_picks: Available picks from trade partner

        Returns:
            Best matching pick, or None
        """
        overall = extract_overall_rating(player, default=70)

        # Determine fair pick round range
        if overall >= 85:
            target_rounds = [1, 2]
        elif overall >= 75:
            target_rounds = [3, 4]
        else:
            target_rounds = [5, 6, 7]

        # Find best matching pick
        for target_round in target_rounds:
            for pick in their_picks:
                if pick.get("round") == target_round:
                    return pick

        # Fallback: any pick
        return their_picks[0] if their_picks else None

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

    def _calculate_value_differential(
        self,
        sending_players: List[Dict],
        sending_picks: List[Dict],
        receiving_players: List[Dict],
        receiving_picks: List[Dict],
    ) -> int:
        """
        Calculate rough value differential (positive = good for us).

        Simple heuristic based on overall ratings and pick rounds.
        """
        def player_value(p: Dict) -> int:
            return (extract_overall_rating(p, default=70) - 70) * 100_000

        def pick_value(p: Dict) -> int:
            round_values = {1: 800_000, 2: 400_000, 3: 200_000,
                          4: 100_000, 5: 50_000, 6: 25_000, 7: 10_000}
            return round_values.get(p.get("round", 7), 10_000)

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
