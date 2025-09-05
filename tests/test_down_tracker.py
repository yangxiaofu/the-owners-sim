"""
Unit tests for Down Situation Tracking System

Tests down progression, first down detection, and turnover logic
in isolation from field position tracking.
"""

import unittest
from src.play_engine.game_state.down_situation import (
    DownState, 
    DownTracker, 
    DownProgressionResult, 
    DownResult
)


class TestDownState(unittest.TestCase):
    """Test DownState data structure and validation"""
    
    def test_down_state_creation(self):
        """Test basic down state creation"""
        down_state = DownState(
            current_down=1,
            yards_to_go=10,
            first_down_line=35
        )
        self.assertEqual(down_state.current_down, 1)
        self.assertEqual(down_state.yards_to_go, 10)
        self.assertEqual(down_state.first_down_line, 35)
    
    def test_down_state_validation(self):
        """Test down state validation for invalid values"""
        # Invalid down number
        with self.assertRaises(ValueError):
            DownState(current_down=0, yards_to_go=10, first_down_line=35)
        
        with self.assertRaises(ValueError):
            DownState(current_down=5, yards_to_go=10, first_down_line=35)
        
        # Invalid yards to go
        with self.assertRaises(ValueError):
            DownState(current_down=1, yards_to_go=0, first_down_line=35)
        
        # Invalid first down line
        with self.assertRaises(ValueError):
            DownState(current_down=1, yards_to_go=10, first_down_line=101)
    
    def test_down_state_utility_methods(self):
        """Test utility methods for down analysis"""
        # First down
        first_down = DownState(current_down=1, yards_to_go=10, first_down_line=35)
        self.assertTrue(first_down.is_first_down())
        self.assertFalse(first_down.is_fourth_down())
        
        # Fourth down
        fourth_down = DownState(current_down=4, yards_to_go=2, first_down_line=35)
        self.assertFalse(fourth_down.is_first_down())
        self.assertTrue(fourth_down.is_fourth_down())
        
        # Short yardage
        short_yardage = DownState(current_down=2, yards_to_go=2, first_down_line=35)
        self.assertTrue(short_yardage.is_short_yardage())
        self.assertFalse(short_yardage.is_long_yardage())
        
        # Long yardage
        long_yardage = DownState(current_down=2, yards_to_go=15, first_down_line=35)
        self.assertFalse(long_yardage.is_short_yardage())
        self.assertTrue(long_yardage.is_long_yardage())


