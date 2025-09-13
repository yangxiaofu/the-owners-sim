"""
Game Simulation Event

Integration between the calendar manager and the existing FullGameSimulator.
This event wraps the sophisticated NFL game simulation system to work within
the daily calendar system.
"""

from datetime import datetime
from typing import Dict, Any, Optional

from .base_simulation_event import BaseSimulationEvent, SimulationResult, EventType

# Import dependencies with fallback handling
try:
    from src.game_management.full_game_simulator import FullGameSimulator
    FULL_GAME_SIMULATOR_AVAILABLE = True
except ImportError:
    try:
        # Alternative import path
        import sys
        from pathlib import Path
        sys.path.append(str(Path(__file__).parent.parent.parent))
        from game_management.full_game_simulator import FullGameSimulator
        FULL_GAME_SIMULATOR_AVAILABLE = True
    except ImportError:
        print("⚠️  FullGameSimulator not available - GameSimulationEvent will use placeholder")
        FULL_GAME_SIMULATOR_AVAILABLE = False

try:
    from src.constants.team_ids import TeamIDs
except ImportError:
    try:
        from constants.team_ids import TeamIDs
    except ImportError:
        print("⚠️  TeamIDs not available - using fallback team mapping")
        # Fallback team mapping
        class TeamIDs:
            DETROIT_LIONS = 22
            GREEN_BAY_PACKERS = 12
            CHICAGO_BEARS = 6


