"""
Draft Service for Game Cycle.

Handles draft operations during the offseason draft stage.
Wraps existing DraftManager and DraftClassAPI for game cycle integration.
"""

from typing import Dict, List, Any, Optional
import json
import logging
import sqlite3


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
        Generate simple draft order when standings unavailable.

        Uses team_id = pick_in_round as a simple fallback.
        This is used for edge cases like first year when skipping to draft.

        Returns:
            Dict with generation result.
        """
        api = self._get_draft_order_api()

        try:
            from database.draft_order_database_api import DraftPick

            picks = []
            for round_num in range(1, 8):
                for pick_in_round in range(1, 33):
                    overall_pick = (round_num - 1) * 32 + pick_in_round
                    # Simple ordering: team_id = pick_in_round
                    team_id = pick_in_round

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

            self._logger.info(f"Generated fallback draft order: {len(picks)} picks")
            return {
                "exists": False,
                "generated": True,
                "total_picks": len(picks),
            }

        except Exception as e:
            self._logger.error(f"Fallback draft order generation failed: {e}")
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
        pick_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process an AI team's draft pick using needs-based selection.

        Uses simple needs-based evaluation:
        - Base value = prospect overall rating
        - Need boost = +15 (CRITICAL), +8 (HIGH), +3 (MEDIUM)

        Args:
            team_id: Team making the pick
            pick_info: Pick info dict

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

        # Evaluate each prospect
        best_prospect = None
        best_score = -1

        for prospect in prospects:
            score = self._evaluate_prospect(
                prospect=prospect,
                team_needs=team_needs,
                pick_position=pick_info["overall_pick"]
            )
            if score > best_score:
                best_score = score
                best_prospect = prospect

        if best_prospect is None:
            return {"success": False, "error": "Could not evaluate prospects"}

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
    # SIMULATION METHODS
    # ========================================================================

    def sim_to_user_pick(self, user_team_id: int) -> List[Dict[str, Any]]:
        """
        Simulate AI picks until it's the user's turn.

        Args:
            user_team_id: User's team ID

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

            # AI pick
            result = self.process_ai_pick(
                team_id=current_pick["current_team_id"],
                pick_info=current_pick
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