"""
Weekly Simulation Controller

A wrapper around SeasonProgressionController that provides week-by-week
control over season simulation instead of full automation.
"""

from datetime import date, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import logging

from simulation.season_progression_controller import (
    SeasonProgressionController, 
    SeasonProgressStats
)
from simulation.calendar_manager import DaySimulationResult
from scheduling.utils.date_calculator import WeekToDateCalculator
from scheduling.data.team_data import TeamDataManager
from stores.game_result_store import GameResultStore
from stores.standings_store import StandingsStore
from database.api import DatabaseAPI


@dataclass
class WeekResults:
    """Results from simulating a single NFL week"""
    week_number: int
    games_played: int
    successful_games: int
    failed_games: int
    game_results: List[Dict[str, Any]]
    week_dates: Dict[str, date]
    errors: List[str]


class WeeklySimulationController:
    """
    Provides week-by-week control over NFL season simulation.
    
    Wraps SeasonProgressionController to allow users to advance
    the season one week at a time instead of simulating the entire
    season automatically.
    """
    
    def __init__(self, database_path: str = "data/database/nfl_simulation.db"):
        """
        Initialize the weekly simulation controller.
        
        Args:
            database_path: Path to SQLite database file
        """
        self.database_path = database_path
        self.logger = logging.getLogger("WeeklySimulationController")
        
        # Core components
        self.season_controller: Optional[SeasonProgressionController] = None
        self.date_calculator: Optional[WeekToDateCalculator] = None
        self.team_manager: Optional[TeamDataManager] = None
        self.game_results_store: Optional[GameResultStore] = None
        self.standings_store: Optional[StandingsStore] = None
        self.database_api = DatabaseAPI(database_path)
        
        # Season state
        self.season_year: Optional[int] = None
        self.dynasty_name: Optional[str] = None
        self.dynasty_id: Optional[str] = None
        self.current_week: int = 0
        self.max_weeks: int = 18  # NFL regular season
        self.season_initialized: bool = False
        self.season_start_date: Optional[date] = None
        self.season_end_date: Optional[date] = None
        
        self.logger.info("WeeklySimulationController initialized")
    
    def initialize_season(self, season_year: int, dynasty_name: str) -> Dict[str, Any]:
        """
        Initialize a new NFL season for week-by-week simulation.
        
        Args:
            season_year: Year the season starts (e.g., 2025)
            dynasty_name: Name for this dynasty/franchise
            
        Returns:
            Dictionary with initialization results and season info
        """
        self.logger.info(f"Initializing {season_year} season: {dynasty_name}")
        
        try:
            # Initialize core components
            self.season_controller = SeasonProgressionController(self.database_path)
            self.date_calculator = WeekToDateCalculator(season_year)
            self.team_manager = TeamDataManager()
            
            # Store season parameters
            self.season_year = season_year
            self.dynasty_name = dynasty_name
            self.current_week = 0
            
            # Calculate season dates
            season_dates = self.date_calculator.get_season_summary()
            self.season_start_date = season_dates['season_start']
            self.season_end_date = season_dates['regular_season_end']
            
            # Initialize the season through SeasonProgressionController
            # We'll initialize but not run the full simulation
            result = self.season_controller._initialize_season(
                season_year, dynasty_name, self.season_start_date
            )
            
            if result['success']:
                # Get store references
                store_manager = self.season_controller.season_initializer.store_manager
                self.game_results_store = store_manager.get_store('game_results')
                self.standings_store = store_manager.get_store('standings')
                
                # Capture dynasty_id and set up store contexts
                self.dynasty_id = result.get('dynasty', {}).get('dynasty_id', '')
                if self.game_results_store:
                    self.game_results_store.set_dynasty_context(self.dynasty_id, season_year)
                if self.standings_store:
                    self.standings_store.set_dynasty_context(self.dynasty_id, season_year)
                
                self.season_initialized = True
                self.logger.info("✅ Season initialization successful")
                
                return {
                    'success': True,
                    'season_year': season_year,
                    'dynasty_name': dynasty_name,
                    'dynasty_id': self.dynasty_id,
                    'total_games': result.get('schedule', {}).get('total_games', 0),
                    'season_start': self.season_start_date,
                    'season_end': self.season_end_date,
                    'total_weeks': self.max_weeks
                }
            else:
                self.logger.error("❌ Season initialization failed")
                return {
                    'success': False,
                    'error': 'Failed to initialize season'
                }
                
        except Exception as e:
            error_msg = f"Season initialization error: {str(e)}"
            self.logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
    
    def simulate_next_week(self) -> WeekResults:
        """
        Simulate the next week of the NFL season.
        
        Returns:
            WeekResults with all games and outcomes for the week
        """
        if not self.season_initialized:
            raise RuntimeError("Season not initialized. Call initialize_season() first.")
        
        if self.current_week >= self.max_weeks:
            raise RuntimeError("Season complete. No more weeks to simulate.")
        
        next_week = self.current_week + 1
        self.logger.info(f"Simulating Week {next_week}...")
        
        try:
            # Get the dates for this week
            week_dates = self.date_calculator.get_game_dates_for_week(next_week)
            
            # Simulate all days in this week
            errors = []
            successful_games = 0
            failed_games = 0
            
            current_date = week_dates['thursday']
            end_date = week_dates['monday']
            
            while current_date <= end_date:
                try:
                    day_result = self.season_controller._simulate_single_day(current_date)
                    successful_games += day_result.successful_events
                    failed_games += day_result.failed_events
                    errors.extend(day_result.errors)
                except Exception as e:
                    error_msg = f"Failed to simulate {current_date}: {str(e)}"
                    errors.append(error_msg)
                    failed_games += 1
                
                current_date += timedelta(days=1)
            
            # Get all games from this week
            week_game_results = self._get_week_game_results(next_week)
            
            # Update current week
            self.current_week = next_week
            
            self.logger.info(f"✅ Week {next_week} simulation complete: {successful_games} games")
            
            return WeekResults(
                week_number=next_week,
                games_played=successful_games + failed_games,
                successful_games=successful_games,
                failed_games=failed_games,
                game_results=week_game_results,
                week_dates=week_dates,
                errors=errors
            )
            
        except Exception as e:
            error_msg = f"Week {next_week} simulation failed: {str(e)}"
            self.logger.error(error_msg)
            
            return WeekResults(
                week_number=next_week,
                games_played=0,
                successful_games=0,
                failed_games=1,
                game_results=[],
                week_dates=week_dates if 'week_dates' in locals() else {},
                errors=[error_msg]
            )
    
    def get_current_standings(self) -> Optional[Dict[str, Any]]:
        """
        Get current season standings from database.
        
        Returns:
            Current standings data or None if not available
        """
        if not self.dynasty_id or not self.season_year:
            self.logger.warning("Cannot get standings - dynasty or season not set")
            return None
        
        try:
            return self.database_api.get_standings(self.dynasty_id, self.season_year)
        except Exception as e:
            self.logger.error(f"Failed to get standings from database: {e}")
            return None
    
    def get_season_status(self) -> Dict[str, Any]:
        """
        Get current season status and progress.
        
        Returns:
            Dictionary with season progress information
        """
        return {
            'season_initialized': self.season_initialized,
            'season_year': self.season_year,
            'dynasty_name': self.dynasty_name,
            'current_week': self.current_week,
            'weeks_remaining': max(0, self.max_weeks - self.current_week),
            'season_complete': self.current_week >= self.max_weeks,
            'progress_percentage': (self.current_week / self.max_weeks) * 100.0,
            'season_start_date': self.season_start_date,
            'season_end_date': self.season_end_date
        }
    
    def get_team_name(self, team_id: int) -> str:
        """
        Get full team name for display.
        
        Args:
            team_id: Numerical team ID
            
        Returns:
            Full team name (e.g., "Detroit Lions")
        """
        if not self.team_manager:
            return f"Team {team_id}"
        
        team = self.team_manager.get_team(team_id)
        return team.full_name if team else f"Team {team_id}"
    
    def _get_week_game_results(self, week: int) -> List[Dict[str, Any]]:
        """
        Get all game results for a specific week from database.
        
        Args:
            week: Week number
            
        Returns:
            List of formatted game results
        """
        if not self.dynasty_id or not self.season_year:
            self.logger.warning("Cannot get game results - dynasty or season not set")
            return []
        
        try:
            games = self.database_api.get_game_results(self.dynasty_id, week, self.season_year)
            formatted_results = []
            
            for game in games:
                result = {
                    'home_team_id': game['home_team_id'],
                    'away_team_id': game['away_team_id'],
                    'home_team_name': self.get_team_name(game['home_team_id']),
                    'away_team_name': self.get_team_name(game['away_team_id']),
                    'home_score': game['home_score'],
                    'away_score': game['away_score'],
                    'winner_id': game['home_team_id'] if game['home_score'] > game['away_score'] else game['away_team_id'],
                    'winner_name': (self.get_team_name(game['home_team_id']) if game['home_score'] > game['away_score'] 
                                  else self.get_team_name(game['away_team_id'])),
                    'is_tie': game['home_score'] == game['away_score'],
                    'date': game['date'],
                    'week': game['week']
                }
                formatted_results.append(result)
            
            return formatted_results
            
        except Exception as e:
            self.logger.error(f"Failed to get week {week} results from database: {e}")
            return []