class GameSimulationEvent(BaseSimulationEvent):
    """
    NFL Game simulation event that integrates with existing FullGameSimulator.
    
    This event wraps the existing game simulation logic to work within the
    calendar manager system, allowing games to be scheduled and executed
    as part of daily simulation progression.
    """
    
    def __init__(self, date: datetime, away_team_id: int, home_team_id: int,
                 week: int = 1, season_type: str = "regular_season",
                 overtime_type: str = "regular_season"):
        """
        Initialize NFL game simulation event
        
        Args:
            date: When this game is scheduled
            away_team_id: Away team ID (1-32)
            home_team_id: Home team ID (1-32) 
            week: Week number in season
            season_type: Type of season (preseason, regular_season, playoffs)
            overtime_type: Overtime rules (regular_season or playoffs)
        """
        # Validate team IDs
        if not (1 <= away_team_id <= 32):
            raise ValueError(f"Away team ID must be 1-32, got {away_team_id}")
        if not (1 <= home_team_id <= 32):
            raise ValueError(f"Home team ID must be 1-32, got {home_team_id}")
        if away_team_id == home_team_id:
            raise ValueError("Away and home teams must be different")
        
        self.away_team_id = away_team_id
        self.home_team_id = home_team_id
        self.week = week
        self.season_type = season_type
        self.overtime_type = overtime_type
        
        # Create descriptive event name
        away_name = self._get_team_abbreviation(away_team_id)
        home_name = self._get_team_abbreviation(home_team_id)
        event_name = f"{away_name} @ {home_name} (Week {week})"
        
        super().__init__(
            date=date,
            event_name=event_name,
            involved_teams=[away_team_id, home_team_id],
            duration_hours=3.5  # NFL games typically take 3-3.5 hours
        )
    
    def simulate(self) -> SimulationResult:
        """
        Execute NFL game simulation using existing FullGameSimulator
        
        Returns:
            SimulationResult: Game results in standard format
        """
        if FULL_GAME_SIMULATOR_AVAILABLE:
            try:
                # Create FullGameSimulator instance
                simulator = FullGameSimulator(
                    away_team_id=self.away_team_id,
                    home_team_id=self.home_team_id,
                    overtime_type=self.overtime_type
                )
                
                print(f"Simulating NFL game: {self.event_name} on {self.date.strftime('%Y-%m-%d')}")
                
                # Run the game simulation
                game_result = simulator.simulate_game()
                
                # Extract key results from game simulation
                final_score = simulator.get_final_score()
                performance_metrics = simulator.get_performance_metrics()
                
                # Convert to standard SimulationResult format
                return SimulationResult(
                    event_type=EventType.GAME,
                    event_name=self.event_name,
                    date=self.date,
                    teams_affected=self.involved_teams,
                    duration_hours=self.duration_hours,
                    success=True,
                    metadata={
                        "game_type": "nfl_game",
                        "away_team_id": self.away_team_id,
                        "home_team_id": self.home_team_id,
                        "week": self.week,
                        "season_type": self.season_type,
                        "final_score": final_score,
                        "winner": game_result.winner.full_name if game_result.winner else "Tie",
                        "total_plays": game_result.total_plays,
                        "total_drives": game_result.total_drives,
                        "game_duration_minutes": game_result.game_duration_minutes,
                        "simulation_performance": performance_metrics,
                        "game_result_object": game_result  # Store full result for detailed access
                    }
                )
                
            except Exception as e:
                # Handle any simulation errors gracefully
                error_msg = f"Game simulation failed: {str(e)}"
                print(f"ERROR: {error_msg}")
                
                return SimulationResult(
                    event_type=EventType.GAME,
                    event_name=self.event_name,
                    date=self.date,
                    teams_affected=self.involved_teams,
                    duration_hours=self.duration_hours,
                    success=False,
                    error_message=error_msg,
                    metadata={
                        "game_type": "nfl_game",
                        "away_team_id": self.away_team_id,
                        "home_team_id": self.home_team_id,
                        "week": self.week,
                        "season_type": self.season_type,
                        "simulation_failed": True
                    }
                )
        else:
            # Fallback placeholder when FullGameSimulator is not available
            print(f"simulate game (placeholder): {self.event_name} on {self.date.strftime('%Y-%m-%d')}")
            
            # Simulate a simple game result
            import random
            away_score = random.randint(7, 35)
            home_score = random.randint(7, 35)
            winner = "Away" if away_score > home_score else "Home" if home_score > away_score else "Tie"
            
            return SimulationResult(
                event_type=EventType.GAME,
                event_name=self.event_name,
                date=self.date,
                teams_affected=self.involved_teams,
                duration_hours=self.duration_hours,
                success=True,
                metadata={
                    "game_type": "placeholder_game",
                    "away_team_id": self.away_team_id,
                    "home_team_id": self.home_team_id,
                    "week": self.week,
                    "season_type": self.season_type,
                    "final_score": {
                        "away": away_score,
                        "home": home_score
                    },
                    "winner": winner,
                    "placeholder": True,
                    "message": f"Placeholder game simulation - {winner} wins {max(away_score, home_score)}-{min(away_score, home_score)}"
                }
            )
    
    def get_event_type(self) -> EventType:
        """Return event type for this game simulation"""
        return EventType.GAME
    
    def get_game_matchup(self) -> Dict[str, Any]:
        """
        Get detailed matchup information for this game
        
        Returns:
            Dictionary with matchup details
        """
        return {
            "away_team": {
                "id": self.away_team_id,
                "abbreviation": self._get_team_abbreviation(self.away_team_id)
            },
            "home_team": {
                "id": self.home_team_id,
                "abbreviation": self._get_team_abbreviation(self.home_team_id)
            },
            "week": self.week,
            "season_type": self.season_type,
            "date": self.date,
            "overtime_rules": self.overtime_type
        }
    
    def can_coexist_with(self, other: BaseSimulationEvent) -> bool:
        """
        Override coexistence logic for games.
        
        Games require exclusive team access and are major events that
        should not be scheduled with other team activities on the same day.
        """
        # Games cannot coexist with any other events for the same teams
        return not bool(set(self.involved_teams) & set(other.involved_teams))
    
    def validate_preconditions(self) -> tuple[bool, Optional[str]]:
        """
        Validate that this game can be executed
        
        Returns:
            tuple: (is_valid, error_message)
        """
        # Run base validation first
        is_valid, error_msg = super().validate_preconditions()
        if not is_valid:
            return is_valid, error_msg
        
        # Additional game-specific validation
        if self.week < 1 or self.week > 20:  # NFL weeks 1-18 regular + playoffs
            return False, f"Invalid week number: {self.week}"
        
        if self.season_type not in ["preseason", "regular_season", "playoffs"]:
            return False, f"Invalid season type: {self.season_type}"
        
        if self.overtime_type not in ["regular_season", "playoffs"]:
            return False, f"Invalid overtime type: {self.overtime_type}"
        
        return True, None
    
    def _get_team_abbreviation(self, team_id: int) -> str:
        """
        Get team abbreviation for display purposes
        
        Args:
            team_id: Team ID (1-32)
            
        Returns:
            Team abbreviation string
        """
        # This is a simplified mapping - in a full implementation you'd
        # load this from the team data system
        team_abbrevs = {
            1: "ARI", 2: "ATL", 3: "BAL", 4: "BUF", 5: "CAR", 6: "CHI", 7: "CIN", 8: "CLE",
            9: "DAL", 10: "DEN", 11: "DET", 12: "GB", 13: "HOU", 14: "IND", 15: "JAX", 16: "KC",
            17: "LV", 18: "LAC", 19: "LAR", 20: "MIA", 21: "MIN", 22: "NE", 23: "NO", 24: "NYG",
            25: "NYJ", 26: "PHI", 27: "PIT", 28: "SF", 29: "SEA", 30: "TB", 31: "TEN", 32: "WAS"
        }
        return team_abbrevs.get(team_id, f"T{team_id}")
    
    def __str__(self) -> str:
        """Enhanced string representation for games"""
        return f"NFL Game: {self.event_name} on {self.date.strftime('%Y-%m-%d')}"
    
    def __repr__(self) -> str:
        """Detailed representation for debugging"""
        return (f"GameSimulationEvent(away={self.away_team_id}, home={self.home_team_id}, "
                f"week={self.week}, date={self.date}, season_type={self.season_type})")