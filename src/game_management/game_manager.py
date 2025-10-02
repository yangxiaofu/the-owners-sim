"""
Game Manager

Central orchestrator for complete NFL game simulation. Coordinates all game systems
including clock management, drive management, possession tracking, scoring, and statistics.
"""

import random
from dataclasses import dataclass
from typing import Optional, Dict, List, Tuple
from enum import Enum

from play_engine.game_state.game_clock import GameClock
from play_engine.game_state.drive_manager import DriveManager
from play_engine.game_state.possession_manager import PossessionManager
from game_management.scoreboard import Scoreboard
from play_engine.simulation.stats import PlayerStatsAccumulator, TeamStatsAccumulator
from team_management.teams.team_loader import Team


class GamePhase(Enum):
    """Current phase of the game"""
    PREGAME = "pregame"
    FIRST_QUARTER = "first_quarter"
    SECOND_QUARTER = "second_quarter"
    HALFTIME = "halftime"
    THIRD_QUARTER = "third_quarter"
    FOURTH_QUARTER = "fourth_quarter"
    OVERTIME = "overtime"
    FINAL = "final"


class CoinTossChoice(Enum):
    """Coin toss choices"""
    RECEIVE = "receive"
    DEFER = "defer"
    KICK = "kick"


@dataclass
class GameState:
    """Complete game state information"""
    home_team: Team
    away_team: Team
    phase: GamePhase
    quarter: int
    score: Dict[int, int]
    possessing_team_id: int
    time_remaining: str
    two_minute_warning: bool
    drives_completed: int
    total_plays: int


