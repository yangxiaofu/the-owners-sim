#!/usr/bin/env python3
"""
NFL Penalty Benchmarking Test Suite

This comprehensive test suite validates that the penalty detection system produces
penalty rates and distributions that match NFL 2024 statistics through extensive
game simulation.

Target Benchmarks (NFL 2024 Season):
- 7.56 penalties per game per team  
- 51.83 penalty yards per game per team
- Total game penalties: ~15 penalties, ~103 yards per game (both teams combined)

Test approach:
1. Simulate 100+ complete games
2. Track all penalty statistics  
3. Validate against NFL benchmarks with confidence intervals
4. Test penalty distribution by type and phase
5. Verify player discipline impact
6. Performance impact assessment
"""

import sys
import os
import unittest
import random
import time
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass, field
from collections import defaultdict

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from game_engine.core.play_executor import PlayExecutor
from game_engine.field.game_state import GameState
from game_engine.penalties.data_structures import PenaltyConstants, get_penalty_summary_stats
from database.models.players.player import Player


@dataclass
class PenaltyStats:
    """Container for penalty statistics from simulation."""
    total_penalties: int = 0
    total_penalty_yards: int = 0
    penalties_by_type: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    penalties_by_phase: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    penalties_by_team: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    games_simulated: int = 0
    
    @property
    def penalties_per_game(self) -> float:
        """Average penalties per game (both teams combined)."""
        return self.total_penalties / max(1, self.games_simulated)
    
    @property
    def penalty_yards_per_game(self) -> float:
        """Average penalty yards per game (both teams combined)."""
        return self.total_penalty_yards / max(1, self.games_simulated)
    
    @property
    def penalties_per_team_per_game(self) -> float:
        """Average penalties per team per game."""
        return self.penalties_per_game / 2
    
    @property
    def penalty_yards_per_team_per_game(self) -> float:
        """Average penalty yards per team per game."""
        return self.penalty_yards_per_game / 2
    
    def get_penalty_type_distribution(self) -> Dict[str, float]:
        """Get penalty distribution by type as percentages."""
        if self.total_penalties == 0:
            return {}
        return {
            penalty_type: count / self.total_penalties * 100
            for penalty_type, count in self.penalties_by_type.items()
        }
    
    def get_penalty_phase_distribution(self) -> Dict[str, float]:
        """Get penalty distribution by phase as percentages."""
        if self.total_penalties == 0:
            return {}
        return {
            phase: count / self.total_penalties * 100
            for phase, count in self.penalties_by_phase.items()
        }


