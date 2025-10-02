"""
Calendar Notification Examples

Demonstrates how to use the calendar notification system with practical examples
for subscribing to calendar events and reacting to calendar state changes.
"""

from typing import Dict, Any
from datetime import datetime

from .calendar_notifications import (
    CalendarEventPublisher,
    CalendarNotification,
    NotificationType,
    DateAdvancedNotification,
    PhaseTransitionNotification,
    MilestoneReachedNotification
)
from .calendar_component import CalendarComponent
from .date_models import Date


class SeasonManagerListener:
    """
    Example listener that demonstrates how a Season Manager might
    react to calendar notifications.
    """

    def __init__(self):
        self.phase_transitions = []
        self.date_advancements = []

    def handle_calendar_notification(self, notification: CalendarNotification) -> None:
        """
        Main notification handler that routes to specific handlers.

        Args:
            notification: Calendar notification received
        """
        if notification.notification_type == NotificationType.DATE_ADVANCED:
            self._handle_date_advanced(notification)
        elif notification.notification_type == NotificationType.PHASE_TRANSITION:
            self._handle_phase_transition(notification)
        elif notification.notification_type == NotificationType.MILESTONE_REACHED:
            self._handle_milestone_reached(notification)

    def _handle_date_advanced(self, notification: CalendarNotification) -> None:
        """Handle date advancement notifications."""
        data = notification.data
        days_advanced = data.get('days_advanced', 0)
        end_date = data.get('end_date')

        print(f"SeasonManager: Calendar advanced {days_advanced} days to {end_date}")

        # Example logic: Check if we need to schedule new events
        if days_advanced >= 7:
            print("  → Weekly maintenance triggered")

        self.date_advancements.append(notification)

    def _handle_phase_transition(self, notification: CalendarNotification) -> None:
        """Handle season phase transition notifications."""
        data = notification.data
        from_phase = data.get('from_phase')
        to_phase = data.get('to_phase')

        print(f"SeasonManager: Season phase changed {from_phase} → {to_phase}")

        # Example logic: Prepare for new phase
        if to_phase == "playoffs":
            print("  → Initializing playoff bracket")
        elif to_phase == "offseason":
            print("  → Starting free agency period")

        self.phase_transitions.append(notification)

    def _handle_milestone_reached(self, notification: CalendarNotification) -> None:
        """Handle milestone reached notifications."""
        data = notification.data
        milestone_name = data.get('milestone_name')
        milestone_date = data.get('milestone_date')

        print(f"SeasonManager: Milestone reached '{milestone_name}' on {milestone_date}")

        # Example logic: Trigger milestone-specific events
        if milestone_name == "NFL Draft":
            print("  → Activating draft system")
        elif milestone_name == "Free Agency":
            print("  → Opening free agent market")


class UIUpdateListener:
    """
    Example listener that demonstrates how UI components might
    react to calendar notifications for display updates.
    """

    def __init__(self):
        self.display_date = None
        self.current_phase = None
        self.update_count = 0

    def update_display(self, notification: CalendarNotification) -> None:
        """
        Update UI displays based on calendar notifications.

        Args:
            notification: Calendar notification received
        """
        self.update_count += 1

        if notification.notification_type == NotificationType.DATE_ADVANCED:
            self.display_date = notification.data.get('end_date')
            print(f"UI: Updated date display to {self.display_date}")

        elif notification.notification_type == NotificationType.PHASE_TRANSITION:
            self.current_phase = notification.data.get('to_phase')
            print(f"UI: Updated phase display to {self.current_phase}")

        elif notification.notification_type == NotificationType.MILESTONE_REACHED:
            milestone = notification.data.get('milestone_name')
            print(f"UI: Showing milestone notification '{milestone}'")


class DatabasePersistenceListener:
    """
    Example listener that demonstrates how database systems might
    react to calendar notifications for persistence operations.
    """

    def __init__(self):
        self.saved_events = []

    def persist_calendar_event(self, notification: CalendarNotification) -> None:
        """
        Save calendar events to database for historical tracking.

        Args:
            notification: Calendar notification to persist
        """
        # Simulate database save
        event_record = {
            "timestamp": notification.timestamp.isoformat(),
            "type": notification.notification_type.value,
            "data": notification.data
        }

        self.saved_events.append(event_record)
        print(f"Database: Saved calendar event {notification.notification_type.value}")


