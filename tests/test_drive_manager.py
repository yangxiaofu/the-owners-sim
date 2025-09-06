"""
Comprehensive DriveManager Tests

Tests the DriveManager system with DriveManagerParams approach including:
- Parameter validation and fail-fast behavior
- Context-dependent drive decision making 
- Drive ending conditions and edge cases
- Multi-play drive progression
- Statistical accumulation
"""

import unittest
from unittest.mock import Mock, MagicMock
from typing import Optional, List
from dataclasses import dataclass

# Import DriveManager components
from src.play_engine.game_state.drive_manager import (
    DriveManager, DriveManagerParams, DriveAssessmentResult, Drive,
    DriveEndReason, DriveStatus, GameClock, ScoreContext, DriveStats,
    DriveManagerError
)

# Import existing game state components for building test data
from src.play_engine.game_state.game_state_manager import GameStateResult, GameState
from src.play_engine.game_state.field_position import FieldPosition, FieldZone, FieldResult
from src.play_engine.game_state.down_situation import DownState, DownProgressionResult, DownResult
from src.play_engine.simulation.stats import PlayStatsSummary, PlayerStats


class DriveManagerParamsBuilder:
    """
    Builder pattern for creating DriveManagerParams with systematic variation
    for comprehensive testing scenarios.
    """
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        """Reset to default valid parameters"""
        # Default play stats
        self._play_stats = PlayStatsSummary(
            play_type="RUN",
            yards_gained=5,
            time_elapsed=30.0
        )
        
        # Default field result
        self._field_result = FieldResult(
            raw_yards_gained=5,
            actual_yards_gained=5,
            new_field_position=FieldPosition(40, "Lions", FieldZone.MIDFIELD),
            is_scored=False,
            scoring_type=None,
            points_scored=0,
            field_events=[],
            possession_change=False
        )
        
        # Default down result  
        self._down_result = DownProgressionResult(
            new_down_state=DownState(1, 5, 45),
            down_result=DownResult.CONTINUE_DRIVE,
            first_down_achieved=False,
            yards_past_first_down=0,
            possession_change=False,
            turnover_on_downs=False,
            down_events=[]
        )
        
        # Default game state
        self._new_game_state = GameState(
            field_position=FieldPosition(40, "Lions", FieldZone.MIDFIELD),
            down_state=DownState(1, 5, 40),
            possessing_team="Lions"
        )
        
        # Default game context
        self._quarter = 2
        self._time_remaining = 450  # 7:30
        self._home_score = 14
        self._away_score = 10
        self._possessing_team_is_home = True
        self._field_position = 40
        self._possessing_team = "Lions"
        
        return self
    
    def with_play_result(self, yards: int, outcome: str = "run", 
                        scoring: bool = False, points: int = 0,
                        turnover: bool = False, possession_change: bool = False) -> 'DriveManagerParamsBuilder':
        """Configure the play result parameters"""
        self._play_stats.yards_gained = yards
        self._play_stats.play_type = outcome
        
        # Update field result
        new_pos = max(0, min(100, self._field_position + yards))
        self._field_result.raw_yards_gained = yards
        self._field_result.actual_yards_gained = yards
        self._field_result.new_field_position = FieldPosition(new_pos, self._possessing_team, FieldZone.MIDFIELD)
        self._field_result.points_scored = points
        self._field_result.is_scored = scoring
        self._field_result.possession_change = possession_change or turnover
        
        # Update down result
        if turnover:
            self._down_result.turnover_on_downs = True
            self._down_result.possession_change = True
            self._down_result.down_result = DownResult.TURNOVER_ON_DOWNS
        elif scoring:
            self._down_result.down_result = DownResult.SCORING_DRIVE
        else:
            self._down_result.down_result = DownResult.CONTINUE_DRIVE
        
        # Update game state accordingly
        self._new_game_state.field_position = FieldPosition(new_pos, self._possessing_team, FieldZone.MIDFIELD)
        self._field_position = new_pos
        
        return self
    
    def with_game_context(self, quarter: int, time_remaining: int) -> 'DriveManagerParamsBuilder':
        """Configure game timing context"""
        self._quarter = quarter
        self._time_remaining = time_remaining
        return self
    
    def with_score_context(self, home_score: int, away_score: int, 
                          possessing_team_is_home: bool = True) -> 'DriveManagerParamsBuilder':
        """Configure scoring context"""
        self._home_score = home_score
        self._away_score = away_score
        self._possessing_team_is_home = possessing_team_is_home
        return self
    
    def with_field_context(self, field_position: int, possessing_team: str = "Lions") -> 'DriveManagerParamsBuilder':
        """Configure field position context"""
        self._field_position = field_position
        self._possessing_team = possessing_team
        
        # Update all related objects
        new_pos = max(0, min(100, field_position + self._field_result.raw_yards_gained))
        self._field_result.new_field_position = FieldPosition(new_pos, possessing_team, FieldZone.MIDFIELD)
        self._new_game_state.field_position = FieldPosition(new_pos, possessing_team, FieldZone.MIDFIELD)
        self._new_game_state.possessing_team = possessing_team
        return self
    
    def with_touchdown(self) -> 'DriveManagerParamsBuilder':
        """Configure a touchdown play"""
        return self.with_play_result(
            yards=self._calculate_td_yards(),
            outcome="PASS_TD", 
            scoring=True, 
            points=6,
            possession_change=True
        )
    
    def with_field_goal(self) -> 'DriveManagerParamsBuilder':
        """Configure a field goal play"""
        return self.with_play_result(
            yards=0,
            outcome="FIELD_GOAL", 
            scoring=True, 
            points=3,
            possession_change=True
        )
    
    def with_interception(self) -> 'DriveManagerParamsBuilder':
        """Configure an interception play"""
        return self.with_play_result(
            yards=0,
            outcome="INTERCEPTION",
            turnover=True,
            possession_change=True
        )
    
    def with_punt(self) -> 'DriveManagerParamsBuilder':
        """Configure a punt play"""
        return self.with_play_result(
            yards=0,
            outcome="PUNT",
            possession_change=True
        )
    
    def with_turnover_on_downs(self) -> 'DriveManagerParamsBuilder':
        """Configure a turnover on downs"""
        self._down_result.starting_down = 4
        self._down_result.ending_down = 1  # Possession change resets downs
        self._down_result.turnover_on_downs = True
        return self.with_play_result(
            yards=-2,
            outcome="FAILED_4TH_DOWN",
            turnover=True,
            possession_change=True
        )
    
    def with_safety(self) -> 'DriveManagerParamsBuilder':
        """Configure a safety play"""
        return self.with_play_result(
            yards=-2,
            outcome="SAFETY",
            scoring=True,
            points=2
        ).with_field_context(2)  # In own end zone
    
    def with_missing_play_result(self) -> 'DriveManagerParamsBuilder':
        """Remove play result to test validation"""
        self._play_stats = None
        return self
    
    def with_invalid_quarter(self, quarter: int) -> 'DriveManagerParamsBuilder':
        """Set invalid quarter for validation testing"""
        self._quarter = quarter
        return self
    
    def with_invalid_time(self, time_remaining: int) -> 'DriveManagerParamsBuilder':
        """Set invalid time for validation testing"""
        self._time_remaining = time_remaining
        return self
    
    def with_invalid_field_position(self, position: int) -> 'DriveManagerParamsBuilder':
        """Set invalid field position for validation testing"""
        self._field_position = position
        # Force the game state field position to trigger validation error
        self._new_game_state.field_position = FieldPosition(position, self._possessing_team, FieldZone.MIDFIELD)
        return self
    
    def _calculate_td_yards(self) -> int:
        """Calculate yards needed for touchdown from current field position"""
        opponent_goal_line = 100 - self._field_position
        return opponent_goal_line
    
    def build(self) -> DriveManagerParams:
        """Build the DriveManagerParams object"""
        # Create GameStateResult
        if self._play_stats is None:
            raise ValueError("Cannot build without play stats")
        
        # Calculate game state flags
        scoring_occurred = self._field_result.is_scored
        possession_changed = self._field_result.possession_change or self._down_result.possession_change
        drive_ended = possession_changed or scoring_occurred
        drive_continues = not drive_ended
        
        # Combine events
        all_events = self._field_result.field_events + self._down_result.down_events
        
        game_state_result = GameStateResult(
            play_summary=self._play_stats,
            field_result=self._field_result,
            down_result=self._down_result,
            new_game_state=self._new_game_state,
            drive_continues=drive_continues,
            possession_changed=possession_changed,
            scoring_occurred=scoring_occurred,
            drive_ended=drive_ended,
            all_game_events=all_events
        )
        
        # Create timing context
        game_clock = GameClock(
            quarter=self._quarter,
            time_remaining_seconds=self._time_remaining
        )
        
        # Create score context
        score_context = ScoreContext(
            home_score=self._home_score,
            away_score=self._away_score,
            possessing_team_is_home=self._possessing_team_is_home
        )
        
        # Build final params - use field position from game state as authoritative
        final_field_position = self._new_game_state.field_position.yard_line
        
        return DriveManagerParams(
            game_state_result=game_state_result,
            game_clock=game_clock,
            score_context=score_context,
            field_position=final_field_position,
            possessing_team=self._possessing_team
        )


