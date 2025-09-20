"""
Season Progression Controller

Orchestrates complete NFL season simulation with day-by-day advancement.
This is the high-level controller that ties together all components for 
end-to-end season simulation from September through February.
"""

from datetime import date, datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
import logging
import time

from simulation.season_initializer import SeasonInitializer
from simulation.calendar_manager import CalendarManager, DaySimulationResult


@dataclass
class SeasonProgressStats:
    """Statistics for season progression tracking"""
    season_start_date: date
    current_date: date
    season_end_date: date
    total_days: int
    days_completed: int
    games_scheduled: int
    games_completed: int
    games_successful: int
    games_failed: int
    total_events_processed: int
    simulation_start_time: datetime
    elapsed_time_seconds: float = 0.0
    estimated_completion_time: Optional[datetime] = None
    
    @property
    def days_remaining(self) -> int:
        return max(0, self.total_days - self.days_completed)
    
    @property
    def progress_percentage(self) -> float:
        if self.total_days == 0:
            return 0.0
        return (self.days_completed / self.total_days) * 100.0
    
    @property
    def game_success_rate(self) -> float:
        total_games = self.games_successful + self.games_failed
        if total_games == 0:
            return 0.0
        return (self.games_successful / total_games) * 100.0


@dataclass 
class SeasonProgressionResult:
    """Result of complete season simulation"""
    success: bool
    season_stats: SeasonProgressStats
    daily_results: List[DaySimulationResult] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    dynasty_id: str = ""
    season_year: int = 0
    final_standings: Optional[Dict[str, Any]] = None


