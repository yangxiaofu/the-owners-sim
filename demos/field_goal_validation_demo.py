#!/usr/bin/env python3
"""
Field Goal & Extra Point Validation Demo

Runs 32-48 games in FULL play-by-play simulation mode and validates field goal
and extra point statistics against NFL benchmarks.

Usage:
    python demos/field_goal_validation_demo.py
    python demos/field_goal_validation_demo.py --num-games 32

Expected runtime: 3-5 minutes for 48 games
"""

import sys
import os
import argparse
import tempfile
import uuid
import random
from typing import List, Tuple, Dict

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from game_management.full_game_simulator import FullGameSimulator
from game_cycle.database.connection import GameCycleDatabase
from database.unified_api import UnifiedDatabaseAPI
from field_goal_tracker import FieldGoalTracker


class FieldGoalValidationDemo:
    """
    Main orchestrator for field goal/extra point validation demo.

    Runs 32-48 games in FULL simulation mode and validates kicking stats
    against NFL benchmarks.
    """

    # NFL Benchmarks (2015-2024 averages)
    NFL_BENCHMARKS = {
        'fg_0_39': {'min': 93.0, 'max': 97.0, 'avg': 95.0},
        'fg_40_49': {'min': 83.0, 'max': 87.0, 'avg': 85.0},
        'fg_50_plus': {'min': 63.0, 'max': 67.0, 'avg': 65.0},
        'extra_points': {'min': 92.0, 'max': 96.0, 'avg': 94.0}
    }

    def __init__(self, num_games: int = 48):
        """
        Initialize demo.

        Args:
            num_games: Number of games to simulate (32-48, default 48 = 3 weeks)
        """
        self.num_games = num_games
        self.db_path = self._create_temp_database()
        self.dynasty_id = self._create_temp_dynasty()
        self.fg_tracker = FieldGoalTracker()
        self._temp_db_path = None

    def run(self):
        """Execute full demo workflow."""
        print("=" * 80)
        print("FIELD GOAL & EXTRA POINT VALIDATION DEMO")
        print("=" * 80)
        print(f"Running {self.num_games} games in FULL simulation mode...")
        print()

        try:
            # Step 1: Run simulations
            game_results = self._simulate_games()

            # Step 2: Aggregate statistics
            stats = self._aggregate_stats(game_results)

            # Step 3: Validate benchmarks
            validation = self._validate_benchmarks(stats)

            # Step 4: Generate terminal report
            self._generate_report(game_results, stats, validation)

        finally:
            # Step 5: Cleanup (always runs)
            self._cleanup()

    def _simulate_games(self) -> List:
        """
        Run game simulations.

        Returns:
            List of GameResult objects
        """
        results = []
        matchups = self._generate_random_matchups()

        for i, (home_id, away_id) in enumerate(matchups):
            print(f"Game {i+1}/{self.num_games}: ", end="", flush=True)

            try:
                # Use FullGameSimulator with FULL mode
                simulator = FullGameSimulator(
                    away_team_id=away_id,
                    home_team_id=home_id,
                    dynasty_id=self.dynasty_id,
                    db_path=self.db_path
                )

                # Run full play-by-play simulation
                game_result = simulator.simulate_game()
                results.append(game_result)

                # Track FG distances from drive results
                self.fg_tracker.track_game(game_result)

                # Print quick summary
                away_abbr = getattr(game_result.away_team, 'abbreviation', 'AWAY')
                home_abbr = getattr(game_result.home_team, 'abbreviation', 'HOME')
                print(f"{away_abbr} {game_result.away_score} @ "
                      f"{home_abbr} {game_result.home_score}")

            except Exception as e:
                print(f"ERROR - {str(e)}")
                # Continue with remaining games

        print()
        return results

    def _aggregate_stats(self, game_results: List) -> Dict:
        """
        Collect kicking stats from all games.

        Args:
            game_results: List of GameResult objects

        Returns:
            Dict with FG/XP statistics
        """
        # Extract FG stats by distance from fg_tracker
        fg_0_39 = self.fg_tracker.get_by_range(0, 39)
        fg_40_49 = self.fg_tracker.get_by_range(40, 49)
        fg_50_plus = self.fg_tracker.get_by_range(50, 100)

        # Extract XP stats from player stats
        xp_attempts = 0
        xp_made = 0

        for game in game_results:
            if not hasattr(game, 'player_stats') or not game.player_stats:
                continue

            for player_stat in game.player_stats:
                # Handle both dict and object formats
                if isinstance(player_stat, dict):
                    position = player_stat.get('position')
                    xp_att = player_stat.get('extra_points_attempted', 0)
                    xp_m = player_stat.get('extra_points_made', 0)
                else:
                    position = getattr(player_stat, 'position', None)
                    xp_att = getattr(player_stat, 'extra_points_attempted', 0)
                    xp_m = getattr(player_stat, 'extra_points_made', 0)

                if position == 'K':
                    xp_attempts += xp_att
                    xp_made += xp_m

        return {
            'fg_0_39': fg_0_39,
            'fg_40_49': fg_40_49,
            'fg_50_plus': fg_50_plus,
            'xp_attempts': xp_attempts,
            'xp_made': xp_made,
            'total_games': len(game_results)
        }

    def _validate_benchmarks(self, stats: Dict) -> Dict:
        """
        Compare stats against NFL benchmarks.

        Args:
            stats: Aggregated statistics dict

        Returns:
            Dict with validation results for each category
        """
        results = {}

        # Validate FG ranges
        for category in ['fg_0_39', 'fg_40_49', 'fg_50_plus']:
            attempts, made = stats[category]
            accuracy = (made / attempts * 100) if attempts > 0 else 0
            benchmark = self.NFL_BENCHMARKS[category]

            results[category] = {
                'attempts': attempts,
                'made': made,
                'accuracy': accuracy,
                'benchmark': benchmark['avg'],
                'pass': benchmark['min'] <= accuracy <= benchmark['max'] if attempts > 0 else None
            }

        # Validate extra points
        xp_accuracy = ((stats['xp_made'] / stats['xp_attempts'] * 100)
                      if stats['xp_attempts'] > 0 else 0)
        xp_benchmark = self.NFL_BENCHMARKS['extra_points']

        results['extra_points'] = {
            'attempts': stats['xp_attempts'],
            'made': stats['xp_made'],
            'accuracy': xp_accuracy,
            'benchmark': xp_benchmark['avg'],
            'pass': (xp_benchmark['min'] <= xp_accuracy <= xp_benchmark['max']
                    if stats['xp_attempts'] > 0 else None)
        }

        return results

    def _generate_report(self, games: List, stats: Dict, validation: Dict):
        """
        Generate terminal report with tables.

        Args:
            games: List of game results
            stats: Aggregated statistics
            validation: Validation results
        """
        print("=" * 80)
        print("VALIDATION RESULTS")
        print("=" * 80)

        # Summary
        print(f"\n📊 Total Games: {stats['total_games']}")

        # FG by distance table
        print("\n🎯 FIELD GOAL ACCURACY BY DISTANCE")
        print("-" * 80)
        print(f"{'Range':<15} {'Att':>6} {'Made':>6} {'Accuracy':>10} {'NFL Avg':>10} {'Status':>12}")
        print("-" * 80)

        for category in ['fg_0_39', 'fg_40_49', 'fg_50_plus']:
            val = validation[category]

            if val['attempts'] == 0:
                status = "⚪ NO DATA"
                accuracy_str = "N/A"
            else:
                status = "✅ PASS" if val['pass'] else "❌ FAIL"
                accuracy_str = f"{val['accuracy']:.1f}%"

            print(f"{category:<15} {val['attempts']:>6} {val['made']:>6} "
                  f"{accuracy_str:>10} {val['benchmark']:>9.1f}% {status:>12}")

        # Extra points
        print("\n⭐ EXTRA POINT ACCURACY")
        print("-" * 80)
        xp_val = validation['extra_points']

        if xp_val['attempts'] == 0:
            print("No extra point attempts in games.")
        else:
            print(f"Attempts: {xp_val['attempts']}")
            print(f"Made: {xp_val['made']}")
            print(f"Accuracy: {xp_val['accuracy']:.1f}%")
            print(f"NFL Average: {xp_val['benchmark']:.1f}%")
            print(f"Status: {'✅ PASS' if xp_val['pass'] else '❌ FAIL'}")

            # Diagnose XP issue if failed
            if not xp_val['pass'] and xp_val['accuracy'] > 96.0:
                print("\n⚠️  ISSUE DETECTED: Extra point accuracy too high!")
                print("    Likely cause: PAT distance set to 24 yards instead of 33 yards")
                print("    Location: src/game_management/game_loop_controller.py:554")
                print("    Current: field_position=93 → 24-yard attempt (98% accuracy)")
                print("    Fix: Change to field_position=83 → 33-yard attempt (92% accuracy)")

        # Overall summary
        print("\n" + "=" * 80)
        all_passed = all(val['pass'] for val in validation.values() if val['pass'] is not None)
        if all_passed:
            print("✅ All benchmarks passed!")
        else:
            print("❌ Some benchmarks failed. See details above.")
        print("=" * 80)

    def _create_temp_database(self) -> str:
        """
        Create temporary database for testing.

        Returns:
            Path to temporary database
        """
        fd, path = tempfile.mkstemp(suffix='.db', prefix='fg_demo_')
        os.close(fd)

        # Initialize schema (happens automatically in __init__)
        db = GameCycleDatabase(path)
        db.close()

        self._temp_db_path = path
        return path

    def _create_temp_dynasty(self) -> str:
        """
        Create temporary dynasty for testing.

        Returns:
            Dynasty ID string
        """
        dynasty_id = f"fg_demo_{uuid.uuid4().hex[:8]}"

        # Initialize dynasty in database
        api = UnifiedDatabaseAPI(self.db_path)
        api.dynasty_initialize(
            dynasty_id=dynasty_id,
            dynasty_name="FG Validation Demo",
            user_team_id=1  # Arbitrary
        )

        return dynasty_id

    def _generate_random_matchups(self) -> List[Tuple[int, int]]:
        """
        Generate random NFL matchups without duplicates.

        Returns:
            List of (home_team_id, away_team_id) tuples
        """
        matchups = []
        used_pairs = set()

        while len(matchups) < self.num_games:
            home_id = random.randint(1, 32)
            away_id = random.randint(1, 32)

            # No team plays itself
            if home_id == away_id:
                continue

            # No duplicate matchups (regardless of home/away)
            pair = tuple(sorted([home_id, away_id]))
            if pair in used_pairs:
                continue

            matchups.append((home_id, away_id))
            used_pairs.add(pair)

        return matchups

    def _cleanup(self):
        """Remove temporary database."""
        if self._temp_db_path and os.path.exists(self._temp_db_path):
            try:
                os.remove(self._temp_db_path)
                print(f"\n🧹 Cleaned up temporary database")
            except Exception as e:
                print(f"\n⚠️  Warning: Could not remove temp database: {e}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Field Goal & Extra Point Validation Demo"
    )
    parser.add_argument(
        '--num-games',
        type=int,
        default=48,
        help='Number of games to simulate (default: 48)'
    )

    args = parser.parse_args()

    # Validate num_games
    if args.num_games < 1 or args.num_games > 100:
        print("Error: num-games must be between 1 and 100")
        sys.exit(1)

    # Run demo
    demo = FieldGoalValidationDemo(num_games=args.num_games)
    demo.run()


if __name__ == '__main__':
    main()
