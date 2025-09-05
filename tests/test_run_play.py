#!/usr/bin/env python3
"""
Comprehensive unit tests for run play simulation

Tests PlayerStats tracking and RunPlaySimulator functionality including
matchup matrix logic and player stat attribution.
"""

import unittest
import sys
import os
from unittest.mock import patch

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from plays.play_stats import PlayerStats, PlayStatsSummary, create_player_stats_from_player
from plays.run_play import RunPlaySimulator
from player import Player, Position
from personnel_package_manager import TeamRosterGenerator, PersonnelPackageManager
from formation import OffensiveFormation, DefensiveFormation


class TestPlayerStats(unittest.TestCase):
    """Test PlayerStats tracking functionality"""
    
    def setUp(self):
        self.stats = PlayerStats("Test Player", 21, Position.RB)
    
    def test_player_stats_initialization(self):
        """Test PlayerStats initialization"""
        self.assertEqual(self.stats.player_name, "Test Player")
        self.assertEqual(self.stats.player_number, 21)
        self.assertEqual(self.stats.position, Position.RB)
        self.assertEqual(self.stats.carries, 0)
        self.assertEqual(self.stats.rushing_yards, 0)
    
    def test_add_carry(self):
        """Test adding carries and rushing yards"""
        self.stats.add_carry(5)
        self.assertEqual(self.stats.carries, 1)
        self.assertEqual(self.stats.rushing_yards, 5)
        
        self.stats.add_carry(3)
        self.assertEqual(self.stats.carries, 2)
        self.assertEqual(self.stats.rushing_yards, 8)
    
    def test_add_tackle(self):
        """Test adding tackles (solo and assisted)"""
        self.stats.add_tackle(assisted=False)
        self.assertEqual(self.stats.tackles, 1)
        self.assertEqual(self.stats.assisted_tackles, 0)
        
        self.stats.add_tackle(assisted=True)
        self.assertEqual(self.stats.tackles, 1)
        self.assertEqual(self.stats.assisted_tackles, 1)
    
    def test_add_block(self):
        """Test adding blocking attempts"""
        self.stats.add_block(successful=True)
        self.assertEqual(self.stats.blocks_made, 1)
        self.assertEqual(self.stats.blocks_missed, 0)
        
        self.stats.add_block(successful=False)
        self.assertEqual(self.stats.blocks_made, 1)
        self.assertEqual(self.stats.blocks_missed, 1)
    
    def test_get_total_stats(self):
        """Test getting non-zero stats summary"""
        # Initially should be empty
        self.assertEqual(self.stats.get_total_stats(), {})
        
        # Add some stats
        self.stats.add_carry(4)
        self.stats.add_block(successful=True)
        
        total_stats = self.stats.get_total_stats()
        expected_stats = {
            'carries': 1,
            'rushing_yards': 4,
            'blocks_made': 1
        }
        
        for key, value in expected_stats.items():
            self.assertEqual(total_stats[key], value)
    
    def test_create_player_stats_from_player(self):
        """Test creating PlayerStats from Player object"""
        player = Player("John Doe", 23, Position.RB, {"overall": 85})
        stats = create_player_stats_from_player(player)
        
        self.assertEqual(stats.player_name, "John Doe")
        self.assertEqual(stats.player_number, 23)
        self.assertEqual(stats.position, Position.RB)


class TestPlayStatsSummary(unittest.TestCase):
    """Test PlayStatsSummary functionality"""
    
    def setUp(self):
        self.summary = PlayStatsSummary("run", 4, 3.2)
        
        # Add some test player stats
        rb_stats = PlayerStats("RB1", 21, Position.RB)
        rb_stats.add_carry(4)
        
        lb_stats = PlayerStats("MLB", 54, Position.MIKE)
        lb_stats.add_tackle(assisted=False)
        
        self.summary.add_player_stats(rb_stats)
        self.summary.add_player_stats(lb_stats)
    
    def test_play_summary_initialization(self):
        """Test PlayStatsSummary initialization"""
        self.assertEqual(self.summary.play_type, "run")
        self.assertEqual(self.summary.yards_gained, 4)
        self.assertEqual(self.summary.time_elapsed, 3.2)
    
    def test_get_players_with_stats(self):
        """Test getting only players who recorded stats"""
        players_with_stats = self.summary.get_players_with_stats()
        self.assertEqual(len(players_with_stats), 2)
        
        # Check that these players have non-empty stats
        for player in players_with_stats:
            self.assertTrue(len(player.get_total_stats()) > 0)
    
    def test_get_rushing_leader(self):
        """Test getting the rushing leader"""
        rushing_leader = self.summary.get_rushing_leader()
        self.assertIsNotNone(rushing_leader)
        self.assertEqual(rushing_leader.player_name, "RB1")
        self.assertEqual(rushing_leader.carries, 1)
        self.assertEqual(rushing_leader.rushing_yards, 4)
    
    def test_get_leading_tackler(self):
        """Test getting the leading tackler"""
        leading_tackler = self.summary.get_leading_tackler()
        self.assertIsNotNone(leading_tackler)
        self.assertEqual(leading_tackler.player_name, "MLB")
        self.assertEqual(leading_tackler.tackles, 1)


