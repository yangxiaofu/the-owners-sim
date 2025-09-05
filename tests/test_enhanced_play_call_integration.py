#!/usr/bin/env python3
"""
Integration tests for enhanced play call system

Tests the complete integration of OffensivePlayCall, DefensivePlayCall,
PlayCallFactory, PlayEngineParams, and play_engine.simulate() to ensure
the enhanced system works correctly end-to-end.
"""

import unittest
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import play_engine
from play_engine_params import PlayEngineParams
from play_calls.offensive_play_call import OffensivePlayCall
from play_calls.defensive_play_call import DefensivePlayCall
from play_calls.play_call_factory import PlayCallFactory
from offensive_play_type import OffensivePlayType
from defensive_play_type import DefensivePlayType
from formation import OffensiveFormation, DefensiveFormation
from personnel_package_manager import TeamRosterGenerator, PersonnelPackageManager
# No longer need PlayCallParams - simplified to only enhanced system


class TestEnhancedPlayCallIntegration(unittest.TestCase):
    """Test integration of enhanced play call system with play engine"""
    
    def setUp(self):
        """Set up test fixtures with team rosters and personnel"""
        # Generate team rosters
        self.offense_roster = TeamRosterGenerator.generate_sample_roster("Test Offense")
        self.defense_roster = TeamRosterGenerator.generate_sample_roster("Test Defense")
        
        # Create personnel managers
        self.offense_manager = PersonnelPackageManager(self.offense_roster)
        self.defense_manager = PersonnelPackageManager(self.defense_roster)
        
        # Get standard personnel packages
        self.i_formation_players = self.offense_manager.get_offensive_personnel(OffensiveFormation.I_FORMATION)
        self.shotgun_players = self.offense_manager.get_offensive_personnel(OffensiveFormation.SHOTGUN)
        self.four_three_players = self.defense_manager.get_defensive_personnel(DefensiveFormation.FOUR_THREE)
        self.nickel_players = self.defense_manager.get_defensive_personnel(DefensiveFormation.NICKEL)
    
    def test_enhanced_run_play_integration(self):
        """Test enhanced run play calls work with play engine"""
        # Create enhanced play calls
        power_run = PlayCallFactory.create_power_run(OffensiveFormation.I_FORMATION)
        run_defense = PlayCallFactory.create_cover_2(DefensiveFormation.FOUR_THREE)
        
        # Create enhanced parameters
        params = PlayEngineParams(
            offensive_players=self.i_formation_players,
            defensive_players=self.four_three_players,
            offensive_play_call=power_run,
            defensive_play_call=run_defense
        )
        
        # Enhanced system is now the only system
        
        # Run simulation
        result = play_engine.simulate(params)
        
        # Verify result
        self.assertEqual(result.outcome, OffensivePlayType.RUN)
        self.assertIsInstance(result.yards, int)
        self.assertGreaterEqual(result.yards, 0)
    
    def test_enhanced_pass_play_integration(self):
        """Test enhanced pass play calls work with play engine"""
        # Create enhanced play calls
        quick_pass = PlayCallFactory.create_quick_pass(OffensiveFormation.SHOTGUN)
        blitz_defense = PlayCallFactory.create_blitz("corner_blitz")
        
        # Create enhanced parameters  
        params = PlayEngineParams(
            offensive_players=self.shotgun_players,
            defensive_players=self.nickel_players,
            offensive_play_call=quick_pass,
            defensive_play_call=blitz_defense
        )
        
        # Verify formation extraction
        self.assertEqual(quick_pass.get_formation(), OffensiveFormation.SHOTGUN)
        self.assertEqual(blitz_defense.get_formation(), DefensiveFormation.NICKEL)
        
        # Run simulation - should handle non-run plays gracefully
        result = play_engine.simulate(params)
        self.assertIsNotNone(result)
    
    def test_factory_situational_play_integration(self):
        """Test factory-created situational plays integrate correctly"""
        # 3rd and long situation
        third_down_offense = PlayCallFactory.create_situational_offense(
            down=3, distance=12, field_position=45
        )
        third_down_defense = PlayCallFactory.create_situational_defense(
            down=3, distance=12, field_position=55
        )
        
        # Should create appropriate plays for 3rd and long
        self.assertTrue(third_down_offense.is_passing_play())
        self.assertTrue(third_down_defense.is_pass_defense())
        
        # Create parameters and simulate
        params = PlayEngineParams(
            offensive_players=self.shotgun_players,  # Appropriate for passing
            defensive_players=self.nickel_players,   # Appropriate for pass defense
            offensive_play_call=third_down_offense,
            defensive_play_call=third_down_defense
        )
        
        result = play_engine.simulate(params)
        self.assertIsNotNone(result)
    
    def test_goal_line_situational_integration(self):
        """Test goal line situation creates appropriate play calls"""
        # Goal line from 1-yard line
        goal_line_offense = PlayCallFactory.create_situational_offense(
            down=1, distance=1, field_position=99
        )
        goal_line_defense = PlayCallFactory.create_situational_defense(
            down=1, distance=1, field_position=1
        )
        
        # Should create goal line plays
        self.assertEqual(goal_line_offense.get_formation(), OffensiveFormation.GOAL_LINE)
        self.assertEqual(goal_line_defense.get_formation(), DefensiveFormation.GOAL_LINE)
        self.assertTrue(goal_line_offense.is_running_play())
        self.assertTrue(goal_line_defense.is_run_defense())
        
        # Get appropriate personnel
        goal_line_offense_players = self.offense_manager.get_offensive_personnel(OffensiveFormation.GOAL_LINE)
        goal_line_defense_players = self.defense_manager.get_defensive_personnel(DefensiveFormation.GOAL_LINE)
        
        params = PlayEngineParams(
            offensive_players=goal_line_offense_players,
            defensive_players=goal_line_defense_players,
            offensive_play_call=goal_line_offense,
            defensive_play_call=goal_line_defense
        )
        
        result = play_engine.simulate(params)
        self.assertEqual(result.outcome, OffensivePlayType.RUN)
    
    def test_formation_extraction_integration(self):
        """Test that play engine correctly extracts formations from play calls"""
        # Create specific formation-based plays
        pistol_run = OffensivePlayCall(
            OffensivePlayType.RUN, 
            OffensiveFormation.PISTOL,
            concept="read_option"
        )
        
        dime_defense = DefensivePlayCall(
            DefensivePlayType.DIME_DEFENSE,
            DefensiveFormation.DIME,
            coverage="deep_zone"
        )
        
        # Get appropriate personnel
        pistol_players = self.offense_manager.get_offensive_personnel(OffensiveFormation.PISTOL)
        dime_players = self.defense_manager.get_defensive_personnel(DefensiveFormation.DIME)
        
        params = PlayEngineParams(
            offensive_players=pistol_players,
            defensive_players=dime_players,
            offensive_play_call=pistol_run,
            defensive_play_call=dime_defense
        )
        
        # The play engine should extract these formations and use them
        result = play_engine.simulate(params)
        self.assertEqual(result.outcome, OffensivePlayType.RUN)
        
    def test_play_call_validation_integration(self):
        """Test that play call validation catches invalid combinations"""
        with self.assertRaises(ValueError):
            # Invalid: Field goal play with regular formation
            invalid_play = OffensivePlayCall(
                OffensivePlayType.FIELD_GOAL,
                OffensiveFormation.I_FORMATION
            )
        
        with self.assertRaises(ValueError):
            # Invalid: Nickel defense play with wrong formation
            invalid_defense = DefensivePlayCall(
                DefensivePlayType.NICKEL_DEFENSE,
                DefensiveFormation.FOUR_THREE
            )
    
    def test_play_call_modification_integration(self):
        """Test that modified play calls work correctly in simulation"""
        # Create base play call
        base_run = PlayCallFactory.create_power_run()
        
        # Modify it
        sweep_run = base_run.with_concept("sweep")
        
        # Both should work in simulation
        base_params = PlayEngineParams(
            offensive_players=self.i_formation_players,
            defensive_players=self.four_three_players,
            offensive_play_call=base_run,
            defensive_play_call=PlayCallFactory.create_cover_2()
        )
        
        sweep_params = PlayEngineParams(
            offensive_players=self.i_formation_players,
            defensive_players=self.four_three_players,
            offensive_play_call=sweep_run,
            defensive_play_call=PlayCallFactory.create_cover_2()
        )
        
        base_result = play_engine.simulate(base_params)
        sweep_result = play_engine.simulate(sweep_params)
        
        # Both should be run plays
        self.assertEqual(base_result.outcome, OffensivePlayType.RUN)
        self.assertEqual(sweep_result.outcome, OffensivePlayType.RUN)
        
        # Concepts should be different
        self.assertEqual(base_run.get_concept(), "power")
        self.assertEqual(sweep_run.get_concept(), "sweep")
    
    def test_available_plays_listing(self):
        """Test that factory provides correct available play listings"""
        offensive_plays = PlayCallFactory.get_available_offensive_plays()
        defensive_plays = PlayCallFactory.get_available_defensive_plays()
        
        # Should have expected plays
        self.assertIn("power_run", offensive_plays)
        self.assertIn("quick_slants", offensive_plays)
        self.assertIn("cover_2_base", defensive_plays)
        self.assertIn("nickel_blitz", defensive_plays)
        
        # Should be able to create all listed plays
        for play_name in offensive_plays:
            play = PlayCallFactory.create_offensive_play(play_name)
            self.assertIsInstance(play, OffensivePlayCall)
        
        for play_name in defensive_plays:
            play = PlayCallFactory.create_defensive_play(play_name)
            self.assertIsInstance(play, DefensivePlayCall)


