#!/usr/bin/env python3
"""
Comprehensive unit tests for enhanced play call system

Tests OffensivePlayCall and DefensivePlayCall functionality including
validation, compatibility checking, and helper methods.
"""

import unittest
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from play_engine.play_calls.offensive_play_call import OffensivePlayCall
from play_engine.play_calls.defensive_play_call import DefensivePlayCall
from play_engine.play_types.offensive_types import OffensivePlayType
from play_engine.play_types.defensive_types import DefensivePlayType
from formation import OffensiveFormation, DefensiveFormation


class TestOffensivePlayCall(unittest.TestCase):
    """Test OffensivePlayCall functionality"""
    
    def test_basic_initialization(self):
        """Test basic offensive play call creation"""
        play_call = OffensivePlayCall(OffensivePlayType.RUN, OffensiveFormation.I_FORMATION)
        
        self.assertEqual(play_call.get_play_type(), OffensivePlayType.RUN)
        self.assertEqual(play_call.get_formation(), OffensiveFormation.I_FORMATION)
        self.assertIsNone(play_call.get_concept())
        self.assertIsNone(play_call.get_personnel_package())
    
    def test_full_initialization(self):
        """Test offensive play call with all parameters"""
        play_call = OffensivePlayCall(
            play_type=OffensivePlayType.RUN,
            formation=OffensiveFormation.I_FORMATION,
            concept="power",
            personnel_package="21",
            target="left_guard"
        )
        
        self.assertEqual(play_call.get_play_type(), OffensivePlayType.RUN)
        self.assertEqual(play_call.get_formation(), OffensiveFormation.I_FORMATION)
        self.assertEqual(play_call.get_concept(), "power")
        self.assertEqual(play_call.get_personnel_package(), "21")
        self.assertEqual(play_call.get_additional_params()["target"], "left_guard")
    
    def test_play_type_validation(self):
        """Test play type validation"""
        # Valid play type should work
        OffensivePlayCall(OffensivePlayType.PASS, OffensiveFormation.SHOTGUN)
        
        # Invalid play type should raise error
        with self.assertRaises(ValueError) as context:
            OffensivePlayCall("invalid_play", OffensiveFormation.SHOTGUN)
        self.assertIn("Invalid offensive play type", str(context.exception))
    
    def test_formation_validation(self):
        """Test formation validation"""
        # Valid formation should work
        OffensivePlayCall(OffensivePlayType.RUN, OffensiveFormation.SINGLEBACK)
        
        # Invalid formation should raise error
        with self.assertRaises(ValueError) as context:
            OffensivePlayCall(OffensivePlayType.RUN, "invalid_formation")
        self.assertIn("Invalid offensive formation", str(context.exception))
    
    def test_special_teams_compatibility(self):
        """Test special teams play/formation compatibility"""
        # Valid special teams combinations
        OffensivePlayCall(OffensivePlayType.FIELD_GOAL, OffensiveFormation.FIELD_GOAL)
        OffensivePlayCall(OffensivePlayType.PUNT, OffensiveFormation.PUNT)
        OffensivePlayCall(OffensivePlayType.KICKOFF, OffensiveFormation.KICKOFF)
        
        # Invalid special teams combinations should raise error
        with self.assertRaises(ValueError) as context:
            OffensivePlayCall(OffensivePlayType.FIELD_GOAL, OffensiveFormation.I_FORMATION)
        self.assertIn("Incompatible play type", str(context.exception))
        
        with self.assertRaises(ValueError) as context:
            OffensivePlayCall(OffensivePlayType.RUN, OffensiveFormation.FIELD_GOAL)
        self.assertIn("Incompatible play type", str(context.exception))
    
    def test_play_type_classification(self):
        """Test play type classification methods"""
        # Running play
        run_call = OffensivePlayCall(OffensivePlayType.RUN, OffensiveFormation.I_FORMATION)
        self.assertTrue(run_call.is_running_play())
        self.assertFalse(run_call.is_passing_play())
        self.assertFalse(run_call.is_special_teams())
        
        # Passing play
        pass_call = OffensivePlayCall(OffensivePlayType.PASS, OffensiveFormation.SHOTGUN)
        self.assertFalse(pass_call.is_running_play())
        self.assertTrue(pass_call.is_passing_play())
        self.assertFalse(pass_call.is_special_teams())
        
        # Special teams play
        fg_call = OffensivePlayCall(OffensivePlayType.FIELD_GOAL, OffensiveFormation.FIELD_GOAL)
        self.assertFalse(fg_call.is_running_play())
        self.assertFalse(fg_call.is_passing_play())
        self.assertTrue(fg_call.is_special_teams())
    
    def test_play_call_modification(self):
        """Test creating modified versions of play calls"""
        original = OffensivePlayCall(OffensivePlayType.RUN, OffensiveFormation.I_FORMATION)
        
        # Test with_concept
        with_concept = original.with_concept("power")
        self.assertEqual(with_concept.get_concept(), "power")
        self.assertEqual(with_concept.get_formation(), OffensiveFormation.I_FORMATION)
        self.assertIsNone(original.get_concept())  # Original unchanged
        
        # Test with_formation
        with_formation = original.with_formation(OffensiveFormation.SINGLEBACK)
        self.assertEqual(with_formation.get_formation(), OffensiveFormation.SINGLEBACK)
        self.assertEqual(with_formation.get_play_type(), OffensivePlayType.RUN)
        self.assertEqual(original.get_formation(), OffensiveFormation.I_FORMATION)  # Original unchanged
    
    def test_equality(self):
        """Test play call equality"""
        call1 = OffensivePlayCall(OffensivePlayType.RUN, OffensiveFormation.I_FORMATION, concept="power")
        call2 = OffensivePlayCall(OffensivePlayType.RUN, OffensiveFormation.I_FORMATION, concept="power")
        call3 = OffensivePlayCall(OffensivePlayType.RUN, OffensiveFormation.I_FORMATION, concept="sweep")
        
        self.assertEqual(call1, call2)
        self.assertNotEqual(call1, call3)
        self.assertNotEqual(call1, "not_a_play_call")
    
    def test_string_representation(self):
        """Test string representation"""
        play_call = OffensivePlayCall(
            OffensivePlayType.RUN, 
            OffensiveFormation.I_FORMATION, 
            concept="power",
            personnel_package="21"
        )
        
        str_repr = str(play_call)
        self.assertIn("OffensivePlayCall", str_repr)
        self.assertIn("offensive_run", str_repr)
        self.assertIn("i_formation", str_repr)
        self.assertIn("power", str_repr)
        self.assertIn("21", str_repr)


