"""
Calendar Manager

Main calendar interface that coordinates date tracking and event management.
Provides a clean, simple API for all calendar operations.
"""

from datetime import date, datetime, timedelta
from typing import List, Optional, Dict, Any, Union
import logging

from .event import Event
from .event_manager import EventManager
from .event_factory import EventFactory


class CalendarManager:
    """
    Main calendar system interface.

    Coordinates date tracking, event scheduling, and event retrieval.
    Provides a simple, clean API for all calendar operations.
    """

    def __init__(self, start_date: Union[date, datetime],
                 database_path: str = "data/database/nfl_simulation.db",
                 enable_cache: bool = True):
        """
        Initialize the calendar manager.

        Args:
            start_date: Starting date for the calendar
            database_path: Path to SQLite database
            enable_cache: Whether to enable event caching
        """
        # Convert datetime to date if needed
        if isinstance(start_date, datetime):
            start_date = start_date.date()

        self.start_date = start_date
        self.current_date = start_date

        # Event management system
        self.event_manager = EventManager(database_path, enable_cache)

        # Logger for debugging
        self.logger = logging.getLogger(__name__)

        self.logger.info(f"CalendarManager initialized with start date: {start_date}")

    def get_current_date(self) -> date:
        """
        Get the current calendar date.

        Returns:
            date: The current date in the calendar
        """
        return self.current_date

    def advance_date(self, days: int = 1) -> date:
        """
        Advance the calendar by a specified number of days.

        Args:
            days: Number of days to advance (default: 1)

        Returns:
            date: The new current date after advancing
        """
        if days < 0:
            self.logger.warning(f"Cannot advance calendar by negative days: {days}")
            return self.current_date

        self.current_date += timedelta(days=days)
        self.logger.debug(f"Advanced calendar to {self.current_date}")
        return self.current_date

    def set_date(self, new_date: Union[date, datetime]) -> date:
        """
        Set the calendar to a specific date.

        Args:
            new_date: Date to set the calendar to

        Returns:
            date: The new current date
        """
        self.current_date = self._convert_to_date(new_date)
        self.logger.debug(f"Set calendar date to {self.current_date}")
        return self.current_date

    def schedule_event(self, event: Event) -> bool:
        """
        Add an event to the calendar.

        Args:
            event: Event to schedule

        Returns:
            bool: True if event was scheduled successfully, False otherwise
        """
        success, error_message = self.event_manager.save_event(event)
        if not success:
            self.logger.warning(f"Failed to schedule event {event.name}: {error_message}")
        return success

    def get_events_for_date(self, target_date: Union[date, datetime]) -> List[Event]:
        """
        Get all events scheduled for a specific date.

        Args:
            target_date: Date to get events for

        Returns:
            List[Event]: List of events scheduled for that date
        """
        target_date = self._convert_to_date(target_date)
        return self.event_manager.get_events_by_date(target_date)

    def get_events_between(self, start_date: Union[date, datetime],
                          end_date: Union[date, datetime]) -> List[Event]:
        """
        Get all events between two dates (inclusive).

        Args:
            start_date: Start of date range
            end_date: End of date range

        Returns:
            List[Event]: List of events in the date range
        """
        start_date = self._convert_to_date(start_date)
        end_date = self._convert_to_date(end_date)
        return self.event_manager.get_events_between(start_date, end_date)

    def remove_event(self, event_id: str) -> bool:
        """
        Remove an event from the calendar.

        Args:
            event_id: Unique ID of the event to remove

        Returns:
            bool: True if event was removed, False if not found
        """
        success, error_message = self.event_manager.delete_event(event_id)
        if not success:
            self.logger.warning(f"Failed to remove event {event_id}: {error_message}")
        return success

    def get_event_by_id(self, event_id: str) -> Optional[Event]:
        """
        Get a specific event by its ID.

        Args:
            event_id: Unique ID of the event

        Returns:
            Optional[Event]: The event if found, None otherwise
        """
        return self.event_manager.get_event_by_id(event_id)

    def has_events_on_date(self, target_date: Union[date, datetime]) -> bool:
        """
        Check if there are any events on a specific date.

        Args:
            target_date: Date to check

        Returns:
            bool: True if there are events on that date, False otherwise
        """
        target_date = self._convert_to_date(target_date)
        events = self.event_manager.get_events_by_date(target_date)
        return len(events) > 0

    def get_next_event_date(self, from_date: Optional[Union[date, datetime]] = None) -> Optional[date]:
        """
        Get the next date that has events scheduled.

        Args:
            from_date: Date to start searching from (default: current date)

        Returns:
            Optional[date]: Next date with events, or None if no future events
        """
        if from_date is None:
            from_date = self.current_date
        else:
            from_date = self._convert_to_date(from_date)

        dates_with_events = self.event_manager.get_dates_with_events()
        future_dates = [d for d in dates_with_events if d > from_date]

        return min(future_dates) if future_dates else None

    def get_previous_event_date(self, from_date: Optional[Union[date, datetime]] = None) -> Optional[date]:
        """
        Get the previous date that had events scheduled.

        Args:
            from_date: Date to start searching from (default: current date)

        Returns:
            Optional[date]: Previous date with events, or None if no past events
        """
        if from_date is None:
            from_date = self.current_date
        else:
            from_date = self._convert_to_date(from_date)

        dates_with_events = self.event_manager.get_dates_with_events()
        past_dates = [d for d in dates_with_events if d < from_date]

        return max(past_dates) if past_dates else None

    def get_calendar_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the calendar state.

        Returns:
            Dict[str, Any]: Summary including current date, total events, etc.
        """
        manager_stats = self.event_manager.get_manager_stats()
        dates_with_events = self.event_manager.get_dates_with_events()

        return {
            "start_date": self.start_date.isoformat(),
            "current_date": self.current_date.isoformat(),
            "total_events": manager_stats.total_events,
            "cached_events": manager_stats.cached_events,
            "dates_with_events": manager_stats.dates_with_events,
            "cache_hit_rate": manager_stats.cache_hit_rate,
            "earliest_event_date": dates_with_events[0].isoformat() if dates_with_events else None,
            "latest_event_date": dates_with_events[-1].isoformat() if dates_with_events else None
        }

    def clear_calendar(self) -> int:
        """
        Remove all events from the calendar.

        Returns:
            int: Number of events that were removed
        """
        cleared_count = self.event_manager.clear_all_events()
        self.logger.info(f"Cleared calendar: {cleared_count} events removed")
        return cleared_count

    def reset_to_date(self, reset_date: Union[date, datetime]) -> None:
        """
        Reset the calendar to a specific date and clear all events.

        Args:
            reset_date: Date to reset the calendar to
        """
        self.current_date = self._convert_to_date(reset_date)
        self.event_manager.clear_all_events()
        self.logger.info(f"Calendar reset to {self.current_date} with all events cleared")

    def _convert_to_date(self, date_input: Union[date, datetime]) -> date:
        """
        Convert datetime to date if needed.

        Args:
            date_input: Date or datetime to convert

        Returns:
            date: Converted date
        """
        if isinstance(date_input, datetime):
            return date_input.date()
        return date_input

    def __str__(self) -> str:
        """String representation of the calendar manager."""
        total_events = self.event_manager.get_events_count()
        return f"CalendarManager(current_date={self.current_date}, events={total_events})"

    # Dynasty and Simulation-Specific Methods

    def schedule_game(
        self,
        name: str,
        event_date: Union[date, datetime],
        away_team_id: int,
        home_team_id: int,
        week: int,
        season: int,
        dynasty_id: str,
        overtime_type: str = "regular_season",
        database_path: Optional[str] = None,
        enable_persistence: bool = True,
        **kwargs
    ) -> bool:
        """
        Schedule a game event with validation and proper metadata structure.

        Args:
            name: Game name (e.g., "Week 1: Browns @ Texans")
            event_date: Date the game is scheduled
            away_team_id: Team ID for away team (1-32)
            home_team_id: Team ID for home team (1-32)
            week: Week number in season
            season: Season year
            dynasty_id: Dynasty identifier
            overtime_type: Type of overtime rules
            database_path: Optional custom database path
            enable_persistence: Whether to enable statistics persistence
            **kwargs: Additional configuration options

        Returns:
            bool: True if game was scheduled successfully, False otherwise
        """
        try:
            event_date = self._convert_to_date(event_date)

            game_event = EventFactory.create_game_event(
                name=name,
                event_date=event_date,
                away_team_id=away_team_id,
                home_team_id=home_team_id,
                week=week,
                season=season,
                dynasty_id=dynasty_id,
                overtime_type=overtime_type,
                database_path=database_path,
                enable_persistence=enable_persistence,
                **kwargs
            )

            # Validate before scheduling
            is_valid, error = EventFactory.validate_event_for_creation(game_event)
            if not is_valid:
                self.logger.error(f"Invalid game event: {error}")
                return False

            return self.schedule_event(game_event)

        except Exception as e:
            self.logger.error(f"Failed to schedule game: {e}")
            return False

    def get_game_events_for_dynasty(
        self,
        dynasty_id: str,
        season: Optional[int] = None,
        status: Optional[str] = None,
        week: Optional[int] = None
    ) -> List[Event]:
        """
        Get all game events for a dynasty, optionally filtered by season, status, or week.

        Args:
            dynasty_id: Dynasty identifier
            season: Optional season filter
            status: Optional status filter ('scheduled', 'completed', etc.)
            week: Optional week filter

        Returns:
            List[Event]: List of game events matching criteria
        """
        try:
            # Determine date range
            if season:
                start_date = date(season, 1, 1)
                end_date = date(season, 12, 31)
                events = self.get_events_between(start_date, end_date)
            else:
                # Get all events (this could be slow for large calendars)
                dates_with_events = self.event_manager.get_dates_with_events()
                if not dates_with_events:
                    return []

                start_date = dates_with_events[0]
                end_date = dates_with_events[-1]
                events = self.get_events_between(start_date, end_date)

            # Filter for dynasty and game events
            game_events = []
            for event in events:
                if (event.get_dynasty_id() == dynasty_id and
                    event.get_event_type() == "game_simulation"):

                    # Apply additional filters
                    if status is not None and event.get_status() != status:
                        continue

                    if week is not None and event.get_week() != week:
                        continue

                    game_events.append(event)

            return game_events

        except Exception as e:
            self.logger.error(f"Failed to get game events for dynasty {dynasty_id}: {e}")
            return []

    def get_upcoming_games(
        self,
        dynasty_id: str,
        from_date: Optional[Union[date, datetime]] = None,
        limit: int = 10
    ) -> List[Event]:
        """
        Get upcoming games for a dynasty.

        Args:
            dynasty_id: Dynasty identifier
            from_date: Date to start searching from (default: current date)
            limit: Maximum number of games to return

        Returns:
            List[Event]: List of upcoming game events
        """
        try:
            if from_date is None:
                from_date = self.current_date
            else:
                from_date = self._convert_to_date(from_date)

            # Get next 90 days of events (should cover most upcoming games)
            end_date = from_date + timedelta(days=90)
            events = self.get_events_between(from_date, end_date)

            upcoming_games = []
            for event in events:
                if (event.get_dynasty_id() == dynasty_id and
                    event.get_event_type() == "game_simulation" and
                    not event.is_completed() and
                    event.event_date >= from_date):

                    upcoming_games.append(event)

                    if len(upcoming_games) >= limit:
                        break

            # Sort by date
            upcoming_games.sort(key=lambda e: e.event_date)
            return upcoming_games

        except Exception as e:
            self.logger.error(f"Failed to get upcoming games for dynasty {dynasty_id}: {e}")
            return []

    def get_events_by_type(
        self,
        event_type: str,
        dynasty_id: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[Union[date, datetime]] = None,
        end_date: Optional[Union[date, datetime]] = None
    ) -> List[Event]:
        """
        Get events by type, optionally filtered by dynasty, status, and date range.

        Args:
            event_type: Type of event to retrieve
            dynasty_id: Optional dynasty filter
            status: Optional status filter
            start_date: Optional start date for range
            end_date: Optional end date for range

        Returns:
            List[Event]: List of events matching criteria
        """
        try:
            # Determine date range
            if start_date is None or end_date is None:
                dates_with_events = self.event_manager.get_dates_with_events()
                if not dates_with_events:
                    return []

                if start_date is None:
                    start_date = dates_with_events[0]
                if end_date is None:
                    end_date = dates_with_events[-1]

            start_date = self._convert_to_date(start_date)
            end_date = self._convert_to_date(end_date)

            events = self.get_events_between(start_date, end_date)

            # Filter events
            filtered_events = []
            for event in events:
                if event.get_event_type() != event_type:
                    continue

                if dynasty_id is not None and event.get_dynasty_id() != dynasty_id:
                    continue

                if status is not None and event.get_status() != status:
                    continue

                filtered_events.append(event)

            return filtered_events

        except Exception as e:
            self.logger.error(f"Failed to get events by type {event_type}: {e}")
            return []

    def mark_event_completed(self, event_id: str, result: Dict[str, Any]) -> bool:
        """
        Mark an event as completed with simulation results.

        Args:
            event_id: Unique ID of the event to mark as completed
            result: Dictionary containing simulation results

        Returns:
            bool: True if event was updated successfully, False otherwise
        """
        try:
            event = self.get_event_by_id(event_id)
            if not event:
                self.logger.warning(f"Event {event_id} not found for completion")
                return False

            # Set results and mark completed
            event.set_simulation_result(result)

            # Update in database
            success, error = self.event_manager.update_event(event)

            if not success:
                self.logger.error(f"Failed to update event {event_id}: {error}")
                return False

            self.logger.info(f"Marked event {event_id} as completed")
            return True

        except Exception as e:
            self.logger.error(f"Failed to mark event {event_id} as completed: {e}")
            return False

    def get_dynasty_summary(self, dynasty_id: str, season: Optional[int] = None) -> Dict[str, Any]:
        """
        Get a summary of dynasty events and status.

        Args:
            dynasty_id: Dynasty identifier
            season: Optional season filter

        Returns:
            Dict[str, Any]: Summary information about the dynasty
        """
        try:
            # Get all events for dynasty
            all_events = self.get_events_by_type(
                event_type="game_simulation",  # Start with games
                dynasty_id=dynasty_id
            )

            if season:
                all_events = [e for e in all_events if e.get_season() == season]

            # Calculate summary statistics
            total_games = len(all_events)
            completed_games = len([e for e in all_events if e.is_completed()])
            upcoming_games = len([e for e in all_events if e.is_scheduled()])

            # Get current standings from completed games
            wins = 0
            losses = 0
            ties = 0

            for event in all_events:
                if event.is_completed():
                    result = event.get_simulation_result()
                    if result and "winner_id" in result:
                        winner_id = result["winner_id"]
                        if winner_id is None:
                            ties += 1
                        else:
                            # Determine if this dynasty's team won
                            config = event.get_simulation_config()
                            home_team = config.get("home_team_id")
                            away_team = config.get("away_team_id")

                            # For now, assume first team in config is "our" team
                            # This could be enhanced with dynasty team tracking
                            our_team = away_team  # Simplified assumption

                            if winner_id == our_team:
                                wins += 1
                            else:
                                losses += 1

            return {
                "dynasty_id": dynasty_id,
                "season": season,
                "total_games": total_games,
                "completed_games": completed_games,
                "upcoming_games": upcoming_games,
                "record": {
                    "wins": wins,
                    "losses": losses,
                    "ties": ties
                },
                "next_game": self.get_upcoming_games(dynasty_id, limit=1)
            }

        except Exception as e:
            self.logger.error(f"Failed to get dynasty summary for {dynasty_id}: {e}")
            return {"dynasty_id": dynasty_id, "error": str(e)}

    def __repr__(self) -> str:
        """Detailed representation of the calendar manager."""
        total_events = self.event_manager.get_events_count()
        return (f"CalendarManager(start_date={self.start_date}, "
                f"current_date={self.current_date}, "
                f"events={total_events})")