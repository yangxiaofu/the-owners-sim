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
    previous_team: str
    new_team: str
    reason: str
    timestamp: datetime
    
    def __str__(self) -> str:
        return f"{self.previous_team} → {self.new_team} ({self.reason})"


class PossessionManager:
    """
    Simple possession tracking manager
    
    Maintains clean separation of concerns by ONLY tracking which team
    has possession of the ball. Does not handle field position, drives,
    downs, or any other game state - those are managed by other components.
    """
    
    def __init__(self, initial_team: str):
        """
        Initialize possession manager with starting team
        
        Args:
            initial_team: Team that starts with possession
        """
        if not initial_team or not initial_team.strip():
            raise ValueError("Initial team cannot be empty")
        
        self.current_team = initial_team.strip()
        self.initial_team = self.current_team  # Track who started with possession
        self.possession_history: List[PossessionChange] = []
    
    def get_possessing_team(self) -> str:
        """
        Get the team that currently has possession
        
        Returns:
            Current possessing team name
        """
        return self.current_team
    
    def change_possession(self, new_team: str, reason: str = "") -> None:
        """
        Change possession to a new team
        
        Args:
            new_team: Team receiving possession
            reason: Optional reason for the possession change
        """
        if not new_team or not new_team.strip():
            raise ValueError("New team cannot be empty")
        
        new_team = new_team.strip()
        
        # Only change if different team
        if new_team == self.current_team:
            return
        
        # Record the possession change
        change = PossessionChange(
            previous_team=self.current_team,
            new_team=new_team,
            reason=reason.strip() if reason else "possession_change",
            timestamp=datetime.now()
        )
        
        # Update current possession
        self.current_team = new_team
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
    
    def get_possession_count(self, team: str) -> int:
        """
        Count how many times a team has had possession
        
        Args:
            team: Team to count possessions for
            
        Returns:
            Number of times team has had possession (including current if applicable)
        """
        if not team:
            return 0
        
        team = team.strip()
        count = 0
        
        # Count times team gained possession from history (appears as new_team)
        for change in self.possession_history:
            if change.new_team == team:
                count += 1
        
        # Add 1 if this was the initial team (started with possession)
        if team == self.initial_team:
            count += 1
            
        return count
    
    def __str__(self) -> str:
        """String representation showing current possession"""
        return f"Possession: {self.current_team}"
    
    def __repr__(self) -> str:
        """Detailed representation with history count"""
        history_count = len(self.possession_history)
        return f"PossessionManager(current={self.current_team}, changes={history_count})"