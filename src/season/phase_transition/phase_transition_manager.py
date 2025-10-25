"""
Phase Transition Manager

Coordinates phase transition detection and execution with clear separation of concerns.
"""

from typing import Optional, Dict, Callable, Any

# Use src. prefix to avoid collision with Python builtin calendar
try:
    from calendar.phase_state import PhaseState
    from calendar.season_phase_tracker import SeasonPhase
except ModuleNotFoundError:
    # Fallback for test environment
    from src.calendar.phase_state import PhaseState
    from src.calendar.season_phase_tracker import SeasonPhase

from .models import PhaseTransition, TransitionFailedError
from .phase_completion_checker import PhaseCompletionChecker


class PhaseTransitionManager:
    """
    Manages NFL season phase transitions.

    Separates transition detection (pure logic) from execution (side effects).
    This separation enables unit testing without database dependencies.

    The manager coordinates between:
    - PhaseState: Current phase (shared mutable state)
    - PhaseCompletionChecker: Pure logic for detecting when transitions should occur
    - Transition Handlers: Side-effectful operations for each transition type

    Example:
        # Setup
        phase_state = PhaseState(SeasonPhase.REGULAR_SEASON)
        checker = PhaseCompletionChecker(database_api)
        handlers = {
            "regular_to_playoffs": regular_to_playoffs_handler,
            "playoffs_to_offseason": playoffs_to_offseason_handler,
        }

        manager = PhaseTransitionManager(phase_state, checker, handlers)

        # Check if transition needed (no side effects)
        transition = manager.check_transition_needed()

        # Execute transition if needed
        if transition:
            manager.execute_transition(transition)
    """

    def __init__(
        self,
        phase_state: PhaseState,
        completion_checker: PhaseCompletionChecker,
        transition_handlers: Dict[str, Callable[[PhaseTransition], None]]
    ):
        """
        Initialize manager with injected dependencies.

        Args:
            phase_state: Shared phase state object (single source of truth)
            completion_checker: Checker for determining if transitions should occur
            transition_handlers: Map of transition names to handler functions
                Format: {"transition_name": handler_function}
                Handler signature: handler(transition: PhaseTransition) -> None
        """
        self.phase_state = phase_state
        self.completion_checker = completion_checker
        self.handlers = transition_handlers

        # Track previous phase for rollback support
        self._previous_phase: Optional[SeasonPhase] = None

    def check_transition_needed(self) -> Optional[PhaseTransition]:
        """
        Check if phase transition should occur (NO SIDE EFFECTS).

        This method performs pure logic - it only reads state and determines
        if a transition should happen. It does not modify any state or trigger
        any side effects.

        Returns:
            PhaseTransition if transition needed, None otherwise

        Example:
            # Safe to call repeatedly - no side effects
            transition = manager.check_transition_needed()
            if transition:
                print(f"Transition ready: {transition}")
                # Can decide whether to execute or not
        """
        current_phase = self.phase_state.phase

        # Check completion based on current phase
        if current_phase == SeasonPhase.REGULAR_SEASON:
            if self.completion_checker.is_regular_season_complete():
                return PhaseTransition(
                    from_phase=SeasonPhase.REGULAR_SEASON,
                    to_phase=SeasonPhase.PLAYOFFS,
                    trigger="regular_season_complete",
                    metadata={}
                )

        elif current_phase == SeasonPhase.PLAYOFFS:
            if self.completion_checker.is_playoffs_complete():
                return PhaseTransition(
                    from_phase=SeasonPhase.PLAYOFFS,
                    to_phase=SeasonPhase.OFFSEASON,
                    trigger="playoffs_complete",
                    metadata={}
                )

        elif current_phase == SeasonPhase.OFFSEASON:
            if self.completion_checker.is_offseason_complete():
                return PhaseTransition(
                    from_phase=SeasonPhase.OFFSEASON,
                    to_phase=SeasonPhase.PRESEASON,
                    trigger="offseason_complete",
                    metadata={}
                )

        # No transition needed
        return None

    def execute_transition(self, transition: PhaseTransition) -> bool:
        """
        Execute phase transition using appropriate handler.

        This method has side effects:
        - Calls transition handlers (which may modify database, create events, etc.)
        - Updates phase_state to new phase

        Supports automatic rollback if transition fails.

        Args:
            transition: The transition to execute

        Returns:
            True if successful

        Raises:
            TransitionFailedError: If transition execution fails

        Example:
            transition = PhaseTransition(
                from_phase=SeasonPhase.REGULAR_SEASON,
                to_phase=SeasonPhase.PLAYOFFS,
                trigger="regular_season_complete"
            )

            try:
                manager.execute_transition(transition)
                print("Transition successful!")
            except TransitionFailedError as e:
                print(f"Transition failed: {e}")
                # Phase automatically rolled back to previous state
        """
        # Validate transition is from current phase
        if transition.from_phase != self.phase_state.phase:
            raise TransitionFailedError(
                f"Transition from_phase ({transition.from_phase.value}) does not match "
                f"current phase ({self.phase_state.phase.value})"
            )

        # Store previous phase for rollback
        self._previous_phase = self.phase_state.phase

        # Get handler key based on transition
        handler_key = self._get_handler_key(transition)

        if handler_key not in self.handlers:
            raise TransitionFailedError(
                f"No handler registered for transition: {handler_key}"
            )

        try:
            # Execute the transition handler
            handler = self.handlers[handler_key]
            handler(transition)

            # Update phase state (this notifies all listeners)
            self.phase_state.phase = transition.to_phase

            return True

        except Exception as e:
            # Rollback phase on failure
            self._rollback_phase()

            raise TransitionFailedError(
                f"Transition execution failed: {handler_key}",
                original_exception=e
            )

    def _get_handler_key(self, transition: PhaseTransition) -> str:
        """
        Get handler key for a transition.

        Args:
            transition: The transition

        Returns:
            Handler key string (e.g., "regular_to_playoffs")
        """
        from_phase = transition.from_phase.value
        to_phase = transition.to_phase.value
        return f"{from_phase}_to_{to_phase}"

    def _rollback_phase(self) -> None:
        """
        Rollback phase to previous state.

        This is called automatically when a transition fails.
        """
        if self._previous_phase is not None:
            self.phase_state.phase = self._previous_phase
            self._previous_phase = None

    def register_handler(
        self,
        from_phase: SeasonPhase,
        to_phase: SeasonPhase,
        handler: Callable[[PhaseTransition], None]
    ) -> None:
        """
        Register a transition handler dynamically.

        Args:
            from_phase: Phase transitioning from
            to_phase: Phase transitioning to
            handler: Handler function for this transition

        Example:
            def custom_handler(transition: PhaseTransition) -> None:
                print(f"Handling: {transition}")
                # Do transition work...

            manager.register_handler(
                SeasonPhase.REGULAR_SEASON,
                SeasonPhase.PLAYOFFS,
                custom_handler
            )
        """
        handler_key = f"{from_phase.value}_to_{to_phase.value}"
        self.handlers[handler_key] = handler

    def get_registered_handlers(self) -> Dict[str, Callable[[PhaseTransition], None]]:
        """
        Get all registered handlers.

        Returns:
            Copy of handlers dictionary
        """
        return self.handlers.copy()

    def has_handler(self, from_phase: SeasonPhase, to_phase: SeasonPhase) -> bool:
        """
        Check if handler exists for a transition.

        Args:
            from_phase: Phase transitioning from
            to_phase: Phase transitioning to

        Returns:
            True if handler exists
        """
        handler_key = f"{from_phase.value}_to_{to_phase.value}"
        return handler_key in self.handlers
