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

    # -------------------------------------------------------------------------
    # Signal Handlers (accumulate actions)
    # -------------------------------------------------------------------------

    def on_offer_submitted(self, player_id: int, offer_data: Dict[str, Any]) -> None:
        """
        Handle offer submission from view.

        Accumulates offer in pending list until execute() is called.

        Args:
            player_id: Player receiving the offer
            offer_data: Dict with aav, years, guaranteed, signing_bonus
        """
        offer = {
            "player_id": player_id,
            "aav": offer_data.get("aav", 0),
            "years": offer_data.get("years", 1),
            "guaranteed": offer_data.get("guaranteed", 0),
            "signing_bonus": offer_data.get("signing_bonus", 0),
        }
        self._wave_actions["submit_offers"].append(offer)

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