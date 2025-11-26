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

        if stage_type == StageType.OFFSEASON_RESIGNING:
            return {
                "stage_name": "Re-signing Period",
                "description": "Re-sign your team's expiring contract players before they hit free agency.",
                "expiring_players": self._get_expiring_contracts(context, user_team_id),
                "is_interactive": True,
            }
        elif stage_type == StageType.OFFSEASON_FREE_AGENCY:
            return {
                "stage_name": "Free Agency",
                "description": "Sign available free agents to fill roster needs.",
                "free_agents": self._get_free_agents(context),
                "is_interactive": True,
            }
        elif stage_type == StageType.OFFSEASON_DRAFT:
            return self._get_draft_preview(context, user_team_id)
        elif stage_type == StageType.OFFSEASON_ROSTER_CUTS:
            return self._get_roster_cuts_preview(context, user_team_id)
        elif stage_type == StageType.OFFSEASON_WAIVER_WIRE:
            return self._get_waiver_wire_preview(context, user_team_id)
        elif stage_type == StageType.OFFSEASON_TRAINING_CAMP:
            return {
                "stage_name": "Training Camp",
                "description": "Finalize your depth charts and prepare for the season.",
                "is_interactive": False,
            }
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
                        # Extract position from JSON array
                        positions = player_info.get("positions", [])
                        if isinstance(positions, str):
                            positions = json.loads(positions)
                        position = positions[0] if positions else ""

                        # Extract overall from JSON attributes
                        attributes = player_info.get("attributes", {})
                        if isinstance(attributes, str):
                            attributes = json.loads(attributes)
                        overall = attributes.get("overall", 0)

                        # Calculate age from birthdate if available
                        age = 0
                        birthdate = player_info.get("birthdate")
                        if birthdate:
                            try:
                                birth_year = int(birthdate.split("-")[0])
                                age = season - birth_year
                            except (ValueError, IndexError):
                                pass

                        # Calculate AAV from contract total_value
                        total_value = contract.get("total_value", 0)
                        contract_years = contract.get("contract_years", 1)
                        aav = total_value // contract_years if contract_years > 0 else 0

                        expiring_players.append({
                            "player_id": player_id,
                            "name": f"{player_info.get('first_name', '')} {player_info.get('last_name', '')}".strip(),
                            "position": position,
                            "age": age,
                            "overall": overall,
                            "salary": aav,
                            "years_remaining": years_remaining,
                            "contract_id": contract.get("contract_id"),
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

            return {
                "stage_name": "NFL Draft",
                "description": "Select players from the draft class to build your team's future.",
                "prospects": prospects,
                "current_pick": current_pick,
                "draft_progress": progress,
                "draft_history": draft_history,
                "draft_complete": progress.get("is_complete", False),
                "is_interactive": True,
            }

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

            return {
                "stage_name": "Roster Cuts",
                "description": f"Cut your roster from {roster_count} players down to the 53-man limit.",
                "roster": roster,
                "roster_count": roster_count,
                "cuts_needed": cuts_needed,
                "cut_suggestions": suggested_ids,
                "is_interactive": True,
            }

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

            return {
                "stage_name": "Waiver Wire",
                "description": f"Submit waiver claims for cut players. Your priority: #{user_priority}",
                "waiver_players": waiver_players,
                "user_priority": user_priority,
                "user_claims": claim_player_ids,
                "total_on_waivers": len(waiver_players),
                "is_interactive": True,
            }

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
        user_cuts = context.get("roster_cut_decisions", [])  # List of player IDs to cut
        db_path = context.get("db_path", self._database_path)

        events = []

        try:
            cuts_service = RosterCutsService(db_path, dynasty_id, season)

            user_cut_results = []
            total_dead_money = 0
            total_cap_savings = 0

            # 1. Process USER team cuts
            for player_id in user_cuts:
                if isinstance(player_id, str):
                    player_id = int(player_id)

                result = cuts_service.cut_player(player_id, user_team_id, add_to_waivers=True)
                if result["success"]:
                    user_cut_results.append(result)
                    total_dead_money += result.get("dead_money", 0)
                    total_cap_savings += result.get("cap_savings", 0)
                    events.append(
                        f"Cut {result['player_name']} (Dead $: ${result['dead_money']:,})"
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
        """Execute training camp phase."""
        events = []

        # TODO: Implement training camp
        # 1. Auto-generate depth charts based on ratings
        # 2. Optional: Small ratings adjustments
        # 3. Finalize rosters for season

        events.append("Training Camp completed")
        events.append("Depth charts finalized")

        return {
            "games_played": [],
            "events_processed": events,
        }

    def _execute_preseason(
        self,
        stage: Stage,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute preseason (optional exhibition games)."""
        events = []

        # TODO: Implement preseason
        # 1. Optional: Simulate 3 exhibition games
        # 2. Or skip entirely and advance to regular season
        # 3. No impact on standings

        events.append("Preseason completed")

        return {
            "games_played": [],  # TODO: Preseason game results
            "events_processed": events,
        }