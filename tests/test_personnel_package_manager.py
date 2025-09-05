#!/usr/bin/env python3
"""
Comprehensive unit tests for PersonnelPackageManager

Tests all aspects of player selection, formation mapping, and validation
for both offensive and defensive personnel packages.
"""

import unittest
import sys
import os
from unittest.mock import patch, MagicMock
from typing import List, Dict

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from player import Player, Position
from personnel_package_manager import PersonnelPackageManager, TeamRosterGenerator
from formation import OffensiveFormation, DefensiveFormation, FormationMapper
from play_engine.play_types.offensive_types import OffensivePlayType
from play_engine.play_types.defensive_types import DefensivePlayType


class TestPersonnelPackageManager(unittest.TestCase):
    """Test PersonnelPackageManager core functionality"""
    
    def setUp(self):
        """Set up test fixtures with a complete roster"""
        self.test_roster = TeamRosterGenerator.generate_sample_roster("Test Team")
        self.manager = PersonnelPackageManager(self.test_roster)
        
        # Create a minimal roster for edge case testing
        self.minimal_roster = [
            Player("QB1", 1, Position.QB, {"overall": 80}),
            Player("RB1", 21, Position.RB, {"overall": 75}),
            Player("WR1", 11, Position.WR, {"overall": 85}),
            Player("WR2", 13, Position.WR, {"overall": 80}),
            Player("TE1", 87, Position.TE, {"overall": 75}),
            Player("LT1", 73, Position.LT, {"overall": 80}),
            Player("LG1", 67, Position.LG, {"overall": 75}),
            Player("C1", 55, Position.C, {"overall": 80}),
            Player("RG1", 65, Position.RG, {"overall": 75}),
            Player("RT1", 71, Position.RT, {"overall": 80}),
            Player("FB1", 44, Position.FB, {"overall": 70})
        ]
    
    def test_initialization(self):
        """Test PersonnelPackageManager initialization"""
        manager = PersonnelPackageManager(self.test_roster)
        
        # Check that roster is stored
        self.assertEqual(len(manager.roster), len(self.test_roster))
        
        # Check that position groups are organized
        self.assertIsInstance(manager.position_groups, dict)
        self.assertGreater(len(manager.position_groups), 0)
        
        # Check that QB position group exists and is sorted by rating
        qb_group = manager.position_groups.get(Position.QB, [])
        self.assertGreater(len(qb_group), 0)
        
        # Verify QBs are sorted by overall rating (descending)
        if len(qb_group) > 1:
            for i in range(len(qb_group) - 1):
                self.assertGreaterEqual(
                    qb_group[i].get_rating('overall'),
                    qb_group[i + 1].get_rating('overall')
                )
    
    def test_position_organization(self):
        """Test that players are correctly organized by position"""
        # Count expected positions from roster
        position_counts = {}
        for player in self.test_roster:
            position = player.primary_position
            position_counts[position] = position_counts.get(position, 0) + 1
        
        # Verify position groups match expected counts
        for position, expected_count in position_counts.items():
            actual_count = len(self.manager.position_groups.get(position, []))
            self.assertEqual(actual_count, expected_count, 
                           f"Position {position} count mismatch")
    
    def test_personnel_package_validation(self):
        """Test personnel package validation"""
        # Test valid package (11 unique players)
        valid_players = self.test_roster[:11]
        self.assertTrue(self.manager.validate_personnel_package(valid_players))
        
        # Test invalid packages
        # Too few players
        self.assertFalse(self.manager.validate_personnel_package(self.test_roster[:10]))
        
        # Too many players
        self.assertFalse(self.manager.validate_personnel_package(self.test_roster[:12]))
        
        # Duplicate players
        duplicate_players = self.test_roster[:10] + [self.test_roster[0]]
        self.assertFalse(self.manager.validate_personnel_package(duplicate_players))
    
    def test_personnel_summary(self):
        """Test personnel summary generation"""
        # Create test players with known positions
        test_players = [
            Player("QB", 1, Position.QB),
            Player("RB", 21, Position.RB),
            Player("WR1", 11, Position.WR),
            Player("WR2", 13, Position.WR),
            Player("TE", 87, Position.TE),
        ]
        
        summary = self.manager.get_personnel_summary(test_players)
        
        expected_summary = {
            Position.QB: 1,
            Position.RB: 1,
            Position.WR: 2,
            Position.TE: 1
        }
        
        self.assertEqual(summary, expected_summary)
    
    def test_generic_player_creation(self):
        """Test generic player creation for insufficient roster scenarios"""
        generic_player = self.manager._create_generic_player(5)
        
        self.assertEqual(generic_player.number, 95)  # 90 + 5
        self.assertEqual(generic_player.primary_position, Position.WR)
        self.assertEqual(generic_player.get_rating('overall'), 60)
        self.assertIn("Generic Player", generic_player.name)