class TestDriveManagerParamsValidation(unittest.TestCase):
    """Test parameter validation and fail-fast behavior"""
    
    def setUp(self):
        self.builder = DriveManagerParamsBuilder()
    
    def test_valid_params_creation(self):
        """Test that valid parameters create successfully"""
        params = self.builder.build()
        
        self.assertIsNotNone(params)
        self.assertEqual(params.possessing_team, "Lions")
        self.assertEqual(params.field_position, 40)
        self.assertEqual(params.game_clock.quarter, 2)
    
    def test_missing_game_state_result_fails(self):
        """Test that missing game state result throws error"""
        with self.assertRaises(ValueError) as context:
            self.builder.with_missing_play_result().build()
        
        self.assertIn("Cannot build without play stats", str(context.exception))
    
    def test_invalid_quarter_fails(self):
        """Test that invalid quarter throws error"""
        with self.assertRaises(ValueError) as context:
            self.builder.with_invalid_quarter(0).build()
        
        self.assertIn("Invalid quarter: 0", str(context.exception))
    
    def test_negative_time_fails(self):
        """Test that negative time throws error"""
        with self.assertRaises(ValueError) as context:
            self.builder.with_invalid_time(-5).build()
        
        self.assertIn("Invalid time_remaining: -5", str(context.exception))
    
    def test_invalid_field_position_fails(self):
        """Test that invalid field position throws error"""
        with self.assertRaises(ValueError) as context:
            self.builder.with_invalid_field_position(101).build()
        
        # The error should come from FieldPosition validation
        self.assertIn("Invalid yard_line: 101", str(context.exception))
    
    def test_negative_scores_fail(self):
        """Test that negative scores throw error"""
        with self.assertRaises(ValueError) as context:
            self.builder.with_score_context(-1, 10).build()
        
        self.assertIn("Invalid home_score: -1", str(context.exception))


