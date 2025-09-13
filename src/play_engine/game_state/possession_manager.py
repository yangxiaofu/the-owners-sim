"""
Possession Manager - Simple Ball Possession Tracking

Tracks only "who has the ball" with clean separation from field positioning,
drive management, and down tracking. This manager answers one question:
"Which team currently possesses the ball?"
"""

from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime


@dataclass
class PossessionChange:
    """
    Record of a possession change event
    """
    previous_team_id: int
    new_team_id: int
    reason: str
    timestamp: datetime
    
    def __str__(self) -> str:
        return f"Team {self.previous_team_id} → Team {self.new_team_id} ({self.reason})"


class PossessionManager:
    """
    Simple possession tracking manager
    
    Maintains clean separation of concerns by ONLY tracking which team
    has possession of the ball. Does not handle field position, drives,
    downs, or any other game state - those are managed by other components.
    """
    
    def __init__(self, initial_team_id: int):
        """
        Initialize possession manager with starting team
        
        Args:
            initial_team_id: Team ID (1-32) that starts with possession
        """
        if not isinstance(initial_team_id, int) or initial_team_id < 1 or initial_team_id > 32:
            raise ValueError("Initial team ID must be an integer between 1 and 32")
        
        self.current_team_id = initial_team_id
        self.initial_team_id = self.current_team_id  # Track who started with possession
        self.possession_history: List[PossessionChange] = []
    
    def get_possessing_team_id(self) -> int:
        """
        Get the team ID that currently has possession
        
        Returns:
            Current possessing team ID (1-32)
        """
        return self.current_team_id
    
    def set_possession(self, new_team_id: int, reason: str = "") -> None:
        """
        Set possession to a new team
        
        Args:
            new_team_id: Team ID (1-32) receiving possession
            reason: Optional reason for the possession change
        """
        if not isinstance(new_team_id, int) or new_team_id < 1 or new_team_id > 32:
            raise ValueError("New team ID must be an integer between 1 and 32")
        
        # Only change if different team
        if new_team_id == self.current_team_id:
            return
        
        # Record the possession change
        change = PossessionChange(
            previous_team_id=self.current_team_id,
            new_team_id=new_team_id,
            reason=reason.strip() if reason else "possession_change",
            timestamp=datetime.now()
        )
        
        # Update current possession
        self.current_team_id = new_team_id
        self.possession_history.append(change)
    
    def get_possession_history(self) -> List[PossessionChange]:
        """
        Get complete history of possession changes
        
        Returns:
            List of all possession changes in chronological order
        """
        return self.possession_history.copy()
    
    def get_recent_possession_changes(self, count: int = 5) -> List[PossessionChange]:
        """
        Get recent possession changes
        
        Args:
            count: Number of recent changes to return
            
        Returns:
            List of most recent possession changes
        """
        return self.possession_history[-count:] if self.possession_history else []
    
    def has_possession_changed(self) -> bool:
        """
        Check if possession has ever changed
        
        Returns:
            True if there have been any possession changes
        """
        return len(self.possession_history) > 0
    
    def get_possession_count(self, team_id: int) -> int:
        """
        Count how many times a team has had possession
        
        Args:
            team_id: Team ID (1-32) to count possessions for
            
        Returns:
            Number of times team has had possession (including current if applicable)
        """
        if not isinstance(team_id, int) or team_id < 1 or team_id > 32:
            return 0
        
        count = 0
        
        # Count times team gained possession from history (appears as new_team_id)
        for change in self.possession_history:
            if change.new_team_id == team_id:
                count += 1
        
        # Add 1 if this was the initial team (started with possession)
        if team_id == self.initial_team_id:
            count += 1
            
        return count
    
    def handle_halftime_change(self, opposing_team_id: int) -> None:
        """
        Handle halftime possession change to opposing team
        
        At halftime, possession automatically goes to the team that did NOT
        receive the opening kickoff, matching NFL rules.
        
        Args:
            opposing_team_id: Team ID (1-32) that should receive possession at halftime
        """
        if not isinstance(opposing_team_id, int) or opposing_team_id < 1 or opposing_team_id > 32:
            raise ValueError("Opposing team ID must be an integer between 1 and 32")
        
        # Change possession to opposing team with halftime reason
        self.set_possession(opposing_team_id, "halftime")
    
    def get_opposing_team_id(self, team_a_id: int, team_b_id: int) -> int:
        """
        Helper to determine which team is the opposing team given current possession
        
        Args:
            team_a_id: First team ID (1-32)
            team_b_id: Second team ID (1-32)
            
        Returns:
            The team ID that does NOT currently have possession
            
        Raises:
            ValueError: If current team is not one of the provided teams
        """
        if not isinstance(team_a_id, int) or not isinstance(team_b_id, int):
            raise ValueError("Both team IDs must be integers")
        if team_a_id < 1 or team_a_id > 32 or team_b_id < 1 or team_b_id > 32:
            raise ValueError("Team IDs must be between 1 and 32")
            
        if self.current_team_id == team_a_id:
            return team_b_id
        elif self.current_team_id == team_b_id:
            return team_a_id
        else:
            raise ValueError(f"Current team ID '{self.current_team_id}' is not one of the provided team IDs: {team_a_id}, {team_b_id}")
    
    def check_play_result_for_possession_change(self, play_result) -> bool:
        """
        Analyze a PlayResult to determine if possession should change
        
        This method examines the PlayResult fields to determine if possession
        should change teams based on NFL rules.
        
        Args:
            play_result: PlayResult object to analyze
            
        Returns:
            True if possession should change, False otherwise
        """
        # Import here to avoid circular imports
        from ..core.play_result import PlayResult
        
        if not isinstance(play_result, PlayResult):
            return False
        
        # Explicit possession change flag (highest priority)
        if hasattr(play_result, 'change_of_possession') and play_result.change_of_possession:
            return True
        
        # Turnovers always change possession
        if hasattr(play_result, 'is_turnover') and play_result.is_turnover:
            return True
            
        # Punts change possession (punt team to receiving team)
        if hasattr(play_result, 'is_punt') and play_result.is_punt:
            return True
            
        # Safety changes possession (scoring team gets possession via free kick)
        if hasattr(play_result, 'is_safety') and play_result.is_safety:
            return True
        
        # Scoring plays generally change possession (touchdowns, field goals)
        # Exception: Safety already handled above
        if hasattr(play_result, 'is_scoring_play') and play_result.is_scoring_play:
            # Field goals and touchdowns typically result in kickoff to opposing team
            return True
            
        # Missed field goals that are returnable may change possession
        if hasattr(play_result, 'is_missed_field_goal') and callable(play_result.is_missed_field_goal):
            if play_result.is_missed_field_goal():
                return True
        
        # Check specific outcomes that indicate possession changes
        if hasattr(play_result, 'outcome'):
            possession_changing_outcomes = [
                "touchback",                    # Kickoff result
                "onside_recovery",              # Successful onside kick recovery
                "kickoff_return_touchdown",     # Kickoff return TD
                "blocked",                      # Blocked punt/FG (may change possession)
                "punt_blocked",                 # Specifically blocked punt
                "field_goal_blocked"            # Blocked field goal
            ]
            
            if play_result.outcome in possession_changing_outcomes:
                return True
        
        # No possession change needed
        return False
    
    def __str__(self) -> str:
        """String representation showing current possession"""
        return f"Possession: Team {self.current_team_id}"
    
    def __repr__(self) -> str:
        """Detailed representation with history count"""
        history_count = len(self.possession_history)
        return f"PossessionManager(current={self.current_team_id}, changes={history_count})"