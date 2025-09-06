"""
Drive Manager - Drive Lifecycle Management

Manages drive state transitions, statistics tracking, and drive ending decisions
based on comprehensive game context. Uses DriveManagerParams to enforce 
complete contextual information for all drive assessments.
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from enum import Enum
from .game_state_manager import GameStateResult
from .game_clock import GameClock
from ..simulation.stats import PlayStatsSummary


class DriveEndReason(Enum):
    """Reasons why a drive can end"""
    TOUCHDOWN = "touchdown"
    FIELD_GOAL = "field_goal"
    TURNOVER_INTERCEPTION = "turnover_interception"
    TURNOVER_FUMBLE = "turnover_fumble"
    TURNOVER_ON_DOWNS = "turnover_on_downs"
    PUNT = "punt"
    SAFETY = "safety"
    END_OF_HALF = "end_of_half"
    END_OF_GAME = "end_of_game"
    END_OF_OVERTIME = "end_of_overtime"


class DriveStatus(Enum):
    """Current status of a drive"""
    ACTIVE = "active"
    ENDED = "ended"



@dataclass
class ScoreContext:
    """Current game score context"""
    home_score: int
    away_score: int
    possessing_team_is_home: bool
    
    def __post_init__(self):
        """Validate score parameters"""
        if self.home_score < 0:
            raise ValueError(f"Invalid home_score: {self.home_score}. Must be >= 0")
        if self.away_score < 0:
            raise ValueError(f"Invalid away_score: {self.away_score}. Must be >= 0")
    
    @property
    def score_differential(self) -> int:
        """Score differential from possessing team's perspective (positive = leading)"""
        if self.possessing_team_is_home:
            return self.home_score - self.away_score
        else:
            return self.away_score - self.home_score
    
    @property
    def is_tied(self) -> bool:
        return self.home_score == self.away_score


@dataclass
class DriveManagerParams:
    """
    Complete contextual parameters required for drive management decisions.
    
    This enforces the "complete context or fail" philosophy - all drive
    assessments must have full game context to make accurate decisions.
    """
    # Play outcome data
    game_state_result: GameStateResult      # What happened on the play
    
    # Game timing context
    game_clock: GameClock                   # Current game time situation
    
    # Score context
    score_context: ScoreContext             # Current score and team perspective
    
    # Field context (extracted from game_state_result for convenience)
    field_position: int                     # Current yard line (0-100)
    possessing_team: str                    # Team with possession
    
    def __post_init__(self):
        """Validate parameter consistency and completeness"""
        # Check required parameters exist
        if not self.game_state_result:
            raise ValueError("DriveManagerParams requires game_state_result")
        if not self.game_clock:
            raise ValueError("DriveManagerParams requires game_clock")
        if not self.score_context:
            raise ValueError("DriveManagerParams requires score_context")
        
        # Validate field position
        if not 0 <= self.field_position <= 100:
            raise ValueError(f"Invalid field_position: {self.field_position}. Must be 0-100")
        
        if not self.possessing_team:
            raise ValueError("DriveManagerParams requires possessing_team")
        
        # Check consistency between parameters
        if self.game_state_result.new_game_state:
            gs_field_pos = self.game_state_result.new_game_state.field_position.yard_line
            if abs(gs_field_pos - self.field_position) > 1:  # Allow small rounding differences
                raise ValueError(f"Inconsistent field position: game_state={gs_field_pos}, param={self.field_position}")


@dataclass
class DriveStats:
    """Statistics for a single drive"""
    drive_number: int
    starting_field_position: int
    current_field_position: int
    possessing_team: str
    plays_run: int = 0
    total_yards: int = 0
    passing_yards: int = 0
    rushing_yards: int = 0
    first_downs: int = 0
    penalties: int = 0
    penalty_yards: int = 0
    time_of_possession_seconds: int = 0
    drive_started_quarter: int = 1
    drive_started_time: int = 900  # 15:00 in seconds
    
    def add_play_stats(self, play_stats: PlayStatsSummary, yards_gained: int):
        """Add stats from a single play to the drive totals"""
        self.plays_run += 1
        self.total_yards += yards_gained
        self.time_of_possession_seconds += int(play_stats.time_elapsed)
        
        # Add play type specific yards
        if play_stats.play_type.upper() in ['PASS', 'PLAY_ACTION_PASS', 'SCREEN_PASS']:
            self.passing_yards += yards_gained
        elif play_stats.play_type.upper() == 'RUN':
            self.rushing_yards += yards_gained
        
        # Track penalties
        if play_stats.penalty_occurred:
            self.penalties += 1
            # Calculate penalty yards (difference between original and final yards)
            if play_stats.original_yards is not None:
                penalty_impact = play_stats.original_yards - play_stats.yards_gained
                self.penalty_yards += abs(penalty_impact)


