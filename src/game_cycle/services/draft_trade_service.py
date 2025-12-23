"""
Draft Trade Service - Manages trade proposals during the NFL Draft.

Handles:
- Generating trade offers from AI teams who want to trade up
- Evaluating GM recommendations based on owner directives
- Executing accepted trades by updating pick ownership

Integration:
- Uses DraftOrderAPI for pick ownership updates
- Uses TradeService for trade evaluation and value calculations
- Integrates with owner philosophy for trade recommendations
"""

import logging
import sqlite3
import uuid
from typing import Any, Dict, List, Optional

from src.game_cycle.database.draft_order_api import DraftOrderAPI
from src.game_cycle.services.trade_service import TradeService
from src.transactions.models import TradeDecisionType


class DraftTradeService:
    """
    Manages trade proposals during the draft.

    Generates realistic trade offers when user is on the clock,
    provides GM recommendations based on owner philosophy,
    and executes approved trades.
    """

    # Jimmy Johnson Draft Pick Value Chart (reference values)
    # Pick 1 = 3000, Pick 10 = 1300, Pick 32 = 590, Pick 64 = 270
    PICK_VALUES = {
        1: 3000, 2: 2600, 3: 2200, 4: 1800, 5: 1700,
        6: 1600, 7: 1500, 8: 1400, 9: 1350, 10: 1300,
        11: 1250, 12: 1200, 13: 1150, 14: 1100, 15: 1050,
        16: 1000, 17: 950, 18: 900, 19: 875, 20: 850,
        21: 800, 22: 780, 23: 760, 24: 740, 25: 720,
        26: 700, 27: 680, 28: 660, 29: 640, 30: 620,
        31: 600, 32: 590,
        # Round 2
        33: 580, 48: 420, 64: 270,
        # Round 3
        65: 265, 96: 148,
        # Round 4
        97: 145, 128: 75,
        # Round 5
        129: 72, 160: 40,
        # Round 6
        161: 38, 192: 20,
        # Round 7
        193: 19, 224: 2,
    }

    # Trade offer frequency by round
    TRADE_INTEREST_BY_ROUND = {
        1: (1, 3),  # Round 1: 1-3 offers
        2: (0, 2),  # Round 2: 0-2 offers
        3: (0, 2),  # Round 3: 0-2 offers
        4: (0, 1),  # Round 4-7: 0-1 offers
        5: (0, 1),
        6: (0, 1),
        7: (0, 0),  # Round 7: rarely trade up
    }

    def __init__(
        self,
        db_path: str,
        dynasty_id: str,
        season: int,
        user_team_id: int
    ):
        """
        Initialize the draft trade service.

        Args:
            db_path: Path to game cycle database
            dynasty_id: Dynasty identifier
            season: Current season year
            user_team_id: User's team ID (1-32)
        """
        self._db_path = db_path
        self._dynasty_id = dynasty_id
        self._season = season
        self._user_team_id = user_team_id
        self._logger = logging.getLogger(__name__)

        # Lazy-loaded services
        self._draft_order_api: Optional[DraftOrderAPI] = None
        self._trade_service: Optional[TradeService] = None

    def _get_draft_order_api(self) -> DraftOrderAPI:
        """Get or create DraftOrderAPI instance."""
        if self._draft_order_api is None:
            self._draft_order_api = DraftOrderAPI(self._db_path)
        return self._draft_order_api

    def _get_trade_service(self) -> TradeService:
        """Get or create TradeService instance."""
        if self._trade_service is None:
            self._trade_service = TradeService(
                db_path=self._db_path,
                dynasty_id=self._dynasty_id,
                season=self._season
            )
        return self._trade_service

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with Row factory."""
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # =========================================================================
    # Trade Offer Generation
    # =========================================================================

    def generate_trade_offers_for_pick(
        self,
        pick_info: Dict[str, Any],
        available_prospects: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Generate AI trade offers when user is on the clock.

        AI teams evaluate if they want to trade up for any prospect
        available at this pick position. Consider:
        - Teams drafting after user might want to trade up
        - Higher value picks (earlier rounds) get more interest
        - Teams with specific needs matching top prospects trade up

        Args:
            pick_info: Dict with {round, pick_in_round, overall, team_id}
            available_prospects: List of prospects still available

        Returns:
            List of trade offer dicts with:
                - proposal_id: str (UUID)
                - offering_team: str
                - offering_team_id: int
                - offering_assets: List[Dict]
                - requesting_pick: str
                - gm_recommendation: str
                - gm_reasoning: str
                - gm_confidence: float
        """
        round_num = pick_info.get("round", 1)
        overall_pick = pick_info.get("overall", 1)

        # Determine how many offers to generate
        min_offers, max_offers = self.TRADE_INTEREST_BY_ROUND.get(round_num, (0, 1))

        if max_offers == 0:
            self._logger.debug(
                f"No trade offers for round {round_num}, pick {overall_pick}"
            )
            return []

        # Find interested teams (drafting after user)
        interested_teams = self._find_interested_teams(
            overall_pick=overall_pick,
            available_prospects=available_prospects,
            max_teams=max_offers
        )

        # Generate offers from interested teams
        offers = []
        for team_info in interested_teams:
            offer = self._create_trade_offer(
                offering_team_id=team_info["team_id"],
                user_pick_info=pick_info,
                team_pick_info=team_info
            )
            if offer:
                offers.append(offer)

        self._logger.info(
            f"Generated {len(offers)} trade offers for pick {overall_pick} "
            f"(round {round_num})"
        )

        return offers

    def _find_interested_teams(
        self,
        overall_pick: int,
        available_prospects: List[Dict[str, Any]],
        max_teams: int
    ) -> List[Dict[str, Any]]:
        """
        Find teams drafting after user who might want to trade up.

        Args:
            overall_pick: User's current pick number
            available_prospects: Prospects still on board
            max_teams: Maximum teams to return

        Returns:
            List of team info dicts with their draft picks
        """
        draft_order_api = self._get_draft_order_api()

        # Get all remaining picks this round (after user)
        current_round = (overall_pick - 1) // 32 + 1
        remaining_picks = draft_order_api.get_draft_order(
            dynasty_id=self._dynasty_id,
            season=self._season,
            round_number=current_round
        )

        # Filter to picks after user's pick
        later_picks = [
            p for p in remaining_picks
            if p.overall_pick > overall_pick and not p.is_completed
        ]

        # Simple heuristic: teams 5-15 picks later are most interested
        interested = []
        for pick in later_picks:
            gap = pick.overall_pick - overall_pick
            if 5 <= gap <= 15:  # Sweet spot for trading up
                interested.append({
                    "team_id": pick.team_id,
                    "overall_pick": pick.overall_pick,
                    "round": pick.round_number,
                    "pick_in_round": pick.pick_in_round,
                    "pick_id": pick.id,
                })

        # Return up to max_teams
        return interested[:max_teams]

    def _create_trade_offer(
        self,
        offering_team_id: int,
        user_pick_info: Dict[str, Any],
        team_pick_info: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Create a trade offer from an AI team to trade up.

        Args:
            offering_team_id: Team making the offer
            user_pick_info: User's pick being requested
            team_pick_info: Offering team's pick info

        Returns:
            Trade offer dict or None if offer can't be constructed
        """
        trade_service = self._get_trade_service()

        user_overall = user_pick_info.get("overall", 1)
        team_overall = team_pick_info.get("overall_pick", 32)

        # Calculate value differential
        user_pick_value = self._calculate_pick_value(user_overall)
        team_pick_value = self._calculate_pick_value(team_overall)
        value_gap = user_pick_value - team_pick_value

        # Find additional picks to match value
        additional_picks = self._find_compensation_picks(
            offering_team_id=offering_team_id,
            value_needed=value_gap
        )

        if not additional_picks:
            self._logger.debug(
                f"Team {offering_team_id} lacks compensation to trade up "
                f"from {team_overall} to {user_overall}"
            )
            return None

        # Build proposal using TradeService
        try:
            their_pick_ids = [team_pick_info["pick_id"]] + [
                p["pick_id"] for p in additional_picks
            ]

            # Get user's pick ID from draft order
            draft_order_api = self._get_draft_order_api()
            user_picks = draft_order_api.get_team_picks(
                dynasty_id=self._dynasty_id,
                team_id=self._user_team_id,
                season=self._season
            )
            user_pick_obj = next(
                (p for p in user_picks if p.overall_pick == user_overall),
                None
            )
            if not user_pick_obj:
                return None

            # Create proposal
            proposal = trade_service.propose_trade(
                team1_id=self._user_team_id,
                team1_player_ids=[],
                team2_id=offering_team_id,
                team2_player_ids=[],
                team1_pick_ids=[user_pick_obj.id],
                team2_pick_ids=their_pick_ids
            )

            # Get GM recommendation
            gm_rec = self.get_gm_trade_recommendation(
                trade_offer={
                    "user_pick": user_pick_info,
                    "their_picks": [team_pick_info] + additional_picks,
                    "value_ratio": proposal.value_ratio,
                    "fairness": proposal.fairness_rating.value,
                }
            )

            # Get team name
            team_name = self._get_team_name(offering_team_id)

            return {
                "proposal_id": str(uuid.uuid4()),
                "offering_team": team_name,
                "offering_team_id": offering_team_id,
                "offering_assets": [
                    {
                        "type": "pick",
                        "round": team_pick_info["round"],
                        "overall": team_pick_info["overall_pick"],
                        "pick_id": team_pick_info["pick_id"],
                    }
                ] + [
                    {
                        "type": "pick",
                        "round": p["round"],
                        "overall": p["overall_pick"],
                        "pick_id": p["pick_id"],
                    }
                    for p in additional_picks
                ],
                "requesting_pick": f"Pick {user_overall} (Round {user_pick_info['round']})",
                "user_pick_id": user_pick_obj.id,
                "gm_recommendation": gm_rec["recommendation"],
                "gm_reasoning": gm_rec["reasoning"],
                "gm_confidence": gm_rec["confidence"],
                "value_ratio": proposal.value_ratio,
            }

        except Exception as e:
            self._logger.warning(
                f"Error creating trade offer from team {offering_team_id}: {e}"
            )
            return None

    def _find_compensation_picks(
        self,
        offering_team_id: int,
        value_needed: int
    ) -> List[Dict[str, Any]]:
        """
        Find additional picks team can offer to match value.

        Args:
            offering_team_id: Team ID offering picks
            value_needed: Value differential to cover

        Returns:
            List of pick info dicts
        """
        draft_order_api = self._get_draft_order_api()

        # Get team's picks for this draft
        team_picks = draft_order_api.get_team_picks(
            dynasty_id=self._dynasty_id,
            team_id=offering_team_id,
            season=self._season
        )

        # Filter to uncompleted picks (not their current pick)
        available = [
            p for p in team_picks
            if not p.is_completed
        ]

        # Sort by value (lower overall = higher value)
        available.sort(key=lambda p: p.overall_pick)

        # Greedy algorithm: add picks until value covered
        compensation = []
        current_value = 0

        for pick in available[1:]:  # Skip first (their current pick)
            if current_value >= value_needed:
                break

            pick_value = self._calculate_pick_value(pick.overall_pick)
            current_value += pick_value
            compensation.append({
                "pick_id": pick.id,
                "round": pick.round_number,
                "overall_pick": pick.overall_pick,
                "value": pick_value,
            })

        # Only return if we got close to value needed (80% minimum)
        if current_value >= value_needed * 0.8:
            return compensation

        return []

    # =========================================================================
    # GM Recommendation
    # =========================================================================

    def get_gm_trade_recommendation(
        self,
        trade_offer: Dict[str, Any],
        owner_directives: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Get GM's recommendation on an incoming trade offer.

        Consider:
        - Pick value differential (using draft pick value chart)
        - Team needs that could be addressed with offered picks
        - Owner philosophy (rebuild = value picks more, win_now = keep high picks)

        Args:
            trade_offer: Trade offer dict with pick details
            owner_directives: Optional owner philosophy/directives

        Returns:
            Dict with:
                - recommendation: "accept" or "reject"
                - reasoning: str
                - confidence: float (0.5-0.95)
        """
        value_ratio = trade_offer.get("value_ratio", 1.0)
        fairness = trade_offer.get("fairness", "BALANCED")

        # Extract philosophy if provided
        philosophy = "maintain"  # Default
        if owner_directives:
            philosophy = owner_directives.get("team_philosophy", "maintain")

        # Base decision on value ratio
        if value_ratio >= 1.15:
            # Great value for us
            recommendation = "accept"
            confidence = 0.85
            reasoning = (
                f"Excellent value in this trade (receiving {value_ratio:.2f}x value). "
                f"The compensation significantly exceeds the value of our pick. "
                f"I recommend accepting this offer."
            )

        elif value_ratio >= 1.05:
            # Good value, depends on philosophy
            if philosophy == "rebuild":
                recommendation = "accept"
                confidence = 0.75
                reasoning = (
                    f"Good value trade (receiving {value_ratio:.2f}x value). "
                    f"Given our rebuild focus, accumulating draft capital is a priority. "
                    f"I recommend accepting."
                )
            else:
                recommendation = "reject"
                confidence = 0.65
                reasoning = (
                    f"Modest value gain (receiving {value_ratio:.2f}x value), "
                    f"but we'd be trading down and losing a chance at a premium prospect. "
                    f"I recommend staying at our current pick."
                )

        elif value_ratio >= 0.95:
            # Balanced trade
            recommendation = "reject"
            confidence = 0.70
            reasoning = (
                f"This is a fair trade (value ratio {value_ratio:.2f}), "
                f"but I recommend staying put to select the best available prospect "
                f"at our current position."
            )

        else:
            # Bad value for us
            recommendation = "reject"
            confidence = 0.90
            reasoning = (
                f"This offer undervalues our pick (only {value_ratio:.2f}x value). "
                f"The compensation is insufficient to move down. "
                f"I strongly recommend rejecting."
            )

        return {
            "recommendation": recommendation,
            "reasoning": reasoning,
            "confidence": min(0.95, max(0.5, confidence)),
        }

    # =========================================================================
    # Trade Execution
    # =========================================================================

    def execute_draft_trade(
        self,
        proposal_id: str,
        offer: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute an approved trade during draft.

        Uses DraftOrderAPI.update_pick_ownership() to transfer picks.

        Args:
            proposal_id: Unique proposal identifier
            offer: Trade offer dict with pick IDs and team info

        Returns:
            Dict with:
                - success: bool
                - new_pick_owner: int (team_id)
                - message: str
        """
        draft_order_api = self._get_draft_order_api()
        conn = self._get_connection()

        try:
            # Extract details
            user_pick_id = offer.get("user_pick_id")
            offering_team_id = offer.get("offering_team_id")
            offering_assets = offer.get("offering_assets", [])

            if not user_pick_id or not offering_team_id:
                return {
                    "success": False,
                    "message": "Invalid trade offer: missing pick IDs or team info"
                }

            # Start transaction
            conn.execute("BEGIN IMMEDIATE")

            # Transfer user's pick to offering team
            success = draft_order_api.update_pick_ownership(
                pick_id=user_pick_id,
                new_owner_team_id=offering_team_id,
                is_traded=True,
                conn=conn
            )

            if not success:
                conn.rollback()
                return {
                    "success": False,
                    "message": f"Failed to transfer pick {user_pick_id}"
                }

            # Transfer offering team's picks to user
            for asset in offering_assets:
                if asset.get("type") == "pick":
                    pick_id = asset.get("pick_id")
                    success = draft_order_api.update_pick_ownership(
                        pick_id=pick_id,
                        new_owner_team_id=self._user_team_id,
                        is_traded=True,
                        conn=conn
                    )

                    if not success:
                        conn.rollback()
                        return {
                            "success": False,
                            "message": f"Failed to transfer pick {pick_id}"
                        }

            # Commit transaction
            conn.commit()

            team_name = offer.get("offering_team", f"Team {offering_team_id}")
            message = (
                f"Trade executed with {team_name}: "
                f"Traded pick {user_pick_id} for {len(offering_assets)} picks"
            )

            self._logger.info(message)

            return {
                "success": True,
                "new_pick_owner": offering_team_id,
                "message": message,
                "traded_picks": len(offering_assets),
            }

        except Exception as e:
            conn.rollback()
            error_msg = f"Trade execution failed: {e}"
            self._logger.error(error_msg, exc_info=True)
            return {
                "success": False,
                "message": error_msg
            }

        finally:
            conn.close()

    # =========================================================================
    # Pick Value Calculation
    # =========================================================================

    def _calculate_pick_value(self, overall_pick: int) -> int:
        """
        Calculate pick value using standard NFL draft value chart.

        Uses Jimmy Johnson draft chart as reference:
        Pick 1 = 3000, Pick 32 = 590, Pick 224 = 2, etc.

        Args:
            overall_pick: Overall pick number (1-262)

        Returns:
            Pick value in arbitrary units
        """
        # Direct lookup for common picks
        if overall_pick in self.PICK_VALUES:
            return self.PICK_VALUES[overall_pick]

        # Interpolate for picks not in chart
        # Round 1 (1-32)
        if overall_pick <= 32:
            return int(3000 - (overall_pick - 1) * (2400 / 31))

        # Round 2 (33-64)
        elif overall_pick <= 64:
            return int(600 - (overall_pick - 32) * (330 / 32))

        # Round 3 (65-96)
        elif overall_pick <= 96:
            return int(270 - (overall_pick - 64) * (122 / 32))

        # Round 4 (97-128)
        elif overall_pick <= 128:
            return int(148 - (overall_pick - 96) * (73 / 32))

        # Round 5 (129-160)
        elif overall_pick <= 160:
            return int(75 - (overall_pick - 128) * (35 / 32))

        # Round 6 (161-192)
        elif overall_pick <= 192:
            return int(40 - (overall_pick - 160) * (20 / 32))

        # Round 7+ (193-262)
        else:
            return max(2, int(20 * (0.95 ** (overall_pick - 192))))

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _get_team_name(self, team_id: int) -> str:
        """Get team name from database."""
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "SELECT team_name FROM teams WHERE team_id = ?",
                (team_id,)
            )
            row = cursor.fetchone()
            if row:
                return row["team_name"]
            return f"Team {team_id}"
        except Exception as e:
            # Log database error but return fallback name
            self._logger.debug(f"Could not fetch team name for team_id {team_id}: {e}")
            return f"Team {team_id}"
        finally:
            conn.close()
