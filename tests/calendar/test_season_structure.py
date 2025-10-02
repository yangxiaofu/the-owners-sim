"""
Test suite for NFL season structure and phase logic.

Tests the season phase management, NFL calendar structure,
and season-aware date calculations.
"""

import pytest
from datetime import datetime
from typing import List, Dict

# Add src to path for testing
import sys
from pathlib import Path
src_path = str(Path(__file__).parent.parent.parent / "src")
sys.path.insert(0, src_path)

from src.calendar.date_models import Date
from src.calendar.season_phase_tracker import (
    SeasonPhase, SeasonPhaseTracker, GameCompletionEvent, TransitionType
)
from src.calendar.phase_transition_triggers import (
    TransitionTriggerManager,
    PreseasonToRegularSeasonTrigger,
    RegularSeasonToPlayoffsTrigger,
    PlayoffsToOffseasonTrigger,
    OffseasonToPreseasonTrigger
)
from src.calendar.season_milestones import (
    SeasonMilestoneCalculator, MilestoneType, SeasonMilestone
)
from src.calendar.calendar_exceptions import CalendarStateException


class TestSeasonPhaseEnum:
    """Test the SeasonPhase enum and its values."""

    def test_season_phase_values(self):
        """Test that all expected season phases are defined."""
        expected_phases = ["preseason", "regular_season", "playoffs", "offseason"]

        actual_phases = [phase.value for phase in SeasonPhase]

        for expected in expected_phases:
            assert expected in actual_phases

        assert len(actual_phases) == 4

    def test_season_phase_ordering(self):
        """Test logical ordering of season phases."""
        phases = list(SeasonPhase)

        # Verify we have exactly 4 phases
        assert len(phases) == 4

        # Verify each phase exists
        assert SeasonPhase.PRESEASON in phases
        assert SeasonPhase.REGULAR_SEASON in phases
        assert SeasonPhase.PLAYOFFS in phases
        assert SeasonPhase.OFFSEASON in phases

    def test_season_phase_string_representation(self):
        """Test string representation of season phases."""
        assert str(SeasonPhase.PRESEASON) == "SeasonPhase.PRESEASON"
        assert SeasonPhase.PRESEASON.value == "preseason"
        assert SeasonPhase.REGULAR_SEASON.value == "regular_season"
        assert SeasonPhase.PLAYOFFS.value == "playoffs"
        assert SeasonPhase.OFFSEASON.value == "offseason"


class TestNFLSeasonStructure:
    """Test NFL season structure constants and logic."""

    def test_nfl_season_constants(self):
        """Test NFL season structure constants."""
        # Test regular season constants
        assert SeasonPhaseTracker.REGULAR_SEASON_GAMES_PER_TEAM == 17
        assert SeasonPhaseTracker.TOTAL_NFL_TEAMS == 32
        assert SeasonPhaseTracker.TOTAL_REGULAR_SEASON_GAMES == 272  # (32 * 17) / 2

    def test_playoff_structure_constants(self):
        """Test NFL playoff structure constants."""
        playoff_games = SeasonPhaseTracker.PLAYOFF_GAMES_BY_ROUND

        # Verify playoff structure
        assert playoff_games["wildcard"] == 6
        assert playoff_games["divisional"] == 4
        assert playoff_games["conference"] == 2
        assert playoff_games["super_bowl"] == 1

        # Verify total playoff games
        total_playoff_games = sum(playoff_games.values())
        assert total_playoff_games == 13
        assert SeasonPhaseTracker.TOTAL_PLAYOFF_GAMES == 13

    def test_season_year_calculation(self):
        """Test NFL season year logic."""
        # NFL seasons span two calendar years (e.g., 2024-25 season)
        # The season year is typically the year when it starts (2024)

        tracker = SeasonPhaseTracker(Date(2024, 8, 1), season_year=2024)
        phase_info = tracker.get_phase_info()
        assert phase_info["season_year"] == 2024

        # Test with different start date
        tracker2 = SeasonPhaseTracker(Date(2025, 1, 15), season_year=2024)
        phase_info2 = tracker2.get_phase_info()
        assert phase_info2["season_year"] == 2024


