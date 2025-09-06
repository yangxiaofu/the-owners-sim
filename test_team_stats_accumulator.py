#!/usr/bin/env python3
"""
Comprehensive testing script for TeamStatsAccumulator.

This script creates various synthetic PlayStatsSummary scenarios and validates
that the TeamStatsAccumulator correctly aggregates team-level statistics.
"""

import sys
import os

# Add src directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from play_engine.simulation.stats import (
    PlayStatsSummary, PlayerStats, TeamStatsAccumulator, TeamStats
)
from dataclasses import dataclass
from typing import List, Dict, Any, Optional


class TestResult:
    """Container for test results"""
    def __init__(self, test_name: str):
        self.test_name = test_name
        self.passed = False
        self.error_message = ""
        self.expected = {}
        self.actual = {}
        
    def fail(self, message: str, expected: Any = None, actual: Any = None):
        self.passed = False
        self.error_message = message
        self.expected = expected or {}
        self.actual = actual or {}
        
    def pass_test(self):
        self.passed = True


class TeamStatsTestSuite:
    """Comprehensive test suite for TeamStatsAccumulator"""
    
    def __init__(self):
        self.results: List[TestResult] = []
        self.accumulator = TeamStatsAccumulator("test_game")
        
    def reset_accumulator(self):
        """Reset accumulator for next test"""
        self.accumulator = TeamStatsAccumulator("test_game")
    
    def create_test_player_stats(self, **kwargs) -> PlayerStats:
        """Create PlayerStats with specified values, defaults to 0"""
        return PlayerStats(
            player_name=kwargs.get('player_name', 'Test Player'),
            player_number=kwargs.get('player_number', 99),
            position=kwargs.get('position', 'RB'),
            carries=kwargs.get('carries', 0),
            rushing_yards=kwargs.get('rushing_yards', 0),
            pass_attempts=kwargs.get('pass_attempts', 0),
            completions=kwargs.get('completions', 0),
            passing_yards=kwargs.get('passing_yards', 0),
            passing_tds=kwargs.get('passing_tds', 0),
            rushing_touchdowns=kwargs.get('rushing_touchdowns', 0),
            interceptions_thrown=kwargs.get('interceptions_thrown', 0),
            sacks=kwargs.get('sacks', 0),
            tackles_for_loss=kwargs.get('tackles_for_loss', 0),
            interceptions=kwargs.get('interceptions', 0),
            forced_fumbles=kwargs.get('forced_fumbles', 0),
            passes_defended=kwargs.get('passes_defended', 0),
            field_goal_attempts=kwargs.get('field_goal_attempts', 0),
            field_goals_made=kwargs.get('field_goals_made', 0)
        )
    
    def create_test_play_summary(self, players: List[PlayerStats], **kwargs) -> PlayStatsSummary:
        """Create PlayStatsSummary with specified players and values"""
        return PlayStatsSummary(
            play_type=kwargs.get('play_type', 'RUN'),
            yards_gained=kwargs.get('yards_gained', 0),
            time_elapsed=kwargs.get('time_elapsed', 5.0),
            player_stats=players,
            penalty_occurred=kwargs.get('penalty_occurred', False)
        )
    
    def run_test(self, test_name: str, test_func):
        """Run a single test and capture results"""
        print(f"\n{'='*60}")
        print(f"Running Test: {test_name}")
        print('='*60)
        
        result = TestResult(test_name)
        self.reset_accumulator()
        
        try:
            test_func(result)
            if result.passed:
                print("✅ PASSED")
            else:
                print(f"❌ FAILED: {result.error_message}")
                if result.expected:
                    print(f"Expected: {result.expected}")
                if result.actual:
                    print(f"Actual: {result.actual}")
                    
        except Exception as e:
            result.fail(f"Test threw exception: {str(e)}")
            print(f"❌ FAILED: {result.error_message}")
            
        self.results.append(result)
        return result.passed
    
    def test_single_rushing_play(self, result: TestResult):
        """Test single rushing play aggregation"""
        # Create a rushing play: Team 1 RB gains 8 yards
        rb_stats = self.create_test_player_stats(
            player_name="Test RB",
            position="RB", 
            carries=1,
            rushing_yards=8
        )
        
        play = self.create_test_play_summary(
            players=[rb_stats],
            play_type="RUN",
            yards_gained=8
        )
        
        # Add to accumulator
        self.accumulator.add_play_stats(play, offensive_team_id=1, defensive_team_id=2)
        
        # Verify team 1 offensive stats
        team1_stats = self.accumulator.get_team_stats(1)
        if not team1_stats:
            result.fail("Team 1 stats not found")
            return
            
        expected_team1 = {
            'total_yards': 8,
            'rushing_yards': 8,
            'passing_yards': 0,
            'touchdowns': 0
        }
        
        actual_team1 = {
            'total_yards': team1_stats.total_yards,
            'rushing_yards': team1_stats.rushing_yards,  
            'passing_yards': team1_stats.passing_yards,
            'touchdowns': team1_stats.touchdowns
        }
        
        if actual_team1 != expected_team1:
            result.fail("Team 1 offensive stats mismatch", expected_team1, actual_team1)
            return
            
        # Verify team 2 has no offensive stats but exists
        team2_stats = self.accumulator.get_team_stats(2)
        if not team2_stats:
            result.fail("Team 2 stats not found")
            return
            
        if team2_stats.total_yards != 0 or team2_stats.rushing_yards != 0:
            result.fail("Team 2 should have no offensive stats")
            return
            
        result.pass_test()
        
        # Display detailed results
        print(f"Team 1 Stats: {actual_team1}")
        print(f"Team 2 Stats: Total yards={team2_stats.total_yards}, Rushing={team2_stats.rushing_yards}")
    
    def test_single_passing_play(self, result: TestResult):
        """Test single passing play aggregation"""
        # Create QB and WR stats for a 15-yard pass
        qb_stats = self.create_test_player_stats(
            player_name="Test QB",
            position="QB",
            pass_attempts=1,
            completions=1, 
            passing_yards=15,
            passing_tds=0
        )
        
        wr_stats = self.create_test_player_stats(
            player_name="Test WR",
            position="WR",
            receptions=1,
            receiving_yards=15
        )
        
        play = self.create_test_play_summary(
            players=[qb_stats, wr_stats],
            play_type="PASS",
            yards_gained=15
        )
        
        self.accumulator.add_play_stats(play, offensive_team_id=3, defensive_team_id=4)
        
        # Verify team 3 stats
        team3_stats = self.accumulator.get_team_stats(3)
        expected = {
            'total_yards': 15,
            'passing_yards': 15,
            'pass_attempts': 1,
            'completions': 1,
            'rushing_yards': 0
        }
        
        actual = {
            'total_yards': team3_stats.total_yards,
            'passing_yards': team3_stats.passing_yards,
            'pass_attempts': team3_stats.pass_attempts,
            'completions': team3_stats.completions,
            'rushing_yards': team3_stats.rushing_yards
        }
        
        if actual != expected:
            result.fail("Team 3 passing stats mismatch", expected, actual)
            return
            
        result.pass_test()
        print(f"Team 3 Stats: {actual}")
    
    def test_defensive_stats(self, result: TestResult):
        """Test defensive stats aggregation"""
        # Create defensive play: sack for loss
        de_stats = self.create_test_player_stats(
            player_name="Test DE",
            position="DE",
            sacks=1,
            tackles_for_loss=1
        )
        
        play = self.create_test_play_summary(
            players=[de_stats],
            play_type="PASS",
            yards_gained=-8  # Sack yardage
        )
        
        self.accumulator.add_play_stats(play, offensive_team_id=5, defensive_team_id=6)
        
        # Verify team 6 (defensive team) gets defensive stats
        team6_stats = self.accumulator.get_team_stats(6)
        
        expected_def = {
            'sacks': 1,
            'tackles_for_loss': 1,
            'interceptions': 0,
            'forced_fumbles': 0
        }
        
        actual_def = {
            'sacks': team6_stats.sacks,
            'tackles_for_loss': team6_stats.tackles_for_loss,
            'interceptions': team6_stats.interceptions,
            'forced_fumbles': team6_stats.forced_fumbles
        }
        
        if actual_def != expected_def:
            result.fail("Team 6 defensive stats mismatch", expected_def, actual_def)
            return
            
        result.pass_test()
        print(f"Team 6 Defensive Stats: {actual_def}")
    
    def test_multiple_plays_same_teams(self, result: TestResult):
        """Test accumulation across multiple plays for same teams"""
        # Play 1: 5-yard run
        rb_stats1 = self.create_test_player_stats(
            rushing_yards=5, carries=1
        )
        play1 = self.create_test_play_summary([rb_stats1], yards_gained=5)
        
        # Play 2: 10-yard pass  
        qb_stats2 = self.create_test_player_stats(
            pass_attempts=1, completions=1, passing_yards=10
        )
        play2 = self.create_test_play_summary([qb_stats2], yards_gained=10)
        
        # Play 3: Defensive sack
        de_stats3 = self.create_test_player_stats(
            sacks=1, tackles_for_loss=1
        )
        play3 = self.create_test_play_summary([de_stats3], yards_gained=-5)
        
        # Add all plays (Team 7 offense vs Team 8 defense)
        self.accumulator.add_play_stats(play1, offensive_team_id=7, defensive_team_id=8)
        self.accumulator.add_play_stats(play2, offensive_team_id=7, defensive_team_id=8)
        self.accumulator.add_play_stats(play3, offensive_team_id=7, defensive_team_id=8)
        
        # Verify Team 7 accumulated offensive stats
        team7_stats = self.accumulator.get_team_stats(7)
        expected_off = {
            'total_yards': 10,  # 5 + 10 + (-5)
            'rushing_yards': 5,
            'passing_yards': 10,
            'pass_attempts': 1,
            'completions': 1
        }
        
        actual_off = {
            'total_yards': team7_stats.total_yards,
            'rushing_yards': team7_stats.rushing_yards,
            'passing_yards': team7_stats.passing_yards,
            'pass_attempts': team7_stats.pass_attempts,
            'completions': team7_stats.completions
        }
        
        if actual_off != expected_off:
            result.fail("Team 7 multi-play offensive stats mismatch", expected_off, actual_off)
            return
        
        # Verify Team 8 defensive stats
        team8_stats = self.accumulator.get_team_stats(8)
        expected_def = {'sacks': 1, 'tackles_for_loss': 1}
        actual_def = {'sacks': team8_stats.sacks, 'tackles_for_loss': team8_stats.tackles_for_loss}
        
        if actual_def != expected_def:
            result.fail("Team 8 multi-play defensive stats mismatch", expected_def, actual_def)
            return
            
        # Verify plays processed count
        if self.accumulator.get_plays_processed() != 3:
            result.fail(f"Expected 3 plays processed, got {self.accumulator.get_plays_processed()}")
            return
        
        result.pass_test()
        print(f"Team 7 Accumulated Offense: {actual_off}")
        print(f"Team 8 Accumulated Defense: {actual_def}")
        print(f"Plays Processed: {self.accumulator.get_plays_processed()}")
    
    def test_field_goal_stats(self, result: TestResult):
        """Test field goal stats aggregation"""
        kicker_stats = self.create_test_player_stats(
            player_name="Test K",
            position="K",
            field_goal_attempts=1,
            field_goals_made=1
        )
        
        play = self.create_test_play_summary(
            players=[kicker_stats],
            play_type="FIELD_GOAL",
            yards_gained=0  # No net yardage on FG
        )
        
        self.accumulator.add_play_stats(play, offensive_team_id=9, defensive_team_id=10)
        
        team9_stats = self.accumulator.get_team_stats(9)
        expected = {'field_goals_attempted': 1, 'field_goals_made': 1}
        actual = {
            'field_goals_attempted': team9_stats.field_goals_attempted,
            'field_goals_made': team9_stats.field_goals_made
        }
        
        if actual != expected:
            result.fail("Field goal stats mismatch", expected, actual)
            return
            
        result.pass_test()
        print(f"Team 9 Special Teams: {actual}")
    
    def test_mixed_player_stats_same_play(self, result: TestResult):
        """Test play with multiple players contributing different stats"""
        # Simulate a play with QB pass, RB block, WR reception, DE pressure
        qb_stats = self.create_test_player_stats(
            player_name="QB1", position="QB",
            pass_attempts=1, completions=1, passing_yards=12
        )
        
        wr_stats = self.create_test_player_stats(
            player_name="WR1", position="WR"
            # WR receiving stats not tracked in PlayerStats in this test
        )
        
        de_stats = self.create_test_player_stats(
            player_name="DE1", position="DE",
            passes_defended=1  # QB hurry that affected the throw
        )
        
        play = self.create_test_play_summary(
            players=[qb_stats, wr_stats, de_stats],
            yards_gained=12
        )
        
        self.accumulator.add_play_stats(play, offensive_team_id=11, defensive_team_id=12)
        
        # Check Team 11 offensive stats
        team11_stats = self.accumulator.get_team_stats(11)
        expected_off = {
            'total_yards': 12,
            'passing_yards': 12,
            'pass_attempts': 1,
            'completions': 1
        }
        
        actual_off = {
            'total_yards': team11_stats.total_yards,
            'passing_yards': team11_stats.passing_yards,
            'pass_attempts': team11_stats.pass_attempts,
            'completions': team11_stats.completions
        }
        
        # Check Team 12 defensive stats
        team12_stats = self.accumulator.get_team_stats(12)
        expected_def = {'passes_defended': 1}
        actual_def = {'passes_defended': team12_stats.passes_defended}
        
        if actual_off != expected_off:
            result.fail("Team 11 mixed play offensive stats mismatch", expected_off, actual_off)
            return
            
        if actual_def != expected_def:
            result.fail("Team 12 mixed play defensive stats mismatch", expected_def, actual_def)
            return
        
        result.pass_test()
        print(f"Team 11 Mixed Play Offense: {actual_off}")
        print(f"Team 12 Mixed Play Defense: {actual_def}")
    
    def test_zero_stats_players(self, result: TestResult):
        """Test that players with zero stats don't affect totals incorrectly"""
        # Create players with zero stats
        zero_player1 = self.create_test_player_stats(player_name="Zero1")
        zero_player2 = self.create_test_player_stats(player_name="Zero2")
        
        # One player with actual stats
        productive_player = self.create_test_player_stats(
            player_name="Productive", rushing_yards=7, carries=1
        )
        
        play = self.create_test_play_summary(
            players=[zero_player1, productive_player, zero_player2],
            yards_gained=7
        )
        
        self.accumulator.add_play_stats(play, offensive_team_id=13, defensive_team_id=14)
        
        team13_stats = self.accumulator.get_team_stats(13)
        
        # Should only reflect the productive player's stats
        expected = {
            'total_yards': 7,
            'rushing_yards': 7,
            'passing_yards': 0,
            'pass_attempts': 0
        }
        
        actual = {
            'total_yards': team13_stats.total_yards,
            'rushing_yards': team13_stats.rushing_yards,
            'passing_yards': team13_stats.passing_yards,
            'pass_attempts': team13_stats.pass_attempts
        }
        
        if actual != expected:
            result.fail("Zero stats players affected totals", expected, actual)
            return
            
        result.pass_test()
        print(f"Team 13 with zero-stat players: {actual}")
    
    def test_empty_player_list(self, result: TestResult):
        """Test handling of plays with no player stats"""
        play = self.create_test_play_summary(
            players=[],  # Empty list
            yards_gained=0
        )
        
        initial_plays = self.accumulator.get_plays_processed()
        self.accumulator.add_play_stats(play, offensive_team_id=15, defensive_team_id=16)
        
        # Should still process the play and create team entries
        if self.accumulator.get_plays_processed() != initial_plays + 1:
            result.fail("Play with empty player list not processed")
            return
        
        team15_stats = self.accumulator.get_team_stats(15)
        team16_stats = self.accumulator.get_team_stats(16)
        
        if not team15_stats or not team16_stats:
            result.fail("Teams not created for empty player list play")
            return
        
        # Both teams should have zero stats
        if team15_stats.total_yards != 0 or team16_stats.total_yards != 0:
            result.fail("Empty player list affected team stats")
            return
            
        result.pass_test()
        print("Empty player list handled correctly")
    
    def test_accumulator_query_methods(self, result: TestResult):
        """Test various query methods of the accumulator"""
        # Add some stats to multiple teams
        play1 = self.create_test_play_summary(
            [self.create_test_player_stats(rushing_yards=5)],
            yards_gained=5
        )
        play2 = self.create_test_play_summary(
            [self.create_test_player_stats(passing_yards=10, pass_attempts=1, completions=1)],
            yards_gained=10
        )
        
        self.accumulator.add_play_stats(play1, offensive_team_id=17, defensive_team_id=18)
        self.accumulator.add_play_stats(play2, offensive_team_id=19, defensive_team_id=20)
        
        # Test get_all_teams_stats
        all_teams = self.accumulator.get_all_teams_stats()
        if len(all_teams) != 4:  # 4 teams should be tracked
            result.fail(f"Expected 4 teams, got {len(all_teams)}")
            return
        
        # Test get_teams_with_stats (only teams with non-zero stats)
        teams_with_stats = self.accumulator.get_teams_with_stats()
        if len(teams_with_stats) != 2:  # Only offensive teams have stats
            result.fail(f"Expected 2 teams with stats, got {len(teams_with_stats)}")
            return
        
        # Test get_team_count
        if self.accumulator.get_team_count() != 4:
            result.fail(f"Expected team count 4, got {self.accumulator.get_team_count()}")
            return
        
        # Test get_plays_processed  
        if self.accumulator.get_plays_processed() != 2:
            result.fail(f"Expected 2 plays processed, got {self.accumulator.get_plays_processed()}")
            return
        
        result.pass_test()
        print(f"All teams: {len(all_teams)}, With stats: {len(teams_with_stats)}")
        print(f"Team count: {self.accumulator.get_team_count()}, Plays: {self.accumulator.get_plays_processed()}")
    
    def run_all_tests(self):
        """Run the complete test suite"""
        print("🏈 TEAM STATS ACCUMULATOR COMPREHENSIVE TEST SUITE 🏈")
        print("="*70)
        
        tests = [
            ("Single Rushing Play", self.test_single_rushing_play),
            ("Single Passing Play", self.test_single_passing_play), 
            ("Defensive Stats", self.test_defensive_stats),
            ("Multiple Plays Same Teams", self.test_multiple_plays_same_teams),
            ("Field Goal Stats", self.test_field_goal_stats),
            ("Mixed Player Stats Same Play", self.test_mixed_player_stats_same_play),
            ("Zero Stats Players", self.test_zero_stats_players),
            ("Empty Player List", self.test_empty_player_list),
            ("Accumulator Query Methods", self.test_accumulator_query_methods)
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            if self.run_test(test_name, test_func):
                passed += 1
        
        # Print summary
        print(f"\n{'='*70}")
        print("🎯 TEST SUITE SUMMARY")
        print('='*70)
        print(f"Passed: {passed}/{total} ({100*passed/total:.1f}%)")
        
        if passed == total:
            print("🎉 ALL TESTS PASSED! 🎉")
        else:
            print(f"❌ {total-passed} tests failed")
            print("\nFailed tests:")
            for result in self.results:
                if not result.passed:
                    print(f"  - {result.test_name}: {result.error_message}")
        
        return passed == total


def main():
    """Run the test suite"""
    suite = TeamStatsTestSuite()
    success = suite.run_all_tests()
    
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()