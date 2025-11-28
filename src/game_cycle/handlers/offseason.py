"""
Offseason Handler - Executes offseason phases.

Handles re-signing, free agency, draft, roster cuts, training camp, preseason.
Madden-style simplified offseason flow.
"""

from typing import Any, Dict, List

from ..stage_definitions import Stage, StageType


class OffseasonHandler:
    """
    Handler for offseason stages (Madden-style).

    Each offseason stage has distinct logic:
    - Re-signing: Re-sign your own expiring players
    - Free Agency: Sign available free agents
    - Draft: Run the NFL Draft (7 rounds)
    - Roster Cuts: Cut roster from 90 to 53
    - Training Camp: Finalize depth charts
    - Preseason: Optional exhibition games
    """

    def __init__(self, database_path: str):
        """
        Initialize the handler.

        Args:
            database_path: Path to SQLite database
        """
        self._database_path = database_path

    def execute(self, stage: Stage, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the offseason stage.

        Args:
            stage: The current offseason stage
            context: Execution context with dynasty_id, etc.

        Returns:
            Dictionary with events_processed, transactions, etc.
        """
        # Dispatch to stage-specific handler
        handlers = {
            StageType.OFFSEASON_FRANCHISE_TAG: self._execute_franchise_tag,
            StageType.OFFSEASON_RESIGNING: self._execute_resigning,
            StageType.OFFSEASON_FREE_AGENCY: self._execute_free_agency,
            StageType.OFFSEASON_DRAFT: self._execute_draft,
            StageType.OFFSEASON_ROSTER_CUTS: self._execute_roster_cuts,
            StageType.OFFSEASON_WAIVER_WIRE: self._execute_waiver_wire,
            StageType.OFFSEASON_TRAINING_CAMP: self._execute_training_camp,
            StageType.OFFSEASON_PRESEASON: self._execute_preseason,
        }

        handler = handlers.get(stage.stage_type)
        if handler:
            return handler(stage, context)

        return {
            "games_played": [],
            "events_processed": [],
        }

    def can_advance(self, stage: Stage, context: Dict[str, Any]) -> bool:
        """
        Check if the offseason stage is complete.

        Args:
            stage: The current offseason stage
            context: Execution context

        Returns:
            True if stage is complete
        """
        # Check draft completion
        if stage.stage_type == StageType.OFFSEASON_DRAFT:
            try:
                from ..services.draft_service import DraftService

                dynasty_id = context.get("dynasty_id")
                season = context.get("season", 2025)
                db_path = context.get("db_path", self._database_path)

                draft_service = DraftService(db_path, dynasty_id, season)
                return draft_service.is_draft_complete()
            except Exception:
                # If error, allow advancement
                return True

        # For other stages, return True (allows progression)
        return True

    def requires_interaction(self, stage: Stage) -> bool:
        """
        Check if a stage requires user interaction.

        Args:
            stage: The offseason stage

        Returns:
            True if user interaction needed
        """
        interactive_stages = {
            StageType.OFFSEASON_FRANCHISE_TAG,  # User can apply franchise tag
            StageType.OFFSEASON_RESIGNING,    # User decides who to re-sign
            StageType.OFFSEASON_FREE_AGENCY,  # User can sign free agents
            StageType.OFFSEASON_DRAFT,        # User makes draft picks
            StageType.OFFSEASON_ROSTER_CUTS,  # User decides who to cut
            StageType.OFFSEASON_WAIVER_WIRE,  # User can submit waiver claims
        }
        return stage.stage_type in interactive_stages

    def get_stage_preview(
        self,
        stage: Stage,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Get preview data for the offseason stage (for UI display).

        Args:
            stage: The current offseason stage
            context: Execution context with dynasty_id, user_team_id, etc.

        Returns:
            Dictionary with stage preview data
        """
        stage_type = stage.stage_type
        user_team_id = context.get("user_team_id", 1)

        if stage_type == StageType.OFFSEASON_FRANCHISE_TAG:
            return self._get_franchise_tag_preview(context, user_team_id)
        elif stage_type == StageType.OFFSEASON_RESIGNING:
            preview = {
                "stage_name": "Re-signing Period",
                "description": "Re-sign your team's expiring contract players before they hit free agency.",
                "expiring_players": self._get_expiring_contracts(context, user_team_id),
                "is_interactive": True,
            }
            # Add cap data for UI display
            preview["cap_data"] = self._get_cap_data(context, user_team_id)
            return preview
        elif stage_type == StageType.OFFSEASON_FREE_AGENCY:
            preview = {
                "stage_name": "Free Agency",
                "description": "Sign available free agents to fill roster needs.",
                "free_agents": self._get_free_agents(context),
                "is_interactive": True,
            }
            # Add cap data for UI display
            preview["cap_data"] = self._get_cap_data(context, user_team_id)
            return preview
        elif stage_type == StageType.OFFSEASON_DRAFT:
            return self._get_draft_preview(context, user_team_id)
        elif stage_type == StageType.OFFSEASON_ROSTER_CUTS:
            return self._get_roster_cuts_preview(context, user_team_id)
        elif stage_type == StageType.OFFSEASON_WAIVER_WIRE:
            return self._get_waiver_wire_preview(context, user_team_id)
        elif stage_type == StageType.OFFSEASON_TRAINING_CAMP:
            # Training camp auto-executes on entry (non-interactive)
            return self._execute_and_preview_training_camp(context, user_team_id)
        elif stage_type == StageType.OFFSEASON_PRESEASON:
            return {
                "stage_name": "Preseason",
                "description": "Complete preseason preparations and move to the regular season.",
                "is_interactive": False,
            }
        else:
            return {
                "stage_name": stage.display_name,
                "description": "Offseason stage",
                "is_interactive": False,
            }

    def _get_cap_data(
        self,
        context: Dict[str, Any],
        team_id: int
    ) -> Dict[str, Any]:
        """
        Get salary cap summary for UI display.

        Args:
            context: Execution context with database APIs
            team_id: Team ID to get cap data for

        Returns:
            Dict with salary_cap_limit, total_spending, available_space,
            dead_money, is_compliant, carryover
        """
        try:
            from ..services.cap_helper import CapHelper

            dynasty_id = context.get("dynasty_id")
            season = context.get("season", 2025)
            db_path = context.get("db_path", self._database_path)

            # During offseason, cap calculations are for NEXT league year
            # (contracts signed during offseason start the following season)
            cap_helper = CapHelper(db_path, dynasty_id, season + 1)
            return cap_helper.get_cap_summary(team_id)

        except Exception as e:
            import traceback
            print(f"[OffseasonHandler] Error getting cap data: {e}")
            traceback.print_exc()
            # Return safe defaults on error
            return {
                "salary_cap_limit": 255_400_000,
                "total_spending": 0,
                "available_space": 255_400_000,
                "dead_money": 0,
                "is_compliant": True,
                "carryover": 0
            }

    def _get_expiring_contracts(
        self,
        context: Dict[str, Any],
        team_id: int
    ) -> List[Dict[str, Any]]:
        """
        Get list of expiring contracts for a team.

        Args:
            context: Execution context with database APIs
            team_id: Team ID to get expiring contracts for

        Returns:
            List of player dictionaries with contract info
        """
        try:
            import json
            from salary_cap.cap_database_api import CapDatabaseAPI
            from database.player_roster_api import PlayerRosterAPI
            from team_management.teams.team_loader import TeamDataLoader

            dynasty_id = context.get("dynasty_id")
            season = context.get("season", 2025)
            db_path = context.get("db_path", self._database_path)

            cap_api = CapDatabaseAPI(db_path)
            roster_api = PlayerRosterAPI(db_path)
            team_loader = TeamDataLoader()

            # Get all active contracts for this team
            contracts = cap_api.get_team_contracts(
                team_id=team_id,
                dynasty_id=dynasty_id,
                season=season,
                active_only=True
            )

            expiring_players = []

            for contract in contracts:
                player_id = contract.get("player_id")
                years_remaining = contract.get("end_year", season) - season + 1

                # Contract expires if years_remaining <= 1
                if years_remaining <= 1:
                    # Get player info - FIX: dynasty_id FIRST, player_id SECOND
                    player_info = roster_api.get_player_by_id(dynasty_id, player_id)

                    if player_info:
                        # Extract position - try direct key first (matches ResigningService)
                        # then fallback to positions array for compatibility
                        position = player_info.get("position", "")
                        if not position:
                            positions = player_info.get("positions", [])
                            if isinstance(positions, str):
                                positions = json.loads(positions)
                            position = positions[0] if positions else ""

                        # Extract overall - use same key as ResigningService
                        # Try "overall_rating" first (ResigningService), then "overall" in attributes
                        overall = player_info.get("overall_rating", 0)
                        if not overall:
                            attributes = player_info.get("attributes", {})
                            if isinstance(attributes, str):
                                attributes = json.loads(attributes)
                            overall = attributes.get("overall", 70)

                        # Get age - use direct "age" key (matches ResigningService)
                        # Fallback to birthdate calculation if not present
                        age = player_info.get("age", 0)
                        if not age:
                            birthdate = player_info.get("birthdate")
                            if birthdate:
                                try:
                                    birth_year = int(birthdate.split("-")[0])
                                    age = season - birth_year
                                except (ValueError, IndexError):
                                    age = 25  # Default fallback

                        # Calculate AAV from contract total_value
                        total_value = contract.get("total_value", 0)
                        contract_years = contract.get("contract_years", 1)
                        aav = total_value // contract_years if contract_years > 0 else 0

                        years_pro = player_info.get("years_pro", 3)

                        # Calculate estimated market AAV for new contract
                        # Uses same logic as ResigningService.resign_player()
                        from offseason.market_value_calculator import MarketValueCalculator
                        market_calc = MarketValueCalculator()
                        market = market_calc.calculate_player_value(
                            position=position,
                            overall=overall,
                            age=age,
                            years_pro=years_pro
                        )
                        estimated_aav = int(market["aav"] * 1_000_000)

                        # Calculate Year 1 cap hit (matches ResigningService contract structure)
                        # This is more accurate than AAV for cap projections because
                        # contracts use escalating salaries (Year 1 is lowest)
                        years = market["years"]
                        total_value_new = int(market["total_value"] * 1_000_000)
                        signing_bonus_new = int(market["signing_bonus"] * 1_000_000)

                        # Escalating salary structure (5% increase per year)
                        remaining = total_value_new - signing_bonus_new
                        total_weight = sum(1.0 + (j * 0.05) for j in range(years))
                        year1_base = int((remaining * 1.0) / total_weight) if total_weight > 0 else 0

                        # Signing bonus proration (max 5 years per NFL rules)
                        proration_years = min(years, 5)
                        bonus_proration = signing_bonus_new // proration_years if proration_years > 0 else 0

                        estimated_year1_cap_hit = year1_base + bonus_proration

                        expiring_players.append({
                            "player_id": player_id,
                            "name": f"{player_info.get('first_name', '')} {player_info.get('last_name', '')}".strip(),
                            "position": position,
                            "age": age,
                            "overall": overall,
                            "salary": aav,
                            "estimated_aav": estimated_aav,  # Market value for new contract
                            "estimated_year1_cap_hit": estimated_year1_cap_hit,  # Actual Year 1 cap impact
                            "years_remaining": years_remaining,
                            "contract_id": contract.get("contract_id"),
                            "years_pro": years_pro,
                        })

            # Sort by overall rating (highest first)
            expiring_players.sort(key=lambda x: x.get("overall", 0), reverse=True)

            return expiring_players

        except Exception as e:
            import traceback
            print(f"[OffseasonHandler] Error getting expiring contracts: {e}")
            traceback.print_exc()
            # Return empty list on error - UI will show "No expiring contracts"
            return []

    def _get_free_agents(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Get list of available free agents.

        Args:
            context: Execution context with database APIs

        Returns:
            List of free agent dictionaries with contract estimates
        """
        try:
            from ..services.free_agency_service import FreeAgencyService

            dynasty_id = context.get("dynasty_id")
            season = context.get("season", 2025)
            db_path = context.get("db_path", self._database_path)

            service = FreeAgencyService(db_path, dynasty_id, season)
            return service.get_available_free_agents()

        except Exception as e:
            import traceback
            print(f"[OffseasonHandler] Error getting free agents: {e}")
            traceback.print_exc()
            return []

    def _get_draft_preview(
        self,
        context: Dict[str, Any],
        user_team_id: int
    ) -> Dict[str, Any]:
        """
        Get draft preview data for UI display.

        Args:
            context: Execution context
            user_team_id: User's team ID

        Returns:
            Dictionary with draft preview data including prospects, current pick, etc.
        """
        try:
            from ..services.draft_service import DraftService
            from team_management.teams.team_loader import TeamDataLoader

            dynasty_id = context.get("dynasty_id")
            season = context.get("season", 2025)
            db_path = context.get("db_path", self._database_path)

            draft_service = DraftService(db_path, dynasty_id, season)
            team_loader = TeamDataLoader()

            # Ensure draft class exists
            draft_service.ensure_draft_class_exists()
            draft_service.ensure_draft_order_exists()

            # Get available prospects
            prospects = draft_service.get_available_prospects(limit=100)

            # Get current pick
            current_pick = draft_service.get_current_pick()
            if current_pick:
                team = team_loader.get_team_by_id(current_pick.get("team_id"))
                current_pick["team_name"] = team.full_name if team else f"Team {current_pick.get('team_id')}"

            # Get draft progress
            progress = draft_service.get_draft_progress()

            # Get draft history
            draft_history = draft_service.get_draft_history()

            preview = {
                "stage_name": "NFL Draft",
                "description": "Select players from the draft class to build your team's future.",
                "prospects": prospects,
                "current_pick": current_pick,
                "draft_progress": progress,
                "draft_history": draft_history,
                "draft_complete": progress.get("is_complete", False),
                "is_interactive": True,
            }
            # Add cap data for UI display
            preview["cap_data"] = self._get_cap_data(context, user_team_id)
            return preview

        except Exception as e:
            import traceback
            print(f"[OffseasonHandler] Error getting draft preview: {e}")
            traceback.print_exc()
            return {
                "stage_name": "NFL Draft",
                "description": "Select players from the draft class to build your team's future.",
                "prospects": [],
                "current_pick": None,
                "draft_progress": {"picks_made": 0, "total_picks": 224},
                "draft_history": [],
                "draft_complete": False,
                "is_interactive": True,
            }

    def _execute_resigning(
        self,
        stage: Stage,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute re-signing phase for all teams.

        Processes:
        1. User team decisions (from context["user_decisions"])
        2. AI team re-signing decisions
        """
        from ..services.resigning_service import ResigningService

        dynasty_id = context.get("dynasty_id")
        season = context.get("season", 2025)
        user_team_id = context.get("user_team_id", 1)
        user_decisions = context.get("user_decisions", {})  # {player_id: "resign"|"release"}
        db_path = context.get("db_path", self._database_path)

        service = ResigningService(db_path, dynasty_id, season)

        events = []
        resigned_players = []
        released_players = []

        # 1. Process USER team decisions (from UI)
        for player_id_str, decision in user_decisions.items():
            player_id = int(player_id_str) if isinstance(player_id_str, str) else player_id_str

            if decision == "resign":
                result = service.resign_player(player_id, user_team_id)
                if result["success"]:
                    resigned_players.append({
                        "player_id": player_id,
                        "player_name": result["player_name"],
                        "team_id": user_team_id,
                        "contract_details": result.get("contract_details", {}),
                    })
                    events.append(f"Re-signed {result['player_name']}")
            else:  # "release"
                result = service.release_player(player_id, user_team_id)
                if result["success"]:
                    released_players.append({
                        "player_id": player_id,
                        "player_name": result["player_name"],
                        "team_id": user_team_id,
                    })
                    events.append(f"Released {result['player_name']} to free agency")

        # 2. Process AI team decisions
        ai_result = service.process_ai_resignings(user_team_id)
        resigned_players.extend(ai_result.get("resigned", []))
        released_players.extend(ai_result.get("released", []))
        events.extend(ai_result.get("events", []))

        events.append(f"Re-signing period completed: {len(resigned_players)} re-signed, {len(released_players)} released")

        return {
            "games_played": [],
            "events_processed": events,
            "resigned": resigned_players,
            "became_free_agents": released_players,
        }

    def _execute_free_agency(
        self,
        stage: Stage,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute free agency phase for all teams."""
        from ..services.free_agency_service import FreeAgencyService

        dynasty_id = context.get("dynasty_id")
        season = context.get("season", 2025)
        user_team_id = context.get("user_team_id", 1)
        fa_decisions = context.get("fa_decisions", {})
        db_path = context.get("db_path", self._database_path)

        service = FreeAgencyService(db_path, dynasty_id, season)

        # Process user and AI signings
        user_signings = self._process_user_fa_signings(service, fa_decisions, user_team_id)
        ai_result = service.process_ai_signings(user_team_id)

        # Build event list
        events = []
        for signing in user_signings:
            events.append(f"Signed FA {signing['player_name']}")
        events.extend(ai_result.get("events", []))
        events.append(
            f"Free Agency completed: {len(user_signings)} user signings, "
            f"{len(ai_result.get('signings', []))} AI signings"
        )

        return {
            "games_played": [],
            "events_processed": events,
            "user_signings": user_signings,
            "ai_signings": ai_result.get("signings", []),
        }

    def _process_user_fa_signings(
        self,
        service,
        fa_decisions: Dict[int, str],
        user_team_id: int
    ) -> List[Dict[str, Any]]:
        """
        Process user's free agent signing decisions.

        Args:
            service: FreeAgencyService instance
            fa_decisions: Dict of {player_id: "sign"}
            user_team_id: User's team ID

        Returns:
            List of successful signing dictionaries
        """
        user_signings = []

        for player_id_str, decision in fa_decisions.items():
            player_id = int(player_id_str) if isinstance(player_id_str, str) else player_id_str

            if decision == "sign":
                result = service.sign_free_agent(player_id, user_team_id)
                if result["success"]:
                    user_signings.append({
                        "player_id": player_id,
                        "player_name": result["player_name"],
                        "team_id": user_team_id,
                        "contract_details": result.get("contract_details", {}),
                    })

        return user_signings

    def _execute_draft(
        self,
        stage: Stage,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute NFL Draft (7 rounds, 224 picks).

        Supports two modes:
        1. Interactive: User makes picks via UI, AI fills in between
        2. Auto-complete: Entire draft simulated automatically

        Context keys:
            - draft_decisions: Dict[int, int] = {overall_pick: prospect_id}
            - auto_complete: bool = True to auto-sim entire draft
            - sim_to_user_pick: bool = True to sim AI picks until user's turn
        """
        from ..services.draft_service import DraftService

        dynasty_id = context.get("dynasty_id")
        season = context.get("season", 2025)
        user_team_id = context.get("user_team_id", 1)
        db_path = context.get("db_path", self._database_path)
        draft_decisions = context.get("draft_decisions", {})  # {pick_num: prospect_id}
        auto_complete = context.get("auto_complete", False)
        sim_to_user_pick = context.get("sim_to_user_pick", False)

        events = []
        picks = []

        try:
            draft_service = DraftService(db_path, dynasty_id, season)

            # Safety: Ensure prerequisites exist
            draft_class_result = draft_service.ensure_draft_class_exists()
            if draft_class_result.get("error"):
                events.append(f"Draft class error: {draft_class_result['error']}")
                return {
                    "games_played": [],
                    "events_processed": events,
                    "picks": [],
                    "draft_complete": False,
                }

            draft_order_result = draft_service.ensure_draft_order_exists()
            if draft_order_result.get("error"):
                events.append(f"Draft order error: {draft_order_result['error']}")
                return {
                    "games_played": [],
                    "events_processed": events,
                    "picks": [],
                    "draft_complete": False,
                }

            if auto_complete:
                # Auto-complete entire draft
                results = draft_service.auto_complete_draft(user_team_id)
                picks = [r for r in results if r.get("success")]
                events.append(f"NFL Draft completed ({len(picks)} picks)")
            else:
                # Interactive mode: process user decision if provided
                current_pick = draft_service.get_current_pick()

                if current_pick:
                    overall_pick = current_pick["overall_pick"]

                    # Execute user pick if decision provided
                    if overall_pick in draft_decisions:
                        prospect_id = draft_decisions[overall_pick]
                        result = draft_service.make_draft_pick(prospect_id, user_team_id, current_pick)
                        if result.get("success"):
                            picks.append(result)
                            events.append(
                                f"Pick {overall_pick}: You selected {result['player_name']} "
                                f"({result['position']}, {result['overall']} OVR)"
                            )

                    # Sim AI picks to user's next turn
                    ai_results = draft_service.sim_to_user_pick(user_team_id)
                    for r in ai_results:
                        if r.get("success"):
                            picks.append(r)
                            events.append(
                                f"Pick {r['overall_pick']}: Team {r['team_id']} selects "
                                f"{r['player_name']} ({r['position']})"
                            )

            progress = draft_service.get_draft_progress()
            is_complete = progress.get("is_complete", False)

            if is_complete:
                events.append("NFL Draft completed - all 224 picks executed")

            return {
                "games_played": [],
                "events_processed": events,
                "picks": picks,
                "draft_complete": is_complete,
                "draft_progress": progress,
            }

        except Exception as e:
            import traceback
            print(f"[OffseasonHandler] Draft execution error: {e}")
            traceback.print_exc()
            events.append(f"Draft error: {str(e)}")
            return {
                "games_played": [],
                "events_processed": events,
                "picks": [],
                "draft_complete": False,
            }

    def _get_roster_cuts_preview(
        self,
        context: Dict[str, Any],
        team_id: int
    ) -> Dict[str, Any]:
        """
        Get roster cuts preview data for UI display.

        Args:
            context: Execution context
            team_id: User's team ID

        Returns:
            Dictionary with roster data and cut suggestions
        """
        try:
            from ..services.roster_cuts_service import RosterCutsService

            dynasty_id = context.get("dynasty_id")
            season = context.get("season", 2025)
            db_path = context.get("db_path", self._database_path)

            cuts_service = RosterCutsService(db_path, dynasty_id, season)

            roster = cuts_service.get_team_roster_for_cuts(team_id)
            roster_count = len(roster)
            cuts_needed = cuts_service.get_cuts_needed(team_id)
            suggestions = cuts_service.get_ai_cut_suggestions(team_id, cuts_needed)

            # Get suggestion player IDs for UI highlighting
            suggested_ids = [p["player_id"] for p in suggestions]

            preview = {
                "stage_name": "Roster Cuts",
                "description": f"Cut your roster from {roster_count} players down to the 53-man limit.",
                "roster": roster,
                "roster_count": roster_count,
                "cuts_needed": cuts_needed,
                "cut_suggestions": suggested_ids,
                "is_interactive": True,
            }
            # Add cap data for UI display
            preview["cap_data"] = self._get_cap_data(context, team_id)
            return preview

        except Exception as e:
            import traceback
            print(f"[OffseasonHandler] Error getting roster cuts preview: {e}")
            traceback.print_exc()
            return {
                "stage_name": "Roster Cuts",
                "description": "Cut your roster from 90 players down to the 53-man limit.",
                "roster": [],
                "roster_count": 0,
                "cuts_needed": 0,
                "cut_suggestions": [],
                "is_interactive": True,
            }

    def _get_waiver_wire_preview(
        self,
        context: Dict[str, Any],
        team_id: int
    ) -> Dict[str, Any]:
        """
        Get waiver wire preview data for UI display.

        Args:
            context: Execution context
            team_id: User's team ID

        Returns:
            Dictionary with waiver players and user's priority
        """
        try:
            from ..services.waiver_service import WaiverService

            dynasty_id = context.get("dynasty_id")
            season = context.get("season", 2025)
            db_path = context.get("db_path", self._database_path)

            waiver_service = WaiverService(db_path, dynasty_id, season)

            waiver_players = waiver_service.get_available_players()
            user_priority = waiver_service.get_team_priority(team_id)
            user_claims = waiver_service.get_team_claims(team_id)
            claim_player_ids = [c["player_id"] for c in user_claims]

            preview = {
                "stage_name": "Waiver Wire",
                "description": f"Submit waiver claims for cut players. Your priority: #{user_priority}",
                "waiver_players": waiver_players,
                "user_priority": user_priority,
                "user_claims": claim_player_ids,
                "total_on_waivers": len(waiver_players),
                "is_interactive": True,
            }
            # Add cap data for UI display
            preview["cap_data"] = self._get_cap_data(context, team_id)
            return preview

        except Exception as e:
            import traceback
            print(f"[OffseasonHandler] Error getting waiver wire preview: {e}")
            traceback.print_exc()
            return {
                "stage_name": "Waiver Wire",
                "description": "Submit waiver claims for cut players.",
                "waiver_players": [],
                "user_priority": 16,
                "user_claims": [],
                "total_on_waivers": 0,
                "is_interactive": True,
            }

    def _get_training_camp_preview(
        self,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Get training camp preview data for UI display.

        Args:
            context: Execution context

        Returns:
            Dictionary with training camp preview info
        """
        dynasty_id = context.get("dynasty_id")
        db_path = context.get("db_path", self._database_path)

        # Get count of players to process
        try:
            import sqlite3
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM players WHERE dynasty_id = ?",
                (dynasty_id,)
            )
            player_count = cursor.fetchone()[0]
            conn.close()
        except Exception:
            player_count = 1700  # Approximate

        return {
            "stage_name": "Training Camp",
            "description": (
                f"Training camp will process {player_count} players with age-weighted development. "
                f"Young players (under 26) are more likely to improve, while veterans (31+) may see regression. "
                f"Depth charts will be regenerated for all teams."
            ),
            "player_count": player_count,
            "is_interactive": False,
        }

    def _execute_and_preview_training_camp(
        self,
        context: Dict[str, Any],
        user_team_id: int
    ) -> Dict[str, Any]:
        """
        Execute training camp and return preview with results.

        Training camp is non-interactive, so we process immediately
        when entering the stage and show results for review.

        Args:
            context: Execution context
            user_team_id: User's team ID for default filter

        Returns:
            Dictionary with training camp results for UI display
        """
        from ..services.training_camp_service import TrainingCampService

        dynasty_id = context.get("dynasty_id")
        season = context.get("season", 2025)
        db_path = context.get("db_path", self._database_path)

        try:
            service = TrainingCampService(db_path, dynasty_id, season)
            result = service.process_all_players()

            summary = result.get("summary", {})
            depth_summary = result.get("depth_chart_summary", {})

            return {
                "stage_name": "Training Camp - Complete",
                "description": (
                    f"Training camp processed {summary.get('total_players', 0)} players. "
                    f"{summary.get('improved_count', 0)} improved, "
                    f"{summary.get('declined_count', 0)} declined, "
                    f"{summary.get('unchanged_count', 0)} unchanged. "
                    f"Depth charts regenerated for {depth_summary.get('teams_updated', 0)}/32 teams."
                ),
                "training_camp_results": result,
                "user_team_id": user_team_id,
                "is_interactive": False,
            }

        except Exception as e:
            import traceback
            print(f"[OffseasonHandler] Training camp error: {e}")
            traceback.print_exc()
            return {
                "stage_name": "Training Camp",
                "description": f"Training camp error: {str(e)}",
                "training_camp_results": None,
                "user_team_id": user_team_id,
                "is_interactive": False,
            }

    def _execute_roster_cuts(
        self,
        stage: Stage,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute roster cuts (90 to 53) with waiver wire.

        Processes:
        1. User team cuts (from context["roster_cut_decisions"])
        2. AI team cuts for all 31 other teams
        3. Cut players added to waiver wire
        """
        from ..services.roster_cuts_service import RosterCutsService

        dynasty_id = context.get("dynasty_id")
        season = context.get("season", 2025)
        user_team_id = context.get("user_team_id", 1)
        user_cuts = context.get("roster_cut_decisions", [])  # List of player IDs or dicts with cut type
        db_path = context.get("db_path", self._database_path)

        events = []

        try:
            cuts_service = RosterCutsService(db_path, dynasty_id, season)

            user_cut_results = []
            total_dead_money = 0
            total_cap_savings = 0

            # 1. Process USER team cuts
            # Support both formats: list of IDs (legacy) or list of dicts with use_june_1
            for cut_item in user_cuts:
                # Handle both formats: int/str player_id or dict with player_id and use_june_1
                if isinstance(cut_item, dict):
                    player_id = cut_item.get("player_id")
                    use_june_1 = cut_item.get("use_june_1", False)
                else:
                    player_id = cut_item
                    use_june_1 = False

                if isinstance(player_id, str):
                    player_id = int(player_id)

                result = cuts_service.cut_player(
                    player_id, user_team_id, add_to_waivers=True, use_june_1=use_june_1
                )
                if result["success"]:
                    user_cut_results.append(result)
                    total_dead_money += result.get("dead_money", 0)
                    total_cap_savings += result.get("cap_savings", 0)

                    # Show cut type in event message
                    cut_type_str = " (June 1)" if use_june_1 else ""
                    next_yr_str = ""
                    if result.get("dead_money_next_year", 0) > 0:
                        next_yr_str = f", Next yr: ${result['dead_money_next_year']:,}"
                    events.append(
                        f"Cut {result['player_name']}{cut_type_str} (Dead $: ${result['dead_money']:,}{next_yr_str})"
                    )

            if user_cut_results:
                events.append(
                    f"Your roster cuts complete: {len(user_cut_results)} players, "
                    f"${total_cap_savings:,} cap savings, ${total_dead_money:,} dead money"
                )

            # 2. Process AI team cuts
            ai_result = cuts_service.process_ai_cuts(user_team_id)
            events.extend(ai_result.get("events", []))

            total_cuts = len(user_cut_results) + ai_result.get("total_cuts", 0)
            events.append(f"Roster cuts completed: {total_cuts} players waived league-wide")

            return {
                "games_played": [],
                "events_processed": events,
                "user_cuts": user_cut_results,
                "ai_cuts": ai_result.get("cuts", []),
                "total_cuts": total_cuts,
                "waiver_wire_ready": True,
            }

        except Exception as e:
            import traceback
            print(f"[OffseasonHandler] Roster cuts error: {e}")
            traceback.print_exc()
            events.append(f"Roster cuts error: {str(e)}")
            return {
                "games_played": [],
                "events_processed": events,
                "user_cuts": [],
                "ai_cuts": [],
                "total_cuts": 0,
            }

    def _execute_waiver_wire(
        self,
        stage: Stage,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute waiver wire claims processing.

        Processes:
        1. User's waiver claims (from context["waiver_claims"])
        2. AI teams submit claims
        3. Process all claims by priority
        4. Clear unclaimed players to free agency
        """
        from ..services.waiver_service import WaiverService

        dynasty_id = context.get("dynasty_id")
        season = context.get("season", 2025)
        user_team_id = context.get("user_team_id", 1)
        user_claims = context.get("waiver_claims", [])  # List of player IDs to claim
        db_path = context.get("db_path", self._database_path)

        events = []

        try:
            waiver_service = WaiverService(db_path, dynasty_id, season)

            # 1. Submit user's claims
            user_claims_submitted = []
            for player_id in user_claims:
                if isinstance(player_id, str):
                    player_id = int(player_id)

                result = waiver_service.submit_claim(user_team_id, player_id)
                if result["success"]:
                    user_claims_submitted.append(result)
                    events.append(f"Submitted waiver claim for player {player_id}")

            # 2. AI teams submit claims
            ai_claims_result = waiver_service.process_ai_claims(user_team_id)
            if ai_claims_result["total_claims"] > 0:
                events.append(f"AI teams submitted {ai_claims_result['total_claims']} waiver claims")

            # 3. Process all claims by priority
            process_result = waiver_service.process_all_claims()
            events.extend(process_result.get("events", []))

            # 4. Clear unclaimed to free agency
            clear_result = waiver_service.clear_unclaimed_to_free_agency()
            if clear_result["total_cleared"] > 0:
                events.append(clear_result["event"])

            events.append(
                f"Waiver wire complete: {process_result['total_awarded']} players claimed, "
                f"{clear_result['total_cleared']} cleared to free agency"
            )

            return {
                "games_played": [],
                "events_processed": events,
                "user_claims": user_claims_submitted,
                "claims_awarded": process_result.get("claims_awarded", []),
                "cleared_to_fa": clear_result.get("cleared_players", []),
            }

        except Exception as e:
            import traceback
            print(f"[OffseasonHandler] Waiver wire error: {e}")
            traceback.print_exc()
            events.append(f"Waiver wire error: {str(e)}")
            return {
                "games_played": [],
                "events_processed": events,
                "claims_awarded": [],
                "cleared_to_fa": [],
            }

    def _execute_training_camp(
        self,
        stage: Stage,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute training camp phase.

        Note: Training camp is now auto-executed during get_stage_preview()
        via _execute_and_preview_training_camp(). This method is a no-op
        that just returns success since processing was already done.

        The processing happens on stage entry so users can see results
        before clicking "Continue to Preseason".
        """
        # Training camp was already processed during preview
        # Just return success - no need to re-process
        return {
            "games_played": [],
            "events_processed": ["Training camp results reviewed - proceeding to preseason"],
        }

    def _get_franchise_tag_preview(
        self,
        context: Dict[str, Any],
        team_id: int
    ) -> Dict[str, Any]:
        """
        Get franchise tag preview data for UI display.

        Args:
            context: Execution context
            team_id: User's team ID

        Returns:
            Dictionary with taggable players and tag status
        """
        try:
            from ..services.franchise_tag_service import FranchiseTagService

            dynasty_id = context.get("dynasty_id")
            season = context.get("season", 2025)
            db_path = context.get("db_path", self._database_path)

            tag_service = FranchiseTagService(db_path, dynasty_id, season)

            # Get taggable players (expiring contracts)
            taggable_players = tag_service.get_taggable_players(team_id)

            # Check if team has already used tag
            tag_used = tag_service.has_team_used_tag(team_id)

            preview = {
                "stage_name": "Franchise Tag Window",
                "description": (
                    "Apply a franchise or transition tag to one expiring contract player. "
                    "Tagged players cannot hit free agency. Each team may use ONE tag per season. "
                    "Note: Tag salary counts against NEXT year's salary cap."
                ),
                "taggable_players": taggable_players,
                "tag_used": tag_used,
                "total_taggable": len(taggable_players),
                "is_interactive": True,
                "current_season": season,
                "next_season": season + 1,
            }
            # Add current season cap data for UI display
            preview["cap_data"] = self._get_cap_data(context, team_id)

            # Add PROJECTED next-year cap (where tag salary will count)
            from ..services.cap_helper import CapHelper
            next_cap_helper = CapHelper(db_path, dynasty_id, season + 1)
            preview["projected_cap_data"] = next_cap_helper.get_cap_summary(team_id)

            return preview

        except Exception as e:
            import traceback
            print(f"[OffseasonHandler] Error getting franchise tag preview: {e}")
            traceback.print_exc()
            return {
                "stage_name": "Franchise Tag Window",
                "description": "Apply a franchise or transition tag to one expiring contract player.",
                "taggable_players": [],
                "tag_used": False,
                "total_taggable": 0,
                "is_interactive": True,
            }

    def _execute_franchise_tag(
        self,
        stage: Stage,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute franchise tag phase for all teams.

        Processes:
        1. User team tag decision (from context["tag_decision"])
        2. AI team tag decisions for all 31 other teams

        Context keys:
            - tag_decision: {"player_id": int, "tag_type": "franchise"|"transition"} or None
        """
        from ..services.franchise_tag_service import FranchiseTagService

        dynasty_id = context.get("dynasty_id")
        season = context.get("season", 2025)
        user_team_id = context.get("user_team_id", 1)
        tag_decision = context.get("tag_decision")  # {"player_id": X, "tag_type": "franchise"|"transition"}
        db_path = context.get("db_path", self._database_path)

        events = []
        tags_applied = []

        try:
            tag_service = FranchiseTagService(db_path, dynasty_id, season)

            # 1. Process USER team tag decision
            if tag_decision and tag_decision.get("player_id"):
                player_id = tag_decision["player_id"]
                tag_type = tag_decision.get("tag_type", "franchise")

                if tag_type == "franchise":
                    result = tag_service.apply_franchise_tag(player_id, user_team_id)
                else:
                    result = tag_service.apply_transition_tag(player_id, user_team_id)

                if result["success"]:
                    tags_applied.append(result)
                    events.append(
                        f"Applied {result['tag_type']} tag to {result['player_name']} "
                        f"({result['position']}) - ${result['tag_salary']:,}"
                    )
                else:
                    events.append(f"Failed to apply tag: {result.get('error', 'Unknown error')}")

            # 2. Process AI team tag decisions
            ai_result = tag_service.process_ai_tags(user_team_id)
            tags_applied.extend(ai_result.get("tags_applied", []))
            events.extend(ai_result.get("events", []))

            total_tags = len(tags_applied)
            events.append(f"Franchise tag window closed: {total_tags} tags applied league-wide")

            return {
                "games_played": [],
                "events_processed": events,
                "tags_applied": tags_applied,
                "total_tags": total_tags,
            }

        except Exception as e:
            import traceback
            print(f"[OffseasonHandler] Franchise tag error: {e}")
            traceback.print_exc()
            events.append(f"Franchise tag error: {str(e)}")
            return {
                "games_played": [],
                "events_processed": events,
                "tags_applied": [],
                "total_tags": 0,
            }

    def _execute_preseason(
        self,
        stage: Stage,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute preseason - triggers season initialization pipeline.

        This runs the SeasonInitializationService which executes a series
        of steps to prepare for the new season (reset records, generate
        schedule, etc.). The pipeline is extendable for future features.
        """
        from ..services.season_init_service import SeasonInitializationService

        dynasty_id = context.get("dynasty_id")
        db_path = context.get("db_path", self._database_path)
        current_season = stage.season_year
        next_season = current_season + 1

        events = []
        events.append(f"Initializing Season {next_season}...")

        # Run initialization pipeline
        service = SeasonInitializationService(
            db_path=db_path,
            dynasty_id=dynasty_id,
            from_season=current_season,
            to_season=next_season
        )

        results = service.run_all()

        # Collect results for UI display
        for result in results:
            status_icon = "✓" if result.status.value == "completed" else "✗"
            events.append(f"{status_icon} {result.step_name}: {result.message}")

        events.append(f"Season {next_season} initialization complete!")

        return {
            "games_played": [],
            "events_processed": events,
            "initialization_results": [
                {"step": r.step_name, "status": r.status.value, "message": r.message}
                for r in results
            ],
        }