class GameManager:
    """
    Central game manager that orchestrates complete NFL game simulation.
    
    Coordinates all game systems:
    - GameClock: Time management and quarter transitions
    - DriveManager: Individual drive lifecycle management
    - PossessionManager: Possession tracking and changes
    - Scoreboard: Score tracking and game results
    - Statistics: Player and team statistics accumulation
    """
    
    def __init__(self, home_team: Team, away_team: Team):
        """
        Initialize game between two teams
        
        Args:
            home_team: Home team object with full metadata
            away_team: Away team object with full metadata
        """
        self.home_team = home_team
        self.away_team = away_team
        
        # Initialize core game systems
        self.game_clock = GameClock()
        self.scoreboard = Scoreboard(home_team.team_id, away_team.team_id)
        self.possession_manager = PossessionManager(home_team.team_id)  # Use team ID, will be updated after coin toss
        
        # Initialize statistics tracking
        self.player_stats = PlayerStatsAccumulator()
        self.team_stats = TeamStatsAccumulator()
        
        # Game state
        self.phase = GamePhase.PREGAME
        self.drives_completed = 0
        self.total_plays = 0
        self.game_log: List[str] = []
        
        # Drive management (initialized when first drive starts)
        self.current_drive: Optional[DriveManager] = None
        
        # Coin toss results (determined at game start)
        self.coin_toss_winner: Optional[int] = None
        self.opening_kickoff_team: Optional[int] = None
        self.second_half_receiving_team: Optional[int] = None
    
    def start_game(self) -> None:
        """
        Start the game with coin toss and opening kickoff setup
        """
        self.phase = GamePhase.FIRST_QUARTER
        # GameClock starts automatically in quarter 1
        
        # Conduct coin toss
        self._conduct_coin_toss()
        
        # Set up for opening kickoff
        self._setup_opening_kickoff()
        
        self._log_event(f"🏈 GAME START: {self.away_team.full_name} @ {self.home_team.full_name}")
        self._log_event(f"🪙 Coin toss: {self._get_team_name(self.coin_toss_winner)} wins the toss")
        self._log_event(f"⚡ Opening kickoff: {self._get_team_name(self.opening_kickoff_team)} kicks off")
    
    def _conduct_coin_toss(self) -> None:
        """Conduct opening coin toss with realistic NFL logic"""
        # Away team calls the toss
        self.coin_toss_winner = random.choice([self.home_team.team_id, self.away_team.team_id])
        
        # Winner typically defers to second half (70% of the time)
        if random.random() < 0.7:
            # Winner defers - opponent receives opening kickoff
            self.opening_kickoff_team = self.coin_toss_winner
            self.second_half_receiving_team = self.coin_toss_winner
            receiving_team = self.home_team.team_id if self.coin_toss_winner == self.away_team.team_id else self.away_team.team_id
        else:
            # Winner elects to receive - they get opening possession
            receiving_team = self.coin_toss_winner  
            self.opening_kickoff_team = self.home_team.team_id if self.coin_toss_winner == self.away_team.team_id else self.away_team.team_id
            self.second_half_receiving_team = self.opening_kickoff_team
        
        # Set initial possession
        self.possession_manager.set_possession(receiving_team, "opening_kickoff")
    
    def _setup_opening_kickoff(self) -> None:
        """Set up the opening kickoff"""
        # In NFL, game starts with kickoff
        # For simulation purposes, we'll assume kickoff results in a touchback
        # and the receiving team starts at their 25-yard line
        receiving_team = self.possession_manager.get_possessing_team_id()
        
        # Start first drive from 25-yard line (typical touchback)
        from src.play_engine.game_state.field_position import FieldPosition, FieldZone
        from src.play_engine.game_state.down_situation import DownState
        
        starting_position = FieldPosition(
            yard_line=25,
            possession_team=receiving_team,
            field_zone=FieldZone.OWN_TERRITORY
        )
        starting_down_state = DownState(
            current_down=1,
            yards_to_go=10,
            first_down_line=35
        )
        
        self.current_drive = DriveManager(
            starting_position=starting_position,
            starting_down_state=starting_down_state,
            possessing_team_id=receiving_team
        )
        
        self._log_event(f"📍 {self._get_team_name(receiving_team)} starts drive at their 25-yard line")
    
    def advance_quarter(self) -> bool:
        """
        Advance to next quarter/half
        
        Returns:
            True if game continues, False if game is over
        """
        current_quarter = self.game_clock.quarter
        
        if current_quarter == 2:
            # End of first half
            self.phase = GamePhase.HALFTIME
            self._handle_halftime()
            self.phase = GamePhase.THIRD_QUARTER
            self.game_clock.start_new_quarter(3)  # Start quarter 3
            return True
        elif current_quarter == 4:
            # End of regulation
            if self.scoreboard.is_tied():
                self.phase = GamePhase.OVERTIME
                self._log_event("⏰ OVERTIME: Game is tied, going to overtime")
                return True
            else:
                self.phase = GamePhase.FINAL
                self._log_event("🏁 FINAL: Game completed")
                return False
        else:
            # Regular quarter transition
            if current_quarter == 1:
                self.phase = GamePhase.SECOND_QUARTER
                self.game_clock.start_new_quarter(2)  # Start quarter 2
            elif current_quarter == 3:
                self.phase = GamePhase.FOURTH_QUARTER
                self.game_clock.start_new_quarter(4)  # Start quarter 4
            return True
    
    def _handle_halftime(self) -> None:
        """Handle halftime possession change and setup"""
        from src.play_engine.game_state.field_position import FieldPosition, FieldZone
        from src.play_engine.game_state.down_situation import DownState
        
        self._log_event("⏸️  HALFTIME")
        
        # Second half kickoff - receiving team was determined at coin toss
        if self.second_half_receiving_team:
            self.possession_manager.handle_halftime_change(self.second_half_receiving_team)
            kicking_team = self.home_team.team_id if self.second_half_receiving_team == self.away_team.team_id else self.away_team.team_id
            
            self._log_event(f"🔄 Second half: {self._get_team_name(kicking_team)} kicks off to {self._get_team_name(self.second_half_receiving_team)}")
            
            # Start new drive from kickoff result (assume touchback)
            starting_position = FieldPosition(
                yard_line=25,
                possession_team=self.second_half_receiving_team,
                field_zone=FieldZone.OWN_TERRITORY
            )
            starting_down_state = DownState(
                current_down=1,
                yards_to_go=10,
                first_down_line=35
            )
            
            self.current_drive = DriveManager(
                starting_position=starting_position,
                starting_down_state=starting_down_state,
                possessing_team_id=self.second_half_receiving_team
            )
    
    def get_game_state(self) -> GameState:
        """
        Get complete current game state
        
        Returns:
            GameState object with all current game information
        """
        return GameState(
            home_team=self.home_team,
            away_team=self.away_team,
            phase=self.phase,
            quarter=self.game_clock.quarter,
            score=self.scoreboard.get_score(),
            possessing_team_id=self.possession_manager.get_possessing_team_id(),
            time_remaining=self.game_clock.get_time_display(),
            two_minute_warning=False,  # Simplified for testing
            drives_completed=self.drives_completed,
            total_plays=self.total_plays
        )
    
    def is_game_over(self) -> bool:
        """Check if game is completed"""
        return self.phase == GamePhase.FINAL
    
    def get_winner(self) -> Optional[Team]:
        """
        Get winning team if game is complete
        
        Returns:
            Winning team object, or None if game not complete or tied
        """
        if not self.is_game_over():
            return None
        
        leading_team_id = self.scoreboard.get_leading_team()
        if leading_team_id is None:
            return None  # Tied game
        
        return self.home_team if leading_team_id == self.home_team.team_id else self.away_team
    
    def get_final_score(self) -> Dict[str, int]:
        """
        Get final score with team names
        
        Returns:
            Dictionary mapping team full names to final scores
        """
        scores = self.scoreboard.get_score()
        return {
            self.home_team.full_name: scores[self.home_team.team_id],
            self.away_team.full_name: scores[self.away_team.team_id]
        }
    
    def get_game_log(self) -> List[str]:
        """Get complete game event log"""
        return self.game_log.copy()
    
    def is_game_tied(self) -> bool:
        """
        Check if the game is currently tied
        
        Returns:
            True if both teams have the same score, False otherwise
        """
        return self.scoreboard.is_tied()
    
    def start_overtime_period(self, quarter: int, time_seconds: int, possession_team_id: Optional[int] = None) -> None:
        """
        API method to start an overtime period with specified configuration
        
        This is the clean interface that OvertimeManager uses to configure
        the game state for overtime without direct manipulation.
        
        Args:
            quarter: Quarter number for overtime (5, 6, 7, etc.)
            time_seconds: Clock time for the period (usually 900 for 15 minutes)  
            possession_team_id: Team to receive possession, None for standard overtime rules
        """
        # Update game phase to overtime
        self.phase = GamePhase.OVERTIME
        
        # Set up game clock for overtime period
        self.game_clock.start_new_quarter(quarter)
        if hasattr(self.game_clock, 'set_time_seconds'):
            self.game_clock.set_time_seconds(time_seconds)
        else:
            # Fallback if method doesn't exist - set time_remaining_seconds directly
            self.game_clock.time_remaining_seconds = time_seconds
        
        # Handle possession for overtime
        if possession_team_id is not None:
            self.possession_manager.set_possession(possession_team_id, "overtime_specified")
        else:
            self._determine_overtime_possession()
        
        # Set up initial drive for overtime (similar to opening kickoff setup)
        self._setup_overtime_drive()
        
        # Log overtime start
        self._log_event(f"🔥 OVERTIME Q{quarter}: Starting {time_seconds//60}-minute period")
    
    def _determine_overtime_possession(self) -> None:
        """
        Handle overtime possession determination using NFL rules
        
        In NFL overtime:
        - Coin toss determines who gets first possession
        - Winner of coin toss can choose to receive, kick, or defer
        - For simulation simplicity, we'll alternate from regulation or use coin toss
        """
        # Simplified: alternate possession from who didn't get opening kickoff
        # In real NFL, this would be a new coin toss
        
        if hasattr(self, 'opening_kickoff_team'):
            # Give possession to team that didn't kick off to start game
            overtime_receiving_team = self.home_team.team_id if self.opening_kickoff_team == self.away_team.team_id else self.away_team.team_id
        else:
            # Fallback: use current possession or random choice
            import random
            overtime_receiving_team = random.choice([self.home_team.team_id, self.away_team.team_id])
        
        self.possession_manager.set_possession(overtime_receiving_team, "overtime_coin_toss")
        self._log_event(f"🪙 Overtime possession: {self._get_team_name(overtime_receiving_team)} receives")
    
    def _setup_overtime_drive(self) -> None:
        """
        Set up the opening drive for overtime period
        
        Similar to opening kickoff setup but for overtime rules.
        In NFL, overtime starts with a kickoff from the 35-yard line.
        """
        receiving_team = self.possession_manager.get_possessing_team_id()
        
        # Start overtime drive from 25-yard line (typical touchback after kickoff)
        from src.play_engine.game_state.field_position import FieldPosition, FieldZone
        from src.play_engine.game_state.down_situation import DownState
        
        starting_position = FieldPosition(
            yard_line=25,
            possession_team=receiving_team,
            field_zone=FieldZone.OWN_TERRITORY
        )
        starting_down_state = DownState(
            current_down=1,
            yards_to_go=10,
            first_down_line=35
        )
        
        self.current_drive = DriveManager(
            starting_position=starting_position,
            starting_down_state=starting_down_state,
            possessing_team_id=receiving_team
        )
        
        self._log_event(f"📍 {self._get_team_name(receiving_team)} starts overtime drive at their 25-yard line")
    
    def _get_team_name(self, team_id: int) -> str:
        """Get team display name by ID"""
        if team_id == self.home_team.team_id:
            return self.home_team.full_name
        elif team_id == self.away_team.team_id:
            return self.away_team.full_name
        else:
            return f"Team {team_id}"
    
    
    def _log_event(self, event: str) -> None:
        """Add event to game log"""
        quarter_info = f"Q{self.game_clock.quarter} {self.game_clock.get_time_display()}"
        self.game_log.append(f"[{quarter_info}] {event}")
        print(f"[{quarter_info}] {event}")
    
    def __str__(self) -> str:
        """String representation of current game status"""
        state = self.get_game_state()
        return (f"{state.away_team.abbreviation} {state.score[state.away_team.team_id]} - "
                f"{state.score[state.home_team.team_id]} {state.home_team.abbreviation} "
                f"({state.phase.value.replace('_', ' ').title()})")
    
    def __repr__(self) -> str:
        """Detailed representation"""
        return f"GameManager({self.away_team.full_name} @ {self.home_team.full_name}, {self.phase.value})"