"""
Calendar Manager

Core calendar system for managing day-by-day simulation progression.
Handles event scheduling, conflict detection, and daily execution of all simulatable events.
"""

from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple, Set, Any
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
import logging

from .events.base_simulation_event import BaseSimulationEvent, SimulationResult, EventType
from .processors.base_processor import BaseResultProcessor, ProcessingStrategy, ProcessorConfig
from .processors import (GameResultProcessor, TrainingResultProcessor, ScoutingResultProcessor, 
                        AdministrativeResultProcessor, RestResultProcessor)
from .results.base_result import ProcessingContext, ProcessingResult, AnySimulationResult
from .season_state_manager import SeasonStateManager


class SchedulingError(Exception):
    """Raised when there are issues with event scheduling"""
    pass


class ConflictResolution(Enum):
    """How to handle scheduling conflicts"""
    REJECT = "reject"           # Reject new event if conflict exists
    RESCHEDULE = "reschedule"   # Try to reschedule conflicting events
    FORCE = "force"             # Allow conflict (override safety checks)


@dataclass
class DaySimulationResult:
    """Result of simulating all events on a single day"""
    date: date
    events_scheduled: int
    events_executed: int
    successful_events: int
    failed_events: int
    event_results: List[SimulationResult] = field(default_factory=list)
    processing_results: List[ProcessingResult] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    total_duration_hours: float = 0.0
    teams_involved: Set[int] = field(default_factory=set)
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate of events for this day"""
        if self.events_executed == 0:
            return 0.0
        return self.successful_events / self.events_executed
    
    @property
    def processing_success_rate(self) -> float:
        """Calculate success rate of result processing for this day"""
        if not self.processing_results:
            return 1.0  # No processing = perfect success
        successful = sum(1 for p in self.processing_results if p.processed_successfully)
        return successful / len(self.processing_results)


@dataclass
class CalendarStats:
    """Statistics about the calendar and scheduled events"""
    total_events: int = 0
    events_by_type: Dict[EventType, int] = field(default_factory=dict)
    teams_with_events: Set[int] = field(default_factory=set)
    date_range: Optional[Tuple[date, date]] = None
    total_scheduled_hours: float = 0.0
    
    # Result processing statistics
    result_processing_enabled: bool = False
    total_processed_results: int = 0
    processing_success_rate: float = 0.0
    season_state_tracked: bool = False


class CalendarManager:
    """
    Core calendar manager for day-by-day simulation system.
    
    Manages event scheduling, conflict resolution, and execution of daily simulations.
    Provides the foundation for season-long simulations with multiple event types.
    """
    
    def __init__(self, start_date: date, 
                 conflict_resolution: ConflictResolution = ConflictResolution.REJECT,
                 enable_result_processing: bool = True,
                 processing_strategy: ProcessingStrategy = ProcessingStrategy.FULL_PROGRESSION,
                 season_year: int = 2024):
        """
        Initialize calendar manager
        
        Args:
            start_date: Starting date for the simulation calendar
            conflict_resolution: How to handle scheduling conflicts
            enable_result_processing: Whether to enable result processing pipeline
            processing_strategy: Default processing strategy for results
            season_year: Year of the season being simulated
        """
        self.current_date = start_date
        self.start_date = start_date
        self.conflict_resolution = conflict_resolution
        self.enable_result_processing = enable_result_processing
        self.processing_strategy = processing_strategy
        self.season_year = season_year
        
        # Event storage - indexed by date for efficient access
        self._events_by_date: Dict[date, List[BaseSimulationEvent]] = defaultdict(list)
        
        # Team availability tracking - tracks which teams are busy on which dates
        self._team_availability: Dict[date, Set[int]] = defaultdict(set)
        
        # Event ID tracking for uniqueness and removal
        self._events_by_id: Dict[str, BaseSimulationEvent] = {}
        
        # Simulation history
        self._simulation_history: Dict[date, DaySimulationResult] = {}
        
        # Logger for debugging and monitoring
        self.logger = logging.getLogger(__name__)
        
        # Result processing system
        if self.enable_result_processing:
            self._initialize_result_processing()
    
    def _initialize_result_processing(self) -> None:
        """Initialize the result processing system"""
        # Create season state manager
        self.season_state_manager = SeasonStateManager(season_year=self.season_year)
        
        # Initialize result processors with default configuration
        processor_config = ProcessorConfig(strategy=self.processing_strategy)
        
        self._result_processors = [
            GameResultProcessor(processor_config),
            TrainingResultProcessor(processor_config),
            ScoutingResultProcessor(processor_config),
            AdministrativeResultProcessor(processor_config),
            RestResultProcessor(processor_config)
        ]
        
        self.logger.info(f"Initialized result processing with {len(self._result_processors)} processors")
    
    def get_season_state_manager(self) -> Optional[SeasonStateManager]:
        """Get the season state manager if result processing is enabled"""
        return getattr(self, 'season_state_manager', None)
    
    def set_processing_strategy(self, strategy: ProcessingStrategy) -> None:
        """Update the processing strategy for all processors"""
        self.processing_strategy = strategy
        
        if self.enable_result_processing and hasattr(self, '_result_processors'):
            for processor in self._result_processors:
                processor.config.strategy = strategy
            self.logger.info(f"Updated processing strategy to {strategy.value}")
    
    def _process_event_result(self, event_result: SimulationResult, context: ProcessingContext) -> Optional[ProcessingResult]:
        """Process an event result through the appropriate processor"""
        if not self.enable_result_processing:
            return None
        
        # Find appropriate processor for this result type
        for processor in self._result_processors:
            if processor.can_process(event_result):
                processing_result = processor.process_with_error_handling(event_result, context)
                
                # Apply to season state manager
                if hasattr(self, 'season_state_manager'):
                    self.season_state_manager.apply_processing_result(processing_result, context)
                
                return processing_result
        
        self.logger.warning(f"No processor found for result type: {type(event_result).__name__}")
        return None
    
    def schedule_event(self, event: BaseSimulationEvent, 
                      target_date: Optional[date] = None) -> Tuple[bool, str]:
        """
        Schedule an event on the calendar
        
        Args:
            event: Event to schedule
            target_date: Optional specific date (uses event.date if None)
            
        Returns:
            tuple: (success, message) indicating if scheduling succeeded
        """
        # Use event's date if no target date specified
        schedule_date = target_date or event.date.date()
        
        # Validate the event first
        is_valid, error_msg = event.validate_preconditions()
        if not is_valid:
            return False, f"Event validation failed: {error_msg}"
        
        # Check for conflicts
        conflicts = self._check_conflicts(event, schedule_date)
        if conflicts:
            return self._handle_conflicts(event, schedule_date, conflicts)
        
        # Schedule the event
        self._add_event_to_schedule(event, schedule_date)
        self.logger.info(f"Scheduled event {event.event_name} on {schedule_date}")
        
        return True, f"Event '{event.event_name}' scheduled successfully for {schedule_date}"
    
    def remove_event(self, event_id: str) -> bool:
        """
        Remove an event from the calendar
        
        Args:
            event_id: ID of event to remove
            
        Returns:
            bool: True if event was removed, False if not found
        """
        if event_id not in self._events_by_id:
            return False
        
        event = self._events_by_id[event_id]
        event_date = event.date.date()
        
        # Remove from date index
        self._events_by_date[event_date].remove(event)
        if not self._events_by_date[event_date]:
            del self._events_by_date[event_date]
        
        # Remove from ID index
        del self._events_by_id[event_id]
        
        # Remove team availability
        for team_id in event.involved_teams:
            self._team_availability[event_date].discard(team_id)
        
        self.logger.info(f"Removed event {event.event_name} from {event_date}")
        return True
    
    def get_events_for_date(self, target_date: date) -> List[BaseSimulationEvent]:
        """
        Get all events scheduled for a specific date
        
        Args:
            target_date: Date to query
            
        Returns:
            List of events scheduled for that date
        """
        return list(self._events_by_date.get(target_date, []))
    
    def get_team_schedule(self, team_id: int, 
                         start_date: Optional[date] = None,
                         end_date: Optional[date] = None) -> Dict[date, List[BaseSimulationEvent]]:
        """
        Get schedule for a specific team within date range
        
        Args:
            team_id: Team to get schedule for
            start_date: Start of date range (default: calendar start)
            end_date: End of date range (default: latest scheduled event)
            
        Returns:
            Dictionary mapping dates to events for that team
        """
        start = start_date or self.start_date
        end = end_date or self._get_latest_event_date()
        
        team_schedule = {}
        current = start
        
        while current <= end:
            events_today = [event for event in self.get_events_for_date(current)
                           if team_id in event.involved_teams]
            if events_today:
                team_schedule[current] = events_today
            current += timedelta(days=1)
        
        return team_schedule
    
    def is_team_available(self, team_id: int, target_date: date) -> bool:
        """
        Check if a team is available on a specific date
        
        Args:
            team_id: Team to check
            target_date: Date to check
            
        Returns:
            bool: True if team is available, False if already scheduled
        """
        return team_id not in self._team_availability[target_date]
    
    def simulate_day(self, target_date: date) -> DaySimulationResult:
        """
        Simulate all events for a specific day
        
        Args:
            target_date: Date to simulate
            
        Returns:
            DaySimulationResult: Complete results for the day
        """
        events = self.get_events_for_date(target_date)
        
        result = DaySimulationResult(
            date=target_date,
            events_scheduled=len(events),
            events_executed=0,
            successful_events=0,
            failed_events=0
        )
        
        self.logger.info(f"Starting simulation for {target_date} with {len(events)} events")
        
        # Create processing context for this day
        context = None
        if self.enable_result_processing:
            # Calculate season week (rough approximation based on start date)
            days_elapsed = (target_date - self.start_date).days
            season_week = max(1, days_elapsed // 7)
            
            context = ProcessingContext(
                current_date=datetime.combine(target_date, datetime.min.time()),
                season_week=season_week,
                season_phase="regular_season"  # Could be enhanced to detect actual phase
            )
        
        for event in events:
            try:
                # Execute event simulation
                event_result = event.simulate()
                
                result.events_executed += 1
                result.event_results.append(event_result)
                result.total_duration_hours += event.duration_hours
                result.teams_involved.update(event.involved_teams)
                
                if event_result.success:
                    result.successful_events += 1
                    self.logger.debug(f"Successfully simulated {event.event_name}")
                    
                    # Process the event result if processing is enabled
                    if self.enable_result_processing and context:
                        try:
                            processing_result = self._process_event_result(event_result, context)
                            if processing_result:
                                result.processing_results.append(processing_result)
                        except Exception as e:
                            error_msg = f"Error processing result for {event.event_name}: {str(e)}"
                            result.errors.append(error_msg)
                            self.logger.error(error_msg, exc_info=True)
                else:
                    result.failed_events += 1
                    error_msg = f"Event {event.event_name} failed: {event_result.error_message}"
                    result.errors.append(error_msg)
                    self.logger.warning(error_msg)
                
            except Exception as e:
                result.failed_events += 1
                error_msg = f"Exception in {event.event_name}: {str(e)}"
                result.errors.append(error_msg)
                self.logger.error(error_msg, exc_info=True)
        
        # Store simulation result
        self._simulation_history[target_date] = result
        
        processing_summary = ""
        if result.processing_results:
            processing_summary = f" (processing: {result.processing_success_rate:.1%})"
        
        self.logger.info(f"Completed simulation for {target_date}: "
                        f"{result.successful_events}/{result.events_executed} events successful{processing_summary}")
        
        return result
    
    def advance_to_date(self, target_date: date) -> List[DaySimulationResult]:
        """
        Advance calendar and simulate all days up to target date
        
        Args:
            target_date: Date to advance to
            
        Returns:
            List of DaySimulationResult for each day simulated
        """
        if target_date < self.current_date:
            raise ValueError(f"Cannot advance backwards from {self.current_date} to {target_date}")
        
        results = []
        current = self.current_date
        
        while current <= target_date:
            day_result = self.simulate_day(current)
            results.append(day_result)
            current += timedelta(days=1)
        
        self.current_date = target_date + timedelta(days=1)
        return results
    
    def get_available_dates(self, team_ids: List[int], 
                           duration_days: int = 1,
                           start_search: Optional[date] = None,
                           max_search_days: int = 30) -> List[date]:
        """
        Find available dates for scheduling events involving specific teams
        
        Args:
            team_ids: Teams that need to be available
            duration_days: How many consecutive days needed
            start_search: When to start searching (default: current_date)
            max_search_days: Maximum days to search ahead
            
        Returns:
            List of available start dates
        """
        start = start_search or self.current_date
        available_dates = []
        
        for days_ahead in range(max_search_days):
            candidate_date = start + timedelta(days=days_ahead)
            
            # Check if all teams are available for the required duration
            is_available = True
            for day_offset in range(duration_days):
                check_date = candidate_date + timedelta(days=day_offset)
                for team_id in team_ids:
                    if not self.is_team_available(team_id, check_date):
                        is_available = False
                        break
                if not is_available:
                    break
            
            if is_available:
                available_dates.append(candidate_date)
        
        return available_dates
    
    def get_calendar_stats(self) -> CalendarStats:
        """
        Get statistics about the current calendar state
        
        Returns:
            CalendarStats: Comprehensive calendar statistics
        """
        stats = CalendarStats()
        
        all_dates = list(self._events_by_date.keys())
        if all_dates:
            stats.date_range = (min(all_dates), max(all_dates))
        
        for events in self._events_by_date.values():
            for event in events:
                stats.total_events += 1
                event_type = event.get_event_type()
                stats.events_by_type[event_type] = stats.events_by_type.get(event_type, 0) + 1
                stats.teams_with_events.update(event.involved_teams)
                stats.total_scheduled_hours += event.duration_hours
        
        # Add processing statistics
        stats.result_processing_enabled = self.enable_result_processing
        stats.season_state_tracked = hasattr(self, 'season_state_manager')
        
        # Calculate processing statistics from simulation history
        total_processing_results = 0
        successful_processing_results = 0
        
        for day_result in self._simulation_history.values():
            total_processing_results += len(day_result.processing_results)
            successful_processing_results += sum(1 for p in day_result.processing_results if p.processed_successfully)
        
        stats.total_processed_results = total_processing_results
        if total_processing_results > 0:
            stats.processing_success_rate = successful_processing_results / total_processing_results
        
        return stats
    
    def get_processing_summary(self) -> Dict[str, Any]:
        """Get a summary of result processing activity"""
        if not self.enable_result_processing:
            return {"result_processing_enabled": False}
        
        summary = {
            "result_processing_enabled": True,
            "processing_strategy": self.processing_strategy.value,
            "season_year": self.season_year
        }
        
        if hasattr(self, 'season_state_manager'):
            summary["season_state"] = self.season_state_manager.get_season_summary()
        
        if hasattr(self, '_result_processors'):
            processor_stats = []
            for processor in self._result_processors:
                processor_stats.append(processor.get_processing_stats())
            summary["processor_statistics"] = processor_stats
        
        return summary
    
    def get_simulation_history(self, start_date: Optional[date] = None, 
                              end_date: Optional[date] = None) -> Dict[date, DaySimulationResult]:
        """Get simulation history within date range"""
        if not start_date and not end_date:
            return dict(self._simulation_history)
        
        filtered_history = {}
        for sim_date, day_result in self._simulation_history.items():
            include = True
            if start_date and sim_date < start_date:
                include = False
            if end_date and sim_date > end_date:
                include = False
            
            if include:
                filtered_history[sim_date] = day_result
        
        return filtered_history
    
    def clear_schedule(self) -> int:
        """
        Clear all scheduled events
        
        Returns:
            int: Number of events cleared
        """
        event_count = len(self._events_by_id)
        
        self._events_by_date.clear()
        self._team_availability.clear()
        self._events_by_id.clear()
        self._simulation_history.clear()
        
        self.logger.info(f"Cleared {event_count} events from calendar")
        return event_count
    
    def _check_conflicts(self, event: BaseSimulationEvent, schedule_date: date) -> List[BaseSimulationEvent]:
        """Check for conflicts with existing events"""
        conflicts = []
        existing_events = self.get_events_for_date(schedule_date)
        
        for existing_event in existing_events:
            if not event.can_coexist_with(existing_event):
                conflicts.append(existing_event)
        
        return conflicts
    
    def _handle_conflicts(self, event: BaseSimulationEvent, 
                         schedule_date: date, 
                         conflicts: List[BaseSimulationEvent]) -> Tuple[bool, str]:
        """Handle scheduling conflicts based on resolution strategy"""
        conflict_names = [c.event_name for c in conflicts]
        
        if self.conflict_resolution == ConflictResolution.REJECT:
            return False, f"Scheduling conflict with events: {conflict_names}"
        
        elif self.conflict_resolution == ConflictResolution.FORCE:
            self._add_event_to_schedule(event, schedule_date)
            return True, f"Event scheduled despite conflicts with: {conflict_names}"
        
        elif self.conflict_resolution == ConflictResolution.RESCHEDULE:
            # Try to find alternative date
            available_dates = self.get_available_dates(event.involved_teams, 1, schedule_date, 7)
            if available_dates:
                alt_date = available_dates[0]
                self._add_event_to_schedule(event, alt_date)
                return True, f"Event rescheduled to {alt_date} due to conflicts"
            else:
                return False, f"Could not reschedule due to conflicts: {conflict_names}"
        
        return False, "Unknown conflict resolution strategy"
    
    def _add_event_to_schedule(self, event: BaseSimulationEvent, schedule_date: date) -> None:
        """Add event to internal schedule structures"""
        # Update event's date to match schedule date
        event.date = datetime.combine(schedule_date, datetime.min.time())
        
        # Add to indexes
        self._events_by_date[schedule_date].append(event)
        self._events_by_id[event.event_id] = event
        
        # Mark teams as unavailable
        for team_id in event.involved_teams:
            self._team_availability[schedule_date].add(team_id)
    
    def _get_latest_event_date(self) -> date:
        """Get the date of the latest scheduled event"""
        if not self._events_by_date:
            return self.current_date
        return max(self._events_by_date.keys())
    
    def __str__(self) -> str:
        """String representation of calendar status"""
        stats = self.get_calendar_stats()
        return (f"CalendarManager(current_date={self.current_date}, "
                f"events={stats.total_events}, "
                f"date_range={stats.date_range})")
    
    def __repr__(self) -> str:
        """Detailed representation for debugging"""
        return (f"CalendarManager(start_date={self.start_date}, "
                f"current_date={self.current_date}, "
                f"conflict_resolution={self.conflict_resolution.value}, "
                f"total_events={len(self._events_by_id)})")