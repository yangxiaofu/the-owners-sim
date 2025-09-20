"""
Daily Simulation Controller

Provides day-by-day control over NFL season simulation.
Allows simulation of individual days, specific dates, or sequences of days.
"""

from datetime import date, timedelta
from typing import Dict, Any, List, Optional, Tuple
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
class DayInfo:
    """Information about a simulation day"""
    date: date
    day_name: str
    games_scheduled: int
    week_number: int
    is_game_day: bool


@dataclass
class MultiDayResults:
    """Results from simulating multiple days"""
    start_date: date
    end_date: date
    days_simulated: int
    total_games: int
    total_successful: int
    total_failed: int
    daily_results: List[DaySimulationResult]
    errors: List[str]


class DailySimulationController:
    """
    Provides day-by-day control over NFL season simulation.
    
    Allows users to simulate individual days, specific dates, or sequences
    of days with fine-grained control over the simulation pace.
    """
    
    def __init__(self, database_path: str = "data/database/nfl_simulation.db"):
        """
        Initialize the daily simulation controller.
        
        Args:
            database_path: Path to SQLite database file
        """
        self.database_path = database_path
        self.logger = logging.getLogger("DailySimulationController")
        
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
        self.current_date: Optional[date] = None
        self.season_initialized: bool = False
        self.season_start_date: Optional[date] = None
        self.season_end_date: Optional[date] = None
        
        self.logger.info("DailySimulationController initialized")
    
    def initialize_season(self, season_year: int, dynasty_name: str) -> Dict[str, Any]:
        """
        Initialize a new NFL season for day-by-day simulation.
        
        Args:
            season_year: Year the season starts (e.g., 2025)
            dynasty_name: Name for this dynasty/franchise
            
        Returns:
            Dictionary with initialization results and season info
        """
        self.logger.info(f"Initializing {season_year} season for daily simulation: {dynasty_name}")
        
        try:
            # Initialize core components
            self.season_controller = SeasonProgressionController(self.database_path)
            self.date_calculator = WeekToDateCalculator(season_year)
            self.team_manager = TeamDataManager()
            
            # Store season parameters
            self.season_year = season_year
            self.dynasty_name = dynasty_name
            
            # Calculate season date range
            season_summary = self.date_calculator.get_season_summary()
            self.season_start_date = season_summary['season_start']
            self.current_date = self.season_start_date
            
            # Initialize the season using the existing controller  
            init_result = self.season_controller._initialize_season(season_year, dynasty_name, self.season_start_date)
            
            if init_result.get('success', False):
                self.dynasty_id = init_result.get('dynasty', {}).get('dynasty_id', '')
                self.season_initialized = True
                
                self.logger.info(f"Daily simulation ready: Dynasty {self.dynasty_id[:8]}...")
                
                return {
                    'success': True,
                    'message': f'Season {season_year} initialized for daily simulation',
                    'dynasty': init_result.get('dynasty', {}),
                    'season_start_date': self.season_start_date.isoformat(),
                    'current_date': self.current_date.isoformat()
                }
            else:
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
    
    def simulate_day(self, target_date: Optional[date] = None) -> DaySimulationResult:
        """
        Simulate a specific day.
        
        Args:
            target_date: Date to simulate (defaults to current_date)
            
        Returns:
            DaySimulationResult with all events and outcomes for the day
        """
        if not self.season_initialized:
            raise RuntimeError("Season not initialized. Call initialize_season() first.")
        
        if target_date is None:
            target_date = self.current_date
        
        if target_date is None:
            raise RuntimeError("No target date specified and current_date not set.")
        
        self.logger.info(f"Simulating {target_date.strftime('%A, %B %d, %Y')}...")
        
        try:
            # Use the existing infrastructure to simulate the day
            day_result = self.season_controller._simulate_single_day(target_date)
            
            # Log results
            if day_result.events_executed > 0:
                self.logger.info(f"📅 {target_date}: {day_result.events_executed} events, "
                               f"{day_result.successful_events} successful, {day_result.failed_events} failed")
            else:
                self.logger.info(f"📅 {target_date}: No games scheduled")
            
            return day_result
            
        except Exception as e:
            error_msg = f"Failed to simulate {target_date}: {str(e)}"
            self.logger.error(error_msg)
            
            # Return a failed result
            return DaySimulationResult(
                date=target_date,
                events_scheduled=0,
                events_executed=0,
                successful_events=0,
                failed_events=1,
                errors=[error_msg]
            )
    
    def simulate_next_day(self) -> DaySimulationResult:
        """
        Simulate the next day in the season.
        
        Returns:
            DaySimulationResult for the next day
        """
        if not self.season_initialized or self.current_date is None:
            raise RuntimeError("Season not initialized or current date not set.")
        
        # Simulate current day
        result = self.simulate_day(self.current_date)
        
        # Advance to next day
        self.current_date += timedelta(days=1)
        
        return result
    
    def simulate_next_game_day(self) -> Tuple[DaySimulationResult, int]:
        """
        Find and simulate the next day that has games scheduled.
        
        Returns:
            Tuple of (DaySimulationResult, days_skipped)
        """
        if not self.season_initialized or self.current_date is None:
            raise RuntimeError("Season not initialized or current date not set.")
        
        days_skipped = 0
        max_search_days = 14  # Don't search more than 2 weeks ahead
        
        search_date = self.current_date
        
        # Find next day with games
        while days_skipped < max_search_days:
            day_info = self.get_day_info(search_date)
            
            if day_info.is_game_day:
                # Found a game day, simulate it
                result = self.simulate_day(search_date)
                self.current_date = search_date + timedelta(days=1)
                
                if days_skipped > 0:
                    self.logger.info(f"Skipped {days_skipped} non-game days")
                
                return result, days_skipped
            
            search_date += timedelta(days=1)
            days_skipped += 1
        
        # No game days found
        raise RuntimeError(f"No game days found in next {max_search_days} days")
    
    def simulate_next_7_days(self) -> MultiDayResults:
        """
        Simulate the next 7 days (full week).
        
        Returns:
            MultiDayResults with all daily results
        """
        if not self.season_initialized or self.current_date is None:
            raise RuntimeError("Season not initialized or current date not set.")
        
        start_date = self.current_date
        end_date = start_date + timedelta(days=6)  # 7 days total
        
        self.logger.info(f"Simulating 7 days: {start_date} to {end_date}")
        
        daily_results = []
        errors = []
        total_games = 0
        total_successful = 0
        total_failed = 0
        
        current_sim_date = start_date
        
        for day_num in range(7):
            try:
                day_result = self.simulate_day(current_sim_date)
                daily_results.append(day_result)
                
                total_games += day_result.events_executed
                total_successful += day_result.successful_events
                total_failed += day_result.failed_events
                errors.extend(day_result.errors)
                
            except Exception as e:
                error_msg = f"Failed to simulate {current_sim_date}: {str(e)}"
                errors.append(error_msg)
                self.logger.error(error_msg)
            
            current_sim_date += timedelta(days=1)
        
        # Update current date
        self.current_date = end_date + timedelta(days=1)
        
        return MultiDayResults(
            start_date=start_date,
            end_date=end_date,
            days_simulated=7,
            total_games=total_games,
            total_successful=total_successful,
            total_failed=total_failed,
            daily_results=daily_results,
            errors=errors
        )
    
    def get_day_info(self, target_date: date) -> DayInfo:
        """
        Get information about a specific day.
        
        Args:
            target_date: Date to get information about
            
        Returns:
            DayInfo with details about the day
        """
        if not self.season_initialized:
            raise RuntimeError("Season not initialized.")
        
        # Calculate week number based on season start date
        if self.season_start_date:
            days_elapsed = (target_date - self.season_start_date).days
            # Each NFL week is roughly 7 days, starting from week 1
            week_number = max(1, (days_elapsed // 7) + 1)
        else:
            week_number = 1  # Default to week 1
        
        # Get games scheduled for this date using enhanced calendar integration
        games_count = 0
        if self.season_controller and self.season_controller.calendar_manager:
            events = self.season_controller.calendar_manager.get_events_for_date(target_date)
            # Count game events specifically
            games_count = len([e for e in events if hasattr(e, 'event_type') and e.event_type.name == "GAME"])
        
        return DayInfo(
            date=target_date,
            day_name=target_date.strftime('%A'),
            games_scheduled=games_count,
            week_number=week_number,
            is_game_day=games_count > 0
        )
    
    def get_current_standings(self) -> Optional[Dict[str, Any]]:
        """
        Get current standings using the database API.
        
        Returns:
            Standings data or None if not available
        """
        if not self.dynasty_id or not self.season_year:
            return None
        
        try:
            return self.database_api.get_standings(self.dynasty_id, self.season_year)
        except Exception as e:
            self.logger.error(f"Failed to get standings: {e}")
            return None
    
    def get_upcoming_games(self, days_ahead: int = 7) -> List[DayInfo]:
        """
        Get information about upcoming game days.
        
        Args:
            days_ahead: Number of days to look ahead
            
        Returns:
            List of DayInfo for days with games
        """
        if not self.season_initialized or self.current_date is None:
            return []
        
        upcoming_game_days = []
        search_date = self.current_date
        
        for _ in range(days_ahead):
            day_info = self.get_day_info(search_date)
            if day_info.is_game_day:
                upcoming_game_days.append(day_info)
            search_date += timedelta(days=1)
        
        return upcoming_game_days
    
    def reset_to_date(self, target_date: date) -> None:
        """
        Reset the current date to a specific date.
        
        Args:
            target_date: Date to reset to
        """
        if not self.season_initialized:
            raise RuntimeError("Season not initialized.")
        
        self.current_date = target_date
        self.logger.info(f"Current date reset to {target_date}")
    
    def get_team_availability(self, team_id: int, target_date: date) -> bool:
        """
        Check if a team is available on a specific date.
        
        Args:
            team_id: Team to check availability for
            target_date: Date to check
            
        Returns:
            True if team is available, False if already scheduled
        """
        if not self.season_initialized or not self.season_controller.calendar_manager:
            return True  # Default to available if calendar not initialized
        
        return self.season_controller.calendar_manager.is_team_available(team_id, target_date)
    
    def find_next_game_dates(self, days_ahead: int = 14) -> List[date]:
        """
        Find all upcoming dates that have games scheduled.
        
        Args:
            days_ahead: Number of days to look ahead
            
        Returns:
            List of dates with games scheduled
        """
        if not self.season_initialized or self.current_date is None:
            return []
        
        game_dates = []
        search_date = self.current_date
        
        for _ in range(days_ahead):
            day_info = self.get_day_info(search_date)
            if day_info.is_game_day:
                game_dates.append(search_date)
            search_date += timedelta(days=1)
        
        return game_dates
    
    def get_calendar_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the calendar state and upcoming events.
        
        Returns:
            Dictionary with calendar statistics and summary
        """
        if not self.season_initialized or not self.season_controller.calendar_manager:
            return {'error': 'Calendar not initialized'}
        
        try:
            # Get calendar stats from the calendar manager
            calendar_stats = self.season_controller.calendar_manager.get_calendar_stats()
            
            # Get upcoming game dates
            upcoming_games = self.find_next_game_dates(14)
            
            # Get simulation history for recent days
            if self.current_date:
                recent_start = self.current_date - timedelta(days=7)
                simulation_history = self.season_controller.calendar_manager.get_simulation_history(
                    recent_start, self.current_date
                )
            else:
                simulation_history = {}
            
            return {
                'current_date': self.current_date.isoformat() if self.current_date else None,
                'total_events': calendar_stats.total_events,
                'events_by_type': {str(k): v for k, v in calendar_stats.events_by_type.items()},
                'teams_with_events': len(calendar_stats.teams_with_events),
                'date_range': [d.isoformat() for d in calendar_stats.date_range] if calendar_stats.date_range else None,
                'upcoming_game_dates': [d.isoformat() for d in upcoming_games],
                'recent_simulation_days': len(simulation_history),
                'result_processing_enabled': calendar_stats.result_processing_enabled,
                'total_scheduled_hours': calendar_stats.total_scheduled_hours
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get calendar summary: {e}")
            return {'error': f'Failed to get calendar summary: {str(e)}'}
    
    def get_week_game_dates(self, week_number: int) -> List[date]:
        """
        Get all dates with games scheduled for a specific week.
        
        Args:
            week_number: NFL week number (1-18)
            
        Returns:
            List of dates with games in that week
        """
        if not self.season_initialized:
            return []
        
        try:
            # Get the date range for this week
            week_dates = self.date_calculator.get_game_dates_for_week(week_number)
            
            # Check each day in the week for games
            game_dates = []
            start_date = week_dates['thursday']
            end_date = week_dates['monday']
            
            current_date = start_date
            while current_date <= end_date:
                day_info = self.get_day_info(current_date)
                if day_info.is_game_day:
                    game_dates.append(current_date)
                current_date += timedelta(days=1)
            
            return game_dates
            
        except Exception as e:
            self.logger.error(f"Failed to get week {week_number} game dates: {e}")
            return []
    
    def get_season_status(self) -> Dict[str, Any]:
        """
        Get current season status and progress for daily simulation.
        
        Returns:
            Dictionary with season progress information
        """
        if not self.season_initialized:
            return {
                'season_initialized': False,
                'season_year': None,
                'dynasty_name': None,
                'current_week': 0,  # Added for compatibility
                'weeks_remaining': 18,  # Added for compatibility
                'current_date': None,
                'season_complete': False,
                'progress_percentage': 0.0,
                'season_start_date': None,
                'season_end_date': None
            }
        
        # Calculate progress based on current date vs season timeline
        progress_percentage = 0.0
        season_complete = False
        current_week = 0
        weeks_remaining = 18
        
        if self.current_date and self.season_start_date:
            # Calculate days elapsed and convert to week equivalent
            days_elapsed = (self.current_date - self.season_start_date).days
            # Each NFL week is roughly 7 days, so calculate current week
            current_week = max(0, min(18, days_elapsed // 7))
            weeks_remaining = max(0, 18 - current_week)
            
            # NFL season is roughly 126 days (18 weeks)
            total_season_days = 126
            progress_percentage = min(100.0, (days_elapsed / total_season_days) * 100.0)
            season_complete = days_elapsed >= total_season_days or current_week >= 18
        
        return {
            'season_initialized': self.season_initialized,
            'season_year': self.season_year,
            'dynasty_name': self.dynasty_name,
            'current_week': current_week,  # Added for compatibility
            'weeks_remaining': weeks_remaining,  # Added for compatibility
            'current_date': self.current_date.isoformat() if self.current_date else None,
            'season_complete': season_complete,
            'progress_percentage': progress_percentage,
            'season_start_date': self.season_start_date.isoformat() if self.season_start_date else None,
            'season_end_date': None,  # We don't track end date in daily controller
            'current_day': self.current_date.strftime('%A, %B %d, %Y') if self.current_date else None,
            'days_elapsed': (self.current_date - self.season_start_date).days if self.current_date and self.season_start_date else 0
        }