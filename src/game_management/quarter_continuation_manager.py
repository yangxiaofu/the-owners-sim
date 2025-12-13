"""
Quarter Continuation Manager

Handles drive state preservation across quarter transitions (Q1→Q2, Q3→Q4).
Provides a single, testable class for all quarter continuation logic.

In the NFL:
- Q1→Q2: Same drive continues, down/distance preserved
- Q2→Q3: Halftime, second half kickoff (new drive)
- Q3→Q4: Same drive continues, down/distance preserved
- Q4 end: Game over (or overtime if tied)
"""

from dataclasses import dataclass
from typing import Optional
from play_engine.game_state.drive_manager import DriveEndReason


@dataclass
class DriveEndState:
    """Captured state when a drive ends"""
    possessing_team_id: int
    field_position: int
    down: int
    yards_to_go: int
    end_reason: DriveEndReason
    quarter: int


@dataclass
class ContinuationState:
    """State for continuing a drive across quarters"""
    should_continue: bool
    possessing_team_id: int
    field_position: int
    down: int
    yards_to_go: int
    reason: str  # "quarter_continuation" or "new_drive"


class QuarterContinuationManager:
    """
    Single source of truth for quarter transition logic.

    Determines whether a drive continues across quarters (Q1→Q2, Q3→Q4)
    and preserves the correct down/distance/field position.

    Usage:
        1. Call capture_drive_end() immediately after each drive ends
        2. Call get_next_drive_state() at the start of each new drive
        3. If should_continue is True, use the preserved state
        4. If should_continue is False, start a new drive (1st & 10)
    """

    def __init__(self):
        self._pending_continuation: Optional[ContinuationState] = None

    def capture_drive_end(self, end_state: DriveEndState) -> None:
        """
        Capture state when a drive ends - call this IMMEDIATELY after drive ends.

        Args:
            end_state: The complete state when the drive ended
        """
        if self._should_continue_drive(end_state):
            self._pending_continuation = ContinuationState(
                should_continue=True,
                possessing_team_id=end_state.possessing_team_id,
                field_position=end_state.field_position,
                down=end_state.down,
                yards_to_go=end_state.yards_to_go,
                reason="quarter_continuation"
            )
        else:
            self._pending_continuation = None

    def get_next_drive_state(self, default_field_position: int = 25) -> ContinuationState:
        """
        Get the state for starting the next drive.

        Args:
            default_field_position: Field position for new drives (default touchback at 25)

        Returns:
            ContinuationState with preserved state if continuing, or default new drive state
        """
        if self._pending_continuation is not None:
            state = self._pending_continuation
            self._pending_continuation = None  # Clear after use
            return state
        else:
            # No continuation - return default new drive state
            return ContinuationState(
                should_continue=False,
                possessing_team_id=0,  # Caller must set
                field_position=default_field_position,
                down=1,
                yards_to_go=10,
                reason="new_drive"
            )

    def has_pending_continuation(self) -> bool:
        """Check if there's a pending continuation (for debugging)"""
        return self._pending_continuation is not None

    def clear_continuation(self) -> None:
        """
        Clear any pending continuation state.

        Used when starting overtime to prevent inheriting 4th quarter
        down/distance state. Overtime should always start fresh with a kickoff.
        """
        self._pending_continuation = None

    def _should_continue_drive(self, end_state: DriveEndState) -> bool:
        """
        Determine if drive should continue into next quarter.

        NFL Rules:
        - Q1→Q2: Drive continues (same half)
        - Q2→Q3: Halftime - new possession via kickoff
        - Q3→Q4: Drive continues (same half)
        - Q4 end: Game over

        Args:
            end_state: The drive end state

        Returns:
            True if drive should continue, False if new drive should start
        """
        # Only continue for time expiration (quarter ended mid-drive)
        if end_state.end_reason != DriveEndReason.TIME_EXPIRATION:
            return False

        # Q1→Q2 and Q3→Q4 are continuations
        # Q2 end is halftime (kickoff)
        # Q4 end is game over
        return end_state.quarter in [1, 3]
