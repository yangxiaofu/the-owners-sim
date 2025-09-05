#!/usr/bin/env python3
"""
Comprehensive unit tests for punt play simulation

Tests PuntSimulator functionality including all punt scenarios, four-phase penalty integration,
formation matchups, and individual player stat attribution.
"""

import unittest
import sys
import os
from unittest.mock import patch, MagicMock

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from play_engine.simulation.punt import PuntSimulator, PuntPlayParams, PuntResult
from play_engine.simulation.stats import PlayerStats, PlayStatsSummary, create_player_stats_from_player
from play_engine.play_types.offensive_types import PuntPlayType
from play_engine.play_types.defensive_types import DefensivePlayType
from play_engine.play_types.punt_types import PuntOutcome
from play_engine.mechanics.penalties.penalty_engine import PlayContext, PenaltyResult
from team_management.players.player import Player, Position


class TestPuntPlayParams(unittest.TestCase):
    """Test PuntPlayParams input validation"""
    
    def test_valid_punt_play_params(self):
        """Test valid PuntPlayParams initialization"""
        context = PlayContext(
            play_type="punt",
            offensive_formation="PUNT",
            defensive_formation="defensive_punt_return"
        )
        
        params = PuntPlayParams(
            punt_type=PuntPlayType.REAL_PUNT,
            defensive_formation=DefensivePlayType.PUNT_RETURN,
            context=context
        )
        
        self.assertEqual(params.punt_type, PuntPlayType.REAL_PUNT)
        self.assertEqual(params.defensive_formation, DefensivePlayType.PUNT_RETURN)
        self.assertEqual(params.context, context)
    
    def test_invalid_punt_type(self):
        """Test invalid punt type raises ValueError"""
        context = PlayContext()
        
        with self.assertRaises(ValueError) as cm:
            PuntPlayParams(
                punt_type="invalid_punt_type",
                defensive_formation=DefensivePlayType.PUNT_RETURN,
                context=context
            )
        
        self.assertIn("Invalid punt type", str(cm.exception))
    
    def test_invalid_defensive_formation(self):
        """Test invalid defensive formation raises ValueError"""
        context = PlayContext()
        
        with self.assertRaises(ValueError) as cm:
            PuntPlayParams(
                punt_type=PuntPlayType.REAL_PUNT,
                defensive_formation="invalid_defense",
                context=context
            )
        
        self.assertIn("Invalid punt defensive formation", str(cm.exception))