class TestDefensivePlayCall(unittest.TestCase):
    """Test DefensivePlayCall functionality"""
    
    def test_basic_initialization(self):
        """Test basic defensive play call creation"""
        play_call = DefensivePlayCall(DefensivePlayType.COVER_2, DefensiveFormation.FOUR_THREE)
        
        self.assertEqual(play_call.get_play_type(), DefensivePlayType.COVER_2)
        self.assertEqual(play_call.get_formation(), DefensiveFormation.FOUR_THREE)
        self.assertIsNone(play_call.get_coverage())
        self.assertIsNone(play_call.get_blitz_package())
        self.assertEqual(play_call.get_hot_routes(), [])
    
    def test_full_initialization(self):
        """Test defensive play call with all parameters"""
        play_call = DefensivePlayCall(
            play_type=DefensivePlayType.BLITZ,
            formation=DefensiveFormation.BLITZ_PACKAGE,
            coverage="man",
            blitz_package="safety_blitz",
            hot_routes=["hot_route_1", "hot_route_2"],
            rush_lanes=["a_gap", "b_gap"]
        )
        
        self.assertEqual(play_call.get_play_type(), DefensivePlayType.BLITZ)
        self.assertEqual(play_call.get_formation(), DefensiveFormation.BLITZ_PACKAGE)
        self.assertEqual(play_call.get_coverage(), "man")
        self.assertEqual(play_call.get_blitz_package(), "safety_blitz")
        self.assertEqual(play_call.get_hot_routes(), ["hot_route_1", "hot_route_2"])
        self.assertEqual(play_call.get_additional_params()["rush_lanes"], ["a_gap", "b_gap"])
    
    def test_play_type_validation(self):
        """Test play type validation"""
        # Valid play type should work
        DefensivePlayCall(DefensivePlayType.COVER_3, DefensiveFormation.FOUR_THREE)
        
        # Invalid play type should raise error
        with self.assertRaises(ValueError) as context:
            DefensivePlayCall("invalid_play", DefensiveFormation.FOUR_THREE)
        self.assertIn("Invalid defensive play type", str(context.exception))
    
    def test_formation_validation(self):
        """Test formation validation"""
        # Valid formation should work
        DefensivePlayCall(DefensivePlayType.COVER_2, DefensiveFormation.NICKEL)
        
        # Invalid formation should raise error
        with self.assertRaises(ValueError) as context:
            DefensivePlayCall(DefensivePlayType.COVER_2, "invalid_formation")
        self.assertIn("Invalid defensive formation", str(context.exception))
    
    def test_specific_play_formation_compatibility(self):
        """Test specific play/formation compatibility requirements"""
        # Valid specific combinations
        DefensivePlayCall(DefensivePlayType.NICKEL_DEFENSE, DefensiveFormation.NICKEL)
        DefensivePlayCall(DefensivePlayType.DIME_DEFENSE, DefensiveFormation.DIME)
        DefensivePlayCall(DefensivePlayType.GOAL_LINE_DEFENSE, DefensiveFormation.GOAL_LINE)
        
        # Invalid specific combinations should raise error
        with self.assertRaises(ValueError) as context:
            DefensivePlayCall(DefensivePlayType.NICKEL_DEFENSE, DefensiveFormation.FOUR_THREE)
        self.assertIn("Incompatible play type", str(context.exception))
    
    def test_coverage_classification(self):
        """Test coverage classification methods"""
        # Man coverage
        man_call = DefensivePlayCall(DefensivePlayType.COVER_1, DefensiveFormation.FOUR_THREE)
        self.assertTrue(man_call.is_man_coverage())
        self.assertFalse(man_call.is_zone_coverage())
        
        # Zone coverage
        zone_call = DefensivePlayCall(DefensivePlayType.COVER_2, DefensiveFormation.FOUR_THREE)
        self.assertFalse(zone_call.is_man_coverage())
        self.assertTrue(zone_call.is_zone_coverage())
        
        # Coverage parameter override
        man_with_zone_param = DefensivePlayCall(DefensivePlayType.FOUR_MAN_RUSH, DefensiveFormation.FOUR_THREE, coverage="zone")
        self.assertFalse(man_with_zone_param.is_man_coverage())
        self.assertTrue(man_with_zone_param.is_zone_coverage())
    
    def test_blitz_classification(self):
        """Test blitz classification"""
        # Blitz play type
        blitz_call = DefensivePlayCall(DefensivePlayType.BLITZ, DefensiveFormation.FOUR_THREE)
        self.assertTrue(blitz_call.is_blitz())
        
        # Blitz formation
        blitz_formation_call = DefensivePlayCall(DefensivePlayType.COVER_1, DefensiveFormation.BLITZ_PACKAGE)
        self.assertTrue(blitz_formation_call.is_blitz())
        
        # Blitz package parameter
        blitz_package_call = DefensivePlayCall(DefensivePlayType.COVER_2, DefensiveFormation.FOUR_THREE, blitz_package="corner_blitz")
        self.assertTrue(blitz_package_call.is_blitz())
        
        # Non-blitz
        standard_call = DefensivePlayCall(DefensivePlayType.COVER_2, DefensiveFormation.FOUR_THREE)
        self.assertFalse(standard_call.is_blitz())
    
    def test_play_type_classification(self):
        """Test pass/run defense classification"""
        # Pass defense
        pass_defense = DefensivePlayCall(DefensivePlayType.COVER_3, DefensiveFormation.FOUR_THREE)
        self.assertTrue(pass_defense.is_pass_defense())
        self.assertFalse(pass_defense.is_run_defense())
        
        # Run defense
        run_defense = DefensivePlayCall(DefensivePlayType.RUN_STUFF, DefensiveFormation.FOUR_SIX)
        self.assertFalse(run_defense.is_pass_defense())
        self.assertTrue(run_defense.is_run_defense())
    
    def test_play_call_modification(self):
        """Test creating modified versions of defensive play calls"""
        original = DefensivePlayCall(DefensivePlayType.COVER_2, DefensiveFormation.FOUR_THREE)
        
        # Test with_coverage
        with_coverage = original.with_coverage("man")
        self.assertEqual(with_coverage.get_coverage(), "man")
        self.assertEqual(with_coverage.get_formation(), DefensiveFormation.FOUR_THREE)
        self.assertIsNone(original.get_coverage())  # Original unchanged
        
        # Test with_blitz_package
        with_blitz = original.with_blitz_package("corner_blitz")
        self.assertEqual(with_blitz.get_blitz_package(), "corner_blitz")
        self.assertIsNone(original.get_blitz_package())  # Original unchanged
        
        # Test add_hot_route
        with_hot_route = original.add_hot_route("slant_hot")
        self.assertEqual(with_hot_route.get_hot_routes(), ["slant_hot"])
        self.assertEqual(original.get_hot_routes(), [])  # Original unchanged
    
    def test_equality(self):
        """Test defensive play call equality"""
        call1 = DefensivePlayCall(DefensivePlayType.COVER_2, DefensiveFormation.FOUR_THREE, coverage="zone")
        call2 = DefensivePlayCall(DefensivePlayType.COVER_2, DefensiveFormation.FOUR_THREE, coverage="zone")
        call3 = DefensivePlayCall(DefensivePlayType.COVER_2, DefensiveFormation.FOUR_THREE, coverage="man")
        
        self.assertEqual(call1, call2)
        self.assertNotEqual(call1, call3)
        self.assertNotEqual(call1, "not_a_play_call")
    
    def test_string_representation(self):
        """Test string representation"""
        play_call = DefensivePlayCall(
            DefensivePlayType.BLITZ,
            DefensiveFormation.BLITZ_PACKAGE,
            coverage="man",
            blitz_package="safety_blitz",
            hot_routes=["slant_hot"]
        )
        
        str_repr = str(play_call)
        self.assertIn("DefensivePlayCall", str_repr)
        self.assertIn("defensive_blitz", str_repr)
        self.assertIn("blitz_package", str_repr)
        self.assertIn("man", str_repr)
        self.assertIn("safety_blitz", str_repr)
        self.assertIn("slant_hot", str_repr)


