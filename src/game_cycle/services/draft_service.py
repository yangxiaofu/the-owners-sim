"""
Draft Service for Game Cycle.

Handles draft operations during the offseason draft stage.
Wraps existing DraftManager and DraftClassAPI for game cycle integration.
"""

from datetime import date
from typing import Dict, List, Any, Optional
import json
import logging
import sqlite3

from src.persistence.transaction_logger import TransactionLogger
from src.game_cycle.models import DraftStrategy, DraftDirection, DraftDirectionResult


class DraftService:
    """
    Service for draft stage operations in game cycle.

    Manages:
    - Draft class generation (one season ahead)
    - Draft order generation based on standings/playoffs
    - AI team draft picks (needs-based selection)
    - User team draft picks (manual or auto)
    - Progress tracking and state persistence

    Architecture:
    - Wraps existing DraftManager for draft logic
    - Wraps DraftClassAPI for prospect database operations
    - Dynasty-isolated (all operations scoped to dynasty_id)
    """

    def __init__(
        self,
        db_path: str,
        dynasty_id: str,
        season: int
    ):
        """
        Initialize the draft service.

        Args:
            db_path: Path to the game cycle database
            dynasty_id: Dynasty identifier for isolation
            season: Current season year (draft year)
        """
        self._db_path = db_path
        self._dynasty_id = dynasty_id
        self._season = season
        self._logger = logging.getLogger(__name__)

        # Lazy-loaded APIs (created on first use)
        self._draft_class_api = None
        self._draft_order_api = None
        self._needs_analyzer = None
        self._cap_helper = None

        # Transaction logger for audit trail
        self._transaction_logger = TransactionLogger(db_path)

    def _get_cap_helper(self):
        """Get or create cap helper instance.

        Uses season + 1 because during the draft (offseason),
        rookie contracts and cap calculations are for the NEXT league year.
        """
        if self._cap_helper is None:
            from .cap_helper import CapHelper
            # Draft picks/contracts are for NEXT season
            self._cap_helper = CapHelper(self._db_path, self._dynasty_id, self._season + 1)
        return self._cap_helper

    def get_cap_summary(self, team_id: int) -> dict:
        """
        Get salary cap summary for a team.

        Args:
            team_id: Team ID

        Returns:
            Dict with salary_cap_limit, total_spending, available_space,
            dead_money, is_compliant
        """
        return self._get_cap_helper().get_cap_summary(team_id)

    def estimate_rookie_cap_hit(self, overall_pick: int) -> int:
        """
        Estimate year-1 cap hit for a rookie based on draft position.

        Args:
            overall_pick: Overall draft pick number (1-224)

        Returns:
            Estimated year-1 cap hit in dollars
        """
        return self._get_cap_helper().estimate_rookie_cap_hit(overall_pick)

    # ========================================================================
    # DRAFT CLASS MANAGEMENT
    # ========================================================================

    def ensure_draft_class_exists(self, draft_year: Optional[int] = None) -> Dict[str, Any]:
        """
        Ensure draft class exists for the specified year.

        If draft class doesn't exist, generates 224 prospects (7 rounds x 32 picks).
        Idempotent - safe to call multiple times.

        Args:
            draft_year: Year for draft class (defaults to self._season)

        Returns:
            Dict with:
                - exists: bool (True if already existed)
                - generated: bool (True if newly generated)
                - prospect_count: int
                - draft_class_id: str
                - error: Optional[str]
        """
        year = draft_year or self._season
        api = self._get_draft_class_api()

        # Idempotency check
        if api.dynasty_has_draft_class(self._dynasty_id, year):
            count = api.get_draft_prospects_count(self._dynasty_id, year)
            self._logger.info(f"Draft class for {year} already exists ({count} prospects)")
            return {
                "exists": True,
                "generated": False,
                "prospect_count": count,
                "draft_class_id": f"DRAFT_{self._dynasty_id}_{year}",
            }

        # Generate new draft class
        try:
            count = api.generate_draft_class(
                dynasty_id=self._dynasty_id,
                season=year
            )
            self._logger.info(f"Generated draft class for {year}: {count} prospects")
            return {
                "exists": False,
                "generated": True,
                "prospect_count": count,
                "draft_class_id": f"DRAFT_{self._dynasty_id}_{year}",
            }
        except Exception as e:
            self._logger.error(f"Draft class generation failed: {e}")
            return {
                "exists": False,
                "generated": False,
                "prospect_count": 0,
                "error": str(e),
            }

    def _get_standings_from_db(self) -> List[Dict[str, Any]]:
        """
        Get all team standings for the season from game_cycle.db.

        Returns:
            List of dicts with team records and playoff progression flags.
        """
        conn = sqlite3.connect(self._db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT team_id, wins, losses, ties,
                   made_playoffs, won_wild_card, won_division_round,
                   won_conference, won_super_bowl
            FROM standings
            WHERE dynasty_id = ? AND season = ? AND season_type = 'regular_season'
            ORDER BY wins DESC, ties DESC
        """, (self._dynasty_id, self._season))

        rows = cursor.fetchall()
        conn.close()

        return [
            {
                "team_id": row[0],
                "wins": row[1],
                "losses": row[2],
                "ties": row[3],
                "made_playoffs": bool(row[4]),
                "won_wild_card": bool(row[5]),
                "won_division_round": bool(row[6]),
                "won_conference": bool(row[7]),
                "won_super_bowl": bool(row[8]),
            }
            for row in rows
        ]

    def _extract_playoff_results(self, standings_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Extract playoff results from standings flags.

        Args:
            standings_data: List of team standings with playoff flags.

        Returns:
            Dict with categorized playoff losers and winners.
        """
        wild_card_losers = []
        divisional_losers = []
        conference_losers = []
        super_bowl_loser = None
        super_bowl_winner = None

        for team in standings_data:
            tid = team["team_id"]
            if team["won_super_bowl"]:
                super_bowl_winner = tid
            elif team["won_conference"]:
                super_bowl_loser = tid
            elif team["won_division_round"]:
                conference_losers.append(tid)
            elif team["won_wild_card"]:
                divisional_losers.append(tid)
            elif team["made_playoffs"]:
                wild_card_losers.append(tid)

        return {
            "wild_card_losers": wild_card_losers,       # 6 teams
            "divisional_losers": divisional_losers,     # 4 teams
            "conference_losers": conference_losers,     # 2 teams
            "super_bowl_loser": super_bowl_loser,       # 1 team
            "super_bowl_winner": super_bowl_winner,     # 1 team
        }

    def _has_valid_playoff_results(self, playoff_results: Dict[str, Any]) -> bool:
        """
        Check if playoff results have complete data for DraftOrderService.

        DraftOrderService requires exact counts:
        - 6 wild card losers
        - 4 divisional losers
        - 2 conference losers
        - Integer super_bowl_loser
        - Integer super_bowl_winner

        Returns:
            True if playoff results are complete and valid.
        """
        return (
            len(playoff_results.get("wild_card_losers", [])) == 6 and
            len(playoff_results.get("divisional_losers", [])) == 4 and
            len(playoff_results.get("conference_losers", [])) == 2 and
            isinstance(playoff_results.get("super_bowl_loser"), int) and
            isinstance(playoff_results.get("super_bowl_winner"), int)
        )

    def ensure_draft_order_exists(self) -> Dict[str, Any]:
        """
        Ensure draft order exists for the current draft year.

        Generates draft order based on inverse standings and playoff results.
        Uses DraftOrderService from main.py for the real algorithm.
        Falls back to simple ordering if no standings data available.

        Returns:
            Dict with:
                - exists: bool
                - generated: bool
                - total_picks: int
                - error: Optional[str]
        """
        api = self._get_draft_order_api()

        # Check if draft order exists
        existing_picks = api.get_draft_order(self._dynasty_id, self._season)
        if existing_picks and len(existing_picks) > 0:
            return {
                "exists": True,
                "generated": False,
                "total_picks": len(existing_picks),
            }

        try:
            # Get standings from game_cycle.db
            standings_data = self._get_standings_from_db()

            if not standings_data:
                # Fallback: generate simple order if no standings
                self._logger.warning(
                    "No standings data found - using fallback draft order"
                )
                return self._generate_fallback_draft_order()

            # Build TeamRecord objects for DraftOrderService
            from offseason.draft_order_service import DraftOrderService, TeamRecord

            standings = [
                TeamRecord(
                    team_id=s["team_id"],
                    wins=s["wins"],
                    losses=s["losses"],
                    ties=s["ties"],
                    win_percentage=s["wins"] / max(s["wins"] + s["losses"] + s["ties"], 1)
                )
                for s in standings_data
            ]

            # Extract playoff results from standings flags
            playoff_results = self._extract_playoff_results(standings_data)

            # Validate playoff results are complete before using DraftOrderService
            if not self._has_valid_playoff_results(playoff_results):
                self._logger.warning(
                    "Incomplete playoff data - using fallback draft order"
                )
                return self._generate_fallback_draft_order()

            # Calculate draft order using existing service
            draft_order_service = DraftOrderService(
                dynasty_id=self._dynasty_id,
                season_year=self._season
            )
            draft_picks = draft_order_service.calculate_draft_order(standings, playoff_results)

            # Convert to DraftPick objects and save
            from database.draft_order_database_api import DraftPick
            db_picks = [
                DraftPick(
                    pick_id=None,
                    dynasty_id=self._dynasty_id,
                    season=self._season,
                    round_number=pick.round_number,
                    pick_in_round=pick.pick_in_round,
                    overall_pick=pick.overall_pick,
                    original_team_id=pick.original_team_id,
                    current_team_id=pick.team_id,
                )
                for pick in draft_picks
            ]

            api.save_draft_order(db_picks)

            self._logger.info(
                f"Generated draft order from standings: {len(db_picks)} picks"
            )
            return {
                "exists": False,
                "generated": True,
                "total_picks": len(db_picks),
            }

        except Exception as e:
            self._logger.error(f"Draft order generation failed: {e}")
            return {
                "exists": False,
                "generated": False,
                "total_picks": 0,
                "error": str(e),
            }

    def _generate_fallback_draft_order(self) -> Dict[str, Any]:
        """
        Generate draft order from standings when playoff data is incomplete.

        Uses inverse standings order (worst record first) to determine
        draft order. This ensures teams with worse records pick earlier
        even when full playoff results aren't available.

        Returns:
            Dict with generation result.
        """
        api = self._get_draft_order_api()

        try:
            from database.draft_order_database_api import DraftPick

            # Get standings sorted by record (worst first for draft)
            standings_data = self._get_standings_from_db()

            if standings_data and len(standings_data) == 32:
                # Sort by wins ASC (worst record first), then ties ASC
                standings_data.sort(key=lambda s: (s["wins"], s["ties"]))
                team_order = [s["team_id"] for s in standings_data]
                self._logger.info("Using standings-based draft order (worst record first)")
            else:
                # Ultimate fallback: reverse team order (team 32 picks 1st, etc.)
                # Still better than sequential team_id = pick_in_round
                team_order = list(range(32, 0, -1))
                self._logger.warning(
                    f"No valid standings ({len(standings_data) if standings_data else 0} teams) - "
                    "using reversed team ID order"
                )

            picks = []
            for round_num in range(1, 8):
                for pick_in_round in range(1, 33):
                    overall_pick = (round_num - 1) * 32 + pick_in_round
                    team_id = team_order[pick_in_round - 1]  # Use standings order

                    pick = DraftPick(
                        pick_id=None,
                        dynasty_id=self._dynasty_id,
                        season=self._season,
                        round_number=round_num,
                        pick_in_round=pick_in_round,
                        overall_pick=overall_pick,
                        original_team_id=team_id,
                        current_team_id=team_id,
                    )
                    picks.append(pick)

            api.save_draft_order(picks)

            self._logger.info(f"Generated standings-based draft order: {len(picks)} picks")
            return {
                "exists": False,
                "generated": True,
                "total_picks": len(picks),
            }

        except Exception as e:
            self._logger.error(f"Draft order generation failed: {e}")
            return {
                "exists": False,
                "generated": False,
                "total_picks": 0,
                "error": str(e),
            }

    # ========================================================================
    # PROSPECT ACCESS
    # ========================================================================

    def get_available_prospects(
        self,
        position_filter: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get available (undrafted) prospects from the draft class.

        Args:
            position_filter: Optional position to filter (QB, RB, WR, etc.)
            limit: Maximum prospects to return

        Returns:
            List of prospect dicts sorted by overall rating (descending)
        """
        api = self._get_draft_class_api()

        if position_filter:
            prospects = api.get_prospects_by_position(
                dynasty_id=self._dynasty_id,
                season=self._season,
                position=position_filter,
                available_only=True
            )
        else:
            prospects = api.get_all_prospects(
                dynasty_id=self._dynasty_id,
                season=self._season,
                available_only=True
            )

        # Transform fields for UI compatibility
        for rank, prospect in enumerate(prospects, start=1):
            # Combine first/last name into 'name' field (UI expects 'name')
            first = prospect.get('first_name', '')
            last = prospect.get('last_name', '')
            prospect['name'] = f"{first} {last}".strip() or "Unknown"

            # Map player_id to prospect_id for UI consistency
            prospect['prospect_id'] = prospect.get('player_id')

            # Add rank based on position in sorted list (already sorted by overall DESC)
            prospect['rank'] = rank

        return prospects[:limit]

    def get_current_pick(self) -> Optional[Dict[str, Any]]:
        """
        Get the current pick on the clock.

        Returns:
            Dict with pick info or None if draft complete
        """
        api = self._get_draft_order_api()
        all_picks = api.get_draft_order(self._dynasty_id, self._season)

        if not all_picks:
            return None

        # Find first un-executed pick
        for pick in all_picks:
            if not pick.is_executed:
                return {
                    "pick_id": pick.pick_id,
                    "round_number": pick.round_number,
                    "round": pick.round_number,  # UI compatibility
                    "pick_in_round": pick.pick_in_round,
                    "overall_pick": pick.overall_pick,
                    "current_team_id": pick.current_team_id,
                    "team_id": pick.current_team_id,  # UI compatibility
                    "original_team_id": pick.original_team_id,
                }

        return None  # Draft complete

    # ========================================================================
    # PICK EXECUTION
    # ========================================================================

    def make_draft_pick(
        self,
        prospect_id: int,
        team_id: int,
        pick_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a draft pick (user or AI).

        Args:
            prospect_id: The prospect's player_id from draft_prospects
            team_id: Team making the pick
            pick_info: Optional pick info (if None, gets current pick)

        Returns:
            Dict with success status and pick details
        """
        draft_api = self._get_draft_class_api()
        order_api = self._get_draft_order_api()

        # Get pick info if not provided
        if pick_info is None:
            pick_info = self.get_current_pick()
            if pick_info is None:
                return {"success": False, "error": "Draft is complete"}

        # Validate team matches current pick
        if pick_info["current_team_id"] != team_id:
            return {
                "success": False,
                "error": f"Team {team_id} does not have pick {pick_info['overall_pick']}"
            }

        # Get prospect info
        prospect = draft_api.get_prospect_by_id(prospect_id, self._dynasty_id)
        if prospect is None:
            return {"success": False, "error": f"Prospect {prospect_id} not found"}

        if prospect.get("is_drafted"):
            return {"success": False, "error": f"Prospect {prospect_id} already drafted"}

        try:
            # Mark prospect as drafted
            draft_api.mark_prospect_drafted(
                player_id=prospect_id,
                team_id=team_id,
                actual_round=pick_info["round_number"],
                actual_pick=pick_info["pick_in_round"],
                dynasty_id=self._dynasty_id
            )

            # Convert prospect to player (returns NEW player_id)
            new_player_id = draft_api.convert_prospect_to_player(
                player_id=prospect_id,
                team_id=team_id,
                dynasty_id=self._dynasty_id
            )

            # Create rookie contract for drafted player
            try:
                from salary_cap.contract_manager import ContractManager
                contract_manager = ContractManager(self._db_path)

                # Get salary cap for rookie contract scaling
                cap_helper = self._get_cap_helper()
                salary_cap = cap_helper.DEFAULT_CAP_LIMIT

                contract_id = contract_manager.create_rookie_contract(
                    player_id=new_player_id,
                    team_id=team_id,
                    dynasty_id=self._dynasty_id,
                    draft_pick=pick_info["overall_pick"],
                    salary_cap=salary_cap,
                    season=self._season  # Rookie contracts start this season (active immediately)
                )
                self._logger.info(
                    f"Created rookie contract {contract_id} for player {new_player_id} "
                    f"(pick #{pick_info['overall_pick']})"
                )

                # Update player's contract_id FK
                from database.player_roster_api import PlayerRosterAPI
                roster_api = PlayerRosterAPI(self._db_path)
                roster_api.update_player_contract_id(
                    dynasty_id=self._dynasty_id,
                    player_id=new_player_id,
                    contract_id=contract_id
                )
            except Exception as contract_err:
                # Log but don't fail the draft pick if contract creation fails
                self._logger.error(
                    f"Failed to create rookie contract for player {new_player_id}: {contract_err}"
                )

            # Mark pick as executed in draft order
            order_api.mark_pick_executed(
                pick_id=pick_info["pick_id"],
                player_id=new_player_id
            )

            player_name = f"{prospect['first_name']} {prospect['last_name']}"

            self._logger.info(
                f"Pick {pick_info['overall_pick']}: Team {team_id} selects "
                f"{player_name} ({prospect['position']}, {prospect['overall']} OVR)"
            )

            # Log transaction for audit trail
            self._transaction_logger.log_transaction(
                dynasty_id=self._dynasty_id,
                season=self._season + 1,  # Draft is for next season
                transaction_type="DRAFT",
                player_id=new_player_id,
                player_name=player_name,
                position=prospect["position"],
                from_team_id=None,  # From draft pool
                to_team_id=team_id,
                transaction_date=date(self._season + 1, 4, 24),  # Draft date (next year)
                details={
                    "round": pick_info["round_number"],
                    "pick": pick_info["pick_in_round"],
                    "overall_pick": pick_info["overall_pick"],
                    "overall": prospect["overall"],
                    "college": prospect.get("college", ""),
                }
            )

            return {
                "success": True,
                "player_id": new_player_id,
                "prospect_id": prospect_id,
                "player_name": player_name,
                "position": prospect["position"],
                "overall": prospect["overall"],
                "round": pick_info["round_number"],
                "pick": pick_info["pick_in_round"],
                "overall_pick": pick_info["overall_pick"],
                "team_id": team_id,
            }

        except Exception as e:
            self._logger.error(f"Draft pick failed: {e}")
            return {"success": False, "error": str(e)}

    def process_ai_pick(
        self,
        team_id: int,
        pick_info: Dict[str, Any],
        draft_direction: Optional[DraftDirection] = None
    ) -> Dict[str, Any]:
        """
        Process an AI team's draft pick using needs-based selection.

        Now supports draft direction for owner-controlled teams:
        - BPA: Ignores needs, picks highest overall
        - Balanced: Default behavior (need boost + reach penalty)
        - Needs-Based: Aggressive need bonuses, willing to reach

        Args:
            team_id: Team making the pick
            pick_info: Pick info dict
            draft_direction: Owner's draft direction (only applies to user's team)

        Returns:
            Dict with success status and pick details
        """
        # Get team needs
        needs_analyzer = self._get_needs_analyzer()
        team_needs = needs_analyzer.analyze_team_needs(
            team_id=team_id,
            season=self._season
        )

        # Get available prospects
        prospects = self.get_available_prospects(limit=224)

        if not prospects:
            return {"success": False, "error": "No prospects available"}

        # Evaluate each prospect using direction-aware evaluation
        best_prospect = None
        best_score = -999
        best_result = None

        for prospect in prospects:
            result = self._evaluate_prospect_with_direction(
                prospect=prospect,
                team_needs=team_needs,
                pick_position=pick_info["overall_pick"],
                direction=draft_direction
            )
            if result.adjusted_score > best_score:
                best_score = result.adjusted_score
                best_prospect = prospect
                best_result = result

        if best_prospect is None:
            return {"success": False, "error": "Could not evaluate prospects"}

        # Log evaluation reason for debugging
        if best_result:
            self._logger.info(f"Pick #{pick_info['overall_pick']}: {best_result.reason}")

        # Make the pick
        return self.make_draft_pick(
            prospect_id=best_prospect["player_id"],
            team_id=team_id,
            pick_info=pick_info
        )

    def _evaluate_prospect(
        self,
        prospect: Dict[str, Any],
        team_needs: List[Dict[str, Any]],
        pick_position: int
    ) -> float:
        """
        Evaluate prospect value for a team.

        Args:
            prospect: Prospect dict with position and overall
            team_needs: List of team needs with urgency scores
            pick_position: Overall pick number (1-224)

        Returns:
            Adjusted value score
        """
        base_value = prospect["overall"]

        # Find position urgency
        position_urgency = 0
        for need in team_needs:
            if need["position"] == prospect["position"]:
                position_urgency = need.get("urgency_score", 0)
                break

        # Apply need-based bonus
        need_boost = 0
        if position_urgency >= 5:  # CRITICAL
            need_boost = 15
        elif position_urgency >= 4:  # HIGH
            need_boost = 8
        elif position_urgency >= 3:  # MEDIUM
            need_boost = 3

        base_value += need_boost

        # Reach penalty
        projected_min = prospect.get("projected_pick_min", 1)
        if pick_position < projected_min - 20:
            base_value -= 5

        return base_value

    # ========================================================================
    # DRAFT DIRECTION EVALUATION METHODS (Phase 1)
    # ========================================================================

    def _evaluate_prospect_with_direction(
        self,
        prospect: Dict[str, Any],
        team_needs: List[Dict[str, Any]],
        pick_position: int,
        direction: Optional[DraftDirection] = None
    ) -> DraftDirectionResult:
        """
        Main dispatcher - routes to strategy-specific evaluators.

        Args:
            prospect: Prospect data dict
            team_needs: List of needs with urgency scores
            pick_position: Overall pick number (1-224)
            direction: Owner's draft direction (None = default Balanced)

        Returns:
            DraftDirectionResult with scores and explanation
        """
        if direction is None:
            direction = DraftDirection(strategy=DraftStrategy.BALANCED)

        base_score = prospect["overall"]

        # Route to strategy-specific evaluator
        if direction.strategy == DraftStrategy.BEST_PLAYER_AVAILABLE:
            result = self._evaluate_bpa(prospect, base_score)
        elif direction.strategy == DraftStrategy.BALANCED:
            result = self._evaluate_balanced(prospect, team_needs, pick_position, base_score)
        elif direction.strategy == DraftStrategy.NEEDS_BASED:
            result = self._evaluate_needs_based(prospect, team_needs, base_score)
        elif direction.strategy == DraftStrategy.POSITION_FOCUS:
            result = self._evaluate_position_focus(
                prospect, team_needs, direction.priority_positions, base_score
            )
        else:
            # Fallback to balanced
            result = self._evaluate_balanced(prospect, team_needs, pick_position, base_score)

        # Phase 3: Apply watchlist bonus (not implemented yet)
        if prospect["player_id"] in direction.watchlist_prospect_ids:
            result.watchlist_bonus = 10
            result.adjusted_score += 10
            result.reason += " | Watchlist target (+10)"

        return result

    def _evaluate_bpa(
        self,
        prospect: Dict[str, Any],
        base_score: float
    ) -> DraftDirectionResult:
        """
        Best Player Available - ignore needs entirely.

        Philosophy: Always draft the highest-rated prospect regardless of need.

        Args:
            prospect: Prospect data dict
            base_score: Prospect's base overall rating

        Returns:
            DraftDirectionResult with BPA evaluation
        """
        return DraftDirectionResult(
            prospect_id=prospect["player_id"],
            prospect_name=prospect["name"],
            original_score=base_score,
            adjusted_score=base_score,
            strategy_bonus=0,
            position_bonus=0,
            watchlist_bonus=0,
            reach_penalty=0,
            reason="BPA: Highest overall rating"
        )

    def _evaluate_balanced(
        self,
        prospect: Dict[str, Any],
        team_needs: List[Dict[str, Any]],
        pick_position: int,
        base_score: float
    ) -> DraftDirectionResult:
        """
        Balanced - current system (needs + reach penalty).

        Philosophy: Balance talent and need - smart drafting that considers both value and fit.

        Args:
            prospect: Prospect data dict
            team_needs: List of team needs with urgency scores
            pick_position: Overall pick number (1-224)
            base_score: Prospect's base overall rating

        Returns:
            DraftDirectionResult with balanced evaluation
        """
        # Find need urgency
        position_urgency = 0
        for need in team_needs:
            if need["position"] == prospect["position"]:
                position_urgency = need.get("urgency_score", 0)
                break

        # Apply need boost
        need_boost = 0
        urgency_label = "LOW"
        if position_urgency >= 5:  # CRITICAL
            need_boost = 15
            urgency_label = "CRITICAL"
        elif position_urgency >= 4:  # HIGH
            need_boost = 8
            urgency_label = "HIGH"
        elif position_urgency >= 3:  # MEDIUM
            need_boost = 3
            urgency_label = "MEDIUM"

        # Reach penalty
        projected_min = prospect.get("projected_pick_min", pick_position)
        reach_penalty = -5 if pick_position < projected_min - 20 else 0

        adjusted_score = base_score + need_boost + reach_penalty

        return DraftDirectionResult(
            prospect_id=prospect["player_id"],
            prospect_name=prospect["name"],
            original_score=base_score,
            adjusted_score=adjusted_score,
            strategy_bonus=need_boost,
            position_bonus=0,
            watchlist_bonus=0,
            reach_penalty=reach_penalty,
            reason=f"Balanced: {urgency_label} need (+{need_boost})"
        )

    def _evaluate_needs_based(
        self,
        prospect: Dict[str, Any],
        team_needs: List[Dict[str, Any]],
        base_score: float
    ) -> DraftDirectionResult:
        """
        Needs-Based - aggressive need bonuses, no reach penalty.

        Philosophy: Aggressively fill roster holes, willing to reach for positional needs.

        Args:
            prospect: Prospect data dict
            team_needs: List of team needs with urgency scores
            base_score: Prospect's base overall rating

        Returns:
            DraftDirectionResult with needs-based evaluation
        """
        # Find need urgency
        position_urgency = 0
        for need in team_needs:
            if need["position"] == prospect["position"]:
                position_urgency = need.get("urgency_score", 0)
                break

        # Double the need boosts (more aggressive)
        need_boost = 0
        urgency_label = "NONE"
        if position_urgency >= 5:  # CRITICAL
            need_boost = 30  # 2x normal
            urgency_label = "CRITICAL"
        elif position_urgency >= 4:  # HIGH
            need_boost = 18
            urgency_label = "HIGH"
        elif position_urgency >= 3:  # MEDIUM
            need_boost = 10
            urgency_label = "MEDIUM"
        elif position_urgency >= 2:  # LOW
            need_boost = 5
            urgency_label = "LOW"

        # NO reach penalty - willing to reach for needs
        adjusted_score = base_score + need_boost

        return DraftDirectionResult(
            prospect_id=prospect["player_id"],
            prospect_name=prospect["name"],
            original_score=base_score,
            adjusted_score=adjusted_score,
            strategy_bonus=need_boost,
            position_bonus=0,
            watchlist_bonus=0,
            reach_penalty=0,
            reason=f"Needs-Based: {urgency_label} need (+{need_boost}), willing to reach"
        )

    def _evaluate_position_focus(
        self,
        prospect: Dict[str, Any],
        team_needs: List[Dict[str, Any]],
        priority_positions: List[str],
        base_score: float
    ) -> DraftDirectionResult:
        """
        Position Focus - only consider priority positions.

        Philosophy: Only consider specific positions, exclude everything else.
        Higher priority = larger bonuses (1st: +25, 2nd: +20, ..., 5th: +5)

        Args:
            prospect: Prospect data dict
            team_needs: List of team needs with urgency scores
            priority_positions: List of 1-5 positions in priority order
            base_score: Prospect's base overall rating

        Returns:
            DraftDirectionResult with position focus evaluation
        """
        prospect_position = prospect["position"]

        # Exclude non-priority positions
        if prospect_position not in priority_positions:
            return DraftDirectionResult(
                prospect_id=prospect["player_id"],
                prospect_name=prospect["name"],
                original_score=base_score,
                adjusted_score=-100,  # Excluded
                strategy_bonus=0,
                position_bonus=0,
                watchlist_bonus=0,
                reach_penalty=0,
                reason=f"Position Focus: {prospect_position} not in priorities (excluded)"
            )

        # Calculate priority rank bonus (1st = +25, 2nd = +20, ..., 5th = +5)
        priority_rank = priority_positions.index(prospect_position) + 1
        position_bonus = (6 - priority_rank) * 5

        # Find need urgency
        position_urgency = 0
        for need in team_needs:
            if need["position"] == prospect_position:
                position_urgency = need.get("urgency_score", 0)
                break

        # Apply need boost (smaller than Needs-Based, but still significant)
        need_boost = 0
        urgency_label = "LOW"
        if position_urgency >= 5:  # CRITICAL
            need_boost = 20
            urgency_label = "CRITICAL"
        elif position_urgency >= 4:  # HIGH
            need_boost = 12
            urgency_label = "HIGH"
        elif position_urgency >= 3:  # MEDIUM
            need_boost = 6
            urgency_label = "MEDIUM"

        adjusted_score = base_score + position_bonus + need_boost

        return DraftDirectionResult(
            prospect_id=prospect["player_id"],
            prospect_name=prospect["name"],
            original_score=base_score,
            adjusted_score=adjusted_score,
            strategy_bonus=need_boost,
            position_bonus=position_bonus,
            watchlist_bonus=0,
            reach_penalty=0,
            reason=f"Position Focus: #{priority_rank} priority (+{position_bonus}), {urgency_label} need (+{need_boost})"
        )

    # ========================================================================
    # SIMULATION METHODS
    # ========================================================================

    def sim_to_user_pick(
        self,
        user_team_id: int,
        draft_direction: Optional[DraftDirection] = None
    ) -> List[Dict[str, Any]]:
        """
        Simulate AI picks until it's the user's turn.

        Args:
            user_team_id: User's team ID
            draft_direction: Strategy for user's team (AI teams use default)

        Returns:
            List of picks made
        """
        picks_made = []

        while True:
            current_pick = self.get_current_pick()
            if current_pick is None:
                break  # Draft complete

            # Stop if it's user's pick
            if current_pick["current_team_id"] == user_team_id:
                break

            # AI pick - only use direction if it's the user's team (shouldn't happen here but safety check)
            direction = draft_direction if current_pick["current_team_id"] == user_team_id else None

            result = self.process_ai_pick(
                team_id=current_pick["current_team_id"],
                pick_info=current_pick,
                draft_direction=direction
            )

            if result["success"]:
                picks_made.append(result)
            else:
                self._logger.error(f"AI pick failed: {result.get('error')}")
                break

        return picks_made

    def auto_complete_draft(self, user_team_id: int) -> List[Dict[str, Any]]:
        """
        Auto-complete the entire remaining draft.

        For user's team, uses best available selection.
        For AI teams, uses needs-based selection.

        Args:
            user_team_id: User's team ID

        Returns:
            List of all picks made
        """
        picks_made = []

        while True:
            current_pick = self.get_current_pick()
            if current_pick is None:
                break  # Draft complete

            team_id = current_pick["current_team_id"]

            # All teams use AI pick logic in auto-complete mode
            result = self.process_ai_pick(
                team_id=team_id,
                pick_info=current_pick
            )

            if result["success"]:
                picks_made.append(result)
            else:
                self._logger.error(f"Pick {current_pick['overall_pick']} failed: {result.get('error')}")
                break

        return picks_made

    # ========================================================================
    # PROGRESS TRACKING
    # ========================================================================

    def get_draft_progress(self) -> Dict[str, Any]:
        """Get current draft progress and status."""
        api = self._get_draft_order_api()
        all_picks = api.get_draft_order(self._dynasty_id, self._season)

        if not all_picks:
            return {
                "draft_year": self._season,
                "total_picks": 0,
                "picks_made": 0,
                "picks_remaining": 0,
                "current_round": 0,
                "current_pick_in_round": 0,
                "is_complete": True,
            }

        picks_made = sum(1 for p in all_picks if p.is_executed)
        picks_remaining = len(all_picks) - picks_made

        current_pick = self.get_current_pick()
        current_round = current_pick["round_number"] if current_pick else 7
        current_in_round = current_pick["pick_in_round"] if current_pick else 32

        return {
            "draft_year": self._season,
            "total_picks": len(all_picks),
            "picks_made": picks_made,
            "picks_remaining": picks_remaining,
            "current_round": current_round,
            "current_pick_in_round": current_in_round,
            "is_complete": picks_remaining == 0,
        }

    def is_draft_complete(self) -> bool:
        """Check if all draft picks have been executed."""
        return self.get_draft_progress()["is_complete"]

    def get_draft_history(
        self,
        round_filter: Optional[int] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get draft picks made with full player/team info.

        Args:
            round_filter: Optional round to filter (1-7), None for all rounds
            limit: Maximum picks to return

        Returns:
            List of pick dicts with team_name, player_name, position, overall
        """
        api = self._get_draft_order_api()
        all_picks = api.get_draft_order(self._dynasty_id, self._season)

        if not all_picks:
            return []

        # Get executed picks
        executed = [p for p in all_picks if p.is_executed]

        # Apply round filter if specified
        if round_filter is not None:
            executed = [p for p in executed if p.round_number == round_filter]

        # Sort by overall pick (descending for most recent first)
        executed.sort(key=lambda p: p.overall_pick, reverse=True)

        # Load team data
        from team_management.teams.team_loader import TeamDataLoader
        team_loader = TeamDataLoader()

        # Build history with enriched player info
        history = []

        for pick in executed[:limit]:
            # Get team name
            team = team_loader.get_team_by_id(pick.current_team_id)
            team_name = team.full_name if team else f"Team {pick.current_team_id}"

            # Get player info from players table
            player_info = self._get_player_info(pick.player_id) if pick.player_id else {}

            history.append({
                "round": pick.round_number,
                "pick": pick.pick_in_round,
                "overall_pick": pick.overall_pick,
                "team_id": pick.current_team_id,
                "team_name": team_name,
                "player_id": pick.player_id,
                "player_name": player_info.get("name", ""),
                "position": player_info.get("position", ""),
                "overall": player_info.get("overall", 0),
            })

        return history

    def _get_player_info(self, player_id: int) -> Dict[str, Any]:
        """
        Look up player name, position, and overall from players table.

        Args:
            player_id: Player ID to look up

        Returns:
            Dict with name, position, overall (empty if not found)
        """
        conn = sqlite3.connect(self._db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT first_name, last_name, positions, attributes
            FROM players
            WHERE dynasty_id = ? AND player_id = ?
        """, (self._dynasty_id, player_id))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return {}

        first_name, last_name, positions_json, attributes_json = row

        # Parse JSON fields
        positions = json.loads(positions_json) if positions_json else []
        attributes = json.loads(attributes_json) if attributes_json else {}

        return {
            "name": f"{first_name} {last_name}".strip(),
            "position": positions[0] if positions else "",
            "overall": attributes.get("overall", 0),
        }

    # ========================================================================
    # LAZY-LOADED HELPERS
    # ========================================================================

    def _get_draft_class_api(self):
        """Lazy-load DraftClassAPI."""
        if self._draft_class_api is None:
            from database.draft_class_api import DraftClassAPI
            self._draft_class_api = DraftClassAPI(self._db_path)
        return self._draft_class_api

    def _get_draft_order_api(self):
        """Lazy-load DraftOrderDatabaseAPI."""
        if self._draft_order_api is None:
            from database.draft_order_database_api import DraftOrderDatabaseAPI
            self._draft_order_api = DraftOrderDatabaseAPI(self._db_path)
        return self._draft_order_api

    def _get_needs_analyzer(self):
        """Lazy-load TeamNeedsAnalyzer."""
        if self._needs_analyzer is None:
            from offseason.team_needs_analyzer import TeamNeedsAnalyzer
            self._needs_analyzer = TeamNeedsAnalyzer(self._db_path, self._dynasty_id)
        return self._needs_analyzer