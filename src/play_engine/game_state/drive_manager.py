"""
Drive Manager - Focused Drive Simulator

Simulates individual drive execution with minimal game-level dependencies:
- Accepts external play results and updates drive state
- Provides current drive situation for external play callers  
- Tracks drive-level statistics internally
- Determines when drives end and basic reason
- Returns drive-specific results only

Does NOT handle:
- Play calling (external responsibility)
- Play execution (external responsibility)  
- Drive transitions (external responsibility)
- Game clock management (external responsibility)
- Possession changes (external responsibility)
- Next drive field positions (external responsibility)
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum
from .field_position import FieldPosition, FieldTracker
from .down_situation import DownState, DownTracker
from ..core.play_result import PlayResult


class DriveEndReason(Enum):
    """Reasons why a drive can end"""
    TOUCHDOWN = "touchdown"
    FIELD_GOAL = "field_goal"
    FIELD_GOAL_MISSED = "field_goal_missed"
    SAFETY = "safety"
    TURNOVER_INTERCEPTION = "turnover_interception"
    TURNOVER_FUMBLE = "turnover_fumble"
    TURNOVER_ON_DOWNS = "turnover_on_downs"
    PUNT = "punt"
    TIME_EXPIRATION = "time_expiration"


class PuntOutcomeType(Enum):
    """Punt-specific play outcomes"""
    PUNT_SUCCESS = "punt"
    PUNT_EXECUTION_FAILED = "punt_execution_failed"
    PUNT_BLOCKED = "punt_blocked"
    PUNT_FORMATION_INVALID = "punt_formation_invalid"



@dataclass
class DriveStats:
    """Drive-level statistics tracked internally by DriveManager"""
    plays_run: int = 0
    total_yards: int = 0
    net_yards: int = 0                      # After penalties
    first_downs_achieved: int = 0
    time_of_possession_seconds: float = 0.0
    
    # Situational efficiency
    third_down_attempts: int = 0
    third_down_conversions: int = 0
    fourth_down_attempts: int = 0
    fourth_down_conversions: int = 0
    red_zone_attempts: int = 0
    red_zone_touchdowns: int = 0
    
    # Penalties
    penalties_committed: int = 0
    penalty_yards: int = 0
    
    @property
    def third_down_percentage(self) -> float:
        """Third down conversion percentage"""
        if self.third_down_attempts == 0:
            return 0.0
        return (self.third_down_conversions / self.third_down_attempts) * 100
    
    @property
    def red_zone_efficiency(self) -> float:
        """Red zone touchdown efficiency"""
        if self.red_zone_attempts == 0:
            return 0.0
        return (self.red_zone_touchdowns / self.red_zone_attempts) * 100


@dataclass  
class DriveSituation:
    """Current drive situation provided to external play callers"""
    # Drive state
    down: int
    yards_to_go: int
    field_position: int
    possessing_team_id: int
    
    # Game context (injected externally when requested)
    time_remaining: Optional[int] = None
    score_differential: Optional[int] = None  
    quarter: Optional[int] = None
    
    # Derived situational flags
    @property
    def is_first_down(self) -> bool:
        return self.down == 1
        
    @property
    def is_second_down(self) -> bool:
        return self.down == 2
        
    @property
    def is_third_down(self) -> bool:
        return self.down == 3
        
    @property
    def is_fourth_down(self) -> bool:
        return self.down == 4
        
    @property
    def is_red_zone(self) -> bool:
        return self.field_position >= 80
        
    @property
    def is_goal_to_go(self) -> bool:
        return self.field_position + self.yards_to_go >= 100
        
    @property
    def is_short_yardage(self) -> bool:
        return self.yards_to_go <= 3
        
    @property
    def is_long_yardage(self) -> bool:
        return self.yards_to_go >= 7
        
    @property
    def is_two_minute_warning(self) -> bool:
        if self.time_remaining is None:
            return False
        return self.time_remaining <= 120  # 2:00 remaining


@dataclass
class DriveResult:
    """Drive outcome with drive-specific information only"""
    # Drive status
    drive_ended: bool
    end_reason: Optional[DriveEndReason] = None
    
    # Drive identification
    possessing_team_id: int = 1
    
    # Field position tracking  
    starting_position: FieldPosition = None
    final_field_position: Optional[FieldPosition] = None
    
    # Drive statistics
    drive_stats: DriveStats = field(default_factory=DriveStats)
    
    # Scoring information
    points_scored: int = 0
    scoring_type: Optional[str] = None
    
    
    # Detailed play history
    play_by_play: List[PlayResult] = field(default_factory=list)


class DriveManagerError(Exception):
    """Custom exception for DriveManager errors"""
    pass


class DriveManager:
    """
    Focused drive simulator for embedding in game-level systems.
    
    Responsibilities:
    - Track drive state (field position, down situation)
    - Process external play results and update state
    - Maintain drive-level statistics
    - Detect drive ending conditions
    - Provide drive situation context for external play callers
    
    Does NOT handle:
    - Play calling (external)
    - Play execution (external)
    - Drive transitions (external)
    - Game clock management (external)
    - Possession determination (external)
    - Next drive setup (external)
    """
    
    def __init__(
        self, 
        starting_position: FieldPosition,
        starting_down_state: DownState,
        possessing_team_id: int
    ):
        """
        Initialize drive with starting conditions
        
        Args:
            starting_position: Starting field position for the drive
            starting_down_state: Starting down and distance situation  
            possessing_team_id: Team ID (1-32) that has possession for this drive
        """
        # Validate inputs
        if not starting_position:
            raise DriveManagerError("starting_position is required")
        if not starting_down_state:
            raise DriveManagerError("starting_down_state is required")
        if not isinstance(possessing_team_id, int) or possessing_team_id < 1 or possessing_team_id > 32:
            raise DriveManagerError("possessing_team_id must be an integer between 1 and 32")
            
        # Drive state
        self.starting_position = starting_position
        self.current_position = starting_position
        self.current_down_state = starting_down_state
        self.possessing_team_id = possessing_team_id
        
        # Drive tracking
        self.drive_ended = False
        self.end_reason: Optional[DriveEndReason] = None
        
        
        # Internal components for state management
        self.field_tracker = FieldTracker()
        self.down_tracker = DownTracker()
        
        # Statistics tracking
        self.stats = DriveStats()
        
        # Play history
        self.play_history: List[PlayResult] = []
    
    def get_possessing_team_id(self) -> int:
        """
        Get the team ID that has possession for this drive
        
        Returns:
            Team ID (1-32) that has possession
        """
        return self.possessing_team_id
    
    def get_current_situation(
        self, 
        game_context: Optional[Dict[str, Any]] = None
    ) -> DriveSituation:
        """
        Get current drive situation for external play callers
        
        Args:
            game_context: Optional dict with time_remaining, score_differential, quarter
            
        Returns:
            DriveSituation with current drive state and context
        """
        if self.drive_ended:
            raise DriveManagerError("Cannot get situation for ended drive")
            
        situation = DriveSituation(
            down=self.current_down_state.current_down,
            yards_to_go=self.current_down_state.yards_to_go,
            field_position=self.current_position.yard_line,
            possessing_team_id=self.possessing_team_id
        )
        
        # Inject game context if provided
        if game_context:
            situation.time_remaining = game_context.get('time_remaining')
            situation.score_differential = game_context.get('score_differential')
            situation.quarter = game_context.get('quarter')
            
        return situation
    
    def process_play_result(self, play_result: PlayResult) -> None:
        """
        Update drive state based on external play execution result
        
        Args:
            play_result: Result of external play execution
        """
        if self.drive_ended:
            raise DriveManagerError("Cannot process play result for ended drive")
            
        # Add to play history
        self.play_history.append(play_result)
        
        # Update statistics first
        self._update_stats(play_result)
        
        # Check for immediate drive-ending conditions
        if self._check_immediate_drive_end(play_result):
            return  # Drive ended, no need to update field/down state
            
        # Process field position changes
        field_result = self.field_tracker.process_play(
            self.current_position,
            play_result.get_net_yards()
        )
        
        # Check for scoring that ends drive
        if field_result.is_scored:
            self._end_drive_scoring(field_result, play_result)
            return
            
        # Update field position
        self.current_position = field_result.new_field_position
        
        # Process down progression  
        down_result = self.down_tracker.process_play(
            self.current_down_state,
            play_result.get_net_yards(),
            self.current_position.yard_line,
            play_result.is_scoring_play
        )
        
        # Check for missed field goals BEFORE checking turnover on downs
        if play_result.is_missed_field_goal():
            self._end_drive(DriveEndReason.FIELD_GOAL_MISSED)
            return
            
        # Check for failed punts BEFORE checking turnover on downs
        if self._is_failed_punt(play_result):
            self._end_drive(DriveEndReason.PUNT)
            return
            
        # Check for turnover on downs
        if down_result.turnover_on_downs:
            self._end_drive(DriveEndReason.TURNOVER_ON_DOWNS)
            return
            
            
        # Update down state if drive continues
        if down_result.new_down_state:
            self.current_down_state = down_result.new_down_state
            
        # Track first downs for statistics  
        if down_result.first_down_achieved:
            self.stats.first_downs_achieved += 1
    
    def is_drive_over(self) -> bool:
        """Check if drive has ended"""
        return self.drive_ended
    
    def get_drive_end_reason(self) -> Optional[DriveEndReason]:
        """Get reason why drive ended (if it has ended)"""
        return self.end_reason
    
    def get_current_stats(self) -> DriveStats:
        """Get current drive statistics (while drive is ongoing)"""
        return self.stats
    
    def get_play_history(self) -> List[PlayResult]:
        """Get list of all plays run during this drive"""
        return self.play_history.copy()
    
    def get_current_field_position(self) -> FieldPosition:
        """Get current field position"""
        return self.current_position
    
    def get_current_down_state(self) -> DownState:
        """Get current down and distance"""
        return self.current_down_state
    
    def get_drive_result(self) -> DriveResult:
        """
        Get comprehensive drive results and statistics
        
        Returns:
            DriveResult with complete drive information
        """
        return DriveResult(
            drive_ended=self.drive_ended,
            end_reason=self.end_reason,
            possessing_team_id=self.possessing_team_id,
            starting_position=self.starting_position,
            final_field_position=self.current_position,
            drive_stats=self.stats,
            points_scored=self._calculate_points_scored(),
            scoring_type=self._get_scoring_type(),
            play_by_play=self.play_history.copy()
        )
    
    def _check_immediate_drive_end(self, play_result: PlayResult) -> bool:
        """Check for play results that immediately end the drive"""
        if play_result.is_turnover:
            if play_result.turnover_type == "interception":
                self._end_drive(DriveEndReason.TURNOVER_INTERCEPTION)
            elif play_result.turnover_type == "fumble":
                self._end_drive(DriveEndReason.TURNOVER_FUMBLE)
            else:
                self._end_drive(DriveEndReason.TURNOVER_FUMBLE)  # Default
            return True
            
        if play_result.is_punt:
            self._end_drive(DriveEndReason.PUNT)
            return True
            
        if play_result.is_safety:
            self._end_drive(DriveEndReason.SAFETY)
            return True
        
        # Check for successful field goal (3 points scored)
        if play_result.is_scoring_play and play_result.points == 3:
            self._end_drive(DriveEndReason.FIELD_GOAL)
            return True
            
        return False
    
    def _is_failed_punt(self, play_result: PlayResult) -> bool:
        """Check if this was a failed punt attempt (parallel to is_missed_field_goal)"""
        # Check punt flag first
        if play_result.is_punt:
            return True
            
        # Check for punt-specific failure outcomes using enum
        punt_failure_outcomes = {
            PuntOutcomeType.PUNT_EXECUTION_FAILED.value,
            PuntOutcomeType.PUNT_BLOCKED.value,
            PuntOutcomeType.PUNT_FORMATION_INVALID.value
        }
        
        return play_result.outcome in punt_failure_outcomes
    
    def _end_drive_scoring(self, field_result, play_result: PlayResult) -> None:
        """End drive due to scoring play"""
        if field_result.scoring_type == "touchdown":
            # ✅ FIX: Update player stats with TD attribution AFTER field tracking detects scoring
            self._update_touchdown_attribution(play_result)
            self._end_drive(DriveEndReason.TOUCHDOWN)
        elif play_result.points == 3:  # Field goal
            self._end_drive(DriveEndReason.FIELD_GOAL)
        elif field_result.scoring_type == "safety":
            self._end_drive(DriveEndReason.SAFETY)

    def _update_touchdown_attribution(self, play_result: PlayResult) -> None:
        """
        Update player stats with touchdown attribution after FieldTracker detects scoring.

        This fixes the timing issue where TD attribution was happening BEFORE
        FieldTracker set points_scored = 6.

        Args:
            play_result: PlayResult with player_stats_summary containing player stats
        """
        # Check if play_result has player stats summary
        if not hasattr(play_result, 'player_stats_summary') or play_result.player_stats_summary is None:
            return

        player_stats_summary = play_result.player_stats_summary

        # Check if the summary has player_stats attribute
        if not hasattr(player_stats_summary, 'player_stats'):
            return

        # Iterate through player stats and add TDs based on play type
        for player_stat in player_stats_summary.player_stats:
            # Rushing touchdown: player had rushing attempts
            if hasattr(player_stat, 'rushing_attempts') and player_stat.rushing_attempts > 0:
                if hasattr(player_stat, 'add_rushing_touchdown'):
                    player_stat.add_rushing_touchdown()
                    print(f"✅ DriveManager: Added rushing TD to {player_stat.player_name}")

            # Passing touchdown: player had passing attempts
            if hasattr(player_stat, 'passing_attempts') and player_stat.passing_attempts > 0:
                if hasattr(player_stat, 'add_passing_touchdown'):
                    player_stat.add_passing_touchdown()
                    print(f"✅ DriveManager: Added passing TD to {player_stat.player_name}")

            # Receiving touchdown: player had receptions
            if hasattr(player_stat, 'receptions') and player_stat.receptions > 0:
                if hasattr(player_stat, 'add_receiving_touchdown'):
                    player_stat.add_receiving_touchdown()
                    print(f"✅ DriveManager: Added receiving TD to {player_stat.player_name}")


    def _end_drive(self, reason: DriveEndReason) -> None:
        """Mark drive as ended with specified reason"""
        self.drive_ended = True
        self.end_reason = reason
    
    def _update_stats(self, play_result: PlayResult) -> None:
        """Update drive statistics based on play result"""
        self.stats.plays_run += 1
        self.stats.total_yards += play_result.yards
        self.stats.net_yards += play_result.get_net_yards()
        self.stats.time_of_possession_seconds += play_result.time_elapsed
        
        # Track penalties
        if play_result.penalty_occurred:
            self.stats.penalties_committed += 1
            self.stats.penalty_yards += abs(play_result.penalty_yards)
            
        # Track situational statistics
        if self.current_down_state.current_down == 3:
            self.stats.third_down_attempts += 1
            if play_result.achieved_first_down:
                self.stats.third_down_conversions += 1
                
        if self.current_down_state.current_down == 4:
            self.stats.fourth_down_attempts += 1
            if play_result.achieved_first_down:
                self.stats.fourth_down_conversions += 1
                
        # Track red zone efficiency
        if self.current_position.yard_line >= 80:  # In red zone
            if self.stats.red_zone_attempts == 0:  # First play in red zone this drive
                self.stats.red_zone_attempts = 1
            if play_result.is_scoring_play and play_result.points == 6:  # Touchdown
                self.stats.red_zone_touchdowns += 1
    
    def _calculate_points_scored(self) -> int:
        """Calculate total points scored during this drive"""
        return sum(play.points for play in self.play_history if play.is_scoring_play)
    
    def _get_scoring_type(self) -> Optional[str]:
        """Get the type of scoring that occurred (if any)"""
        if self.end_reason == DriveEndReason.TOUCHDOWN:
            return "touchdown"
        elif self.end_reason == DriveEndReason.FIELD_GOAL:
            return "field_goal"
        elif self.end_reason == DriveEndReason.SAFETY:
            return "safety"
        return None
    
    
    
