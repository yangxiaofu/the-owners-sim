"""
Offseason Handler - Executes offseason phases.

Handles re-signing, free agency, draft, roster cuts, training camp, preseason.
Madden-style simplified offseason flow.
"""

import sqlite3
from typing import Any, Dict, List, Optional

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
            StageType.OFFSEASON_HONORS: self._execute_honors,
            StageType.OFFSEASON_OWNER: self._execute_owner,
            StageType.OFFSEASON_FRANCHISE_TAG: self._execute_franchise_tag,
            StageType.OFFSEASON_RESIGNING: self._execute_resigning,
            StageType.OFFSEASON_FREE_AGENCY: self._execute_free_agency,
            StageType.OFFSEASON_TRADING: self._execute_trading,
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

        # Check roster cuts completion (user's roster must be at/below 53)
        if stage.stage_type == StageType.OFFSEASON_ROSTER_CUTS:
            try:
                from ..services.roster_cuts_service import RosterCutsService

                dynasty_id = context.get("dynasty_id")
                season = context.get("season", 2025)
                db_path = context.get("db_path", self._database_path)
                user_team_id = context.get("user_team_id", 1)

                cuts_service = RosterCutsService(db_path, dynasty_id, season)
                cuts_needed = cuts_service.get_cuts_needed(user_team_id)
                return cuts_needed == 0  # Can advance only if at or below 53
            except Exception:
                # If error, allow advancement
                return True

        # Check FA completion (all waves must be done)
        if stage.stage_type == StageType.OFFSEASON_FREE_AGENCY:
            try:
                from ..services.fa_wave_executor import FAWaveExecutor

                dynasty_id = context.get("dynasty_id")
                season = context.get("season", 2025)
                db_path = context.get("db_path", self._database_path)

                executor = FAWaveExecutor.create(db_path, dynasty_id, season)
                return executor.is_fa_complete()
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
            StageType.OFFSEASON_TRADING,      # User can propose/accept trades
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

        if stage_type == StageType.OFFSEASON_HONORS:
            return {
                "stage_name": "NFL Honors",
                "description": "Announce season awards: MVP, OPOY, DPOY, All-Pro teams, and Pro Bowl selections.",
                "action_label": "Announce Awards",
                "is_interactive": False,
                "show_awards_after": True,  # Signal to UI to show awards tab after execution
            }
        elif stage_type == StageType.OFFSEASON_OWNER:
            return {
                "stage_name": "Owner Review",
                "description": "Review the season and make decisions about your GM and Head Coach.",
                "action_label": "Continue",
                "is_interactive": True,
            }
        elif stage_type == StageType.OFFSEASON_FRANCHISE_TAG:
            return self._get_franchise_tag_preview(context, user_team_id)
        elif stage_type == StageType.OFFSEASON_RESIGNING:
            return self._get_resigning_preview(context, user_team_id)
        elif stage_type == StageType.OFFSEASON_FREE_AGENCY:
            return self._get_free_agency_preview(context, user_team_id)
        elif stage_type == StageType.OFFSEASON_TRADING:
            return self._get_trading_preview(context, user_team_id)
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

    def _get_resigning_preview(
        self,
        context: Dict[str, Any],
        team_id: int
    ) -> Dict[str, Any]:
        """
        Get re-signing preview data for UI display.

        Includes GM extension proposals if owner directives exist.
        (Tollgate 6: Re-signing Integration)

        Args:
            context: Execution context
            team_id: User's team ID

        Returns:
            Dictionary with expiring players, cap data, and GM proposals
        """
        expiring_players = self._get_expiring_contracts(context, team_id)

        preview = {
            "stage_name": "Re-signing Period",
            "description": "Re-sign your team's expiring contract players before they hit free agency.",
            "expiring_players": expiring_players,
            "is_interactive": True,
        }
        # Add cap data for UI display
        preview["cap_data"] = self._get_cap_data(context, team_id)

        # Generate GM proposals if directives exist (Tollgate 6)
        gm_proposals = []
        trust_gm = False

        if expiring_players:
            try:
                from ..database.owner_directives_api import OwnerDirectivesAPI
                from ..database.proposal_api import ProposalAPI
                from ..database.connection import GameCycleDatabase
                from ..services.proposal_generators import ResigningProposalGenerator

                dynasty_id = context.get("dynasty_id")
                season = context.get("season", 2025)
                db_path = context.get("db_path", self._database_path)

                # Load owner directives
                # Note: Directives are saved for "next season" during Owner Review,
                # so we need to load season + 1 during offseason stages
                db = GameCycleDatabase(db_path)
                directives_api = OwnerDirectivesAPI(db)
                directives = directives_api.get_directives(dynasty_id, team_id, season + 1)

                if directives:
                    trust_gm = directives.trust_gm

                    # Generate proposals
                    generator = ResigningProposalGenerator(
                        db_path=db_path,
                        dynasty_id=dynasty_id,
                        season=season,
                        team_id=team_id,
                        directives=directives,
                    )
                    proposals = generator.generate_proposals(expiring_players)

                    if proposals:
                        # Persist proposals to database
                        proposal_api = ProposalAPI(db)
                        for proposal in proposals:
                            proposal_api.create_proposal(proposal)

                        # Handle Trust GM mode - auto-approve all
                        if trust_gm:
                            for proposal in proposals:
                                proposal_api.approve_proposal(
                                    dynasty_id=dynasty_id,
                                    team_id=team_id,
                                    proposal_id=proposal.proposal_id,
                                    notes="Auto-approved (Trust GM mode)",
                                )
                            gm_proposals = [
                                p.to_dict() | {"auto_approved": True}
                                for p in proposals
                            ]
                        else:
                            gm_proposals = [
                                p.to_dict() | {"auto_approved": False}
                                for p in proposals
                            ]

            except Exception as prop_error:
                print(f"[OffseasonHandler] Error generating resigning proposals: {prop_error}")
                import traceback
                traceback.print_exc()

        preview["gm_proposals"] = gm_proposals
        preview["trust_gm"] = trust_gm

        # Get GM rejection recommendations (players NOT to extend)
        gm_rejections = []
        if expiring_players:
            try:
                from ..services.resigning_service import ResigningService

                dynasty_id = context.get("dynasty_id")
                season = context.get("season", 2025)
                db_path = context.get("db_path", self._database_path)

                resigning_service = ResigningService(
                    db_path=db_path,
                    dynasty_id=dynasty_id,
                    season=season
                )

                gm_rejections = resigning_service.get_gm_rejection_recommendations(
                    team_id=team_id,
                    expiring_players=expiring_players
                )

            except Exception as reject_error:
                print(f"[OffseasonHandler] Error generating rejection recommendations: {reject_error}")
                import traceback
                traceback.print_exc()

        preview["gm_rejections"] = gm_rejections

        return preview

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

    def _get_free_agency_preview(
        self,
        context: Dict[str, Any],
        user_team_id: int
    ) -> Dict[str, Any]:
        """
        Get free agency preview data with wave-based filtering.

        Args:
            context: Execution context
            user_team_id: User's team ID

        Returns:
            Dictionary with wave state, filtered players, and user offers
        """
        try:
            from ..services.fa_wave_executor import FAWaveExecutor

            dynasty_id = context.get("dynasty_id")
            season = context.get("season", 2025)
            db_path = context.get("db_path", self._database_path)

            executor = FAWaveExecutor.create(db_path, dynasty_id, season)

            # Get wave state
            wave_state = executor.get_wave_state()
            wave_summary = executor.get_wave_summary()

            # Get available players for current wave (filtered by OVR tier)
            available_players = executor.get_available_players(user_team_id)

            # Get user's pending offers
            user_offers = executor.get_team_pending_offers(user_team_id)

            preview = {
                "stage_name": f"Free Agency - {wave_state.get('wave_name', 'Unknown')}",
                "description": (
                    f"Day {wave_state.get('current_day', 1)}/{wave_state.get('days_in_wave', 1)}. "
                    f"Submit offers to available players. Offers resolve at wave end."
                ),
                "wave_state": wave_state,
                "wave_summary": wave_summary,
                "free_agents": available_players,
                "user_offers": user_offers,
                "total_available": len(available_players),
                "pending_offers_count": wave_summary.get("pending_offers", 0),
                "signing_allowed": wave_state.get("signing_allowed", False),
                "is_fa_complete": executor.is_fa_complete(),
                "is_interactive": True,
            }
            # Add cap data for UI display
            preview["cap_data"] = self._get_cap_data(context, user_team_id)
            return preview

        except Exception as e:
            import traceback
            print(f"[OffseasonHandler] Error getting free agency preview: {e}")
            traceback.print_exc()
            # Fallback to basic preview
            return {
                "stage_name": "Free Agency",
                "description": "Sign available free agents to fill roster needs.",
                "free_agents": self._get_free_agents(context),
                "wave_state": None,
                "is_interactive": True,
            }

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

            # Tollgate 9: Generate GM draft proposal if user's pick is on the clock
            gm_proposal = None
            trust_gm = False

            if current_pick and current_pick.get("team_id") == user_team_id:
                try:
                    from ..services.proposal_generators.draft_generator import DraftProposalGenerator
                    from ..database.owner_directives_api import OwnerDirectivesAPI
                    from ..database.proposal_api import ProposalAPI
                    from ..models.owner_directives import OwnerDirectives
                    from database.database_api import DatabaseAPI

                    # Load owner directives (saved for season + 1 during Owner Review)
                    directives_api = OwnerDirectivesAPI(db_path)
                    directives_dict = directives_api.get_directives(dynasty_id, user_team_id, season + 1)

                    if directives_dict:
                        directives_dict["dynasty_id"] = dynasty_id
                        directives_dict["team_id"] = user_team_id
                        directives_dict["season"] = season
                        directives = OwnerDirectives.from_dict(directives_dict)
                        trust_gm = directives.trust_gm

                        # Generate draft proposal
                        generator = DraftProposalGenerator(
                            db_path=db_path,
                            dynasty_id=dynasty_id,
                            season=season,
                            team_id=user_team_id,
                            directives=directives,
                        )
                        proposal = generator.generate_proposal_for_pick(
                            pick_info=current_pick,
                            available_prospects=prospects,
                        )

                        # Persist proposal
                        db_api = DatabaseAPI(db_path)
                        with db_api.get_game_cycle_connection() as conn:
                            proposal_api = ProposalAPI(conn, dynasty_id)
                            proposal_api.create_proposal(proposal)

                            if trust_gm:
                                proposal_api.approve_proposal(
                                    dynasty_id=dynasty_id,
                                    team_id=user_team_id,
                                    proposal_id=proposal.proposal_id,
                                    notes="Auto-approved by Trust GM mode"
                                )

                        gm_proposal = proposal.to_dict()

                except Exception as e:
                    import traceback
                    print(f"[OffseasonHandler] Error generating draft proposal: {e}")
                    traceback.print_exc()

            preview["gm_proposal"] = gm_proposal
            preview["trust_gm"] = trust_gm

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
        1. Approved GM extension proposals (Tollgate 6)
        2. User team manual decisions (from context["user_decisions"])
        3. AI team re-signing decisions
        """
        from ..services.resigning_service import ResigningService

        dynasty_id = context.get("dynasty_id")
        season = context.get("season", 2025)
        user_team_id = context.get("user_team_id", 1)
        user_decisions = context.get("user_decisions", {})  # {player_id: "resign"|"release"}
        approved_proposals = context.get("approved_proposals", [])  # Tollgate 6
        db_path = context.get("db_path", self._database_path)

        service = ResigningService(db_path, dynasty_id, season)

        events = []
        resigned_players = []
        released_players = []
        processed_player_ids = set()  # Track players handled by proposals

        # 1. Process APPROVED GM extension proposals (Tollgate 6)
        for proposal_dict in approved_proposals:
            player_id = int(proposal_dict.get("subject_player_id", 0))
            if not player_id:
                continue

            player_name = proposal_dict.get("details", {}).get("player_name", "Unknown")

            result = service.resign_player(
                player_id,
                user_team_id,
                player_info=None,
                skip_preference_check=True,  # GM already evaluated
            )

            if result["success"]:
                resigned_players.append({
                    "player_id": player_id,
                    "player_name": result["player_name"],
                    "team_id": user_team_id,
                    "contract_details": result.get("contract_details", {}),
                    "gm_proposed": True,  # Mark as GM-proposed extension
                })
                events.append(f"Re-signed {result['player_name']} (GM recommendation)")
                processed_player_ids.add(player_id)
            else:
                # Log failure but continue
                error = result.get("error_message", "Unknown error")
                events.append(f"Failed to re-sign {player_name}: {error}")

        # 2. Process USER team manual decisions (skip if already handled by proposal)
        for player_id_str, decision in user_decisions.items():
            player_id = int(player_id_str) if isinstance(player_id_str, str) else player_id_str

            # Skip if already processed via GM proposal
            if player_id in processed_player_ids:
                continue

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

        # 3. Process AI team decisions
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
        """
        Execute free agency phase with wave-based progression.

        Uses FAWaveExecutor for multi-wave management:
        - Wave 0: Legal Tampering (no signings)
        - Wave 1: Elite players (85+ OVR)
        - Wave 2: Quality players (75-84 OVR)
        - Wave 3: Depth players (65-74 OVR)
        - Wave 4: Post-Draft (all remaining)

        Context keys:
            fa_wave_actions: {
                "submit_offers": [{"player_id": int, "aav": int, ...}],
                "withdraw_offers": [offer_id, ...]
            }
            wave_control: {
                "advance_day": bool,
                "advance_wave": bool,
                "enable_post_draft": bool
            }
        """
        from ..services.fa_wave_executor import FAWaveExecutor, OfferOutcome
        from team_management.teams.team_loader import TeamDataLoader

        dynasty_id = context.get("dynasty_id")
        season = context.get("season", 2025)
        user_team_id = context.get("user_team_id", 1)
        db_path = context.get("db_path", self._database_path)

        # Get action and control contexts
        fa_wave_actions = context.get("fa_wave_actions", {})
        wave_control = context.get("wave_control", {})

        # Legacy support: convert old fa_decisions to new format
        legacy_decisions = context.get("fa_decisions", {})
        if legacy_decisions and not fa_wave_actions:
            fa_wave_actions = self._convert_legacy_fa_decisions(legacy_decisions)

        # TOLLGATE 7: Process approved proposals from previous iteration
        # When owner clicks "Approve" on a GM proposal, it gets added here
        approved_proposal_ids = context.get("approved_proposal_ids", [])
        if approved_proposal_ids:
            print(f"[DEBUG OffseasonHandler] Processing {len(approved_proposal_ids)} approved proposals")
            try:
                from ..database.proposal_api import ProposalAPI
                from ..models.proposal_enums import ProposalStatus
                import sqlite3

                conn = sqlite3.connect(db_path)
                proposal_api = ProposalAPI(conn, dynasty_id)

                # Get approved proposals and convert to offers
                additional_offers = []
                for proposal_id in approved_proposal_ids:
                    proposal = proposal_api.get_proposal(proposal_id)
                    if proposal and proposal.proposal_type.value == "SIGNING":
                        details = proposal.details
                        contract = details.get("contract", {})

                        # Build offer from proposal details
                        offer = {
                            "player_id": int(proposal.subject_player_id),
                            "aav": contract.get("aav", 5_000_000),
                            "years": contract.get("years", 3),
                            "guaranteed": contract.get("guaranteed", 0),
                            "signing_bonus": details.get("signing_bonus", 0),
                        }
                        additional_offers.append(offer)

                        # Mark proposal as executed
                        proposal_api.update_status(
                            proposal_id,
                            ProposalStatus.APPROVED,
                            notes="Offer submitted"
                        )
                        print(f"[DEBUG OffseasonHandler] Submitting offer for player {offer['player_id']} from proposal {proposal_id}")

                conn.close()

                # Add to existing offers
                existing_offers = fa_wave_actions.get("submit_offers", [])
                fa_wave_actions["submit_offers"] = existing_offers + additional_offers

            except Exception as e:
                print(f"[WARNING OffseasonHandler] Failed to process approved proposals: {e}")
                import traceback
                traceback.print_exc()

        # Create executor (factory handles service instantiation)
        executor = FAWaveExecutor.create(db_path, dynasty_id, season)

        # Execute turn with all actions
        result = executor.execute(
            user_team_id=user_team_id,
            submit_offers=fa_wave_actions.get("submit_offers", []),
            withdraw_offers=fa_wave_actions.get("withdraw_offers", []),
            advance_day=wave_control.get("advance_day", False),
            advance_wave=wave_control.get("advance_wave", False),
            enable_post_draft=wave_control.get("enable_post_draft", False)
        )

        # CRITICAL: Fetch fresh wave state after execution to ensure consistency
        # Don't rely on result.wave which may be stale - get directly from database
        fresh_wave_state = executor.get_wave_state()

        # MILESTONE 10/13: Generate GM proposals (if guidance provided and wave active)
        # Load owner directives for FA guidance if not explicitly provided
        gm_proposals = []
        fa_guidance = context.get("fa_guidance")  # FAGuidance object from UI
        gm_archetype = context.get("gm_archetype")  # GMArchetype object from team

        # Try to load FA guidance from owner directives if not provided
        if fa_guidance is None:
            try:
                from ..database.owner_directives_api import OwnerDirectivesAPI
                from ..models.owner_directives import OwnerDirectives

                # Note: Directives are saved for "next season" during Owner Review,
                # so we need to load season + 1 during offseason stages
                directives_api = OwnerDirectivesAPI(db_path)
                directives_dict = directives_api.get_directives(dynasty_id, user_team_id, season + 1)
                if directives_dict:
                    directives_dict["dynasty_id"] = dynasty_id
                    directives_dict["team_id"] = user_team_id
                    directives_dict["season"] = season
                    owner_directives = OwnerDirectives.from_dict(directives_dict)
                    fa_guidance = owner_directives.to_fa_guidance()
            except Exception:
                pass  # Proceed without directives if loading fails

        if fa_guidance and gm_archetype and not fresh_wave_state.get("wave_complete", False):
            try:
                from ..services.gm_fa_proposal_engine import GMFAProposalEngine

                # Get available players for current wave
                available_players = executor.get_available_players(user_team_id=user_team_id)

                # Get team needs (stub for now - Phase 1 uses simple position-based needs)
                team_needs = self._get_team_needs(db_path, dynasty_id, user_team_id)

                # Get cap space
                from salary_cap.cap_calculator import CapCalculator
                cap_calc = CapCalculator(db_path)
                cap_data = cap_calc.calculate_team_cap(user_team_id, season, dynasty_id)
                cap_space = cap_data.get("available_cap", 0)

                # Generate proposals
                engine = GMFAProposalEngine(gm_archetype, fa_guidance)
                ephemeral_proposals = engine.generate_proposals(
                    available_players=available_players,
                    team_needs=team_needs,
                    cap_space=cap_space,
                    wave=fresh_wave_state.get("current_wave", 0)
                )

                print(f"[DEBUG OffseasonHandler] Generated {len(ephemeral_proposals)} GM proposals for wave {fresh_wave_state.get('current_wave')}")

                # TOLLGATE 7: Convert ephemeral proposals to persistent format
                if ephemeral_proposals:
                    from ..services.proposal_generators import FASigningProposalGenerator
                    from ..database.proposal_api import ProposalAPI
                    from ..models.proposal_enums import ProposalStatus

                    # Get directives for generator (reload if we only have fa_guidance)
                    directives_for_gen = None
                    if 'owner_directives' in dir():
                        directives_for_gen = owner_directives
                    else:
                        # Reload directives
                        try:
                            directives_dict_reload = directives_api.get_directives(dynasty_id, user_team_id, season + 1)
                            if directives_dict_reload:
                                directives_dict_reload["dynasty_id"] = dynasty_id
                                directives_dict_reload["team_id"] = user_team_id
                                directives_dict_reload["season"] = season
                                from ..models.owner_directives import OwnerDirectives as OD
                                directives_for_gen = OD.from_dict(directives_dict_reload)
                        except Exception:
                            pass

                    # Convert to persistent proposals
                    generator = FASigningProposalGenerator(
                        db_path=db_path,
                        dynasty_id=dynasty_id,
                        season=season,
                        team_id=user_team_id,
                        directives=directives_for_gen,
                    )
                    persistent_proposals = generator.generate_proposals(
                        gm_proposals=ephemeral_proposals,
                        wave_number=fresh_wave_state.get("current_wave", 0),
                        cap_space=cap_space,
                    )

                    # Persist to database
                    import sqlite3
                    conn = sqlite3.connect(db_path)
                    proposal_api = ProposalAPI(conn, dynasty_id)

                    for proposal in persistent_proposals:
                        proposal_api.create_proposal(proposal)

                    # Handle Trust GM mode: auto-approve and execute
                    if directives_for_gen and directives_for_gen.trust_gm:
                        print(f"[DEBUG OffseasonHandler] Trust GM mode: auto-approving {len(persistent_proposals)} proposals")
                        for proposal in persistent_proposals:
                            proposal.approve(notes="Auto-approved (Trust GM mode)")
                            proposal_api.update_status(
                                proposal.proposal_id,
                                ProposalStatus.APPROVED,
                                notes="Auto-approved (Trust GM mode)"
                            )

                    conn.close()

                    # Use persistent proposals (as dicts) for return
                    gm_proposals = [p.to_dict() for p in persistent_proposals]
                    print(f"[DEBUG OffseasonHandler] Persisted {len(gm_proposals)} proposals to database")
                else:
                    gm_proposals = []
            except Exception as e:
                print(f"[WARNING OffseasonHandler] Failed to generate GM proposals: {e}")
                import traceback
                traceback.print_exc()
                gm_proposals = []

        # Format events from structured result
        events = self._format_fa_events(result, user_team_id)

        # Convert SigningResult dataclasses to dicts for compatibility
        user_signings = [
            {
                "player_id": s.player_id,
                "player_name": s.player_name,
                "team_id": s.team_id,
                "aav": s.aav,
                "years": s.years,
            }
            for s in result.signings if s.team_id == user_team_id
        ]
        ai_signings = [
            {
                "player_id": s.player_id,
                "player_name": s.player_name,
                "team_id": s.team_id,
                "aav": s.aav,
                "years": s.years,
            }
            for s in result.signings if s.team_id != user_team_id
        ]
        surprises = [
            {
                "player_id": s.player_id,
                "player_name": s.player_name,
                "team_id": s.team_id,
                "aav": s.aav,
            }
            for s in result.surprises
        ]

        # Calculate user_lost_bids: players user bid on but signed elsewhere
        user_lost_bids = []
        team_loader = TeamDataLoader()

        for offer in result.offers_submitted:
            if offer.outcome == OfferOutcome.SUBMITTED:
                player_id = offer.player_id
                # Check if this player signed with a different team
                signing = next(
                    (s for s in result.signings if s.player_id == player_id),
                    None
                )
                if signing and signing.team_id != user_team_id:
                    # User lost this bid - player signed elsewhere
                    team = team_loader.get_team_by_id(signing.team_id)
                    team_name = team.full_name if team else f"Team {signing.team_id}"

                    user_lost_bids.append({
                        "player_id": signing.player_id,
                        "player_name": signing.player_name,
                        "position": "",  # Not in SigningResult
                        "overall": 0,    # Not in SigningResult
                        "team_id": signing.team_id,
                        "team_name": team_name,
                        "aav": signing.aav,
                        "years": signing.years,
                    })

        # ALSO check for players who rejected ALL offers
        # These players had user offers but no signing anywhere
        for offer in result.offers_submitted:
            if offer.outcome == OfferOutcome.SUBMITTED:
                player_id = offer.player_id

                # If player rejected all offers, they'll be in rejections list
                if player_id in result.rejections:
                    # Get player name from database (rejections list only has IDs)
                    import sqlite3
                    conn = sqlite3.connect(db_path)
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT
                            first_name || ' ' || last_name as name,
                            positions,
                            attributes
                        FROM players
                        WHERE dynasty_id = ? AND player_id = ?
                    """, (dynasty_id, player_id))
                    row = cursor.fetchone()
                    conn.close()

                    if row:
                        import json
                        positions = json.loads(row["positions"])
                        attributes = json.loads(row["attributes"])
                        user_lost_bids.append({
                            "player_id": player_id,
                            "player_name": row["name"],
                            "position": positions[0] if positions else "",
                            "overall": attributes.get("overall", 0),
                            "team_id": None,  # No team - rejected all
                            "team_name": "Rejected All Offers",  # Special marker
                            "aav": 0,  # No contract
                            "years": 0,
                        })

        # Add team names to user signings for dialog display
        for signing in user_signings:
            team = team_loader.get_team_by_id(user_team_id)
            signing["team_name"] = team.full_name if team else f"Team {user_team_id}"
            signing["position"] = ""  # Not in SigningResult
            signing["overall"] = 0    # Not in SigningResult

        # Use FRESH wave state from database (not from result which may be stale)
        print(f"[DEBUG OffseasonHandler] Returning wave_state: wave={fresh_wave_state.get('current_wave')}, name={fresh_wave_state.get('wave_name')}")
        rejections_added = len([p for p in user_lost_bids if p.get('team_name') == 'Rejected All Offers'])
        print(f"[DEBUG OffseasonHandler] wave_advanced={wave_control.get('advance_wave', False)}, user_signings={len(user_signings)}, user_lost_bids={len(user_lost_bids)}, rejections_added={rejections_added}, gm_proposals={len(gm_proposals)}")

        # Generate FA headlines for notable signings
        all_signings = user_signings + ai_signings
        if all_signings:
            current_wave = fresh_wave_state.get("current_wave", 0)
            self._generate_fa_headlines(context, all_signings, current_wave)

        return {
            "games_played": [],
            "events_processed": events,
            "user_signings": user_signings,
            "user_lost_bids": user_lost_bids,
            "ai_signings": ai_signings,
            "surprises": surprises,
            "gm_proposals": gm_proposals,  # Milestone 10: GM proposals for owner approval
            "wave_state": {
                "wave": fresh_wave_state.get("current_wave", 0),
                "wave_name": fresh_wave_state.get("wave_name", "Unknown"),
                "current_day": fresh_wave_state.get("current_day", 1),
                "days_in_wave": fresh_wave_state.get("days_in_wave", 1),
                "wave_complete": fresh_wave_state.get("wave_complete", False),
                "pending_offers": fresh_wave_state.get("pending_offers", 0),
            },
            "wave_advanced": wave_control.get("advance_wave", False),
            "is_fa_complete": result.is_fa_complete,  # This comes from executor method, not state dict
        }

    def _format_fa_events(self, result, user_team_id: int) -> List[str]:
        """
        Format WaveExecutionResult into event strings.

        Args:
            result: WaveExecutionResult from executor
            user_team_id: User's team ID

        Returns:
            List of formatted event strings
        """
        from ..services.fa_wave_executor import OfferOutcome

        events = []
        events.append(f"Free Agency {result.wave_name} - Day {result.current_day}")

        # Offer submissions
        for offer in result.offers_submitted:
            if offer.outcome == OfferOutcome.SUBMITTED:
                events.append(f"Submitted offer to player {offer.player_id}")
            else:
                events.append(f"Offer failed: {offer.error}")

        # Offer withdrawals
        for offer_id in result.offers_withdrawn:
            events.append(f"Withdrew offer #{offer_id}")

        # AI activity
        if result.ai_offers_made > 0:
            events.append(f"AI teams submitted {result.ai_offers_made} offers")

        # Surprise signings
        for s in result.surprises:
            events.append(f"SURPRISE: {s.player_name} signed by Team {s.team_id}!")

        # Signings from wave resolution
        for s in result.signings:
            events.append(
                f"Signed: {s.player_name} to Team {s.team_id} "
                f"({s.years} yr, ${s.aav:,}/yr)"
            )

        # Rejections
        for player_id in result.rejections:
            events.append(f"Player {player_id} rejected all offers")

        # Summary
        events.append(f"Pending offers: {result.pending_offers}")

        return events

    def _convert_legacy_fa_decisions(
        self,
        fa_decisions: Dict[Any, str]
    ) -> Dict[str, Any]:
        """
        Convert legacy fa_decisions format to new fa_wave_actions format.

        Legacy format: {player_id: "sign"}
        New format: {"submit_offers": [{player_id, aav, years, ...}], "withdraw_offers": []}

        Args:
            fa_decisions: Legacy format dict

        Returns:
            New format fa_wave_actions dict
        """
        submit_offers = []

        for player_id_str, decision in fa_decisions.items():
            player_id = int(player_id_str) if isinstance(player_id_str, str) else player_id_str

            if decision == "sign":
                # Legacy signing uses market rate, so we need to estimate
                # The executor will use market value from the service
                submit_offers.append({
                    "player_id": player_id,
                    "aav": 0,  # Will be calculated from market
                    "years": 3,  # Default
                    "guaranteed": 0,  # Will be calculated
                    "signing_bonus": 0,
                })

        return {
            "submit_offers": submit_offers,
            "withdraw_offers": [],
        }

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
        from ..database.owner_directives_api import OwnerDirectivesAPI
        from ..models.owner_directives import OwnerDirectives

        dynasty_id = context.get("dynasty_id")
        season = context.get("season", 2025)
        user_team_id = context.get("user_team_id", 1)
        db_path = context.get("db_path", self._database_path)
        draft_decisions = context.get("draft_decisions", {})  # {pick_num: prospect_id}
        auto_complete = context.get("auto_complete", False)
        sim_to_user_pick = context.get("sim_to_user_pick", False)
        draft_direction = context.get("draft_direction")  # Owner's strategy (from UI override)

        events = []
        picks = []

        try:
            # Load owner directives if no explicit draft_direction provided
            if draft_direction is None:
                try:
                    # Note: Directives are saved for "next season" during Owner Review,
                    # so we need to load season + 1 during offseason stages
                    directives_api = OwnerDirectivesAPI(db_path)
                    directives_dict = directives_api.get_directives(dynasty_id, user_team_id, season + 1)
                    if directives_dict:
                        directives_dict["dynasty_id"] = dynasty_id
                        directives_dict["team_id"] = user_team_id
                        directives_dict["season"] = season
                        owner_directives = OwnerDirectives.from_dict(directives_dict)
                        draft_direction = owner_directives.to_draft_direction()
                        events.append(f"Using owner directives: {owner_directives.draft_strategy} strategy")

                        # Resolve draft wishlist names to prospect IDs
                        if owner_directives.draft_wishlist:
                            try:
                                from database.draft_class_api import DraftClassAPI
                                draft_class_api = DraftClassAPI()
                                for prospect_name in owner_directives.draft_wishlist:
                                    prospect = draft_class_api.find_prospect_by_name(
                                        dynasty_id, season, prospect_name
                                    )
                                    if prospect:
                                        draft_direction.watchlist_prospect_ids.append(
                                            prospect["player_id"]
                                        )
                                        events.append(
                                            f"Watchlist: {prospect['first_name']} {prospect['last_name']} "
                                            f"({prospect['position']}, {prospect['overall']} OVR)"
                                        )
                            except Exception as e:
                                pass  # Proceed without resolved wishlist
                except Exception as e:
                    pass  # Proceed without directives if loading fails

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
                # Auto-complete entire draft with owner directives
                results = draft_service.auto_complete_draft(
                    user_team_id=user_team_id,
                    draft_direction=draft_direction
                )
                picks = [r for r in results if r.get("success")]
                events.append(f"NFL Draft completed ({len(picks)} picks)")
            else:
                # Interactive mode: process user decision if provided
                current_pick = draft_service.get_current_pick()

                if current_pick:
                    overall_pick = current_pick["overall_pick"]

                    # Tollgate 9: Check for approved GM draft proposal FIRST
                    approved_prospect_id = self._get_approved_draft_pick(
                        context=context,
                        user_team_id=user_team_id,
                    )

                    if approved_prospect_id:
                        # Execute the approved GM pick
                        result = draft_service.make_draft_pick(
                            approved_prospect_id, user_team_id, current_pick
                        )
                        if result.get("success"):
                            picks.append(result)
                            events.append(
                                f"Pick {overall_pick}: You selected {result['player_name']} "
                                f"({result['position']}, {result['overall']} OVR) (GM recommendation)"
                            )
                    # Execute user pick if decision provided (manual override)
                    elif overall_pick in draft_decisions:
                        prospect_id = draft_decisions[overall_pick]
                        result = draft_service.make_draft_pick(prospect_id, user_team_id, current_pick)
                        if result.get("success"):
                            picks.append(result)
                            events.append(
                                f"Pick {overall_pick}: You selected {result['player_name']} "
                                f"({result['position']}, {result['overall']} OVR)"
                            )

                    # Sim AI picks to user's next turn (with draft direction if provided)
                    ai_results = draft_service.sim_to_user_pick(
                        user_team_id=user_team_id,
                        draft_direction=draft_direction
                    )
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

            # Generate draft headlines for notable picks
            if picks:
                self._generate_draft_headlines(context, picks, is_complete)

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

    def _get_approved_draft_pick(
        self,
        context: Dict[str, Any],
        user_team_id: int,
    ) -> Optional[int]:
        """
        Get prospect ID from approved GM draft proposal.

        Checks for approved DRAFT_PICK proposals for the current pick.
        If found, marks the proposal as executed and returns the prospect ID.

        Args:
            context: Execution context with dynasty_id, season, db_path
            user_team_id: User's team ID

        Returns:
            Prospect ID if approved proposal exists, None otherwise
        """
        try:
            from ..database.proposal_api import ProposalAPI
            from ..models.proposal_enums import ProposalType

            dynasty_id = context.get("dynasty_id")
            db_path = context.get("db_path", self._database_path)

            with sqlite3.connect(db_path) as conn:
                proposal_api = ProposalAPI(conn, dynasty_id)

                # Get approved draft pick proposals
                approved = proposal_api.get_approved_proposals(
                    dynasty_id=dynasty_id,
                    team_id=user_team_id,
                    stage="OFFSEASON_DRAFT",
                    proposal_type=ProposalType.DRAFT_PICK,
                )

                if not approved:
                    return None

                # Take the first approved proposal (should only be one per pick)
                proposal = approved[0]
                prospect_id = proposal.details.get("prospect_id")

                if not prospect_id:
                    print(f"[OffseasonHandler] Approved draft proposal missing prospect_id")
                    return None

                # Mark as executed so it won't be picked up again
                proposal_api.mark_proposal_executed(
                    dynasty_id=dynasty_id,
                    team_id=user_team_id,
                    proposal_id=proposal.proposal_id,
                )

                return prospect_id

        except Exception as e:
            print(f"[OffseasonHandler] Error getting approved draft pick: {e}")
            return None

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

            # Tollgate 10: Generate GM cut proposals
            gm_proposals = []
            trust_gm = False

            if cuts_needed > 0:
                from ..database.owner_directives_api import OwnerDirectivesAPI
                from ..database.connection import GameCycleDatabase

                db = GameCycleDatabase(db_path)
                conn = db.get_connection()

                directives_api = OwnerDirectivesAPI(conn, dynasty_id)
                directives = directives_api.get_directives(dynasty_id, team_id, season + 1)

                if directives:
                    trust_gm = directives.trust_gm

                    from ..services.proposal_generators.cuts_generator import RosterCutsProposalGenerator

                    generator = RosterCutsProposalGenerator(
                        db_path=db_path,
                        dynasty_id=dynasty_id,
                        season=season,
                        team_id=team_id,
                        directives=directives,
                    )

                    proposals = generator.generate_proposals(roster, cuts_needed)

                    # Persist proposals
                    from ..database.proposal_api import ProposalAPI
                    proposal_api = ProposalAPI(conn, dynasty_id)

                    for proposal in proposals:
                        proposal_api.create_proposal(proposal)

                        if trust_gm:
                            proposal_api.approve_proposal(
                                dynasty_id, team_id, proposal.proposal_id
                            )

                    gm_proposals = [p.to_dict() for p in proposals]

            preview = {
                "stage_name": "Roster Cuts",
                "description": f"Cut your roster from {roster_count} players down to the 53-man limit.",
                "roster": roster,
                "roster_count": roster_count,
                "cuts_needed": cuts_needed,
                "cut_suggestions": suggested_ids,
                "gm_proposals": gm_proposals,
                "trust_gm": trust_gm,
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

            # Tollgate 11: Generate GM waiver proposals
            gm_proposals = []
            trust_gm = False

            if waiver_players:  # Only generate if players available
                from ..database.owner_directives_api import OwnerDirectivesAPI
                from ..database.connection import GameCycleDatabase

                db = GameCycleDatabase(db_path)
                conn = db.get_connection()

                directives_api = OwnerDirectivesAPI(conn, dynasty_id)
                directives = directives_api.get_directives(dynasty_id, team_id, season + 1)

                if directives:
                    trust_gm = directives.trust_gm

                    from ..services.proposal_generators.waiver_generator import WaiverProposalGenerator

                    generator = WaiverProposalGenerator(
                        db_path=db_path,
                        dynasty_id=dynasty_id,
                        season=season,
                        team_id=team_id,
                        directives=directives,
                    )

                    proposals = generator.generate_proposals(waiver_players)

                    # Persist proposals
                    from ..database.proposal_api import ProposalAPI
                    proposal_api = ProposalAPI(conn, dynasty_id)

                    for proposal in proposals:
                        proposal_api.create_proposal(proposal)

                        if trust_gm:
                            proposal_api.approve_proposal(
                                dynasty_id, team_id, proposal.proposal_id
                            )

                    gm_proposals = [p.to_dict() for p in proposals]

            preview = {
                "stage_name": "Waiver Wire",
                "description": f"Submit waiver claims for cut players. Your priority: #{user_priority}",
                "waiver_players": waiver_players,
                "user_priority": user_priority,
                "user_claims": claim_player_ids,
                "total_on_waivers": len(waiver_players),
                "gm_proposals": gm_proposals,
                "trust_gm": trust_gm,
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

            # Tollgate 10: Execute approved GM proposals first
            from ..database.proposal_api import ProposalAPI
            from ..database.connection import GameCycleDatabase
            from ..models.proposal_enums import ProposalType

            db = GameCycleDatabase(db_path)
            conn = db.get_connection()
            proposal_api = ProposalAPI(conn, dynasty_id)

            approved = proposal_api.get_approved_proposals(
                dynasty_id=dynasty_id,
                team_id=user_team_id,
                stage="OFFSEASON_ROSTER_CUTS",
                proposal_type=ProposalType.CUT,
            )

            if approved:
                # Execute approved GM proposals
                for proposal in approved:
                    player_id = proposal.details.get("player_id")
                    use_june_1 = proposal.details.get("use_june_1", False)

                    if not player_id:
                        continue

                    result = cuts_service.cut_player(
                        player_id=player_id,
                        team_id=user_team_id,
                        add_to_waivers=True,
                        use_june_1=use_june_1,
                    )

                    if result.get("success"):
                        user_cut_results.append(result)
                        total_dead_money += result.get("dead_money", 0)
                        total_cap_savings += result.get("cap_savings", 0)

                        # Show GM recommendation in event message
                        cut_type_str = " (June 1)" if use_june_1 else ""
                        next_yr_str = ""
                        if result.get("dead_money_next_year", 0) > 0:
                            next_yr_str = f", Next yr: ${result['dead_money_next_year']:,}"
                        events.append(
                            f"Cut {result['player_name']}{cut_type_str} - "
                            f"${result['cap_savings']/1_000_000:.1f}M saved, "
                            f"${result['dead_money']/1_000_000:.1f}M dead (GM recommendation)"
                        )

                    # Mark executed
                    proposal_api.mark_proposal_executed(
                        dynasty_id, user_team_id, proposal.proposal_id
                    )

                if user_cut_results:
                    events.append(
                        f"GM-recommended cuts complete: {len(user_cut_results)} players, "
                        f"${total_cap_savings:,} cap savings, ${total_dead_money:,} dead money"
                    )

            # 1. Process manual USER team cuts (if provided, overrides/supplements GM proposals)
            elif user_cuts:
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

            # Tollgate 11: Execute approved GM proposals first
            from ..database.proposal_api import ProposalAPI
            from ..database.connection import GameCycleDatabase
            from ..models.proposal_enums import ProposalType

            db = GameCycleDatabase(db_path)
            conn = db.get_connection()
            proposal_api = ProposalAPI(conn, dynasty_id)

            approved = proposal_api.get_approved_proposals(
                dynasty_id=dynasty_id,
                team_id=user_team_id,
                stage="OFFSEASON_WAIVER_WIRE",
                proposal_type=ProposalType.WAIVER_CLAIM,
            )

            gm_claims_submitted = []
            if approved:
                # Execute approved GM proposals
                for proposal in approved:
                    player_id = proposal.details.get("player_id")

                    if not player_id:
                        continue

                    result = waiver_service.submit_claim(user_team_id, player_id)

                    if result.get("success"):
                        gm_claims_submitted.append(result)
                        events.append(
                            f"Submitted claim for {proposal.details.get('player_name', f'player {player_id}')} "
                            f"(GM recommendation)"
                        )

                    # Mark executed
                    proposal_api.mark_proposal_executed(
                        dynasty_id, user_team_id, proposal.proposal_id
                    )

                if gm_claims_submitted:
                    events.append(
                        f"GM-recommended claims: {len(gm_claims_submitted)} submitted"
                    )

            # 1. Submit manual user's claims (supplements GM proposals)
            user_claims_submitted = []
            if user_claims:
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

            # Generate GM proposal if directives exist and tag not used
            gm_proposal = None
            trust_gm = False

            if not tag_used:
                try:
                    from ..database.owner_directives_api import OwnerDirectivesAPI
                    from ..database.proposal_api import ProposalAPI
                    from ..database.connection import GameCycleDatabase
                    from ..services.proposal_generators import FranchiseTagProposalGenerator

                    # Load owner directives
                    # Note: Directives are saved for "next season" during Owner Review,
                    # so we need to load season + 1 during offseason stages
                    db = GameCycleDatabase(db_path)
                    directives_api = OwnerDirectivesAPI(db)
                    directives = directives_api.get_directives(dynasty_id, team_id, season + 1)

                    if directives:
                        trust_gm = directives.trust_gm

                        # Generate proposal
                        generator = FranchiseTagProposalGenerator(
                            db_path=db_path,
                            dynasty_id=dynasty_id,
                            season=season,
                            team_id=team_id,
                            directives=directives,
                        )
                        proposal = generator.generate_proposal()

                        if proposal:
                            # Persist proposal to database
                            proposal_api = ProposalAPI(db)
                            proposal_api.create_proposal(proposal)

                            gm_proposal = proposal.to_dict()

                            # Handle Trust GM mode - auto-approve
                            if trust_gm:
                                proposal_api.approve_proposal(
                                    dynasty_id=dynasty_id,
                                    team_id=team_id,
                                    proposal_id=proposal.proposal_id,
                                    notes="Auto-approved (Trust GM mode)",
                                )
                                gm_proposal["auto_approved"] = True
                            else:
                                gm_proposal["auto_approved"] = False

                except Exception as prop_error:
                    print(f"[OffseasonHandler] Error generating tag proposal: {prop_error}")
                    import traceback
                    traceback.print_exc()

            preview["gm_proposal"] = gm_proposal
            preview["trust_gm"] = trust_gm

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
                "gm_proposal": None,
                "trust_gm": False,
            }

    def _execute_honors(
        self,
        stage: Stage,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute NFL Honors stage - calculate and announce awards.

        This is the first offseason stage, occurring right after the Super Bowl.
        Calculates MVP, OPOY, DPOY, OROY, DROY, CPOY, All-Pro teams, Pro Bowl,
        and statistical leaders.

        Also applies annual decay to inactive RECENT rivalries (Milestone 11, Tollgate 6).

        In real NFL, the NFL Honors ceremony occurs Thursday before the Super Bowl,
        but for game flow simplicity, we run it as the first offseason stage.
        """
        from ..services.awards_service import AwardsService

        dynasty_id = context.get("dynasty_id")
        season = context.get("season", 2025)
        db_path = context.get("db_path", self._database_path)

        events = []
        awards_calculated = []

        # Decay inactive RECENT rivalries (Milestone 11, Tollgate 6)
        # This runs at the start of offseason to decay rivalries that didn't meet this season
        try:
            from ..database.connection import GameCycleDatabase
            from ..services.rivalry_service import RivalryService

            gc_db = GameCycleDatabase(db_path)
            rivalry_service = RivalryService(gc_db)
            decay_results = rivalry_service.decay_inactive_rivalries(dynasty_id, season)

            for rivalry, new_intensity, status in decay_results:
                if status == 'removed':
                    events.append(f"Rivalry ended: {rivalry.rivalry_name}")
                elif status == 'decayed':
                    events.append(
                        f"Rivalry fading: {rivalry.rivalry_name} "
                        f"({rivalry.intensity} -> {new_intensity})"
                    )
        except Exception as e:
            # Don't fail the entire stage if rivalry decay fails
            import logging
            logging.getLogger(__name__).warning(f"Failed to decay rivalries: {e}")

        try:
            service = AwardsService(db_path, dynasty_id, season)

            # Check if awards already exist (idempotent)
            if service.awards_already_calculated():
                events.append(f"Awards for {season} season already calculated")
                return {
                    "games_played": [],
                    "events_processed": events,
                    "awards_calculated": [],
                    "already_calculated": True,
                }

            # CRITICAL: Aggregate player stats into season grades BEFORE awards calculation
            # The EligibilityChecker reads from player_season_grades, which must be populated
            # from player_game_stats (accumulated during regular season).
            #
            # OPTIMIZATION: Skip aggregation if grades already exist (for re-runs)
            try:
                from ..database.analytics_api import AnalyticsAPI
                analytics_api = AnalyticsAPI(db_path)

                # Check if grades already calculated (skip expensive re-aggregation)
                if analytics_api.season_grades_exist(dynasty_id, season):
                    events.append("Season grades already calculated - skipping aggregation")
                else:
                    # Prefer game_grades aggregation (has OL blocking grades, etc.)
                    # Fall back to stats-based if no game grades exist
                    if analytics_api.game_grades_exist(dynasty_id, season):
                        grades_aggregated = analytics_api.aggregate_season_grades_from_game_grades(
                            dynasty_id, season
                        )
                        events.append(f"Aggregated season grades from game grades for {grades_aggregated} players")
                    else:
                        grades_aggregated = analytics_api.aggregate_season_grades_from_stats(
                            dynasty_id, season
                        )
                        events.append(f"Aggregated season grades from stats for {grades_aggregated} players")
            except Exception as agg_error:
                import logging
                import traceback
                logging.getLogger(__name__).warning(
                    f"Failed to aggregate season grades: {agg_error}"
                )
                traceback.print_exc()
                events.append(f"Warning: Could not aggregate player grades - awards may be incomplete")

            # Calculate all major awards
            awards = service.calculate_all_awards()
            for award_id, result in awards.items():
                if result.has_winner:
                    awards_calculated.append({
                        "award_id": award_id,
                        "winner_name": result.winner.player_name,
                        "winner_position": result.winner.position,
                        "vote_share": result.winner.vote_share,
                    })
                    events.append(
                        f"{result.winner.player_name} ({result.winner.position}) "
                        f"wins {award_id.upper()} with {result.winner.vote_share:.1%} of votes"
                    )

            # Select All-Pro teams
            all_pro = service.select_all_pro_teams()
            first_team_count = sum(len(players) for players in all_pro.first_team.values())
            second_team_count = sum(len(players) for players in all_pro.second_team.values())
            events.append(f"All-Pro teams selected: {first_team_count} First Team, {second_team_count} Second Team")

            # Select Pro Bowl rosters
            pro_bowl = service.select_pro_bowl_rosters()
            afc_count = sum(len(players) for players in pro_bowl.afc_roster.values())
            nfc_count = sum(len(players) for players in pro_bowl.nfc_roster.values())
            events.append(f"Pro Bowl rosters selected: {afc_count} AFC, {nfc_count} NFC")

            # Record statistical leaders
            stat_leaders = service.record_statistical_leaders()
            events.append(f"Statistical leaders recorded: {stat_leaders.total_recorded} entries")

            events.append(f"NFL Honors complete - {len(awards_calculated)} awards presented")

            # Generate headlines for awards
            self._generate_awards_headlines(
                context, awards_calculated, all_pro, pro_bowl
            )

            return {
                "games_played": [],
                "events_processed": events,
                "awards_calculated": awards_calculated,
                "all_pro_count": first_team_count + second_team_count,
                "pro_bowl_count": afc_count + nfc_count,
            }

        except Exception as e:
            import traceback
            print(f"[OffseasonHandler] NFL Honors error: {e}")
            traceback.print_exc()
            events.append(f"NFL Honors error: {str(e)}")
            return {
                "games_played": [],
                "events_processed": events,
                "awards_calculated": [],
                "error": str(e),
            }

    def _execute_owner(
        self,
        stage: Stage,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute Owner Review stage - GM/HC management and directives.

        This stage allows the owner to:
        - Review the season performance
        - Fire/hire GM and Head Coach
        - Set strategic directives for the upcoming season

        Context keys (input):
            - dynasty_id: Dynasty identifier
            - season: Current season year
            - user_team_id: User's team ID
            - db_path: Database path

        Context keys (processed by controller):
            - gm_hire: {"candidate_id": str} when hiring GM
            - hc_hire: {"candidate_id": str} when hiring HC
            - directives: Dict of owner directives to save

        Returns:
            - current_staff: Dict with 'gm' and 'hc' data
            - season_summary: Dict with season record and target
            - prev_directives: Dict with existing directives
            - events_processed: List of event strings
        """
        from ..services.owner_service import OwnerService
        from ..database.standings_api import StandingsAPI

        dynasty_id = context.get("dynasty_id")
        season = context.get("season", 2025)
        user_team_id = context.get("user_team_id", 1)
        db_path = context.get("db_path", self._database_path)

        events = []

        try:
            service = OwnerService(db_path, dynasty_id, season)

            # Ensure staff exists for this team/season
            current_staff = service.ensure_staff_exists(user_team_id)
            events.append(f"Owner reviewed {season} season performance")

            # Get season summary with standings
            season_summary = {"season": season, "wins": None, "losses": None, "target_wins": None}
            try:
                from ..database.connection import GameCycleDatabase
                with GameCycleDatabase(db_path) as conn:
                    standings_api = StandingsAPI(conn, dynasty_id)
                    standings = standings_api.get_standings(season)
                    for team_data in standings:
                        if team_data.get("team_id") == user_team_id:
                            season_summary["wins"] = team_data.get("wins", 0)
                            season_summary["losses"] = team_data.get("losses", 0)
                            break
            except Exception:
                pass  # Standings may not exist yet

            # Get previous directives (if any)
            prev_directives = service.get_directives(user_team_id)
            if prev_directives:
                season_summary["target_wins"] = prev_directives.get("target_wins")

            return {
                "games_played": [],
                "events_processed": events,
                "current_staff": current_staff,
                "season_summary": season_summary,
                "prev_directives": prev_directives,
            }

        except Exception as e:
            events.append(f"Error in owner review: {str(e)}")
            return {
                "games_played": [],
                "events_processed": events,
                "current_staff": None,
                "season_summary": {"season": season},
                "prev_directives": None,
            }

    def _execute_franchise_tag(
        self,
        stage: Stage,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute franchise tag phase for all teams.

        Processes:
        1. User team tag decision (from approved_proposal or tag_decision)
        2. AI team tag decisions for all 31 other teams

        Context keys:
            - approved_proposal: Dict from approved PersistentGMProposal (Tollgate 5)
            - tag_decision: {"player_id": int, "tag_type": "franchise"|"transition"} (legacy)
        """
        from ..services.franchise_tag_service import FranchiseTagService

        dynasty_id = context.get("dynasty_id")
        season = context.get("season", 2025)
        user_team_id = context.get("user_team_id", 1)
        approved_proposal = context.get("approved_proposal")  # New: from proposal system
        tag_decision = context.get("tag_decision")  # Legacy: direct decision
        db_path = context.get("db_path", self._database_path)

        events = []
        tags_applied = []

        try:
            tag_service = FranchiseTagService(db_path, dynasty_id, season)

            # 1. Process USER team tag decision
            # Priority: approved_proposal > tag_decision
            player_id = None
            tag_type = None

            if approved_proposal:
                # Extract from approved GM proposal
                player_id = approved_proposal.get("subject_player_id")
                if player_id:
                    player_id = int(player_id)
                details = approved_proposal.get("details", {})
                proposal_tag_type = details.get("tag_type", "non_exclusive")
                # Map proposal tag_type to service tag_type
                tag_type = "franchise" if proposal_tag_type in ["exclusive", "non_exclusive"] else "transition"
                events.append("Processing approved GM franchise tag proposal")

            elif tag_decision and tag_decision.get("player_id"):
                # Legacy direct decision path
                player_id = tag_decision["player_id"]
                tag_type = tag_decision.get("tag_type", "franchise")

            # Execute the tag if we have a decision
            if player_id:
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

    # =========================================================================
    # Trading Stage Methods (Tollgate 5)
    # =========================================================================

    def _get_trading_preview(
        self,
        context: Dict[str, Any],
        user_team_id: int
    ) -> Dict[str, Any]:
        """
        Get trading period preview data for UI display.

        Args:
            context: Execution context
            user_team_id: User's team ID

        Returns:
            Dictionary with tradeable assets and recent trade history
        """
        try:
            from ..services.trade_service import TradeService
            from team_management.teams.team_loader import TeamDataLoader

            dynasty_id = context.get("dynasty_id")
            season = context.get("season", 2025)
            db_path = context.get("db_path", self._database_path)

            trade_service = TradeService(db_path, dynasty_id, season)
            team_loader = TeamDataLoader()

            # Ensure draft pick ownership exists for trades
            trade_service.initialize_pick_ownership()

            # Get user's tradeable players
            user_players = trade_service.get_tradeable_players(user_team_id)

            # Get user's tradeable draft picks
            user_picks = trade_service.get_tradeable_picks(user_team_id)

            # Get recent trade history (this season, all teams)
            trade_history = trade_service.get_trade_history(season=season)

            # Get all teams for trade partner selection
            teams = []
            for team_id in range(1, 33):
                if team_id != user_team_id:
                    team = team_loader.get_team_by_id(team_id)
                    if team:
                        teams.append({
                            "team_id": team_id,
                            "name": team.full_name,
                            "abbreviation": team.abbreviation,
                        })

            preview = {
                "stage_name": "Trading Period",
                "description": (
                    "Trade players and draft picks with other teams. "
                    "Propose trades, review incoming offers, and negotiate deals. "
                    "AI teams will also be actively trading during this period."
                ),
                "user_players": user_players,
                "user_picks": user_picks,
                "trade_history": trade_history[:10],  # Limit to recent 10
                "available_teams": teams,
                "trade_count_this_season": len(trade_history),
                "is_interactive": True,
            }
            # Add cap data for UI display
            preview["cap_data"] = self._get_cap_data(context, user_team_id)

            # Generate GM trade proposals (Tollgate 8)
            gm_proposals = []
            trust_gm = False

            try:
                from ..database.owner_directives_api import OwnerDirectivesAPI
                from ..database.proposal_api import ProposalAPI
                from ..database.connection import GameCycleDatabase
                from ..services.proposal_generators import TradeProposalGenerator

                # Load owner directives (saved for season + 1 during Owner Review)
                db = GameCycleDatabase(db_path)
                directives_api = OwnerDirectivesAPI(db)
                directives = directives_api.get_directives(
                    dynasty_id, user_team_id, season + 1
                )

                if directives:
                    trust_gm = directives.trust_gm

                    # Generate trade proposals
                    generator = TradeProposalGenerator(
                        db_path=db_path,
                        dynasty_id=dynasty_id,
                        season=season,
                        team_id=user_team_id,
                        directives=directives,
                    )
                    proposals = generator.generate_proposals()

                    if proposals:
                        # Persist proposals to database
                        proposal_api = ProposalAPI(db)
                        for proposal in proposals:
                            proposal_api.create_proposal(proposal)

                        # Handle Trust GM mode - auto-approve all
                        if trust_gm:
                            for proposal in proposals:
                                proposal_api.approve_proposal(
                                    dynasty_id=dynasty_id,
                                    team_id=user_team_id,
                                    proposal_id=proposal.proposal_id,
                                    notes="Auto-approved (Trust GM mode)",
                                )
                            gm_proposals = [
                                p.to_dict() | {"auto_approved": True}
                                for p in proposals
                            ]
                        else:
                            gm_proposals = [
                                p.to_dict() | {"auto_approved": False}
                                for p in proposals
                            ]

            except Exception as prop_error:
                print(f"[OffseasonHandler] Error generating trade proposals: {prop_error}")
                import traceback
                traceback.print_exc()

            preview["gm_proposals"] = gm_proposals
            preview["trust_gm"] = trust_gm

            return preview

        except Exception as e:
            import traceback
            print(f"[OffseasonHandler] Error getting trading preview: {e}")
            traceback.print_exc()
            return {
                "stage_name": "Trading Period",
                "description": "Trade players and draft picks with other teams.",
                "user_players": [],
                "user_picks": [],
                "trade_history": [],
                "available_teams": [],
                "trade_count_this_season": 0,
                "is_interactive": True,
            }

    def _execute_trading(
        self,
        stage: Stage,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute trading phase for all teams.

        Processes:
        1. User's trade proposals (from context["trade_proposals"])
        2. AI-to-AI trades with ~50% chance per team (high activity)

        Context keys:
            - trade_proposals: List of user trade proposals to execute
              Each proposal: {
                  "team1_player_ids": [int],
                  "team2_id": int,
                  "team2_player_ids": [int],
                  "team1_pick_ids": [int],  # Optional
                  "team2_pick_ids": [int],  # Optional
              }
        """
        from ..services.trade_service import TradeService

        dynasty_id = context.get("dynasty_id")
        season = context.get("season", 2025)
        user_team_id = context.get("user_team_id", 1)
        user_proposals = context.get("trade_proposals", [])
        db_path = context.get("db_path", self._database_path)

        events = []
        executed_trades = []

        try:
            trade_service = TradeService(db_path, dynasty_id, season)

            # Ensure draft pick ownership initialized
            trade_service.initialize_pick_ownership()

            # 0. Execute approved GM trade proposals (Tollgate 8)
            approved_results = self._execute_approved_trade_proposals(
                context=context,
                user_team_id=user_team_id,
                trade_service=trade_service,
            )
            executed_trades.extend(approved_results.get("trades", []))
            events.extend(approved_results.get("events", []))

            # 1. Process USER trade proposals (manual proposals from UI)
            for prop_data in user_proposals:
                team2_id = prop_data.get("team2_id")
                team1_player_ids = prop_data.get("team1_player_ids", [])
                team2_player_ids = prop_data.get("team2_player_ids", [])
                team1_pick_ids = prop_data.get("team1_pick_ids", [])
                team2_pick_ids = prop_data.get("team2_pick_ids", [])

                try:
                    # Create and evaluate proposal
                    proposal = trade_service.propose_trade(
                        team1_id=user_team_id,
                        team1_player_ids=team1_player_ids,
                        team2_id=team2_id,
                        team2_player_ids=team2_player_ids,
                        team1_pick_ids=team1_pick_ids,
                        team2_pick_ids=team2_pick_ids
                    )

                    # Have AI evaluate the trade
                    decision = trade_service.evaluate_ai_trade(
                        proposal=proposal,
                        ai_team_id=team2_id,
                        is_offseason=True
                    )

                    if decision.decision.value == "accept":
                        # Execute the trade
                        result = trade_service.execute_trade(proposal)
                        executed_trades.append(result)
                        events.append(
                            f"Trade accepted! Team {team2_id} agreed to your offer "
                            f"(Trade #{result['trade_id']})"
                        )
                    elif decision.decision.value == "counter":
                        events.append(
                            f"Team {team2_id} countered your offer. "
                            f"Reason: {decision.reasoning[:50]}..."
                        )
                    else:
                        events.append(
                            f"Team {team2_id} rejected your trade offer. "
                            f"Reason: {decision.reasoning[:50]}..."
                        )

                except ValueError as e:
                    events.append(f"Trade proposal error: {str(e)}")

            # 2. Process AI-to-AI trades (high activity ~50% per team)
            ai_result = self._process_ai_trades(trade_service, user_team_id)
            executed_trades.extend(ai_result.get("trades", []))
            events.extend(ai_result.get("events", []))

            total_trades = len(executed_trades)
            events.append(
                f"Trading period completed: {total_trades} trades executed league-wide"
            )

            # Generate trade headlines
            if executed_trades:
                self._generate_trade_headlines(context, executed_trades)

            return {
                "games_played": [],
                "events_processed": events,
                "executed_trades": executed_trades,
                "total_trades": total_trades,
            }

        except Exception as e:
            import traceback
            print(f"[OffseasonHandler] Trading execution error: {e}")
            traceback.print_exc()
            events.append(f"Trading error: {str(e)}")
            return {
                "games_played": [],
                "events_processed": events,
                "executed_trades": [],
                "total_trades": 0,
            }

    def _execute_approved_trade_proposals(
        self,
        context: Dict[str, Any],
        user_team_id: int,
        trade_service,
    ) -> Dict[str, Any]:
        """
        Execute trades from approved GM proposals (Tollgate 8).

        Retrieves approved TRADE proposals from ProposalAPI and executes
        them via TradeService.

        Args:
            context: Execution context with dynasty_id, db_path
            user_team_id: User's team ID
            trade_service: TradeService instance

        Returns:
            Dict with trades list and events list
        """
        from ..database.proposal_api import ProposalAPI
        from ..database.connection import GameCycleDatabase
        from ..models.proposal_enums import ProposalType

        events = []
        executed_trades = []

        dynasty_id = context.get("dynasty_id")
        db_path = context.get("db_path", self._database_path)

        try:
            db = GameCycleDatabase(db_path)
            proposal_api = ProposalAPI(db)

            # Get approved trade proposals
            approved = proposal_api.get_approved_proposals(
                dynasty_id=dynasty_id,
                team_id=user_team_id,
                stage="OFFSEASON_TRADING",
                proposal_type=ProposalType.TRADE,
            )

            if not approved:
                return {"trades": [], "events": []}

            for proposal in approved:
                details = proposal.details

                # Extract execution fields
                trade_partner_id = details.get("trade_partner_id")
                sending_player_ids = details.get("sending_player_ids", [])
                sending_pick_ids = details.get("sending_pick_ids", [])
                receiving_player_ids = details.get("receiving_player_ids", [])
                receiving_pick_ids = details.get("receiving_pick_ids", [])

                if not trade_partner_id:
                    events.append(
                        f"Skipped proposal {proposal.proposal_id}: missing partner ID"
                    )
                    continue

                try:
                    # Reconstruct and execute the trade
                    trade_proposal = trade_service.propose_trade(
                        team1_id=user_team_id,
                        team1_player_ids=sending_player_ids,
                        team2_id=trade_partner_id,
                        team2_player_ids=receiving_player_ids,
                        team1_pick_ids=sending_pick_ids,
                        team2_pick_ids=receiving_pick_ids,
                    )

                    # Execute without re-evaluating (already approved)
                    result = trade_service.execute_trade(trade_proposal)
                    executed_trades.append(result)

                    partner_name = details.get("trade_partner", f"Team {trade_partner_id}")
                    events.append(
                        f"GM trade executed with {partner_name} "
                        f"(Trade #{result.get('trade_id', '?')})"
                    )

                    # Mark proposal as executed
                    proposal_api.mark_proposal_executed(
                        dynasty_id=dynasty_id,
                        team_id=user_team_id,
                        proposal_id=proposal.proposal_id,
                    )

                except Exception as trade_error:
                    events.append(
                        f"Failed to execute GM trade proposal: {str(trade_error)}"
                    )

        except Exception as e:
            print(f"[OffseasonHandler] Error executing approved trade proposals: {e}")
            import traceback
            traceback.print_exc()

        return {"trades": executed_trades, "events": events}

    def _process_ai_trades(
        self,
        trade_service,
        user_team_id: int
    ) -> Dict[str, Any]:
        """
        Process AI-to-AI trades during offseason trading period.

        High activity mode: ~50% of teams attempt trades, leading to
        approximately 15+ trades per offseason (realistic NFL offseason).

        Args:
            trade_service: TradeService instance
            user_team_id: User's team ID (excluded from AI-initiated trades)

        Returns:
            Dict with trades list and events list
        """
        import random

        events = []
        executed_trades = []
        ai_trade_probability = 0.50  # 50% chance per team to attempt trade

        # Get all AI team IDs (exclude user)
        ai_teams = [t for t in range(1, 33) if t != user_team_id]
        random.shuffle(ai_teams)  # Randomize order

        # Track which teams have already traded this round to avoid conflicts
        teams_traded_this_round = set()

        for team1_id in ai_teams:
            # Skip if team already traded this round
            if team1_id in teams_traded_this_round:
                continue

            # Roll dice for trade attempt
            if random.random() > ai_trade_probability:
                continue

            # Find a trade partner (another AI team not yet traded)
            potential_partners = [
                t for t in ai_teams
                if t != team1_id and t not in teams_traded_this_round
            ]
            if not potential_partners:
                continue

            team2_id = random.choice(potential_partners)

            try:
                # Get tradeable players for both teams
                team1_players = trade_service.get_tradeable_players(team1_id)
                team2_players = trade_service.get_tradeable_players(team2_id)

                if not team1_players or not team2_players:
                    continue

                # Simple AI trade logic: propose swapping 1-2 players
                # Pick random players (weighted toward lower overall to trade away)
                team1_players_sorted = sorted(
                    team1_players, key=lambda p: p.get("overall_rating", 70)
                )
                team2_players_sorted = sorted(
                    team2_players, key=lambda p: p.get("overall_rating", 70)
                )

                # Select 1-2 players from each team (lower rated more likely)
                num_players = random.randint(1, min(2, len(team1_players_sorted), len(team2_players_sorted)))
                team1_offer = [p["player_id"] for p in team1_players_sorted[:num_players]]
                team2_offer = [p["player_id"] for p in team2_players_sorted[:num_players]]

                # Optionally include draft picks (30% chance)
                team1_picks = []
                team2_picks = []
                if random.random() < 0.30:
                    picks1 = trade_service.get_tradeable_picks(team1_id)
                    picks2 = trade_service.get_tradeable_picks(team2_id)
                    if picks1:
                        team1_picks = [random.choice(picks1)["id"]]
                    if picks2:
                        team2_picks = [random.choice(picks2)["id"]]

                # Create proposal
                proposal = trade_service.propose_trade(
                    team1_id=team1_id,
                    team1_player_ids=team1_offer,
                    team2_id=team2_id,
                    team2_player_ids=team2_offer,
                    team1_pick_ids=team1_picks,
                    team2_pick_ids=team2_picks
                )

                # Run negotiation between both AI teams
                negotiation_result = trade_service.negotiate_trade(
                    initial_proposal=proposal,
                    max_rounds=2,
                    is_offseason=True
                )

                if negotiation_result.success:
                    # Execute the agreed trade
                    final_proposal = negotiation_result.final_proposal
                    result = trade_service.execute_trade(final_proposal)
                    executed_trades.append(result)
                    teams_traded_this_round.add(team1_id)
                    teams_traded_this_round.add(team2_id)
                    events.append(
                        f"AI Trade: Team {team1_id} and Team {team2_id} "
                        f"completed a trade (#{result['trade_id']})"
                    )

            except Exception as e:
                # Log but don't fail the whole process
                print(f"[OffseasonHandler] AI trade error (Team {team1_id} <-> {team2_id}): {e}")
                continue

        return {
            "trades": executed_trades,
            "events": events,
            "teams_traded": list(teams_traded_this_round),
        }

    def _get_team_needs(
        self,
        db_path: str,
        dynasty_id: str,
        team_id: int
    ) -> Dict[str, int]:
        """
        Get team's position needs for GM proposal scoring.

        Returns dict mapping position -> need level:
            0 = Critical need (no starter)
            1 = High need (weak starter or no backup)
            2 = Moderate need (need depth)
            3+ = Low/no need (position filled)

        Phase 1 MVP: Simple depth chart count
        Future: Sophisticated needs analysis (rating thresholds, scheme fit, age)
        """
        import sqlite3
        import json

        needs = {}

        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Get all rostered players for this team
            cursor.execute("""
                SELECT positions, attributes
                FROM players
                WHERE dynasty_id = ? AND team_id = ?
            """, (dynasty_id, team_id))

            rows = cursor.fetchall()
            conn.close()

            # Count players by position
            position_counts = {}
            for row in rows:
                positions = json.loads(row["positions"])
                if positions:
                    primary_pos = positions[0]
                    position_counts[primary_pos] = position_counts.get(primary_pos, 0) + 1

            # Standard positions to check
            standard_positions = [
                "QB", "RB", "WR", "TE", "OT", "OG", "C",
                "EDGE", "DT", "LB", "CB", "S", "K", "P"
            ]

            # Convert counts to need levels
            for pos in standard_positions:
                count = position_counts.get(pos, 0)
                if count == 0:
                    needs[pos] = 0  # Critical - no player at position
                elif count == 1:
                    needs[pos] = 1  # High - only one player
                elif count == 2:
                    needs[pos] = 2  # Moderate - minimal depth
                elif count == 3:
                    needs[pos] = 3  # Low - some depth
                else:
                    needs[pos] = 4  # Very low - good depth

        except Exception as e:
            print(f"[WARNING OffseasonHandler] Failed to get team needs: {e}")
            # Return default needs (all positions moderately needed)
            needs = {pos: 2 for pos in [
                "QB", "RB", "WR", "TE", "OT", "OG", "C",
                "EDGE", "DT", "LB", "CB", "S", "K", "P"
            ]}

        return needs

    # =========================================================================
    # Media Coverage Headline Generation
    # =========================================================================

    def _generate_awards_headlines(
        self,
        context: Dict[str, Any],
        awards_calculated: List[Dict],
        all_pro: Any,
        pro_bowl: Any
    ) -> None:
        """
        Generate and persist headlines for NFL Honors awards.

        Args:
            context: Execution context with dynasty_id, season, db_path
            awards_calculated: List of award result dictionaries
            all_pro: AllProSelection result
            pro_bowl: ProBowlSelection result
        """
        try:
            from ..database.connection import GameCycleDatabase
            from ..database.media_coverage_api import MediaCoverageAPI

            dynasty_id = context.get("dynasty_id")
            season = context.get("season", 2025)
            db_path = context.get("db_path", self._database_path)

            gc_db = GameCycleDatabase(db_path)
            try:
                media_api = MediaCoverageAPI(gc_db)

                # Week 23 for offseason awards
                week = 23

                # Generate headline for MVP (highest priority)
                mvp = next((a for a in awards_calculated if a["award_id"] == "mvp"), None)
                if mvp:
                    media_api.save_headline(
                        dynasty_id=dynasty_id,
                        season=season,
                        week=week,
                        headline_data={
                            'headline_type': 'AWARD',
                            'headline': f"{mvp['winner_name']} Wins NFL MVP Award",
                            'subheadline': f"The {mvp['winner_position']} earns {mvp['vote_share']:.1%} of votes in landslide victory",
                            'body_text': f"{mvp['winner_name']} has been named the NFL's Most Valuable Player for the {season} season, capturing {mvp['vote_share']:.1%} of the votes. The {mvp['winner_position']} capped off an incredible campaign that saw him dominate opponents week after week.",
                            'sentiment': 'POSITIVE',
                            'priority': 95,
                            'team_ids': [],
                            'player_ids': [],
                            'game_id': None,
                            'metadata': {'award_type': 'mvp'}
                        }
                    )
                    print(f"[OffseasonHandler] Generated MVP headline for {mvp['winner_name']}")

                # Generate combined awards headline
                if len(awards_calculated) > 1:
                    award_names = [a['award_id'].upper() for a in awards_calculated[:5]]
                    media_api.save_headline(
                        dynasty_id=dynasty_id,
                        season=season,
                        week=week,
                        headline_data={
                            'headline_type': 'AWARD',
                            'headline': f"NFL Honors: {season} Award Winners Announced",
                            'subheadline': f"{len(awards_calculated)} major awards presented at star-studded ceremony",
                            'body_text': f"The NFL's best were honored at the annual NFL Honors ceremony. Winners included: " + ", ".join([f"{a['winner_name']} ({a['award_id'].upper()})" for a in awards_calculated[:5]]) + ".",
                            'sentiment': 'POSITIVE',
                            'priority': 85,
                            'team_ids': [],
                            'player_ids': [],
                            'game_id': None,
                            'metadata': {'award_type': 'honors_summary'}
                        }
                    )

                # Generate OROY/DROY headlines
                oroy = next((a for a in awards_calculated if a["award_id"] == "oroy"), None)
                droy = next((a for a in awards_calculated if a["award_id"] == "droy"), None)

                if oroy:
                    media_api.save_headline(
                        dynasty_id=dynasty_id,
                        season=season,
                        week=week,
                        headline_data={
                            'headline_type': 'AWARD',
                            'headline': f"{oroy['winner_name']} Named Offensive Rookie of the Year",
                            'subheadline': f"The {oroy['winner_position']} had an immediate impact in his first NFL season",
                            'body_text': f"{oroy['winner_name']} has been named the NFL's Offensive Rookie of the Year. The {oroy['winner_position']} made an immediate impact, showing why he was worth the draft pick.",
                            'sentiment': 'POSITIVE',
                            'priority': 75,
                            'team_ids': [],
                            'player_ids': [],
                            'game_id': None,
                            'metadata': {'award_type': 'oroy'}
                        }
                    )

                if droy:
                    media_api.save_headline(
                        dynasty_id=dynasty_id,
                        season=season,
                        week=week,
                        headline_data={
                            'headline_type': 'AWARD',
                            'headline': f"{droy['winner_name']} Named Defensive Rookie of the Year",
                            'subheadline': f"The {droy['winner_position']} terrorized opposing offenses",
                            'body_text': f"{droy['winner_name']} has been named the NFL's Defensive Rookie of the Year. The {droy['winner_position']} made his presence felt immediately.",
                            'sentiment': 'POSITIVE',
                            'priority': 75,
                            'team_ids': [],
                            'player_ids': [],
                            'game_id': None,
                            'metadata': {'award_type': 'droy'}
                        }
                    )

            finally:
                gc_db.close()

        except Exception as e:
            print(f"[OffseasonHandler] Failed to generate awards headlines: {e}")

    def _generate_draft_headlines(
        self,
        context: Dict[str, Any],
        picks: List[Dict],
        is_complete: bool
    ) -> None:
        """
        Generate and persist headlines for draft picks.

        Args:
            context: Execution context with dynasty_id, season, db_path
            picks: List of draft pick results
            is_complete: Whether draft is finished
        """
        if not picks:
            return

        try:
            from ..database.connection import GameCycleDatabase
            from ..database.media_coverage_api import MediaCoverageAPI
            from team_management.teams.team_loader import TeamDataLoader

            dynasty_id = context.get("dynasty_id")
            season = context.get("season", 2025)
            db_path = context.get("db_path", self._database_path)

            gc_db = GameCycleDatabase(db_path)
            team_loader = TeamDataLoader()

            try:
                media_api = MediaCoverageAPI(gc_db)

                # Week 24 for draft headlines
                week = 24

                # Generate headline for first overall pick
                first_pick = next((p for p in picks if p.get("overall_pick") == 1), None)
                if first_pick:
                    team = team_loader.get_team_by_id(first_pick["team_id"])
                    team_name = team.full_name if team else f"Team {first_pick['team_id']}"
                    media_api.save_headline(
                        dynasty_id=dynasty_id,
                        season=season,
                        week=week,
                        headline_data={
                            'headline_type': 'SIGNING',
                            'headline': f"{team_name} Select {first_pick['player_name']} with No. 1 Pick",
                            'subheadline': f"The {first_pick['position']} ({first_pick.get('overall', 0)} OVR) is the {season} NFL Draft's top selection",
                            'body_text': f"{team_name} made {first_pick['player_name']} the first overall selection in the {season} NFL Draft. The {first_pick['position']} is expected to make an immediate impact.",
                            'sentiment': 'HYPE',
                            'priority': 90,
                            'team_ids': [first_pick["team_id"]],
                            'player_ids': [],
                            'game_id': None,
                            'metadata': {'event_type': 'draft_pick', 'pick_number': 1}
                        }
                    )

                # Generate headline for notable first round picks (top 10)
                first_round_picks = [p for p in picks if p.get("overall_pick", 999) <= 10 and p.get("overall_pick") != 1]
                for pick in first_round_picks[:3]:  # Limit to 3 additional first round headlines
                    team = team_loader.get_team_by_id(pick["team_id"])
                    team_name = team.full_name if team else f"Team {pick['team_id']}"
                    media_api.save_headline(
                        dynasty_id=dynasty_id,
                        season=season,
                        week=week,
                        headline_data={
                            'headline_type': 'SIGNING',
                            'headline': f"{team_name} Land {pick['player_name']} at No. {pick['overall_pick']}",
                            'subheadline': f"The {pick['position']} fills a key need for {team_name}",
                            'body_text': f"With the {pick['overall_pick']} pick, {team_name} selected {pick['player_name']}. The {pick['position']} was considered a top prospect.",
                            'sentiment': 'POSITIVE',
                            'priority': 80 - pick['overall_pick'],
                            'team_ids': [pick["team_id"]],
                            'player_ids': [],
                            'game_id': None,
                            'metadata': {'event_type': 'draft_pick', 'pick_number': pick['overall_pick']}
                        }
                    )

                # If draft complete, generate summary headline
                if is_complete:
                    media_api.save_headline(
                        dynasty_id=dynasty_id,
                        season=season,
                        week=week,
                        headline_data={
                            'headline_type': 'SIGNING',
                            'headline': f"{season} NFL Draft Complete: 224 Selections Made",
                            'subheadline': "All 32 teams fill roster needs over seven rounds",
                            'body_text': f"The {season} NFL Draft has concluded with all 224 picks now on the books. Teams will now shift focus to rookie minicamps and offseason workouts.",
                            'sentiment': 'NEUTRAL',
                            'priority': 85,
                            'team_ids': [],
                            'player_ids': [],
                            'game_id': None,
                            'metadata': {'event_type': 'draft_complete'}
                        }
                    )
                    print(f"[OffseasonHandler] Generated draft completion headline")

            finally:
                gc_db.close()

        except Exception as e:
            print(f"[OffseasonHandler] Failed to generate draft headlines: {e}")

    def _generate_fa_headlines(
        self,
        context: Dict[str, Any],
        signings: List[Dict],
        wave: int
    ) -> None:
        """
        Generate and persist headlines for free agency signings.

        Args:
            context: Execution context with dynasty_id, season, db_path
            signings: List of signing results
            wave: Current FA wave (0-4)
        """
        if not signings:
            return

        try:
            from ..database.connection import GameCycleDatabase
            from ..database.media_coverage_api import MediaCoverageAPI
            from team_management.teams.team_loader import TeamDataLoader

            dynasty_id = context.get("dynasty_id")
            season = context.get("season", 2025)
            db_path = context.get("db_path", self._database_path)

            gc_db = GameCycleDatabase(db_path)
            team_loader = TeamDataLoader()

            try:
                media_api = MediaCoverageAPI(gc_db)

                # Week 25 for FA headlines
                week = 25

                # Sort signings by AAV to find biggest deals
                sorted_signings = sorted(signings, key=lambda s: s.get("aav", 0), reverse=True)

                # Generate headlines for top 3 signings by value
                for signing in sorted_signings[:3]:
                    team = team_loader.get_team_by_id(signing["team_id"])
                    team_name = team.full_name if team else f"Team {signing['team_id']}"
                    aav_millions = signing.get("aav", 0) / 1_000_000
                    years = signing.get("years", 1)

                    media_api.save_headline(
                        dynasty_id=dynasty_id,
                        season=season,
                        week=week,
                        headline_data={
                            'headline_type': 'SIGNING',
                            'headline': f"{team_name} Sign {signing['player_name']}",
                            'subheadline': f"{years}-year, ${aav_millions:.1f}M/year deal addresses key need",
                            'body_text': f"{team_name} have agreed to terms with {signing['player_name']} on a {years}-year contract worth ${aav_millions:.1f}M per year. The signing bolsters the roster heading into the {season} season.",
                            'sentiment': 'POSITIVE',
                            'priority': min(85, 60 + int(aav_millions)),
                            'team_ids': [signing["team_id"]],
                            'player_ids': [signing.get("player_id")],
                            'game_id': None,
                            'metadata': {'event_type': 'fa_signing', 'wave': wave, 'aav': signing.get("aav", 0)}
                        }
                    )

                # If wave 1, generate "market opens" headline
                if wave == 1 and len(signings) > 5:
                    media_api.save_headline(
                        dynasty_id=dynasty_id,
                        season=season,
                        week=week,
                        headline_data={
                            'headline_type': 'SIGNING',
                            'headline': f"Free Agency Frenzy: {len(signings)} Players Sign on Opening Day",
                            'subheadline': "Elite free agents find new homes as market opens",
                            'body_text': f"Free agency is officially underway with {len(signings)} players signing new contracts on the first day of the legal tampering period ending. Teams wasted no time addressing roster needs.",
                            'sentiment': 'HYPE',
                            'priority': 88,
                            'team_ids': [],
                            'player_ids': [],
                            'game_id': None,
                            'metadata': {'event_type': 'fa_market_open', 'wave': wave}
                        }
                    )

            finally:
                gc_db.close()

        except Exception as e:
            print(f"[OffseasonHandler] Failed to generate FA headlines: {e}")

    def _generate_trade_headlines(
        self,
        context: Dict[str, Any],
        executed_trades: List[Dict]
    ) -> None:
        """
        Generate and persist headlines for completed trades.

        Args:
            context: Execution context with dynasty_id, season, db_path
            executed_trades: List of executed trade results
        """
        if not executed_trades:
            return

        try:
            from ..database.connection import GameCycleDatabase
            from ..database.media_coverage_api import MediaCoverageAPI
            from team_management.teams.team_loader import TeamDataLoader

            dynasty_id = context.get("dynasty_id")
            season = context.get("season", 2025)
            db_path = context.get("db_path", self._database_path)

            gc_db = GameCycleDatabase(db_path)
            team_loader = TeamDataLoader()

            try:
                media_api = MediaCoverageAPI(gc_db)

                # Week 26 for trade headlines
                week = 26

                for trade in executed_trades[:5]:  # Limit to 5 trade headlines
                    team1_id = trade.get("team1_id")
                    team2_id = trade.get("team2_id")

                    team1 = team_loader.get_team_by_id(team1_id)
                    team2 = team_loader.get_team_by_id(team2_id)
                    team1_name = team1.full_name if team1 else f"Team {team1_id}"
                    team2_name = team2.full_name if team2 else f"Team {team2_id}"

                    # Get primary player names
                    team1_players = trade.get("team1_player_names", [])
                    team2_players = trade.get("team2_player_names", [])

                    if team1_players:
                        headline = f"{team1_name} Trade {team1_players[0]} to {team2_name}"
                        subheadline = f"{'Multiple pieces' if len(team1_players) > 1 or team2_players else 'Assets'} heading in return"
                    elif team2_players:
                        headline = f"{team1_name} Acquire {team2_players[0]} from {team2_name}"
                        subheadline = f"Trade reshapes rosters for both teams"
                    else:
                        headline = f"{team1_name} and {team2_name} Complete Trade"
                        subheadline = "Draft picks exchanged between teams"

                    media_api.save_headline(
                        dynasty_id=dynasty_id,
                        season=season,
                        week=week,
                        headline_data={
                            'headline_type': 'TRADE',
                            'headline': headline,
                            'subheadline': subheadline,
                            'body_text': f"{team1_name} and {team2_name} have agreed to a trade. This move signals both teams' intentions heading into the {season} season.",
                            'sentiment': 'NEUTRAL',
                            'priority': 75,
                            'team_ids': [team1_id, team2_id],
                            'player_ids': [],
                            'game_id': None,
                            'metadata': {'event_type': 'trade', 'trade_id': trade.get('trade_id')}
                        }
                    )

                # Summary headline if many trades
                if len(executed_trades) >= 5:
                    media_api.save_headline(
                        dynasty_id=dynasty_id,
                        season=season,
                        week=week,
                        headline_data={
                            'headline_type': 'TRADE',
                            'headline': f"Active Trade Period: {len(executed_trades)} Deals Completed",
                            'subheadline': "Teams reshape rosters ahead of training camp",
                            'body_text': f"The offseason trade market has been busy with {len(executed_trades)} trades completed league-wide. Teams continue to position themselves for the upcoming season.",
                            'sentiment': 'NEUTRAL',
                            'priority': 80,
                            'team_ids': [],
                            'player_ids': [],
                            'game_id': None,
                            'metadata': {'event_type': 'trade_summary', 'trade_count': len(executed_trades)}
                        }
                    )

            finally:
                gc_db.close()

        except Exception as e:
            print(f"[OffseasonHandler] Failed to generate trade headlines: {e}")