class TestPlayCallSystemConsistency(unittest.TestCase):
    """Test consistency across the enhanced play call system"""
    
    def test_formation_personnel_consistency(self):
        """Test that play call formations match available personnel"""
        roster = TeamRosterGenerator.generate_sample_roster("Test Team")
        offense_manager = PersonnelPackageManager(roster)
        defense_manager = PersonnelPackageManager(roster)
        
        # Test all factory-created offensive plays
        for play_name in PlayCallFactory.get_available_offensive_plays():
            play_call = PlayCallFactory.create_offensive_play(play_name)
            formation = play_call.get_formation()
            
            # Should be able to get personnel for this formation
            try:
                personnel = offense_manager.get_offensive_personnel(formation)
                self.assertEqual(len(personnel), 11)
            except KeyError:
                self.fail(f"Formation {formation} from play {play_name} not supported by personnel manager")
        
        # Test all factory-created defensive plays  
        for play_name in PlayCallFactory.get_available_defensive_plays():
            play_call = PlayCallFactory.create_defensive_play(play_name)
            formation = play_call.get_formation()
            
            # Should be able to get personnel for this formation
            try:
                personnel = defense_manager.get_defensive_personnel(formation)
                self.assertEqual(len(personnel), 11)
            except KeyError:
                self.fail(f"Formation {formation} from play {play_name} not supported by personnel manager")
    
    def test_play_type_consistency(self):
        """Test that play types are consistent across system"""
        # All factory plays should create valid play call objects
        for play_name in PlayCallFactory.get_available_offensive_plays():
            play_call = PlayCallFactory.create_offensive_play(play_name)
            self.assertIsInstance(play_call, OffensivePlayCall)
            self.assertIsNotNone(play_call.get_play_type())
        
        for play_name in PlayCallFactory.get_available_defensive_plays():
            play_call = PlayCallFactory.create_defensive_play(play_name)
            self.assertIsInstance(play_call, DefensivePlayCall)
            self.assertIsNotNone(play_call.get_play_type())
    
    def test_situational_play_calling_coverage(self):
        """Test that situational play calling covers common scenarios"""
        # Test various down and distance scenarios
        scenarios = [
            (1, 10, 25),  # 1st and 10 from own 25
            (2, 3, 67),   # 2nd and 3 in red zone
            (3, 8, 45),   # 3rd and long midfield
            (4, 1, 98),   # 4th and inches at goal line
            (1, 10, 95),  # 1st and goal from 5
            (3, 15, 15),  # 3rd and very long in own territory
        ]
        
        for down, distance, field_position in scenarios:
            offense_call = PlayCallFactory.create_situational_offense(down, distance, field_position)
            defense_call = PlayCallFactory.create_situational_defense(down, distance, 100 - field_position)
            
            # Should create valid play calls
            self.assertIsInstance(offense_call, OffensivePlayCall)
            self.assertIsInstance(defense_call, DefensivePlayCall)
            
            # Play calls should make situational sense
            if distance <= 2 and down >= 3:
                # Short yardage should favor running
                self.assertTrue(offense_call.is_running_play())
                self.assertTrue(defense_call.is_run_defense())
            elif distance >= 8 and down == 3:
                # 3rd and long should favor passing
                self.assertTrue(offense_call.is_passing_play())
                self.assertTrue(defense_call.is_pass_defense())


if __name__ == '__main__':
    unittest.main(verbosity=2)