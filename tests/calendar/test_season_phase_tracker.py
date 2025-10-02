"""
Test suite for season phase tracking functionality.

Tests the event-driven season phase management system including
phase transitions, game completion tracking, and milestone calculations.
"""

import pytest
from datetime import datetime
from typing import List

from src.calendar.date_models import Date
from src.calendar.season_phase_tracker import (
    SeasonPhaseTracker, SeasonPhase, TransitionType,
    GameCompletionEvent, PhaseTransition
)
from src.calendar.phase_transition_triggers import (
    TransitionTriggerManager,
    PreseasonToRegularSeasonTrigger,
    RegularSeasonToPlayoffsTrigger,
    PlayoffsToOffseasonTrigger,
    OffseasonToPreseasonTrigger
)
from src.calendar.season_milestones import (
    SeasonMilestoneCalculator, MilestoneType, create_season_milestone_calculator
)
from src.calendar.calendar_component import CalendarComponent
from src.calendar.calendar_exceptions import CalendarStateException


class TestSeasonPhaseTracker:
    """Test the core season phase tracking functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.start_date = Date(2024, 8, 1)  # Start in offseason
        self.season_year = 2024
        self.tracker = SeasonPhaseTracker(self.start_date, self.season_year)

    def test_initialization(self):
        """Test tracker initialization."""
        assert self.tracker.get_current_phase() == SeasonPhase.OFFSEASON
        assert len(self.tracker.get_transition_history()) == 0

        phase_info = self.tracker.get_phase_info()
        assert phase_info["current_phase"] == "offseason"
        assert phase_info["season_year"] == 2024
        assert phase_info["completed_games_total"] == 0

    def test_preseason_game_completion(self):
        """Test recording preseason game completion."""
        game_event = GameCompletionEvent(
            game_id="preseason_1",
            home_team_id=1,
            away_team_id=2,
            completion_date=Date(2024, 8, 10),
            completion_time=datetime(2024, 8, 10, 20, 0),
            week=1,
            game_type="preseason",
            season_year=2024
        )

        # This should trigger transition to preseason
        transition = self.tracker.record_game_completion(game_event)

        assert transition is not None
        assert transition.transition_type == TransitionType.SEASON_START
        assert transition.from_phase == SeasonPhase.OFFSEASON
        assert transition.to_phase == SeasonPhase.PRESEASON
        assert self.tracker.get_current_phase() == SeasonPhase.PRESEASON

    def test_regular_season_start_transition(self):
        """Test transition from preseason to regular season."""
        # First, transition to preseason
        preseason_game = GameCompletionEvent(
            game_id="preseason_1",
            home_team_id=1,
            away_team_id=2,
            completion_date=Date(2024, 8, 10),
            completion_time=datetime(2024, 8, 10, 20, 0),
            week=1,
            game_type="preseason",
            season_year=2024
        )
        self.tracker.record_game_completion(preseason_game)

        # Now record first regular season game
        regular_game = GameCompletionEvent(
            game_id="regular_1",
            home_team_id=3,
            away_team_id=4,
            completion_date=Date(2024, 9, 5),
            completion_time=datetime(2024, 9, 5, 13, 0),
            week=1,
            game_type="regular",
            season_year=2024
        )

        transition = self.tracker.record_game_completion(regular_game)

        assert transition is not None
        assert transition.transition_type == TransitionType.REGULAR_SEASON_START
        assert transition.from_phase == SeasonPhase.PRESEASON
        assert transition.to_phase == SeasonPhase.REGULAR_SEASON
        assert self.tracker.get_current_phase() == SeasonPhase.REGULAR_SEASON

    def test_regular_season_completion_transition(self):
        """Test transition from regular season to playoffs."""
        # Set up in regular season
        self.tracker.force_phase_transition(
            SeasonPhase.REGULAR_SEASON,
            Date(2024, 9, 5)
        )

        # Simulate completing all 272 regular season games
        completed_games = []
        for i in range(272):
            game_event = GameCompletionEvent(
                game_id=f"regular_{i+1}",
                home_team_id=(i % 32) + 1,
                away_team_id=((i + 1) % 32) + 1,
                completion_date=Date(2024, 12, 31),
                completion_time=datetime(2024, 12, 31, 16, 0),
                week=18,
                game_type="regular",
                season_year=2024
            )
            completed_games.append(game_event)

        # Record all but the last game
        for game in completed_games[:-1]:
            transition = self.tracker.record_game_completion(game)
            assert transition is None  # No transition yet

        # Record the final game - should trigger playoff transition
        final_game = completed_games[-1]
        transition = self.tracker.record_game_completion(final_game)

        assert transition is not None
        assert transition.transition_type == TransitionType.PLAYOFFS_START
        assert transition.from_phase == SeasonPhase.REGULAR_SEASON
        assert transition.to_phase == SeasonPhase.PLAYOFFS
        assert self.tracker.get_current_phase() == SeasonPhase.PLAYOFFS

    def test_super_bowl_completion_transition(self):
        """Test transition from playoffs to offseason."""
        # Set up in playoffs
        self.tracker.force_phase_transition(
            SeasonPhase.PLAYOFFS,
            Date(2025, 1, 15)
        )

        # Record Super Bowl completion
        super_bowl = GameCompletionEvent(
            game_id="super_bowl_2025",
            home_team_id=1,
            away_team_id=2,
            completion_date=Date(2025, 2, 11),
            completion_time=datetime(2025, 2, 11, 18, 30),
            week=22,
            game_type="super_bowl",
            season_year=2024
        )

        transition = self.tracker.record_game_completion(super_bowl)

        assert transition is not None
        assert transition.transition_type == TransitionType.OFFSEASON_START
        assert transition.from_phase == SeasonPhase.PLAYOFFS
        assert transition.to_phase == SeasonPhase.OFFSEASON
        assert self.tracker.get_current_phase() == SeasonPhase.OFFSEASON

    def test_invalid_game_event_validation(self):
        """Test validation of game events."""
        # Invalid game type
        with pytest.raises(CalendarStateException):
            invalid_game = GameCompletionEvent(
                game_id="invalid_1",
                home_team_id=1,
                away_team_id=2,
                completion_date=Date(2024, 8, 10),
                completion_time=datetime(2024, 8, 10, 20, 0),
                week=1,
                game_type="invalid_type",
                season_year=2024
            )
            self.tracker.record_game_completion(invalid_game)

        # Wrong season year
        with pytest.raises(CalendarStateException):
            wrong_season = GameCompletionEvent(
                game_id="wrong_season",
                home_team_id=1,
                away_team_id=2,
                completion_date=Date(2024, 8, 10),
                completion_time=datetime(2024, 8, 10, 20, 0),
                week=1,
                game_type="preseason",
                season_year=2023  # Wrong year
            )
            self.tracker.record_game_completion(wrong_season)

    def test_phase_transition_pending(self):
        """Test detection of pending phase transitions."""
        # Set up in regular season
        self.tracker.force_phase_transition(
            SeasonPhase.REGULAR_SEASON,
            Date(2024, 9, 5)
        )

        # Add 95% of regular season games (259 out of 272)
        for i in range(259):
            game_event = GameCompletionEvent(
                game_id=f"regular_{i+1}",
                home_team_id=(i % 32) + 1,
                away_team_id=((i + 1) % 32) + 1,
                completion_date=Date(2024, 12, 28),
                completion_time=datetime(2024, 12, 28, 16, 0),
                week=17,
                game_type="regular",
                season_year=2024
            )
            self.tracker.record_game_completion(game_event)

        assert self.tracker.is_phase_transition_pending() == True

    def test_transition_listeners(self):
        """Test phase transition event listeners."""
        transitions_received = []

        def transition_listener(transition: PhaseTransition):
            transitions_received.append(transition)

        self.tracker.add_transition_listener(transition_listener)

        # Trigger a transition
        preseason_game = GameCompletionEvent(
            game_id="preseason_1",
            home_team_id=1,
            away_team_id=2,
            completion_date=Date(2024, 8, 10),
            completion_time=datetime(2024, 8, 10, 20, 0),
            week=1,
            game_type="preseason",
            season_year=2024
        )

        self.tracker.record_game_completion(preseason_game)

        assert len(transitions_received) == 1
        assert transitions_received[0].to_phase == SeasonPhase.PRESEASON

        # Remove listener
        self.tracker.remove_transition_listener(transition_listener)

        # Force another transition
        self.tracker.force_phase_transition(
            SeasonPhase.REGULAR_SEASON,
            Date(2024, 9, 5)
        )

        # Should still be only 1 transition (listener was removed)
        assert len(transitions_received) == 1


class TestPhaseTransitionTriggers:
    """Test the phase transition trigger system."""

    def setup_method(self):
        """Set up test fixtures."""
        self.trigger_manager = TransitionTriggerManager()

    def test_trigger_manager_initialization(self):
        """Test trigger manager contains all standard triggers."""
        # Should have 4 standard NFL transition triggers
        assert len(self.trigger_manager.triggers) == 4

        # Check specific trigger types exist
        trigger_types = [type(t).__name__ for t in self.trigger_manager.triggers]
        expected_types = [
            "OffseasonToPreseasonTrigger",
            "PreseasonToRegularSeasonTrigger",
            "RegularSeasonToPlayoffsTrigger",
            "PlayoffsToOffseasonTrigger"
        ]

        for expected_type in expected_types:
            assert expected_type in trigger_types

    def test_preseason_trigger(self):
        """Test preseason to regular season trigger."""
        trigger = PreseasonToRegularSeasonTrigger()

        # No regular season games yet
        completed_games = []
        games_by_type = {"regular": [], "preseason": []}
        current_state = {}

        result = trigger.check_trigger(completed_games, games_by_type, current_state)
        assert result is None

        # Add Week 1 regular season game
        regular_game = GameCompletionEvent(
            game_id="regular_week1_1",
            home_team_id=1,
            away_team_id=2,
            completion_date=Date(2024, 9, 5),
            completion_time=datetime(2024, 9, 5, 13, 0),
            week=1,
            game_type="regular",
            season_year=2024
        )

        games_by_type["regular"] = [regular_game]

        result = trigger.check_trigger(completed_games, games_by_type, current_state)
        assert result is not None
        assert result.to_phase == SeasonPhase.REGULAR_SEASON

    def test_playoffs_trigger(self):
        """Test regular season to playoffs trigger."""
        trigger = RegularSeasonToPlayoffsTrigger()

        # Create exactly 272 regular season games
        regular_games = []
        for i in range(272):
            game = GameCompletionEvent(
                game_id=f"regular_{i+1}",
                home_team_id=(i % 32) + 1,
                away_team_id=((i + 1) % 32) + 1,
                completion_date=Date(2024, 12, 31),
                completion_time=datetime(2024, 12, 31, 16, 0),
                week=18,
                game_type="regular",
                season_year=2024
            )
            regular_games.append(game)

        games_by_type = {"regular": regular_games}
        current_state = {}

        result = trigger.check_trigger(regular_games, games_by_type, current_state)
        assert result is not None
        assert result.to_phase == SeasonPhase.PLAYOFFS
        assert result.metadata["total_regular_games"] == 272

    def test_offseason_trigger(self):
        """Test playoffs to offseason trigger."""
        trigger = PlayoffsToOffseasonTrigger()

        # Create Super Bowl game
        super_bowl = GameCompletionEvent(
            game_id="super_bowl_2025",
            home_team_id=1,
            away_team_id=2,
            completion_date=Date(2025, 2, 11),
            completion_time=datetime(2025, 2, 11, 18, 30),
            week=22,
            game_type="super_bowl",
            season_year=2024
        )

        games_by_type = {"super_bowl": [super_bowl]}
        current_state = {}

        result = trigger.check_trigger([super_bowl], games_by_type, current_state)
        assert result is not None
        assert result.to_phase == SeasonPhase.OFFSEASON
        assert result.metadata["trigger"] == "super_bowl_complete"

    def test_next_transition_info(self):
        """Test getting next transition information."""
        # Test for each phase
        offseason_info = self.trigger_manager.get_next_transition_info(SeasonPhase.OFFSEASON)
        assert offseason_info["next_transition"] == "preseason"

        preseason_info = self.trigger_manager.get_next_transition_info(SeasonPhase.PRESEASON)
        assert preseason_info["next_transition"] == "regular_season"

        regular_info = self.trigger_manager.get_next_transition_info(SeasonPhase.REGULAR_SEASON)
        assert regular_info["next_transition"] == "playoffs"

        playoff_info = self.trigger_manager.get_next_transition_info(SeasonPhase.PLAYOFFS)
        assert playoff_info["next_transition"] == "offseason"


class TestSeasonMilestones:
    """Test the season milestone calculation system."""

    def setup_method(self):
        """Set up test fixtures."""
        self.calculator = create_season_milestone_calculator()

    def test_milestone_calculator_initialization(self):
        """Test milestone calculator has all standard milestones."""
        definitions = self.calculator.get_milestone_definitions()

        expected_types = [
            MilestoneType.DRAFT,
            MilestoneType.FREE_AGENCY,
            MilestoneType.TRAINING_CAMP,
            MilestoneType.SCHEDULE_RELEASE,
            MilestoneType.TRADE_DEADLINE,
            MilestoneType.ROSTER_CUTS
        ]

        for milestone_type in expected_types:
            assert milestone_type in definitions

    def test_milestone_calculation_with_super_bowl_date(self):
        """Test milestone calculation based on Super Bowl completion."""
        super_bowl_date = Date(2025, 2, 11)  # Sunday, Feb 11, 2025
        season_year = 2024

        milestones = self.calculator.calculate_milestones_for_season(
            season_year=season_year,
            super_bowl_date=super_bowl_date
        )

        assert len(milestones) > 0

        # Find specific milestones
        draft_milestone = next((m for m in milestones if m.milestone_type == MilestoneType.DRAFT), None)
        assert draft_milestone is not None
        # Draft should be approximately 11 weeks after Super Bowl
        days_to_draft = super_bowl_date.days_until(draft_milestone.date)
        assert 70 <= days_to_draft <= 84  # 10-12 weeks range

        free_agency_milestone = next((m for m in milestones if m.milestone_type == MilestoneType.FREE_AGENCY), None)
        assert free_agency_milestone is not None
        # Free agency should be about 2 weeks after Super Bowl
        days_to_fa = super_bowl_date.days_until(free_agency_milestone.date)
        assert 10 <= days_to_fa <= 20  # Around 2 weeks

    def test_milestone_calculation_without_base_date(self):
        """Test milestone calculation with estimated dates."""
        season_year = 2024

        milestones = self.calculator.calculate_milestones_for_season(
            season_year=season_year
        )

        assert len(milestones) > 0

        # All milestones should have estimated dates in 2025
        for milestone in milestones:
            assert milestone.base_event == "estimated"
            # Most milestones should be in the following year
            if milestone.milestone_type in [MilestoneType.DRAFT, MilestoneType.FREE_AGENCY]:
                assert milestone.date.year == 2025

    def test_next_milestone_detection(self):
        """Test finding the next upcoming milestone."""
        current_date = Date(2025, 3, 1)  # Early March

        milestones = self.calculator.calculate_milestones_for_season(
            season_year=2024,
            super_bowl_date=Date(2025, 2, 11)
        )

        next_milestone = self.calculator.get_next_milestone(current_date, milestones)
        assert next_milestone is not None
        assert next_milestone.date > current_date

    def test_recent_milestones_detection(self):
        """Test finding recently passed milestones."""
        current_date = Date(2025, 3, 15)  # Mid-March

        milestones = self.calculator.calculate_milestones_for_season(
            season_year=2024,
            super_bowl_date=Date(2025, 2, 11)
        )

        recent_milestones = self.calculator.get_recent_milestones(
            current_date, milestones, days_back=30
        )

        # Should find milestones that occurred in the last 30 days
        for milestone in recent_milestones:
            days_ago = milestone.date.days_until(current_date)
            assert 0 <= days_ago <= 30


class TestCalendarComponentIntegration:
    """Test integration of calendar component with season phase tracking."""

    def setup_method(self):
        """Set up test fixtures."""
        self.start_date = Date(2024, 8, 1)
        self.calendar = CalendarComponent(self.start_date, season_year=2024)

    def test_calendar_season_phase_integration(self):
        """Test calendar component tracks season phases."""
        # Should start in offseason
        assert self.calendar.get_current_phase() == SeasonPhase.OFFSEASON
        assert self.calendar.is_offseason() == True
        assert self.calendar.is_during_regular_season() == False
        assert self.calendar.is_during_playoffs() == False

    def test_game_completion_recording(self):
        """Test recording game completions through calendar."""
        # Record preseason game
        preseason_game = GameCompletionEvent(
            game_id="preseason_1",
            home_team_id=1,
            away_team_id=2,
            completion_date=Date(2024, 8, 10),
            completion_time=datetime(2024, 8, 10, 20, 0),
            week=1,
            game_type="preseason",
            season_year=2024
        )

        transition = self.calendar.record_game_completion(preseason_game)

        assert transition is not None
        assert self.calendar.get_current_phase() == SeasonPhase.PRESEASON
        assert self.calendar.is_offseason() == False

    def test_milestone_tracking(self):
        """Test milestone tracking through calendar."""
        milestones = self.calendar.get_season_milestones()
        assert len(milestones) > 0

        # Should have next milestone
        next_milestone = self.calendar.get_next_milestone()
        assert next_milestone is not None

    def test_phase_info_comprehensive(self):
        """Test comprehensive phase information."""
        phase_info = self.calendar.get_phase_info()

        required_keys = [
            "current_phase", "phase_start_date", "season_year",
            "days_in_current_phase", "completed_games_total",
            "next_milestone", "recent_milestones_count"
        ]

        for key in required_keys:
            assert key in phase_info

    def test_force_phase_transition(self):
        """Test manual phase transitions."""
        transition = self.calendar.force_phase_transition(
            SeasonPhase.REGULAR_SEASON,
            {"reason": "testing"}
        )

        assert transition is not None
        assert self.calendar.get_current_phase() == SeasonPhase.REGULAR_SEASON
        assert self.calendar.is_during_regular_season() == True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])