class TestPuntEnums(unittest.TestCase):
    """Test punt-related enum functionality"""
    
    def test_punt_play_type_constants(self):
        """Test PuntPlayType constants"""
        self.assertEqual(PuntPlayType.REAL_PUNT, "punt_real")
        self.assertEqual(PuntPlayType.FAKE_PUNT_PASS, "punt_fake_pass")
        self.assertEqual(PuntPlayType.FAKE_PUNT_RUN, "punt_fake_run")
    
    def test_punt_play_type_methods(self):
        """Test PuntPlayType utility methods"""
        all_types = PuntPlayType.get_all_types()
        self.assertEqual(len(all_types), 3)
        self.assertIn(PuntPlayType.REAL_PUNT, all_types)
        self.assertIn(PuntPlayType.FAKE_PUNT_PASS, all_types)
        self.assertIn(PuntPlayType.FAKE_PUNT_RUN, all_types)
        
        # Test is_fake_punt method
        self.assertFalse(PuntPlayType.is_fake_punt(PuntPlayType.REAL_PUNT))
        self.assertTrue(PuntPlayType.is_fake_punt(PuntPlayType.FAKE_PUNT_PASS))
        self.assertTrue(PuntPlayType.is_fake_punt(PuntPlayType.FAKE_PUNT_RUN))
    
    def test_punt_outcome_constants(self):
        """Test PuntOutcome constants"""
        self.assertEqual(PuntOutcome.FAIR_CATCH, "punt_fair_catch")
        self.assertEqual(PuntOutcome.PUNT_RETURN, "punt_return")
        self.assertEqual(PuntOutcome.TOUCHBACK, "punt_touchback")
        self.assertEqual(PuntOutcome.BLOCKED, "punt_blocked")
    
    def test_punt_outcome_methods(self):
        """Test PuntOutcome utility methods"""
        real_outcomes = PuntOutcome.get_real_punt_outcomes()
        self.assertEqual(len(real_outcomes), 9)
        self.assertIn(PuntOutcome.FAIR_CATCH, real_outcomes)
        self.assertIn(PuntOutcome.PUNT_RETURN, real_outcomes)
        self.assertNotIn(PuntOutcome.FAKE_SUCCESS, real_outcomes)
        
        fake_outcomes = PuntOutcome.get_fake_punt_outcomes()
        self.assertEqual(len(fake_outcomes), 3)
        self.assertIn(PuntOutcome.FAKE_SUCCESS, fake_outcomes)
        self.assertNotIn(PuntOutcome.FAIR_CATCH, fake_outcomes)
        
        # Test utility methods
        self.assertTrue(PuntOutcome.is_successful_punt(PuntOutcome.FAIR_CATCH))
        self.assertTrue(PuntOutcome.is_successful_punt(PuntOutcome.TOUCHBACK))
        self.assertFalse(PuntOutcome.is_successful_punt(PuntOutcome.BLOCKED))
        
        self.assertTrue(PuntOutcome.involves_return(PuntOutcome.PUNT_RETURN))
        self.assertTrue(PuntOutcome.involves_return(PuntOutcome.MUFFED))
        self.assertFalse(PuntOutcome.involves_return(PuntOutcome.FAIR_CATCH))
        
        self.assertTrue(PuntOutcome.is_turnover(PuntOutcome.BLOCKED))
        self.assertTrue(PuntOutcome.is_turnover(PuntOutcome.MUFFED))
        self.assertFalse(PuntOutcome.is_turnover(PuntOutcome.FAIR_CATCH))
    
    def test_defensive_punt_formations(self):
        """Test defensive punt formations"""
        punt_defenses = DefensivePlayType.get_punt_defenses()
        self.assertEqual(len(punt_defenses), 4)
        self.assertIn(DefensivePlayType.PUNT_RETURN, punt_defenses)
        self.assertIn(DefensivePlayType.PUNT_BLOCK, punt_defenses)
        self.assertIn(DefensivePlayType.PUNT_SAFE, punt_defenses)
        self.assertIn(DefensivePlayType.SPREAD_RETURN, punt_defenses)


