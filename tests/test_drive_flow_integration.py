"""
Drive Flow Integration Tests

Tests the complete integration between DriveTransitionManager, PossessionManager,
GameLoopController, and GameManager for realistic drive-to-drive transitions.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from dataclasses import dataclass

from src.game_management.game_loop_controller import GameLoopController, DriveResult
from src.game_management.game_manager import GameManager, GamePhase
from src.game_management.drive_transition_manager import DriveTransitionManager, TransitionResult, TransitionType
from src.play_engine.game_state.possession_manager import PossessionManager
from src.play_engine.game_state.drive_manager import DriveManager, DriveEndReason
from src.play_engine.game_state.field_position import FieldPosition, FieldZone
from src.play_engine.game_state.down_situation import DownState
from src.team_management.teams.team_loader import Team


@pytest.fixture
def mock_teams():
    """Create mock home and away teams"""
    home_team = Mock(spec=Team)
    home_team.team_id = 22  # Detroit Lions
    home_team.full_name = "Detroit Lions"
    home_team.abbreviation = "DET"
    
    away_team = Mock(spec=Team)
    away_team.team_id = 12  # Green Bay Packers
    away_team.full_name = "Green Bay Packers"
    away_team.abbreviation = "GB"
    
    return home_team, away_team


@pytest.fixture
def mock_game_manager(mock_teams):
    """Create a mock GameManager with proper team setup"""
    home_team, away_team = mock_teams
    game_manager = Mock(spec=GameManager)
    
    # Set up possession manager
    game_manager.possession_manager = PossessionManager(home_team.team_id)
    
    # Set up scoreboard
    game_manager.scoreboard = Mock()
    game_manager.scoreboard.add_score = Mock()
    
    # Set up game clock
    game_manager.game_clock = Mock()
    
    return game_manager


@pytest.fixture
def coaching_configs():
    """Mock coaching staff configurations"""
    home_config = {"head_coach": {"archetype": "balanced"}}
    away_config = {"head_coach": {"archetype": "aggressive"}}
    return home_config, away_config


@pytest.fixture
def mock_rosters():
    """Create mock player rosters"""
    home_roster = [Mock() for _ in range(11)]  # 11 players
    away_roster = [Mock() for _ in range(11)]  # 11 players
    return home_roster, away_roster


@pytest.fixture
def game_loop_controller(mock_teams, mock_game_manager, coaching_configs, mock_rosters):
    """Create GameLoopController with mocked dependencies"""
    home_team, away_team = mock_teams
    home_config, away_config = coaching_configs
    home_roster, away_roster = mock_rosters
    
    # Mock the StaffFactory, CoachingStaff, and PlayCaller creation
    with patch('src.game_management.game_loop_controller.StaffFactory') as mock_staff_factory, \
         patch('src.game_management.game_loop_controller.PlayCaller') as mock_play_caller_class:
        
        mock_staff = Mock()
        mock_staff_factory.return_value.create_balanced_staff.return_value = mock_staff
        mock_play_caller_class.return_value = Mock()
        
        controller = GameLoopController(
            game_manager=mock_game_manager,
            home_team=home_team,
            away_team=away_team,
            home_coaching_staff_config=home_config,
            away_coaching_staff_config=away_config,
            home_roster=home_roster,
            away_roster=away_roster
        )
    
    return controller


class TestPossessionManagerTeamIDIntegration:
    """Test PossessionManager with integer team IDs"""
    
    def test_possession_manager_initialization(self):
        """Test PossessionManager initializes with team ID"""
        pm = PossessionManager(22)  # Detroit Lions
        assert pm.get_possessing_team_id() == 22
        assert pm.initial_team_id == 22
    
    def test_possession_manager_team_id_validation(self):
        """Test team ID validation in PossessionManager"""
        # Valid team IDs
        pm = PossessionManager(1)
        assert pm.get_possessing_team_id() == 1
        
        pm = PossessionManager(32)
        assert pm.get_possessing_team_id() == 32
        
        # Invalid team IDs
        with pytest.raises(ValueError):
            PossessionManager(0)
        
        with pytest.raises(ValueError):
            PossessionManager(33)
        
        with pytest.raises(ValueError):
            PossessionManager("invalid")
    
    def test_set_possession_with_team_ids(self):
        """Test setting possession with integer team IDs"""
        pm = PossessionManager(22)  # Start with Detroit
        
        pm.set_possession(12, "touchdown_kickoff")  # Change to Green Bay
        assert pm.get_possessing_team_id() == 12
        
        # Check possession history
        history = pm.get_possession_history()
        assert len(history) == 1
        assert history[0].previous_team_id == 22
        assert history[0].new_team_id == 12
        assert history[0].reason == "touchdown_kickoff"
    
    def test_get_opposing_team_id(self):
        """Test helper method to get opposing team"""
        pm = PossessionManager(22)  # Detroit has possession
        
        opposing_team = pm.get_opposing_team_id(22, 12)
        assert opposing_team == 12  # Green Bay is opposing
        
        # Change possession and test again
        pm.set_possession(12)
        opposing_team = pm.get_opposing_team_id(22, 12)
        assert opposing_team == 22  # Now Detroit is opposing


class TestDriveTransitionManagerIntegration:
    """Test DriveTransitionManager with fixed interfaces"""
    
    def test_drive_transition_manager_initialization(self, mock_teams):
        """Test DriveTransitionManager initializes with PossessionManager"""
        home_team, away_team = mock_teams
        pm = PossessionManager(home_team.team_id)
        dtm = DriveTransitionManager(possession_manager=pm)
        
        assert dtm.possession_manager is pm
    
    def test_touchdown_transition_integration(self, mock_teams):
        """Test complete touchdown transition flow"""
        home_team, away_team = mock_teams
        pm = PossessionManager(home_team.team_id)
        dtm = DriveTransitionManager(possession_manager=pm)
        
        # Create a mock completed drive that ended in touchdown
        completed_drive = Mock(spec=DriveManager)
        completed_drive.get_drive_end_reason.return_value = DriveEndReason.TOUCHDOWN
        completed_drive.get_possessing_team_id.return_value = home_team.team_id
        completed_drive.get_current_field_position.return_value = Mock(yard_line=5)
        
        # Execute transition
        result = dtm.handle_drive_transition(
            completed_drive=completed_drive,
            home_team_id=home_team.team_id,
            away_team_id=away_team.team_id
        )
        
        # Verify transition result
        assert result.transition_type == TransitionType.TOUCHDOWN
        assert result.new_possessing_team_id == away_team.team_id  # Opposing team gets kickoff
        assert result.kickoff_result is not None
        assert result.new_starting_field_position >= 20  # Reasonable kickoff position
        
        # Verify possession changed
        assert pm.get_possessing_team_id() == away_team.team_id
    
    def test_field_goal_transition_integration(self, mock_teams):
        """Test complete field goal transition flow"""
        home_team, away_team = mock_teams
        pm = PossessionManager(home_team.team_id)
        dtm = DriveTransitionManager(possession_manager=pm)
        
        # Create mock completed drive that ended in field goal
        completed_drive = Mock(spec=DriveManager)
        completed_drive.get_drive_end_reason.return_value = DriveEndReason.FIELD_GOAL
        completed_drive.get_possessing_team_id.return_value = home_team.team_id
        completed_drive.get_current_field_position.return_value = Mock(yard_line=25)
        
        # Execute transition
        result = dtm.handle_drive_transition(
            completed_drive=completed_drive,
            home_team_id=home_team.team_id,
            away_team_id=away_team.team_id
        )
        
        # Verify transition result
        assert result.transition_type == TransitionType.FIELD_GOAL
        assert result.new_possessing_team_id == away_team.team_id
        assert result.kickoff_result is not None
        
        # Verify possession changed
        assert pm.get_possessing_team_id() == away_team.team_id
    
    def test_punt_transition_integration(self, mock_teams):
        """Test punt transition with field position calculation"""
        home_team, away_team = mock_teams
        pm = PossessionManager(home_team.team_id)
        dtm = DriveTransitionManager(possession_manager=pm)
        
        # Create mock completed drive that ended in punt
        completed_drive = Mock(spec=DriveManager)
        completed_drive.get_drive_end_reason.return_value = DriveEndReason.PUNT
        completed_drive.get_possessing_team_id.return_value = home_team.team_id
        completed_drive.get_current_field_position.return_value = Mock(yard_line=35)
        
        # Execute transition
        result = dtm.handle_drive_transition(
            completed_drive=completed_drive,
            home_team_id=home_team.team_id,
            away_team_id=away_team.team_id
        )
        
        # Verify transition result
        assert result.transition_type == TransitionType.PUNT
        assert result.new_possessing_team_id == away_team.team_id
        assert result.punt_result is not None
        assert 10 <= result.new_starting_field_position <= 80  # Reasonable punt result
        
        # Verify possession changed
        assert pm.get_possessing_team_id() == away_team.team_id
    
    def test_turnover_transition_integration(self, mock_teams):
        """Test turnover transition with immediate possession change"""
        home_team, away_team = mock_teams
        pm = PossessionManager(home_team.team_id)
        dtm = DriveTransitionManager(possession_manager=pm)
        
        # Create mock completed drive that ended in turnover
        completed_drive = Mock(spec=DriveManager)
        completed_drive.get_drive_end_reason.return_value = DriveEndReason.TURNOVER_INTERCEPTION
        completed_drive.get_possessing_team_id.return_value = home_team.team_id
        completed_drive.get_current_field_position.return_value = Mock(yard_line=45)
        
        # Execute transition
        result = dtm.handle_drive_transition(
            completed_drive=completed_drive,
            home_team_id=home_team.team_id,
            away_team_id=away_team.team_id
        )
        
        # Verify transition result
        assert result.transition_type == TransitionType.TURNOVER
        assert result.new_possessing_team_id == away_team.team_id
        assert result.time_elapsed == 0  # No time elapsed on turnovers
        assert result.new_starting_field_position == 55  # Flipped field position (100 - 45)
        
        # Verify possession changed
        assert pm.get_possessing_team_id() == away_team.team_id


class TestGameLoopControllerDriveTransitions:
    """Test GameLoopController drive transition integration"""
    
    def test_drive_transition_manager_initialization(self, game_loop_controller):
        """Test that GameLoopController properly initializes DriveTransitionManager"""
        assert hasattr(game_loop_controller, 'drive_transition_manager')
        assert game_loop_controller.drive_transition_manager is not None
        
        # Verify it has correct possession manager reference
        assert game_loop_controller.drive_transition_manager.possession_manager is game_loop_controller.game_manager.possession_manager
    
    def test_handle_touchdown_drive_transition(self, game_loop_controller, mock_teams):
        """Test complete touchdown drive transition through GameLoopController"""
        home_team, away_team = mock_teams
        
        # Create drive result that ended in touchdown
        drive_result = DriveResult(
            possessing_team_id=home_team.team_id,
            starting_field_position=25,
            ending_field_position=5,
            drive_outcome=DriveEndReason.TOUCHDOWN,
            plays=[],
            total_plays=8,
            total_yards=70,
            time_elapsed=350,
            points_scored=6
        )
        
        # Execute drive transition
        game_loop_controller._handle_drive_transition(drive_result)
        
        # Verify scoring was handled
        game_loop_controller.game_manager.scoreboard.add_score.assert_called_once_with(home_team.team_id, 6)
        
        # Verify possession changed to opposing team
        assert game_loop_controller.game_manager.possession_manager.get_possessing_team_id() == away_team.team_id
        
        # Verify transition field position was set for next drive
        assert game_loop_controller.next_drive_field_position is not None
        assert game_loop_controller.next_drive_possessing_team_id == away_team.team_id
    
    def test_handle_field_goal_drive_transition(self, game_loop_controller, mock_teams):
        """Test field goal drive transition"""
        home_team, away_team = mock_teams
        
        drive_result = DriveResult(
            possessing_team_id=home_team.team_id,
            starting_field_position=45,
            ending_field_position=28,
            drive_outcome=DriveEndReason.FIELD_GOAL,
            plays=[],
            total_plays=6,
            total_yards=17,
            points_scored=3
        )
        
        # Execute drive transition
        game_loop_controller._handle_drive_transition(drive_result)
        
        # Verify scoring
        game_loop_controller.game_manager.scoreboard.add_score.assert_called_once_with(home_team.team_id, 3)
        
        # Verify possession changed
        assert game_loop_controller.game_manager.possession_manager.get_possessing_team_id() == away_team.team_id
    
    def test_handle_punt_drive_transition(self, game_loop_controller, mock_teams):
        """Test punt drive transition"""
        home_team, away_team = mock_teams
        
        drive_result = DriveResult(
            possessing_team_id=home_team.team_id,
            starting_field_position=20,
            ending_field_position=38,
            drive_outcome=DriveEndReason.PUNT,
            plays=[],
            total_plays=5,
            total_yards=18
        )
        
        # Execute drive transition
        game_loop_controller._handle_drive_transition(drive_result)
        
        # Verify no scoring for punt
        game_loop_controller.game_manager.scoreboard.add_score.assert_not_called()
        
        # Verify possession changed
        assert game_loop_controller.game_manager.possession_manager.get_possessing_team_id() == away_team.team_id
        
        # Verify field position was set for next drive
        assert game_loop_controller.next_drive_field_position is not None
    
    def test_handle_safety_drive_transition(self, game_loop_controller, mock_teams):
        """Test safety drive transition with opposing team scoring"""
        home_team, away_team = mock_teams
        
        drive_result = DriveResult(
            possessing_team_id=home_team.team_id,
            starting_field_position=95,
            ending_field_position=99,
            drive_outcome=DriveEndReason.SAFETY,
            plays=[],
            total_plays=2,
            total_yards=-4
        )
        
        # Execute drive transition
        game_loop_controller._handle_drive_transition(drive_result)
        
        # Verify safety scoring (2 points to opposing team)
        game_loop_controller.game_manager.scoreboard.add_score.assert_called_once_with(away_team.team_id, 2)
        
        # Verify possession changed to opposing team
        assert game_loop_controller.game_manager.possession_manager.get_possessing_team_id() == away_team.team_id
    
    def test_next_drive_field_position_usage(self, game_loop_controller, mock_teams):
        """Test that next drive uses transition field position"""
        home_team, away_team = mock_teams
        
        # Set up transition field position
        game_loop_controller.next_drive_field_position = 35
        game_loop_controller.next_drive_possessing_team_id = away_team.team_id
        
        # Mock the DriveManager creation to capture the field position
        with patch('src.game_management.game_loop_controller.DriveManager') as mock_drive_manager:
            # Mock play execution to avoid complex setup
            mock_drive_instance = Mock()
            mock_drive_instance.is_drive_over.return_value = True
            mock_drive_instance.get_drive_result.return_value = Mock(end_reason=DriveEndReason.PUNT)
            mock_drive_manager.return_value = mock_drive_instance
            
            # Execute drive creation
            try:
                game_loop_controller._run_drive(away_team.team_id)
            except:
                pass  # We expect this to fail due to mocking, but we can check the DriveManager call
            
            # Verify DriveManager was called with correct field position
            args, kwargs = mock_drive_manager.call_args
            starting_position = kwargs['starting_position']  # DriveManager uses keyword arguments
            assert starting_position.yard_line == 35
            
            # Verify transition data was cleared
            assert game_loop_controller.next_drive_field_position is None
            assert game_loop_controller.next_drive_possessing_team_id is None


class TestEndToEndDriveFlow:
    """Test complete end-to-end drive flow scenarios"""
    
    def test_sequential_drive_transitions(self, game_loop_controller, mock_teams):
        """Test multiple sequential drive transitions"""
        home_team, away_team = mock_teams
        
        # First drive: Home team scores touchdown
        td_drive = DriveResult(
            possessing_team_id=home_team.team_id,
            starting_field_position=25,
            ending_field_position=0,
            drive_outcome=DriveEndReason.TOUCHDOWN,
            plays=[], total_plays=7, total_yards=75
        )
        
        game_loop_controller._handle_drive_transition(td_drive)
        
        # Verify first transition
        assert game_loop_controller.game_manager.possession_manager.get_possessing_team_id() == away_team.team_id
        first_field_pos = game_loop_controller.next_drive_field_position
        
        # Second drive: Away team punts
        punt_drive = DriveResult(
            possessing_team_id=away_team.team_id,
            starting_field_position=first_field_pos,
            ending_field_position=40,
            drive_outcome=DriveEndReason.PUNT,
            plays=[], total_plays=4, total_yards=15
        )
        
        game_loop_controller._handle_drive_transition(punt_drive)
        
        # Verify second transition
        assert game_loop_controller.game_manager.possession_manager.get_possessing_team_id() == home_team.team_id
        second_field_pos = game_loop_controller.next_drive_field_position
        
        # Verify field positions are realistic
        assert 20 <= first_field_pos <= 80  # Kickoff return (can be anywhere from touchback to long return)
        assert 10 <= second_field_pos <= 90  # Punt return (wider range due to punt variability)
        
        # Verify scoring calls
        assert game_loop_controller.game_manager.scoreboard.add_score.call_count == 1
    
    def test_statistics_integration_with_transitions(self, game_loop_controller, mock_teams):
        """Test that drive transitions are properly recorded in statistics"""
        home_team, away_team = mock_teams
        
        # Mock the stats aggregator
        mock_stats = Mock()
        game_loop_controller.stats_aggregator = mock_stats
        
        # Execute drive transition
        drive_result = DriveResult(
            possessing_team_id=home_team.team_id,
            starting_field_position=30,
            ending_field_position=20,
            drive_outcome=DriveEndReason.FIELD_GOAL,
            plays=[], total_plays=5, total_yards=25
        )
        
        game_loop_controller._handle_drive_transition(drive_result)
        
        # Verify statistics were recorded
        mock_stats.record_drive_completion.assert_called_once_with(
            drive_outcome=DriveEndReason.FIELD_GOAL.value,
            possessing_team_id=home_team.team_id
        )


if __name__ == '__main__':
    pytest.main([__file__, '-v'])