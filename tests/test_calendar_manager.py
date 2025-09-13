#!/usr/bin/env python3
"""
Calendar Manager Tests

Test suite for the calendar-based daily simulation system.
Tests event scheduling, conflict detection, and daily simulation execution.
"""

import sys
from pathlib import Path
import unittest
from datetime import datetime, date, timedelta

# Add src to path for imports
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from simulation.calendar_manager import CalendarManager, ConflictResolution
from simulation.events import (
    BaseSimulationEvent, SimulationResult, EventType,
    GameSimulationEvent, TrainingEvent, ScoutingEvent, RestDayEvent
)


class MockEvent(BaseSimulationEvent):
    """Mock event for testing purposes"""
    
    def __init__(self, date: datetime, team_id: int, event_name: str = "Mock Event"):
        super().__init__(date, event_name, [team_id], 1.0)
        self.simulate_called = False
        self.should_fail = False
    
    def simulate(self) -> SimulationResult:
        self.simulate_called = True
        
        if self.should_fail:
            return SimulationResult(
                event_type=EventType.TRAINING,
                event_name=self.event_name,
                date=self.date,
                teams_affected=self.involved_teams,
                duration_hours=self.duration_hours,
                success=False,
                error_message="Mock failure"
            )
        
        return SimulationResult(
            event_type=EventType.TRAINING,
            event_name=self.event_name,
            date=self.date,
            teams_affected=self.involved_teams,
            duration_hours=self.duration_hours,
            success=True
        )
    
    def get_event_type(self) -> EventType:
        return EventType.TRAINING


