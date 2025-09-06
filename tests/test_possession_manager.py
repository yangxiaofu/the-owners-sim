"""
Unit tests for Possession Manager

Tests the simple possession tracking functionality with clean separation
from field position, drive management, and down tracking.
"""

import unittest
from datetime import datetime, timedelta
from src.play_engine.game_state.possession_manager import (
    PossessionManager,
    PossessionChange
)


class TestPossessionChange(unittest.TestCase):
    """Test PossessionChange data structure"""
    
    def test_possession_change_creation(self):
        """Test basic possession change creation"""
        timestamp = datetime.now()
        change = PossessionChange(
            previous_team="Lions",
            new_team="Packers",
            reason="interception",
            timestamp=timestamp
        )
        
        self.assertEqual(change.previous_team, "Lions")
        self.assertEqual(change.new_team, "Packers")
        self.assertEqual(change.reason, "interception")
        self.assertEqual(change.timestamp, timestamp)
    
    def test_possession_change_string_representation(self):
        """Test string representation of possession change"""
        change = PossessionChange(
            previous_team="Lions",
            new_team="Packers",
            reason="fumble",
            timestamp=datetime.now()
        )
        
        expected = "Lions → Packers (fumble)"
        self.assertEqual(str(change), expected)


class TestPossessionManager(unittest.TestCase):
    """Test PossessionManager functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.manager = PossessionManager("Detroit Lions")
    
    def test_possession_manager_creation(self):
        """Test basic possession manager creation"""
        self.assertEqual(self.manager.get_possessing_team(), "Detroit Lions")
        self.assertEqual(len(self.manager.get_possession_history()), 0)
        self.assertFalse(self.manager.has_possession_changed())
    
    def test_initial_team_validation(self):
        """Test validation of initial team"""
        # Valid team
        manager = PossessionManager("Valid Team")
        self.assertEqual(manager.get_possessing_team(), "Valid Team")
        
        # Test whitespace trimming
        manager = PossessionManager("  Spaced Team  ")
        self.assertEqual(manager.get_possessing_team(), "Spaced Team")
        
        # Invalid cases
        with self.assertRaises(ValueError):
            PossessionManager("")
        
        with self.assertRaises(ValueError):
            PossessionManager("   ")
        
        with self.assertRaises(ValueError):
            PossessionManager(None)
    
    def test_basic_possession_change(self):
        """Test basic possession change functionality"""
        # Initial state
        self.assertEqual(self.manager.get_possessing_team(), "Detroit Lions")
        self.assertFalse(self.manager.has_possession_changed())
        
        # Change possession
        self.manager.change_possession("Green Bay Packers", "interception")
        
        # Verify change
        self.assertEqual(self.manager.get_possessing_team(), "Green Bay Packers")
        self.assertTrue(self.manager.has_possession_changed())
        
        # Check history
        history = self.manager.get_possession_history()
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0].previous_team, "Detroit Lions")
        self.assertEqual(history[0].new_team, "Green Bay Packers")
        self.assertEqual(history[0].reason, "interception")
    
    def test_multiple_possession_changes(self):
        """Test multiple possession changes"""
        # Change 1: Lions → Packers
        self.manager.change_possession("Packers", "fumble")
        
        # Change 2: Packers → Lions  
        self.manager.change_possession("Lions", "interception")
        
        # Change 3: Lions → Bears
        self.manager.change_possession("Bears", "turnover_on_downs")
        
        # Verify final state
        self.assertEqual(self.manager.get_possessing_team(), "Bears")
        
        # Verify history
        history = self.manager.get_possession_history()
        self.assertEqual(len(history), 3)
        
        # Check each change
        self.assertEqual(history[0].previous_team, "Detroit Lions")
        self.assertEqual(history[0].new_team, "Packers")
        self.assertEqual(history[0].reason, "fumble")
        
        self.assertEqual(history[1].previous_team, "Packers")
        self.assertEqual(history[1].new_team, "Lions")
        self.assertEqual(history[1].reason, "interception")
        
        self.assertEqual(history[2].previous_team, "Lions")
        self.assertEqual(history[2].new_team, "Bears")
        self.assertEqual(history[2].reason, "turnover_on_downs")
    
    def test_possession_change_validation(self):
        """Test validation of possession changes"""
        # Valid changes
        self.manager.change_possession("Valid Team", "valid_reason")
        self.assertEqual(self.manager.get_possessing_team(), "Valid Team")
        
        # Test whitespace trimming
        self.manager.change_possession("  Spaced Team  ", "  spaced reason  ")
        self.assertEqual(self.manager.get_possessing_team(), "Spaced Team")
        
        # Invalid new team
        with self.assertRaises(ValueError):
            self.manager.change_possession("", "reason")
        
        with self.assertRaises(ValueError):
            self.manager.change_possession("   ", "reason")
        
        with self.assertRaises(ValueError):
            self.manager.change_possession(None, "reason")
    
    def test_no_change_same_team(self):
        """Test that changing to same team doesn't create history entry"""
        initial_team = self.manager.get_possessing_team()
        initial_history_length = len(self.manager.get_possession_history())
        
        # Try to change to same team
        self.manager.change_possession("Detroit Lions", "no_change")
        
        # Should remain unchanged
        self.assertEqual(self.manager.get_possessing_team(), initial_team)
        self.assertEqual(len(self.manager.get_possession_history()), initial_history_length)
    
    def test_default_reason(self):
        """Test possession change with default reason"""
        self.manager.change_possession("New Team")
        
        history = self.manager.get_possession_history()
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0].reason, "possession_change")
    
    def test_possession_count(self):
        """Test possession counting for teams"""
        # Initial state - Lions start with possession (never lost it)
        self.assertEqual(self.manager.get_possession_count("Detroit Lions"), 1)
        self.assertEqual(self.manager.get_possession_count("Packers"), 0)
        
        # Lions → Packers
        self.manager.change_possession("Packers", "fumble")
        self.assertEqual(self.manager.get_possession_count("Detroit Lions"), 1)
        self.assertEqual(self.manager.get_possession_count("Packers"), 1)
        
        # Packers → Lions
        self.manager.change_possession("Detroit Lions", "interception")
        self.assertEqual(self.manager.get_possession_count("Detroit Lions"), 2)
        self.assertEqual(self.manager.get_possession_count("Packers"), 1)
        
        # Lions → Bears
        self.manager.change_possession("Bears", "punt")
        self.assertEqual(self.manager.get_possession_count("Detroit Lions"), 2)
        self.assertEqual(self.manager.get_possession_count("Packers"), 1)
        self.assertEqual(self.manager.get_possession_count("Bears"), 1)
        
        # Test invalid team
        self.assertEqual(self.manager.get_possession_count(""), 0)
        self.assertEqual(self.manager.get_possession_count(None), 0)
    
    def test_recent_possession_changes(self):
        """Test getting recent possession changes"""
        # Add multiple changes
        teams = ["Packers", "Lions", "Bears", "Vikings", "Cowboys", "Giants"]
        for i, team in enumerate(teams):
            self.manager.change_possession(team, f"reason_{i}")
        
        # Get recent changes
        recent_3 = self.manager.get_recent_possession_changes(3)
        self.assertEqual(len(recent_3), 3)
        self.assertEqual(recent_3[-1].new_team, "Giants")  # Most recent
        self.assertEqual(recent_3[-2].new_team, "Cowboys")
        self.assertEqual(recent_3[-3].new_team, "Vikings")
        
        # Get more than available
        all_changes = self.manager.get_recent_possession_changes(10)
        self.assertEqual(len(all_changes), 6)  # Only 6 changes made
        
        # Empty manager
        empty_manager = PossessionManager("Team")
        recent = empty_manager.get_recent_possession_changes(5)
        self.assertEqual(len(recent), 0)
    
    def test_possession_history_immutability(self):
        """Test that returned history cannot modify internal state"""
        self.manager.change_possession("Packers", "test")
        
        # Get history and try to modify it
        history = self.manager.get_possession_history()
        original_length = len(history)
        
        # Try to modify returned list
        history.append(PossessionChange("Fake", "Team", "fake", datetime.now()))
        
        # Internal state should be unchanged
        internal_history = self.manager.get_possession_history()
        self.assertEqual(len(internal_history), original_length)
        self.assertNotEqual(len(history), len(internal_history))
    
    def test_string_representations(self):
        """Test string representations of manager"""
        # Initial state
        self.assertEqual(str(self.manager), "Possession: Detroit Lions")
        self.assertEqual(repr(self.manager), "PossessionManager(current=Detroit Lions, changes=0)")
        
        # After changes
        self.manager.change_possession("Packers", "test")
        self.manager.change_possession("Lions", "test")
        
        self.assertEqual(str(self.manager), "Possession: Lions")
        self.assertEqual(repr(self.manager), "PossessionManager(current=Lions, changes=2)")
    
    def test_timestamp_ordering(self):
        """Test that possession changes maintain chronological order"""
        start_time = datetime.now()
        
        # Make changes with small delays to ensure timestamp differences
        self.manager.change_possession("Team1", "reason1")
        first_change_time = self.manager.get_possession_history()[-1].timestamp
        
        self.manager.change_possession("Team2", "reason2")
        second_change_time = self.manager.get_possession_history()[-1].timestamp
        
        # Verify chronological ordering
        self.assertGreaterEqual(first_change_time, start_time)
        self.assertGreaterEqual(second_change_time, first_change_time)
        
        # Verify history is in order
        history = self.manager.get_possession_history()
        for i in range(1, len(history)):
            self.assertGreaterEqual(history[i].timestamp, history[i-1].timestamp)


