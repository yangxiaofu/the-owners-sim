"""
Game Clock Manager - Time and Quarter Tracking

Handles all game timing including quarter progression, time management,
and game phase detection. Maintains clean separation from other game
state managers while providing comprehensive time tracking capabilities.
"""

from dataclasses import dataclass
from typing import Optional, List
from enum import Enum


class GamePhase(Enum):
    """Current phase of the game"""
    FIRST_HALF = "first_half"
    HALFTIME = "halftime"
    SECOND_HALF = "second_half"
    OVERTIME = "overtime"
    GAME_OVER = "game_over"


@dataclass
class ClockResult:
    """
    Result of time advancement operations
    
    Provides feedback about what happened when time was advanced,
    allowing other managers to react to clock events.
    """
    time_advanced: float              # Actual seconds advanced
    quarter_ended: bool = False       # Quarter boundary crossed
    half_ended: bool = False          # Half boundary crossed (Q2 or Q4)
    game_ended: bool = False          # Game ended (regulation time expired)
    quarter_started: Optional[int] = None  # New quarter number if started
    new_phase: Optional[GamePhase] = None  # New game phase if changed
    
    # Time-based triggers
    two_minute_warning: bool = False  # Crossed 2:00 threshold
    clock_events: List[str] = None    # Descriptive events that occurred
    
    def __post_init__(self):
        """Initialize events list if not provided"""
        if self.clock_events is None:
            self.clock_events = []


