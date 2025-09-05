"""
Game State Manager - Unified Orchestrator

Coordinates field position and down situation tracking to provide
a complete game state management system.
"""

from dataclasses import dataclass
from typing import Optional, List
from ..simulation.stats import PlayStatsSummary
from .field_position import FieldPosition, FieldTracker, FieldResult
from .down_situation import DownState, DownTracker, DownProgressionResult


@dataclass
class GameState:
    """
    Complete game state combining field position and down situation
    """
    field_position: FieldPosition        # Current ball position on field
    down_state: DownState               # Current down and distance situation
    possessing_team: str                # Team that currently has the ball
    
    def __post_init__(self):
        """Validate game state consistency"""
        if self.field_position.possession_team != self.possessing_team:
            self.field_position.possession_team = self.possessing_team


@dataclass
class GameStateResult:
    """
    Unified result combining field position and down progression results
    
    This is the primary interface for all game state updates, preserving
    the detailed results from both field and down tracking while providing
    a clean, comprehensive view of the game state changes.
    """
    # Original play data (preserved from PlayStatsSummary)
    play_summary: PlayStatsSummary      # Original play statistics
    
    # Field tracking results
    field_result: FieldResult           # Field position changes and scoring
    
    # Down tracking results  
    down_result: DownProgressionResult  # Down progression and first down detection
    
    # Unified game state
    new_game_state: Optional[GameState] # Updated complete game state (None if possession change)
    
    # High-level game events
    drive_continues: bool               # Is the same team still driving?
    possession_changed: bool            # Did possession change to other team?
    scoring_occurred: bool              # Did any scoring happen?
    drive_ended: bool                   # Did the current drive end?
    
    # Combined events for easy access
    all_game_events: List[str]          # All events from field and down tracking
    
    def __post_init__(self):
        """Calculate high-level game state flags and combine events"""
        # Determine if drive continues
        self.drive_continues = (
            not self.possession_changed and 
            not self.scoring_occurred and
            not self.drive_ended
        )
        
        # Combine all events from field and down results
        self.all_game_events = []
        self.all_game_events.extend(self.field_result.field_events)
        self.all_game_events.extend(self.down_result.down_events)
    
    def get_points_scored(self) -> int:
        """Get total points scored on this play"""
        return self.field_result.points_scored
    
    def get_actual_yards_gained(self) -> int:
        """Get field-adjusted yards gained (may differ from raw play yards)"""
        return self.field_result.actual_yards_gained
    
    def is_first_down(self) -> bool:
        """Check if this play resulted in a first down"""
        return self.down_result.first_down_achieved
    
    def is_turnover_on_downs(self) -> bool:
        """Check if this play resulted in turnover on downs"""
        return self.down_result.turnover_on_downs


class GameStateManager:
    """
    Orchestrates field position and down situation tracking
    
    Provides a unified interface for processing play results and updating
    complete game state. Coordinates between FieldTracker and DownTracker
    while maintaining their separation of concerns.
    """
    
    def __init__(self):
        """Initialize the game state manager with trackers"""
        self.field_tracker = FieldTracker()
        self.down_tracker = DownTracker()
    
    def process_play(self, current_game_state: GameState, 
                    play_summary: PlayStatsSummary) -> GameStateResult:
        """
        Process a completed play and update complete game state
        
        Args:
            current_game_state: Current field position and down situation
            play_summary: Results from play simulation
        
        Returns:
            GameStateResult with comprehensive game state updates
        """
        # Phase 1: Process field position changes
        field_result = self.field_tracker.process_play(
            current_position=current_game_state.field_position,
            raw_yards_gained=play_summary.yards_gained,
            play_type=play_summary.play_type
        )
        
        # Phase 2: Process down situation changes
        down_result = self.down_tracker.process_play(
            current_down_state=current_game_state.down_state,
            yards_gained=field_result.actual_yards_gained,  # Use field-adjusted yards
            new_field_position=field_result.new_field_position.yard_line,
            is_scoring_play=field_result.is_scored
        )
        
        # Phase 3: Determine new game state
        new_game_state = None
        possession_changed = field_result.possession_change or down_result.possession_change
        
        if not possession_changed and down_result.new_down_state is not None:
            # Drive continues with same team
            new_game_state = GameState(
                field_position=field_result.new_field_position,
                down_state=down_result.new_down_state,
                possessing_team=current_game_state.possessing_team
            )
        
        # Phase 4: Create unified result
        result = GameStateResult(
            play_summary=play_summary,
            field_result=field_result,
            down_result=down_result,
            new_game_state=new_game_state,
            drive_continues=False,  # Will be calculated in __post_init__
            possession_changed=possession_changed,
            scoring_occurred=field_result.is_scored,
            drive_ended=possession_changed or field_result.is_scored,
            all_game_events=[]  # Will be populated in __post_init__
        )
        
        return result
    
    def process_turnover(self, current_game_state: GameState, 
                        turnover_type: str, new_possessing_team: str) -> GameStateResult:
        """
        Handle turnover situations (fumbles, interceptions, etc.)
        
        Args:
            current_game_state: Game state where turnover occurred
            turnover_type: Type of turnover ("fumble", "interception", etc.)
            new_possessing_team: Team that recovered the ball
        
        Returns:
            GameStateResult with possession change and field position flip
        """
        # Process field position change due to turnover
        field_result = self.field_tracker.process_turnover(
            current_position=current_game_state.field_position,
            turnover_type=turnover_type
        )
        
        # Update possession team in field result
        field_result.new_field_position.possession_team = new_possessing_team
        
        # Create new drive for recovering team
        new_down_state = self.down_tracker.create_new_drive(
            starting_field_position=field_result.new_field_position.yard_line
        )
        
        # Create new game state with possession change
        new_game_state = GameState(
            field_position=field_result.new_field_position,
            down_state=new_down_state,
            possessing_team=new_possessing_team
        )
        
        # Create mock play summary for turnover
        turnover_play_summary = PlayStatsSummary(
            play_type=f"turnover_{turnover_type}",
            yards_gained=0,
            time_elapsed=0.0
        )
        
        # Create down result for turnover
        from .down_situation import DownResult
        down_result = DownProgressionResult(
            new_down_state=new_down_state,
            down_result=DownResult.CONTINUE_DRIVE,
            possession_change=True,
            down_events=[turnover_type, "new_drive_started"]
        )
        
        result = GameStateResult(
            play_summary=turnover_play_summary,
            field_result=field_result,
            down_result=down_result,
            new_game_state=new_game_state,
            drive_continues=False,  # Will be calculated in __post_init__
            possession_changed=True,
            scoring_occurred=False,
            drive_ended=True,
            all_game_events=[]  # Will be populated in __post_init__
        )
        
        return result
    
    def create_new_drive(self, starting_field_position: int, 
                        possessing_team: str) -> GameState:
        """
        Create a new drive state (typically after kickoff, punt, etc.)
        
        Args:
            starting_field_position: Yard line where drive begins
            possessing_team: Team starting the new drive
        
        Returns:
            GameState for beginning of new possession
        """
        field_position = FieldPosition(
            yard_line=starting_field_position,
            possession_team=possessing_team,
            field_zone=None  # Will be auto-calculated
        )
        
        down_state = self.down_tracker.create_new_drive(starting_field_position)
        
        return GameState(
            field_position=field_position,
            down_state=down_state,
            possessing_team=possessing_team
        )