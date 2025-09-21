"""
Event

Base event class for the calendar system.
Simple data container for events with date, name, and metadata.
"""

from datetime import datetime, date
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass, field
import uuid


@dataclass
class Event:
    """
    Base event class for calendar system.

    Simple data container that holds event information without complex logic.
    All events have a date, name, unique ID, and optional metadata.
    """

    name: str
    event_date: Union[date, datetime]
    event_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Initialize event after creation."""
        # Generate unique ID if not provided
        if self.event_id is None:
            self.event_id = str(uuid.uuid4())

        # Convert datetime to date if needed for consistency
        if isinstance(self.event_date, datetime):
            self.event_date = self.event_date.date()

    def get_date(self) -> date:
        """
        Get the event date.

        Returns:
            date: The date this event is scheduled for
        """
        return self.event_date

    def get_name(self) -> str:
        """
        Get the event name.

        Returns:
            str: The name of this event
        """
        return self.name

    def get_id(self) -> str:
        """
        Get the unique event ID.

        Returns:
            str: The unique identifier for this event
        """
        return self.event_id

    def get_metadata(self, key: str = None) -> Any:
        """
        Get event metadata.

        Args:
            key: Optional specific metadata key to retrieve

        Returns:
            Any: All metadata if key is None, specific value if key provided
        """
        if key is None:
            return self.metadata.copy()
        return self.metadata.get(key)

    def set_metadata(self, key: str, value: Any) -> None:
        """
        Set event metadata.

        Args:
            key: Metadata key
            value: Metadata value
        """
        self.metadata[key] = value

    def has_metadata(self, key: str) -> bool:
        """
        Check if event has specific metadata key.

        Args:
            key: Metadata key to check

        Returns:
            bool: True if key exists in metadata
        """
        return key in self.metadata

    # Simulation-specific convenience methods
    def get_event_type(self) -> Optional[str]:
        """
        Get the event type for simulation categorization.

        Returns:
            Optional[str]: The event type (e.g., 'game_simulation', 'draft_simulation')
        """
        return self.metadata.get("event_type")

    def set_event_type(self, event_type: str) -> None:
        """
        Set the event type for simulation categorization.

        Args:
            event_type: The type of simulation event
        """
        self.metadata["event_type"] = event_type

    def get_dynasty_id(self) -> Optional[str]:
        """
        Get the dynasty ID this event belongs to.

        Returns:
            Optional[str]: The dynasty identifier
        """
        return self.metadata.get("dynasty_id")

    def set_dynasty_id(self, dynasty_id: str) -> None:
        """
        Set the dynasty ID this event belongs to.

        Args:
            dynasty_id: The dynasty identifier
        """
        self.metadata["dynasty_id"] = dynasty_id

    def get_simulation_config(self) -> Dict[str, Any]:
        """
        Get the simulation configuration for this event.

        Returns:
            Dict[str, Any]: Configuration dictionary for simulation execution
        """
        return self.metadata.get("simulation_config", {})

    def set_simulation_config(self, config: Dict[str, Any]) -> None:
        """
        Set the simulation configuration for this event.

        Args:
            config: Configuration dictionary for simulation execution
        """
        self.metadata["simulation_config"] = config

    def update_simulation_config(self, **kwargs) -> None:
        """
        Update specific fields in the simulation configuration.

        Args:
            **kwargs: Key-value pairs to update in the simulation config
        """
        config = self.get_simulation_config()
        config.update(kwargs)
        self.set_simulation_config(config)

    def get_status(self) -> str:
        """
        Get the current status of this event.

        Returns:
            str: Event status ('scheduled', 'in_progress', 'completed', 'cancelled')
        """
        return self.metadata.get("status", "scheduled")

    def set_status(self, status: str) -> None:
        """
        Set the current status of this event.

        Args:
            status: New status ('scheduled', 'in_progress', 'completed', 'cancelled')
        """
        self.metadata["status"] = status

    def is_completed(self) -> bool:
        """
        Check if this event has been completed.

        Returns:
            bool: True if the event is completed
        """
        return self.get_status() == "completed"

    def is_scheduled(self) -> bool:
        """
        Check if this event is scheduled (not yet executed).

        Returns:
            bool: True if the event is scheduled
        """
        return self.get_status() == "scheduled"

    def get_simulation_result(self) -> Optional[Dict[str, Any]]:
        """
        Get the results from simulation execution.

        Returns:
            Optional[Dict[str, Any]]: Simulation results, or None if not completed
        """
        return self.metadata.get("simulation_result")

    def set_simulation_result(self, result: Dict[str, Any]) -> None:
        """
        Set the results from simulation execution and mark as completed.

        Args:
            result: Dictionary containing simulation results
        """
        self.metadata["simulation_result"] = result
        self.set_status("completed")

    def get_season(self) -> Optional[int]:
        """
        Get the season this event belongs to.

        Returns:
            Optional[int]: Season year
        """
        return self.metadata.get("season")

    def set_season(self, season: int) -> None:
        """
        Set the season this event belongs to.

        Args:
            season: Season year
        """
        self.metadata["season"] = season

    def get_week(self) -> Optional[int]:
        """
        Get the week this event occurs in (for game events).

        Returns:
            Optional[int]: Week number
        """
        return self.metadata.get("week")

    def set_week(self, week: int) -> None:
        """
        Set the week this event occurs in.

        Args:
            week: Week number
        """
        self.metadata["week"] = week

    def __str__(self) -> str:
        """String representation of the event."""
        return f"Event('{self.name}' on {self.event_date})"

    def __repr__(self) -> str:
        """Detailed representation of the event."""
        return f"Event(name='{self.name}', date={self.event_date}, id={self.event_id})"

    def __eq__(self, other) -> bool:
        """Event equality based on event ID."""
        if not isinstance(other, Event):
            return False
        return self.event_id == other.event_id

    def __hash__(self) -> int:
        """Hash based on event ID for use in sets/dicts."""
        return hash(self.event_id)