class TestCalendarManager(unittest.TestCase):
    """Test cases for CalendarManager functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.start_date = date(2024, 9, 1)
        self.calendar = CalendarManager(self.start_date)
    
    def test_calendar_initialization(self):
        """Test calendar manager initialization"""
        self.assertEqual(self.calendar.current_date, self.start_date)
        self.assertEqual(self.calendar.start_date, self.start_date)
        self.assertEqual(len(self.calendar._events_by_date), 0)
        self.assertEqual(len(self.calendar._events_by_id), 0)
    
    def test_event_scheduling_success(self):
        """Test successful event scheduling"""
        event = MockEvent(datetime(2024, 9, 5), team_id=1, event_name="Test Event")
        
        success, message = self.calendar.schedule_event(event)
        
        self.assertTrue(success)
        self.assertIn("scheduled successfully", message.lower())
        self.assertEqual(len(self.calendar._events_by_date), 1)
        self.assertEqual(len(self.calendar._events_by_id), 1)
    
    def test_event_scheduling_conflict_rejection(self):
        """Test conflict detection and rejection"""
        date_conflict = datetime(2024, 9, 5)
        
        # Schedule first event
        event1 = MockEvent(date_conflict, team_id=1, event_name="Event 1")
        success1, _ = self.calendar.schedule_event(event1)
        self.assertTrue(success1)
        
        # Try to schedule conflicting event (same team, same day)
        event2 = MockEvent(date_conflict, team_id=1, event_name="Event 2")
        success2, message2 = self.calendar.schedule_event(event2)
        
        self.assertFalse(success2)
        self.assertIn("conflict", message2.lower())
        self.assertEqual(len(self.calendar._events_by_date[date_conflict.date()]), 1)
    
    def test_event_scheduling_no_conflict_different_teams(self):
        """Test that different teams can have events on same day"""
        same_date = datetime(2024, 9, 5)
        
        event1 = MockEvent(same_date, team_id=1, event_name="Team 1 Event")
        event2 = MockEvent(same_date, team_id=2, event_name="Team 2 Event")
        
        success1, _ = self.calendar.schedule_event(event1)
        success2, _ = self.calendar.schedule_event(event2)
        
        self.assertTrue(success1)
        self.assertTrue(success2)
        self.assertEqual(len(self.calendar._events_by_date[same_date.date()]), 2)
    
    def test_event_removal(self):
        """Test event removal from calendar"""
        event = MockEvent(datetime(2024, 9, 5), team_id=1)
        
        # Schedule event
        self.calendar.schedule_event(event)
        self.assertEqual(len(self.calendar._events_by_id), 1)
        
        # Remove event
        removed = self.calendar.remove_event(event.event_id)
        
        self.assertTrue(removed)
        self.assertEqual(len(self.calendar._events_by_id), 0)
        self.assertEqual(len(self.calendar._events_by_date), 0)
    
    def test_get_events_for_date(self):
        """Test retrieving events for specific date"""
        target_date = datetime(2024, 9, 5)
        other_date = datetime(2024, 9, 6)
        
        event1 = MockEvent(target_date, team_id=1)
        event2 = MockEvent(target_date, team_id=2)
        event3 = MockEvent(other_date, team_id=1)
        
        for event in [event1, event2, event3]:
            self.calendar.schedule_event(event)
        
        events_target = self.calendar.get_events_for_date(target_date.date())
        events_other = self.calendar.get_events_for_date(other_date.date())
        events_empty = self.calendar.get_events_for_date(date(2024, 9, 7))
        
        self.assertEqual(len(events_target), 2)
        self.assertEqual(len(events_other), 1)
        self.assertEqual(len(events_empty), 0)
    
    def test_team_availability(self):
        """Test team availability checking"""
        test_date = date(2024, 9, 5)
        
        # Initially team should be available
        self.assertTrue(self.calendar.is_team_available(1, test_date))
        
        # Schedule event for team 1
        event = MockEvent(datetime.combine(test_date, datetime.min.time()), team_id=1)
        self.calendar.schedule_event(event)
        
        # Team 1 should no longer be available, team 2 should still be available
        self.assertFalse(self.calendar.is_team_available(1, test_date))
        self.assertTrue(self.calendar.is_team_available(2, test_date))
    
    def test_simulate_day_success(self):
        """Test daily simulation with successful events"""
        test_date = date(2024, 9, 5)
        
        event1 = MockEvent(datetime.combine(test_date, datetime.min.time()), 
                          team_id=1, event_name="Event 1")
        event2 = MockEvent(datetime.combine(test_date, datetime.min.time()), 
                          team_id=2, event_name="Event 2")
        
        self.calendar.schedule_event(event1)
        self.calendar.schedule_event(event2)
        
        result = self.calendar.simulate_day(test_date)
        
        self.assertEqual(result.date, test_date)
        self.assertEqual(result.events_scheduled, 2)
        self.assertEqual(result.events_executed, 2)
        self.assertEqual(result.successful_events, 2)
        self.assertEqual(result.failed_events, 0)
        self.assertTrue(event1.simulate_called)
        self.assertTrue(event2.simulate_called)
    
    def test_simulate_day_with_failures(self):
        """Test daily simulation with some event failures"""
        test_date = date(2024, 9, 5)
        
        event1 = MockEvent(datetime.combine(test_date, datetime.min.time()), 
                          team_id=1, event_name="Success Event")
        event2 = MockEvent(datetime.combine(test_date, datetime.min.time()), 
                          team_id=2, event_name="Failure Event")
        event2.should_fail = True
        
        self.calendar.schedule_event(event1)
        self.calendar.schedule_event(event2)
        
        result = self.calendar.simulate_day(test_date)
        
        self.assertEqual(result.events_executed, 2)
        self.assertEqual(result.successful_events, 1)
        self.assertEqual(result.failed_events, 1)
        self.assertEqual(len(result.errors), 1)
        self.assertIn("Mock failure", result.errors[0])
    
    def test_advance_to_date(self):
        """Test advancing calendar through multiple days"""
        # Schedule events on multiple days
        for days_ahead in range(3):
            event_date = datetime(2024, 9, 5) + timedelta(days=days_ahead)
            event = MockEvent(event_date, team_id=1)
            self.calendar.schedule_event(event)
        
        # Advance 3 days
        results = self.calendar.advance_to_date(date(2024, 9, 7))
        
        self.assertEqual(len(results), 3)  # 3 days simulated
        self.assertEqual(self.calendar.current_date, date(2024, 9, 8))  # Advanced past target
        
        # Check that events were executed
        total_executed = sum(r.events_executed for r in results)
        self.assertEqual(total_executed, 3)
    
    def test_get_team_schedule(self):
        """Test getting schedule for specific team"""
        team_id = 1
        
        # Schedule events for team across multiple dates
        dates = [datetime(2024, 9, 5), datetime(2024, 9, 7), datetime(2024, 9, 10)]
        for event_date in dates:
            event = MockEvent(event_date, team_id)
            self.calendar.schedule_event(event)
        
        # Also schedule event for different team
        other_event = MockEvent(datetime(2024, 9, 6), team_id=2)
        self.calendar.schedule_event(other_event)
        
        team_schedule = self.calendar.get_team_schedule(team_id)
        
        self.assertEqual(len(team_schedule), 3)  # Only team 1's events
        for schedule_date in team_schedule:
            events = team_schedule[schedule_date]
            self.assertTrue(all(team_id in event.involved_teams for event in events))
    
    def test_get_available_dates(self):
        """Test finding available dates for teams"""
        team_id = 1
        
        # Schedule event on Sept 5
        busy_date = datetime(2024, 9, 5)
        event = MockEvent(busy_date, team_id)
        self.calendar.schedule_event(event)
        
        # Find available dates starting from Sept 4
        available_dates = self.calendar.get_available_dates(
            [team_id], 1, date(2024, 9, 4), 5
        )
        
        # Should include Sept 4, 6, 7, 8 but not Sept 5
        self.assertIn(date(2024, 9, 4), available_dates)
        self.assertNotIn(date(2024, 9, 5), available_dates)
        self.assertIn(date(2024, 9, 6), available_dates)
    
    def test_calendar_stats(self):
        """Test calendar statistics calculation"""
        # Schedule various events
        events = [
            MockEvent(datetime(2024, 9, 5), 1),
            MockEvent(datetime(2024, 9, 6), 2),
            TrainingEvent(datetime(2024, 9, 7), 1),
            RestDayEvent(datetime(2024, 9, 8), 2)
        ]
        
        for event in events:
            self.calendar.schedule_event(event)
        
        stats = self.calendar.get_calendar_stats()
        
        self.assertEqual(stats.total_events, 4)
        self.assertEqual(len(stats.teams_with_events), 2)
        self.assertEqual(stats.date_range, (date(2024, 9, 5), date(2024, 9, 8)))
        self.assertGreater(stats.total_scheduled_hours, 0)
    
    def test_clear_schedule(self):
        """Test clearing all scheduled events"""
        # Schedule some events
        for i in range(3):
            event = MockEvent(datetime(2024, 9, 5) + timedelta(days=i), team_id=1)
            self.calendar.schedule_event(event)
        
        self.assertEqual(len(self.calendar._events_by_id), 3)
        
        # Clear schedule
        cleared_count = self.calendar.clear_schedule()
        
        self.assertEqual(cleared_count, 3)
        self.assertEqual(len(self.calendar._events_by_id), 0)
        self.assertEqual(len(self.calendar._events_by_date), 0)


class TestEventIntegration(unittest.TestCase):
    """Test integration between calendar manager and actual event types"""
    
    def setUp(self):
        self.calendar = CalendarManager(date(2024, 9, 1))
    
    def test_placeholder_events(self):
        """Test that placeholder events work with calendar manager"""
        test_date = date(2024, 9, 5)
        
        events = [
            TrainingEvent(datetime.combine(test_date, datetime.min.time()), 1, "practice"),
            ScoutingEvent(datetime.combine(test_date, datetime.min.time()), 2, "prospects"),
            RestDayEvent(datetime.combine(test_date, datetime.min.time()), 3, "recovery")
        ]
        
        # Schedule all events
        for event in events:
            success, _ = self.calendar.schedule_event(event)
            self.assertTrue(success, f"Failed to schedule {event.event_name}")
        
        # Simulate the day
        result = self.calendar.simulate_day(test_date)
        
        self.assertEqual(result.events_executed, 3)
        self.assertEqual(result.successful_events, 3)
        self.assertEqual(result.failed_events, 0)
    
    def test_game_event_scheduling(self):
        """Test that game events can be scheduled and have correct properties"""
        game = GameSimulationEvent(
            date=datetime(2024, 9, 8),
            away_team_id=22,  # Detroit Lions
            home_team_id=12,  # Green Bay Packers  
            week=1
        )
        
        success, message = self.calendar.schedule_event(game)
        self.assertTrue(success)
        
        # Verify game properties
        self.assertEqual(game.get_event_type(), EventType.GAME)
        self.assertEqual(len(game.involved_teams), 2)
        self.assertIn(22, game.involved_teams)
        self.assertIn(12, game.involved_teams)
        self.assertEqual(game.duration_hours, 3.5)
    
    def test_event_coexistence_rules(self):
        """Test that different event types follow coexistence rules correctly"""
        test_date = datetime(2024, 9, 8)
        team_id = 22
        
        # Schedule a game for Detroit Lions
        game = GameSimulationEvent(test_date, away_team_id=12, home_team_id=team_id, week=1)
        success1, _ = self.calendar.schedule_event(game)
        self.assertTrue(success1)
        
        # Try to schedule training for same team (should conflict)
        training = TrainingEvent(test_date, team_id, "practice")
        success2, message2 = self.calendar.schedule_event(training)
        self.assertFalse(success2)
        self.assertIn("conflict", message2.lower())
        
        # Schedule training for different team (should succeed)
        other_training = TrainingEvent(test_date, 6, "practice")  # Chicago Bears
        success3, _ = self.calendar.schedule_event(other_training)
        self.assertTrue(success3)


def main():
    """Run all tests"""
    # Configure test discovery and execution
    unittest.main(verbosity=2, buffer=True)


if __name__ == '__main__':
    main()