from dataclasses import dataclass
from typing import Optional

from ....field.game_state import GameState


@dataclass
class GameContext:
    """
    Encapsulates all game situation data needed for clock strategy decisions.
    
    This context object provides a comprehensive snapshot of the current game
    situation that clock management strategies can use to make informed decisions.
    """
    
    # Core game state
    score_differential: int  # Positive = leading, Negative = trailing, 0 = tied
    time_remaining: int      # Seconds remaining in current quarter
    quarter: int            # Current quarter (1-4)
    down: int              # Current down (1-4)
    yards_to_go: int       # Yards needed for first down
    field_position: int    # Yard line (1-100, towards opponent's goal)
    possession_team_id: Optional[int]  # ID of team with possession
    
    # Situational flags - computed during initialization
    is_two_minute_drill: bool = False      # Within 2 minutes of half/game end
    is_final_minute: bool = False          # Within 1 minute of quarter end
    is_leading: bool = False              # Team has positive score differential
    is_trailing: bool = False             # Team has negative score differential
    is_tied: bool = False                 # Game is tied
    is_fourth_down: bool = False          # Currently 4th down
    is_short_yardage: bool = False        # 3 yards or less to go
    is_goal_line: bool = False            # In red zone (80+ yard line)
    is_late_game: bool = False            # 4th quarter
    is_critical_time: bool = False        # Late in game with close score
    is_blowout: bool = False              # Large score differential (21+ points)
    
    @classmethod
    def from_game_state(cls, game_state: GameState, team_id: Optional[int] = None) -> 'GameContext':
        """
        Factory method to create GameContext from game state components.
        
        Args:
            game_state: The current game state containing field, clock, and scoreboard
            team_id: The team ID for perspective-based calculations (optional)
            
        Returns:
            GameContext instance with all situational flags properly set
        """
        # Use possession team if no specific team_id provided
        perspective_team_id = team_id or game_state.field.possession_team_id
        
        # Calculate score differential from the perspective team's view
        if perspective_team_id is not None:
            score_diff = game_state.scoreboard.get_score_differential(perspective_team_id)
        else:
            # If no team perspective, use absolute differential
            home_score, away_score = game_state.scoreboard.get_score()
            score_diff = home_score - away_score
        
        # Create base context with core data
        context = cls(
            score_differential=score_diff,
            time_remaining=game_state.clock.clock,
            quarter=game_state.clock.quarter,
            down=game_state.field.down,
            yards_to_go=game_state.field.yards_to_go,
            field_position=game_state.field.field_position,
            possession_team_id=game_state.field.possession_team_id
        )
        
        # Set situational flags
        context._analyze_situation()
        
        return context
    
    def _analyze_situation(self) -> None:
        """
        Analyze the current game situation and set all boolean flags.
        
        This method examines the core game state data and derives situational
        context that clock management strategies need for decision making.
        """
        # Time-based situations
        self.is_two_minute_drill = self._is_two_minute_situation()
        self.is_final_minute = self.time_remaining <= 60
        self.is_late_game = self.quarter >= 4
        
        # Score-based situations
        self.is_leading = self.score_differential > 0
        self.is_trailing = self.score_differential < 0
        self.is_tied = self.score_differential == 0
        self.is_blowout = abs(self.score_differential) >= 21
        
        # Field situation
        self.is_fourth_down = self.down == 4
        self.is_short_yardage = self.yards_to_go <= 3
        self.is_goal_line = self.field_position >= 80
        
        # Composite situations
        self.is_critical_time = self._is_critical_time_situation()
    
    def _is_two_minute_situation(self) -> bool:
        """Check if we're in a two-minute drill scenario."""
        return (
            (self.quarter == 2 and self.time_remaining <= 120) or  # End of 1st half
            (self.quarter == 4 and self.time_remaining <= 120)     # End of game
        )
    
    def _is_critical_time_situation(self) -> bool:
        """
        Determine if this is a critical time situation requiring careful clock management.
        
        Critical time is defined as late in the game with a close score where
        every possession and time decision matters significantly.
        """
        close_game = abs(self.score_differential) <= 14  # Within two touchdowns
        late_in_game = (
            (self.quarter == 4 and self.time_remaining <= 480) or  # Last 8 minutes of 4th
            (self.quarter == 4 and self.time_remaining <= 120) or  # Last 2 minutes
            (self.quarter == 2 and self.time_remaining <= 120)     # End of half
        )
        
        return close_game and late_in_game
    
    def get_time_pressure_level(self) -> str:
        """
        Get a descriptive string for the current time pressure level.
        
        Returns:
            String describing time pressure: 'none', 'low', 'medium', 'high', 'critical'
        """
        if self.is_two_minute_drill:
            return 'critical'
        elif self.is_final_minute:
            return 'high'
        elif self.is_critical_time:
            return 'medium'
        elif self.is_late_game and abs(self.score_differential) <= 7:
            return 'low'
        else:
            return 'none'
    
    def should_preserve_clock(self) -> bool:
        """
        Determine if the team should generally try to preserve clock time.
        
        This is typically true when leading late in the game.
        """
        return self.is_leading and (self.is_late_game or self.is_critical_time)
    
    def should_hurry_up(self) -> bool:
        """
        Determine if the team should generally try to move quickly.
        
        This is typically true when trailing and time is running short.
        """
        return self.is_trailing and (self.is_two_minute_drill or self.is_critical_time)
    
    def __str__(self) -> str:
        """Human-readable representation of the game context."""
        score_desc = "tied"
        if self.is_leading:
            score_desc = f"leading by {self.score_differential}"
        elif self.is_trailing:
            score_desc = f"trailing by {abs(self.score_differential)}"
        
        minutes = self.time_remaining // 60
        seconds = self.time_remaining % 60
        time_desc = f"{minutes:02d}:{seconds:02d}"
        
        return (f"Q{self.quarter} {time_desc} - {score_desc} - "
                f"{self.down} & {self.yards_to_go} at {self.field_position}")