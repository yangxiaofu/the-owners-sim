"""
Tests for NFL Overtime Manager and Possession Tracking.

Validates compliance with 2023+ NFL overtime rules:
- Regular Season: 10-minute period with guaranteed possession
- Playoffs: 15-minute periods with guaranteed possession
- Exception: First team scores TD = immediate win
- After both possess: any score wins (sudden death)
"""

import pytest
from unittest.mock import MagicMock

from game_management.overtime_manager import (
    OvertimeType,
    OvertimePhase,
    OvertimeSetup,
    OvertimePossessionTracker,
    IOvertimeManager,
    RegularSeasonOvertimeManager,
    PlayoffOvertimeManager,
    create_overtime_manager,
)


# ==================== OvertimePossessionTracker Tests ====================

class TestOvertimePossessionTracker:
    """Tests for OvertimePossessionTracker class."""

    def test_initial_state(self):
        """Tracker should start in GUARANTEED phase with no possessions."""
        tracker = OvertimePossessionTracker(team_a_id=1, team_b_id=2)
        assert tracker.phase == OvertimePhase.GUARANTEED
        assert len(tracker.possessions) == 0
        assert tracker.team_a_points == 0
        assert tracker.team_b_points == 0
        assert tracker.should_game_end() is False

    def test_first_td_ends_game(self):
        """If first team scores TD, game ends immediately."""
        tracker = OvertimePossessionTracker(team_a_id=1, team_b_id=2)
        tracker.record_possession(team_id=1, result="touchdown", points=7)
        assert tracker.should_game_end() is True
        assert tracker.get_winning_team_id() == 1
        # Should still be in GUARANTEED phase (never reached sudden death)
        assert tracker.phase == OvertimePhase.GUARANTEED

    def test_first_fg_allows_response(self):
        """If first team scores FG, second team gets possession."""
        tracker = OvertimePossessionTracker(team_a_id=1, team_b_id=2)
        tracker.record_possession(team_id=1, result="field_goal", points=3)
        assert tracker.should_game_end() is False  # Team 2 gets a chance
        assert tracker.phase == OvertimePhase.GUARANTEED

    def test_second_team_td_wins_after_fg(self):
        """Second team scoring TD after FG wins."""
        tracker = OvertimePossessionTracker(team_a_id=1, team_b_id=2)
        tracker.record_possession(team_id=1, result="field_goal", points=3)
        tracker.record_possession(team_id=2, result="touchdown", points=7)
        assert tracker.should_game_end() is True
        assert tracker.get_winning_team_id() == 2

    def test_second_team_fg_wins_after_punt(self):
        """If first team punts, second team wins with any score."""
        tracker = OvertimePossessionTracker(team_a_id=1, team_b_id=2)
        tracker.record_possession(team_id=1, result="punt", points=0)
        tracker.record_possession(team_id=2, result="field_goal", points=3)
        assert tracker.should_game_end() is True
        assert tracker.get_winning_team_id() == 2

    def test_matching_fg_continues_sudden_death(self):
        """If both teams score FG, sudden death begins."""
        tracker = OvertimePossessionTracker(team_a_id=1, team_b_id=2)
        tracker.record_possession(team_id=1, result="field_goal", points=3)
        tracker.record_possession(team_id=2, result="field_goal", points=3)
        assert tracker.should_game_end() is False
        assert tracker.phase == OvertimePhase.SUDDEN_DEATH

    def test_sudden_death_any_score_wins(self):
        """After both possess, any score wins."""
        tracker = OvertimePossessionTracker(team_a_id=1, team_b_id=2)
        tracker.record_possession(team_id=1, result="field_goal", points=3)
        tracker.record_possession(team_id=2, result="field_goal", points=3)
        # Now in sudden death - next score wins
        tracker.record_possession(team_id=1, result="field_goal", points=3)
        assert tracker.should_game_end() is True
        assert tracker.get_winning_team_id() == 1

    def test_both_teams_punt_continues_sudden_death(self):
        """If both teams punt, game continues in sudden death."""
        tracker = OvertimePossessionTracker(team_a_id=1, team_b_id=2)
        tracker.record_possession(team_id=1, result="punt", points=0)
        tracker.record_possession(team_id=2, result="punt", points=0)
        assert tracker.should_game_end() is False
        assert tracker.phase == OvertimePhase.SUDDEN_DEATH

    def test_first_safety_ends_game(self):
        """Safety on first possession ends game (defensive score)."""
        tracker = OvertimePossessionTracker(team_a_id=1, team_b_id=2)
        # Team 1 has ball, gives up safety - Team 2 scores 2 points
        tracker.record_possession(team_id=1, result="safety", points=0)
        assert tracker.should_game_end() is True

    def test_turnover_does_not_end_game_in_guaranteed_phase(self):
        """Turnover during first possession doesn't end game."""
        tracker = OvertimePossessionTracker(team_a_id=1, team_b_id=2)
        tracker.record_possession(team_id=1, result="turnover", points=0)
        assert tracker.should_game_end() is False
        assert tracker.phase == OvertimePhase.GUARANTEED

    def test_reset_clears_state(self):
        """Reset should clear all state for new period."""
        tracker = OvertimePossessionTracker(team_a_id=1, team_b_id=2)
        tracker.record_possession(team_id=1, result="field_goal", points=3)
        tracker.record_possession(team_id=2, result="field_goal", points=3)
        tracker.reset()
        assert len(tracker.possessions) == 0
        assert tracker.phase == OvertimePhase.GUARANTEED
        assert tracker.team_a_points == 0
        assert tracker.team_b_points == 0