class TestOffensivePersonnel(unittest.TestCase):
    """Test offensive personnel selection for all play types"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_roster = TeamRosterGenerator.generate_sample_roster("Offense Test")
        self.manager = PersonnelPackageManager(self.test_roster)
    
    def test_all_offensive_play_types(self):
        """Test that all offensive play types return valid personnel"""
        offensive_play_types = [
            OffensivePlayType.RUN,
            OffensivePlayType.PASS,
            OffensivePlayType.PLAY_ACTION_PASS,
            OffensivePlayType.SCREEN_PASS,
            OffensivePlayType.QUICK_SLANT,
            OffensivePlayType.DEEP_BALL,
            OffensivePlayType.FIELD_GOAL,
            OffensivePlayType.PUNT,
            OffensivePlayType.KICKOFF,
            OffensivePlayType.TWO_POINT_CONVERSION,
            OffensivePlayType.KNEEL_DOWN,
            OffensivePlayType.SPIKE
        ]
        
        for play_type in offensive_play_types:
            with self.subTest(play_type=play_type):
                personnel = self.manager.get_offensive_personnel_for_play(play_type)
                
                # Basic validation
                self.assertEqual(len(personnel), 11, f"Play type {play_type} should have 11 players")
                self.assertTrue(self.manager.validate_personnel_package(personnel))
                
                # Check formation mapping
                formation = self.manager.get_formation_for_play(play_type, 'offense')
                self.assertIsNotNone(formation)
    
    def test_i_formation_personnel(self):
        """Test I-Formation personnel for run plays"""
        personnel = self.manager.get_offensive_personnel_for_play(OffensivePlayType.RUN)
        summary = self.manager.get_personnel_summary(personnel)
        
        # I-Formation should have: QB, RB, FB, 2 WR, 1 TE, 5 OL
        expected_positions = {
            Position.QB: 1,
            Position.RB: 1,
            Position.FB: 1,
            Position.WR: 2,
            Position.TE: 1,
            Position.LT: 1,
            Position.LG: 1,
            Position.C: 1,
            Position.RG: 1,
            Position.RT: 1
        }
        
        for position, count in expected_positions.items():
            self.assertGreaterEqual(
                summary.get(position, 0), count,
                f"I-Formation should have at least {count} {position}"
            )
    
    def test_field_goal_personnel(self):
        """Test field goal unit personnel"""
        personnel = self.manager.get_offensive_personnel_for_play(OffensivePlayType.FIELD_GOAL)
        summary = self.manager.get_personnel_summary(personnel)
        
        # Field goal unit should have specialists
        self.assertGreaterEqual(summary.get(Position.K, 0), 1, "Should have kicker")
        self.assertGreaterEqual(summary.get(Position.H, 0), 1, "Should have holder")
        self.assertGreaterEqual(summary.get(Position.LS, 0), 1, "Should have long snapper")
        
        # Should have protection
        total_linemen = sum(summary.get(pos, 0) for pos in 
                          [Position.LT, Position.LG, Position.RG, Position.RT])
        self.assertGreaterEqual(total_linemen, 4, "Should have offensive line protection")
    
    def test_punt_personnel(self):
        """Test punt unit personnel"""
        personnel = self.manager.get_offensive_personnel_for_play(OffensivePlayType.PUNT)
        summary = self.manager.get_personnel_summary(personnel)
        
        # Punt unit should have punter and long snapper
        self.assertGreaterEqual(summary.get(Position.P, 0), 1, "Should have punter")
        self.assertGreaterEqual(summary.get(Position.LS, 0), 1, "Should have long snapper")
    
    def test_kickoff_personnel(self):
        """Test kickoff unit personnel"""
        personnel = self.manager.get_offensive_personnel_for_play(OffensivePlayType.KICKOFF)
        summary = self.manager.get_personnel_summary(personnel)
        
        # Kickoff unit should have kicker and coverage specialists
        self.assertGreaterEqual(summary.get(Position.K, 0), 1, "Should have kicker")
        self.assertGreaterEqual(summary.get(Position.WR, 0), 1, "Should have coverage players")


class TestDefensivePersonnel(unittest.TestCase):
    """Test defensive personnel selection for all play types"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_roster = TeamRosterGenerator.generate_sample_roster("Defense Test")
        self.manager = PersonnelPackageManager(self.test_roster)
    
    def test_all_defensive_play_types(self):
        """Test that all defensive play types return valid personnel"""
        defensive_play_types = [
            DefensivePlayType.COVER_0,
            DefensivePlayType.COVER_1,
            DefensivePlayType.COVER_2,
            DefensivePlayType.COVER_3,
            DefensivePlayType.MAN_COVERAGE,
            DefensivePlayType.ZONE_COVERAGE,
            DefensivePlayType.FOUR_MAN_RUSH,
            DefensivePlayType.BLITZ,
            DefensivePlayType.CORNER_BLITZ,
            DefensivePlayType.SAFETY_BLITZ,
            DefensivePlayType.NICKEL_DEFENSE,
            DefensivePlayType.DIME_DEFENSE,
            DefensivePlayType.GOAL_LINE_DEFENSE,
            DefensivePlayType.PREVENT_DEFENSE,
            DefensivePlayType.RUN_STUFF
        ]
        
        for play_type in defensive_play_types:
            with self.subTest(play_type=play_type):
                personnel = self.manager.get_defensive_personnel_for_play(play_type)
                
                # Basic validation
                self.assertEqual(len(personnel), 11, f"Play type {play_type} should have 11 players")
                self.assertTrue(self.manager.validate_personnel_package(personnel))
                
                # Check formation mapping
                formation = self.manager.get_formation_for_play(play_type, 'defense')
                self.assertIsNotNone(formation)
    
    def test_four_three_base_personnel(self):
        """Test 4-3 base defense personnel"""
        personnel = self.manager.get_defensive_personnel_for_play(DefensivePlayType.COVER_2)
        summary = self.manager.get_personnel_summary(personnel)
        
        # 4-3 base should have: 2 DE, 2 DT, Mike/Sam/Will, 2 CB, FS, SS
        expected_positions = {
            Position.DE: 2,
            Position.DT: 2,
            Position.MIKE: 1,
            Position.SAM: 1,
            Position.WILL: 1,
            Position.CB: 2,
            Position.FS: 1,
            Position.SS: 1
        }
        
        for position, count in expected_positions.items():
            actual_count = summary.get(position, 0)
            self.assertGreaterEqual(
                actual_count, count,
                f"4-3 base should have at least {count} {position}, got {actual_count}"
            )
    
    def test_nickel_defense_personnel(self):
        """Test nickel defense personnel"""
        personnel = self.manager.get_defensive_personnel_for_play(DefensivePlayType.NICKEL_DEFENSE)
        summary = self.manager.get_personnel_summary(personnel)
        
        # Nickel should have extra DB coverage
        total_dbs = sum(summary.get(pos, 0) for pos in [Position.CB, Position.NCB, Position.FS, Position.SS])
        self.assertGreaterEqual(total_dbs, 5, "Nickel defense should have 5+ DBs")
        
        # Should have nickel corner
        self.assertGreaterEqual(summary.get(Position.NCB, 0), 1, "Should have nickel corner")
    
    def test_dime_defense_personnel(self):
        """Test dime defense personnel"""
        personnel = self.manager.get_defensive_personnel_for_play(DefensivePlayType.DIME_DEFENSE)
        summary = self.manager.get_personnel_summary(personnel)
        
        # Dime should have even more DB coverage
        total_dbs = sum(summary.get(pos, 0) for pos in [Position.CB, Position.NCB, Position.FS, Position.SS])
        self.assertGreaterEqual(total_dbs, 6, "Dime defense should have 6+ DBs")
        
        # Should have multiple nickel corners
        self.assertGreaterEqual(summary.get(Position.NCB, 0), 1, "Should have nickel coverage")
    
    def test_goal_line_defense_personnel(self):
        """Test goal line defense personnel"""
        personnel = self.manager.get_defensive_personnel_for_play(DefensivePlayType.GOAL_LINE_DEFENSE)
        summary = self.manager.get_personnel_summary(personnel)
        
        # Goal line should have heavy run-stopping personnel
        total_linemen = sum(summary.get(pos, 0) for pos in [Position.DE, Position.DT, Position.NT])
        total_linebackers = sum(summary.get(pos, 0) for pos in [Position.MIKE, Position.SAM, Position.WILL, Position.ILB, Position.OLB])
        
        self.assertGreaterEqual(total_linemen, 4, "Goal line should have heavy D-line")
        self.assertGreaterEqual(total_linebackers, 2, "Goal line should have multiple linebackers")
    
    def test_blitz_package_personnel(self):
        """Test blitz package personnel"""
        personnel = self.manager.get_defensive_personnel_for_play(DefensivePlayType.BLITZ)
        summary = self.manager.get_personnel_summary(personnel)
        
        # Blitz package should have extra rushers/safeties
        total_safeties = sum(summary.get(pos, 0) for pos in [Position.FS, Position.SS])
        self.assertGreaterEqual(total_safeties, 1, "Blitz should have safety support")


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error conditions"""
    
    def test_empty_roster(self):
        """Test behavior with empty roster"""
        empty_manager = PersonnelPackageManager([])
        
        # Should still return 11 players (all generic)
        personnel = empty_manager.get_offensive_personnel_for_play(OffensivePlayType.RUN)
        self.assertEqual(len(personnel), 11)
        
        # All should be generic players
        for player in personnel:
            self.assertIn("Generic Player", player.name)
    
    def test_insufficient_players(self):
        """Test behavior with insufficient players for a position"""
        # Create roster with only 1 QB but formations might need more flexibility
        limited_roster = [
            Player("QB1", 1, Position.QB, {"overall": 80}),
            Player("RB1", 21, Position.RB, {"overall": 75}),
            # Missing many positions
        ]
        
        limited_manager = PersonnelPackageManager(limited_roster)
        personnel = limited_manager.get_offensive_personnel_for_play(OffensivePlayType.RUN)
        
        # Should still get 11 players
        self.assertEqual(len(personnel), 11)
        
        # Should have at least the available players
        qb_count = sum(1 for p in personnel if p.primary_position == Position.QB)
        self.assertGreaterEqual(qb_count, 1)
    
    def test_missing_specialist_positions(self):
        """Test behavior when specialist positions are missing"""
        # Create roster without kicker
        no_kicker_roster = [p for p in TeamRosterGenerator.generate_sample_roster() 
                           if p.primary_position != Position.K]
        
        no_kicker_manager = PersonnelPackageManager(no_kicker_roster)
        personnel = no_kicker_manager.get_offensive_personnel_for_play(OffensivePlayType.FIELD_GOAL)
        
        # Should still get 11 players
        self.assertEqual(len(personnel), 11)
        
        # Should validate as legal personnel package
        self.assertTrue(no_kicker_manager.validate_personnel_package(personnel))
    
    def test_formation_mapping_consistency(self):
        """Test that formation mapping is consistent"""
        manager = PersonnelPackageManager(TeamRosterGenerator.generate_sample_roster())
        
        # Test same play type multiple times
        play_type = OffensivePlayType.RUN
        formation1 = manager.get_formation_for_play(play_type, 'offense')
        formation2 = manager.get_formation_for_play(play_type, 'offense')
        
        self.assertEqual(formation1, formation2, "Formation mapping should be consistent")
    
    def test_player_selection_quality(self):
        """Test that higher-rated players are selected first"""
        # Create roster with varying ratings at same position
        test_roster = [
            Player("QB High", 1, Position.QB, {"overall": 95}),
            Player("QB Med", 2, Position.QB, {"overall": 75}),
            Player("QB Low", 3, Position.QB, {"overall": 55}),
        ]
        
        # Add other positions to fill out roster
        test_roster.extend(TeamRosterGenerator.generate_sample_roster()[3:])
        
        manager = PersonnelPackageManager(test_roster)
        personnel = manager.get_offensive_personnel_for_play(OffensivePlayType.PASS)
        
        # Find the QB in the personnel
        qb_in_personnel = None
        for player in personnel:
            if player.primary_position == Position.QB:
                qb_in_personnel = player
                break
        
        self.assertIsNotNone(qb_in_personnel)
        # Should select the highest-rated QB
        self.assertEqual(qb_in_personnel.name, "QB High")


class TestIntegration(unittest.TestCase):
    """Integration tests with real play scenarios"""
    
    def setUp(self):
        """Set up integration test fixtures"""
        self.lions_roster = TeamRosterGenerator.generate_sample_roster("Detroit Lions")
        self.commanders_roster = TeamRosterGenerator.generate_sample_roster("Washington Commanders") 
        
        self.lions_manager = PersonnelPackageManager(self.lions_roster)
        self.commanders_manager = PersonnelPackageManager(self.commanders_roster)
    
    def test_realistic_game_scenario(self):
        """Test realistic game scenarios with different play matchups"""
        scenarios = [
            (OffensivePlayType.RUN, DefensivePlayType.COVER_2),
            (OffensivePlayType.PASS, DefensivePlayType.BLITZ),
            (OffensivePlayType.FIELD_GOAL, DefensivePlayType.GOAL_LINE_DEFENSE),
            (OffensivePlayType.PUNT, DefensivePlayType.PREVENT_DEFENSE),
            (OffensivePlayType.DEEP_BALL, DefensivePlayType.DIME_DEFENSE)
        ]
        
        for offensive_play, defensive_play in scenarios:
            with self.subTest(offense=offensive_play, defense=defensive_play):
                # Get personnel for both sides
                offensive_personnel = self.lions_manager.get_offensive_personnel_for_play(offensive_play)
                defensive_personnel = self.commanders_manager.get_defensive_personnel_for_play(defensive_play)
                
                # Validate both sides
                self.assertEqual(len(offensive_personnel), 11)
                self.assertEqual(len(defensive_personnel), 11)
                self.assertTrue(self.lions_manager.validate_personnel_package(offensive_personnel))
                self.assertTrue(self.commanders_manager.validate_personnel_package(defensive_personnel))
                
                # Check formations are appropriate
                off_formation = self.lions_manager.get_formation_for_play(offensive_play, 'offense')
                def_formation = self.commanders_manager.get_formation_for_play(defensive_play, 'defense')
                
                self.assertIsNotNone(off_formation)
                self.assertIsNotNone(def_formation)
    
    def test_special_teams_coordination(self):
        """Test special teams scenarios"""
        # Kickoff vs Kick Return
        kickoff_personnel = self.lions_manager.get_offensive_personnel_for_play(OffensivePlayType.KICKOFF)
        kickoff_summary = self.lions_manager.get_personnel_summary(kickoff_personnel)
        
        # Should have kicker and coverage team
        self.assertGreaterEqual(kickoff_summary.get(Position.K, 0), 1)
        self.assertGreaterEqual(kickoff_summary.get(Position.WR, 0), 1, "Should have coverage specialists")
    
    def test_performance_with_large_roster(self):
        """Test performance with realistically large roster"""
        large_roster = []
        
        # Create multiple players at each position
        positions = Position.get_offensive_positions() + Position.get_defensive_positions()
        for position in positions:
            for i in range(3):  # 3 players per position
                large_roster.append(
                    Player(f"{position} {i+1}", i*10, position, {"overall": 70 + i*5})
                )
        
        large_manager = PersonnelPackageManager(large_roster)
        
        # Should still work efficiently
        personnel = large_manager.get_offensive_personnel_for_play(OffensivePlayType.RUN)
        self.assertEqual(len(personnel), 11)
        self.assertTrue(large_manager.validate_personnel_package(personnel))


class TestFormationBasedPersonnel(unittest.TestCase):
    """Test the new formation-based personnel selection methods"""
    
    def setUp(self):
        self.roster = TeamRosterGenerator.generate_sample_roster()
        self.manager = PersonnelPackageManager(self.roster)
    
    def test_offensive_formation_direct_selection(self):
        """Test direct formation-based offensive personnel selection"""
        # Test I-Formation directly
        i_formation_players = self.manager.get_offensive_personnel(OffensiveFormation.I_FORMATION)
        summary = self.manager.get_personnel_summary(i_formation_players)
        
        # I-Formation should have QB, RB, FB, 2 WR, TE, 5 OL
        self.assertEqual(summary.get(Position.QB), 1)
        self.assertEqual(summary.get(Position.RB), 1)
        self.assertEqual(summary.get(Position.FB), 1)
        self.assertEqual(summary.get(Position.WR), 2)
        self.assertEqual(summary.get(Position.TE), 1)
        self.assertEqual(len(i_formation_players), 11)
        
        # Test Shotgun formation directly  
        shotgun_players = self.manager.get_offensive_personnel(OffensiveFormation.SHOTGUN)
        shotgun_summary = self.manager.get_personnel_summary(shotgun_players)
        
        # Shotgun should have QB, RB, 3 WR, TE, 5 OL
        self.assertEqual(shotgun_summary.get(Position.QB), 1)
        self.assertEqual(shotgun_summary.get(Position.RB), 1)
        self.assertEqual(shotgun_summary.get(Position.WR), 3)
        self.assertEqual(shotgun_summary.get(Position.TE), 1)
        self.assertEqual(len(shotgun_players), 11)
        
    def test_defensive_formation_direct_selection(self):
        """Test direct formation-based defensive personnel selection"""
        # Test 4-3 base directly
        four_three_players = self.manager.get_defensive_personnel(DefensiveFormation.FOUR_THREE)
        summary = self.manager.get_personnel_summary(four_three_players)
        
        # 4-3 should have 2 DE, 2 DT, Mike/Sam/Will, 2 CB, FS, SS
        self.assertEqual(summary.get(Position.DE), 2)
        self.assertEqual(summary.get(Position.DT), 2)
        self.assertEqual(summary.get(Position.MIKE), 1)
        self.assertEqual(summary.get(Position.SAM), 1)
        self.assertEqual(summary.get(Position.WILL), 1)
        self.assertEqual(summary.get(Position.CB), 2)
        self.assertEqual(summary.get(Position.FS), 1)
        self.assertEqual(summary.get(Position.SS), 1)
        self.assertEqual(len(four_three_players), 11)
        
        # Test Nickel defense directly
        nickel_players = self.manager.get_defensive_personnel(DefensiveFormation.NICKEL)
        nickel_summary = self.manager.get_personnel_summary(nickel_players)
        
        # Nickel should have extra DB coverage
        total_dbs = sum(nickel_summary.get(pos, 0) for pos in [Position.CB, Position.NCB, Position.FS, Position.SS])
        self.assertGreaterEqual(total_dbs, 5, "Nickel should have 5+ DBs")
        self.assertEqual(len(nickel_players), 11)
        
    def test_backward_compatibility(self):
        """Test that old play-type methods still work"""
        # Old method should still work
        old_method_players = self.manager.get_offensive_personnel_for_play(OffensivePlayType.RUN)
        
        # New method should give same result
        new_method_players = self.manager.get_offensive_personnel(OffensiveFormation.I_FORMATION)
        
        old_summary = self.manager.get_personnel_summary(old_method_players)
        new_summary = self.manager.get_personnel_summary(new_method_players)
        
        self.assertEqual(old_summary, new_summary, 
                        "Backward compatibility methods should work identically")
        
    def test_formation_consistency(self):
        """Test that formation requirements are consistently applied"""
        formations_to_test = [
            OffensiveFormation.I_FORMATION,
            OffensiveFormation.SHOTGUN, 
            OffensiveFormation.FOUR_WIDE,
            OffensiveFormation.GOAL_LINE
        ]
        
        for formation in formations_to_test:
            with self.subTest(formation=formation):
                players = self.manager.get_offensive_personnel(formation)
                self.assertEqual(len(players), 11, f"{formation} should have exactly 11 players")
                self.assertTrue(self.manager.validate_personnel_package(players), 
                              f"{formation} should produce valid personnel package")


if __name__ == '__main__':
    # Run specific test classes or all tests
    unittest.main(verbosity=2)