"""
Integration tests for Game State Manager

Tests the complete game state management system coordination between
field position tracking and down situation tracking.
"""

import unittest
from src.play_engine.game_state.game_state_manager import (
    GameState, 
    GameStateManager, 
    GameStateResult
)
from src.play_engine.game_state.field_position import FieldPosition, FieldZone
from src.play_engine.game_state.down_situation import DownState
from src.play_engine.simulation.stats import PlayStatsSummary


class TestGameState(unittest.TestCase):
    """Test GameState data structure"""
    
    def test_game_state_creation(self):
        """Test basic game state creation"""
        field_pos = FieldPosition(25, "Team A", FieldZone.OWN_TERRITORY)
        down_state = DownState(1, 10, 35)
        
        game_state = GameState(
            field_position=field_pos,
            down_state=down_state,
            possessing_team="Team A"
        )
        
        self.assertEqual(game_state.possessing_team, "Team A")
        self.assertEqual(game_state.field_position.yard_line, 25)
        self.assertEqual(game_state.down_state.current_down, 1)
    
    def test_game_state_consistency_correction(self):
        """Test automatic correction of possession team inconsistency"""
        field_pos = FieldPosition(25, "Team B", FieldZone.OWN_TERRITORY)  # Wrong team
        down_state = DownState(1, 10, 35)
        
        game_state = GameState(
            field_position=field_pos,
            down_state=down_state,
            possessing_team="Team A"  # Correct team
        )
        
        # Should auto-correct field position possession
        self.assertEqual(game_state.field_position.possession_team, "Team A")