class TestRunPlaySimulator(unittest.TestCase):
    """Test RunPlaySimulator functionality"""
    
    def setUp(self):
        # Generate test rosters
        offense_roster = TeamRosterGenerator.generate_sample_roster("Test Offense")
        defense_roster = TeamRosterGenerator.generate_sample_roster("Test Defense")
        
        # Create personnel managers
        offense_manager = PersonnelPackageManager(offense_roster)
        defense_manager = PersonnelPackageManager(defense_roster)
        
        # Get proper 11-man units
        self.offensive_players = offense_manager.get_offensive_personnel(OffensiveFormation.I_FORMATION)
        self.defensive_players = defense_manager.get_defensive_personnel(DefensiveFormation.FOUR_THREE)
        
        # Create simulator
        self.simulator = RunPlaySimulator(
            offensive_players=self.offensive_players,
            defensive_players=self.defensive_players,
            offensive_formation=OffensiveFormation.I_FORMATION,
            defensive_formation=DefensiveFormation.FOUR_THREE
        )
    
    def test_simulator_initialization(self):
        """Test RunPlaySimulator initialization"""
        self.assertEqual(len(self.simulator.offensive_players), 11)
        self.assertEqual(len(self.simulator.defensive_players), 11)
        self.assertEqual(self.simulator.offensive_formation, OffensiveFormation.I_FORMATION)
        self.assertEqual(self.simulator.defensive_formation, DefensiveFormation.FOUR_THREE)
    
    def test_determine_play_outcome(self):
        """Test play outcome determination"""
        yards_gained, time_elapsed = self.simulator._determine_play_outcome()
        
        # Check reasonable bounds
        self.assertGreaterEqual(yards_gained, 0)
        self.assertLessEqual(yards_gained, 15)  # Reasonable upper bound
        self.assertGreaterEqual(time_elapsed, 2.5)
        self.assertLessEqual(time_elapsed, 5.0)
    
    def test_matchup_matrix_coverage(self):
        """Test that matchup matrix provides expected outcomes"""
        # Create personnel for Nickel defense
        offense_roster = TeamRosterGenerator.generate_sample_roster("Test Offense")
        defense_roster = TeamRosterGenerator.generate_sample_roster("Test Defense")
        
        offense_manager = PersonnelPackageManager(offense_roster)
        defense_manager = PersonnelPackageManager(defense_roster)
        
        offense_players = offense_manager.get_offensive_personnel(OffensiveFormation.I_FORMATION)
        defense_players = defense_manager.get_defensive_personnel(DefensiveFormation.NICKEL)
        
        # Test known matchup
        simulator = RunPlaySimulator(
            offense_players, defense_players,
            OffensiveFormation.I_FORMATION, DefensiveFormation.NICKEL
        )
        
        # Run multiple simulations to test variance
        outcomes = []
        for _ in range(20):
            yards, time = simulator._determine_play_outcome()
            outcomes.append(yards)
        
        # Should have reasonable distribution around expected value
        avg_yards = sum(outcomes) / len(outcomes)
        self.assertGreaterEqual(avg_yards, 3.0)
        self.assertLessEqual(avg_yards, 7.0)
    
    def test_simulate_run_play(self):
        """Test complete run play simulation"""
        summary = self.simulator.simulate_run_play()
        
        # Check play summary
        self.assertEqual(summary.play_type, "run")
        self.assertGreaterEqual(summary.yards_gained, 0)
        self.assertGreater(summary.time_elapsed, 0)
        
        # Should have some player stats
        players_with_stats = summary.get_players_with_stats()
        self.assertGreater(len(players_with_stats), 0)
        
        # Should have a rushing leader
        rushing_leader = summary.get_rushing_leader()
        self.assertIsNotNone(rushing_leader)
        self.assertEqual(rushing_leader.carries, 1)
    
    def test_player_stat_attribution(self):
        """Test that stats are correctly attributed to players"""
        # Run simulation with fixed outcome
        with patch.object(self.simulator, '_determine_play_outcome', return_value=(5, 3.5)):
            summary = self.simulator.simulate_run_play()
        
        # Check that RB got carry stats
        rushing_leader = summary.get_rushing_leader()
        self.assertIsNotNone(rushing_leader)
        self.assertEqual(rushing_leader.carries, 1)
        self.assertEqual(rushing_leader.rushing_yards, 5)
        
        # Check that offensive linemen got blocking stats
        blockers = [stats for stats in summary.player_stats 
                   if stats.blocks_made > 0 or stats.blocks_missed > 0]
        self.assertGreater(len(blockers), 0)
        
        # Check that defenders got tackle stats  
        tacklers = [stats for stats in summary.player_stats 
                   if stats.tackles > 0 or stats.assisted_tackles > 0]
        self.assertGreater(len(tacklers), 0)
    
    def test_find_player_methods(self):
        """Test player finding helper methods"""
        rb = self.simulator._find_player_by_position(Position.RB)
        self.assertIsNotNone(rb)
        self.assertEqual(rb.primary_position, Position.RB)
        
        ol_players = self.simulator._find_players_by_positions([Position.LT, Position.C, Position.RT])
        self.assertGreater(len(ol_players), 0)
        
        for player in ol_players:
            self.assertIn(player.primary_position, [Position.LT, Position.C, Position.RT])
    
    def test_tackler_selection_logic(self):
        """Test tackler selection based on yards gained"""
        potential_tacklers = [p for p in self.defensive_players[:5]]  # Use first 5 defenders
        
        # Short run should have fewer tacklers
        short_run_tacklers = self.simulator._select_tacklers(2, potential_tacklers)
        self.assertGreaterEqual(len(short_run_tacklers), 1)
        self.assertLessEqual(len(short_run_tacklers), 2)
        
        # Long run should potentially have more tacklers
        long_run_tacklers = self.simulator._select_tacklers(8, potential_tacklers)
        self.assertGreaterEqual(len(long_run_tacklers), 1)


