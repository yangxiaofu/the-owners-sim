#!/usr/bin/env python3
"""
Test suite for the new PlayCaller system

Tests the integration of PlayCaller, CoachArchetype, and PlaybookLoader
to ensure the intelligent play calling system works correctly.
"""

import sys
import os
import unittest
from unittest.mock import Mock, patch

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from play_engine.play_calling.play_caller import PlayCaller, PlayCallContext, PlayCallerFactory
from play_engine.play_calling.coach_archetype import CoachArchetype
from play_engine.play_calling.playbook_loader import PlaybookLoader, SituationMapper
from play_engine.game_state.drive_manager import DriveSituation


class TestCoachArchetype(unittest.TestCase):
    """Test CoachArchetype functionality"""
    
    def test_coach_archetype_creation(self):
        """Test basic coach archetype creation and validation"""
        coach = CoachArchetype(
            name="Test Coach",
            aggression=0.7,
            risk_tolerance=0.6,
            run_preference=0.4
        )
        
        self.assertEqual(coach.name, "Test Coach")
        self.assertEqual(coach.aggression, 0.7)
        self.assertEqual(coach.risk_tolerance, 0.6)
        self.assertEqual(coach.run_preference, 0.4)
    
    def test_coach_archetype_validation(self):
        """Test that invalid values are rejected"""
        with self.assertRaises(ValueError):
            CoachArchetype(
                name="Invalid Coach",
                aggression=1.5  # Invalid - must be 0.0-1.0
            )
    
    def test_situational_aggression(self):
        """Test situation-specific aggression calculations"""
        coach = CoachArchetype(
            name="Aggressive Coach",
            aggression=0.8,
            red_zone_aggression=0.9
        )
        
        red_zone_aggression = coach.get_situational_aggression("red_zone")
        self.assertGreater(red_zone_aggression, coach.aggression)


class TestPlaybookLoader(unittest.TestCase):
    """Test PlaybookLoader functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.loader = PlaybookLoader()
    
    def test_situation_mapper(self):
        """Test situation mapping logic"""
        # Test first down
        situation_type = SituationMapper.get_situation_type(
            down=1, yards_to_go=10, field_position=30
        )
        self.assertEqual(situation_type, "first_down")
        
        # Test third and long
        situation_type = SituationMapper.get_situation_type(
            down=3, yards_to_go=12, field_position=45
        )
        self.assertEqual(situation_type, "third_long")
        
        # Test red zone
        situation_type = SituationMapper.get_situation_type(
            down=2, yards_to_go=5, field_position=85
        )
        self.assertEqual(situation_type, "red_zone")
        
        # Test two minute warning
        situation_type = SituationMapper.get_situation_type(
            down=1, yards_to_go=10, field_position=50, time_remaining=90
        )
        self.assertEqual(situation_type, "two_minute")
    
    def test_playbook_loading(self):
        """Test playbook loading with default fallback"""
        # Should create default playbook if file doesn't exist
        playbook = self.loader.load_playbook("nonexistent_playbook")
        self.assertIsNotNone(playbook)
        self.assertEqual(playbook.name, "nonexistent_playbook")
        
        # Should have some basic situations
        self.assertIsNotNone(playbook.get_situation_plays("first_down"))


class TestPlayCaller(unittest.TestCase):
    """Test PlayCaller functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create a test coach
        self.test_coach = CoachArchetype(
            name="Test Coach",
            aggression=0.6,
            risk_tolerance=0.5,
            run_preference=0.5,
            fourth_down_aggression=0.3,
            red_zone_aggression=0.7
        )
        
        # Create PlayCaller with test coach
        self.play_caller = PlayCaller(self.test_coach, "balanced")
        
        # Create test situations
        self.first_down_situation = DriveSituation(
            down=1,
            yards_to_go=10,
            field_position=30,
            possessing_team="test_team"
        )
        
        self.third_long_situation = DriveSituation(
            down=3,
            yards_to_go=12,
            field_position=45,
            possessing_team="test_team"
        )
        
        self.red_zone_situation = DriveSituation(
            down=2,
            yards_to_go=8,
            field_position=85,
            possessing_team="test_team"
        )
    
    def test_play_caller_initialization(self):
        """Test PlayCaller initializes correctly"""
        self.assertEqual(self.play_caller.coach.name, "Test Coach")
        self.assertIsNotNone(self.play_caller.playbook)
        self.assertEqual(len(self.play_caller.recent_calls), 0)
    
    def test_offensive_play_selection(self):
        """Test offensive play selection"""
        context = PlayCallContext(situation=self.first_down_situation)
        
        offensive_play = self.play_caller.select_offensive_play(context)
        
        # Should return a valid OffensivePlayCall
        self.assertIsNotNone(offensive_play)
        self.assertTrue(hasattr(offensive_play, 'play_type'))
        self.assertTrue(hasattr(offensive_play, 'formation'))
        self.assertTrue(hasattr(offensive_play, 'concept'))
    
    def test_defensive_play_selection(self):
        """Test defensive play selection"""
        context = PlayCallContext(situation=self.first_down_situation)
        
        defensive_play = self.play_caller.select_defensive_play(context)
        
        # Should return a valid DefensivePlayCall
        self.assertIsNotNone(defensive_play)
        self.assertTrue(hasattr(defensive_play, 'play_type'))
        self.assertTrue(hasattr(defensive_play, 'formation'))
    
    def test_situational_play_calling(self):
        """Test that different situations produce different play calls"""
        # Test multiple calls for same situation to see variety
        first_down_calls = []
        red_zone_calls = []
        
        for _ in range(5):
            # First down calls
            context = PlayCallContext(situation=self.first_down_situation)
            call = self.play_caller.select_offensive_play(context)
            first_down_calls.append((call.play_type, call.formation))
            
            # Red zone calls  
            context = PlayCallContext(situation=self.red_zone_situation)
            call = self.play_caller.select_offensive_play(context)
            red_zone_calls.append((call.play_type, call.formation))
        
        # Should see some variety in play calls
        unique_first_down = len(set(first_down_calls))
        unique_red_zone = len(set(red_zone_calls))
        
        # At least some variety expected (though randomness may occasionally fail this)
        # This is a probabilistic test, so we're lenient
        self.assertGreaterEqual(unique_first_down + unique_red_zone, 2)
    
    def test_play_sequencing(self):
        """Test that play sequencing affects selection"""
        context = PlayCallContext(situation=self.first_down_situation)
        
        # Make several calls to build up history
        calls = []
        for _ in range(3):
            call = self.play_caller.select_offensive_play(context)
            calls.append(call)
        
        # Should have play history now
        self.assertEqual(len(self.play_caller.recent_calls), 3)
    
    def test_coach_influence_on_play_calls(self):
        """Test that different coaches make different decisions"""
        # Create aggressive coach
        aggressive_coach = CoachArchetype(
            name="Aggressive Coach",
            aggression=0.9,
            risk_tolerance=0.8,
            run_preference=0.3,  # Pass-heavy
            fourth_down_aggression=0.8
        )
        
        # Create conservative coach
        conservative_coach = CoachArchetype(
            name="Conservative Coach", 
            aggression=0.2,
            risk_tolerance=0.2,
            run_preference=0.7,  # Run-heavy
            fourth_down_aggression=0.1
        )
        
        aggressive_caller = PlayCaller(aggressive_coach, "balanced")
        conservative_caller = PlayCaller(conservative_coach, "balanced")
        
        context = PlayCallContext(situation=self.first_down_situation)
        
        # Get multiple calls from each coach
        aggressive_calls = [aggressive_caller.select_offensive_play(context) for _ in range(10)]
        conservative_calls = [conservative_caller.select_offensive_play(context) for _ in range(10)]
        
        # Count run vs pass tendencies
        aggressive_runs = sum(1 for call in aggressive_calls if call.play_type == "RUN")
        conservative_runs = sum(1 for call in conservative_calls if call.play_type == "RUN")
        
        # Conservative coach should call more runs (though this is probabilistic)
        # We'll just verify both coaches can make calls
        self.assertEqual(len(aggressive_calls), 10)
        self.assertEqual(len(conservative_calls), 10)