class TestGameStateManager(unittest.TestCase):
    """Test GameStateManager integration and coordination"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.manager = GameStateManager()
        
        # Standard game state for testing
        self.standard_field_pos = FieldPosition(25, "Team A", FieldZone.OWN_TERRITORY)
        self.standard_down_state = DownState(1, 10, 35)
        self.standard_game_state = GameState(
            field_position=self.standard_field_pos,
            down_state=self.standard_down_state,
            possessing_team="Team A"
        )
    
    def create_play_summary(self, play_type: str, yards_gained: int) -> PlayStatsSummary:
        """Helper to create PlayStatsSummary for testing"""
        return PlayStatsSummary(
            play_type=play_type,
            yards_gained=yards_gained,
            time_elapsed=3.5
        )
    
    def test_normal_play_processing(self):
        """Test processing a normal play that continues the drive"""
        play_summary = self.create_play_summary("run", 6)
        
        result = self.manager.process_play(self.standard_game_state, play_summary)
        
        # Check field result
        self.assertEqual(result.field_result.actual_yards_gained, 6)
        self.assertEqual(result.field_result.new_field_position.yard_line, 31)
        self.assertFalse(result.field_result.is_scored)
        
        # Check down result
        self.assertFalse(result.down_result.first_down_achieved)
        self.assertEqual(result.down_result.new_down_state.current_down, 2)
        self.assertEqual(result.down_result.new_down_state.yards_to_go, 4)  # 10 - 6 = 4
        
        # Check unified result
        self.assertTrue(result.drive_continues)
        self.assertFalse(result.possession_changed)
        self.assertFalse(result.scoring_occurred)
        self.assertFalse(result.drive_ended)
        self.assertIsNotNone(result.new_game_state)
        self.assertEqual(result.new_game_state.field_position.yard_line, 31)
        self.assertEqual(result.new_game_state.down_state.current_down, 2)
    
    def test_first_down_achievement(self):
        """Test play that achieves first down"""
        play_summary = self.create_play_summary("pass", 12)
        
        result = self.manager.process_play(self.standard_game_state, play_summary)
        
        # Should achieve first down and reset
        self.assertTrue(result.down_result.first_down_achieved)
        self.assertEqual(result.down_result.new_down_state.current_down, 1)
        self.assertEqual(result.down_result.new_down_state.yards_to_go, 10)
        self.assertEqual(result.down_result.new_down_state.first_down_line, 47)  # 37 + 10
        
        # Drive should continue
        self.assertTrue(result.drive_continues)
        self.assertTrue(result.is_first_down())
    
    def test_touchdown_play(self):
        """Test the famous 5-yard line + 10-yard pass = touchdown scenario"""
        # Set up red zone scenario
        red_zone_field_pos = FieldPosition(95, "Team A", FieldZone.RED_ZONE)
        red_zone_down_state = DownState(2, 8, 100)  # 2nd and goal
        red_zone_game_state = GameState(red_zone_field_pos, red_zone_down_state, "Team A")
        
        play_summary = self.create_play_summary("pass", 10)
        
        result = self.manager.process_play(red_zone_game_state, play_summary)
        
        # Field tracking: should detect touchdown with adjusted yards
        self.assertEqual(result.field_result.raw_yards_gained, 10)  # Preserve mechanics
        self.assertEqual(result.field_result.actual_yards_gained, 5)  # Field-adjusted
        self.assertTrue(result.field_result.is_scored)
        self.assertEqual(result.field_result.scoring_type, "touchdown")
        self.assertEqual(result.field_result.points_scored, 6)
        
        # Down tracking: should recognize scoring play and end drive
        self.assertIsNone(result.down_result.new_down_state)  # Drive ended
        
        # Unified result: should indicate scoring and drive end
        self.assertTrue(result.scoring_occurred)
        self.assertTrue(result.drive_ended)
        self.assertFalse(result.drive_continues)
        self.assertEqual(result.get_points_scored(), 6)
        self.assertEqual(result.get_actual_yards_gained(), 5)
        self.assertIsNone(result.new_game_state)  # Drive over
    
    def test_turnover_on_downs(self):
        """Test failed 4th down conversion"""
        fourth_down_field_pos = FieldPosition(45, "Team A", FieldZone.OWN_TERRITORY)
        fourth_down_state = DownState(4, 3, 48)
        fourth_down_game_state = GameState(fourth_down_field_pos, fourth_down_state, "Team A")
        
        play_summary = self.create_play_summary("run", 2)  # Not enough yards
        
        result = self.manager.process_play(fourth_down_game_state, play_summary)
        
        # Should result in turnover on downs
        self.assertTrue(result.down_result.turnover_on_downs)
        self.assertTrue(result.down_result.possession_change)
        self.assertIsNone(result.down_result.new_down_state)
        
        # Drive should end with possession change
        self.assertTrue(result.possession_changed)
        self.assertTrue(result.drive_ended)
        self.assertFalse(result.drive_continues)
        self.assertTrue(result.is_turnover_on_downs())
        self.assertIsNone(result.new_game_state)
    
    def test_safety_scenario(self):
        """Test safety from own goal line"""
        own_goal_field_pos = FieldPosition(2, "Team A", FieldZone.OWN_GOAL_LINE)
        own_goal_down_state = DownState(3, 8, 10)
        own_goal_game_state = GameState(own_goal_field_pos, own_goal_down_state, "Team A")
        
        play_summary = self.create_play_summary("pass", -5)  # Sack in end zone
        
        result = self.manager.process_play(own_goal_game_state, play_summary)
        
        # Should detect safety
        self.assertTrue(result.field_result.is_scored)
        self.assertEqual(result.field_result.scoring_type, "safety")
        self.assertEqual(result.field_result.points_scored, 2)
        self.assertEqual(result.field_result.new_field_position.yard_line, 0)
        
        # Should end drive due to scoring
        self.assertTrue(result.scoring_occurred)
        self.assertTrue(result.drive_ended)
        self.assertEqual(result.get_points_scored(), 2)
    
    def test_long_gain_with_first_down(self):
        """Test very long gain that gets first down with yards to spare"""
        play_summary = self.create_play_summary("run", 45)
        
        result = self.manager.process_play(self.standard_game_state, play_summary)
        
        # Should move ball and achieve first down
        self.assertEqual(result.field_result.new_field_position.yard_line, 70)
        self.assertTrue(result.down_result.first_down_achieved)
        self.assertEqual(result.down_result.yards_past_first_down, 35)  # 45 - 10 = 35
        
        # Should enter opponent territory
        self.assertEqual(result.new_game_state.field_position.field_zone, FieldZone.OPPONENT_TERRITORY)
    
    def test_negative_yardage_coordination(self):
        """Test coordination between field and down tracking with negative yards"""
        play_summary = self.create_play_summary("pass", -8)  # Sack
        
        result = self.manager.process_play(self.standard_game_state, play_summary)
        
        # Field should move backward
        self.assertEqual(result.field_result.new_field_position.yard_line, 17)
        
        # Down should advance with increased yards to go
        self.assertEqual(result.down_result.new_down_state.current_down, 2)
        self.assertEqual(result.down_result.new_down_state.yards_to_go, 18)  # 10 + 8 = 18
        self.assertEqual(result.down_result.new_down_state.first_down_line, 35)  # Unchanged
    
    def test_process_turnover_fumble(self):
        """Test turnover processing (fumble)"""
        result = self.manager.process_turnover(self.standard_game_state, "fumble", "Team B")
        
        # Should flip field position (25 becomes 75 for other team)
        self.assertEqual(result.field_result.new_field_position.yard_line, 75)
        self.assertEqual(result.field_result.new_field_position.possession_team, "Team B")
        
        # Should create new drive for recovering team
        self.assertEqual(result.new_game_state.down_state.current_down, 1)
        self.assertEqual(result.new_game_state.down_state.yards_to_go, 10)
        self.assertEqual(result.new_game_state.possessing_team, "Team B")
        
        # Should indicate possession change
        self.assertTrue(result.possession_changed)
        self.assertTrue(result.drive_ended)
        self.assertIn("fumble", result.all_game_events)
    
    def test_create_new_drive(self):
        """Test creating a new drive (e.g., after kickoff)"""
        new_game_state = self.manager.create_new_drive(30, "Team B")
        
        self.assertEqual(new_game_state.field_position.yard_line, 30)
        self.assertEqual(new_game_state.possessing_team, "Team B")
        self.assertEqual(new_game_state.down_state.current_down, 1)
        self.assertEqual(new_game_state.down_state.yards_to_go, 10)
        self.assertEqual(new_game_state.down_state.first_down_line, 40)
    
    def test_game_state_result_utility_methods(self):
        """Test GameStateResult utility methods"""
        play_summary = self.create_play_summary("run", 6)
        result = self.manager.process_play(self.standard_game_state, play_summary)
        
        # Test utility methods
        self.assertEqual(result.get_actual_yards_gained(), 6)
        self.assertEqual(result.get_points_scored(), 0)
        self.assertFalse(result.is_first_down())
        self.assertFalse(result.is_turnover_on_downs())
        
        # Test combined events
        self.assertIsInstance(result.all_game_events, list)
        self.assertTrue(len(result.all_game_events) > 0)  # Should have down progression event


class TestGameStateManagerComplexScenarios(unittest.TestCase):
    """Test complex multi-play scenarios"""
    
    def setUp(self):
        self.manager = GameStateManager()
    
    def test_complete_drive_sequence(self):
        """Test a complete drive from start to touchdown"""
        # Start drive at own 20
        game_state = self.manager.create_new_drive(20, "Team A")
        self.assertEqual(game_state.field_position.yard_line, 20)
        
        # 1st and 10: 8-yard run
        play1 = PlayStatsSummary("run", 8, 4.0)
        result1 = self.manager.process_play(game_state, play1)
        self.assertEqual(result1.new_game_state.field_position.yard_line, 28)
        self.assertEqual(result1.new_game_state.down_state.current_down, 2)
        self.assertEqual(result1.new_game_state.down_state.yards_to_go, 2)
        
        # 2nd and 2: 15-yard pass (first down)
        play2 = PlayStatsSummary("pass", 15, 6.0)
        result2 = self.manager.process_play(result1.new_game_state, play2)
        self.assertTrue(result2.is_first_down())
        self.assertEqual(result2.new_game_state.field_position.yard_line, 43)
        self.assertEqual(result2.new_game_state.down_state.current_down, 1)
        
        # Continue drive to red zone
        red_zone_state = GameState(
            FieldPosition(92, "Team A", FieldZone.RED_ZONE),
            DownState(1, 10, 100),
            "Team A"
        )
        
        # 1st and goal: 8-yard touchdown pass
        td_play = PlayStatsSummary("pass", 15, 5.0)  # 15 yards but only 8 to goal
        td_result = self.manager.process_play(red_zone_state, td_play)
        
        self.assertTrue(td_result.scoring_occurred)
        self.assertEqual(td_result.get_actual_yards_gained(), 8)  # Field-constrained
        self.assertEqual(td_result.get_points_scored(), 6)
        self.assertIsNone(td_result.new_game_state)  # Drive over
    
    def test_fourth_down_scenarios(self):
        """Test various 4th down scenarios"""
        fourth_down_state = GameState(
            FieldPosition(55, "Team A", FieldZone.OPPONENT_TERRITORY),
            DownState(4, 2, 57),
            "Team A"
        )
        
        # Successful conversion
        conversion_play = PlayStatsSummary("run", 3, 3.0)
        conversion_result = self.manager.process_play(fourth_down_state, conversion_play)
        self.assertTrue(conversion_result.is_first_down())
        self.assertTrue(conversion_result.drive_continues)
        
        # Failed conversion
        failed_play = PlayStatsSummary("pass", 1, 4.0)
        failed_result = self.manager.process_play(fourth_down_state, failed_play)
        self.assertTrue(failed_result.is_turnover_on_downs())
        self.assertTrue(failed_result.possession_changed)
        self.assertIsNone(failed_result.new_game_state)


if __name__ == '__main__':
    unittest.main()