class TestDriveManagerCore(unittest.TestCase):
    """Test core DriveManager functionality"""
    
    def setUp(self):
        self.drive_manager = DriveManager()
        self.builder = DriveManagerParamsBuilder()
    
    def test_drive_manager_initialization(self):
        """Test DriveManager starts with no active drive"""
        self.assertIsNone(self.drive_manager.get_current_drive())
        self.assertEqual(len(self.drive_manager.get_drive_history()), 0)
        self.assertFalse(self.drive_manager.has_active_drive())
    
    def test_start_new_drive(self):
        """Test starting a new drive"""
        drive = self.drive_manager.start_new_drive(25, "Lions", 1, 900)
        
        self.assertIsNotNone(drive)
        self.assertEqual(drive.possessing_team, "Lions")
        self.assertEqual(drive.starting_position, 25)
        self.assertEqual(drive.drive_number, 1)
        self.assertTrue(self.drive_manager.has_active_drive())
    
    def test_cannot_start_drive_while_active(self):
        """Test that starting a new drive while one is active fails"""
        self.drive_manager.start_new_drive(25, "Lions", 1, 900)
        
        with self.assertRaises(DriveManagerError):
            self.drive_manager.start_new_drive(30, "Packers", 1, 870)
    
    def test_assess_without_active_drive_fails(self):
        """Test that assessing without an active drive fails"""
        params = self.builder.build()
        
        with self.assertRaises(DriveManagerError):
            self.drive_manager.assess_drive_status(params)