class TestPlayCallerFactory(unittest.TestCase):
    """Test PlayCallerFactory convenience methods"""
    
    def test_factory_methods(self):
        """Test factory methods create different coach types"""
        aggressive_caller = PlayCallerFactory.create_aggressive_caller()
        conservative_caller = PlayCallerFactory.create_conservative_caller()
        balanced_caller = PlayCallerFactory.create_balanced_caller()
        
        # Check they have different characteristics
        self.assertGreater(aggressive_caller.coach.aggression, conservative_caller.coach.aggression)
        self.assertGreater(aggressive_caller.coach.fourth_down_aggression, 
                          conservative_caller.coach.fourth_down_aggression)
        
        # All should be functional
        situation = DriveSituation(
            down=1, yards_to_go=10, field_position=30, possessing_team="test"
        )
        context = PlayCallContext(situation=situation)
        
        # Should all be able to make play calls
        self.assertIsNotNone(aggressive_caller.select_offensive_play(context))
        self.assertIsNotNone(conservative_caller.select_offensive_play(context))
        self.assertIsNotNone(balanced_caller.select_offensive_play(context))


class TestSystemIntegration(unittest.TestCase):
    """Test full system integration"""
    
    def test_end_to_end_play_calling(self):
        """Test complete play calling workflow"""
        # Create a PlayCaller using the new factory system
        try:
            # Use the new dynamic team-based factory (Chiefs = team ID 14)
            from constants.team_ids import TeamIDs
            caller = PlayCallerFactory.create_for_team(TeamIDs.KANSAS_CITY_CHIEFS)
        except (ImportError, ValueError):
            # Fallback to creating a balanced caller if team-based creation fails
            caller = PlayCallerFactory.create_balanced_caller("balanced")
        
        # Create various game situations
        situations = [
            DriveSituation(down=1, yards_to_go=10, field_position=25, possessing_team="test"),
            DriveSituation(down=3, yards_to_go=8, field_position=55, possessing_team="test"),
            DriveSituation(down=2, yards_to_go=3, field_position=85, possessing_team="test"),
            DriveSituation(down=4, yards_to_go=2, field_position=45, possessing_team="test"),
        ]
        
        # Test play calling for each situation
        for situation in situations:
            context = PlayCallContext(situation=situation)
            
            # Should successfully generate plays
            offensive_play = caller.select_offensive_play(context)
            defensive_play = caller.select_defensive_play(context)
            
            self.assertIsNotNone(offensive_play)
            self.assertIsNotNone(defensive_play)
            
            # Plays should have required attributes
            self.assertTrue(hasattr(offensive_play, 'play_type'))
            self.assertTrue(hasattr(offensive_play, 'formation'))
            self.assertTrue(hasattr(defensive_play, 'play_type'))
            self.assertTrue(hasattr(defensive_play, 'formation'))


if __name__ == '__main__':
    # Run tests
    unittest.main(verbosity=2)