class TestIntegration(unittest.TestCase):
    """Integration tests for run play simulation"""
    
    def test_multiple_simulations_consistency(self):
        """Test that multiple simulations produce consistent results"""
        offense_roster = TeamRosterGenerator.generate_sample_roster("Offense")
        defense_roster = TeamRosterGenerator.generate_sample_roster("Defense")
        
        offense_manager = PersonnelPackageManager(offense_roster)
        defense_manager = PersonnelPackageManager(defense_roster)
        
        offense = offense_manager.get_offensive_personnel(OffensiveFormation.SINGLEBACK)
        defense = defense_manager.get_defensive_personnel(DefensiveFormation.FOUR_THREE)
        
        simulator = RunPlaySimulator(
            offense, defense,
            OffensiveFormation.SINGLEBACK,
            DefensiveFormation.FOUR_THREE
        )
        
        results = []
        for _ in range(10):
            summary = simulator.simulate_run_play()
            results.append(summary)
        
        # All should be run plays
        for result in results:
            self.assertEqual(result.play_type, "run")
            self.assertGreaterEqual(result.yards_gained, 0)
            self.assertIsNotNone(result.get_rushing_leader())
    
    def test_different_formations_produce_different_outcomes(self):
        """Test that different formation matchups produce different outcomes"""
        offense_roster = TeamRosterGenerator.generate_sample_roster("Offense")
        defense_roster = TeamRosterGenerator.generate_sample_roster("Defense")
        
        offense_manager = PersonnelPackageManager(offense_roster)
        defense_manager = PersonnelPackageManager(defense_roster)
        
        # Get personnel for different formations
        i_formation_offense = offense_manager.get_offensive_personnel(OffensiveFormation.I_FORMATION)
        four_three_defense = defense_manager.get_defensive_personnel(DefensiveFormation.FOUR_THREE)
        goal_line_defense = defense_manager.get_defensive_personnel(DefensiveFormation.GOAL_LINE)
        
        # Simulate I-Formation vs 4-3 (should be decent)
        sim1 = RunPlaySimulator(i_formation_offense, four_three_defense, 
                               OffensiveFormation.I_FORMATION, DefensiveFormation.FOUR_THREE)
        
        # Simulate I-Formation vs Goal Line (should be worse for offense)
        sim2 = RunPlaySimulator(i_formation_offense, goal_line_defense,
                               OffensiveFormation.I_FORMATION, DefensiveFormation.GOAL_LINE)
        
        # Run multiple simulations and compare averages
        results1 = [sim1.simulate_run_play().yards_gained for _ in range(15)]
        results2 = [sim2.simulate_run_play().yards_gained for _ in range(15)]
        
        avg1 = sum(results1) / len(results1)
        avg2 = sum(results2) / len(results2)
        
        # I-Formation vs 4-3 should generally produce more yards than vs Goal Line
        self.assertGreater(avg1, avg2)


if __name__ == '__main__':
    unittest.main(verbosity=2)