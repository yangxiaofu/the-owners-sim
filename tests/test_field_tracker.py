"""
Unit tests for Field Position Tracking System

Tests field position calculations, boundary detection, and scoring logic
in isolation from down tracking and other game systems.
"""

import unittest
from src.play_engine.game_state.field_position import (
    FieldPosition, 
    FieldTracker, 
    FieldResult, 
    FieldZone
)


class TestFieldPosition(unittest.TestCase):
    """Test FieldPosition data structure and calculations"""
    
    def test_field_position_creation(self):
        """Test basic field position creation and validation"""
        pos = FieldPosition(
            yard_line=25,
            possession_team="Team A",
            field_zone=FieldZone.OWN_TERRITORY
        )
        self.assertEqual(pos.yard_line, 25)
        self.assertEqual(pos.possession_team, "Team A")
        self.assertEqual(pos.field_zone, FieldZone.OWN_TERRITORY)
    
    def test_field_position_validation(self):
        """Test field position validation for invalid yard lines"""
        with self.assertRaises(ValueError):
            FieldPosition(yard_line=-1, possession_team="Team A", field_zone=FieldZone.OWN_TERRITORY)
        
        with self.assertRaises(ValueError):
            FieldPosition(yard_line=101, possession_team="Team A", field_zone=FieldZone.OWN_TERRITORY)
    
    def test_field_zone_auto_calculation(self):
        """Test automatic field zone calculation"""
        test_cases = [
            (0, FieldZone.OWN_END_ZONE),
            (10, FieldZone.OWN_GOAL_LINE),
            (25, FieldZone.OWN_TERRITORY), 
            (50, FieldZone.MIDFIELD),
            (65, FieldZone.OPPONENT_TERRITORY),
            (85, FieldZone.RED_ZONE),
            (100, FieldZone.OPPONENT_END_ZONE)
        ]
        
        for yard_line, expected_zone in test_cases:
            pos = FieldPosition(yard_line=yard_line, possession_team="Team A", field_zone=FieldZone.OWN_TERRITORY)
            self.assertEqual(pos.field_zone, expected_zone, f"Yard line {yard_line} should be {expected_zone}")
    
    def test_distance_calculations(self):
        """Test distance calculation methods"""
        pos = FieldPosition(yard_line=25, possession_team="Team A", field_zone=FieldZone.OWN_TERRITORY)
        
        self.assertEqual(pos.distance_to_goal(), 75)  # 100 - 25
        self.assertEqual(pos.distance_to_own_goal(), 25)  # 25 - 0
        self.assertFalse(pos.is_in_red_zone())
        self.assertTrue(pos.is_in_own_territory())
    
    def test_red_zone_detection(self):
        """Test red zone detection"""
        red_zone_pos = FieldPosition(yard_line=85, possession_team="Team A", field_zone=FieldZone.RED_ZONE)
        self.assertTrue(red_zone_pos.is_in_red_zone())
        self.assertFalse(red_zone_pos.is_in_own_territory())