# ==================== RegularSeasonOvertimeManager Tests ====================

class TestRegularSeasonOvertimeManager:
    """Tests for RegularSeasonOvertimeManager class."""

    def test_overtime_duration_is_10_minutes(self):
        """Regular season OT should be 10 minutes (600 seconds)."""
        manager = RegularSeasonOvertimeManager()
        setup = manager.setup_overtime_period()
        assert setup.clock_time_seconds == 600  # 10 minutes

    def test_overtime_duration_constant(self):
        """OVERTIME_DURATION_SECONDS should be 600."""
        assert RegularSeasonOvertimeManager.OVERTIME_DURATION_SECONDS == 600

    def test_setup_overtime_period_returns_correct_quarter(self):
        """First OT period should be quarter 5."""
        manager = RegularSeasonOvertimeManager()
        setup = manager.setup_overtime_period()
        assert setup.quarter_number == 5

    def test_setup_overtime_period_not_sudden_death(self):
        """OT should NOT be immediate sudden death (guaranteed possession first)."""
        manager = RegularSeasonOvertimeManager()
        setup = manager.setup_overtime_period()
        assert setup.sudden_death is False

    def test_max_one_overtime_period(self):
        """Regular season allows maximum 1 overtime period."""
        manager = RegularSeasonOvertimeManager()
        manager.setup_overtime_period()
        with pytest.raises(ValueError):
            manager.setup_overtime_period()

    def test_should_enter_overtime_when_tied(self):
        """Should enter overtime when game is tied at end of regulation."""
        manager = RegularSeasonOvertimeManager()
        game_state = MagicMock()
        game_state.quarter = 4
        game_state.score = {1: 21, 2: 21}
        assert manager.should_enter_overtime(game_state) is True

    def test_should_not_enter_overtime_when_not_tied(self):
        """Should not enter overtime when game is not tied."""
        manager = RegularSeasonOvertimeManager()
        game_state = MagicMock()
        game_state.quarter = 4
        game_state.score = {1: 24, 2: 21}
        assert manager.should_enter_overtime(game_state) is False

    def test_should_not_continue_overtime(self):
        """Regular season OT ends after 1 period regardless of outcome."""
        manager = RegularSeasonOvertimeManager()
        game_state = MagicMock()
        game_state.score = {1: 21, 2: 21}
        assert manager.should_continue_overtime(game_state) is False

    def test_reset_allows_new_period(self):
        """Reset should allow setting up a new OT period."""
        manager = RegularSeasonOvertimeManager()
        manager.setup_overtime_period()
        manager.reset()
        # Should be able to setup again after reset
        setup = manager.setup_overtime_period()
        assert setup.quarter_number == 5


# ==================== PlayoffOvertimeManager Tests ====================

class TestPlayoffOvertimeManager:
    """Tests for PlayoffOvertimeManager class."""

    def test_overtime_duration_is_15_minutes(self):
        """Playoff OT should be 15 minutes (900 seconds)."""
        manager = PlayoffOvertimeManager()
        setup = manager.setup_overtime_period()
        assert setup.clock_time_seconds == 900  # 15 minutes

    def test_overtime_duration_constant(self):
        """OVERTIME_DURATION_SECONDS should be 900."""
        assert PlayoffOvertimeManager.OVERTIME_DURATION_SECONDS == 900

    def test_setup_overtime_period_not_sudden_death(self):
        """Playoff OT should NOT be immediate sudden death."""
        manager = PlayoffOvertimeManager()
        setup = manager.setup_overtime_period()
        assert setup.sudden_death is False

    def test_multiple_overtime_periods_allowed(self):
        """Playoffs allow unlimited overtime periods."""
        manager = PlayoffOvertimeManager()
        setup1 = manager.setup_overtime_period()
        assert setup1.quarter_number == 5
        setup2 = manager.setup_overtime_period()
        assert setup2.quarter_number == 6
        setup3 = manager.setup_overtime_period()
        assert setup3.quarter_number == 7

    def test_should_continue_overtime_when_tied(self):
        """Playoff OT continues until someone wins."""
        manager = PlayoffOvertimeManager()
        game_state = MagicMock()
        game_state.score = {1: 21, 2: 21}
        assert manager.should_continue_overtime(game_state) is True

    def test_should_not_continue_overtime_when_not_tied(self):
        """Playoff OT ends when someone is ahead."""
        manager = PlayoffOvertimeManager()
        game_state = MagicMock()
        game_state.score = {1: 24, 2: 21}
        assert manager.should_continue_overtime(game_state) is False