class GameClock:
    """
    Game clock manager for comprehensive time tracking
    
    Handles quarter progression, time management, and game phase detection
    with clean separation from drive and possession management.
    """
    
    def __init__(self, quarter: int = 1, time_remaining_seconds: int = 900):
        """
        Initialize game clock
        
        Args:
            quarter: Starting quarter (1-4, 5+ for overtime)
            time_remaining_seconds: Time remaining in current quarter (default 15:00)
        """
        self.quarter = quarter
        self.time_remaining_seconds = time_remaining_seconds
        self.is_halftime = False
        self.game_phase = self._determine_game_phase()
        
        # Validate parameters
        self._validate_clock_state()
    
    def _validate_clock_state(self):
        """Validate current clock parameters"""
        if self.quarter < 1:
            raise ValueError(f"Invalid quarter: {self.quarter}. Must be >= 1")
        if self.time_remaining_seconds < 0:
            raise ValueError(f"Invalid time_remaining: {self.time_remaining_seconds}. Must be >= 0")
    
    def _determine_game_phase(self) -> GamePhase:
        """Determine current game phase based on quarter and time"""
        if self.is_halftime:
            return GamePhase.HALFTIME
        elif self.quarter <= 2:
            return GamePhase.FIRST_HALF
        elif self.quarter <= 4:
            return GamePhase.SECOND_HALF
        elif self.quarter >= 5:
            return GamePhase.OVERTIME
        else:
            return GamePhase.GAME_OVER
    
    def advance_time(self, seconds_elapsed: float) -> ClockResult:
        """
        Advance game clock by specified seconds
        
        Args:
            seconds_elapsed: Seconds to advance the clock
            
        Returns:
            ClockResult with information about what happened during advancement
        """
        if seconds_elapsed < 0:
            raise ValueError(f"Cannot advance time by negative amount: {seconds_elapsed}")
        
        # Don't advance time during halftime
        if self.is_halftime:
            return ClockResult(time_advanced=0.0, clock_events=["Clock stopped - halftime"])
        
        original_time = self.time_remaining_seconds
        original_quarter = self.quarter
        
        # Create result object to track changes
        result = ClockResult(time_advanced=seconds_elapsed)
        
        # Check for two-minute warning before advancing time
        if (original_time > 120 and 
            (original_time - seconds_elapsed) <= 120 and 
            self.quarter in [2, 4]):
            result.two_minute_warning = True
            result.clock_events.append("Two-minute warning")
        
        # Advance time
        new_time = max(0, self.time_remaining_seconds - int(seconds_elapsed))
        
        # Handle quarter transitions
        if new_time == 0 and original_time > 0:
            # Quarter ended
            result.quarter_ended = True
            result.clock_events.append(f"End of Q{self.quarter}")
            
            # Check for half/game endings
            if self.quarter == 2:
                result.half_ended = True
                result.clock_events.append("End of first half")
                self.is_halftime = True
                result.new_phase = GamePhase.HALFTIME
            elif self.quarter == 4:
                result.half_ended = True
                result.game_ended = True
                result.clock_events.append("End of regulation")
                result.new_phase = GamePhase.GAME_OVER
            elif self.quarter >= 5:
                # Overtime handling - would need game context to determine if game actually ends
                result.clock_events.append(f"End of overtime Q{self.quarter}")
        
        self.time_remaining_seconds = new_time
        
        # Update game phase
        old_phase = self.game_phase
        self.game_phase = self._determine_game_phase()
        if self.game_phase != old_phase:
            result.new_phase = self.game_phase
        
        return result
    
    def start_new_quarter(self, quarter: int, time_seconds: int = 900) -> ClockResult:
        """
        Start a new quarter with specified time
        
        Args:
            quarter: New quarter number
            time_seconds: Time for new quarter (default 15:00)
            
        Returns:
            ClockResult indicating quarter change
        """
        old_quarter = self.quarter
        self.quarter = quarter
        self.time_remaining_seconds = time_seconds
        self.is_halftime = False
        
        # Update game phase
        old_phase = self.game_phase
        self.game_phase = self._determine_game_phase()
        
        result = ClockResult(
            time_advanced=0.0,
            quarter_started=quarter,
            new_phase=self.game_phase if self.game_phase != old_phase else None,
            clock_events=[f"Started Q{quarter}"]
        )
        
        self._validate_clock_state()
        return result
    
    def start_halftime(self) -> ClockResult:
        """Start halftime break"""
        self.is_halftime = True
        self.game_phase = GamePhase.HALFTIME
        
        return ClockResult(
            time_advanced=0.0,
            new_phase=GamePhase.HALFTIME,
            clock_events=["Halftime started"]
        )
    
    def end_halftime(self) -> ClockResult:
        """End halftime and prepare for second half"""
        self.is_halftime = False
        
        # Start Q3 with full time
        return self.start_new_quarter(3, 900)
    
    def get_time_display(self) -> str:
        """
        Get formatted time display
        
        Returns:
            Time in format "Q1 15:00" or "HALFTIME"
        """
        if self.is_halftime:
            return "HALFTIME"
        
        minutes = self.time_remaining_seconds // 60
        seconds = self.time_remaining_seconds % 60
        return f"Q{self.quarter} {minutes}:{seconds:02d}"
    
    def get_detailed_time_info(self) -> dict:
        """Get comprehensive time information"""
        return {
            "quarter": self.quarter,
            "time_remaining_seconds": self.time_remaining_seconds,
            "time_display": self.get_time_display(),
            "game_phase": self.game_phase.value,
            "is_halftime": self.is_halftime,
            "is_end_of_quarter": self.is_end_of_quarter,
            "is_end_of_half": self.is_end_of_half,
            "is_end_of_game": self.is_end_of_game,
            "is_overtime": self.is_overtime,
            "is_two_minute_warning_active": self.is_two_minute_warning_active
        }
    
    # Properties for backward compatibility and state queries
    @property
    def is_end_of_quarter(self) -> bool:
        """Check if quarter time has expired"""
        return self.time_remaining_seconds == 0
    
    @property
    def is_end_of_half(self) -> bool:
        """Check if half has ended (Q2 or Q4 with no time)"""
        return self.is_end_of_quarter and self.quarter in [2, 4]
    
    @property
    def is_end_of_game(self) -> bool:
        """Check if regulation game has ended (Q4 with no time)"""
        return self.is_end_of_quarter and self.quarter == 4
    
    @property
    def is_overtime(self) -> bool:
        """Check if currently in overtime"""
        return self.quarter >= 5
    
    @property
    def is_two_minute_warning_active(self) -> bool:
        """Check if within two-minute warning period"""
        return (self.time_remaining_seconds <= 120 and 
                self.quarter in [2, 4] and 
                not self.is_halftime)
    
    @property
    def is_clock_running(self) -> bool:
        """Check if clock should be running (not halftime, not expired)"""
        return not self.is_halftime and not self.is_end_of_quarter
    
    def __str__(self) -> str:
        """String representation of clock state"""
        return self.get_time_display()
    
    def __repr__(self) -> str:
        """Detailed representation for debugging"""
        return f"GameClock(quarter={self.quarter}, time={self.time_remaining_seconds}s, phase={self.game_phase.value})"