def demo_notification_system():
    """
    Demonstrate the complete notification system with multiple subscribers.
    """
    print("=== Calendar Notification System Demo ===\n")

    # Create publisher and listeners
    publisher = CalendarEventPublisher()
    season_manager = SeasonManagerListener()
    ui_listener = UIUpdateListener()
    db_listener = DatabasePersistenceListener()

    # Subscribe listeners with different patterns
    print("Setting up subscriptions...")

    # Season manager wants all notifications
    publisher.subscribe(season_manager.handle_calendar_notification)

    # UI only wants date and phase changes
    publisher.subscribe(
        ui_listener.update_display,
        [NotificationType.DATE_ADVANCED, NotificationType.PHASE_TRANSITION]
    )

    # Database wants to persist everything
    publisher.subscribe(db_listener.persist_calendar_event)

    print(f"Subscribers configured: {publisher.get_subscriber_count()}\n")

    # Create calendar with publisher
    start_date = Date(2024, 9, 5)
    calendar = CalendarComponent(start_date, season_year=2024, publisher=publisher)

    print("=== Simulating Calendar Operations ===\n")

    # Demonstrate date advancement
    print("1. Advancing calendar by 7 days...")
    result = calendar.advance(7)
    print()

    # Demonstrate phase transition (simulate game completion)
    print("2. Simulating game completion that triggers phase transition...")
    from .season_phase_tracker import GameCompletionEvent

    game_event = GameCompletionEvent(
        game_id="game_001",
        home_team_id=1,
        away_team_id=2,
        completion_date=calendar.get_current_date(),
        completion_time=datetime.now(),
        week=1,
        game_type="regular",
        season_year=2024
    )

    transition = calendar.record_game_completion(game_event)
    if transition:
        print(f"Phase transition occurred!")
    else:
        print("No phase transition triggered")
    print()

    # Demonstrate milestone notification
    print("3. Simulating milestone reached...")
    if calendar._publisher:
        calendar._publisher.publish_milestone_reached(
            "NFL Draft", Date(2025, 4, 24), {"round": 1, "location": "Detroit"}
        )
    print()

    # Show final status
    print("=== Final Status ===")
    print(f"UI updates: {ui_listener.update_count}")
    print(f"Season manager phase transitions: {len(season_manager.phase_transitions)}")
    print(f"Season manager date advancements: {len(season_manager.date_advancements)}")
    print(f"Database events saved: {len(db_listener.saved_events)}")

    return {
        "publisher": publisher,
        "season_manager": season_manager,
        "ui_listener": ui_listener,
        "db_listener": db_listener,
        "calendar": calendar
    }


def demo_typed_subscriptions():
    """
    Demonstrate type-specific subscriptions for efficiency.
    """
    print("\n=== Typed Subscription Demo ===\n")

    publisher = CalendarEventPublisher()

    # Create specialized listeners
    def phase_only_listener(notification: CalendarNotification):
        print(f"Phase Listener: {notification.notification_type.value}")

    def date_only_listener(notification: CalendarNotification):
        print(f"Date Listener: {notification.notification_type.value}")

    def milestone_only_listener(notification: CalendarNotification):
        print(f"Milestone Listener: {notification.notification_type.value}")

    # Subscribe to specific types
    publisher.subscribe(phase_only_listener, [NotificationType.PHASE_TRANSITION])
    publisher.subscribe(date_only_listener, [NotificationType.DATE_ADVANCED])
    publisher.subscribe(milestone_only_listener, [NotificationType.MILESTONE_REACHED])

    print(f"Subscribers: {publisher.get_subscriber_count()}\n")

    # Test with different notification types
    from .date_models import DateAdvanceResult

    test_result = DateAdvanceResult(
        start_date=Date(2024, 9, 5),
        end_date=Date(2024, 9, 12),
        days_advanced=7
    )

    print("Publishing date advanced notification...")
    publisher.publish_date_advanced(test_result)
    print()

    print("Publishing milestone notification...")
    publisher.publish_milestone_reached("Test Milestone", Date(2024, 9, 15))
    print()

    # Note: Phase transitions require PhaseTransition object from actual calendar


if __name__ == "__main__":
    # Run the demos
    demo_notification_system()
    demo_typed_subscriptions()