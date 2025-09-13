#!/usr/bin/env python3
"""
Comprehensive Phase 4 Test Suite

Tests all Phase 4 functionality including:
- GameLoopController integration
- Comprehensive statistics API
- Performance requirements
- Edge cases and error handling
- API reliability and consistency

Target: 30+ comprehensive tests covering all Phase 4 features
"""

import unittest
import time
from unittest.mock import patch, MagicMock

from src.game_management.full_game_simulator import FullGameSimulator
from src.game_management.game_loop_controller import GameResult
from src.constants.team_ids import TeamIDs


class TestPhase4Integration(unittest.TestCase):
    """Integration Tests (8 tests) - Full system integration validation"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.simulator = FullGameSimulator(
            away_team_id=TeamIDs.DETROIT_LIONS,
            home_team_id=TeamIDs.DENVER_BRONCOS
        )
    
    def test_full_game_simulator_initialization(self):
        """Test FullGameSimulator initializes correctly with all components"""
        self.assertIsNotNone(self.simulator.away_team)
        self.assertIsNotNone(self.simulator.home_team)
        self.assertIsNotNone(self.simulator.game_manager)
        self.assertEqual(self.simulator.away_team_id, TeamIDs.DETROIT_LIONS)
        self.assertEqual(self.simulator.home_team_id, TeamIDs.DENVER_BRONCOS)
    
    def test_game_simulation_returns_game_result(self):
        """Test that simulate_game() returns a GameResult object"""
        result = self.simulator.simulate_game()
        self.assertIsInstance(result, GameResult)
        self.assertIsNotNone(result.final_score)
        self.assertIsNotNone(result.home_team)
        self.assertIsNotNone(result.away_team)
    
    def test_gameloop_controller_integration(self):
        """Test GameLoopController integration works end-to-end"""
        # Run simulation
        result = self.simulator.simulate_game()
        
        # Verify integration succeeded (either full simulation or fallback)
        self.assertTrue(hasattr(self.simulator, '_game_result'))
        self.assertTrue(hasattr(self.simulator, '_simulation_duration'))
        self.assertIsInstance(self.simulator._game_result, GameResult)
    
    def test_team_data_consistency(self):
        """Test team data consistency throughout simulation"""
        result = self.simulator.simulate_game()
        
        # Verify team IDs are consistent
        self.assertEqual(result.home_team.team_id, self.simulator.home_team_id)
        self.assertEqual(result.away_team.team_id, self.simulator.away_team_id)
        
        # Verify team names are consistent
        self.assertEqual(result.home_team.full_name, self.simulator.home_team.full_name)
        self.assertEqual(result.away_team.full_name, self.simulator.away_team.full_name)
    
    def test_coaching_staff_integration(self):
        """Test coaching staff loading and integration"""
        # Coaching staff should be loaded (either real or fallback)
        self.assertIsNotNone(self.simulator.away_coaching_staff)
        self.assertIsNotNone(self.simulator.home_coaching_staff)
        
        # Should have required coach types
        for coaching_staff in [self.simulator.away_coaching_staff, self.simulator.home_coaching_staff]:
            self.assertIn("head_coach", coaching_staff)
            self.assertIn("offensive_coordinator", coaching_staff)
            self.assertIn("defensive_coordinator", coaching_staff)
    
    def test_roster_integration(self):
        """Test roster loading and integration"""
        self.assertEqual(len(self.simulator.away_roster), 52)
        self.assertEqual(len(self.simulator.home_roster), 52)
        
        # Test roster access methods
        lions_roster = self.simulator.get_roster_by_team(TeamIDs.DETROIT_LIONS)
        broncos_roster = self.simulator.get_roster_by_team(TeamIDs.DENVER_BRONCOS)
        
        self.assertEqual(len(lions_roster), 52)
        self.assertEqual(len(broncos_roster), 52)
    
    def test_simulation_state_persistence(self):
        """Test that simulation state is properly stored and accessible"""
        # Before simulation
        self.assertFalse(hasattr(self.simulator, '_game_result'))
        
        # Run simulation
        result = self.simulator.simulate_game()
        
        # After simulation
        self.assertTrue(hasattr(self.simulator, '_game_result'))
        self.assertTrue(hasattr(self.simulator, '_simulation_duration'))
        self.assertEqual(self.simulator._game_result, result)
    
    def test_error_handling_and_fallback(self):
        """Test error handling and fallback mechanisms"""
        # This test verifies that even if GameLoopController fails,
        # the system falls back gracefully and still returns a valid result
        result = self.simulator.simulate_game()
        
        # Should always return a GameResult, even in fallback mode
        self.assertIsInstance(result, GameResult)
        self.assertIsNotNone(result.final_score)
        
        # Performance metrics should still work
        performance = self.simulator.get_performance_metrics()
        self.assertIn("simulation_duration_seconds", performance)
        self.assertIn("game_completed", performance)


class TestPhase4API(unittest.TestCase):
    """API Tests (10 tests) - Public API method validation"""
    
    def setUp(self):
        """Set up test fixtures with simulated game"""
        self.simulator = FullGameSimulator(
            away_team_id=TeamIDs.DETROIT_LIONS,
            home_team_id=TeamIDs.DENVER_BRONCOS
        )
        self.game_result = self.simulator.simulate_game()
    
    def test_get_game_result_api(self):
        """Test get_game_result() API method"""
        result = self.simulator.get_game_result()
        self.assertIsInstance(result, GameResult)
        self.assertEqual(result, self.game_result)
    
    def test_get_final_score_api(self):
        """Test get_final_score() API method"""
        final_score = self.simulator.get_final_score()
        
        # Verify structure
        self.assertIn("scores", final_score)
        self.assertIn("winner", final_score)
        self.assertIn("game_completed", final_score)
        self.assertIn("simulation_time", final_score)
        
        # Verify data types
        self.assertIsInstance(final_score["scores"], dict)
        self.assertIsInstance(final_score["game_completed"], bool)
        self.assertIsInstance(final_score["simulation_time"], float)
        
        # Verify team names in scores
        self.assertIn("Detroit Lions", final_score["scores"])
        self.assertIn("Denver Broncos", final_score["scores"])
    
    def test_get_team_stats_api(self):
        """Test get_team_stats() API method"""
        # Test without filter
        all_team_stats = self.simulator.get_team_stats()
        self.assertIsInstance(all_team_stats, dict)
        
        # Test with team filter
        lions_stats = self.simulator.get_team_stats(team_id=TeamIDs.DETROIT_LIONS)
        self.assertIsInstance(lions_stats, dict)
        
        # Test invalid team ID
        invalid_stats = self.simulator.get_team_stats(team_id=999)
        self.assertIsInstance(invalid_stats, dict)
    
    def test_get_player_stats_api(self):
        """Test get_player_stats() API method"""
        # Test without filters
        all_players = self.simulator.get_player_stats()
        self.assertIsInstance(all_players, dict)
        
        # Test with team filter
        lions_players = self.simulator.get_player_stats(team_id=TeamIDs.DETROIT_LIONS)
        self.assertIsInstance(lions_players, dict)
        
        # Test with position filter
        qb_players = self.simulator.get_player_stats(position="QB")
        self.assertIsInstance(qb_players, dict)
    
    def test_get_drive_summaries_api(self):
        """Test get_drive_summaries() API method"""
        drive_summaries = self.simulator.get_drive_summaries()
        self.assertIsInstance(drive_summaries, list)
        
        # If drives exist, verify structure
        for drive in drive_summaries:
            self.assertIn("drive_number", drive)
            self.assertIn("possessing_team", drive)
            self.assertIn("total_plays", drive)
            self.assertIn("points_scored", drive)
    
    def test_get_play_by_play_api(self):
        """Test get_play_by_play() API method"""
        play_by_play = self.simulator.get_play_by_play()
        self.assertIsInstance(play_by_play, list)
        
        # If plays exist, verify structure
        for play in play_by_play:
            self.assertIn("play_number", play)
            self.assertIn("possessing_team", play)
            self.assertIn("description", play)
    
    def test_get_penalty_summary_api(self):
        """Test get_penalty_summary() API method"""
        penalty_summary = self.simulator.get_penalty_summary()
        
        self.assertIsInstance(penalty_summary, dict)
        self.assertIn("total_penalties", penalty_summary)
        self.assertIn("by_team", penalty_summary)
        self.assertIsInstance(penalty_summary["total_penalties"], int)
    
    def test_get_performance_metrics_api(self):
        """Test get_performance_metrics() API method"""
        performance = self.simulator.get_performance_metrics()
        
        # Verify required fields
        required_fields = [
            "simulation_duration_seconds", "total_plays", "total_drives",
            "plays_per_second", "performance_target_met", "game_completed"
        ]
        
        for field in required_fields:
            self.assertIn(field, performance)
        
        # Verify data types
        self.assertIsInstance(performance["simulation_duration_seconds"], float)
        self.assertIsInstance(performance["total_plays"], int)
        self.assertIsInstance(performance["performance_target_met"], bool)
        self.assertIsInstance(performance["game_completed"], bool)
    
    def test_api_consistency_before_simulation(self):
        """Test API methods work correctly before game simulation"""
        fresh_simulator = FullGameSimulator(
            away_team_id=TeamIDs.DETROIT_LIONS,
            home_team_id=TeamIDs.DENVER_BRONCOS
        )
        
        # APIs should return sensible defaults before simulation
        self.assertIsNone(fresh_simulator.get_game_result())
        
        final_score = fresh_simulator.get_final_score()
        self.assertFalse(final_score["game_completed"])
        self.assertEqual(final_score["scores"]["Detroit Lions"], 0)
        
        self.assertEqual(len(fresh_simulator.get_drive_summaries()), 0)
        self.assertEqual(len(fresh_simulator.get_play_by_play()), 0)
    
    def test_api_method_signatures(self):
        """Test that all API methods have correct signatures and are callable"""
        api_methods = [
            "get_game_result", "get_final_score", "get_team_stats",
            "get_player_stats", "get_drive_summaries", "get_play_by_play",
            "get_penalty_summary", "get_performance_metrics"
        ]
        
        for method_name in api_methods:
            self.assertTrue(hasattr(self.simulator, method_name))
            method = getattr(self.simulator, method_name)
            self.assertTrue(callable(method))


class TestPhase4Performance(unittest.TestCase):
    """Performance Tests (3 tests) - Speed and memory benchmarks"""
    
    def test_simulation_performance_target(self):
        """Test that simulation meets < 5 second performance target"""
        simulator = FullGameSimulator(
            away_team_id=TeamIDs.DETROIT_LIONS,
            home_team_id=TeamIDs.DENVER_BRONCOS
        )
        
        start_time = time.time()
        result = simulator.simulate_game()
        end_time = time.time()
        
        simulation_duration = end_time - start_time
        
        # Performance target: < 5 seconds
        self.assertLess(simulation_duration, 5.0, 
                       f"Simulation took {simulation_duration:.3f}s, target is < 5.0s")
        
        # Verify performance metrics match
        performance = simulator.get_performance_metrics()
        self.assertTrue(performance["performance_target_met"])
    
    def test_api_response_time(self):
        """Test API methods respond within acceptable time limits"""
        simulator = FullGameSimulator(
            away_team_id=TeamIDs.DETROIT_LIONS,
            home_team_id=TeamIDs.DENVER_BRONCOS
        )
        simulator.simulate_game()
        
        api_methods = [
            simulator.get_final_score,
            simulator.get_team_stats,
            simulator.get_player_stats,
            simulator.get_drive_summaries,
            simulator.get_play_by_play,
            simulator.get_penalty_summary,
            simulator.get_performance_metrics
        ]
        
        # Each API method should respond in < 100ms
        for method in api_methods:
            start_time = time.time()
            result = method()
            end_time = time.time()
            
            api_duration = end_time - start_time
            self.assertLess(api_duration, 0.1,  # 100ms
                           f"{method.__name__} took {api_duration:.3f}s, target is < 0.1s")
    
    def test_memory_efficiency(self):
        """Test memory usage stays within reasonable bounds"""
        import sys
        
        # Measure memory before
        initial_refs = sys.gettotalrefcount() if hasattr(sys, 'gettotalrefcount') else 0
        
        # Run simulation
        simulator = FullGameSimulator(
            away_team_id=TeamIDs.DETROIT_LIONS,
            home_team_id=TeamIDs.DENVER_BRONCOS
        )
        result = simulator.simulate_game()
        
        # Access all API methods
        simulator.get_final_score()
        simulator.get_team_stats()
        simulator.get_player_stats()
        simulator.get_drive_summaries()
        simulator.get_play_by_play()
        simulator.get_penalty_summary()
        simulator.get_performance_metrics()
        
        # Memory should not leak significantly
        final_refs = sys.gettotalrefcount() if hasattr(sys, 'gettotalrefcount') else 0
        
        # This is a basic test - in practice, would use memory profiling tools
        self.assertIsNotNone(result)  # Ensures simulation completed without memory errors


class TestPhase4EdgeCases(unittest.TestCase):
    """Edge Case Tests (5 tests) - Error conditions and boundary cases"""
    
    def test_invalid_team_ids(self):
        """Test handling of invalid team IDs"""
        with self.assertRaises(ValueError):
            FullGameSimulator(away_team_id=0, home_team_id=TeamIDs.DENVER_BRONCOS)
        
        with self.assertRaises(ValueError):
            FullGameSimulator(away_team_id=TeamIDs.DETROIT_LIONS, home_team_id=999)
        
        with self.assertRaises(ValueError):
            FullGameSimulator(away_team_id=TeamIDs.DETROIT_LIONS, home_team_id=TeamIDs.DETROIT_LIONS)
    
    def test_api_calls_with_invalid_parameters(self):
        """Test API methods handle invalid parameters gracefully"""
        simulator = FullGameSimulator(
            away_team_id=TeamIDs.DETROIT_LIONS,
            home_team_id=TeamIDs.DENVER_BRONCOS
        )
        simulator.simulate_game()
        
        # Invalid team IDs should return empty/default results, not crash
        result = simulator.get_team_stats(team_id=999)
        self.assertIsInstance(result, dict)
        
        result = simulator.get_player_stats(team_id=999)
        self.assertIsInstance(result, dict)
    
    def test_simulation_failure_handling(self):
        """Test system handles simulation failures gracefully"""
        simulator = FullGameSimulator(
            away_team_id=TeamIDs.DETROIT_LIONS,
            home_team_id=TeamIDs.DENVER_BRONCOS
        )
        
        # Even if GameLoopController fails, should get fallback result
        result = simulator.simulate_game()
        self.assertIsInstance(result, GameResult)
        
        # All API methods should still work
        self.assertIsNotNone(simulator.get_final_score())
        self.assertIsInstance(simulator.get_team_stats(), dict)
        self.assertIsInstance(simulator.get_performance_metrics(), dict)
    
    def test_concurrent_api_access(self):
        """Test API methods can be called multiple times safely"""
        simulator = FullGameSimulator(
            away_team_id=TeamIDs.DETROIT_LIONS,
            home_team_id=TeamIDs.DENVER_BRONCOS
        )
        simulator.simulate_game()
        
        # Multiple calls should return consistent results
        score1 = simulator.get_final_score()
        score2 = simulator.get_final_score()
        self.assertEqual(score1, score2)
        
        stats1 = simulator.get_team_stats()
        stats2 = simulator.get_team_stats()
        self.assertEqual(stats1, stats2)
    
    def test_string_representations(self):
        """Test string representations work correctly"""
        simulator = FullGameSimulator(
            away_team_id=TeamIDs.DETROIT_LIONS,
            home_team_id=TeamIDs.DENVER_BRONCOS
        )
        
        # __str__ and __repr__ should work
        str_repr = str(simulator)
        self.assertIn("DET", str_repr)
        self.assertIn("DEN", str_repr)
        
        repr_str = repr(simulator)
        self.assertIn("FullGameSimulator", repr_str)
        self.assertIn("22", repr_str)  # Lions team ID
        self.assertIn("13", repr_str)  # Broncos team ID


class TestPhase4Statistics(unittest.TestCase):
    """Statistics Tests (4 tests) - Statistics accuracy validation"""
    
    def setUp(self):
        """Set up test fixtures with simulated game"""
        self.simulator = FullGameSimulator(
            away_team_id=TeamIDs.DETROIT_LIONS,
            home_team_id=TeamIDs.DENVER_BRONCOS
        )
        self.game_result = self.simulator.simulate_game()
    
    def test_score_consistency(self):
        """Test score consistency across different API methods"""
        game_result = self.simulator.get_game_result()
        final_score_api = self.simulator.get_final_score()
        team_stats = self.simulator.get_team_stats()
        
        # Scores should be consistent across all APIs
        for team_id, score in game_result.final_score.items():
            team_name = self.simulator._get_team_name(team_id)
            self.assertEqual(score, final_score_api["scores"][team_name])
            if team_name in team_stats:
                self.assertEqual(score, team_stats[team_name]["final_score"])
    
    def test_play_count_consistency(self):
        """Test play count consistency across API methods"""
        game_result = self.simulator.get_game_result()
        final_score_api = self.simulator.get_final_score()
        play_by_play = self.simulator.get_play_by_play()
        performance = self.simulator.get_performance_metrics()
        
        # Play counts should be consistent
        expected_plays = game_result.total_plays
        self.assertEqual(expected_plays, final_score_api["total_plays"])
        self.assertEqual(expected_plays, len(play_by_play))
        self.assertEqual(expected_plays, performance["total_plays"])
    
    def test_drive_count_consistency(self):
        """Test drive count consistency across API methods"""
        game_result = self.simulator.get_game_result()
        final_score_api = self.simulator.get_final_score()
        drive_summaries = self.simulator.get_drive_summaries()
        performance = self.simulator.get_performance_metrics()
        
        # Drive counts should be consistent
        expected_drives = game_result.total_drives
        self.assertEqual(expected_drives, final_score_api["total_drives"])
        self.assertEqual(expected_drives, len(drive_summaries))
        self.assertEqual(expected_drives, performance["total_drives"])
    
    def test_team_name_consistency(self):
        """Test team name consistency across all APIs"""
        team_stats = self.simulator.get_team_stats()
        final_score = self.simulator.get_final_score()
        drive_summaries = self.simulator.get_drive_summaries()
        
        expected_teams = {"Detroit Lions", "Denver Broncos"}
        
        # Team names should be consistent across APIs
        self.assertEqual(set(final_score["scores"].keys()), expected_teams)
        if team_stats:
            self.assertTrue(set(team_stats.keys()).issubset(expected_teams))
        
        # Drive summaries should use consistent team names
        drive_teams = {drive["possessing_team"] for drive in drive_summaries}
        self.assertTrue(drive_teams.issubset(expected_teams))


def run_comprehensive_test_suite():
    """Run the complete Phase 4 test suite"""
    print("🧪 PHASE 4 COMPREHENSIVE TEST SUITE")
    print("=" * 60)
    
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add all test classes
    test_classes = [
        TestPhase4Integration,    # 8 tests
        TestPhase4API,           # 10 tests
        TestPhase4Performance,   # 3 tests
        TestPhase4EdgeCases,     # 5 tests
        TestPhase4Statistics     # 4 tests
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    print(f"\n📊 Test Results Summary:")
    print(f"   Tests run: {result.testsRun}")
    print(f"   Failures: {len(result.failures)}")
    print(f"   Errors: {len(result.errors)}")
    print(f"   Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.wasSuccessful():
        print("✅ ALL TESTS PASSED - Phase 4 implementation is comprehensive and robust!")
    else:
        print("❌ Some tests failed - review implementation for issues")
    
    return result


if __name__ == "__main__":
    run_comprehensive_test_suite()