class TestSeasonPhaseLogic:
    """Test season phase transition logic and calculations."""

    def setup_method(self):
        """Set up test fixtures."""
        self.start_date = Date(2024, 8, 1)
        self.season_year = 2024
        self.tracker = SeasonPhaseTracker(self.start_date, self.season_year)

    def test_initial_phase_setup(self):
        """Test initial season phase setup."""
        assert self.tracker.get_current_phase() == SeasonPhase.OFFSEASON

        phase_info = self.tracker.get_phase_info()
        assert phase_info["current_phase"] == "offseason"
        assert phase_info["season_year"] == 2024
        assert phase_info["completed_games_total"] == 0

    def test_preseason_phase_transition(self):
        """Test transition into preseason phase."""
        # Record first preseason game
        preseason_game = GameCompletionEvent(
            game_id="preseason_week1_game1",
            home_team_id=1,
            away_team_id=2,
            completion_date=Date(2024, 8, 10),
            completion_time=datetime(2024, 8, 10, 19, 0),
            week=1,
            game_type="preseason",
            season_year=2024
        )

        transition = self.tracker.record_game_completion(preseason_game)

        assert transition is not None
        assert transition.transition_type == TransitionType.SEASON_START
        assert transition.from_phase == SeasonPhase.OFFSEASON
        assert transition.to_phase == SeasonPhase.PRESEASON
        assert self.tracker.get_current_phase() == SeasonPhase.PRESEASON

    def test_regular_season_phase_transition(self):
        """Test transition into regular season phase."""
        # First transition to preseason
        self.tracker.force_phase_transition(SeasonPhase.PRESEASON, Date(2024, 8, 10))

        # Record first regular season game
        regular_game = GameCompletionEvent(
            game_id="week1_regular_game1",
            home_team_id=3,
            away_team_id=4,
            completion_date=Date(2024, 9, 8),
            completion_time=datetime(2024, 9, 8, 13, 0),
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

    def test_playoff_phase_transition(self):
        """Test transition into playoff phase."""
        # Set up in regular season
        self.tracker.force_phase_transition(SeasonPhase.REGULAR_SEASON, Date(2024, 9, 8))

        # Add regular season games (272 total needed)
        for i in range(271):  # Add 271 games first
            game = GameCompletionEvent(
                game_id=f"regular_game_{i+1}",
                home_team_id=(i % 32) + 1,
                away_team_id=((i + 1) % 32) + 1,
                completion_date=Date(2025, 1, 7),
                completion_time=datetime(2025, 1, 7, 16, 0),
                week=18,
                game_type="regular",
                season_year=2024
            )
            self.tracker.record_game_completion(game)

        # Add the final 272nd game that should trigger playoffs
        final_game = GameCompletionEvent(
            game_id="final_regular_game",
            home_team_id=31,
            away_team_id=32,
            completion_date=Date(2025, 1, 8),
            completion_time=datetime(2025, 1, 8, 20, 0),
            week=18,
            game_type="regular",
            season_year=2024
        )

        transition = self.tracker.record_game_completion(final_game)

        assert transition is not None
        assert transition.transition_type == TransitionType.PLAYOFFS_START
        assert transition.from_phase == SeasonPhase.REGULAR_SEASON
        assert transition.to_phase == SeasonPhase.PLAYOFFS
        assert self.tracker.get_current_phase() == SeasonPhase.PLAYOFFS

    def test_offseason_phase_transition(self):
        """Test transition into offseason phase."""
        # Set up in playoffs
        self.tracker.force_phase_transition(SeasonPhase.PLAYOFFS, Date(2025, 1, 15))

        # Record Super Bowl completion
        super_bowl = GameCompletionEvent(
            game_id="super_bowl_2025",
            home_team_id=1,
            away_team_id=2,
            completion_date=Date(2025, 2, 9),
            completion_time=datetime(2025, 2, 9, 18, 30),
            week=22,  # Super Bowl week
            game_type="super_bowl",
            season_year=2024
        )

        transition = self.tracker.record_game_completion(super_bowl)

        assert transition is not None
        assert transition.transition_type == TransitionType.OFFSEASON_START
        assert transition.from_phase == SeasonPhase.PLAYOFFS
        assert transition.to_phase == SeasonPhase.OFFSEASON
        assert self.tracker.get_current_phase() == SeasonPhase.OFFSEASON


class TestSeasonCalculations:
    """Test season-aware date calculations and utilities."""

    def setup_method(self):
        """Set up test fixtures."""
        self.milestone_calculator = SeasonMilestoneCalculator()

    def test_milestone_calculation_types(self):
        """Test that all expected milestone types are supported."""
        definitions = self.milestone_calculator.get_milestone_definitions()

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

    def test_super_bowl_based_calculations(self):
        """Test milestone calculations based on Super Bowl date."""
        super_bowl_date = Date(2025, 2, 9)  # Sunday
        season_year = 2024

        milestones = self.milestone_calculator.calculate_milestones_for_season(
            season_year=season_year,
            super_bowl_date=super_bowl_date
        )

        # Find specific milestones
        draft_milestone = next((m for m in milestones if m.milestone_type == MilestoneType.DRAFT), None)
        fa_milestone = next((m for m in milestones if m.milestone_type == MilestoneType.FREE_AGENCY), None)

        assert draft_milestone is not None
        assert fa_milestone is not None

        # Draft should be ~11 weeks after Super Bowl
        days_to_draft = super_bowl_date.days_until(draft_milestone.date)
        assert 70 <= days_to_draft <= 84  # 10-12 weeks range

        # Free agency should be ~2 weeks after Super Bowl
        days_to_fa = super_bowl_date.days_until(fa_milestone.date)
        assert 10 <= days_to_fa <= 21  # 1.5-3 weeks range

    def test_season_progression_logic(self):
        """Test logical progression through NFL season."""
        # Test that phases follow logical NFL season order
        # This is more of a structural test than a calculation test

        # Create a tracker and simulate full season progression
        tracker = SeasonPhaseTracker(Date(2024, 7, 1), season_year=2024)

        # Should start in offseason
        assert tracker.get_current_phase() == SeasonPhase.OFFSEASON

        # Force transitions to test phase ordering
        tracker.force_phase_transition(SeasonPhase.PRESEASON, Date(2024, 8, 1))
        assert tracker.get_current_phase() == SeasonPhase.PRESEASON

        tracker.force_phase_transition(SeasonPhase.REGULAR_SEASON, Date(2024, 9, 1))
        assert tracker.get_current_phase() == SeasonPhase.REGULAR_SEASON

        tracker.force_phase_transition(SeasonPhase.PLAYOFFS, Date(2025, 1, 1))
        assert tracker.get_current_phase() == SeasonPhase.PLAYOFFS

        tracker.force_phase_transition(SeasonPhase.OFFSEASON, Date(2025, 2, 15))
        assert tracker.get_current_phase() == SeasonPhase.OFFSEASON

    def test_season_phase_information(self):
        """Test season phase information and metadata."""
        tracker = SeasonPhaseTracker(Date(2024, 8, 1), season_year=2024)

        # Test phase info retrieval
        phase_info = tracker.get_phase_info()
        assert isinstance(phase_info, dict)
        assert "current_phase" in phase_info
        assert "season_year" in phase_info
        assert "completed_games_total" in phase_info

        # Test transition history
        history = tracker.get_transition_history()
        assert isinstance(history, list)
        assert len(history) == 0  # No transitions yet


class TestSeasonPhaseTransitionTriggers:
    """Test the trigger management system for season phases."""

    def setup_method(self):
        """Set up test fixtures."""
        self.trigger_manager = TransitionTriggerManager()

    def test_trigger_manager_initialization(self):
        """Test that trigger manager has all required triggers."""
        triggers = self.trigger_manager.triggers
        assert len(triggers) == 4

        # Check trigger types
        trigger_classes = [type(trigger).__name__ for trigger in triggers]
        expected_classes = [
            "OffseasonToPreseasonTrigger",
            "PreseasonToRegularSeasonTrigger",
            "RegularSeasonToPlayoffsTrigger",
            "PlayoffsToOffseasonTrigger"
        ]

        for expected_class in expected_classes:
            assert expected_class in trigger_classes

    def test_trigger_conditions(self):
        """Test trigger condition evaluation."""
        # Test regular season to playoffs trigger
        playoffs_trigger = RegularSeasonToPlayoffsTrigger()

        # Create 272 regular season games
        regular_games = []
        for i in range(272):
            game = GameCompletionEvent(
                game_id=f"game_{i+1}",
                home_team_id=(i % 32) + 1,
                away_team_id=((i + 1) % 32) + 1,
                completion_date=Date(2025, 1, 8),
                completion_time=datetime(2025, 1, 8, 16, 0),
                week=18,
                game_type="regular",
                season_year=2024
            )
            regular_games.append(game)

        games_by_type = {"regular": regular_games}
        current_state = {}

        result = playoffs_trigger.check_trigger(regular_games, games_by_type, current_state)
        assert result is not None
        assert result.to_phase == SeasonPhase.PLAYOFFS

    def test_next_transition_prediction(self):
        """Test prediction of next phase transitions."""
        for phase in SeasonPhase:
            transition_info = self.trigger_manager.get_next_transition_info(phase)

            assert "next_transition" in transition_info
            assert "description" in transition_info
            assert "typical_timing" in transition_info

            # Verify logical next transitions
            if phase == SeasonPhase.OFFSEASON:
                assert transition_info["next_transition"] == "preseason"
            elif phase == SeasonPhase.PRESEASON:
                assert transition_info["next_transition"] == "regular_season"
            elif phase == SeasonPhase.REGULAR_SEASON:
                assert transition_info["next_transition"] == "playoffs"
            elif phase == SeasonPhase.PLAYOFFS:
                assert transition_info["next_transition"] == "offseason"


class TestSeasonStructureEdgeCases:
    """Test edge cases and boundary conditions in season structure."""

    def test_invalid_game_events(self):
        """Test handling of invalid game completion events."""
        tracker = SeasonPhaseTracker(Date(2024, 8, 1), season_year=2024)

        # Test invalid game type
        with pytest.raises(CalendarStateException):
            invalid_game = GameCompletionEvent(
                game_id="invalid_game",
                home_team_id=1,
                away_team_id=2,
                completion_date=Date(2024, 8, 10),
                completion_time=datetime(2024, 8, 10, 19, 0),
                week=1,
                game_type="invalid_type",
                season_year=2024
            )
            tracker.record_game_completion(invalid_game)

        # Test wrong season year
        with pytest.raises(CalendarStateException):
            wrong_season = GameCompletionEvent(
                game_id="wrong_season",
                home_team_id=1,
                away_team_id=2,
                completion_date=Date(2024, 8, 10),
                completion_time=datetime(2024, 8, 10, 19, 0),
                week=1,
                game_type="preseason",
                season_year=2023  # Wrong year
            )
            tracker.record_game_completion(wrong_season)

    def test_season_transition_boundary_conditions(self):
        """Test boundary conditions during season transitions."""
        tracker = SeasonPhaseTracker(Date(2024, 8, 1), season_year=2024)

        # Test transition pending detection
        tracker.force_phase_transition(SeasonPhase.REGULAR_SEASON, Date(2024, 9, 8))

        # Add 95% of regular season games
        for i in range(259):  # 95% of 272 games
            game = GameCompletionEvent(
                game_id=f"game_{i+1}",
                home_team_id=(i % 32) + 1,
                away_team_id=((i + 1) % 32) + 1,
                completion_date=Date(2024, 12, 30),
                completion_time=datetime(2024, 12, 30, 16, 0),
                week=17,
                game_type="regular",
                season_year=2024
            )
            tracker.record_game_completion(game)

        # Should detect that transition is pending
        assert tracker.is_phase_transition_pending() == True

    def test_season_reset_functionality(self):
        """Test season reset functionality."""
        tracker = SeasonPhaseTracker(Date(2024, 8, 1), season_year=2024)

        # Add some games and transition phases
        tracker.force_phase_transition(SeasonPhase.REGULAR_SEASON, Date(2024, 9, 8))

        game = GameCompletionEvent(
            game_id="test_game",
            home_team_id=1,
            away_team_id=2,
            completion_date=Date(2024, 9, 15),
            completion_time=datetime(2024, 9, 15, 13, 0),
            week=2,
            game_type="regular",
            season_year=2024
        )
        tracker.record_game_completion(game)

        # Verify initial state
        assert tracker.get_current_phase() == SeasonPhase.REGULAR_SEASON
        assert len(tracker.get_transition_history()) > 0

        # Reset to new season
        tracker.reset_season(2025, Date(2025, 8, 1))

        # Verify reset state
        assert tracker.get_current_phase() == SeasonPhase.OFFSEASON
        phase_info = tracker.get_phase_info()
        assert phase_info["season_year"] == 2025
        assert phase_info["completed_games_total"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])