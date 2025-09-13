#!/usr/bin/env python3
"""
Unit Tests for GameLoopController

Tests all aspects of the game loop orchestration system:
- Initialization and dependency injection
- Game flow orchestration (quarters, drives, plays)
- Drive management and transitions
- Statistics tracking and result generation
- Data structure validation
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, call
from dataclasses import dataclass
from typing import Dict, List, Any

# Import the class under test
from src.game_management.game_loop_controller import (
    GameLoopController, 
    GameResult, 
    DriveResult,
    DriveEndReason
)

# Import dependencies for mocking
from src.game_management.game_manager import GameManager, GamePhase
from src.play_engine.game_state.drive_manager import DriveManager, DriveSituation
from src.play_engine.play_calling.coaching_staff import CoachingStaff
from src.play_engine.play_calling.play_caller import PlayCaller, PlayCallContext
from src.play_engine.core.play_result import PlayResult
from src.team_management.teams.team_loader import Team


class TestGameLoopControllerInitialization:
    """Test GameLoopController initialization and dependency setup"""
    
    def setup_method(self):
        """Set up test fixtures"""
        # Mock teams
        self.home_team = Mock(spec=Team)
        self.home_team.team_id = 1
        self.home_team.abbreviation = "DET"
        self.home_team.full_name = "Detroit Lions"
        
        self.away_team = Mock(spec=Team)
        self.away_team.team_id = 2
        self.away_team.abbreviation = "GB"
        self.away_team.full_name = "Green Bay Packers"
        
        # Mock rosters
        self.home_roster = [Mock() for _ in range(53)]
        self.away_roster = [Mock() for _ in range(53)]
        
        # Mock coaching staff configs
        self.home_coaching_config = {
            "head_coach": {"name": "Dan Campbell", "archetype": "aggressive"},
            "offensive_coordinator": {"name": "Ben Johnson", "style": "pass_heavy"},
            "defensive_coordinator": {"name": "Aaron Glenn", "style": "aggressive"}
        }
        self.away_coaching_config = {
            "head_coach": {"name": "Matt LaFleur", "archetype": "balanced"},
            "offensive_coordinator": {"name": "Adam Stenavich", "style": "balanced"},
            "defensive_coordinator": {"name": "Joe Barry", "style": "conservative"}
        }
        
        # Mock GameManager
        self.game_manager = Mock(spec=GameManager)
    
    @patch.object(GameLoopController, '_create_coaching_staff_from_config')
    @patch('src.game_management.game_loop_controller.PlayCaller')
    def test_initialization_creates_all_components(self, mock_play_caller, mock_staff_factory):
        """Test that initialization creates all required components"""
        # Setup mocks
        mock_home_staff = Mock(spec=CoachingStaff)
        mock_away_staff = Mock(spec=CoachingStaff)
        mock_staff_factory.side_effect = [mock_home_staff, mock_away_staff]
        
        mock_home_caller = Mock(spec=PlayCaller)
        mock_away_caller = Mock(spec=PlayCaller)
        mock_play_caller.side_effect = [mock_home_caller, mock_away_caller]
        
        # Create controller
        controller = GameLoopController(
            game_manager=self.game_manager,
            home_team=self.home_team,
            away_team=self.away_team,
            home_coaching_staff_config=self.home_coaching_config,
            away_coaching_staff_config=self.away_coaching_config,
            home_roster=self.home_roster,
            away_roster=self.away_roster
        )
        
        # Verify initialization
        assert controller.game_manager == self.game_manager
        assert controller.home_team == self.home_team
        assert controller.away_team == self.away_team
        assert controller.home_roster == self.home_roster
        assert controller.away_roster == self.away_roster
        
        # Verify coaching staff creation
        assert mock_staff_factory.call_count == 2
        mock_staff_factory.assert_any_call(self.home_coaching_config, 1)
        mock_staff_factory.assert_any_call(self.away_coaching_config, 2)
        
        # Verify play caller creation
        assert mock_play_caller.call_count == 2
        assert controller.home_play_caller == mock_home_caller
        assert controller.away_play_caller == mock_away_caller
        
        # Verify tracking initialization
        assert controller.drive_results == []
        assert controller.total_plays == 0
    
    def test_initialization_with_invalid_teams_raises_error(self):
        """Test that initialization with invalid teams raises appropriate errors"""
        # Test with None team
        with pytest.raises(AttributeError):
            GameLoopController(
                game_manager=self.game_manager,
                home_team=None,
                away_team=self.away_team,
                home_coaching_staff_config=self.home_coaching_config,
                away_coaching_staff_config=self.away_coaching_config,
                home_roster=self.home_roster,
                away_roster=self.away_roster
            )


class TestGameOrchestration:
    """Test main game orchestration methods"""
    
    def setup_method(self):
        """Set up test fixtures with mocked controller"""
        with patch.object(GameLoopController, '_create_coaching_staff_from_config'), \
             patch('src.game_management.game_loop_controller.PlayCaller'):
            
            self.controller = GameLoopController(
                game_manager=Mock(spec=GameManager),
                home_team=Mock(team_id=1, abbreviation="DET"),
                away_team=Mock(team_id=2, abbreviation="GB"), 
                home_coaching_staff_config={},
                away_coaching_staff_config={},
                home_roster=[],
                away_roster=[]
            )
    
    @patch.object(GameLoopController, '_run_quarter')
    @patch.object(GameLoopController, '_is_game_over')
    @patch.object(GameLoopController, '_needs_overtime')
    @patch.object(GameLoopController, '_run_overtime')
    @patch.object(GameLoopController, '_generate_final_result')
    def test_run_game_normal_four_quarters(self, mock_generate_result, mock_run_overtime, 
                                         mock_needs_overtime, mock_is_game_over, mock_run_quarter):
        """Test normal four-quarter game without overtime"""
        # Setup mocks
        mock_is_game_over.return_value = False  # Game continues through all quarters
        mock_needs_overtime.return_value = False
        mock_result = Mock(spec=GameResult)
        mock_generate_result.return_value = mock_result
        
        # Run game
        result = self.controller.run_game()
        
        # Verify quarter execution
        assert mock_run_quarter.call_count == 4
        expected_calls = [call(1), call(2), call(3), call(4)]
        mock_run_quarter.assert_has_calls(expected_calls)
        
        # Verify overtime logic
        mock_needs_overtime.assert_called_once()
        mock_run_overtime.assert_not_called()
        
        # Verify result generation
        mock_generate_result.assert_called_once()
        assert result == mock_result
    
    @patch.object(GameLoopController, '_run_quarter')
    @patch.object(GameLoopController, '_is_game_over')
    @patch.object(GameLoopController, '_needs_overtime')
    @patch.object(GameLoopController, '_run_overtime')
    @patch.object(GameLoopController, '_generate_final_result')
    def test_run_game_with_overtime(self, mock_generate_result, mock_run_overtime,
                                  mock_needs_overtime, mock_is_game_over, mock_run_quarter):
        """Test game that goes to overtime"""
        # Setup mocks
        mock_is_game_over.return_value = False
        mock_needs_overtime.return_value = True
        mock_result = Mock(spec=GameResult)
        mock_generate_result.return_value = mock_result
        
        # Run game
        result = self.controller.run_game()
        
        # Verify all quarters run
        assert mock_run_quarter.call_count == 4
        
        # Verify overtime execution
        mock_needs_overtime.assert_called_once()
        mock_run_overtime.assert_called_once()
        
        assert result == mock_result
    
    @patch.object(GameLoopController, '_is_quarter_complete')
    @patch.object(GameLoopController, '_determine_next_possession')
    @patch.object(GameLoopController, '_run_drive')
    @patch.object(GameLoopController, '_handle_drive_transition')
    def test_run_quarter_executes_multiple_drives(self, mock_handle_transition, mock_run_drive,
                                                mock_determine_possession, mock_is_quarter_complete):
        """Test that _run_quarter executes multiple drives until quarter ends"""
        # Setup mocks
        mock_is_quarter_complete.side_effect = [False, False, False, True]  # 3 drives then quarter ends
        mock_determine_possession.return_value = 1  # Home team possession
        
        mock_drive_results = [
            Mock(spec=DriveResult),
            Mock(spec=DriveResult), 
            Mock(spec=DriveResult)
        ]
        mock_run_drive.side_effect = mock_drive_results
        
        # Setup GameManager mock attributes
        self.controller.game_manager.possession_manager = Mock()
        self.controller.game_manager.possession_manager.get_possessing_team_id.return_value = None
        self.controller.game_manager.advance_quarter = Mock()
        
        # Run quarter
        self.controller._run_quarter(1)
        
        # Verify quarter advancement
        self.controller.game_manager.advance_quarter.assert_called_once()
        
        # Verify drives executed
        assert mock_run_drive.call_count == 3
        assert mock_handle_transition.call_count == 3
        
        # Verify drive results stored
        assert len(self.controller.drive_results) == 3
        assert self.controller.drive_results == mock_drive_results


class TestDriveExecution:
    """Test individual drive and play execution"""
    
    def setup_method(self):
        """Set up test fixtures"""
        with patch.object(GameLoopController, '_create_coaching_staff_from_config'), \
             patch('src.game_management.game_loop_controller.PlayCaller'):
            
            self.controller = GameLoopController(
                game_manager=Mock(spec=GameManager),
                home_team=Mock(team_id=1, abbreviation="DET"),
                away_team=Mock(team_id=2, abbreviation="GB"),
                home_coaching_staff_config={},
                away_coaching_staff_config={},
                home_roster=[Mock() for _ in range(10)],
                away_roster=[Mock() for _ in range(10)]
            )
    
    @patch('src.game_management.game_loop_controller.DriveManager')
    @patch.object(GameLoopController, '_run_play')
    def test_run_drive_executes_plays_until_drive_ends(self, mock_run_play, mock_drive_manager_class):
        """Test that _run_drive executes plays until DriveManager indicates drive is over"""
        # Setup DriveManager mock
        mock_drive_manager = Mock(spec=DriveManager)
        mock_drive_manager_class.return_value = mock_drive_manager
        mock_drive_manager.is_drive_over.side_effect = [False, False, False, True]  # 3 plays then drive ends
        
        # Setup drive result
        mock_drive_result = Mock()
        mock_drive_result.end_reason = DriveEndReason.TOUCHDOWN
        mock_drive_manager.get_drive_result.return_value = mock_drive_result
        
        # Setup field tracker mock
        mock_drive_manager.field_tracker = Mock()
        mock_drive_manager.field_tracker.current_position = Mock()
        mock_drive_manager.field_tracker.current_position.yard_line = 0
        
        # Setup play results
        mock_play_results = [
            Mock(spec=PlayResult, yards_gained=5),
            Mock(spec=PlayResult, yards_gained=10),
            Mock(spec=PlayResult, yards_gained=25)
        ]
        mock_run_play.side_effect = mock_play_results
        
        # Run drive
        result = self.controller._run_drive(possessing_team_id=1)
        
        # Verify DriveManager creation
        mock_drive_manager_class.assert_called_once_with(
            possessing_team_id=1,
            starting_field_position=20,
            starting_down=1,
            starting_yards_to_go=10
        )
        
        # Verify play execution
        assert mock_run_play.call_count == 3
        assert mock_drive_manager.process_play_result.call_count == 3
        
        # Verify result structure
        assert isinstance(result, DriveResult)
        assert result.possessing_team_id == 1
        assert result.total_plays == 3
        assert result.total_yards == 40  # 5 + 10 + 25
        assert result.drive_outcome == DriveEndReason.TOUCHDOWN
        assert len(result.plays) == 3
        
        # Verify total plays counter updated
        assert self.controller.total_plays == 3
    
    @patch('src.game_management.game_loop_controller.PlayEngineParams')
    @patch('src.game_management.game_loop_controller.simulate')
    def test_run_play_coordinates_all_components(self, mock_simulate, mock_play_params_class):
        """Test that _run_play coordinates play calling and execution"""
        # Setup mocks
        mock_drive_manager = Mock(spec=DriveManager)
        mock_situation = Mock(spec=DriveSituation)
        mock_situation.down = 1
        mock_situation.yards_to_go = 10
        mock_field_position = Mock()
        mock_field_position.yard_line = 50
        mock_situation.field_position = mock_field_position
        mock_drive_manager.get_current_situation.return_value = mock_situation
        
        mock_offensive_play_call = Mock()
        mock_defensive_play_call = Mock()
        
        self.controller.home_play_caller.select_offensive_play.return_value = mock_offensive_play_call
        self.controller.away_play_caller.select_defensive_play.return_value = mock_defensive_play_call
        
        mock_play_params = Mock()
        mock_play_params_class.return_value = mock_play_params
        
        mock_play_result = Mock(spec=PlayResult)
        mock_play_result.outcome = "run"
        mock_play_result.yards_gained = 7
        mock_play_result.yards = 7  # Used by CentralizedStatsAggregator for big plays check
        mock_play_result.points = 0
        mock_play_result.time_elapsed = 25.0
        mock_play_result.is_scoring_play = False
        mock_play_result.is_turnover = False
        mock_play_result.is_punt = False
        mock_play_result.penalty_occurred = False
        mock_play_result.penalty_yards = 0
        mock_play_result.achieved_first_down = False
        mock_play_result.has_player_stats.return_value = False
        mock_play_result.is_missed_field_goal.return_value = False
        mock_simulate.return_value = mock_play_result
        
        # Run play
        result = self.controller._run_play(mock_drive_manager, possessing_team_id=1)
        
        # Verify situation retrieval (called twice: once for play context, once for stats recording)
        assert mock_drive_manager.get_current_situation.call_count == 2
        
        # Verify play calling
        self.controller.home_play_caller.select_offensive_play.assert_called_once()
        self.controller.away_play_caller.select_defensive_play.assert_called_once()
        
        # Verify play execution
        mock_simulate.assert_called_once_with(mock_play_params)
        
        assert result == mock_play_result


class TestDriveTransitions:
    """Test drive transition handling and possession changes"""
    
    def setup_method(self):
        """Set up test fixtures"""
        with patch.object(GameLoopController, '_create_coaching_staff_from_config'), \
             patch('src.game_management.game_loop_controller.PlayCaller'):
            
            self.controller = GameLoopController(
                game_manager=Mock(spec=GameManager),
                home_team=Mock(team_id=1),
                away_team=Mock(team_id=2),
                home_coaching_staff_config={},
                away_coaching_staff_config={},
                home_roster=[],
                away_roster=[]
            )
    
    def test_handle_drive_transition_touchdown_adds_score(self):
        """Test that touchdown drives add correct score to scoreboard"""
        drive_result = Mock(spec=DriveResult)
        drive_result.drive_outcome = DriveEndReason.TOUCHDOWN
        drive_result.possessing_team_id = 1
        
        # Setup GameManager scoreboard mock
        self.controller.game_manager.scoreboard = Mock()
        
        # Handle transition
        self.controller._handle_drive_transition(drive_result)
        
        # Verify touchdown score added
        self.controller.game_manager.scoreboard.add_score.assert_called_once_with(1, 6)
    
    def test_handle_drive_transition_field_goal_adds_score(self):
        """Test that field goal drives add correct score"""
        drive_result = Mock(spec=DriveResult)
        drive_result.drive_outcome = DriveEndReason.FIELD_GOAL
        drive_result.possessing_team_id = 2
        
        # Setup GameManager scoreboard mock
        self.controller.game_manager.scoreboard = Mock()
        
        # Handle transition
        self.controller._handle_drive_transition(drive_result)
        
        # Verify field goal score added
        self.controller.game_manager.scoreboard.add_score.assert_called_once_with(2, 3)
    
    def test_handle_drive_transition_punt_no_score(self):
        """Test that punt drives do not add score"""
        drive_result = Mock(spec=DriveResult)
        drive_result.drive_outcome = DriveEndReason.PUNT
        drive_result.possessing_team_id = 1
        
        # Setup GameManager scoreboard mock
        self.controller.game_manager.scoreboard = Mock()
        
        # Handle transition
        self.controller._handle_drive_transition(drive_result)
        
        # Verify no score added
        self.controller.game_manager.scoreboard.add_score.assert_not_called()


class TestResultGeneration:
    """Test final result generation and statistics compilation"""
    
    def setup_method(self):
        """Set up test fixtures"""
        with patch.object(GameLoopController, '_create_coaching_staff_from_config'), \
             patch('src.game_management.game_loop_controller.PlayCaller'):
            
            self.controller = GameLoopController(
                game_manager=Mock(spec=GameManager),
                home_team=Mock(team_id=1, full_name="Detroit Lions"),
                away_team=Mock(team_id=2, full_name="Green Bay Packers"),
                home_coaching_staff_config={},
                away_coaching_staff_config={},
                home_roster=[],
                away_roster=[]
            )
    
    def test_generate_final_result_determines_winner_correctly(self):
        """Test that final result correctly determines the winner"""
        # Setup game state
        mock_game_state = Mock()
        mock_game_state.score = {1: 24, 2: 17}  # Home team wins
        self.controller.game_manager.get_game_state.return_value = mock_game_state
        
        # Setup drive results
        self.controller.drive_results = [Mock(), Mock(), Mock()]
        self.controller.total_plays = 120
        
        # Generate result
        result = self.controller._generate_final_result()
        
        # Verify result structure
        assert isinstance(result, GameResult)
        assert result.home_team == self.controller.home_team
        assert result.away_team == self.controller.away_team
        assert result.final_score == {1: 24, 2: 17}
        assert result.winner == self.controller.home_team  # Home team won
        assert result.total_plays == 120
        assert result.total_drives == 3
    
    def test_generate_final_result_handles_tie_game(self):
        """Test that final result handles tie games correctly"""
        # Setup tied game state
        mock_game_state = Mock()
        mock_game_state.score = {1: 21, 2: 21}  # Tied game
        self.controller.game_manager.get_game_state.return_value = mock_game_state
        
        self.controller.drive_results = []
        self.controller.total_plays = 0
        
        # Generate result
        result = self.controller._generate_final_result()
        
        # Verify tie handling
        assert result.winner is None
        assert result.final_score == {1: 21, 2: 21}


class TestGameStateMonitoring:
    """Test real-time game state monitoring capabilities"""
    
    def setup_method(self):
        """Set up test fixtures"""
        with patch.object(GameLoopController, '_create_coaching_staff_from_config'), \
             patch('src.game_management.game_loop_controller.PlayCaller'):
            
            self.controller = GameLoopController(
                game_manager=Mock(spec=GameManager),
                home_team=Mock(team_id=1),
                away_team=Mock(team_id=2),
                home_coaching_staff_config={},
                away_coaching_staff_config={},
                home_roster=[],
                away_roster=[]
            )
    
    def test_get_current_game_state_returns_complete_state(self):
        """Test that get_current_game_state returns comprehensive state information"""
        # Setup game state
        mock_game_state = Mock()
        mock_game_state.quarter = 2
        mock_game_state.time_remaining = "8:45"
        mock_game_state.score = {1: 14, 2: 10}
        mock_game_state.phase = GamePhase.SECOND_QUARTER
        
        self.controller.game_manager.get_game_state.return_value = mock_game_state
        self.controller.drive_results = [Mock(), Mock()]
        self.controller.total_plays = 45
        
        # Get current state
        state = self.controller.get_current_game_state()
        
        # Verify state structure
        expected_state = {
            "quarter": 2,
            "time_remaining": "8:45",
            "score": {1: 14, 2: 10},
            "phase": "second_quarter",
            "drives_completed": 2,
            "total_plays": 45
        }
        
        assert state == expected_state


class TestDataStructures:
    """Test data structure validation and integrity"""
    
    def test_drive_result_initialization(self):
        """Test DriveResult data structure initialization and defaults"""
        drive_result = DriveResult(
            possessing_team_id=1,
            starting_field_position=25,
            ending_field_position=5,
            drive_outcome=DriveEndReason.TOUCHDOWN
        )
        
        # Verify required fields
        assert drive_result.possessing_team_id == 1
        assert drive_result.starting_field_position == 25
        assert drive_result.ending_field_position == 5
        assert drive_result.drive_outcome == DriveEndReason.TOUCHDOWN
        
        # Verify default values
        assert drive_result.plays == []
        assert drive_result.total_plays == 0
        assert drive_result.total_yards == 0
        assert drive_result.time_elapsed == 0
        assert drive_result.points_scored == 0
    
    def test_game_result_initialization(self):
        """Test GameResult data structure initialization and defaults"""
        home_team = Mock()
        away_team = Mock()
        
        game_result = GameResult(
            home_team=home_team,
            away_team=away_team,
            final_score={1: 21, 2: 14},
            winner=home_team,
            total_plays=150,
            total_drives=20,
            game_duration_minutes=180
        )
        
        # Verify required fields
        assert game_result.home_team == home_team
        assert game_result.away_team == away_team
        assert game_result.final_score == {1: 21, 2: 14}
        assert game_result.winner == home_team
        assert game_result.total_plays == 150
        assert game_result.total_drives == 20
        assert game_result.game_duration_minutes == 180
        
        # Verify default values
        assert game_result.drive_results == []
        assert game_result.final_statistics is None


# Integration test markers for pytest
class TestGameLoopControllerIntegration:
    """Integration tests that require actual dependencies (marked for separate execution)"""
    
    @pytest.mark.integration
    def test_full_game_simulation_integration(self):
        """Integration test for complete game simulation (requires real components)"""
        # This would test with actual GameManager, CoachingStaff, etc.
        # Marked as integration test to run separately from unit tests
        pass


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])