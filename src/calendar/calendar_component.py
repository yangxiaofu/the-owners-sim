"""
Calendar Component

Main calendar management component providing thread-safe date advancement
and comprehensive state tracking for the NFL simulation system.
"""

import threading
from datetime import date as PyDate
from typing import Union, Dict, Any, Optional, List

from .date_models import Date, DateAdvanceResult, normalize_date
from .calendar_exceptions import (
    InvalidDaysException,
    InvalidDateException,
    CalendarStateException
)
from .season_phase_tracker import (
    SeasonPhaseTracker, SeasonPhase, GameCompletionEvent, PhaseTransition
)
from .season_milestones import (
    SeasonMilestoneCalculator, SeasonMilestone, create_season_milestone_calculator
)
from .calendar_notifications import CalendarEventPublisher


class CalendarComponent:
    """
    Thread-safe calendar component for managing simulation date state.

    Provides date advancement capabilities with comprehensive validation,
    statistics tracking, and concurrent operation support.
    """

    # Constants
    MIN_ADVANCE_DAYS = 1
    MAX_ADVANCE_DAYS = 365

    def __init__(self, start_date: Union[Date, PyDate, str], season_year: Optional[int] = None,
                 publisher: Optional[CalendarEventPublisher] = None,
                 phase_state: Optional['PhaseState'] = None,
                 database_api: Optional[Any] = None,
                 dynasty_id: str = "default"):
        """
        Initialize calendar component.

        Args:
            start_date: Starting date (Date object, Python date, or string)
            season_year: NFL season year (e.g., 2024 for 2024-25 season)
            publisher: Optional event publisher for calendar notifications
            phase_state: Optional shared PhaseState object for phase tracking
            database_api: Optional database API for event-based phase detection
            dynasty_id: Dynasty context for database queries

        Raises:
            InvalidDateException: If start_date is invalid
        """
        try:
            self._current_date = normalize_date(start_date)
        except ValueError as e:
            raise InvalidDateException(date_string=str(start_date), original_error=e)

        self._creation_date = self._current_date
        self._lock = threading.Lock()

        # Statistics tracking
        self._total_days_advanced = 0
        self._advancement_count = 0
        self._max_single_advance = 0

        # Season phase tracking
        if season_year is None:
            season_year = self._current_date.year

        # Use shared phase_state if provided, otherwise create SeasonPhaseTracker
        self._external_phase_state = phase_state
        if phase_state is None:
            # Backward compatibility: create internal phase tracker with event-based detection
            self._season_phase_tracker = SeasonPhaseTracker(
                self._current_date,
                season_year,
                database_api=database_api,
                dynasty_id=dynasty_id
            )
        else:
            # Use external phase state (preferred for new code)
            self._season_phase_tracker = None  # Don't need tracker for phase

        self._milestone_calculator = create_season_milestone_calculator()
        self._season_milestones: List[SeasonMilestone] = []

        # Optional event publisher for notifications
        self._publisher: Optional[CalendarEventPublisher] = publisher

        # Initialize milestones for the season
        self._update_season_milestones()

    def advance(self, days: Union[int, float]) -> DateAdvanceResult:
        """
        Advance calendar by specified number of days.

        Args:
            days: Number of days to advance (must be positive integer)

        Returns:
            DateAdvanceResult with advancement details

        Raises:
            InvalidDaysException: If days is invalid
            CalendarStateException: If internal state is corrupted
        """
        # Validate days parameter
        self._validate_days_parameter(days)
        days = int(days)  # Convert to int after validation

        with self._lock:
            try:
                start_date = self._current_date

                # Perform date advancement
                end_date = start_date.add_days(days)

                # Update internal state
                self._current_date = end_date
                self._total_days_advanced += days
                self._advancement_count += 1
                self._max_single_advance = max(self._max_single_advance, days)

                # Create result
                result = DateAdvanceResult(
                    start_date=start_date,
                    end_date=end_date,
                    days_advanced=days
                )

                # Publish date advancement notification if publisher is configured
                if self._publisher:
                    self._publisher.publish_date_advanced(result)

                return result

            except Exception as e:
                # If something went wrong, try to maintain state consistency
                raise CalendarStateException(
                    f"Failed to advance calendar by {days} days",
                    state_info={
                        "current_date": str(self._current_date),
                        "attempted_days": days,
                        "error": str(e)
                    }
                )

    def advance_to(self, target_date: Union[Date, PyDate, str]) -> DateAdvanceResult:
        """
        Advance calendar to a specific target date.

        This is a convenience method for advancing to a known future date without
        manually calculating the number of days. Enforces forward-only progression.

        Args:
            target_date: Target date to advance to (must be in the future)

        Returns:
            DateAdvanceResult with advancement details

        Raises:
            InvalidDateException: If target_date is invalid
            CalendarStateException: If target_date is not in the future

        Example:
            # Jump from current date to preseason start
            calendar.advance_to(Date(2026, 8, 1))
        """
        # Normalize target date
        try:
            target = normalize_date(target_date)
        except ValueError as e:
            raise InvalidDateException(date_string=str(target_date), original_error=e)

        # Get current date (thread-safe)
        current = self.get_current_date()

        # Calculate days to advance
        days_to_advance = current.days_until(target)

        # Validate forward progression
        if days_to_advance < 0:
            raise CalendarStateException(
                f"Cannot advance to past date! Current: {current}, Target: {target}",
                state_info={
                    "current_date": str(current),
                    "target_date": str(target),
                    "days_difference": days_to_advance
                }
            )
        elif days_to_advance == 0:
            # Already at target date - return no-op result
            return DateAdvanceResult(
                start_date=current,
                end_date=current,
                days_advanced=0
            )

        # Advance to target using standard advance() method
        # This preserves statistics and thread-safety
        return self.advance(days_to_advance)

    def get_current_date(self) -> Date:
        """
        Get the current calendar date.

        Returns:
            Current Date object (thread-safe)
        """
        with self._lock:
            return self._current_date

    def get_current_season(self) -> int:
        """
        Get the current season year.

        Returns:
            Year of current date
        """
        return self.get_current_date().year

    def get_calendar_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive calendar statistics.

        Returns:
            Dictionary containing calendar usage statistics
        """
        with self._lock:
            current_date = self._current_date
            # Calculate days since creation directly to avoid deadlock
            days_since_creation = self._creation_date.days_until(self._current_date)

            return {
                "current_date": str(current_date),
                "current_year": current_date.year,
                "creation_date": str(self._creation_date),
                "total_days_advanced": self._total_days_advanced,
                "advancement_count": self._advancement_count,
                "average_advance_size": (
                    self._total_days_advanced / self._advancement_count
                    if self._advancement_count > 0 else 0
                ),
                "max_single_advance": self._max_single_advance,
                "days_since_creation": days_since_creation
            }

    def reset(self, new_date: Union[Date, PyDate, str], allow_backwards: bool = False) -> None:
        """
        Reset calendar to a new date and clear statistics.

        WARNING: This method clears all calendar statistics and should only be used for:
        - Initial calendar setup
        - Testing/debugging scenarios
        - Intentional complete restarts

        For normal forward time progression, use advance() or advance_to() instead.

        Args:
            new_date: New starting date
            allow_backwards: If False, raises error if new_date is before current date.
                           Set to True only for testing/debugging scenarios.
                           Default: False (enforce forward-only progression)

        Raises:
            InvalidDateException: If new_date is invalid
            CalendarStateException: If new_date is in the past and allow_backwards=False
        """
        try:
            normalized_date = normalize_date(new_date)
        except ValueError as e:
            raise InvalidDateException(date_string=str(new_date), original_error=e)

        with self._lock:
            # Validate forward progression unless explicitly allowed
            if not allow_backwards:
                current = self._current_date
                if normalized_date < current:
                    raise CalendarStateException(
                        f"Cannot reset to past date! Current: {current}, New: {normalized_date}. "
                        f"Use advance_to() for forward progression, or pass allow_backwards=True for testing.",
                        state_info={
                            "current_date": str(current),
                            "new_date": str(normalized_date),
                            "allow_backwards": allow_backwards
                        }
                    )

            self._current_date = normalized_date
            self._creation_date = normalized_date
            self._total_days_advanced = 0
            self._advancement_count = 0
            self._max_single_advance = 0

    def days_since_creation(self) -> int:
        """
        Get number of days since calendar was created/reset.

        Returns:
            Days between creation date and current date
        """
        with self._lock:
            return self._creation_date.days_until(self._current_date)

    def is_same_date(self, other_date: Union[Date, PyDate, str]) -> bool:
        """
        Check if current date matches another date.

        Args:
            other_date: Date to compare against

        Returns:
            True if dates match, False otherwise
        """
        try:
            other = normalize_date(other_date)
            return self.get_current_date() == other
        except ValueError:
            return False

    def days_until(self, target_date: Union[Date, PyDate, str]) -> int:
        """
        Calculate days until target date.

        Args:
            target_date: Target date

        Returns:
            Number of days (positive if future, negative if past)

        Raises:
            InvalidDateException: If target_date is invalid
        """
        try:
            target = normalize_date(target_date)
        except ValueError as e:
            raise InvalidDateException(date_string=str(target_date), original_error=e)

        current = self.get_current_date()
        return current.days_until(target)

    def can_advance(self, days: Union[int, float]) -> bool:
        """
        Check if calendar can advance by specified days.

        Args:
            days: Number of days to check

        Returns:
            True if advancement is valid, False otherwise
        """
        try:
            self._validate_days_parameter(days)
            return True
        except InvalidDaysException:
            return False

    # Season Phase Methods

    def get_current_phase(self) -> SeasonPhase:
        """Get the current NFL season phase."""
        with self._lock:
            # Use external phase state if provided
            if self._external_phase_state:
                return self._external_phase_state.phase
            # Fallback to internal tracker (backward compatibility)
            return self._season_phase_tracker.get_current_phase()

    def get_current_week(self) -> int:
        """
        Get the current week number within the season.

        Note: This is a simplified implementation. In a full system,
        this would be calculated based on actual game schedule.
        """
        # This is a placeholder implementation
        # In a real system, this would be calculated based on the current phase
        # and the actual game schedule
        return 1

    def get_season_day(self) -> int:
        """Get the number of days since the season started."""
        with self._lock:
            # Use internal tracker if available
            if self._season_phase_tracker:
                phase_info = self._season_phase_tracker.get_phase_info()
                return phase_info.get("days_in_current_phase", 0)
            # External phase state doesn't track days in phase
            return 0

    def is_offseason(self) -> bool:
        """Check if currently in the offseason."""
        return self.get_current_phase() == SeasonPhase.OFFSEASON

    def is_during_regular_season(self) -> bool:
        """Check if currently during the regular season."""
        return self.get_current_phase() == SeasonPhase.REGULAR_SEASON

    def is_during_playoffs(self) -> bool:
        """Check if currently during the playoffs."""
        return self.get_current_phase() == SeasonPhase.PLAYOFFS

    def get_next_milestone(self) -> Optional[SeasonMilestone]:
        """Get the next upcoming season milestone."""
        with self._lock:
            return self._milestone_calculator.get_next_milestone(
                self._current_date, self._season_milestones
            )

    def get_recent_milestones(self, days_back: int = 30) -> List[SeasonMilestone]:
        """Get milestones that occurred recently."""
        with self._lock:
            return self._milestone_calculator.get_recent_milestones(
                self._current_date, self._season_milestones, days_back
            )

    def get_season_milestones(self) -> List[SeasonMilestone]:
        """Get all season milestones."""
        with self._lock:
            return self._season_milestones.copy()

    def record_game_completion(self, game_event: GameCompletionEvent) -> Optional[PhaseTransition]:
        """
        Record a completed game and check for phase transitions.

        Args:
            game_event: The completed game event

        Returns:
            PhaseTransition if a transition was triggered, None otherwise
        """
        with self._lock:
            # Only internal tracker supports game completion tracking
            if not self._season_phase_tracker:
                # External phase state doesn't support game completion events
                return None

            transition = self._season_phase_tracker.record_game_completion(game_event)

            if transition:
                # Update milestones when phase changes
                self._update_season_milestones()

                # Publish phase transition notification if publisher is configured
                if self._publisher:
                    self._publisher.publish_phase_transition(transition)

            return transition

    def get_phase_info(self) -> Dict[str, Any]:
        """Get comprehensive information about the current season phase."""
        with self._lock:
            # Use external phase state if provided
            if self._external_phase_state:
                # Simplified phase info for external phase state
                base_info = {
                    "current_phase": self._external_phase_state.phase.value,
                    "phase_name": self._external_phase_state.phase.name
                }
            else:
                # Full phase info from internal tracker (backward compatibility)
                base_info = self._season_phase_tracker.get_phase_info()

            # Add milestone information (avoid nested locking)
            next_milestone = self._milestone_calculator.get_next_milestone(
                self._current_date, self._season_milestones
            )
            recent_milestones = self._milestone_calculator.get_recent_milestones(
                self._current_date, self._season_milestones, 30
            )

            base_info.update({
                "next_milestone": {
                    "name": next_milestone.name if next_milestone else None,
                    "date": str(next_milestone.date) if next_milestone else None,
                    "type": next_milestone.milestone_type.value if next_milestone else None
                },
                "recent_milestones_count": len(recent_milestones),
                "total_milestones": len(self._season_milestones)
            })

            return base_info

    def get_days_until_next_phase(self) -> Optional[int]:
        """
        Get the number of days until the next phase transition.

        Note: This is an estimate since transitions are event-driven.
        """
        # This would need more sophisticated prediction logic
        # For now, return None as transitions are event-driven
        return None

    def force_phase_transition(self, to_phase: SeasonPhase,
                              metadata: Optional[Dict[str, Any]] = None) -> PhaseTransition:
        """
        Force a phase transition (for testing or manual control).

        Args:
            to_phase: Phase to transition to
            metadata: Optional metadata for the transition

        Returns:
            The transition that was executed
        """
        with self._lock:
            # Use external phase state if provided
            if self._external_phase_state:
                # Update external phase state directly
                old_phase = self._external_phase_state.phase
                self._external_phase_state.phase = to_phase

                # Create transition object for consistency
                transition = PhaseTransition(
                    from_phase=old_phase,
                    to_phase=to_phase,
                    transition_date=self._current_date,
                    metadata=metadata or {}
                )
            else:
                # Use internal tracker (backward compatibility)
                transition = self._season_phase_tracker.force_phase_transition(
                    to_phase, self._current_date, metadata
                )

            self._update_season_milestones()

            # Publish phase transition notification if publisher is configured
            if self._publisher:
                self._publisher.publish_phase_transition(transition)

            return transition

    def _update_season_milestones(self) -> None:
        """Update season milestones based on current state."""
        # Get season year from phase info if available
        if self._season_phase_tracker:
            phase_info = self._season_phase_tracker.get_phase_info()
            season_year = phase_info.get("season_year", self._current_date.year)
        else:
            # External phase state doesn't track season year, use current year
            season_year = self._current_date.year

        # Calculate milestones for the current season
        self._season_milestones = self._milestone_calculator.calculate_milestones_for_season(
            season_year=season_year,
            super_bowl_date=None,  # Would be set when Super Bowl is completed
            regular_season_start=None  # Would be set when regular season starts
        )

    def _validate_days_parameter(self, days: Union[int, float]) -> None:
        """
        Validate the days parameter for advancement.

        Args:
            days: Days parameter to validate

        Raises:
            InvalidDaysException: If days is invalid
        """
        # Check type
        if not isinstance(days, (int, float)):
            raise InvalidDaysException(
                days=0,  # Placeholder since we can't convert
                min_days=self.MIN_ADVANCE_DAYS,
                max_days=self.MAX_ADVANCE_DAYS
            )

        # Check if it's effectively an integer
        if isinstance(days, float) and not days.is_integer():
            raise InvalidDaysException(
                days=int(days),
                min_days=self.MIN_ADVANCE_DAYS,
                max_days=self.MAX_ADVANCE_DAYS
            )

        days_int = int(days)

        # Check range
        if days_int < self.MIN_ADVANCE_DAYS:
            raise InvalidDaysException(
                days=days_int,
                min_days=self.MIN_ADVANCE_DAYS,
                max_days=self.MAX_ADVANCE_DAYS
            )

        if days_int > self.MAX_ADVANCE_DAYS:
            raise InvalidDaysException(
                days=days_int,
                min_days=self.MIN_ADVANCE_DAYS,
                max_days=self.MAX_ADVANCE_DAYS
            )

    def __str__(self) -> str:
        """String representation of calendar."""
        current = self.get_current_date()
        return f"CalendarComponent(current_date={current})"

    def __repr__(self) -> str:
        """Developer representation of calendar."""
        current = self.get_current_date()
        return f"CalendarComponent(current_date={current!r})"


# Factory Functions

def create_calendar(start_date: Optional[Union[Date, PyDate, str]] = None) -> CalendarComponent:
    """
    Create a new calendar component.

    Args:
        start_date: Starting date (defaults to today if None)

    Returns:
        New CalendarComponent instance
    """
    if start_date is None:
        start_date = Date.today()

    return CalendarComponent(start_date)


def advance_calendar_days(calendar: CalendarComponent, days: int) -> Date:
    """
    Advance calendar and return new date.

    Args:
        calendar: Calendar to advance
        days: Number of days to advance

    Returns:
        New current date after advancement
    """
    calendar.advance(days)
    return calendar.get_current_date()