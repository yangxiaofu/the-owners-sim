"""
Draft Simulation Controller - Manages draft pick pacing and automation.

Handles:
- Speed control (manual, 1s, 3s, instant)
- Timer-based delays between AI picks
- Delegation mode (GM auto-picks for user team)
- Pick sequencing (single or batch processing)
- User turn detection and pause

Part of Milestone 14: Contract Valuation Engine - Draft UI enhancements.
"""

from typing import Optional, Dict, Any
import logging

from PySide6.QtCore import QObject, Signal, QTimer
from PySide6.QtWidgets import QApplication

from src.team_management.teams.team_loader import get_team_by_id


class DraftSimulationController(QObject):
    """
    Controls draft simulation pacing and state.

    Manages timer-based delays between picks, delegation mode,
    and user turn detection. Emits signals for UI updates.

    Speed Modes:
        0 = Manual (user advances each pick)
        1000 = 1 second between picks
        3000 = 3 seconds between picks
        -1 = Instant (no delay, but process events for UI responsiveness)

    Signals:
        pick_completed: Emitted after each pick with detailed result
        user_turn_reached: Emitted when user's team is on the clock
        draft_completed: Emitted when all picks are made
        simulation_started: Emitted when auto-simulation begins
        simulation_stopped: Emitted when auto-simulation is stopped
    """

    # Signals
    pick_completed = Signal(dict)  # Detailed pick result
    user_turn_reached = Signal()
    draft_completed = Signal()
    simulation_started = Signal()
    simulation_stopped = Signal()

    def __init__(
        self,
        draft_service,  # DraftService instance
        user_team_id: int,
        parent: Optional[QObject] = None
    ):
        """
        Initialize draft simulation controller.

        Args:
            draft_service: DraftService instance for pick processing
            user_team_id: User's team ID for turn detection
            parent: Optional Qt parent object
        """
        super().__init__(parent)

        self._draft_service = draft_service
        self._user_team_id = user_team_id
        self._logger = logging.getLogger(__name__)

        # State
        self._speed_ms = 0  # Default to manual
        self._is_delegated = False  # GM handles user picks when True
        self._is_simulating = False
        self._is_paused = False
        self._stop_requested = False

        # Last pick result for UI display
        self._last_pick_result: Optional[Dict[str, Any]] = None

        # Timer for delayed pick processing
        self._pick_timer = QTimer(self)
        self._pick_timer.setSingleShot(True)
        self._pick_timer.timeout.connect(self._process_next_pick_internal)

    # =========================================================================
    # Configuration
    # =========================================================================

    def set_speed(self, speed_ms: int) -> None:
        """
        Set simulation speed.

        Args:
            speed_ms: Delay between picks in milliseconds
                      0 = Manual mode
                      1000 = 1 second
                      3000 = 3 seconds
                      -1 = Instant (no delay)
        """
        self._speed_ms = speed_ms
        self._logger.info(f"Draft speed set to {speed_ms}ms")

    def set_delegation(self, delegate: bool) -> None:
        """
        Enable/disable GM delegation for user team.

        When enabled, GM handles all picks automatically (including user's).

        Args:
            delegate: True to delegate all picks to GM
        """
        self._is_delegated = delegate
        self._logger.info(f"Draft delegation {'enabled' if delegate else 'disabled'}")

    # =========================================================================
    # Manual Control
    # =========================================================================

    def process_next_pick(self) -> bool:
        """
        Process next pick manually (for manual mode).

        Returns:
            True if pick was processed, False if draft is complete
        """
        if self._is_simulating:
            self._logger.warning("Cannot process manual pick - simulation in progress")
            return False

        return self._process_single_pick()

    # =========================================================================
    # Automated Simulation
    # =========================================================================

    def simulate_to_user_pick(self) -> None:
        """
        Auto-simulate until user's turn, respecting speed setting.

        Processes AI picks with configured delay until:
        - User's team is on the clock (and delegation is off)
        - Draft is complete
        - Simulation is stopped/paused
        """
        if self._is_simulating:
            self._logger.warning("Simulation already in progress")
            return

        self._is_simulating = True
        self._is_paused = False
        self._stop_requested = False

        self.simulation_started.emit()
        self._logger.info("Starting simulation to user pick")

        # Start the simulation chain
        self._continue_simulation_to_user()

    def auto_complete_draft(self) -> None:
        """
        Complete entire draft automatically, respecting speed setting.

        Processes all remaining picks (including user's team if delegated).
        """
        if self._is_simulating:
            self._logger.warning("Simulation already in progress")
            return

        self._is_simulating = True
        self._is_paused = False
        self._stop_requested = False

        self.simulation_started.emit()
        self._logger.info("Starting auto-complete draft")

        # Start the simulation chain
        self._continue_simulation_complete()

    def pause(self) -> None:
        """Pause ongoing simulation."""
        if not self._is_simulating:
            self._logger.warning("No simulation in progress to pause")
            return

        self._is_paused = True
        self._pick_timer.stop()
        self._logger.info("Draft simulation paused")

    def resume(self) -> None:
        """Resume paused simulation."""
        if not self._is_simulating or not self._is_paused:
            self._logger.warning("No paused simulation to resume")
            return

        self._is_paused = False
        self._logger.info("Draft simulation resumed")

        # Continue from where we left off
        # Determine which mode we were in based on delegation state
        # (simulate_to_user_pick vs auto_complete_draft)
        # For simplicity, always continue in "complete" mode when resumed
        self._continue_simulation_complete()

    def stop(self) -> None:
        """Stop ongoing simulation."""
        if not self._is_simulating:
            return

        self._stop_requested = True
        self._is_simulating = False
        self._is_paused = False
        self._pick_timer.stop()

        self.simulation_stopped.emit()
        self._logger.info("Draft simulation stopped")

    # =========================================================================
    # State Queries
    # =========================================================================

    @property
    def is_simulating(self) -> bool:
        """Check if simulation is currently running."""
        return self._is_simulating

    @property
    def is_paused(self) -> bool:
        """Check if simulation is paused."""
        return self._is_paused

    @property
    def is_delegated(self) -> bool:
        """Check if delegation mode is enabled."""
        return self._is_delegated

    @property
    def speed_ms(self) -> int:
        """Get current speed setting in milliseconds."""
        return self._speed_ms

    @property
    def last_pick_result(self) -> Optional[Dict[str, Any]]:
        """Get the last completed pick result."""
        return self._last_pick_result

    # =========================================================================
    # Internal Implementation
    # =========================================================================

    def _process_single_pick(self) -> bool:
        """
        Process a single draft pick.

        Returns:
            True if pick was processed, False if draft complete
        """
        # Get current pick
        current_pick = self._draft_service.get_current_pick()

        if not current_pick:
            # Draft complete
            self._on_draft_complete()
            return False

        team_id = current_pick["team_id"]

        # Determine if this is user's pick
        is_user_pick = (team_id == self._user_team_id)

        # Process pick based on delegation setting
        if is_user_pick and not self._is_delegated:
            # User's turn and not delegated - stop simulation
            if self._is_simulating:
                self._is_simulating = False
                self.user_turn_reached.emit()
                self._logger.info(f"User turn reached - Pick #{current_pick['overall_pick']}")
            return False
        else:
            # AI pick or delegated user pick
            result = self._draft_service.process_ai_pick(
                team_id=team_id,
                pick_info=current_pick,
                draft_direction=None  # TODO: Support draft direction in delegation mode
            )

            if result.get("success"):
                # Enrich result with team name and college
                enriched_result = self._enrich_pick_result(result, team_id)
                self._last_pick_result = enriched_result

                # Emit signal with enriched data
                self.pick_completed.emit(enriched_result)

                self._logger.info(
                    f"Pick #{result['overall_pick']}: "
                    f"{enriched_result['team_name']} selects "
                    f"{result['player_name']} ({result['position']}) - "
                    f"{result['overall']} OVR"
                )
                return True
            else:
                # Pick failed
                error = result.get("error", "Unknown error")
                self._logger.error(f"Pick failed: {error}")
                self._on_draft_complete()  # Stop on error
                return False

    def _enrich_pick_result(self, result: Dict[str, Any], team_id: int) -> Dict[str, Any]:
        """
        Enrich pick result with team name and map keys for AIPickDisplayWidget.

        Args:
            result: Raw pick result from DraftService
            team_id: Team that made the pick

        Returns:
            Enriched result dict with normalized keys for UI display
        """
        enriched = result.copy()

        # Get team name
        team = get_team_by_id(team_id)
        enriched["team_name"] = team.full_name if team else f"Team {team_id}"

        # Map DraftService keys to AIPickDisplayWidget expected keys
        # player_name -> prospect_name
        enriched["prospect_name"] = result.get("player_name", "Unknown Player")
        # overall_pick -> pick_number
        enriched["pick_number"] = result.get("overall_pick", 0)
        # pick -> pick_in_round
        enriched["pick_in_round"] = result.get("pick", 0)

        # Keep college (now returned from DraftService.make_draft_pick)
        enriched["college"] = result.get("college", "Unknown")

        # Placeholder fields for future enhancement
        enriched["needs_met"] = []  # TODO: Add from draft evaluation
        enriched["reasoning"] = ""  # TODO: Add from draft evaluation

        return enriched

    def _continue_simulation_to_user(self) -> None:
        """
        Continue simulation until user's turn (internal).

        Called recursively via timer to process picks one at a time
        with configured delay until user's turn is reached.
        """
        if self._stop_requested or self._is_paused:
            return

        # Check if we're at user's turn
        current_pick = self._draft_service.get_current_pick()

        if not current_pick:
            # Draft complete
            self._on_draft_complete()
            return

        is_user_turn = (current_pick["team_id"] == self._user_team_id)

        if is_user_turn and not self._is_delegated:
            # Stop at user's turn
            self._is_simulating = False
            self.user_turn_reached.emit()
            self._logger.info("Simulation stopped at user's turn")
            return

        # Process this pick and continue
        success = self._process_single_pick()

        if not success:
            # Draft complete or error
            return

        # Schedule next pick with delay
        self._schedule_next_pick(self._continue_simulation_to_user)

    def _continue_simulation_complete(self) -> None:
        """
        Continue simulation to completion (internal).

        Called recursively via timer to process all remaining picks
        with configured delay.
        """
        if self._stop_requested or self._is_paused:
            return

        # Check if draft is complete
        current_pick = self._draft_service.get_current_pick()

        if not current_pick:
            # Draft complete
            self._on_draft_complete()
            return

        # Process this pick
        success = self._process_single_pick()

        if not success:
            # Draft complete or error
            return

        # Schedule next pick with delay
        self._schedule_next_pick(self._continue_simulation_complete)

    def _schedule_next_pick(self, continuation_fn) -> None:
        """
        Schedule next pick based on speed setting.

        Args:
            continuation_fn: Function to call for next pick
        """
        if self._speed_ms == 0:
            # Manual mode fallback - use instant instead of stopping
            self._logger.info("Manual mode during simulation - using instant mode")
            self._speed_ms = -1  # Switch to instant
            # Fall through to instant mode handling

        if self._speed_ms == -1:
            # Instant mode - process events to keep UI responsive
            QApplication.processEvents()
            continuation_fn()

        else:
            # Timed mode - use QTimer for delay
            self._pick_timer.timeout.disconnect()  # Clear previous connections
            self._pick_timer.timeout.connect(continuation_fn)
            self._pick_timer.start(self._speed_ms)

    def _process_next_pick_internal(self) -> None:
        """
        Internal slot for timer-based pick processing.

        This is connected to the timer timeout signal and should
        not be called directly. Use _schedule_next_pick instead.
        """
        # This is a fallback - should normally use continuation functions
        self._logger.warning("Timer-based pick processing called without continuation")

    def _on_draft_complete(self) -> None:
        """Handle draft completion."""
        print("=" * 60)
        print("[DraftSimulationController] _on_draft_complete() - EMITTING draft_completed SIGNAL")
        print("=" * 60)

        self._is_simulating = False
        self._is_paused = False
        self._pick_timer.stop()

        self.draft_completed.emit()
        self._logger.info("Draft complete - all picks made")
        print("[DraftSimulationController] draft_completed signal emitted")
