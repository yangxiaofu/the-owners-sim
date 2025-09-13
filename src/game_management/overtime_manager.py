"""
Overtime Manager System

Modular, testable overtime management with clean API separation.
Handles different overtime rule sets (Regular Season vs Playoffs) through
dependency injection and interface-based design.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
from enum import Enum


class OvertimeType(Enum):
    """Types of overtime rules"""
    REGULAR_SEASON = "regular_season"
    PLAYOFFS = "playoffs"


@dataclass
class OvertimeSetup:
    """
    Configuration for setting up an overtime period
    
    Encapsulates all parameters needed to start an overtime period,
    allowing the GameManager to configure itself without the 
    GameLoopController needing to know implementation details.
    """
    quarter_number: int                # 5, 6, 7, etc.
    clock_time_seconds: int            # Usually 900 (15 minutes)
    possession_team_id: Optional[int]  # None = use standard overtime possession rules
    sudden_death: bool                 # True = first score wins
    description: str                   # For logging/debugging


class IOvertimeManager(ABC):
    """
    Interface for overtime rule management
    
    Provides clean API separation between game flow control and 
    overtime rule logic. Different implementations can handle
    different rule sets while maintaining the same interface.
    """
    
    @abstractmethod
    def should_enter_overtime(self, game_state) -> bool:
        """
        Determines if overtime should begin based on current game state
        
        Args:
            game_state: Current GameState with scores, quarter, phase, etc.
            
        Returns:
            True if overtime should start, False if game should end
        """
        pass
    
    @abstractmethod  
    def should_continue_overtime(self, game_state) -> bool:
        """
        Determines if overtime should continue after current period
        
        Args:
            game_state: Current GameState after overtime period completion
            
        Returns:
            True if additional overtime needed, False if game can end
        """
        pass
    
    @abstractmethod
    def setup_overtime_period(self) -> OvertimeSetup:
        """
        Provides configuration for the next overtime period
        
        Returns:
            OvertimeSetup with all parameters needed to start overtime
        """
        pass
    
    @abstractmethod
    def reset(self) -> None:
        """Reset manager state for new game"""
        pass


class RegularSeasonOvertimeManager(IOvertimeManager):
    """
    NFL Regular Season Overtime Rules
    
    - Single 15-minute sudden-death period
    - Game CAN end in tie if no scoring occurs
    - First team to score wins immediately
    """
    
    def __init__(self):
        """Initialize regular season overtime manager"""
        self.periods_completed = 0
        self.max_periods = 1  # Regular season allows only 1 overtime period
    
    def should_enter_overtime(self, game_state) -> bool:
        """
        Enter overtime if:
        - Game is tied at end of regulation (quarter >= 4)
        - Haven't already played overtime period
        """
        return (game_state.quarter >= 4 and 
                self._is_game_tied(game_state) and 
                self.periods_completed == 0)
    
    def should_continue_overtime(self, game_state) -> bool:
        """
        Regular season overtime ends after 1 period regardless of outcome
        Game can end in tie if no one scores
        """
        return False  # Never continue beyond first overtime period
    
    def setup_overtime_period(self) -> OvertimeSetup:
        """Set up single 15-minute sudden-death overtime period"""
        if self.periods_completed >= self.max_periods:
            raise ValueError("Regular season allows maximum 1 overtime period")
        
        self.periods_completed += 1
        
        return OvertimeSetup(
            quarter_number=5,  # First overtime is quarter 5
            clock_time_seconds=15 * 60,  # 15 minutes
            possession_team_id=None,  # Use standard overtime coin toss
            sudden_death=True,
            description="Regular Season Overtime Period 1"
        )
    
    def reset(self) -> None:
        """Reset for new game"""
        self.periods_completed = 0
    
    def _is_game_tied(self, game_state) -> bool:
        """Check if game is currently tied"""
        scores = game_state.score
        team_ids = list(scores.keys())
        return len(team_ids) == 2 and scores[team_ids[0]] == scores[team_ids[1]]


class PlayoffOvertimeManager(IOvertimeManager):
    """
    NFL Playoff Overtime Rules
    
    - Multiple 15-minute sudden-death periods
    - Game CANNOT end in tie - continues until winner determined  
    - Each period is sudden-death (first score wins)
    """
    
    def __init__(self):
        """Initialize playoff overtime manager"""
        self.periods_completed = 0
    
    def should_enter_overtime(self, game_state) -> bool:
        """
        Enter overtime if game is tied at end of regulation
        """
        return (game_state.quarter >= 4 and 
                self._is_game_tied(game_state))
    
    def should_continue_overtime(self, game_state) -> bool:
        """
        Playoff overtime continues until someone wins
        Cannot end in tie - keep playing until winner determined
        """
        return self._is_game_tied(game_state)
    
    def setup_overtime_period(self) -> OvertimeSetup:
        """Set up next playoff overtime period"""
        self.periods_completed += 1
        
        return OvertimeSetup(
            quarter_number=4 + self.periods_completed,  # 5, 6, 7, 8, etc.
            clock_time_seconds=15 * 60,  # 15 minutes each period
            possession_team_id=None,  # Use standard overtime possession rules
            sudden_death=True,
            description=f"Playoff Overtime Period {self.periods_completed}"
        )
    
    def reset(self) -> None:
        """Reset for new game"""
        self.periods_completed = 0
    
    def _is_game_tied(self, game_state) -> bool:
        """Check if game is currently tied"""
        scores = game_state.score
        team_ids = list(scores.keys())
        return len(team_ids) == 2 and scores[team_ids[0]] == scores[team_ids[1]]


def create_overtime_manager(overtime_type: OvertimeType) -> IOvertimeManager:
    """
    Factory function to create appropriate overtime manager
    
    Args:
        overtime_type: Type of overtime rules to use
        
    Returns:
        Configured overtime manager instance
    """
    if overtime_type == OvertimeType.REGULAR_SEASON:
        return RegularSeasonOvertimeManager()
    elif overtime_type == OvertimeType.PLAYOFFS:
        return PlayoffOvertimeManager()
    else:
        raise ValueError(f"Unknown overtime type: {overtime_type}")