@dataclass
class DriveAssessmentResult:
    """Result of drive status assessment"""
    is_drive_ended: bool
    drive_status: DriveStatus
    end_reason: Optional[DriveEndReason]
    drive_stats: DriveStats
    next_possession_team: Optional[str]
    requires_game_end: bool = False        # Drive end also ends game
    requires_half_end: bool = False        # Drive end also ends half
    
    @property
    def drive_continues(self) -> bool:
        """True if drive is still active"""
        return self.drive_status == DriveStatus.ACTIVE


class Drive:
    """Represents a single drive with all its plays and statistics"""
    
    def __init__(self, drive_number: int, starting_position: int, possessing_team: str, 
                 starting_quarter: int, starting_time: int):
        self.drive_number = drive_number
        self.starting_position = starting_position
        self.possessing_team = possessing_team
        self.status = DriveStatus.ACTIVE
        self.end_reason: Optional[DriveEndReason] = None
        
        # Initialize drive stats
        self.stats = DriveStats(
            drive_number=drive_number,
            starting_field_position=starting_position,
            current_field_position=starting_position,
            possessing_team=possessing_team,
            drive_started_quarter=starting_quarter,
            drive_started_time=starting_time
        )
        
        # Play history
        self.plays: List[GameStateResult] = []
    
    def add_play(self, game_state_result: GameStateResult):
        """Add a play result to this drive"""
        self.plays.append(game_state_result)
        
        # Update drive stats
        if game_state_result.new_game_state:
            self.stats.current_field_position = game_state_result.new_game_state.field_position.yard_line
        
        # Add play statistics
        yards_gained = game_state_result.get_actual_yards_gained()
        self.stats.add_play_stats(game_state_result.play_summary, yards_gained)
        
        # Track first downs
        if game_state_result.is_first_down():
            self.stats.first_downs += 1
    
    def end_drive(self, reason: DriveEndReason):
        """Mark drive as ended with specified reason"""
        self.status = DriveStatus.ENDED
        self.end_reason = reason


class DriveManagerError(Exception):
    """Custom exception for DriveManager errors"""
    pass