class TestDriveEndingDecisions(unittest.TestCase):
    """Test drive ending decision logic based on context"""
    
    def setUp(self):
        self.drive_manager = DriveManager()
        self.builder = DriveManagerParamsBuilder()
        # Start a drive for testing
        self.drive_manager.start_new_drive(25, "Lions", 2, 450)
    
    def test_touchdown_ends_drive(self):
        """Test that touchdown ends drive"""
        params = self.builder.with_touchdown().build()
        result = self.drive_manager.assess_drive_status(params)
        
        self.assertTrue(result.is_drive_ended)
        self.assertEqual(result.end_reason, DriveEndReason.TOUCHDOWN)
        self.assertIsNotNone(result.next_possession_team)
        self.assertFalse(self.drive_manager.has_active_drive())
    
    def test_field_goal_ends_drive(self):
        """Test that field goal ends drive"""
        params = self.builder.with_field_goal().build()
        result = self.drive_manager.assess_drive_status(params)
        
        self.assertTrue(result.is_drive_ended)
        self.assertEqual(result.end_reason, DriveEndReason.FIELD_GOAL)
        self.assertIsNotNone(result.next_possession_team)
    
    def test_interception_ends_drive(self):
        """Test that interception ends drive"""
        params = self.builder.with_interception().build()
        result = self.drive_manager.assess_drive_status(params)
        
        self.assertTrue(result.is_drive_ended)
        self.assertEqual(result.end_reason, DriveEndReason.TURNOVER_INTERCEPTION)
        self.assertIsNotNone(result.next_possession_team)
    
    def test_turnover_on_downs_ends_drive(self):
        """Test that turnover on downs ends drive"""
        params = self.builder.with_turnover_on_downs().build()
        result = self.drive_manager.assess_drive_status(params)
        
        self.assertTrue(result.is_drive_ended)
        self.assertEqual(result.end_reason, DriveEndReason.TURNOVER_ON_DOWNS)
    
    def test_punt_ends_drive(self):
        """Test that punt ends drive"""
        params = self.builder.with_punt().build()
        result = self.drive_manager.assess_drive_status(params)
        
        self.assertTrue(result.is_drive_ended)
        self.assertEqual(result.end_reason, DriveEndReason.PUNT)
    
    def test_safety_ends_drive(self):
        """Test that safety ends drive"""
        params = self.builder.with_safety().build()
        result = self.drive_manager.assess_drive_status(params)
        
        self.assertTrue(result.is_drive_ended)
        self.assertEqual(result.end_reason, DriveEndReason.SAFETY)
    
    def test_normal_play_continues_drive(self):
        """Test that normal play continues drive"""
        params = self.builder.with_play_result(yards=7, outcome="RUN").build()
        result = self.drive_manager.assess_drive_status(params)
        
        self.assertFalse(result.is_drive_ended)
        self.assertEqual(result.drive_status, DriveStatus.ACTIVE)
        self.assertIsNone(result.end_reason)
        self.assertTrue(self.drive_manager.has_active_drive())


