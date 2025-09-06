"""
Scoreboard System

Provides clean, separated score tracking for NFL simulation games.
Handles all scoring types with proper point values and maintains
complete scoring history for analysis.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum


class ScoringType(Enum):
    """
    NFL scoring types with their point values
    
    Each scoring type maps directly to its point value for easy scoring logic.
    """
    TOUCHDOWN = 6
    FIELD_GOAL = 3
    SAFETY = 2
    EXTRA_POINT = 1
    TWO_POINT_CONVERSION = 2


@dataclass
class ScoringEvent:
    """
    Represents a single scoring event in the game
    
    Captures all relevant information about when and how points were scored.
    Useful for game analysis, statistics, and replay functionality.
    """
    team_id: int                    # Numerical team ID (1-32) that scored
    scoring_type: ScoringType       # Type of scoring play
    points: int                     # Points awarded for this event
    description: str = ""           # Optional play description
    quarter: int = 1                # Quarter when scoring occurred
    game_time: str = ""             # Game clock when scoring occurred
    
    def __post_init__(self):
        """Validate scoring event data"""
        if not 1 <= self.team_id <= 32:
            raise ValueError(f"Invalid team_id: {self.team_id}. Must be 1-32.")
        
        if not 1 <= self.quarter <= 4:  # Allow overtime later if needed
            raise ValueError(f"Invalid quarter: {self.quarter}. Must be 1-4.")
        
        if self.points != self.scoring_type.value:
            raise ValueError(f"Points mismatch: {self.points} != {self.scoring_type.value}")


class Scoreboard:
    """
    Main scoreboard class for tracking game scores
    
    Provides clean separation between scoring logic and the play engine.
    Maintains both current scores and complete scoring history.
    """
    
    def __init__(self, home_team_id: int, away_team_id: int):
        """
        Initialize scoreboard for two teams
        
        Args:
            home_team_id: Numerical ID (1-32) for home team
            away_team_id: Numerical ID (1-32) for away team
        """
        # Validate team IDs
        if not 1 <= home_team_id <= 32:
            raise ValueError(f"Invalid home_team_id: {home_team_id}. Must be 1-32.")
        if not 1 <= away_team_id <= 32:
            raise ValueError(f"Invalid away_team_id: {away_team_id}. Must be 1-32.")
        if home_team_id == away_team_id:
            raise ValueError("Home and away team IDs must be different.")
        
        self.home_team_id = home_team_id
        self.away_team_id = away_team_id
        
        # Initialize scores to zero
        self.scores: Dict[int, int] = {
            home_team_id: 0,
            away_team_id: 0
        }
        
        # Track all scoring events
        self.scoring_history: List[ScoringEvent] = []
    
    def add_score(self, team_id: int, scoring_type: ScoringType, 
                  description: str = "", quarter: int = 1, game_time: str = "") -> None:
        """
        Add points to a team's score
        
        Args:
            team_id: Team that scored (must be one of the two teams in game)
            scoring_type: Type of scoring play
            description: Optional description of the scoring play
            quarter: Quarter when scoring occurred (default: 1)
            game_time: Game clock time when scoring occurred
            
        Raises:
            ValueError: If team_id is not one of the teams in this game
        """
        if team_id not in self.scores:
            raise ValueError(f"Team {team_id} is not in this game. Valid teams: {list(self.scores.keys())}")
        
        points = scoring_type.value
        
        # Create scoring event
        event = ScoringEvent(
            team_id=team_id,
            scoring_type=scoring_type,
            points=points,
            description=description,
            quarter=quarter,
            game_time=game_time
        )
        
        # Update score and history
        self.scores[team_id] += points
        self.scoring_history.append(event)
    
    def get_score(self) -> Dict[int, int]:
        """
        Get current scores for both teams
        
        Returns:
            Dictionary mapping team_id to current score
        """
        return self.scores.copy()
    
    def get_team_score(self, team_id: int) -> int:
        """
        Get current score for a specific team
        
        Args:
            team_id: Team to get score for
            
        Returns:
            Current score for the team
            
        Raises:
            ValueError: If team_id is not in this game
        """
        if team_id not in self.scores:
            raise ValueError(f"Team {team_id} is not in this game. Valid teams: {list(self.scores.keys())}")
        
        return self.scores[team_id]
    
    def get_scoring_history(self) -> List[ScoringEvent]:
        """
        Get complete scoring history
        
        Returns:
            List of all scoring events in chronological order
        """
        return self.scoring_history.copy()
    
    def get_team_scoring_history(self, team_id: int) -> List[ScoringEvent]:
        """
        Get scoring history for a specific team
        
        Args:
            team_id: Team to get scoring history for
            
        Returns:
            List of scoring events for the specified team
        """
        if team_id not in self.scores:
            raise ValueError(f"Team {team_id} is not in this game. Valid teams: {list(self.scores.keys())}")
        
        return [event for event in self.scoring_history if event.team_id == team_id]
    
    def is_tied(self) -> bool:
        """
        Check if the game is currently tied
        
        Returns:
            True if both teams have the same score
        """
        scores = list(self.scores.values())
        return scores[0] == scores[1]
    
    def get_leading_team(self) -> Optional[int]:
        """
        Get the team ID of the currently leading team
        
        Returns:
            Team ID of leading team, or None if tied
        """
        if self.is_tied():
            return None
        
        return max(self.scores.keys(), key=lambda team: self.scores[team])
    
    def get_score_difference(self) -> int:
        """
        Get the point difference between teams
        
        Returns:
            Absolute difference in scores
        """
        scores = list(self.scores.values())
        return abs(scores[0] - scores[1])
    
    def reset_scores(self) -> None:
        """
        Reset all scores to zero (for testing or new game)
        
        Clears both current scores and scoring history.
        """
        for team_id in self.scores:
            self.scores[team_id] = 0
        self.scoring_history.clear()
    
    def __str__(self) -> str:
        """String representation of current score"""
        home_score = self.scores[self.home_team_id]
        away_score = self.scores[self.away_team_id]
        return f"Team {self.home_team_id}: {home_score}, Team {self.away_team_id}: {away_score}"
    
    def __repr__(self) -> str:
        """Detailed representation of scoreboard"""
        return f"Scoreboard(home_team={self.home_team_id}, away_team={self.away_team_id}, scores={self.scores})"