class DriveManager:
    """
    Manages drive lifecycle, statistics, and ending decisions based on
    comprehensive game context provided via DriveManagerParams.
    """
    
    def __init__(self):
        self.current_drive: Optional[Drive] = None
        self.drive_history: List[Drive] = []
        self._drive_counter = 0
    
    def start_new_drive(self, starting_position: int, possessing_team: str,
                       starting_quarter: int, starting_time: int) -> Drive:
        """Start a new drive with the given parameters"""
        self._drive_counter += 1
        
        # End current drive if one exists
        if self.current_drive and self.current_drive.status == DriveStatus.ACTIVE:
            # This shouldn't happen in normal flow - current drive should be ended first
            raise DriveManagerError("Cannot start new drive while another drive is active")
        
        # Create new drive
        self.current_drive = Drive(
            drive_number=self._drive_counter,
            starting_position=starting_position,
            possessing_team=possessing_team,
            starting_quarter=starting_quarter,
            starting_time=starting_time
        )
        
        return self.current_drive
    
    def assess_drive_status(self, params: DriveManagerParams) -> DriveAssessmentResult:
        """
        Assess whether the drive should continue or end based on complete game context.
        
        This is the core decision-making function that uses all available context
        to determine drive status.
        """
        if not self.current_drive:
            raise DriveManagerError("No active drive to assess")
        
        # Add this play to the current drive
        self.current_drive.add_play(params.game_state_result)
        
        # Check for drive-ending conditions in priority order
        
        # 1. Time-based endings (highest priority)
        if params.game_clock.is_end_of_game:
            return self._end_drive_with_game_end(DriveEndReason.END_OF_GAME, params)
        
        if params.game_clock.is_end_of_half:
            return self._end_drive_with_half_end(DriveEndReason.END_OF_HALF, params)
        
        # 2. Scoring plays
        if params.game_state_result.scoring_occurred:
            points = params.game_state_result.get_points_scored()
            if points == 6:  # Touchdown
                return self._end_drive(DriveEndReason.TOUCHDOWN, params)
            elif points == 3:  # Field Goal
                return self._end_drive(DriveEndReason.FIELD_GOAL, params)
            elif points == 2:  # Safety
                return self._end_drive(DriveEndReason.SAFETY, params)
        
        # 3. Possession changes (turnovers)
        if params.game_state_result.possession_changed:
            # Determine turnover type from play stats
            play_stats = params.game_state_result.play_summary
            if "interception" in play_stats.play_type.lower():
                return self._end_drive(DriveEndReason.TURNOVER_INTERCEPTION, params)
            elif "fumble" in play_stats.play_type.lower():
                return self._end_drive(DriveEndReason.TURNOVER_FUMBLE, params)
            elif params.game_state_result.is_turnover_on_downs():
                return self._end_drive(DriveEndReason.TURNOVER_ON_DOWNS, params)
            elif "punt" in play_stats.play_type.lower():
                return self._end_drive(DriveEndReason.PUNT, params)
            else:
                # Generic possession change
                return self._end_drive(DriveEndReason.TURNOVER_FUMBLE, params)  # Default assumption
        
        # 4. If no drive-ending conditions, drive continues
        return DriveAssessmentResult(
            is_drive_ended=False,
            drive_status=DriveStatus.ACTIVE,
            end_reason=None,
            drive_stats=self.current_drive.stats,
            next_possession_team=None
        )
    
    def _end_drive(self, reason: DriveEndReason, params: DriveManagerParams) -> DriveAssessmentResult:
        """End the current drive with specified reason"""
        if not self.current_drive:
            raise DriveManagerError("No active drive to end")
        
        # End the drive
        self.current_drive.end_drive(reason)
        
        # Add to history
        self.drive_history.append(self.current_drive)
        
        # Determine next possession team
        next_possession = self._determine_next_possession(reason, params)
        
        # Create result
        result = DriveAssessmentResult(
            is_drive_ended=True,
            drive_status=DriveStatus.ENDED,
            end_reason=reason,
            drive_stats=self.current_drive.stats,
            next_possession_team=next_possession
        )
        
        # Clear current drive
        self.current_drive = None
        
        return result
    
    def _end_drive_with_game_end(self, reason: DriveEndReason, params: DriveManagerParams) -> DriveAssessmentResult:
        """End drive and mark that game also ends"""
        result = self._end_drive(reason, params)
        result.requires_game_end = True
        return result
    
    def _end_drive_with_half_end(self, reason: DriveEndReason, params: DriveManagerParams) -> DriveAssessmentResult:
        """End drive and mark that half also ends"""
        result = self._end_drive(reason, params)
        result.requires_half_end = True
        return result
    
    def _determine_next_possession(self, reason: DriveEndReason, params: DriveManagerParams) -> Optional[str]:
        """Determine which team gets possession after drive ends"""
        current_team = params.possessing_team
        
        # For most turnovers, possession goes to the other team
        if reason in [DriveEndReason.TURNOVER_INTERCEPTION, 
                     DriveEndReason.TURNOVER_FUMBLE, 
                     DriveEndReason.TURNOVER_ON_DOWNS,
                     DriveEndReason.PUNT]:
            return self._get_opponent_team(current_team)
        
        # For scoring plays, determine based on game rules
        elif reason == DriveEndReason.TOUCHDOWN:
            return self._get_opponent_team(current_team)  # Kickoff to opponent
        elif reason == DriveEndReason.FIELD_GOAL:
            return self._get_opponent_team(current_team)  # Kickoff to opponent
        elif reason == DriveEndReason.SAFETY:
            return current_team  # Team that was scored against gets free kick
        
        # For game/half endings, next possession may not be relevant
        elif reason in [DriveEndReason.END_OF_GAME, DriveEndReason.END_OF_HALF]:
            return None  # Will be determined by game flow controller
        
        return None
    
    def _get_opponent_team(self, team: str) -> str:
        """Get the opponent team name (simplified for now)"""
        # This is a simplified implementation - in real system would need
        # proper team mapping
        return "Opponent" if team != "Opponent" else "Home"
    
    def get_current_drive(self) -> Optional[Drive]:
        """Get the currently active drive"""
        return self.current_drive
    
    def get_drive_history(self) -> List[Drive]:
        """Get all completed drives"""
        return self.drive_history.copy()
    
    def get_drive_count(self) -> int:
        """Get total number of drives (completed + current)"""
        return self._drive_counter
    
    def has_active_drive(self) -> bool:
        """Check if there is currently an active drive"""
        return self.current_drive is not None and self.current_drive.status == DriveStatus.ACTIVE