class TestContextDependentDecisions(unittest.TestCase):
    """Test that same play results in different decisions based on context"""
    
    def setUp(self):
        self.drive_manager = DriveManager()
        self.builder = DriveManagerParamsBuilder()
    
    def test_failed_4th_down_different_contexts(self):
        """Test failed 4th down in different game time contexts"""
        
        # Context A: Mid-game - drive ends with turnover
        self.drive_manager.start_new_drive(30, "Lions", 2, 450)  # Q2, 7:30 remaining
        
        params_mid_game = (self.builder
                          .with_turnover_on_downs()
                          .with_game_context(2, 450)
                          .build())
        
        result_mid_game = self.drive_manager.assess_drive_status(params_mid_game)
        
        self.assertTrue(result_mid_game.is_drive_ended)
        self.assertEqual(result_mid_game.end_reason, DriveEndReason.TURNOVER_ON_DOWNS)
        self.assertFalse(result_mid_game.requires_game_end)
        self.assertFalse(result_mid_game.requires_half_end)
        
        # Context B: End of game - drive and game end
        self.drive_manager.start_new_drive(30, "Lions", 4, 0)  # Q4, 0:00 remaining
        
        params_game_end = (self.builder
                          .reset()
                          .with_turnover_on_downs()
                          .with_game_context(4, 0)  # End of game
                          .build())
        
        result_game_end = self.drive_manager.assess_drive_status(params_game_end)
        
        self.assertTrue(result_game_end.is_drive_ended)
        self.assertEqual(result_game_end.end_reason, DriveEndReason.END_OF_GAME)
        self.assertTrue(result_game_end.requires_game_end)
        
        # Context C: End of half - drive and half end
        self.drive_manager.start_new_drive(30, "Lions", 2, 0)  # Q2, 0:00 remaining
        
        params_half_end = (self.builder
                          .reset()
                          .with_turnover_on_downs()
                          .with_game_context(2, 0)  # End of half
                          .build())
        
        result_half_end = self.drive_manager.assess_drive_status(params_half_end)
        
        self.assertTrue(result_half_end.is_drive_ended)
        self.assertEqual(result_half_end.end_reason, DriveEndReason.END_OF_HALF)
        self.assertTrue(result_half_end.requires_half_end)
    
    def test_touchdown_different_time_contexts(self):
        """Test touchdown in different time contexts"""
        
        # Regular time touchdown
        self.drive_manager.start_new_drive(25, "Lions", 3, 300)
        params_regular = self.builder.with_touchdown().build()
        result_regular = self.drive_manager.assess_drive_status(params_regular)
        
        self.assertEqual(result_regular.end_reason, DriveEndReason.TOUCHDOWN)
        self.assertFalse(result_regular.requires_game_end)
        
        # Game-winning touchdown as time expires
        self.drive_manager.start_new_drive(25, "Lions", 4, 0)
        params_game_winner = (self.builder
                             .reset()
                             .with_touchdown()
                             .with_game_context(4, 0)
                             .build())
        result_game_winner = self.drive_manager.assess_drive_status(params_game_winner)
        
        self.assertEqual(result_game_winner.end_reason, DriveEndReason.END_OF_GAME)
        self.assertTrue(result_game_winner.requires_game_end)


class TestMultiPlayDriveProgression(unittest.TestCase):
    """Test drive statistics accumulation across multiple plays"""
    
    def setUp(self):
        self.drive_manager = DriveManager()
        self.builder = DriveManagerParamsBuilder()
        self.drive_manager.start_new_drive(25, "Lions", 1, 900)
    
    def test_multi_play_drive_statistics(self):
        """Test statistics accumulation across multiple plays"""
        
        # Play 1: 5-yard run
        params1 = self.builder.with_play_result(5, "RUN").build()
        result1 = self.drive_manager.assess_drive_status(params1)
        
        self.assertFalse(result1.is_drive_ended)
        self.assertEqual(result1.drive_stats.plays_run, 1)
        self.assertEqual(result1.drive_stats.total_yards, 5)
        self.assertEqual(result1.drive_stats.rushing_yards, 5)
        self.assertEqual(result1.drive_stats.passing_yards, 0)
        
        # Play 2: 12-yard pass (first down)
        params2 = (self.builder
                   .reset()
                   .with_play_result(12, "PASS")
                   .with_field_context(30)  # New field position
                   .build())
        result2 = self.drive_manager.assess_drive_status(params2)
        
        self.assertFalse(result2.is_drive_ended)
        self.assertEqual(result2.drive_stats.plays_run, 2)
        self.assertEqual(result2.drive_stats.total_yards, 17)  # 5 + 12
        self.assertEqual(result2.drive_stats.rushing_yards, 5)
        self.assertEqual(result2.drive_stats.passing_yards, 12)
        
        # Play 3: Touchdown pass
        params3 = (self.builder
                   .reset()
                   .with_touchdown()
                   .with_field_context(42)
                   .build())
        result3 = self.drive_manager.assess_drive_status(params3)
        
        self.assertTrue(result3.is_drive_ended)
        self.assertEqual(result3.drive_stats.plays_run, 3)
        self.assertTrue(result3.drive_stats.total_yards > 17)  # Includes TD yards
        
        # Verify drive is in history
        history = self.drive_manager.get_drive_history()
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0].stats.plays_run, 3)


