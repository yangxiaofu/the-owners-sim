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
        # Implementation will be added later
        pass

    def get_name(self) -> str:
        """
        Get the event name.

        Returns:
            str: The name of this event
        """
        # Implementation will be added later
        pass

    def get_id(self) -> str:
        """
        Get the unique event ID.

        Returns:
            str: The unique identifier for this event
        """
        # Implementation will be added later
        pass

    def get_metadata(self, key: str = None) -> Any:
        """
        Get event metadata.

        Args:
            key: Optional specific metadata key to retrieve

        Returns:
            Any: All metadata if key is None, specific value if key provided
        """
        # Implementation will be added later
        pass

    def set_metadata(self, key: str, value: Any) -> None:
        """
        Set event metadata.

        Args:
            key: Metadata key
            value: Metadata value
        """
        # Implementation will be added later
        pass

    def has_metadata(self, key: str) -> bool:
        """
        Check if event has specific metadata key.

        Args:
            key: Metadata key to check

        Returns:
            bool: True if key exists in metadata
        """
        # Implementation will be added later
        pass

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