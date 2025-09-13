"""
Calendar Integration Adapter

Bridges the schedule generator with the CalendarManager system,
converting scheduled games into simulatable events.
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, date
import json
import sys
from pathlib import Path

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from simulation.calendar_manager import CalendarManager, ConflictResolution
from simulation.events.game_simulation_event import GameSimulationEvent
from ..data.schedule_models import ScheduledGame, SeasonSchedule, WeekSchedule


@dataclass
class LoadResult:
    """Result of loading schedule into calendar"""
    successful_games: int = 0
    failed_games: int = 0
    conflicts: List[Dict] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate"""
        total = self.successful_games + self.failed_games
        return self.successful_games / total if total > 0 else 0.0
    
    def add_conflict(self, game: ScheduledGame, error: str):
        """Add a conflict to the result"""
        self.conflicts.append({
            'game_id': game.game_id,
            'week': game.week,
            'teams': f"{game.away_team_id} @ {game.home_team_id}",
            'error': error
        })
        self.failed_games += 1
    
    def add_success(self, game: ScheduledGame):
        """Record successful game scheduling"""
        self.successful_games += 1
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for reporting"""
        return {
            'successful_games': self.successful_games,
            'failed_games': self.failed_games,
            'success_rate': f"{self.success_rate:.1%}",
            'conflicts': self.conflicts,
            'warnings': self.warnings
        }


class ScheduleCalendarAdapter:
    """
    Adapter for integrating NFL schedules with CalendarManager.
    
    Handles conversion between schedule format and calendar events,
    manages conflict resolution, and provides validation.
    """
    
    def __init__(self, calendar_manager: CalendarManager, 
                 conflict_resolution: ConflictResolution = ConflictResolution.REJECT):
        """
        Initialize adapter with calendar manager.
        
        Args:
            calendar_manager: CalendarManager instance to load games into
            conflict_resolution: How to handle scheduling conflicts
        """
        self.calendar = calendar_manager
        self.conflict_resolution = conflict_resolution
        self.loaded_games: List[ScheduledGame] = []
    
    def load_schedule(self, schedule: SeasonSchedule, 
                      validate_first: bool = True) -> LoadResult:
        """
        Load complete season schedule into calendar.
        
        Args:
            schedule: SeasonSchedule to load
            validate_first: Whether to validate schedule before loading
            
        Returns:
            LoadResult with success/failure information
        """
        result = LoadResult()
        
        # Validate schedule if requested
        if validate_first:
            is_valid, errors = schedule.validate()
            if not is_valid:
                for error in errors:
                    result.warnings.append(f"Validation warning: {error}")
        
        # Load games week by week
        for week_num in sorted(schedule.weeks.keys()):
            week = schedule.weeks[week_num]
            week_result = self._load_week(week)
            
            result.successful_games += week_result.successful_games
            result.failed_games += week_result.failed_games
            result.conflicts.extend(week_result.conflicts)
            result.warnings.extend(week_result.warnings)
        
        # Store loaded games for reference
        self.loaded_games = schedule.get_all_games()
        
        # Final summary
        if result.failed_games > 0:
            result.warnings.append(
                f"Failed to schedule {result.failed_games} games. "
                f"Check conflicts list for details."
            )
        
        return result
    
    def _load_week(self, week: WeekSchedule) -> LoadResult:
        """Load all games from a single week"""
        result = LoadResult()
        
        # Sort games by time slot for proper scheduling order
        sorted_games = sorted(week.games, key=lambda g: (g.game_date, g.time_slot.value))
        
        for game in sorted_games:
            try:
                # Convert to calendar event
                event = game.to_calendar_event()
                
                # Schedule in calendar
                success, message = self.calendar.schedule_event(event)
                
                if success:
                    result.add_success(game)
                else:
                    result.add_conflict(game, message)
                    
            except Exception as e:
                result.add_conflict(game, f"Exception: {str(e)}")
        
        return result
    
    def load_games_list(self, games: List[ScheduledGame]) -> LoadResult:
        """
        Load a list of games into the calendar.
        
        Useful for partial schedules or custom game lists.
        """
        result = LoadResult()
        
        for game in games:
            try:
                event = game.to_calendar_event()
                success, message = self.calendar.schedule_event(event)
                
                if success:
                    result.add_success(game)
                else:
                    result.add_conflict(game, message)
                    
            except Exception as e:
                result.add_conflict(game, f"Exception: {str(e)}")
        
        self.loaded_games.extend(games)
        return result
    
    def load_from_json_file(self, filepath: str) -> LoadResult:
        """
        Load schedule from JSON file.
        
        Expected format:
        [
            {
                "game_id": "G0001",
                "week": 1,
                "date": "2024-09-08T13:00:00",
                "home_team": 22,
                "away_team": 12,
                "time_slot": "Sunday 1:00 PM ET",
                "game_type": "division"
            },
            ...
        ]
        """
        result = LoadResult()
        
        try:
            with open(filepath, 'r') as f:
                games_data = json.load(f)
            
            games = []
            for game_data in games_data:
                try:
                    game = ScheduledGame.from_dict(game_data)
                    games.append(game)
                except Exception as e:
                    result.warnings.append(f"Failed to parse game: {e}")
            
            # Load parsed games
            games_result = self.load_games_list(games)
            result.successful_games = games_result.successful_games
            result.failed_games = games_result.failed_games
            result.conflicts = games_result.conflicts
            
        except FileNotFoundError:
            result.warnings.append(f"File not found: {filepath}")
        except json.JSONDecodeError as e:
            result.warnings.append(f"Invalid JSON: {e}")
        except Exception as e:
            result.warnings.append(f"Unexpected error: {e}")
        
        return result
    
    def verify_loaded_schedule(self) -> Dict[str, any]:
        """
        Verify the loaded schedule in the calendar.
        
        Returns statistics about what was loaded.
        """
        stats = {
            'total_games_loaded': len(self.loaded_games),
            'calendar_event_count': 0,
            'teams_with_games': set(),
            'weeks_with_games': set(),
            'primetime_count': 0,
            'conflicts_detected': []
        }
        
        # Check each loaded game
        for game in self.loaded_games:
            # Track teams and weeks
            stats['teams_with_games'].add(game.home_team_id)
            stats['teams_with_games'].add(game.away_team_id)
            stats['weeks_with_games'].add(game.week)
            
            # Count primetime
            if game.is_primetime:
                stats['primetime_count'] += 1
            
            # Check if game exists in calendar
            events = self.calendar.get_events_for_date(game.game_date.date())
            for event in events:
                if hasattr(event, 'home_team_id') and hasattr(event, 'away_team_id'):
                    if (event.home_team_id == game.home_team_id and 
                        event.away_team_id == game.away_team_id):
                        stats['calendar_event_count'] += 1
                        break
        
        # Convert sets to counts for JSON serialization
        stats['unique_teams'] = len(stats['teams_with_games'])
        stats['unique_weeks'] = len(stats['weeks_with_games'])
        del stats['teams_with_games']
        del stats['weeks_with_games']
        
        return stats
    
    def export_calendar_schedule(self, output_path: str):
        """
        Export the loaded schedule from calendar to JSON file.
        
        Useful for debugging and verification.
        """
        schedule_data = []
        
        for game in self.loaded_games:
            game_dict = game.to_dict()
            
            # Add calendar status
            events = self.calendar.get_events_for_date(game.game_date.date())
            game_dict['in_calendar'] = False
            
            for event in events:
                if hasattr(event, 'home_team_id') and hasattr(event, 'away_team_id'):
                    if (event.home_team_id == game.home_team_id and 
                        event.away_team_id == game.away_team_id):
                        game_dict['in_calendar'] = True
                        break
            
            schedule_data.append(game_dict)
        
        # Write to file
        with open(output_path, 'w') as f:
            json.dump(schedule_data, f, indent=2, default=str)
        
        return len(schedule_data)
    
    def clear_loaded_games(self):
        """Clear the list of loaded games"""
        self.loaded_games.clear()
    
    def get_team_calendar_schedule(self, team_id: int) -> List[GameSimulationEvent]:
        """
        Get all games for a team from the calendar.
        
        Returns GameSimulationEvents for compatibility with existing code.
        """
        team_games = []
        
        # Get team schedule from calendar
        team_schedule = self.calendar.get_team_schedule(team_id)
        
        for date_key, events in team_schedule.items():
            for event in events:
                if isinstance(event, GameSimulationEvent):
                    team_games.append(event)
        
        return sorted(team_games, key=lambda g: g.date)


class BatchScheduleLoader:
    """
    Load multiple schedules or schedule variations.
    
    Useful for testing different schedule configurations.
    """
    
    def __init__(self, base_calendar: CalendarManager):
        """Initialize with base calendar"""
        self.base_calendar = base_calendar
        self.adapters: Dict[str, ScheduleCalendarAdapter] = {}
    
    def load_schedule_variant(self, name: str, schedule: SeasonSchedule) -> LoadResult:
        """Load a named schedule variant"""
        adapter = ScheduleCalendarAdapter(self.base_calendar)
        result = adapter.load_schedule(schedule)
        self.adapters[name] = adapter
        return result
    
    def compare_variants(self) -> Dict:
        """Compare loaded schedule variants"""
        comparison = {}
        
        for name, adapter in self.adapters.items():
            stats = adapter.verify_loaded_schedule()
            comparison[name] = stats
        
        return comparison