class TestEdgeCasesAndBoundaryValues(unittest.TestCase):
    """Test edge cases and boundary value scenarios"""
    
    def setUp(self):
        self.drive_manager = DriveManager()
        self.builder = DriveManagerParamsBuilder()
    
    def test_boundary_field_positions(self):
        """Test drives at field boundary positions"""
        
        # Drive starting at own 1-yard line
        self.drive_manager.start_new_drive(1, "Lions", 2, 600)
        params_own_goal = (self.builder
                          .with_field_context(1)
                          .with_play_result(-2, "RUN")  # Goes into end zone
                          .with_safety()
                          .build())
        
        result_safety = self.drive_manager.assess_drive_status(params_own_goal)
        self.assertTrue(result_safety.is_drive_ended)
        self.assertEqual(result_safety.end_reason, DriveEndReason.SAFETY)
        
        # Drive at opponent 1-yard line
        self.drive_manager.start_new_drive(99, "Lions", 3, 400)
        params_red_zone = (self.builder
                          .reset()
                          .with_field_context(99)
                          .with_touchdown()
                          .build())
        
        result_td = self.drive_manager.assess_drive_status(params_red_zone)
        self.assertTrue(result_td.is_drive_ended)
        self.assertEqual(result_td.end_reason, DriveEndReason.TOUCHDOWN)
    
    def test_time_boundary_conditions(self):
        """Test time-based boundary conditions"""
        
        # 0:01 remaining vs 0:00 remaining
        self.drive_manager.start_new_drive(50, "Lions", 4, 1)  # 1 second left
        params_last_second = (self.builder
                             .with_game_context(4, 1)
                             .with_play_result(3, "RUN")
                             .build())
        
        result_last_second = self.drive_manager.assess_drive_status(params_last_second)
        self.assertFalse(result_last_second.is_drive_ended)  # Game hasn't ended yet
        
        # 0:00 remaining - game ends
        # Use a separate drive manager instance for the 0:00 test
        drive_manager_2 = DriveManager()
        drive_manager_2.start_new_drive(50, "Lions", 4, 0)  # No time left
        params_no_time = (self.builder
                         .reset()
                         .with_game_context(4, 0)
                         .with_play_result(3, "RUN")
                         .build())
        
        result_no_time = drive_manager_2.assess_drive_status(params_no_time)
        self.assertTrue(result_no_time.is_drive_ended)
        self.assertEqual(result_no_time.end_reason, DriveEndReason.END_OF_GAME)
    
    def test_score_differential_impact(self):
        """Test how score differential affects context"""
        
        # Test with different score situations
        score_scenarios = [
            (0, 0, "tied game"),
            (21, 20, "leading by 1"),
            (14, 28, "trailing by 14"),
            (35, 7, "blowout lead")
        ]
        
        for home_score, away_score, description in score_scenarios:
            with self.subTest(scenario=description):
                self.drive_manager = DriveManager()  # Reset for each scenario
                self.drive_manager.start_new_drive(30, "Lions", 4, 120)
                
                params = (self.builder
                         .reset()
                         .with_score_context(home_score, away_score)
                         .with_game_context(4, 120)  # 2:00 remaining
                         .with_play_result(5, "RUN")
                         .build())
                
                result = self.drive_manager.assess_drive_status(params)
                
                # Score differential should be available in context
                expected_diff = home_score - away_score
                self.assertEqual(params.score_context.score_differential, expected_diff)
                
                # Drive should continue for normal plays regardless of score
                self.assertFalse(result.is_drive_ended)
    
    def test_overtime_scenarios(self):
        """Test overtime game scenarios"""
        
        self.drive_manager.start_new_drive(25, "Lions", 5, 900)  # Overtime
        
        params_ot_td = (self.builder
                       .with_game_context(5, 300)  # 5th quarter (OT)
                       .with_touchdown()
                       .build())
        
        result_ot_td = self.drive_manager.assess_drive_status(params_ot_td)
        
        self.assertTrue(result_ot_td.is_drive_ended)
        self.assertEqual(result_ot_td.end_reason, DriveEndReason.TOUCHDOWN)
        self.assertTrue(params_ot_td.game_clock.is_overtime)


if __name__ == '__main__':
    # Run all tests
    unittest.main(verbosity=2)