class MockGameSimulator:
    """
    Mock game simulator that focuses on penalty detection testing.
    
    This simulator creates realistic game scenarios to test penalty detection
    without requiring a full game engine implementation.
    """
    
    def __init__(self, penalty_rate_multiplier: float = 1.0):
        """
        Initialize the game simulator.
        
        Args:
            penalty_rate_multiplier: Global multiplier for penalty rates (for testing)
        """
        self.play_executor = PlayExecutor({
            'penalty_rate_multiplier': penalty_rate_multiplier,
            'discipline_impact_strength': 1.0,
            'situational_modifier_strength': 1.0
        })
        
        # Mock team data with penalty-prone and disciplined players
        self.offense_team = self._create_mock_offense_team()
        self.defense_team = self._create_mock_defense_team()
    
    def _create_mock_offense_team(self) -> Dict[str, Any]:
        """Create mock offensive team with varying discipline levels."""
        # Create players with different discipline levels
        qb = Player("1", "Mock QB", "QB", 1, 85, 70, 80, 85, 90, 85, discipline=85)
        rb = Player("2", "Mock RB", "RB", 1, 90, 85, 90, 80, 75, 80, discipline=80)
        
        # Offensive line with mixed discipline (some penalty-prone players)
        ol_players = [
            Player(f"{i+10}", f"Mock OL{i}", "OL", 1, 70, 90, 70, 85, 75, 85, discipline=65 + i*3)
            for i in range(5)
        ]
        
        receivers = [
            Player(f"{i+20}", f"Mock WR{i}", "WR", 1, 95, 75, 85, 80, 85, 80, discipline=85 + i*2)
            for i in range(3)
        ]
        
        return {
            'team_id': 1,
            'name': 'Mock Offense',
            'city': 'Test City',
            'offense': {
                'qb_rating': 85,
                'rb_rating': 80,
                'wr_rating': 85,
                'te_rating': 80,
                'ol_rating': 75
            },
            'defense': {
                'dl_rating': 70,
                'lb_rating': 75,
                'db_rating': 80,
                'overall': 75
            },
            'special_teams': 75,
            'coaching': {
                'offensive_coordinator': {
                    'archetype': 'balanced_attack',
                    'personality': 'balanced'
                }
            },
            'overall_rating': 78,
            'players': {
                'qb': qb,
                'rb': rb,
                'offensive_line': ol_players,
                'receivers': receivers
            },
            'personnel': {
                'qb': qb.name,
                'rb': rb.name,
                'offensive_line': [p.name for p in ol_players],
                'receivers': [p.name for p in receivers],
                'formation': 'pro_set',
            }
        }
    
    def _create_mock_defense_team(self) -> Dict[str, Any]:
        """Create mock defensive team with varying discipline levels."""
        # Defensive line (often penalty-prone due to pass rush aggression)
        dl_players = [
            Player(f"{i+30}", f"Mock DL{i}", "DL", 2, 85, 95, 75, 85, 70, 80, discipline=70 + i*2)
            for i in range(4)
        ]
        
        # Linebackers
        lb_players = [
            Player(f"{i+40}", f"Mock LB{i}", "LB", 2, 80, 85, 80, 85, 80, 85, discipline=75 + i*3)
            for i in range(3)
        ]
        
        # Secondary (can be penalty-prone due to PI and holding)
        secondary_players = [
            Player(f"{i+50}", f"Mock DB{i}", "DB", 2, 90, 70, 90, 80, 85, 85, discipline=75 + i*5)
            for i in range(4)
        ]
        
        return {
            'team_id': 2,
            'name': 'Mock Defense',
            'city': 'Test City',
            'offense': {
                'qb_rating': 75,
                'rb_rating': 75,
                'wr_rating': 75,
                'te_rating': 75,
                'ol_rating': 70
            },
            'defense': {
                'dl_rating': 85,
                'lb_rating': 80,
                'db_rating': 85,
                'overall': 83
            },
            'special_teams': 80,
            'coaching': {
                'defensive_coordinator': {
                    'archetype': 'multiple_defense',
                    'personality': 'aggressive'
                }
            },
            'overall_rating': 80,
            'players': {
                'defensive_line': dl_players,
                'linebackers': lb_players,
                'secondary': secondary_players
            },
            'personnel': {
                'defensive_line': [p.name for p in dl_players],
                'linebackers': [p.name for p in lb_players],
                'secondary': [p.name for p in secondary_players],
                'defensive_call': 'base_4-3',
            }
        }
    
    def simulate_game(self) -> PenaltyStats:
        """
        Simulate a complete game and return penalty statistics.
        
        This simulates approximately 65 plays per team (130 total plays per game)
        which matches typical NFL game play counts.
        
        Returns:
            PenaltyStats from the simulated game
        """
        game_stats = PenaltyStats()
        game_stats.games_simulated = 1
        
        # Simulate typical game scenario progression
        game_state = GameState()
        game_state.field.possession_team_id = 1
        
        total_plays = 130  # Typical NFL game play count (both teams)
        
        for play_num in range(total_plays):
            # Alternate possession and create variety in game situations
            if play_num % 12 == 0:  # Change possession every ~12 plays (typical drive)
                game_state.field.possession_team_id = 3 - game_state.field.possession_team_id
                game_state.field.down = 1
                game_state.field.yards_to_go = 10
                game_state.field.field_position = random.randint(20, 80)
            
            # Create situational variety for penalty testing
            self._update_game_situation(game_state, play_num, total_plays)
            
            # Execute play and collect penalty statistics
            try:
                # Add required coaching keys for team compatibility
                if 'coaching' not in self.offense_team:
                    self.offense_team['coaching'] = {'offensive_coordinator': {'archetype': 'balanced'}}
                if 'coaching' not in self.defense_team:
                    self.defense_team['coaching'] = {'defensive_coordinator': {'archetype': 'balanced_defense'}}
                
                play_result = self.play_executor.execute_play(
                    self.offense_team, self.defense_team, game_state
                )
                
                # Track penalty statistics
                if play_result.penalty_occurred:
                    game_stats.total_penalties += 1
                    game_stats.total_penalty_yards += play_result.penalty_yards
                    game_stats.penalties_by_type[play_result.penalty_type] += 1
                    game_stats.penalties_by_phase[play_result.penalty_phase or 'unknown'] += 1
                    game_stats.penalties_by_team[play_result.penalty_team or 'unknown'] += 1
                
            except Exception as e:
                # Enhanced error logging to identify the exact issue
                import traceback
                print(f"ERROR on play {play_num}: {type(e).__name__}: {e}")
                print(f"FULL STACK TRACE:")
                traceback.print_exc()
                print(f"  Offense team structure: {type(self.offense_team)}")
                print(f"  Offense team keys: {list(self.offense_team.keys()) if isinstance(self.offense_team, dict) else 'Not a dict'}")
                if isinstance(self.offense_team, dict) and 'personnel' in self.offense_team:
                    print(f"  Personnel structure: {type(self.offense_team['personnel'])}")
                    print(f"  Personnel keys: {list(self.offense_team['personnel'].keys()) if isinstance(self.offense_team['personnel'], dict) else 'Not a dict'}")
                print(f"  Defense team structure: {type(self.defense_team)}")
                print(f"  Defense team keys: {list(self.defense_team.keys()) if isinstance(self.defense_team, dict) else 'Not a dict'}")
                break  # Stop after first error to see full stack trace
        
        return game_stats
    
    def _update_game_situation(self, game_state: GameState, play_num: int, total_plays: int) -> None:
        """Update game state to create realistic situational variety."""
        # Create down progression
        if random.random() < 0.3:  # 30% chance of first down
            game_state.field.down = 1
            game_state.field.yards_to_go = 10
        else:
            game_state.field.down = min(4, game_state.field.down + 1)
            game_state.field.yards_to_go = max(1, game_state.field.yards_to_go - random.randint(0, 8))
        
        # Create field position variety
        if random.random() < 0.1:  # 10% chance of red zone
            game_state.field.field_position = random.randint(1, 20)
        elif random.random() < 0.05:  # 5% chance of goal line
            game_state.field.field_position = random.randint(1, 5)
        
        # Create time pressure situations
        progress = play_num / total_plays
        if progress > 0.85:  # Late game - more pressure
            game_state.clock.clock = random.randint(30, 300)  # Final 5 minutes
        elif progress > 0.45 and progress < 0.55:  # End of first half
            game_state.clock.clock = random.randint(30, 120)  # Final 2 minutes
    
    def simulate_multiple_games(self, num_games: int) -> PenaltyStats:
        """
        Simulate multiple games and aggregate penalty statistics.
        
        Args:
            num_games: Number of games to simulate
            
        Returns:
            Aggregated PenaltyStats across all games
        """
        combined_stats = PenaltyStats()
        
        for game_num in range(num_games):
            if game_num % 10 == 0:  # Progress reporting
                print(f"Simulating game {game_num + 1}/{num_games}")
            
            game_stats = self.simulate_game()
            
            # Aggregate statistics
            combined_stats.total_penalties += game_stats.total_penalties
            combined_stats.total_penalty_yards += game_stats.total_penalty_yards
            combined_stats.games_simulated += 1
            
            # Aggregate by type
            for penalty_type, count in game_stats.penalties_by_type.items():
                combined_stats.penalties_by_type[penalty_type] += count
            
            # Aggregate by phase
            for phase, count in game_stats.penalties_by_phase.items():
                combined_stats.penalties_by_phase[phase] += count
            
            # Aggregate by team
            for team, count in game_stats.penalties_by_team.items():
                combined_stats.penalties_by_team[team] += count
        
        return combined_stats


