"""
Schedule to Event Converter

Converts GameSlots from the schedule into GameSimulationEvents for the calendar.
Handles date/time mapping and event creation.
"""

from typing import List, Optional
from datetime import datetime, date, time
import logging

from ..template.schedule_template import SeasonSchedule
from ..template.time_slots import GameSlot, TimeSlot
from ..utils.date_calculator import WeekToDateCalculator


class ScheduleToEventConverter:
    """
    Converts scheduled GameSlots into GameSimulationEvents.
    
    This class bridges the gap between the abstract schedule (Week 1, TNF)
    and concrete calendar events (September 4, 2025 8:20 PM).
    """
    
    def __init__(self, date_calculator: WeekToDateCalculator, team_registry=None, store_manager=None):
        """
        Initialize the converter with a date calculator and optional components.
        
        Args:
            date_calculator: Calculator for mapping weeks to actual dates
            team_registry: Dynasty Team Registry for consistent team data (optional)
            store_manager: StoreManager for immediate game result persistence (optional)
        """
        self.date_calculator = date_calculator
        self.team_registry = team_registry
        self.store_manager = store_manager
        self.logger = logging.getLogger(__name__)
        
        # Log registry status for debugging
        if self.team_registry:
            if hasattr(self.team_registry, 'is_initialized') and self.team_registry.is_initialized():
                self.logger.info(f"ScheduleToEventConverter initialized with registry: {len(self.team_registry)} teams")
            else:
                self.logger.warning("ScheduleToEventConverter initialized with uninitialized registry")
        else:
            self.logger.warning("ScheduleToEventConverter initialized without team registry - events will use fallback team mappings")
        
    def convert_schedule(self, schedule: SeasonSchedule) -> List:
        """
        Convert all assigned games in a schedule to GameSimulationEvents.
        
        Args:
            schedule: The season schedule with assigned games
            
        Returns:
            List of GameSimulationEvents ready for calendar scheduling
        """
        events = []
        assigned_games = schedule.get_assigned_games()
        
        self.logger.info(f"Converting {len(assigned_games)} games to events")
        
        for game in assigned_games:
            try:
                event = self.convert_game_slot(game)
                if event:
                    events.append(event)
            except Exception as e:
                self.logger.error(f"Failed to convert game {game}: {e}")
                
        self.logger.info(f"Successfully converted {len(events)} games to events")
        return events
    
    def convert_game_slot(self, game_slot: GameSlot):
        """
        Convert a single GameSlot to a GameSimulationEvent.
        
        Args:
            game_slot: The game slot with week, time slot, and team IDs
            
        Returns:
            GameSimulationEvent ready for calendar scheduling
        """
        # Get the game datetime
        game_datetime = self._get_game_datetime(game_slot.week, game_slot.time_slot)
        
        # Try to import GameSimulationEvent - handle if not available
        try:
            from simulation.events.game_simulation_event import GameSimulationEvent
        except ImportError:
            # If GameSimulationEvent not available, return a dict representation
            self.logger.warning("GameSimulationEvent not available, using dict")
            return {
                'date': game_datetime,
                'away_team_id': game_slot.away_team_id,
                'home_team_id': game_slot.home_team_id,
                'week': game_slot.week,
                'season_type': 'regular_season'
            }
        
        # Create GameSimulationEvent with registry injection
        try:
            event = GameSimulationEvent(
                date=game_datetime,
                away_team_id=game_slot.away_team_id,
                home_team_id=game_slot.home_team_id,
                week=game_slot.week,
                season_type="regular_season",
                team_registry=self.team_registry,  # Inject registry to avoid import issues
                store_manager=self.store_manager   # Inject store manager for immediate persistence
            )
            
            # Validate event creation with registry (for critical team IDs)
            if self.team_registry and hasattr(self.team_registry, 'is_initialized') and self.team_registry.is_initialized():
                # Test problematic team mappings that caused the original issue
                if game_slot.away_team_id in [14, 16] or game_slot.home_team_id in [14, 16]:
                    expected_14 = self.team_registry.get_team_abbreviation(14) if hasattr(self.team_registry, 'get_team_abbreviation') else None
                    expected_16 = self.team_registry.get_team_abbreviation(16) if hasattr(self.team_registry, 'get_team_abbreviation') else None
                    
                    self.logger.debug(f"Created event with registry: {event.event_name} "
                                    f"(Team 14={expected_14}, Team 16={expected_16})")
            
            return event
            
        except TypeError as e:
            # GameSimulationEvent doesn't support team_registry parameter yet
            self.logger.warning(f"GameSimulationEvent doesn't support registry injection yet: {e}")
            self.logger.warning("Creating event without registry - this may cause Week 5+ standings issues")
            
            # Fallback to original creation without registry but with store_manager
            return GameSimulationEvent(
                date=game_datetime,
                away_team_id=game_slot.away_team_id,
                home_team_id=game_slot.home_team_id,
                week=game_slot.week,
                season_type="regular_season",
                store_manager=self.store_manager
            )
        except Exception as e:
            self.logger.error(f"Failed to create GameSimulationEvent for Week {game_slot.week} "
                            f"Teams {game_slot.away_team_id}@{game_slot.home_team_id}: {e}")
            raise
    
    def _get_game_datetime(self, week: int, time_slot: TimeSlot) -> datetime:
        """
        Get the actual datetime for a game based on week and time slot.
        
        Args:
            week: NFL week number (1-18)
            time_slot: Time slot enum (TNF, SUNDAY_EARLY, etc.)
            
        Returns:
            datetime object with the game's date and time
        """
        # Get the dates for this week
        game_dates = self.date_calculator.get_game_dates_for_week(week)
        
        # Determine which day based on time slot
        time_slot_value = time_slot.value.upper()
        
        # Check for exact slot names first
        if time_slot_value == 'TNF' or 'THURSDAY' in time_slot_value:
            game_date = game_dates['thursday']
            game_time = time(20, 20)  # 8:20 PM ET for TNF
        elif time_slot_value == 'MNF' or ('MONDAY' in time_slot_value and time_slot_value != 'MNF'):
            game_date = game_dates['monday']
            game_time = time(20, 15)  # 8:15 PM ET for MNF
        elif time_slot_value == 'SNF':
            game_date = game_dates['sunday']
            game_time = time(20, 20)  # 8:20 PM ET for SNF
        else:  # Sunday games (early and late afternoon)
            game_date = game_dates['sunday']
            
            # Add time component based on slot
            if 'EARLY' in time_slot_value or '1PM' in time_slot_value:
                game_time = time(13, 0)  # 1:00 PM ET
            elif 'LATE' in time_slot_value or '4PM' in time_slot_value or '425' in time_slot_value:
                game_time = time(16, 25)  # 4:25 PM ET
            else:
                # Default to 1 PM for any unrecognized slot
                game_time = time(13, 0)
                self.logger.warning(f"Unknown time slot '{time_slot_value}', defaulting to 1 PM")
        
        return datetime.combine(game_date, game_time)
    
    def get_event_summary(self, events: List) -> dict:
        """
        Get a summary of the converted events.
        
        Args:
            events: List of GameSimulationEvents
            
        Returns:
            Dictionary with event statistics
        """
        if not events:
            return {
                'total_events': 0,
                'weeks_covered': [],
                'thursday_games': 0,
                'sunday_games': 0,
                'monday_games': 0,
                'primetime_games': 0
            }
        
        weeks = set()
        thursday_count = 0
        sunday_count = 0
        monday_count = 0
        primetime_count = 0
        
        for event in events:
            # Handle both dict and GameSimulationEvent
            if isinstance(event, dict):
                event_date = event['date']
                week = event['week']
            else:
                event_date = event.date
                week = event.week
            
            weeks.add(week)
            
            # Count by day of week
            weekday = event_date.weekday()
            if weekday == 3:  # Thursday
                thursday_count += 1
                primetime_count += 1  # TNF is primetime
            elif weekday == 6:  # Sunday
                sunday_count += 1
                # Check if it's Sunday Night
                if event_date.hour >= 20:
                    primetime_count += 1
            elif weekday == 0:  # Monday
                monday_count += 1
                primetime_count += 1  # MNF is primetime
        
        return {
            'total_events': len(events),
            'weeks_covered': sorted(list(weeks)),
            'thursday_games': thursday_count,
            'sunday_games': sunday_count,
            'monday_games': monday_count,
            'primetime_games': primetime_count,
            'first_game': min((e['date'] if isinstance(e, dict) else e.date) for e in events),
            'last_game': max((e['date'] if isinstance(e, dict) else e.date) for e in events)
        }