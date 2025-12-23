"""
Free Agency UI Controller - Handles wave-based FA UI logic.

Part of Milestone 8: Free Agency Depth - Tollgate 4.

Separation of Concerns: Extracted from StageUIController for:
- Testability (inject mock backend)
- Single Responsibility (only FA logic)
- DRY (follows FAWaveExecutor pattern from Tollgate 3)
"""

from typing import Dict, Any, List, Optional

from PySide6.QtCore import QObject, Signal


class FreeAgencyUIController(QObject):
    """
    UI Controller for wave-based Free Agency.

    Signals:
        execution_complete: Emitted when wave action execution completes (result_dict)
        error_occurred: Emitted when wave action execution fails (error_msg)
    """

    # Signals for direct wave button execution
    execution_complete = Signal(dict)  # result dict
    error_occurred = Signal(str)       # error message

    def __init__(
        self,
        backend,  # BackendStageController
        dynasty_id: str,
        season: int,
        user_team_id: int,
        db_path: str = None,
        parent: Optional[QObject] = None
    ):
        """
        Initialize FA UI controller with dependencies.

        Args:
            backend: BackendStageController instance (injectable for testing)
            dynasty_id: Current dynasty ID
            season: Current season year
            user_team_id: User's team ID
            db_path: Database path for context building
            parent: Optional Qt parent
        """
        super().__init__(parent)
        self._backend = backend
        self._dynasty_id = dynasty_id
        self._season = season
        self._user_team_id = user_team_id
        self._db_path = db_path

        # Wave action state
        self._wave_actions: Dict[str, List] = {
            "submit_offers": [],
            "withdraw_offers": [],
        }
        self._wave_control: Dict[str, bool] = {
            "advance_day": False,
            "advance_wave": False,
            "enable_post_draft": False,
        }

        # Milestone 10: GM-driven FA guidance and proposals
        self._fa_guidance = None  # FAGuidance object from pre-FA dialog
        self._gm_archetype = None  # GMArchetype for proposal generation

        # Cap-clearing trade proposals (keyed by proposal_id)
        self._cap_clearing_trade_proposals: Dict[str, Any] = {}

        # View reference (optional, for refresh)
        self._view = None

    # -------------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------------

    @property
    def dynasty_id(self) -> str:
        """Get dynasty ID."""
        return self._dynasty_id

    @property
    def season(self) -> int:
        """Get season year."""
        return self._season

    @property
    def user_team_id(self) -> int:
        """Get user team ID."""
        return self._user_team_id

    # -------------------------------------------------------------------------
    # View Connection
    # -------------------------------------------------------------------------

    def connect_view(self, fa_view) -> None:
        """
        Connect to FreeAgencyView signals.

        Called when view supports wave signals (Tollgate 5+).
        Uses hasattr checks for backward compatibility with views
        that don't have wave signals yet.

        Args:
            fa_view: FreeAgencyView instance
        """
        self._view = fa_view

        # Connect offer signals if available
        if hasattr(fa_view, 'offer_submitted'):
            fa_view.offer_submitted.connect(self.on_offer_submitted)
        if hasattr(fa_view, 'offer_withdrawn'):
            fa_view.offer_withdrawn.connect(self.on_offer_withdrawn)

        # Connect wave control signals if available
        if hasattr(fa_view, 'process_day_requested'):
            fa_view.process_day_requested.connect(self.on_process_day)
        if hasattr(fa_view, 'process_wave_requested'):
            fa_view.process_wave_requested.connect(self.on_process_wave)

        # Connect trade search signal (cap-clearing trades)
        if hasattr(fa_view, 'trade_search_requested'):
            fa_view.trade_search_requested.connect(self.on_trade_search_requested)

    # -------------------------------------------------------------------------
    # Signal Handlers (accumulate actions)
    # -------------------------------------------------------------------------

    def on_offer_submitted(self, player_id: int, offer_data: Dict[str, Any]) -> None:
        """
        Handle offer submission from view.

        Accumulates offer in pending list until execute() is called.
        Also calculates Year-1 cap hit using CapHelper (SSOT) and updates
        the view's pending cap commit.

        Args:
            player_id: Player receiving the offer
            offer_data: Dict with aav, years, guaranteed, signing_bonus
        """
        aav = offer_data.get("aav", 0)
        years = offer_data.get("years", 1)
        signing_bonus = offer_data.get("signing_bonus", 0)

        offer = {
            "player_id": player_id,
            "aav": aav,
            "years": years,
            "guaranteed": offer_data.get("guaranteed", 0),
            "signing_bonus": signing_bonus,
        }
        self._wave_actions["submit_offers"].append(offer)

        # Calculate Year-1 cap hit using CapHelper (SSOT) and update view
        if self._view and self._db_path:
            try:
                from game_cycle.services.cap_helper import CapHelper
                # Offseason uses season + 1 for cap calculations
                cap_helper = CapHelper(self._db_path, self._dynasty_id, self._season + 1)
                total_value = aav * years
                year1_cap_hit = cap_helper.calculate_signing_cap_hit(
                    total_value=total_value,
                    signing_bonus=signing_bonus,
                    years=years
                )
                self._view.update_pending_cap_commit(player_id, year1_cap_hit)
            except Exception as e:
                # Fallback: keep the AAV estimate set by the view
                import logging
                logging.getLogger(__name__).debug(f"Could not calculate Year-1 cap hit: {e}")

    def on_offer_withdrawn(self, offer_id: int) -> None:
        """
        Handle offer withdrawal from view.

        Accumulates withdrawal in pending list until execute() is called.

        Args:
            offer_id: ID of offer to withdraw
        """
        self._wave_actions["withdraw_offers"].append(offer_id)

    def on_process_day(self) -> None:
        """Handle Process Day button - execute immediately."""
        self._wave_control["advance_day"] = True
        self._execute_wave_action()

    def on_process_wave(self) -> None:
        """
        Handle Process Wave button - smart routing based on wave state.

        - If days remain: advance_day (process next day)
        - If wave complete: advance_wave (resolve offers, move to next wave/stage)
        """
        # Get current wave state to determine action
        preview = self._backend.get_stage_preview()
        wave_state = preview.get("wave_state", {})

        current_day = wave_state.get("current_day", 1)
        days_in_wave = wave_state.get("days_in_wave", 1)
        wave_complete = wave_state.get("wave_complete", False)

        # Smart routing: advance day if incomplete, advance wave if complete
        if wave_complete or current_day >= days_in_wave:
            # Wave is complete or on last day → try to advance wave
            self._wave_control["advance_wave"] = True
        else:
            # Days remain → advance to next day
            self._wave_control["advance_day"] = True

        self._execute_wave_action()

    def on_enable_post_draft(self) -> None:
        """Handle request to enable post-draft wave after draft completes."""
        self._wave_control["enable_post_draft"] = True

    # -------------------------------------------------------------------------
    # Execution
    # -------------------------------------------------------------------------

    def build_context(self, base_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build FA-specific context for backend execution.

        Adds wave actions, control flags, and GM guidance to base context.

        Args:
            base_context: Base context with dynasty_id, season, etc.

        Returns:
            Context with fa_wave_actions, wave_control, fa_guidance, and gm_archetype added
        """
        context = base_context.copy()
        context["fa_wave_actions"] = {
            "submit_offers": self._wave_actions["submit_offers"].copy(),
            "withdraw_offers": self._wave_actions["withdraw_offers"].copy(),
        }
        context["wave_control"] = self._wave_control.copy()

        # Milestone 10: Add GM guidance and archetype for proposal generation
        if self._fa_guidance:
            context["fa_guidance"] = self._fa_guidance
        if self._gm_archetype:
            context["gm_archetype"] = self._gm_archetype

        return context

    def execute(self, base_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute FA action via backend.

        Builds context with wave actions, calls backend, clears pending.

        Args:
            base_context: Base context from parent controller

        Returns:
            Execution result dict with stage_name, events, success, can_advance
        """
        context = self.build_context(base_context)
        result = self._backend.execute_current_stage(extra_context=context)

        # Clear pending actions after execution
        self.clear_pending()

        return {
            "stage_name": result.stage.display_name,
            "games_played": result.games_played,
            "events_processed": result.events_processed,
            "errors": result.errors,
            "success": result.success,
            "can_advance": result.can_advance,
        }

    def clear_pending(self) -> None:
        """Clear pending wave actions after execution."""
        self._wave_actions = {
            "submit_offers": [],
            "withdraw_offers": [],
        }
        self._wave_control = {
            "advance_day": False,
            "advance_wave": False,
            "enable_post_draft": False,
        }

    def _execute_wave_action(self) -> None:
        """
        Execute wave action immediately without waiting for main button.

        Builds context, executes via backend, emits signals for result/error.
        """
        try:
            # Build execution context
            context = {
                "dynasty_id": self._dynasty_id,
                "season": self._season,
                "user_team_id": self._user_team_id,
            }
            if self._db_path:
                context["db_path"] = self._db_path

            context = self.build_context(context)

            # Execute via backend
            result = self._backend.execute_current_stage(extra_context=context)

            # Clear pending actions
            self.clear_pending()

            # Build result dict - include handler_data for wave results
            result_dict = {
                "stage_name": result.stage.display_name,
                "events_processed": result.events_processed,
                "success": result.success,
                "can_advance": result.can_advance,
            }

            # Merge in handler_data (includes user_signings, user_lost_bids, wave_advanced, etc.)
            if hasattr(result, 'handler_data') and result.handler_data:
                result_dict.update(result.handler_data)

            # Emit completion signal
            self.execution_complete.emit(result_dict)

        except Exception as e:
            # Emit error signal
            self.error_occurred.emit(str(e))

    # -------------------------------------------------------------------------
    # View Refresh
    # -------------------------------------------------------------------------

    def refresh_view(self, preview: Dict[str, Any]) -> None:
        """
        Refresh FA view with wave state from preview.

        Detects wave changes and clears pending offer state only when
        wave actually advances. Preserves pending state during day progression.

        Args:
            preview: Stage preview from backend
        """
        if not self._view:
            return

        # Get current wave before update
        previous_wave = self._view.current_wave if hasattr(self._view, 'current_wave') else -1

        # Get new wave state from preview
        wave_state = preview.get("wave_state", {})
        current_wave = wave_state.get("current_wave", 0)

        # Update wave info if view supports it
        if wave_state and hasattr(self._view, 'set_wave_info'):
            self._view.set_wave_info(
                wave=current_wave,
                wave_name=wave_state.get("wave_name", ""),
                day=wave_state.get("current_day", 1),
                days_total=wave_state.get("days_in_wave", 1),
            )

        # Clear pending state ONLY if wave changed (not just day progression)
        if previous_wave != -1 and current_wave != previous_wave:
            if hasattr(self._view, 'clear_pending_state'):
                self._view.clear_pending_state()

        # Update free agents list
        free_agents = preview.get("free_agents", [])
        if free_agents and hasattr(self._view, 'set_free_agents'):
            self._view.set_free_agents(free_agents)

        # Update pending offers count
        pending = wave_state.get("pending_offers", 0)
        if hasattr(self._view, 'set_pending_offers_count'):
            self._view.set_pending_offers_count(pending)

        # Update cap data
        cap_data = preview.get("cap_data", {})
        if cap_data and hasattr(self._view, 'set_cap_data'):
            self._view.set_cap_data(cap_data)

    # -------------------------------------------------------------------------
    # State Queries (for testing/debugging)
    # -------------------------------------------------------------------------

    def get_wave_actions(self) -> Dict[str, List]:
        """
        Get copy of pending wave actions.

        Returns:
            Dict with submit_offers and withdraw_offers lists (copies)
        """
        return {
            "submit_offers": self._wave_actions["submit_offers"].copy(),
            "withdraw_offers": self._wave_actions["withdraw_offers"].copy(),
        }

    def get_wave_control(self) -> Dict[str, bool]:
        """
        Get copy of wave control flags.

        Returns:
            Dict with advance_day, advance_wave, enable_post_draft flags
        """
        return self._wave_control.copy()

    def has_pending_actions(self) -> bool:
        """
        Check if any actions are pending.

        Returns:
            True if there are pending offers, withdrawals, or control flags
        """
        return (
            len(self._wave_actions["submit_offers"]) > 0 or
            len(self._wave_actions["withdraw_offers"]) > 0 or
            any(self._wave_control.values())
        )

    # -------------------------------------------------------------------------
    # Milestone 10: GM-Driven FA Guidance & Proposals
    # -------------------------------------------------------------------------

    def set_fa_guidance(self, guidance) -> None:
        """
        Set the owner's FA guidance for GM proposal generation.

        Args:
            guidance: FAGuidance object from pre-FA dialog
        """
        self._fa_guidance = guidance
        print(f"[DEBUG FreeAgencyUIController] FA guidance set: {guidance.philosophy.value if guidance else None}")

    def set_gm_archetype(self, archetype) -> None:
        """
        Set the GM archetype for proposal generation.

        Args:
            archetype: GMArchetype object
        """
        self._gm_archetype = archetype
        print(f"[DEBUG FreeAgencyUIController] GM archetype set: {archetype.name if archetype else None}")

    def get_fa_guidance(self):
        """Get current FA guidance (for testing/debugging)."""
        return self._fa_guidance

    def has_fa_guidance(self) -> bool:
        """Check if FA guidance has been set."""
        return self._fa_guidance is not None

    # -------------------------------------------------------------------------
    # Cap-Clearing Trade Search (for unaffordable GM signing proposals)
    # -------------------------------------------------------------------------

    def on_trade_search_requested(self, proposal_id: str, cap_shortage: int) -> None:
        """
        Handle trade search request from unaffordable GM signing proposal.

        Flow:
        1. Get proposal details for context
        2. Generate cap-clearing trades using TradeProposalGenerator
        3. Show TradeSearchDialog with results
        4. If user approves trade, add to pending proposals

        Args:
            proposal_id: ID of the signing proposal we can't afford
            cap_shortage: Amount over cap (positive number)
        """
        # Get proposal for context
        proposal = self._get_proposal_by_id(proposal_id)
        if not proposal:
            print(f"[ERROR] Could not find proposal {proposal_id}")
            return

        # Extract player info for dialog header
        details = proposal.get("details", {})
        player_info = {
            "name": details.get("player_name", "Unknown"),
            "position": details.get("position", ""),
            "aav": details.get("contract", {}).get("aav", 0)
        }

        # Generate cap-clearing trades
        trade_options = self._generate_cap_clearing_trades(cap_shortage)

        # Show dialog
        from game_cycle_ui.dialogs.trade_search_dialog import TradeSearchDialog

        dialog = TradeSearchDialog(
            parent=self._view,
            player_info=player_info,
            cap_shortage=cap_shortage,
            trade_options=trade_options
        )

        # Connect trade selection signal
        dialog.trade_selected.connect(
            lambda trade_id: self._on_cap_clearing_trade_selected(trade_id, proposal_id)
        )

        # Show dialog (modal)
        dialog.exec()

    def _generate_cap_clearing_trades(self, min_cap_to_clear: int) -> List[Dict]:
        """
        Generate cap-clearing trade proposals.

        Uses TradeProposalGenerator with owner directives to find AI-accepted
        trades that free up cap space.

        Args:
            min_cap_to_clear: Target cap savings (for context/logging)

        Returns:
            List of trade proposal dicts for UI display
        """
        from game_cycle.services.proposal_generators.trade_generator import (
            TradeProposalGenerator
        )
        from game_cycle.models.owner_directives import OwnerDirectives

        # Get owner directives (need for protected players list)
        directives = self._get_owner_directives()

        # Create generator
        generator = TradeProposalGenerator(
            db_path=self._db_path,
            dynasty_id=self._dynasty_id,
            season=self._season,
            team_id=self._user_team_id,
            directives=directives
        )

        # Generate proposals
        try:
            proposals = generator.generate_cap_clearing_trades(
                min_cap_to_clear=min_cap_to_clear,
                max_proposals=5
            )

            # Store proposals in memory for later retrieval
            self._cap_clearing_trade_proposals.clear()
            for proposal in proposals:
                self._cap_clearing_trade_proposals[proposal.proposal_id] = proposal

            # Convert to dict format for UI
            return [p.to_dict() for p in proposals]

        except Exception as e:
            print(f"[ERROR] Failed to generate cap-clearing trades: {e}")
            return []

    def _on_cap_clearing_trade_selected(self, trade_proposal_id: str, signing_proposal_id: str):
        """
        Handle user approving a cap-clearing trade from dialog.

        Adds the trade to pending proposals for owner review.
        Maintains workflow consistency.

        Args:
            trade_proposal_id: ID of approved trade proposal
            signing_proposal_id: Original signing proposal (for context)
        """
        from game_cycle.database.proposal_api import ProposalAPI
        from game_cycle.database.connection import GameCycleDatabase
        from game_cycle.models.proposal_enums import ProposalStatus

        try:
            # Find the trade proposal from in-memory storage
            trade_proposal = self._cap_clearing_trade_proposals.get(trade_proposal_id)

            if not trade_proposal:
                print(f"[ERROR] Trade proposal {trade_proposal_id} not found in memory")
                return

            print(f"[INFO] Trade {trade_proposal_id} approved for cap clearing")
            print(f"[INFO] This will help sign player from proposal {signing_proposal_id}")

            # Set status to PENDING so it appears in GM proposals
            trade_proposal.status = ProposalStatus.PENDING

            # Persist to database
            db = GameCycleDatabase(self._db_path)
            proposal_api = ProposalAPI(db)

            proposal_api.create_proposal(trade_proposal)

            print(f"[SUCCESS] Trade proposal {trade_proposal_id} persisted to database")

            # Refresh GM proposals view if available
            if self._view and hasattr(self._view, 'refresh_gm_proposals'):
                self._view.refresh_gm_proposals()
                print("[SUCCESS] GM proposals view refreshed")

            # Clean up the in-memory proposal (it's now in DB)
            del self._cap_clearing_trade_proposals[trade_proposal_id]

        except Exception as e:
            print(f"[ERROR] Failed to approve cap-clearing trade: {e}")
            import traceback
            traceback.print_exc()

    def _get_proposal_by_id(self, proposal_id: str) -> Optional[Dict]:
        """
        Get a proposal by ID from the database.

        Args:
            proposal_id: Proposal ID to find

        Returns:
            Proposal dict or None if not found
        """
        from game_cycle.database.proposal_api import ProposalAPI
        from game_cycle.database.connection import GameCycleDatabase

        try:
            db = GameCycleDatabase(self._db_path)
            proposal_api = ProposalAPI(db)

            proposal = proposal_api.get_proposal(
                dynasty_id=self._dynasty_id,
                team_id=self._user_team_id,
                proposal_id=proposal_id
            )

            if proposal:
                return proposal.to_dict()

            return None

        except Exception as e:
            print(f"[ERROR] Failed to get proposal {proposal_id}: {e}")
            return None

    def _get_owner_directives(self) -> 'OwnerDirectives':
        """
        Get owner directives from database.

        Returns:
            OwnerDirectives object (uses defaults if not found)
        """
        from game_cycle.models.owner_directives import OwnerDirectives
        from game_cycle.database.connection import GameCycleDatabase
        import sqlite3

        try:
            db = GameCycleDatabase(self._db_path)
            conn = db.get_connection()

            cursor = conn.execute(
                """
                SELECT team_philosophy, budget_stance, protected_player_ids,
                       expendable_player_ids, priority_positions
                FROM owner_directives
                WHERE dynasty_id = ? AND team_id = ? AND season = ?
                """,
                (self._dynasty_id, self._user_team_id, self._season)
            )

            row = cursor.fetchone()

            if row:
                import json
                return OwnerDirectives(
                    team_philosophy=row[0] or "maintain",
                    budget_stance=row[1] or "moderate",
                    protected_player_ids=json.loads(row[2]) if row[2] else [],
                    expendable_player_ids=json.loads(row[3]) if row[3] else [],
                    priority_positions=json.loads(row[4]) if row[4] else []
                )
            else:
                # Return defaults if not found
                return OwnerDirectives(
                    team_philosophy="maintain",
                    budget_stance="moderate",
                    protected_player_ids=[],
                    expendable_player_ids=[],
                    priority_positions=[]
                )

        except Exception as e:
            print(f"[ERROR] Failed to get owner directives: {e}")
            # Return defaults on error
            from game_cycle.models.owner_directives import OwnerDirectives
            return OwnerDirectives(
                team_philosophy="maintain",
                budget_stance="moderate",
                protected_player_ids=[],
                expendable_player_ids=[],
                priority_positions=[]
            )