class SeasonProgressionController:
    """
    High-level orchestrator for complete NFL season simulation.
    
    This controller manages the day-by-day progression through an entire
    NFL season, coordinating all simulation components and providing
    comprehensive progress tracking and error recovery.
    """
    
    def __init__(self, database_path: str = "data/database/nfl_simulation.db"):
        """
        Initialize the season progression controller.
        
        Args:
            database_path: Path to SQLite database file
        """
        self.database_path = database_path
        self.logger = logging.getLogger("SeasonProgressionController")
        
        # Core components
        self.season_initializer: Optional[SeasonInitializer] = None
        self.calendar_manager: Optional[CalendarManager] = None
        
        # Progress tracking
        self.current_stats: Optional[SeasonProgressStats] = None
        self.daily_results: List[DaySimulationResult] = []
        self.simulation_paused = False
        self.pause_requested = False
        
        # Error recovery
        self.max_consecutive_failures = 5
        self.consecutive_failures = 0
        
        self.logger.info("SeasonProgressionController initialized")
    
    def simulate_complete_season(
        self,
        season_year: int,
        dynasty_name: str,
        start_date: Optional[date] = None,
        progress_callback: Optional[callable] = None
    ) -> SeasonProgressionResult:
        """
        Simulate a complete NFL season from start to finish.
        
        Args:
            season_year: Year the season starts (e.g., 2025)
            dynasty_name: Name for this dynasty/franchise
            start_date: Optional custom start date (defaults to NFL season start)
            progress_callback: Optional callback for progress updates
            
        Returns:
            SeasonProgressionResult with complete simulation results
        """
        self.logger.info(f"🏈 Starting complete {season_year} NFL season simulation")
        simulation_start = datetime.now()
        errors = []
        
        try:
            # Step 1: Initialize Season
            self.logger.info("Step 1: Initializing season...")
            result = self._initialize_season(season_year, dynasty_name, start_date)
            if not result['success']:
                return SeasonProgressionResult(
                    success=False,
                    season_stats=self._create_empty_stats(season_year, simulation_start),
                    errors=["Failed to initialize season"]
                )
            
            # Step 2: Calculate season timeline
            self.logger.info("Step 2: Calculating season timeline...")
            season_dates = self._calculate_season_dates(season_year, start_date)
            
            # Step 3: Initialize progress tracking
            self.current_stats = SeasonProgressStats(
                season_start_date=season_dates['start'],
                current_date=season_dates['start'],
                season_end_date=season_dates['end'],
                total_days=(season_dates['end'] - season_dates['start']).days + 1,
                days_completed=0,
                games_scheduled=result['schedule']['total_games'],
                games_completed=0,
                games_successful=0,
                games_failed=0,
                total_events_processed=0,
                simulation_start_time=simulation_start
            )
            
            self.logger.info(f"Season timeline: {season_dates['start']} to {season_dates['end']}")
            self.logger.info(f"Total days to simulate: {self.current_stats.total_days}")
            self.logger.info(f"Games scheduled: {self.current_stats.games_scheduled}")
            
            # Step 4: Day-by-day simulation
            self.logger.info("Step 4: Beginning day-by-day simulation...")
            self._simulate_season_progression(progress_callback)
            
            # Step 5: Generate final results
            self.logger.info("Step 5: Generating final results...")
            final_standings = self._get_final_standings()
            
            # Calculate final statistics
            self.current_stats.elapsed_time_seconds = (datetime.now() - simulation_start).total_seconds()
            
            self.logger.info("🏆 Season simulation completed successfully!")
            self._log_final_statistics()
            
            return SeasonProgressionResult(
                success=True,
                season_stats=self.current_stats,
                daily_results=self.daily_results,
                dynasty_id=self.season_initializer.get_dynasty_id(),
                season_year=season_year,
                final_standings=final_standings
            )
            
        except Exception as e:
            error_msg = f"Season simulation failed: {str(e)}"
            self.logger.error(error_msg)
            errors.append(error_msg)
            
            return SeasonProgressionResult(
                success=False,
                season_stats=self.current_stats or self._create_empty_stats(season_year, simulation_start),
                daily_results=self.daily_results,
                errors=errors
            )
    
    def _initialize_season(self, season_year: int, dynasty_name: str, start_date: Optional[date]) -> Dict[str, Any]:
        """Initialize the season using SeasonInitializer"""
        self.season_initializer = SeasonInitializer(self.database_path)
        
        result = self.season_initializer.initialize_season(
            season_year=season_year,
            dynasty_name=dynasty_name,
            start_date=start_date
        )
        
        if result['success']:
            self.calendar_manager = self.season_initializer.get_calendar_manager()
            self.logger.info(f"✅ Season initialized: {result['dynasty']['dynasty_id'][:8]}...")
            self.logger.info(f"✅ Games scheduled: {result['schedule']['total_games']}")
        
        return result
    
    def _calculate_season_dates(self, season_year: int, start_date: Optional[date]) -> Dict[str, date]:
        """Calculate season start and end dates"""
        if start_date:
            season_start = start_date
        else:
            # NFL season typically starts first Thursday of September
            season_start = date(season_year, 9, 1)
            # Find first Thursday
            while season_start.weekday() != 3:  # Thursday is weekday 3
                season_start += timedelta(days=1)
        
        # Season ends in early February (Super Bowl + 1 week)
        season_end = date(season_year + 1, 2, 15)
        
        return {
            'start': season_start,
            'end': season_end
        }
    
    def _simulate_season_progression(self, progress_callback: Optional[callable] = None):
        """Simulate day-by-day progression through the season"""
        current_date = self.current_stats.season_start_date
        
        while current_date <= self.current_stats.season_end_date:
            # Check for pause request
            if self.pause_requested:
                self.simulation_paused = True
                self.logger.info("⏸️ Season simulation paused")
                break
            
            # Simulate this day
            try:
                day_result = self._simulate_single_day(current_date)
                self.daily_results.append(day_result)
                
                # Update progress statistics
                self._update_progress_stats(day_result)
                
                # Call progress callback if provided
                if progress_callback:
                    progress_callback(self.current_stats, day_result)
                
                # Log progress periodically
                if self.current_stats.days_completed % 7 == 0:  # Weekly updates
                    self._log_progress()
                
                # Reset failure counter on success
                self.consecutive_failures = 0
                
            except Exception as e:
                self.consecutive_failures += 1
                error_msg = f"Failed to simulate {current_date}: {str(e)}"
                self.logger.error(error_msg)
                
                # Check if we've hit max failures
                if self.consecutive_failures >= self.max_consecutive_failures:
                    raise RuntimeError(f"Too many consecutive failures ({self.max_consecutive_failures})")
                
                # Create a failure result for this day
                failure_result = DaySimulationResult(
                    date=current_date,
                    events_scheduled=0,
                    events_executed=0,
                    successful_events=0,
                    failed_events=1,
                    errors=[error_msg]
                )
                self.daily_results.append(failure_result)
                self._update_progress_stats(failure_result)
            
            # Advance to next day
            current_date += timedelta(days=1)
            self.current_stats.current_date = current_date
    
    def _simulate_single_day(self, target_date: date) -> DaySimulationResult:
        """Simulate a single day using the calendar manager"""
        if not self.calendar_manager:
            raise RuntimeError("Calendar manager not initialized")
        
        # Use the calendar manager to simulate the day
        result = self.calendar_manager.simulate_day(target_date)
        
        # Log significant days (game days)
        if result.events_executed > 0:
            self.logger.info(f"📅 {target_date}: {result.events_executed} events, {result.successful_events} successful")
            if result.failed_events > 0:
                self.logger.warning(f"   ⚠️ {result.failed_events} failed events")
        
        return result
    
    def _update_progress_stats(self, day_result: DaySimulationResult):
        """Update progress statistics with day result"""
        self.current_stats.days_completed += 1
        self.current_stats.games_completed += day_result.events_executed  # Assuming events are games
        self.current_stats.games_successful += day_result.successful_events
        self.current_stats.games_failed += day_result.failed_events
        self.current_stats.total_events_processed += day_result.events_executed
        
        # Update elapsed time
        self.current_stats.elapsed_time_seconds = (
            datetime.now() - self.current_stats.simulation_start_time
        ).total_seconds()
        
        # Estimate completion time based on current progress
        if self.current_stats.days_completed > 0:
            avg_seconds_per_day = self.current_stats.elapsed_time_seconds / self.current_stats.days_completed
            remaining_seconds = avg_seconds_per_day * self.current_stats.days_remaining
            self.current_stats.estimated_completion_time = (
                datetime.now() + timedelta(seconds=remaining_seconds)
            )
    
    def _get_final_standings(self) -> Optional[Dict[str, Any]]:
        """Get final standings from the store manager"""
        if not self.season_initializer or not self.season_initializer.store_manager:
            return None
        
        try:
            standings_store = self.season_initializer.store_manager.get_store('standings')
            if standings_store:
                return standings_store.get_standings()
        except Exception as e:
            self.logger.error(f"Failed to get final standings: {e}")
        
        return None
    
    def _log_progress(self):
        """Log current progress"""
        stats = self.current_stats
        self.logger.info(f"📊 Progress: {stats.progress_percentage:.1f}% "
                        f"({stats.days_completed}/{stats.total_days} days)")
        self.logger.info(f"🎮 Games: {stats.games_completed} completed "
                        f"({stats.game_success_rate:.1f}% success rate)")
        
        if stats.estimated_completion_time:
            eta = stats.estimated_completion_time.strftime("%H:%M:%S")
            self.logger.info(f"⏰ ETA: {eta}")
    
    def _log_final_statistics(self):
        """Log final simulation statistics"""
        stats = self.current_stats
        duration_minutes = stats.elapsed_time_seconds / 60.0
        
        self.logger.info("=" * 60)
        self.logger.info("🏆 SEASON SIMULATION COMPLETE")
        self.logger.info("=" * 60)
        self.logger.info(f"Season: {stats.season_start_date} to {stats.current_date}")
        self.logger.info(f"Duration: {duration_minutes:.1f} minutes")
        self.logger.info(f"Days simulated: {stats.days_completed}")
        self.logger.info(f"Games completed: {stats.games_completed}")
        self.logger.info(f"Success rate: {stats.game_success_rate:.1f}%")
        self.logger.info(f"Events processed: {stats.total_events_processed}")
        self.logger.info("=" * 60)
    
    def _create_empty_stats(self, season_year: int, start_time: datetime) -> SeasonProgressStats:
        """Create empty stats for failed initialization"""
        return SeasonProgressStats(
            season_start_date=date(season_year, 9, 1),
            current_date=date(season_year, 9, 1),
            season_end_date=date(season_year + 1, 2, 15),
            total_days=0,
            days_completed=0,
            games_scheduled=0,
            games_completed=0,
            games_successful=0,
            games_failed=0,
            total_events_processed=0,
            simulation_start_time=start_time
        )
    
    def pause_simulation(self):
        """Request simulation pause at next safe point"""
        self.pause_requested = True
        self.logger.info("⏸️ Pause requested - will pause at next day boundary")
    
    def resume_simulation(self):
        """Resume paused simulation"""
        if self.simulation_paused:
            self.simulation_paused = False
            self.pause_requested = False
            self.logger.info("▶️ Simulation resumed")
    
    def get_current_status(self) -> Dict[str, Any]:
        """Get current simulation status"""
        if not self.current_stats:
            return {"status": "not_initialized"}
        
        return {
            "status": "paused" if self.simulation_paused else "running",
            "progress_percentage": self.current_stats.progress_percentage,
            "days_completed": self.current_stats.days_completed,
            "games_completed": self.current_stats.games_completed,
            "success_rate": self.current_stats.game_success_rate,
            "elapsed_time_minutes": self.current_stats.elapsed_time_seconds / 60.0,
            "estimated_completion": self.current_stats.estimated_completion_time
        }