class TestDownTracker(unittest.TestCase):
    """Test DownTracker down progression logic"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.tracker = DownTracker()
    
    def test_first_down_achieved(self):
        """Test first down achievement resets to 1st and 10"""
        down_state = DownState(current_down=3, yards_to_go=5, first_down_line=30)
        
        result = self.tracker.process_play(down_state, yards_gained=8, new_field_position=33)
        
        self.assertEqual(result.down_result, DownResult.FIRST_DOWN_ACHIEVED)
        self.assertTrue(result.first_down_achieved)
        self.assertEqual(result.yards_past_first_down, 3)  # 8 - 5 = 3 extra yards
        self.assertEqual(result.new_down_state.current_down, 1)
        self.assertEqual(result.new_down_state.yards_to_go, 10)
        self.assertEqual(result.new_down_state.first_down_line, 43)  # 33 + 10
        self.assertIn("first_down_achieved", result.down_events)
    
    def test_exact_first_down(self):
        """Test achieving exactly the yards needed for first down"""
        down_state = DownState(current_down=2, yards_to_go=7, first_down_line=30)
        
        result = self.tracker.process_play(down_state, yards_gained=7, new_field_position=30)
        
        self.assertTrue(result.first_down_achieved)
        self.assertEqual(result.yards_past_first_down, 0)
        self.assertEqual(result.new_down_state.current_down, 1)
        self.assertEqual(result.new_down_state.yards_to_go, 10)
    
    def test_first_down_near_goal_line(self):
        """Test first down achievement near goal line (less than 10 yards to go)"""
        down_state = DownState(current_down=2, yards_to_go=5, first_down_line=95)
        
        result = self.tracker.process_play(down_state, yards_gained=7, new_field_position=97)
        
        self.assertTrue(result.first_down_achieved)
        self.assertEqual(result.new_down_state.current_down, 1)
        self.assertEqual(result.new_down_state.yards_to_go, 3)  # Only 3 yards to goal
        self.assertEqual(result.new_down_state.first_down_line, 100)  # Capped at goal line
    
    def test_down_progression_no_first_down(self):
        """Test normal down progression when first down not achieved"""
        down_state = DownState(current_down=1, yards_to_go=10, first_down_line=35)
        
        result = self.tracker.process_play(down_state, yards_gained=4, new_field_position=29)
        
        self.assertEqual(result.down_result, DownResult.CONTINUE_DRIVE)
        self.assertFalse(result.first_down_achieved)
        self.assertEqual(result.new_down_state.current_down, 2)
        self.assertEqual(result.new_down_state.yards_to_go, 6)  # 10 - 4 = 6
        self.assertEqual(result.new_down_state.first_down_line, 35)  # Unchanged
        self.assertIn("advance_to_2nd_down", result.down_events)
    
    def test_all_down_progressions(self):
        """Test progression through all downs"""
        # 1st to 2nd
        first_down = DownState(current_down=1, yards_to_go=10, first_down_line=35)
        result = self.tracker.process_play(first_down, yards_gained=3, new_field_position=28)
        self.assertEqual(result.new_down_state.current_down, 2)
        self.assertIn("advance_to_2nd_down", result.down_events)
        
        # 2nd to 3rd
        second_down = DownState(current_down=2, yards_to_go=7, first_down_line=35)
        result = self.tracker.process_play(second_down, yards_gained=2, new_field_position=27)
        self.assertEqual(result.new_down_state.current_down, 3)
        self.assertIn("advance_to_3rd_down", result.down_events)
        
        # 3rd to 4th
        third_down = DownState(current_down=3, yards_to_go=5, first_down_line=35)
        result = self.tracker.process_play(third_down, yards_gained=1, new_field_position=26)
        self.assertEqual(result.new_down_state.current_down, 4)
        self.assertIn("advance_to_4th_down", result.down_events)
    
    def test_fourth_down_conversion(self):
        """Test successful 4th down conversion"""
        fourth_down = DownState(current_down=4, yards_to_go=3, first_down_line=35)
        
        result = self.tracker.process_play(fourth_down, yards_gained=5, new_field_position=37)
        
        self.assertTrue(result.first_down_achieved)
        self.assertEqual(result.down_result, DownResult.FIRST_DOWN_ACHIEVED)
        self.assertEqual(result.new_down_state.current_down, 1)
        self.assertFalse(result.turnover_on_downs)
    
    def test_turnover_on_downs(self):
        """Test failed 4th down conversion (turnover on downs)"""
        fourth_down = DownState(current_down=4, yards_to_go=5, first_down_line=35)
        
        result = self.tracker.process_play(fourth_down, yards_gained=3, new_field_position=33)
        
        self.assertEqual(result.down_result, DownResult.TURNOVER_ON_DOWNS)
        self.assertFalse(result.first_down_achieved)
        self.assertTrue(result.turnover_on_downs)
        self.assertTrue(result.possession_change)
        self.assertIsNone(result.new_down_state)  # Possession changes, no new down state
        self.assertIn("turnover_on_downs", result.down_events)
        self.assertIn("possession_change", result.down_events)
    
    def test_scoring_play_handling(self):
        """Test that scoring plays end the drive regardless of down"""
        down_state = DownState(current_down=2, yards_to_go=5, first_down_line=30)
        
        result = self.tracker.process_play(down_state, yards_gained=8, new_field_position=100, is_scoring_play=True)
        
        self.assertEqual(result.down_result, DownResult.SCORING_DRIVE)
        self.assertIsNone(result.new_down_state)  # Drive ended
        self.assertIn("scoring_play", result.down_events)
        self.assertIn("drive_ended", result.down_events)
    
    def test_negative_yards_handling(self):
        """Test handling of negative yardage (sacks, tackles for loss)"""
        down_state = DownState(current_down=2, yards_to_go=8, first_down_line=35)
        
        result = self.tracker.process_play(down_state, yards_gained=-3, new_field_position=22)
        
        self.assertEqual(result.down_result, DownResult.CONTINUE_DRIVE)
        self.assertEqual(result.new_down_state.current_down, 3)
        self.assertEqual(result.new_down_state.yards_to_go, 11)  # 8 + 3 = 11
        self.assertEqual(result.new_down_state.first_down_line, 35)  # Unchanged
    
    def test_no_gain_play(self):
        """Test play with no yards gained"""
        down_state = DownState(current_down=2, yards_to_go=6, first_down_line=30)
        
        result = self.tracker.process_play(down_state, yards_gained=0, new_field_position=24)
        
        self.assertEqual(result.new_down_state.current_down, 3)
        self.assertEqual(result.new_down_state.yards_to_go, 6)  # Unchanged
    
    def test_penalty_automatic_first_down(self):
        """Test automatic first down penalties"""
        down_state = DownState(current_down=3, yards_to_go=8, first_down_line=35)
        
        result = self.tracker.process_penalty(down_state, penalty_yards=15, is_automatic_first_down=True)
        
        self.assertTrue(result.first_down_achieved)
        self.assertEqual(result.new_down_state.current_down, 1)
        self.assertEqual(result.new_down_state.yards_to_go, 10)
        self.assertIn("automatic_first_down", result.down_events)
        self.assertIn("penalty_first_down", result.down_events)
    
    def test_penalty_yardage_adjustment(self):
        """Test penalty that adjusts yardage but doesn't give automatic first down"""
        down_state = DownState(current_down=2, yards_to_go=8, first_down_line=35)
        
        result = self.tracker.process_penalty(down_state, penalty_yards=5, is_automatic_first_down=False)
        
        self.assertFalse(result.first_down_achieved)
        self.assertEqual(result.new_down_state.current_down, 2)  # Same down
        self.assertEqual(result.new_down_state.yards_to_go, 3)  # 8 - 5 = 3
        self.assertEqual(result.new_down_state.first_down_line, 40)  # 35 + 5 = 40
        self.assertIn("penalty_yardage_adjustment", result.down_events)
    
    def test_create_new_drive(self):
        """Test creating a new drive state"""
        new_drive = self.tracker.create_new_drive(starting_field_position=25)
        
        self.assertEqual(new_drive.current_down, 1)
        self.assertEqual(new_drive.yards_to_go, 10)
        self.assertEqual(new_drive.first_down_line, 35)  # 25 + 10
    
    def test_new_drive_near_goal(self):
        """Test creating new drive near goal line"""
        new_drive = self.tracker.create_new_drive(starting_field_position=95)
        
        self.assertEqual(new_drive.current_down, 1)
        self.assertEqual(new_drive.yards_to_go, 5)  # Only 5 yards to goal
        self.assertEqual(new_drive.first_down_line, 100)  # Capped at goal line