# ==================== Factory Function Tests ====================

class TestCreateOvertimeManager:
    """Tests for create_overtime_manager factory function."""

    def test_creates_regular_season_manager(self):
        """Factory should create RegularSeasonOvertimeManager for REGULAR_SEASON."""
        manager = create_overtime_manager(OvertimeType.REGULAR_SEASON)
        assert isinstance(manager, RegularSeasonOvertimeManager)

    def test_creates_playoff_manager(self):
        """Factory should create PlayoffOvertimeManager for PLAYOFFS."""
        manager = create_overtime_manager(OvertimeType.PLAYOFFS)
        assert isinstance(manager, PlayoffOvertimeManager)

    def test_raises_for_unknown_type(self):
        """Factory should raise ValueError for unknown type."""
        with pytest.raises(ValueError):
            create_overtime_manager("invalid")


# ==================== OvertimeSetup Tests ====================

class TestOvertimeSetup:
    """Tests for OvertimeSetup dataclass."""

    def test_dataclass_fields(self):
        """OvertimeSetup should have all required fields."""
        setup = OvertimeSetup(
            quarter_number=5,
            clock_time_seconds=600,
            possession_team_id=None,
            sudden_death=False,
            description="Test OT"
        )
        assert setup.quarter_number == 5
        assert setup.clock_time_seconds == 600
        assert setup.possession_team_id is None
        assert setup.sudden_death is False
        assert setup.description == "Test OT"


# ==================== Integration Scenario Tests ====================

class TestOvertimeScenarios:
    """Integration tests for realistic overtime scenarios."""

    def test_scenario_first_team_td_walkoff(self):
        """Scenario: First team scores TD = immediate win."""
        tracker = OvertimePossessionTracker(team_a_id=10, team_b_id=20)
        # Team 10 receives, drives down field, scores TD
        tracker.record_possession(team_id=10, result="touchdown", points=7)
        assert tracker.should_game_end() is True
        assert tracker.get_winning_team_id() == 10

    def test_scenario_fg_followed_by_td_response(self):
        """Scenario: First team scores FG, second team responds with TD."""
        tracker = OvertimePossessionTracker(team_a_id=10, team_b_id=20)
        # Team 10 kicks FG
        tracker.record_possession(team_id=10, result="field_goal", points=3)
        assert tracker.should_game_end() is False
        # Team 20 responds with TD
        tracker.record_possession(team_id=20, result="touchdown", points=7)
        assert tracker.should_game_end() is True
        assert tracker.get_winning_team_id() == 20

    def test_scenario_both_teams_fg_sudden_death(self):
        """Scenario: Both teams score FG, then sudden death FG wins."""
        tracker = OvertimePossessionTracker(team_a_id=10, team_b_id=20)
        # Team 10 kicks FG
        tracker.record_possession(team_id=10, result="field_goal", points=3)
        # Team 20 matches with FG
        tracker.record_possession(team_id=20, result="field_goal", points=3)
        assert tracker.should_game_end() is False
        assert tracker.phase == OvertimePhase.SUDDEN_DEATH
        # Team 10 gets ball back, kicks another FG
        tracker.record_possession(team_id=10, result="field_goal", points=3)
        assert tracker.should_game_end() is True
        assert tracker.get_winning_team_id() == 10  # Team 10: 6pts, Team 20: 3pts

    def test_scenario_punt_punt_fg_wins(self):
        """Scenario: Both teams punt, then FG wins in sudden death."""
        tracker = OvertimePossessionTracker(team_a_id=10, team_b_id=20)
        # Team 10 punts
        tracker.record_possession(team_id=10, result="punt", points=0)
        # Team 20 punts
        tracker.record_possession(team_id=20, result="punt", points=0)
        assert tracker.should_game_end() is False
        assert tracker.phase == OvertimePhase.SUDDEN_DEATH
        # Team 10 kicks FG to win
        tracker.record_possession(team_id=10, result="field_goal", points=3)
        assert tracker.should_game_end() is True
        assert tracker.get_winning_team_id() == 10

    def test_scenario_multiple_turnovers_before_score(self):
        """Scenario: Multiple turnovers before someone scores."""
        tracker = OvertimePossessionTracker(team_a_id=10, team_b_id=20)
        # Team 10 turns it over
        tracker.record_possession(team_id=10, result="turnover", points=0)
        assert tracker.should_game_end() is False
        # Team 20 turns it over
        tracker.record_possession(team_id=20, result="turnover", points=0)
        assert tracker.should_game_end() is False
        assert tracker.phase == OvertimePhase.SUDDEN_DEATH
        # Team 10 finally scores
        tracker.record_possession(team_id=10, result="touchdown", points=7)
        assert tracker.should_game_end() is True
        assert tracker.get_winning_team_id() == 10