class TestPuntSimulator(unittest.TestCase):
    """Test PuntSimulator functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create mock players
        self.offensive_players = []
        self.defensive_players = []
        
        # Create punter
        punter = MagicMock()
        punter.name = "Test Punter"
        punter.primary_position = Position.P
        punter.get_rating.return_value = 80
        self.offensive_players.append(punter)
        
        # Create other offensive players
        for i in range(10):
            player = MagicMock()
            player.name = f"Offensive Player {i}"
            player.primary_position = Position.LB if i < 5 else Position.CB
            player.get_rating.return_value = 75
            self.offensive_players.append(player)
        
        # Create returner
        returner = MagicMock()
        returner.name = "Test Returner"
        returner.primary_position = Position.CB
        returner.get_rating.return_value = 80
        self.defensive_players.append(returner)
        
        # Create other defensive players
        for i in range(10):
            player = MagicMock()
            player.name = f"Defensive Player {i}"
            player.primary_position = Position.LB if i < 5 else Position.CB
            player.get_rating.return_value = 75
            self.defensive_players.append(player)
        
        # Create simulator
        self.simulator = PuntSimulator(
            offensive_players=self.offensive_players,
            defensive_players=self.defensive_players,
            offensive_formation="PUNT",
            defensive_formation="defensive_punt_return"
        )
    
    def test_simulator_initialization(self):
        """Test PuntSimulator initialization"""
        self.assertEqual(len(self.simulator.offensive_players), 11)
        self.assertEqual(len(self.simulator.defensive_players), 11)
        self.assertEqual(self.simulator.offensive_formation, "PUNT")
        self.assertEqual(self.simulator.defensive_formation, "defensive_punt_return")
        
        # Check that key players were identified
        self.assertIsNotNone(self.simulator.punter)
        self.assertIsNotNone(self.simulator.returner)
        self.assertEqual(self.simulator.punter.name, "Test Punter")
        self.assertEqual(self.simulator.returner.name, "Test Returner")
    
    @patch('random.random')
    def test_real_punt_fair_catch(self, mock_random):
        """Test real punt resulting in fair catch"""
        # Mock randomness to ensure specific outcome
        mock_random.side_effect = [0.8, 0.9, 0.9, 0.1, 0.5]  # No block, no out of bounds, no illegal touching, no muff, no downed, fair catch
        
        context = PlayContext(play_type="punt", field_position=50)
        params = PuntPlayParams(
            punt_type=PuntPlayType.REAL_PUNT,
            defensive_formation=DefensivePlayType.PUNT_RETURN,
            context=context
        )
        
        with patch.object(self.simulator.penalty_engine, 'check_pre_snap_penalty') as mock_pre_penalty, \
             patch.object(self.simulator.penalty_engine, 'check_during_play_penalty') as mock_during_penalty, \
             patch.object(self.simulator.penalty_engine, 'check_post_play_penalty') as mock_post_penalty:
            
            # Mock no penalties
            mock_pre_penalty.return_value = MagicMock(penalty_occurred=False)
            mock_during_penalty.return_value = MagicMock(penalty_occurred=False)
            mock_post_penalty.return_value = MagicMock(penalty_occurred=False)
            
            result = self.simulator.simulate_punt_play(params)
            
            self.assertIsInstance(result, PlayStatsSummary)
            self.assertEqual(result.play_type, "punt")
            self.assertGreater(result.yards_gained, 0)  # Should have net punt yards
            self.assertGreater(result.time_elapsed, 0)
    
    @patch('random.random')
    def test_real_punt_with_return(self, mock_random):
        """Test real punt with return attempt"""
        # Mock randomness: no block, no out of bounds, no illegal touching, no muff, no downed, no fair catch
        mock_random.side_effect = [0.8, 0.9, 0.9, 0.9, 0.9, 0.9] + [0.5] * 10  # Return attempt
        
        context = PlayContext(play_type="punt", field_position=50)
        params = PuntPlayParams(
            punt_type=PuntPlayType.REAL_PUNT,
            defensive_formation=DefensivePlayType.PUNT_RETURN,
            context=context
        )
        
        with patch.object(self.simulator.penalty_engine, 'check_pre_snap_penalty') as mock_pre_penalty, \
             patch.object(self.simulator.penalty_engine, 'check_during_play_penalty') as mock_during_penalty, \
             patch.object(self.simulator.penalty_engine, 'check_post_play_penalty') as mock_post_penalty:
            
            # Mock no penalties
            mock_pre_penalty.return_value = MagicMock(penalty_occurred=False)
            mock_during_penalty.return_value = MagicMock(penalty_occurred=False)
            mock_post_penalty.return_value = MagicMock(penalty_occurred=False)
            
            result = self.simulator.simulate_punt_play(params)
            
            self.assertIsInstance(result, PlayStatsSummary)
            # Net yards should be punt distance minus return yards
            # Could be positive (good punt) or negative (long return)
    
    @patch('random.random')
    def test_blocked_punt(self, mock_random):
        """Test blocked punt scenario"""
        # Mock randomness to ensure block occurs
        mock_random.side_effect = [0.01]  # Very low number to trigger block
        
        context = PlayContext(play_type="punt", field_position=50)
        params = PuntPlayParams(
            punt_type=PuntPlayType.REAL_PUNT,
            defensive_formation=DefensivePlayType.PUNT_BLOCK,  # Higher block probability
            context=context
        )
        
        with patch.object(self.simulator.penalty_engine, 'check_pre_snap_penalty') as mock_pre_penalty, \
             patch.object(self.simulator.penalty_engine, 'check_during_play_penalty') as mock_during_penalty, \
             patch.object(self.simulator.penalty_engine, 'check_post_play_penalty') as mock_post_penalty:
            
            # Mock no penalties
            mock_pre_penalty.return_value = MagicMock(penalty_occurred=False)
            mock_during_penalty.return_value = MagicMock(penalty_occurred=False)
            mock_post_penalty.return_value = MagicMock(penalty_occurred=False)
            
            result = self.simulator.simulate_punt_play(params)
            
            self.assertIsInstance(result, PlayStatsSummary)
            self.assertEqual(result.yards_gained, 0)  # Blocked punt = 0 yards
    
    @patch('random.random')
    def test_fake_punt_pass_success(self, mock_random):
        """Test successful fake punt pass"""
        # Mock randomness: no block, successful fake pass
        mock_random.side_effect = [0.8, 0.2, 0.5]  # No block, successful completion
        
        context = PlayContext(play_type="punt", field_position=50, down=4, distance=3)
        params = PuntPlayParams(
            punt_type=PuntPlayType.FAKE_PUNT_PASS,
            defensive_formation=DefensivePlayType.PUNT_SAFE,
            context=context
        )
        
        with patch.object(self.simulator.penalty_engine, 'check_pre_snap_penalty') as mock_pre_penalty, \
             patch.object(self.simulator.penalty_engine, 'check_during_play_penalty') as mock_during_penalty, \
             patch.object(self.simulator.penalty_engine, 'check_post_play_penalty') as mock_post_penalty:
            
            # Mock no penalties
            mock_pre_penalty.return_value = MagicMock(penalty_occurred=False)
            mock_during_penalty.return_value = MagicMock(penalty_occurred=False)
            mock_post_penalty.return_value = MagicMock(penalty_occurred=False)
            
            result = self.simulator.simulate_punt_play(params)
            
            self.assertIsInstance(result, PlayStatsSummary)
            self.assertGreaterEqual(result.yards_gained, 0)  # Should gain some yards
    
    @patch('random.random')
    def test_fake_punt_run_success(self, mock_random):
        """Test successful fake punt run"""
        # Mock randomness: no block, successful fake run
        mock_random.side_effect = [0.8, 0.2, 0.5]  # No block, successful run
        
        context = PlayContext(play_type="punt", field_position=50, down=4, distance=2)
        params = PuntPlayParams(
            punt_type=PuntPlayType.FAKE_PUNT_RUN,
            defensive_formation=DefensivePlayType.PUNT_SAFE,
            context=context
        )
        
        with patch.object(self.simulator.penalty_engine, 'check_pre_snap_penalty') as mock_pre_penalty, \
             patch.object(self.simulator.penalty_engine, 'check_during_play_penalty') as mock_during_penalty, \
             patch.object(self.simulator.penalty_engine, 'check_post_play_penalty') as mock_post_penalty:
            
            # Mock no penalties
            mock_pre_penalty.return_value = MagicMock(penalty_occurred=False)
            mock_during_penalty.return_value = MagicMock(penalty_occurred=False)
            mock_post_penalty.return_value = MagicMock(penalty_occurred=False)
            
            result = self.simulator.simulate_punt_play(params)
            
            self.assertIsInstance(result, PlayStatsSummary)
            self.assertGreaterEqual(result.yards_gained, 0)  # Should gain some yards
    
    def test_pre_snap_penalty_negates_play(self):
        """Test that pre-snap penalty negates punt play"""
        context = PlayContext(play_type="punt", field_position=50)
        params = PuntPlayParams(
            punt_type=PuntPlayType.REAL_PUNT,
            defensive_formation=DefensivePlayType.PUNT_RETURN,
            context=context
        )
        
        with patch.object(self.simulator.penalty_engine, 'check_pre_snap_penalty') as mock_pre_penalty:
            # Mock pre-snap penalty occurs
            penalty_instance = MagicMock()
            mock_pre_penalty.return_value = MagicMock(
                penalty_occurred=True,
                penalty_instance=penalty_instance
            )
            
            result = self.simulator.simulate_punt_play(params)
            
            self.assertIsInstance(result, PlayStatsSummary)
            self.assertEqual(result.yards_gained, 0)  # No punt occurred
            self.assertTrue(result.penalty_occurred)
            self.assertTrue(result.play_negated)
            self.assertEqual(result.penalty_instance, penalty_instance)
    
    def test_during_play_penalty_affects_outcome(self):
        """Test that during-play penalty affects punt outcome"""
        context = PlayContext(play_type="punt", field_position=50)
        params = PuntPlayParams(
            punt_type=PuntPlayType.REAL_PUNT,
            defensive_formation=DefensivePlayType.PUNT_RETURN,
            context=context
        )
        
        with patch.object(self.simulator.penalty_engine, 'check_pre_snap_penalty') as mock_pre_penalty, \
             patch.object(self.simulator.penalty_engine, 'check_during_play_penalty') as mock_during_penalty, \
             patch.object(self.simulator.penalty_engine, 'check_post_play_penalty') as mock_post_penalty, \
             patch('random.random') as mock_random:
            
            # Mock no pre-snap penalty
            mock_pre_penalty.return_value = MagicMock(penalty_occurred=False)
            
            # Mock during-play penalty occurs
            penalty_instance = MagicMock()
            mock_during_penalty.return_value = MagicMock(
                penalty_occurred=True,
                penalty_instance=penalty_instance,
                modified_yards=15,  # Penalty adds yards
                play_negated=False
            )
            
            # Mock no post-play penalty
            mock_post_penalty.return_value = MagicMock(penalty_occurred=False)
            
            # Mock fair catch to make test predictable
            mock_random.side_effect = [0.8, 0.9, 0.9, 0.1, 0.9, 0.1]  # Fair catch
            
            result = self.simulator.simulate_punt_play(params)
            
            self.assertIsInstance(result, PlayStatsSummary)
            self.assertTrue(result.penalty_occurred)
            self.assertFalse(result.play_negated)
            self.assertEqual(result.penalty_instance, penalty_instance)
    
    def test_formation_matchup_affects_outcomes(self):
        """Test that different defensive formations affect punt outcomes"""
        context = PlayContext(play_type="punt", field_position=50)
        
        # Test punt block formation has higher block probability
        params_block = PuntPlayParams(
            punt_type=PuntPlayType.REAL_PUNT,
            defensive_formation=DefensivePlayType.PUNT_BLOCK,
            context=context
        )
        
        # Test punt safe formation affects fake success rates
        params_safe = PuntPlayParams(
            punt_type=PuntPlayType.FAKE_PUNT_PASS,
            defensive_formation=DefensivePlayType.PUNT_SAFE,
            context=context
        )
        
        # We can't easily test the exact probabilities without complex mocking,
        # but we can verify that the formation matchups are retrieved correctly
        matchup_block = self.simulator._get_formation_matchup(DefensivePlayType.PUNT_BLOCK)
        matchup_safe = self.simulator._get_formation_matchup(DefensivePlayType.PUNT_SAFE)
        
        self.assertIsInstance(matchup_block, dict)
        self.assertIsInstance(matchup_safe, dict)
        
        # Punt block should have higher block probability than punt safe
        if 'block_probability' in matchup_block and 'block_probability' in matchup_safe:
            self.assertGreater(matchup_block['block_probability'], matchup_safe['block_probability'])
    
    def test_player_stat_attribution(self):
        """Test that player stats are correctly attributed"""
        context = PlayContext(play_type="punt", field_position=50)
        params = PuntPlayParams(
            punt_type=PuntPlayType.REAL_PUNT,
            defensive_formation=DefensivePlayType.PUNT_RETURN,
            context=context
        )
        
        with patch.object(self.simulator.penalty_engine, 'check_pre_snap_penalty') as mock_pre_penalty, \
             patch.object(self.simulator.penalty_engine, 'check_during_play_penalty') as mock_during_penalty, \
             patch.object(self.simulator.penalty_engine, 'check_post_play_penalty') as mock_post_penalty, \
             patch('random.random') as mock_random:
            
            # Mock no penalties
            mock_pre_penalty.return_value = MagicMock(penalty_occurred=False)
            mock_during_penalty.return_value = MagicMock(penalty_occurred=False)
            mock_post_penalty.return_value = MagicMock(penalty_occurred=False)
            
            # Mock fair catch for predictable outcome
            mock_random.side_effect = [0.8, 0.9, 0.9, 0.1, 0.9, 0.1]  # Fair catch
            
            result = self.simulator.simulate_punt_play(params)
            
            self.assertIsInstance(result, PlayStatsSummary)
            
            # Check that player stats were added
            self.assertGreater(len(result.player_stats), 0)
            
            # Should have punter stats
            punter_stats_found = False
            for stats in result.player_stats:
                if stats.player_name == "Test Punter":
                    punter_stats_found = True
                    break
            
            self.assertTrue(punter_stats_found, "Punter stats should be attributed")


class TestFormationMatchups(unittest.TestCase):
    """Test formation matchup effects"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.offensive_players = [MagicMock() for _ in range(11)]
        self.defensive_players = [MagicMock() for _ in range(11)]
        
        for i, player in enumerate(self.offensive_players):
            player.name = f"Offensive Player {i}"
            player.get_rating.return_value = 75
        
        for i, player in enumerate(self.defensive_players):
            player.name = f"Defensive Player {i}"
            player.get_rating.return_value = 75
    
    def test_all_punt_defensive_formations(self):
        """Test that all punt defensive formations work"""
        punt_defenses = DefensivePlayType.get_punt_defenses()
        
        for defense in punt_defenses:
            with self.subTest(defense=defense):
                simulator = PuntSimulator(
                    offensive_players=self.offensive_players,
                    defensive_players=self.defensive_players,
                    offensive_formation="PUNT",
                    defensive_formation=defense
                )
                
                matchup = simulator._get_formation_matchup(defense)
                self.assertIsInstance(matchup, dict)
                self.assertIn('block_probability', matchup)
                self.assertIn('fake_advantage_pass', matchup)
                self.assertIn('fake_advantage_run', matchup)
    
    def test_formation_matchup_values(self):
        """Test that formation matchups return reasonable values"""
        simulator = PuntSimulator(
            offensive_players=self.offensive_players,
            defensive_players=self.defensive_players,
            offensive_formation="PUNT",
            defensive_formation="defensive_punt_return"
        )
        
        matchup = simulator._get_formation_matchup(DefensivePlayType.PUNT_RETURN)
        
        # Check that all values are reasonable probabilities
        self.assertGreaterEqual(matchup.get('block_probability', 0), 0)
        self.assertLessEqual(matchup.get('block_probability', 1), 1)
        self.assertGreaterEqual(matchup.get('fake_advantage_pass', 0), 0)
        self.assertLessEqual(matchup.get('fake_advantage_pass', 2), 2)
        self.assertGreaterEqual(matchup.get('fake_advantage_run', 0), 0)
        self.assertLessEqual(matchup.get('fake_advantage_run', 2), 2)


if __name__ == '__main__':
    # Create test suite
    suite = unittest.TestSuite()
    
    # Add all test classes
    test_classes = [
        TestPuntPlayParams,
        TestPuntEnums,
        TestPuntSimulator,
        TestFormationMatchups
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Exit with error code if tests failed
    sys.exit(0 if result.wasSuccessful() else 1)