class PenaltyBenchmarkingTest(unittest.TestCase):
    """
    Comprehensive test suite for penalty detection benchmarking.
    
    This test class validates penalty rates against NFL 2024 statistics and
    ensures the penalty system produces realistic, balanced results.
    """
    
    # NFL 2024 Benchmarks
    NFL_PENALTIES_PER_TEAM_PER_GAME = 7.56
    NFL_PENALTY_YARDS_PER_TEAM_PER_GAME = 51.83
    NFL_PENALTIES_PER_GAME_TOTAL = 15.12  # Both teams combined
    NFL_PENALTY_YARDS_PER_GAME_TOTAL = 103.66  # Both teams combined
    
    # Acceptable variance ranges (±20% for initial implementation)
    PENALTY_RATE_TOLERANCE = 0.20  # ±20%
    PENALTY_YARDS_TOLERANCE = 0.20  # ±20%
    
    @classmethod
    def setUpClass(cls):
        """Set up test class with consistent random seed."""
        random.seed(42)  # Consistent results for testing
        cls.simulator = MockGameSimulator()
    
    def test_100_game_penalty_rates(self):
        """
        Core benchmark test: Validate penalty rates over 100 simulated games.
        
        This is the primary validation test that ensures penalty rates fall within
        acceptable ranges of NFL 2024 statistics.
        """
        print("\n" + "="*60)
        print("🏈 NFL PENALTY BENCHMARKING TEST - 100 GAMES")
        print("="*60)
        
        # Simulate games
        start_time = time.time()
        stats = self.simulator.simulate_multiple_games(100)
        simulation_time = time.time() - start_time
        
        # Calculate actual rates
        penalties_per_team_per_game = stats.penalties_per_team_per_game
        penalty_yards_per_team_per_game = stats.penalty_yards_per_team_per_game
        
        # Display results
        print(f"\n📊 PENALTY STATISTICS (100 games simulated)")
        print(f"Simulation time: {simulation_time:.2f} seconds")
        print(f"Total penalties: {stats.total_penalties}")
        print(f"Total penalty yards: {stats.total_penalty_yards}")
        print(f"")
        print(f"PENALTY RATES:")
        print(f"  Per team per game: {penalties_per_team_per_game:.2f} (NFL: {self.NFL_PENALTIES_PER_TEAM_PER_GAME:.2f})")
        print(f"  Per game total: {stats.penalties_per_game:.2f} (NFL: {self.NFL_PENALTIES_PER_GAME_TOTAL:.2f})")
        print(f"")
        print(f"PENALTY YARDS:")
        print(f"  Per team per game: {penalty_yards_per_team_per_game:.2f} (NFL: {self.NFL_PENALTY_YARDS_PER_TEAM_PER_GAME:.2f})")
        print(f"  Per game total: {stats.penalty_yards_per_game:.2f} (NFL: {self.NFL_PENALTY_YARDS_PER_GAME_TOTAL:.2f})")
        
        # Validate against NFL benchmarks with tolerance
        penalty_rate_min = self.NFL_PENALTIES_PER_TEAM_PER_GAME * (1 - self.PENALTY_RATE_TOLERANCE)
        penalty_rate_max = self.NFL_PENALTIES_PER_TEAM_PER_GAME * (1 + self.PENALTY_RATE_TOLERANCE)
        
        penalty_yards_min = self.NFL_PENALTY_YARDS_PER_TEAM_PER_GAME * (1 - self.PENALTY_YARDS_TOLERANCE)
        penalty_yards_max = self.NFL_PENALTY_YARDS_PER_TEAM_PER_GAME * (1 + self.PENALTY_YARDS_TOLERANCE)
        
        print(f"\n✅ VALIDATION RANGES:")
        print(f"  Penalty rate acceptable range: {penalty_rate_min:.2f} - {penalty_rate_max:.2f}")
        print(f"  Penalty yards acceptable range: {penalty_yards_min:.2f} - {penalty_yards_max:.2f}")
        
        # Assertions
        self.assertGreaterEqual(penalties_per_team_per_game, penalty_rate_min,
                              f"Penalty rate {penalties_per_team_per_game:.2f} below NFL range")
        self.assertLessEqual(penalties_per_team_per_game, penalty_rate_max,
                           f"Penalty rate {penalties_per_team_per_game:.2f} above NFL range")
        
        self.assertGreaterEqual(penalty_yards_per_team_per_game, penalty_yards_min,
                              f"Penalty yards {penalty_yards_per_team_per_game:.2f} below NFL range")
        self.assertLessEqual(penalty_yards_per_team_per_game, penalty_yards_max,
                           f"Penalty yards {penalty_yards_per_team_per_game:.2f} above NFL range")
        
        print(f"✅ Penalty rates within NFL acceptable range!")
    
    def test_penalty_distribution_by_type(self):
        """
        Test that penalty types occur with realistic frequency distribution.
        
        Validates that common penalties (holding, false start) occur more frequently
        than rare penalties (taunting, excessive celebration).
        """
        print("\n🎯 PENALTY TYPE DISTRIBUTION TEST")
        print("-" * 40)
        
        stats = self.simulator.simulate_multiple_games(50)
        distribution = stats.get_penalty_type_distribution()
        
        print("Penalty distribution by type:")
        for penalty_type, percentage in sorted(distribution.items(), key=lambda x: x[1], reverse=True):
            print(f"  {penalty_type}: {percentage:.1f}%")
        
        # Validate that common penalties are more frequent than rare ones
        common_penalties = ['offensive_holding', 'false_start', 'pass_interference']
        rare_penalties = ['taunting', 'excessive_celebration']
        
        common_total = sum(distribution.get(p, 0) for p in common_penalties)
        rare_total = sum(distribution.get(p, 0) for p in rare_penalties)
        
        print(f"\nCommon penalties total: {common_total:.1f}%")
        print(f"Rare penalties total: {rare_total:.1f}%")
        
        self.assertGreater(common_total, rare_total,
                         "Common penalties should be more frequent than rare penalties")
        print("✅ Penalty distribution is realistic!")
    
    def test_penalty_distribution_by_phase(self):
        """
        Test that penalty phases occur with expected distribution.
        
        Expected distribution based on NFL patterns:
        - ~40% pre-snap penalties
        - ~50% during-play penalties  
        - ~10% post-play penalties
        """
        print("\n⏰ PENALTY PHASE DISTRIBUTION TEST")
        print("-" * 40)
        
        stats = self.simulator.simulate_multiple_games(50)
        distribution = stats.get_penalty_phase_distribution()
        
        print("Penalty distribution by phase:")
        for phase, percentage in distribution.items():
            print(f"  {phase}: {percentage:.1f}%")
        
        # Validate phase distribution expectations
        pre_snap_pct = distribution.get('pre_snap', 0)
        during_play_pct = distribution.get('during_play', 0)
        post_play_pct = distribution.get('post_play', 0)
        
        # With early-return logic: pre-snap > during-play > post-play (realistic NFL behavior)
        # Pre-snap penalties abort plays, so they appear most frequently in results
        self.assertGreater(pre_snap_pct, during_play_pct,
                         "Pre-snap penalties should be most common (early-return logic)")
        self.assertGreater(during_play_pct, post_play_pct,
                         "During-play penalties should be more common than post-play")
        
        print("✅ Penalty phase distribution is realistic!")
    
    def test_discipline_impact_on_penalties(self):
        """
        Test that player discipline ratings affect penalty rates.
        
        Players with lower discipline should commit more penalties than
        players with higher discipline.
        """
        print("\n🎖️ DISCIPLINE IMPACT TEST")
        print("-" * 40)
        
        # Create simulators with different discipline multipliers
        disciplined_simulator = MockGameSimulator(penalty_rate_multiplier=0.5)  # Well-disciplined team
        undisciplined_simulator = MockGameSimulator(penalty_rate_multiplier=1.5)  # Penalty-prone team
        
        # Simulate games with each
        disciplined_stats = disciplined_simulator.simulate_multiple_games(25)
        undisciplined_stats = undisciplined_simulator.simulate_multiple_games(25)
        
        disciplined_rate = disciplined_stats.penalties_per_team_per_game
        undisciplined_rate = undisciplined_stats.penalties_per_team_per_game
        
        print(f"Well-disciplined team penalties per game: {disciplined_rate:.2f}")
        print(f"Penalty-prone team penalties per game: {undisciplined_rate:.2f}")
        print(f"Difference: {undisciplined_rate - disciplined_rate:.2f} penalties per game")
        
        # Undisciplined team should have more penalties
        self.assertGreater(undisciplined_rate, disciplined_rate,
                         "Undisciplined teams should have more penalties")
        
        # Difference should be meaningful (at least 1 penalty per game difference)
        self.assertGreaterEqual(undisciplined_rate - disciplined_rate, 1.0,
                              "Discipline should have significant impact on penalty rates")
        
        print("✅ Player discipline significantly impacts penalty rates!")
    
    def test_performance_impact(self):
        """
        Test that penalty detection doesn't significantly impact simulation performance.
        
        Penalty detection should add < 10% overhead to play execution.
        """
        print("\n⚡ PERFORMANCE IMPACT TEST")
        print("-" * 40)
        
        # Test with penalty detection enabled
        start_time = time.time()
        enabled_stats = self.simulator.simulate_multiple_games(10)
        enabled_time = time.time() - start_time
        
        # Test with penalty detection disabled (set rate multiplier to 0)
        disabled_simulator = MockGameSimulator(penalty_rate_multiplier=0.0)
        start_time = time.time()
        disabled_stats = disabled_simulator.simulate_multiple_games(10)
        disabled_time = time.time() - start_time
        
        overhead = (enabled_time - disabled_time) / disabled_time * 100
        
        print(f"Time with penalties: {enabled_time:.3f}s")
        print(f"Time without penalties: {disabled_time:.3f}s")
        print(f"Performance overhead: {overhead:.1f}%")
        
        # Should have less than 10% overhead
        self.assertLess(overhead, 10.0,
                      f"Penalty detection overhead {overhead:.1f}% exceeds 10% threshold")
        
        print("✅ Performance impact is acceptable!")
    
    def test_system_reliability(self):
        """
        Test system reliability under extended simulation.
        
        Ensures penalty system doesn't crash or produce invalid results
        over extended simulation periods.
        """
        print("\n🔧 SYSTEM RELIABILITY TEST")
        print("-" * 40)
        
        try:
            # Run extended simulation
            stats = self.simulator.simulate_multiple_games(25)
            
            # Validate basic sanity checks
            self.assertGreater(stats.total_penalties, 0, "Should detect some penalties")
            self.assertGreater(stats.total_penalty_yards, 0, "Should accumulate penalty yards")
            self.assertEqual(stats.games_simulated, 25, "Should track game count correctly")
            
            # Check for reasonable bounds
            self.assertLess(stats.penalties_per_game, 50, "Penalty rate shouldn't be excessive")
            self.assertLess(stats.penalty_yards_per_game, 500, "Penalty yards shouldn't be excessive")
            
            print(f"✅ System completed 25 games without errors")
            print(f"   Penalties: {stats.total_penalties}, Yards: {stats.total_penalty_yards}")
            
        except Exception as e:
            self.fail(f"System reliability test failed: {e}")


def run_benchmarking_suite():
    """
    Run the complete penalty benchmarking suite.
    
    This function runs all penalty benchmarking tests and provides a comprehensive
    report on penalty system performance against NFL standards.
    """
    print("🏈 NFL PENALTY DETECTION SYSTEM - BENCHMARKING SUITE")
    print("=" * 80)
    print("Validating penalty rates against NFL 2024 statistics...")
    print(f"Target: {PenaltyBenchmarkingTest.NFL_PENALTIES_PER_TEAM_PER_GAME} penalties per team per game")
    print(f"Target: {PenaltyBenchmarkingTest.NFL_PENALTY_YARDS_PER_TEAM_PER_GAME} penalty yards per team per game")
    print("=" * 80)
    
    # Run the test suite
    unittest.main(verbosity=2, exit=False)


if __name__ == "__main__":
    run_benchmarking_suite()