class TestDownTrackerEdgeCases(unittest.TestCase):
    """Test edge cases and boundary conditions for DownTracker"""
    
    def setUp(self):
        self.tracker = DownTracker()
    
    def test_fourth_and_goal_conversion(self):
        """Test 4th and goal conversion scenarios"""
        # 4th and goal from 3
        fourth_and_goal = DownState(current_down=4, yards_to_go=3, first_down_line=100)
        
        # Successful conversion (touchdown - scoring play)
        result = self.tracker.process_play(fourth_and_goal, yards_gained=3, new_field_position=100, is_scoring_play=True)
        self.assertEqual(result.down_result, DownResult.SCORING_DRIVE)
        
        # Failed conversion (turnover on downs)
        result = self.tracker.process_play(fourth_and_goal, yards_gained=1, new_field_position=98, is_scoring_play=False)
        self.assertEqual(result.down_result, DownResult.TURNOVER_ON_DOWNS)
    
    def test_very_long_yardage_situations(self):
        """Test very long yardage situations (3rd and 25+)"""
        long_yardage = DownState(current_down=3, yards_to_go=27, first_down_line=50)
        
        # Partial conversion
        result = self.tracker.process_play(long_yardage, yards_gained=15, new_field_position=38)
        self.assertEqual(result.new_down_state.current_down, 4)
        self.assertEqual(result.new_down_state.yards_to_go, 12)  # 27 - 15 = 12
        
        # Full conversion
        result = self.tracker.process_play(long_yardage, yards_gained=30, new_field_position=35)
        self.assertTrue(result.first_down_achieved)
        self.assertEqual(result.yards_past_first_down, 3)  # 30 - 27 = 3
    
    def test_ordinal_conversion(self):
        """Test the private ordinal method"""
        self.assertEqual(self.tracker._ordinal(1), "1st")
        self.assertEqual(self.tracker._ordinal(2), "2nd")
        self.assertEqual(self.tracker._ordinal(3), "3rd") 
        self.assertEqual(self.tracker._ordinal(4), "4th")


if __name__ == '__main__':
    unittest.main()