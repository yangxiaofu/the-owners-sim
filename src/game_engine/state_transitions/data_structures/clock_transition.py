"""
ClockTransition - Time and Quarter Management

This data structure represents all changes to game time, quarter progression,
and clock-related game state. It handles time advancement, clock stoppages,
quarter transitions, timeouts, and special timing situations.

Key responsibilities:
- Track game time progression and changes
- Handle quarter transitions and overtime
- Manage clock stoppages and running clock scenarios
- Track timeout usage and clock management
- Handle special timing rules (two-minute warning, etc.)
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from enum import Enum


class ClockStopReason(Enum):
    """Enumeration of reasons why the game clock stopped."""
    INCOMPLETE_PASS = "incomplete_pass"
    OUT_OF_BOUNDS = "out_of_bounds"
    TIMEOUT_CALLED = "timeout_called"
    INJURY_TIMEOUT = "injury_timeout"
    PENALTY = "penalty"
    MEASUREMENT = "measurement"
    SCORING_PLAY = "scoring_play"
    TURNOVER = "turnover"
    TWO_MINUTE_WARNING = "two_minute_warning"
    QUARTER_END = "quarter_end"
    GAME_END = "game_end"
    REFEREE_TIMEOUT = "referee_timeout"
    TELEVISION_TIMEOUT = "television_timeout"
    CHANGE_OF_POSSESSION = "change_of_possession"
    FIRST_DOWN = "first_down"  # In final 2 minutes of half
    SPIKE = "spike"
    KNEEL_DOWN = "kneel_down"


class TimeoutType(Enum):
    """Types of timeouts that can be called."""
    TEAM_TIMEOUT = "team_timeout"
    INJURY_TIMEOUT = "injury_timeout"
    OFFICIALS_TIMEOUT = "officials_timeout"
    TELEVISION_TIMEOUT = "television_timeout"
    TWO_MINUTE_WARNING = "two_minute_warning"
    QUARTER_BREAK = "quarter_break"
    HALFTIME = "halftime"
    OVERTIME_BREAK = "overtime_break"


@dataclass(frozen=True)
class ClockTransition:
    """
    Immutable representation of clock and time-related changes.
    
    This object contains all information about how game time progresses,
    including clock changes, quarter transitions, and timing situations.
    
    Attributes:
        # Basic Time Information
        time_advanced: Whether game time moved forward
        seconds_elapsed: Number of seconds that elapsed on the play
        new_game_time: New game time after the play (in seconds)
        old_game_time: Previous game time before the play
        
        # Clock Control
        clock_running: Whether the clock should be running after the play
        clock_stopped: Whether the clock was stopped
        clock_stop_reason: Why the clock stopped (if applicable)
        clock_will_start_on_snap: Whether clock starts on snap (vs. on whistle)
        
        # Quarter Information
        current_quarter: Current quarter number
        quarter_changed: Whether the quarter advanced
        new_quarter: New quarter number (if changed)
        time_remaining_in_quarter: Time left in current quarter
        
        # Game Phase
        first_half: Whether currently in first half
        second_half: Whether currently in second half
        overtime: Whether currently in overtime
        overtime_period: Which overtime period (if applicable)
        
        # Special Timing Situations
        two_minute_warning_triggered: Whether two-minute warning was triggered
        under_two_minutes: Whether under 2 minutes in half
        final_minute: Whether in final minute of quarter/game
        hurry_up_situation: Whether this is a hurry-up/no-huddle situation
        
        # Timeout Information
        timeout_called: Whether a timeout was called
        timeout_type: Type of timeout called
        timeout_team: Team that called the timeout (if applicable)
        timeouts_remaining_home: Remaining timeouts for home team
        timeouts_remaining_away: Remaining timeouts for away team
        
        # Game Ending
        quarter_ending: Whether this play ends the quarter
        half_ending: Whether this play ends the half
        game_ending: Whether this play ends the game
        regulation_ending: Whether regulation time is ending
        
        # Clock Management Strategy
        deliberate_clock_management: Whether team is managing clock intentionally
        trying_to_stop_clock: Whether team is trying to stop the clock
        trying_to_run_clock: Whether team is trying to run out the clock
        clock_management_situation: Description of clock management scenario
        
        # Play Clock
        play_clock_reset: Whether play clock was reset
        play_clock_violation: Whether there was a play clock violation
        delay_of_game: Whether delay of game occurred
        
        # Special Rules
        automatic_timeout: Whether an automatic timeout occurred
        injury_timeout_charged: Whether injury timeout was charged to team
        excess_timeout: Whether team used excess timeout (penalty)
        
        # Time Calculations
        actual_play_duration: Real time the play took to complete
        time_between_plays: Time elapsed between plays
        total_game_time_elapsed: Total time elapsed in game
        
        # Context and Metadata
        critical_time_situation: Whether this is a critical time management situation
        end_of_game_scenario: Whether this is an end-of-game scenario
        comeback_situation: Whether team is in comeback mode
        clock_management_pressure: Level of clock pressure (low/medium/high)
    """
    
    # Basic Time Information
    time_advanced: bool
    seconds_elapsed: int
    new_game_time: int  # Total seconds remaining in quarter
    old_game_time: int
    
    # Clock Control
    clock_running: bool = True
    clock_stopped: bool = False
    clock_stop_reason: Optional[ClockStopReason] = None
    clock_will_start_on_snap: bool = True
    
    # Quarter Information
    current_quarter: int = 1
    quarter_changed: bool = False
    new_quarter: Optional[int] = None
    time_remaining_in_quarter: int = 900  # 15 minutes = 900 seconds
    
    # Game Phase
    first_half: bool = True
    second_half: bool = False
    overtime: bool = False
    overtime_period: int = 0
    
    # Special Timing Situations
    two_minute_warning_triggered: bool = False
    under_two_minutes: bool = False
    final_minute: bool = False
    hurry_up_situation: bool = False
    
    # Timeout Information
    timeout_called: bool = False
    timeout_type: Optional[TimeoutType] = None
    timeout_team: Optional[str] = None
    timeouts_remaining_home: int = 3
    timeouts_remaining_away: int = 3
    
    # Game Ending
    quarter_ending: bool = False
    half_ending: bool = False
    game_ending: bool = False
    regulation_ending: bool = False
    
    # Clock Management Strategy
    deliberate_clock_management: bool = False
    trying_to_stop_clock: bool = False
    trying_to_run_clock: bool = False
    clock_management_situation: Optional[str] = None
    
    # Play Clock
    play_clock_reset: bool = True
    play_clock_violation: bool = False
    delay_of_game: bool = False
    
    # Special Rules
    automatic_timeout: bool = False
    injury_timeout_charged: bool = False
    excess_timeout: bool = False
    
    # Time Calculations
    actual_play_duration: Optional[int] = None
    time_between_plays: Optional[int] = None
    total_game_time_elapsed: Optional[int] = None
    
    # Context and Metadata
    critical_time_situation: bool = False
    end_of_game_scenario: bool = False
    comeback_situation: bool = False
    clock_management_pressure: str = "low"  # low, medium, high
    
    def __post_init__(self):
        """Validate clock data and calculate derived fields."""
        # Validate quarter
        if not (1 <= self.current_quarter <= 5):  # Including overtime
            raise ValueError(f"Quarter must be 1-5, got {self.current_quarter}")
        
        # Validate time values
        if self.new_game_time < 0:
            raise ValueError(f"Game time cannot be negative, got {self.new_game_time}")
        
        if self.seconds_elapsed < 0:
            raise ValueError(f"Elapsed time cannot be negative, got {self.seconds_elapsed}")
        
        # Set derived timing flags
        object.__setattr__(self, 'under_two_minutes', self.new_game_time <= 120)  # 2 minutes
        object.__setattr__(self, 'final_minute', self.new_game_time <= 60)
        
        # Set game phase flags
        if self.current_quarter <= 2:
            object.__setattr__(self, 'first_half', True)
            object.__setattr__(self, 'second_half', False)
        elif self.current_quarter <= 4:
            object.__setattr__(self, 'first_half', False)
            object.__setattr__(self, 'second_half', True)
        else:
            object.__setattr__(self, 'first_half', False)
            object.__setattr__(self, 'second_half', False)
            object.__setattr__(self, 'overtime', True)
            object.__setattr__(self, 'overtime_period', self.current_quarter - 4)
        
        # Set ending flags
        if self.new_game_time <= 0:
            object.__setattr__(self, 'quarter_ending', True)
            if self.current_quarter in [2, 4]:
                object.__setattr__(self, 'half_ending', True)
            if self.current_quarter == 4:
                object.__setattr__(self, 'regulation_ending', True)
        
        # Set critical time situations
        if self.under_two_minutes or self.final_minute or self.quarter_ending:
            object.__setattr__(self, 'critical_time_situation', True)
        
        # Set clock management pressure
        if self.final_minute:
            object.__setattr__(self, 'clock_management_pressure', 'high')
        elif self.under_two_minutes:
            object.__setattr__(self, 'clock_management_pressure', 'medium')
    
    def get_time_display(self) -> str:
        """Return game time in MM:SS format."""
        minutes = self.new_game_time // 60
        seconds = self.new_game_time % 60
        return f"{minutes:02d}:{seconds:02d}"
    
    def get_quarter_display(self) -> str:
        """Return quarter in human-readable format."""
        if self.overtime:
            if self.overtime_period == 1:
                return "OT"
            else:
                return f"OT{self.overtime_period}"
        else:
            quarters = {1: "1st", 2: "2nd", 3: "3rd", 4: "4th"}
            return quarters.get(self.current_quarter, f"{self.current_quarter}th")
    
    def get_game_phase_description(self) -> str:
        """Return description of current game phase."""
        if self.overtime:
            return f"Overtime Period {self.overtime_period}"
        elif self.first_half:
            return "First Half"
        else:
            return "Second Half"
    
    def get_clock_status_description(self) -> str:
        """Return description of clock status."""
        if not self.clock_running:
            if self.clock_stop_reason:
                return f"Clock stopped - {self.clock_stop_reason.value.replace('_', ' ')}"
            return "Clock stopped"
        
        if self.clock_will_start_on_snap:
            return "Clock will start on snap"
        else:
            return "Clock running"
    
    def get_timeout_description(self) -> str:
        """Return description of timeout situation."""
        if not self.timeout_called:
            return "No timeout"
        
        timeout_desc = self.timeout_type.value.replace('_', ' ').title()
        
        if self.timeout_team:
            return f"{timeout_desc} - {self.timeout_team}"
        
        return timeout_desc
    
    def get_time_pressure_description(self) -> str:
        """Return description of time pressure situation."""
        descriptions = []
        
        if self.final_minute:
            descriptions.append("Final minute")
        elif self.under_two_minutes:
            descriptions.append("Under 2 minutes")
        
        if self.two_minute_warning_triggered:
            descriptions.append("Two-minute warning")
        
        if self.hurry_up_situation:
            descriptions.append("Hurry-up offense")
        
        if self.quarter_ending:
            descriptions.append("Quarter ending")
        
        if self.game_ending:
            descriptions.append("Game ending")
        
        return " | ".join(descriptions) if descriptions else "Normal time situation"
    
    def get_clock_management_description(self) -> str:
        """Return description of clock management strategy."""
        if not self.deliberate_clock_management:
            return "No special clock management"
        
        if self.trying_to_stop_clock:
            return "Trying to stop clock"
        elif self.trying_to_run_clock:
            return "Running out the clock"
        elif self.clock_management_situation:
            return self.clock_management_situation
        
        return "Clock management situation"
    
    def is_critical_time(self) -> bool:
        """Return True if this is a critical time management situation."""
        return (self.critical_time_situation or self.end_of_game_scenario or 
                self.comeback_situation or self.clock_management_pressure == 'high')
    
    def requires_strategic_clock_management(self) -> bool:
        """Return True if strategic clock management is important."""
        return (self.under_two_minutes or self.trying_to_stop_clock or 
                self.trying_to_run_clock or self.comeback_situation)
    
    def get_summary(self) -> str:
        """Return a complete summary of this clock transition."""
        parts = []
        
        # Time advancement
        if self.time_advanced:
            parts.append(f"Time: -{self.seconds_elapsed}s to {self.get_time_display()}")
        
        # Quarter info
        if self.quarter_changed:
            parts.append(f"Quarter: {self.get_quarter_display()}")
        
        # Clock status
        parts.append(self.get_clock_status_description())
        
        # Timeout
        if self.timeout_called:
            parts.append(self.get_timeout_description())
        
        # Special situations
        time_pressure = self.get_time_pressure_description()
        if time_pressure != "Normal time situation":
            parts.append(f"[{time_pressure}]")
        
        return " | ".join(parts)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert this clock transition to a dictionary."""
        return {
            'time_info': {
                'time_advanced': self.time_advanced,
                'seconds_elapsed': self.seconds_elapsed,
                'new_game_time': self.new_game_time,
                'old_game_time': self.old_game_time,
                'time_display': self.get_time_display(),
                'time_remaining_in_quarter': self.time_remaining_in_quarter
            },
            'clock_control': {
                'clock_running': self.clock_running,
                'clock_stopped': self.clock_stopped,
                'clock_stop_reason': self.clock_stop_reason.value if self.clock_stop_reason else None,
                'clock_will_start_on_snap': self.clock_will_start_on_snap,
                'clock_status_description': self.get_clock_status_description()
            },
            'quarter_info': {
                'current_quarter': self.current_quarter,
                'quarter_changed': self.quarter_changed,
                'new_quarter': self.new_quarter,
                'quarter_display': self.get_quarter_display(),
                'game_phase': self.get_game_phase_description()
            },
            'game_phase': {
                'first_half': self.first_half,
                'second_half': self.second_half,
                'overtime': self.overtime,
                'overtime_period': self.overtime_period
            },
            'timing_situations': {
                'two_minute_warning_triggered': self.two_minute_warning_triggered,
                'under_two_minutes': self.under_two_minutes,
                'final_minute': self.final_minute,
                'hurry_up_situation': self.hurry_up_situation,
                'critical_time_situation': self.critical_time_situation,
                'time_pressure_description': self.get_time_pressure_description()
            },
            'timeout_info': {
                'timeout_called': self.timeout_called,
                'timeout_type': self.timeout_type.value if self.timeout_type else None,
                'timeout_team': self.timeout_team,
                'timeouts_remaining_home': self.timeouts_remaining_home,
                'timeouts_remaining_away': self.timeouts_remaining_away,
                'timeout_description': self.get_timeout_description()
            },
            'game_ending': {
                'quarter_ending': self.quarter_ending,
                'half_ending': self.half_ending,
                'game_ending': self.game_ending,
                'regulation_ending': self.regulation_ending,
                'end_of_game_scenario': self.end_of_game_scenario
            },
            'clock_management': {
                'deliberate_clock_management': self.deliberate_clock_management,
                'trying_to_stop_clock': self.trying_to_stop_clock,
                'trying_to_run_clock': self.trying_to_run_clock,
                'clock_management_situation': self.clock_management_situation,
                'clock_management_pressure': self.clock_management_pressure,
                'requires_strategic_management': self.requires_strategic_clock_management(),
                'clock_management_description': self.get_clock_management_description()
            },
            'play_clock': {
                'play_clock_reset': self.play_clock_reset,
                'play_clock_violation': self.play_clock_violation,
                'delay_of_game': self.delay_of_game
            },
            'special_timeouts': {
                'automatic_timeout': self.automatic_timeout,
                'injury_timeout_charged': self.injury_timeout_charged,
                'excess_timeout': self.excess_timeout
            },
            'time_calculations': {
                'actual_play_duration': self.actual_play_duration,
                'time_between_plays': self.time_between_plays,
                'total_game_time_elapsed': self.total_game_time_elapsed
            },
            'summary': self.get_summary(),
            'is_critical_time': self.is_critical_time()
        }