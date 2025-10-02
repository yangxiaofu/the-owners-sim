"""
Calendar Notifications

Notification system for calendar state changes. Provides a publisher-subscriber
pattern for other systems to be notified when calendar operations occur.

This is NOT the same as the BaseEvent system - these are notifications ABOUT
calendar changes, not simulation events to be executed.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List, Callable, Optional
from enum import Enum

from .date_models import Date, DateAdvanceResult
from .season_phase_tracker import PhaseTransition, SeasonPhase


class NotificationType(Enum):
    """Types of calendar notifications that can be published."""
    DATE_ADVANCED = "date_advanced"
    PHASE_TRANSITION = "phase_transition"
    MILESTONE_REACHED = "milestone_reached"
    SEASON_STARTED = "season_started"
    SEASON_ENDED = "season_ended"


@dataclass(frozen=True)
class CalendarNotification:
    """
    Notification about a calendar state change.

    This is a simple data structure containing information about what
    changed in the calendar system. Subscribers receive these notifications
    to stay informed about calendar state changes.
    """
    notification_type: NotificationType
    timestamp: datetime
    data: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate notification data."""
        if not isinstance(self.timestamp, datetime):
            raise ValueError("Timestamp must be a datetime object")
        if not isinstance(self.data, dict):
            raise ValueError("Data must be a dictionary")


@dataclass(frozen=True)
class DateAdvancedNotification(CalendarNotification):
    """Specific notification for date advancement."""

    @classmethod
    def from_advance_result(cls, result: DateAdvanceResult) -> "DateAdvancedNotification":
        """Create notification from DateAdvanceResult."""
        return cls(
            notification_type=NotificationType.DATE_ADVANCED,
            timestamp=datetime.now(),
            data={
                "start_date": str(result.start_date),
                "end_date": str(result.end_date),
                "days_advanced": result.days_advanced,
                "advancement_id": getattr(result, 'advancement_id', None)
            }
        )


@dataclass(frozen=True)
class PhaseTransitionNotification(CalendarNotification):
    """Specific notification for season phase transitions."""

    @classmethod
    def from_phase_transition(cls, transition: PhaseTransition) -> "PhaseTransitionNotification":
        """Create notification from PhaseTransition."""
        return cls(
            notification_type=NotificationType.PHASE_TRANSITION,
            timestamp=datetime.now(),
            data={
                "from_phase": transition.from_phase.value if transition.from_phase else None,
                "to_phase": transition.to_phase.value,
                "trigger_date": str(transition.trigger_date),
                "transition_type": transition.transition_type.value,
                "metadata": transition.metadata
            }
        )


@dataclass(frozen=True)
class MilestoneReachedNotification(CalendarNotification):
    """Specific notification for season milestones."""

    @classmethod
    def create(cls, milestone_name: str, milestone_date: Date,
               metadata: Optional[Dict[str, Any]] = None) -> "MilestoneReachedNotification":
        """Create milestone notification."""
        return cls(
            notification_type=NotificationType.MILESTONE_REACHED,
            timestamp=datetime.now(),
            data={
                "milestone_name": milestone_name,
                "milestone_date": str(milestone_date),
                "metadata": metadata or {}
            }
        )


# Type alias for notification listeners
NotificationListener = Callable[[CalendarNotification], None]


class CalendarEventPublisher:
    """
    Publisher for calendar notifications using observer pattern.

    Manages subscribers and publishes notifications when calendar
    state changes occur. This enables loose coupling between the
    calendar system and other components that need to react to
    calendar changes.
    """

    def __init__(self):
        """Initialize publisher with empty subscriber list."""
        self._subscribers: List[NotificationListener] = []
        self._type_subscribers: Dict[NotificationType, List[NotificationListener]] = {
            notification_type: [] for notification_type in NotificationType
        }

    def subscribe(self, listener: NotificationListener,
                  notification_types: Optional[List[NotificationType]] = None) -> None:
        """
        Subscribe to calendar notifications.

        Args:
            listener: Callable that receives CalendarNotification objects
            notification_types: Optional list of specific types to listen for.
                               If None, listener receives all notifications.
        """
        if not callable(listener):
            raise ValueError("Listener must be callable")

        if notification_types is None:
            # Subscribe to all notifications
            if listener not in self._subscribers:
                self._subscribers.append(listener)
        else:
            # Subscribe to specific notification types
            for notification_type in notification_types:
                if notification_type not in self._type_subscribers:
                    self._type_subscribers[notification_type] = []
                if listener not in self._type_subscribers[notification_type]:
                    self._type_subscribers[notification_type].append(listener)

    def unsubscribe(self, listener: NotificationListener) -> None:
        """
        Unsubscribe from all calendar notifications.

        Args:
            listener: The listener to remove from all subscriptions
        """
        # Remove from general subscribers
        if listener in self._subscribers:
            self._subscribers.remove(listener)

        # Remove from type-specific subscribers
        for type_list in self._type_subscribers.values():
            if listener in type_list:
                type_list.remove(listener)

    def publish(self, notification: CalendarNotification) -> None:
        """
        Publish a calendar notification to all relevant subscribers.

        Args:
            notification: The notification to publish
        """
        # Notify general subscribers (those subscribed to all types)
        for listener in self._subscribers:
            try:
                listener(notification)
            except Exception as e:
                # Log error but don't let one bad listener break others
                print(f"Warning: Calendar notification listener failed: {e}")

        # Notify type-specific subscribers
        type_subscribers = self._type_subscribers.get(notification.notification_type, [])
        for listener in type_subscribers:
            try:
                listener(notification)
            except Exception as e:
                # Log error but don't let one bad listener break others
                print(f"Warning: Calendar notification listener failed: {e}")

    def publish_date_advanced(self, result: DateAdvanceResult) -> None:
        """
        Convenience method to publish date advancement notification.

        Args:
            result: DateAdvanceResult from calendar advancement
        """
        notification = DateAdvancedNotification.from_advance_result(result)
        self.publish(notification)

    def publish_phase_transition(self, transition: PhaseTransition) -> None:
        """
        Convenience method to publish phase transition notification.

        Args:
            transition: PhaseTransition from season phase tracker
        """
        notification = PhaseTransitionNotification.from_phase_transition(transition)
        self.publish(notification)

    def publish_milestone_reached(self, milestone_name: str, milestone_date: Date,
                                  metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Convenience method to publish milestone reached notification.

        Args:
            milestone_name: Name of the milestone (e.g., "NFL Draft", "Free Agency")
            milestone_date: Date the milestone occurred
            metadata: Optional additional data about the milestone
        """
        notification = MilestoneReachedNotification.create(
            milestone_name, milestone_date, metadata
        )
        self.publish(notification)

    def get_subscriber_count(self) -> Dict[str, int]:
        """
        Get current subscriber counts for monitoring.

        Returns:
            Dictionary with subscriber counts by type
        """
        return {
            "all_types": len(self._subscribers),
            **{
                f"type_{notification_type.value}": len(subscribers)
                for notification_type, subscribers in self._type_subscribers.items()
            }
        }