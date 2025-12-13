"""
Overtime Manager System

Modular, testable overtime management with clean API separation.
Handles different overtime rule sets (Regular Season vs Playoffs) through
dependency injection and interface-based design.

NFL Overtime Rules (2023+):
- Regular Season: 10-minute period, guaranteed possession for both teams
- Playoffs: 15-minute periods, guaranteed possession for both teams
- Exception: First team scores a TD = game ends immediately
- After both teams possess, any score wins (sudden death)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, List, Dict
from enum import Enum


class OvertimeType(Enum):
    """Types of overtime rules"""
    REGULAR_SEASON = "regular_season"
    PLAYOFFS = "playoffs"


class OvertimePhase(Enum):
    """
    Phase within an overtime period.

    NFL OT proceeds through distinct phases:
    1. GUARANTEED - Both teams must get at least one possession
    2. SUDDEN_DEATH - After both possess, any score wins
    """
    GUARANTEED = "guaranteed"      # Both teams get at least one possession
    SUDDEN_DEATH = "sudden_death"  # Any score wins


@dataclass
class OvertimeSetup:
    """
    Configuration for setting up an overtime period

    Encapsulates all parameters needed to start an overtime period,
    allowing the GameManager to configure itself without the
    GameLoopController needing to know implementation details.
    """
    quarter_number: int                # 5, 6, 7, etc.
    clock_time_seconds: int            # 600 for regular season, 900 for playoffs
    possession_team_id: Optional[int]  # None = use standard overtime possession rules
    sudden_death: bool                 # True = any score wins (after guaranteed possession)
    description: str                   # For logging/debugging


class OvertimePossessionTracker:
    """
    Tracks possessions in overtime to enforce NFL rules.

    NFL OT Rules (2023+):
    1. Both teams get at least one possession
    2. If team A scores TD on first possession → game over immediately
    3. If team A scores FG → team B gets a possession to match/beat
    4. After both possess → sudden death (any score wins)

    This tracker maintains state across drives within an OT period
    and determines when the game should end based on NFL rules.
    """

    def __init__(self, team_a_id: int, team_b_id: int):
        """
        Initialize tracker with the two teams playing.

        Args:
            team_a_id: ID of first team to possess (winner of OT coin toss)
            team_b_id: ID of second team
        """
        self.team_a_id = team_a_id
        self.team_b_id = team_b_id
        self.possessions: List[Dict] = []
        self.phase = OvertimePhase.GUARANTEED
        self.team_a_points = 0
        self.team_b_points = 0

    def record_possession(self, team_id: int, result: str, points: int) -> None:
        """
        Record a possession result.

        Args:
            team_id: Team that just possessed
            result: "touchdown", "field_goal", "turnover", "punt",
                   "turnover_on_downs", "time_expired", "safety"
            points: Points scored (6/7 for TD, 3 for FG, 0 otherwise)
        """
        self.possessions.append({
            "team_id": team_id,
            "result": result,
            "points": points,
        })

        # Track cumulative points
        if team_id == self.team_a_id:
            self.team_a_points += points
        else:
            self.team_b_points += points

        # Transition to sudden death after both teams have possessed
        if len(self.possessions) >= 2 and self.phase == OvertimePhase.GUARANTEED:
            # Check if both teams have had at least one possession
            teams_possessed = set(p["team_id"] for p in self.possessions)
            if len(teams_possessed) == 2:
                self.phase = OvertimePhase.SUDDEN_DEATH

    def should_game_end(self) -> bool:
        """
        Check if game should end based on NFL overtime rules.

        Returns:
            True if game should end, False if more play is needed
        """
        if len(self.possessions) == 0:
            return False

        first_possession = self.possessions[0]

        # Rule: TD on first possession = game over immediately
        if first_possession["result"] == "touchdown":
            return True

        # Safety on first possession also ends game (defensive score)
        if first_possession["result"] == "safety":
            return True

        # Check if both teams have possessed
        teams_possessed = set(p["team_id"] for p in self.possessions)

        if len(teams_possessed) >= 2:
            # Both teams have had at least one possession

            # If scores are different, leader wins
            if self.team_a_points != self.team_b_points:
                return True

            # Scores are tied - check for sudden death scores
            # (any score after initial possessions from both teams)
            if len(self.possessions) > 2:
                # Someone scored after both teams had their guaranteed possession
                latest = self.possessions[-1]
                if latest["points"] > 0:
                    return True

        return False

    def get_current_phase(self) -> OvertimePhase:
        """Return current OT phase."""
        return self.phase

    def get_winning_team_id(self) -> Optional[int]:
        """
        Get the winning team if game has ended.

        Returns:
            Team ID of winner, or None if game not over or tied
        """
        if not self.should_game_end():
            return None

        if self.team_a_points > self.team_b_points:
            return self.team_a_id
        elif self.team_b_points > self.team_a_points:
            return self.team_b_id
        else:
            return None  # Still tied (shouldn't happen if should_game_end is True)

    def reset(self) -> None:
        """Reset tracker for new overtime period (playoffs only)."""
        self.possessions = []
        self.phase = OvertimePhase.GUARANTEED
        self.team_a_points = 0
        self.team_b_points = 0


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
    NFL Regular Season Overtime Rules (2023+)

    - Single 10-minute overtime period (changed from 15 min in 2017)
    - GUARANTEED POSSESSION: Both teams get at least one possession
    - Exception: First team scores TD = game ends immediately
    - After both possess: any score wins (sudden death)
    - Game CAN end in tie if still tied after overtime period
    """

    # Regular season overtime is 10 minutes (changed from 15 in 2017)
    OVERTIME_DURATION_SECONDS = 10 * 60  # 600 seconds

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
        Regular season overtime ends after 1 period regardless of outcome.
        Game can end in tie if no one scores.
        """
        return False  # Never continue beyond first overtime period

    def setup_overtime_period(self) -> OvertimeSetup:
        """
        Set up 10-minute overtime period with guaranteed possession rules.

        NFL Rules (2023+):
        - 10-minute period (not 15)
        - Both teams must get at least one possession
        - TD on first possession = immediate win
        - FG on first possession = other team gets chance
        - After both possess = sudden death
        """
        if self.periods_completed >= self.max_periods:
            raise ValueError("Regular season allows maximum 1 overtime period")

        self.periods_completed += 1

        return OvertimeSetup(
            quarter_number=5,  # First overtime is quarter 5
            clock_time_seconds=self.OVERTIME_DURATION_SECONDS,  # 10 minutes
            possession_team_id=None,  # Use overtime coin toss
            sudden_death=False,  # NOT immediate sudden death - guaranteed possession first
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
    NFL Playoff Overtime Rules (2022+)

    - Multiple 15-minute overtime periods
    - GUARANTEED POSSESSION: Both teams get at least one possession per period
    - Exception: First team scores TD = game ends immediately
    - After both possess: any score wins (sudden death)
    - Game CANNOT end in tie - continues until winner determined
    """

    # Playoff overtime is 15 minutes per period
    OVERTIME_DURATION_SECONDS = 15 * 60  # 900 seconds

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
        Playoff overtime continues until someone wins.
        Cannot end in tie - keep playing until winner determined.
        """
        return self._is_game_tied(game_state)

    def setup_overtime_period(self) -> OvertimeSetup:
        """
        Set up next 15-minute playoff overtime period.

        NFL Rules (2022+):
        - 15-minute periods
        - Both teams must get at least one possession per period
        - TD on first possession = immediate win
        - FG on first possession = other team gets chance
        - After both possess = sudden death
        - If still tied after period, play another period
        """
        self.periods_completed += 1

        return OvertimeSetup(
            quarter_number=4 + self.periods_completed,  # 5, 6, 7, 8, etc.
            clock_time_seconds=self.OVERTIME_DURATION_SECONDS,  # 15 minutes
            possession_team_id=None,  # Use overtime coin toss
            sudden_death=False,  # NOT immediate sudden death - guaranteed possession first
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