class TestFieldTracker(unittest.TestCase):
    """Test FieldTracker play processing logic"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.tracker = FieldTracker()
    
    def test_normal_play_processing(self):
        """Test normal play that stays within field boundaries"""
        current_pos = FieldPosition(yard_line=25, possession_team="Team A", field_zone=FieldZone.OWN_TERRITORY)
        
        result = self.tracker.process_play(current_pos, raw_yards_gained=10)
        
        self.assertEqual(result.raw_yards_gained, 10)
        self.assertEqual(result.actual_yards_gained, 10)
        self.assertEqual(result.new_field_position.yard_line, 35)
        self.assertFalse(result.is_scored)
        self.assertFalse(result.possession_change)
        self.assertEqual(result.points_scored, 0)
    
    def test_touchdown_detection(self):
        """Test touchdown detection when ball crosses goal line"""
        current_pos = FieldPosition(yard_line=95, possession_team="Team A", field_zone=FieldZone.RED_ZONE)
        
        result = self.tracker.process_play(current_pos, raw_yards_gained=10)
        
        # Should detect touchdown and adjust yards
        self.assertEqual(result.raw_yards_gained, 10)  # Preserve raw result
        self.assertEqual(result.actual_yards_gained, 5)  # Adjusted to goal line
        self.assertEqual(result.new_field_position.yard_line, 100)
        self.assertTrue(result.is_scored)
        self.assertEqual(result.scoring_type, "touchdown")
        self.assertEqual(result.points_scored, 6)
        self.assertTrue(result.possession_change)  # Scoring team kicks off
        self.assertIn("touchdown", result.field_events)
    
    def test_exact_goal_line_play(self):
        """Test play that reaches exactly the goal line"""
        current_pos = FieldPosition(yard_line=95, possession_team="Team A", field_zone=FieldZone.RED_ZONE)
        
        result = self.tracker.process_play(current_pos, raw_yards_gained=5)
        
        self.assertEqual(result.actual_yards_gained, 5)
        self.assertEqual(result.new_field_position.yard_line, 100)
        self.assertTrue(result.is_scored)
        self.assertEqual(result.scoring_type, "touchdown")
    
    def test_safety_detection(self):
        """Test safety detection when ball goes behind own goal line"""
        current_pos = FieldPosition(yard_line=2, possession_team="Team A", field_zone=FieldZone.OWN_GOAL_LINE)
        
        result = self.tracker.process_play(current_pos, raw_yards_gained=-5)
        
        # Should detect safety
        self.assertEqual(result.raw_yards_gained, -5)
        self.assertEqual(result.actual_yards_gained, -2)  # Adjusted to own goal line
        self.assertEqual(result.new_field_position.yard_line, 0)
        self.assertTrue(result.is_scored)
        self.assertEqual(result.scoring_type, "safety")
        self.assertEqual(result.points_scored, 2)
        self.assertTrue(result.possession_change)
        self.assertIn("safety", result.field_events)
    
    def test_exact_own_goal_line_play(self):
        """Test play that reaches exactly own goal line (safety)"""
        current_pos = FieldPosition(yard_line=3, possession_team="Team A", field_zone=FieldZone.OWN_GOAL_LINE)
        
        result = self.tracker.process_play(current_pos, raw_yards_gained=-3)
        
        self.assertEqual(result.actual_yards_gained, -3)
        self.assertEqual(result.new_field_position.yard_line, 0)
        self.assertTrue(result.is_scored)
        self.assertEqual(result.scoring_type, "safety")
    
    def test_field_zone_change_detection(self):
        """Test detection of field zone changes"""
        current_pos = FieldPosition(yard_line=45, possession_team="Team A", field_zone=FieldZone.OWN_TERRITORY)
        
        result = self.tracker.process_play(current_pos, raw_yards_gained=15)
        
        # Should move from OWN_TERRITORY to OPPONENT_TERRITORY
        self.assertEqual(result.new_field_position.yard_line, 60)
        self.assertEqual(result.new_field_position.field_zone, FieldZone.OPPONENT_TERRITORY)
        self.assertIn("entered_opponent_territory", result.field_events)
    
    def test_no_gain_play(self):
        """Test play with no yards gained"""
        current_pos = FieldPosition(yard_line=25, possession_team="Team A", field_zone=FieldZone.OWN_TERRITORY)
        
        result = self.tracker.process_play(current_pos, raw_yards_gained=0)
        
        self.assertEqual(result.actual_yards_gained, 0)
        self.assertEqual(result.new_field_position.yard_line, 25)
        self.assertEqual(result.new_field_position.field_zone, FieldZone.OWN_TERRITORY)
        self.assertFalse(result.is_scored)
    
    def test_negative_yardage_play(self):
        """Test play with lost yardage (sack, tackle for loss)"""
        current_pos = FieldPosition(yard_line=35, possession_team="Team A", field_zone=FieldZone.OWN_TERRITORY)
        
        result = self.tracker.process_play(current_pos, raw_yards_gained=-8)
        
        self.assertEqual(result.actual_yards_gained, -8)
        self.assertEqual(result.new_field_position.yard_line, 27)
        self.assertFalse(result.is_scored)
    
    def test_very_long_gain(self):
        """Test very long gain that doesn't score (99-yard play)"""
        current_pos = FieldPosition(yard_line=1, possession_team="Team A", field_zone=FieldZone.OWN_GOAL_LINE)
        
        result = self.tracker.process_play(current_pos, raw_yards_gained=98)
        
        self.assertEqual(result.actual_yards_gained, 98)
        self.assertEqual(result.new_field_position.yard_line, 99)
        self.assertEqual(result.new_field_position.field_zone, FieldZone.RED_ZONE)
        self.assertFalse(result.is_scored)
    
    def test_process_turnover(self):
        """Test turnover processing with field position flip"""
        current_pos = FieldPosition(yard_line=25, possession_team="Team A", field_zone=FieldZone.OWN_TERRITORY)
        
        result = self.tracker.process_turnover(current_pos, turnover_type="fumble")
        
        # Field position should flip perspective (25 becomes 75 for other team)
        self.assertEqual(result.new_field_position.yard_line, 75)
        self.assertTrue(result.possession_change)
        self.assertIn("fumble", result.field_events)
        self.assertIn("possession_change", result.field_events)
    
    def test_midfield_turnover(self):
        """Test turnover exactly at midfield"""
        current_pos = FieldPosition(yard_line=50, possession_team="Team A", field_zone=FieldZone.MIDFIELD)
        
        result = self.tracker.process_turnover(current_pos, turnover_type="interception")
        
        # 50-yard line should become 50-yard line for other team
        self.assertEqual(result.new_field_position.yard_line, 50)
        self.assertEqual(result.new_field_position.field_zone, FieldZone.MIDFIELD)


