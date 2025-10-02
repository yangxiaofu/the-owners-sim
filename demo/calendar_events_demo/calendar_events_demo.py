#!/usr/bin/env python3
"""
Calendar Events Demo

Demonstrates simulating a day using the calendar and events API:
1. Initialize calendar at a specific date
2. Populate events database with scheduled games
3. Use DaySimulationCoordinator to simulate one day
4. Display results: games played, scores, phase status

This demonstrates the integration of:
- CalendarComponent (date/time management)
- EventDatabaseAPI (event storage/retrieval)
- GameEvent (game simulation wrapper)
- DaySimulationCoordinator (orchestration)
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from datetime import datetime
from calendar.calendar_component import CalendarComponent
from calendar.simulation_executor import SimulationExecutor
from calendar.date_models import Date
from calendar.calendar_notifications import CalendarEventPublisher, CalendarNotification, NotificationType
from events import EventDatabaseAPI
from demo.calendar_events_demo.schedule_populator import SchedulePopulator


def print_header(title: str, width: int = 80):
    """Print a formatted header."""
    print(f"\n{'='*width}")
    print(f"{title.center(width)}")
    print(f"{'='*width}\n")


def print_section(title: str, width: int = 80):
    """Print a formatted section header."""
    print(f"\n{'─'*width}")
    print(f"🔹 {title}")
    print(f"{'─'*width}")


def display_game_results(games_played: list):
    """Display formatted game results."""
    print_section("Game Results")

    successful_games = [g for g in games_played if g.get('success', False)]

    if not successful_games:
        print("No games were successfully simulated.")
        return

    for i, game in enumerate(successful_games, 1):
        print(f"\nGame {i}: {game['matchup']}")
        print(f"  Away Team {game['away_team_id']}: {game['away_score']}")
        print(f"  Home Team {game['home_team_id']}: {game['home_score']}")

        if game.get('winner_name'):
            print(f"  🏆 Winner: {game['winner_name']}")

        print(f"  Total Plays: {game['total_plays']}")


def display_phase_info(phase_info: dict):
    """Display formatted phase information."""
    print_section("Season Phase Information")

    print(f"Current Phase: {phase_info.get('current_phase', 'Unknown')}")
    print(f"Season Year: {phase_info.get('season_year', 'Unknown')}")
    print(f"Days in Phase: {phase_info.get('days_in_current_phase', 0)}")
    print(f"Completed Games (Total): {phase_info.get('completed_games_total', 0)}")
    print(f"Completed Regular Season Games: {phase_info.get('completed_regular_season_games', 0)}")
    print(f"Regular Season Progress: {phase_info.get('regular_season_completion_percentage', 0):.1f}%")
    print(f"Next Transition: {phase_info.get('next_transition_trigger', 'Unknown')}")


def create_demo_listeners():
    """Create demo notification listeners to showcase the notification system."""
    notifications_received = []

    def calendar_event_listener(notification: CalendarNotification):
        """Listen to all calendar notifications and log them."""
        notifications_received.append(notification)

        if notification.notification_type == NotificationType.DATE_ADVANCED:
            data = notification.data
            days = data.get('days_advanced', 0)
            end_date = data.get('end_date')
            print(f"📅 Calendar Event: Advanced {days} days to {end_date}")

        elif notification.notification_type == NotificationType.PHASE_TRANSITION:
            data = notification.data
            from_phase = data.get('from_phase')
            to_phase = data.get('to_phase')
            print(f"🔄 Calendar Event: Phase transition {from_phase} → {to_phase}")

        elif notification.notification_type == NotificationType.MILESTONE_REACHED:
            data = notification.data
            milestone = data.get('milestone_name')
            milestone_date = data.get('milestone_date')
            print(f"🎯 Calendar Event: Milestone '{milestone}' reached on {milestone_date}")

    def season_manager_listener(notification: CalendarNotification):
        """Simulate how a Season Manager might react to calendar events."""
        if notification.notification_type == NotificationType.PHASE_TRANSITION:
            data = notification.data
            to_phase = data.get('to_phase')

            if to_phase == "playoffs":
                print("  🏆 Season Manager: Preparing playoff bracket...")
            elif to_phase == "offseason":
                print("  📋 Season Manager: Activating free agency...")
            elif to_phase == "regular_season":
                print("  🏈 Season Manager: Regular season started!")

    return calendar_event_listener, season_manager_listener, notifications_received


def main():
    """Main demo execution."""
    print_header("CALENDAR EVENTS DEMO WITH NOTIFICATIONS", 80)
    print("Demonstrating day-by-day simulation using calendar and events API")
    print("✨ NEW: Includes calendar notification system showcase")

    # ========================================
    # STEP 1: Setup
    # ========================================
    print_section("Step 1: Initialize Components")

    # Create calendar event publisher and listeners
    publisher = CalendarEventPublisher()
    calendar_listener, season_manager_listener, notifications_received = create_demo_listeners()

    # Subscribe listeners
    print("Setting up calendar notification listeners...")
    publisher.subscribe(calendar_listener)  # Listen to all events
    publisher.subscribe(season_manager_listener, [NotificationType.PHASE_TRANSITION])  # Phase transitions only
    print(f"✅ Notification subscribers configured: {publisher.get_subscriber_count()}")

    # Initialize calendar - start on Thursday before Week 1 (Sept 5, 2024)
    start_date = Date(2024, 9, 5)
    calendar = CalendarComponent(start_date=start_date, season_year=2024, publisher=publisher)
    print(f"✅ Calendar initialized at {calendar.get_current_date()}")
    print(f"   Current Phase: {calendar.get_current_phase().value}")
    print(f"📡 Calendar notifications ENABLED")

    # Initialize events database
    event_db = EventDatabaseAPI("data/database/calendar_demo_events.db")
    print(f"✅ Event Database initialized")

    # Initialize simulation executor
    executor = SimulationExecutor(calendar, event_db)
    print(f"✅ Simulation Executor initialized")

    # ========================================
    # STEP 2: Populate Schedule
    # ========================================
    print_section("Step 2: Populate Week 1 Schedule")

    populator = SchedulePopulator(event_db)

    # Clear any existing events
    print("Clearing existing events...")
    populator.clear_all_events()

    # Create Week 1 schedule
    games = populator.create_week_1_schedule(season=2024)

    # Show schedule summary
    summary = populator.get_schedule_summary()
    print(f"\n📊 Schedule Summary:")
    print(f"   Total Games: {summary['total_games']}")
    print(f"   Weeks with Games: {summary['weeks_with_games']}")
    for week, count in summary['games_by_week'].items():
        print(f"   - Week {week}: {count} games")

    # ========================================
    # STEP 3: Simulate Thursday Night
    # ========================================
    print_header("SIMULATING THURSDAY NIGHT FOOTBALL", 80)
    print(f"Current Date: {executor.get_current_date()}")
    print(f"Current Phase: {calendar.get_current_phase().value}")

    # Simulate Thursday (Sept 5)
    thursday_results = executor.simulate_day()

    # Display Thursday results
    display_game_results(thursday_results['games_played'])

    if thursday_results.get('phase_transitions'):
        print_section("Phase Transitions")
        for transition in thursday_results['phase_transitions']:
            print(f"✨ {transition['from_phase']} → {transition['to_phase']}")
            print(f"   Trigger: {transition['metadata'].get('trigger', 'Unknown')}")

    # ========================================
    # STEP 4: Advance to Sunday
    # ========================================
    print_section("Step 4: Advance Calendar to Sunday")

    print("Advancing 3 days to Sunday (Sept 8)...")
    print("📡 Watch for calendar notifications...")
    new_date = executor.advance_calendar(3)
    print(f"✅ Calendar advanced to {new_date}")
    print(f"   Current Phase: {calendar.get_current_phase().value}")

    # ========================================
    # STEP 5: Simulate Sunday
    # ========================================
    print_header("SIMULATING SUNDAY GAMES", 80)
    print(f"Current Date: {executor.get_current_date()}")

    # Simulate Sunday (Sept 8)
    sunday_results = executor.simulate_day()

    # Display Sunday results
    display_game_results(sunday_results['games_played'])

    if sunday_results.get('phase_transitions'):
        print_section("Phase Transitions")
        for transition in sunday_results['phase_transitions']:
            print(f"✨ {transition['from_phase']} → {transition['to_phase']}")
            print(f"   Trigger: {transition['metadata'].get('trigger', 'Unknown')}")

    # ========================================
    # STEP 6: Demonstrate Manual Milestone Notification
    # ========================================
    print_section("Step 6: Manual Milestone Notification")

    print("Demonstrating milestone notification...")
    print("📡 Publishing manual milestone notification...")
    if calendar._publisher:
        calendar._publisher.publish_milestone_reached(
            "Training Camp Starts", Date(2024, 7, 15), {"location": "Team Facilities"}
        )

    # ========================================
    # STEP 7: Summary
    # ========================================
    print_header("DEMO SUMMARY", 80)

    print(f"📅 Days Simulated: Thursday (Sept 5) and Sunday (Sept 8)")
    print(f"🏈 Thursday Games: {thursday_results['games_count']}")
    print(f"🏈 Sunday Games: {sunday_results['games_count']}")
    print(f"✅ Total Games Simulated: {thursday_results['games_count'] + sunday_results['games_count']}")

    # Display final phase info
    display_phase_info(executor.get_phase_info())

    # Calendar statistics
    print_section("Calendar Statistics")
    cal_stats = calendar.get_calendar_statistics()
    print(f"Total Days Advanced: {cal_stats['total_days_advanced']}")
    print(f"Advancement Count: {cal_stats['advancement_count']}")
    print(f"Days Since Creation: {cal_stats['days_since_creation']}")

    # Notification system summary
    print_section("Notification System Summary")
    print(f"📡 Total Calendar Notifications Received: {len(notifications_received)}")
    notification_types = {}
    for notification in notifications_received:
        notification_type = notification.notification_type.value
        notification_types[notification_type] = notification_types.get(notification_type, 0) + 1

    for notification_type, count in notification_types.items():
        print(f"   • {notification_type}: {count}")

    print(f"📊 Subscriber Status: {publisher.get_subscriber_count()}")

    print_header("DEMO COMPLETE", 80)
    print("✨ Successfully demonstrated calendar-driven day simulation with notifications!")
    print("\nKey Takeaways:")
    print("  • Calendar manages date/time state and phase tracking")
    print("  • EventDatabaseAPI stores scheduled games")
    print("  • SimulationExecutor orchestrates daily simulation")
    print("  • GameEvents execute actual game simulations")
    print("  • Phase transitions happen automatically based on game completions")
    print("  • 🆕 Calendar notifications enable loose coupling between systems")
    print("  • 🆕 Multiple systems can react to calendar changes automatically")
    print("  • 🆕 Observer pattern enables event-driven simulation architecture")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