class TestPlayCallCompatibility(unittest.TestCase):
    """Test cross-play call interactions"""
    
    def test_offensive_defensive_independence(self):
        """Test that offensive and defensive play calls are independent"""
        offense = OffensivePlayCall(OffensivePlayType.RUN, OffensiveFormation.I_FORMATION)
        defense = DefensivePlayCall(DefensivePlayType.COVER_2, DefensiveFormation.FOUR_THREE)
        
        # Should be able to create both without conflicts
        self.assertEqual(offense.get_play_type(), OffensivePlayType.RUN)
        self.assertEqual(defense.get_play_type(), DefensivePlayType.COVER_2)
        
        # Should not be equal to each other
        self.assertNotEqual(offense, defense)
    
    def test_realistic_matchups(self):
        """Test realistic offensive vs defensive matchups"""
        # Power run vs run defense
        power_run = OffensivePlayCall(OffensivePlayType.RUN, OffensiveFormation.I_FORMATION, concept="power")
        run_defense = DefensivePlayCall(DefensivePlayType.RUN_STUFF, DefensiveFormation.FOUR_SIX)
        
        self.assertTrue(power_run.is_running_play())
        self.assertTrue(run_defense.is_run_defense())
        
        # Four verticals vs prevent defense
        four_verts = OffensivePlayCall(OffensivePlayType.DEEP_BALL, OffensiveFormation.FOUR_WIDE, concept="four_verticals")
        prevent = DefensivePlayCall(DefensivePlayType.PREVENT_DEFENSE, DefensiveFormation.PREVENT)
        
        self.assertTrue(four_verts.is_passing_play())
        self.assertTrue(prevent.is_pass_defense())


if __name__ == '__main__':
    unittest.main(verbosity=2)