class TestFieldTrackerEdgeCases(unittest.TestCase):
    """Test edge cases and boundary conditions for FieldTracker"""
    
    def setUp(self):
        self.tracker = FieldTracker()
    
    def test_five_yard_line_ten_yard_pass(self):
        """Test the classic example: 5-yard line + 10-yard pass = touchdown"""
        current_pos = FieldPosition(yard_line=95, possession_team="Team A", field_zone=FieldZone.RED_ZONE)
        
        result = self.tracker.process_play(current_pos, raw_yards_gained=10)
        
        self.assertEqual(result.raw_yards_gained, 10)     # Preserve mechanics
        self.assertEqual(result.actual_yards_gained, 5)   # Field reality
        self.assertTrue(result.is_scored)
        self.assertEqual(result.scoring_type, "touchdown")
    
    def test_one_yard_line_scenarios(self):
        """Test various scenarios from the 1-yard line"""
        one_yard_pos = FieldPosition(yard_line=99, possession_team="Team A", field_zone=FieldZone.RED_ZONE)
        
        # 1-yard TD
        result = self.tracker.process_play(one_yard_pos, raw_yards_gained=1)
        self.assertTrue(result.is_scored)
        self.assertEqual(result.actual_yards_gained, 1)
        
        # Goal line stand (no gain)
        result = self.tracker.process_play(one_yard_pos, raw_yards_gained=0)
        self.assertFalse(result.is_scored)
        self.assertEqual(result.new_field_position.yard_line, 99)
        
        # Stuffed at goal line (loss)
        result = self.tracker.process_play(one_yard_pos, raw_yards_gained=-2)
        self.assertFalse(result.is_scored)
        self.assertEqual(result.new_field_position.yard_line, 97)
    
    def test_own_one_yard_line_scenarios(self):
        """Test scenarios from team's own 1-yard line"""
        own_one_pos = FieldPosition(yard_line=1, possession_team="Team A", field_zone=FieldZone.OWN_GOAL_LINE)
        
        # Escape for positive yards
        result = self.tracker.process_play(own_one_pos, raw_yards_gained=5)
        self.assertFalse(result.is_scored)
        self.assertEqual(result.new_field_position.yard_line, 6)
        
        # Stay at 1-yard line
        result = self.tracker.process_play(own_one_pos, raw_yards_gained=0)
        self.assertFalse(result.is_scored)
        self.assertEqual(result.new_field_position.yard_line, 1)
        
        # Safety
        result = self.tracker.process_play(own_one_pos, raw_yards_gained=-1)
        self.assertTrue(result.is_scored)
        self.assertEqual(result.scoring_type, "safety")


if __name__ == '__main__':
    unittest.main()