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
    from game_management.full_game_simulator import FullGameSimulator
    FULL_GAME_SIMULATOR_AVAILABLE = True
except ImportError:
    try:
        # Fallback import path
        from src.game_management.full_game_simulator import FullGameSimulator
        FULL_GAME_SIMULATOR_AVAILABLE = True
    except ImportError:
        print("⚠️  FullGameSimulator not available - GameSimulationEvent will use placeholder")
        FULL_GAME_SIMULATOR_AVAILABLE = False

try:
    from stores.store_manager import StoreManager
    STORE_MANAGER_AVAILABLE = True
except ImportError:
    STORE_MANAGER_AVAILABLE = False

try:
    from constants.team_ids import TeamIDs
except ImportError:
    try:
        from src.constants.team_ids import TeamIDs
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
                 overtime_type: str = "regular_season", team_registry=None, store_manager=None):
        """
        Initialize NFL game simulation event
        
        Args:
            date: When this game is scheduled
            away_team_id: Away team ID (1-32)
            home_team_id: Home team ID (1-32) 
            week: Week number in season
            season_type: Type of season (preseason, regular_season, playoffs)
            overtime_type: Overtime rules (regular_season or playoffs)
            team_registry: Optional Dynasty Team Registry for consistent team data
            store_manager: Optional StoreManager for immediate result persistence
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
        self.team_registry = team_registry  # Store injected registry for consistent team data
        self.store_manager = store_manager  # Store manager for immediate persistence
        
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
                game_result = simulator.simulate_game(date=self.date)
                
                # Process game results through store manager for immediate persistence
                game_id = None
                player_stats_for_result = []

                if self.store_manager and STORE_MANAGER_AVAILABLE:
                    try:
                        game_id = f"{self.season_type}_{self.week}_{self.away_team_id}_{self.home_team_id}_{self.date.strftime('%Y%m%d')}"
                        transaction_result = self.store_manager.process_game_complete(game_id, game_result)
                        if transaction_result.success:
                            print(f"✅ Game results persisted: {game_id}")

                            # Extract player stats from store after successful persistence
                            try:
                                # Get the player stats that were just stored
                                player_stats_store = self.store_manager.player_stats_store
                                if hasattr(player_stats_store, 'data') and game_id in player_stats_store.data:
                                    stored_stats = player_stats_store.data[game_id]
                                    if stored_stats:
                                        player_stats_for_result = stored_stats
                                        print(f"✅ Extracted {len(player_stats_for_result)} player stats from store")
                                    else:
                                        print(f"⚠️  No player stats found in store for game {game_id}")
                                else:
                                    print(f"⚠️  Game {game_id} not found in player stats store")
                            except Exception as e:
                                print(f"⚠️  Error extracting player stats from store: {e}")
                        else:
                            print(f"⚠️  Game results persistence failed: {transaction_result.errors}")
                    except Exception as e:
                        print(f"❌ Error persisting game results: {e}")

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
                        "game_result_object": game_result,  # Store full result for detailed access
                        "player_stats": player_stats_for_result  # Store player stats for persistence
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
        Get team abbreviation for display purposes using Dynasty Team Registry
        
        Args:
            team_id: Team ID
            
        Returns:
            Team abbreviation string
        """
        # PRIORITY 1: Use injected registry (fixes import path issues)
        if (self.team_registry and 
            hasattr(self.team_registry, 'is_initialized') and 
            self.team_registry.is_initialized() and
            hasattr(self.team_registry, 'get_team_abbreviation')):
            try:
                return self.team_registry.get_team_abbreviation(team_id)
            except Exception as e:
                # Log but continue to fallback
                print(f"⚠️  Injected registry failed for team {team_id}: {e}")
        
        # PRIORITY 2: Try to import registry (original approach, may fail due to import path issues)
        try:
            # Import registry here to avoid circular imports
            from team_registry import get_registry
            
            # Use registry if available and initialized
            registry = get_registry()
            if registry and hasattr(registry, 'is_initialized') and registry.is_initialized():
                return registry.get_team_abbreviation(team_id)
        
        except ImportError:
            # Registry not available due to import path issues - this was the root cause
            pass
        except Exception:
            # Registry not initialized or other error, fall back
            pass
        
        # Fallback: Basic team abbreviation mapping
        # This is kept for backwards compatibility but should not be used
        # when registry is properly initialized
        team_abbrevs = {
            1: "BUF", 2: "MIA", 3: "NE", 4: "NYJ", 5: "BAL", 6: "CIN", 7: "CLE", 8: "PIT",
            9: "HOU", 10: "IND", 11: "JAX", 12: "TEN", 13: "DEN", 14: "KC", 15: "LV", 16: "LAC",
            17: "DAL", 18: "NYG", 19: "PHI", 20: "WAS", 21: "CHI", 22: "DET", 23: "GB", 24: "MIN",
            25: "ATL", 26: "CAR", 27: "NO", 28: "TB", 29: "ARI", 30: "LAR", 31: "SF", 32: "SEA"
        }
        return team_abbrevs.get(team_id, f"T{team_id}")
    
    def __str__(self) -> str:
        """Enhanced string representation for games"""
        return f"NFL Game: {self.event_name} on {self.date.strftime('%Y-%m-%d')}"
    
    def __repr__(self) -> str:
        """Detailed representation for debugging"""
        return (f"GameSimulationEvent(away={self.away_team_id}, home={self.home_team_id}, "
                f"week={self.week}, date={self.date}, season_type={self.season_type})")