class TestPossessionManagerEdgeCases(unittest.TestCase):
    """Test edge cases and error conditions"""
    
    def test_empty_string_handling(self):
        """Test handling of empty strings and whitespace"""
        manager = PossessionManager("Initial Team")
        
        # Empty reason should get default
        manager.change_possession("New Team", "")
        history = manager.get_possession_history()
        self.assertEqual(history[0].reason, "possession_change")
        
        # Whitespace-only reason should be trimmed
        manager.change_possession("Another Team", "   ")
        history = manager.get_possession_history()
        self.assertEqual(history[1].reason, "")  # Trimmed empty string
    
    def test_special_characters_in_names(self):
        """Test handling of special characters in team names"""
        special_names = [
            "Team-With-Hyphens",
            "Team With Spaces",
            "Team.With.Dots",
            "Team_With_Underscores",
            "Team's Apostrophe",
            "Team (Parentheses)",
        ]
        
        manager = PossessionManager(special_names[0])
        
        for i, name in enumerate(special_names[1:], 1):
            manager.change_possession(name, f"test_{i}")
            self.assertEqual(manager.get_possessing_team(), name)
    
    def test_case_sensitivity(self):
        """Test that team names are case-sensitive"""
        manager = PossessionManager("lions")
        
        manager.change_possession("Lions", "case_test")  # Capital L
        self.assertEqual(manager.get_possessing_team(), "Lions")
        
        history = manager.get_possession_history()
        self.assertEqual(history[0].previous_team, "lions")
        self.assertEqual(history[0].new_team, "Lions")


if __name__ == '__main__':
    unittest.main()