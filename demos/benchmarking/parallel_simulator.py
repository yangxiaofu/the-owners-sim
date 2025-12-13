"""
Parallel Game Simulator

Manages parallel execution of multiple game simulations using
multiprocessing for efficient benchmarking.
"""

import os
import sys
import time
import random
import tempfile
import uuid
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Any, Callable, Dict, List, Optional, Tuple
from contextlib import redirect_stdout, redirect_stderr
import io

# Add src to path for imports (needed in worker processes)
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)
if os.path.join(_PROJECT_ROOT, 'src') not in sys.path:
    sys.path.insert(0, os.path.join(_PROJECT_ROOT, 'src'))


def simulate_single_game(args: Tuple[int, int, int, bool]) -> Dict[str, Any]:
    """
    Worker function to simulate a single game.

    IMPORTANT: Must be module-level function for multiprocessing pickle.

    Args:
        args: Tuple of (game_id, away_team_id, home_team_id, suppress_output)

    Returns:
        Dictionary with game result and stats, or error info
    """
    game_id, away_id, home_id, suppress_output = args

    # Ensure path is set in worker process
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    if os.path.join(project_root, 'src') not in sys.path:
        sys.path.insert(0, os.path.join(project_root, 'src'))

    start_time = time.time()

    try:
        # Suppress output if requested
        if suppress_output:
            stdout_capture = io.StringIO()
            stderr_capture = io.StringIO()
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                result = _run_simulation(game_id, away_id, home_id)
        else:
            result = _run_simulation(game_id, away_id, home_id)

        elapsed = time.time() - start_time
        result['simulation_time'] = elapsed
        return result

    except Exception as e:
        elapsed = time.time() - start_time
        return {
            'game_id': game_id,
            'error': str(e),
            'away_team_id': away_id,
            'home_team_id': home_id,
            'simulation_time': elapsed,
        }


def _run_simulation(game_id: int, away_id: int, home_id: int) -> Dict[str, Any]:
    """
    Internal function to run the actual simulation.

    Uses demo mode (synthetic rosters) for isolated, database-free simulation.
    """
    from game_management.full_game_simulator import FullGameSimulator

    # Use demo mode (no dynasty_id, no db_path) for isolated simulation
    # This uses synthetic rosters generated on the fly
    simulator = FullGameSimulator(
        away_team_id=away_id,
        home_team_id=home_id,
        dynasty_id=None,  # Demo mode
        db_path=None      # No database
    )

    game_result = simulator.simulate_game()

    # Access comprehensive stats via stats_aggregator
    all_stats = {}
    if hasattr(simulator, '_game_loop_controller') and simulator._game_loop_controller:
        stats_agg = simulator._game_loop_controller.stats_aggregator
        if stats_agg:
            all_stats = stats_agg.get_all_statistics()

    return {
        'game_id': game_id,
        'game_result': game_result,
        'all_stats': all_stats,
        'away_team_id': away_id,
        'home_team_id': home_id,
    }


def _cleanup_temp_db(db_path: str):
    """Clean up temporary database and associated files."""
    for suffix in ['', '-shm', '-wal', '-journal']:
        path = db_path + suffix
        try:
            if os.path.exists(path):
                os.remove(path)
        except OSError:
            pass  # Ignore cleanup errors


class ParallelGameSimulator:
    """
    Manages parallel execution of multiple game simulations.

    Uses ProcessPoolExecutor to run games across multiple CPU cores.
    """

    def __init__(
        self,
        num_games: int = 500,
        num_workers: Optional[int] = None,
        suppress_output: bool = True
    ):
        """
        Initialize parallel simulator.

        Args:
            num_games: Target number of games to simulate (default 500)
            num_workers: Number of parallel processes (default: cpu_count - 1)
            suppress_output: Suppress game-by-game console output
        """
        self.num_games = num_games
        self.num_workers = num_workers or max(1, mp.cpu_count() - 1)
        self.suppress_output = suppress_output

    def generate_matchups(self) -> List[Tuple[int, int, int, bool]]:
        """
        Generate random but balanced matchups.

        Ensures diverse team pairings across all 32 teams.

        Returns:
            List of (game_id, away_team_id, home_team_id, suppress_output) tuples
        """
        matchups = []
        all_team_ids = list(range(1, 33))  # Teams 1-32

        for game_id in range(self.num_games):
            # Randomly select two different teams
            away_id, home_id = random.sample(all_team_ids, 2)
            matchups.append((game_id, away_id, home_id, self.suppress_output))

        return matchups

    def generate_round_robin_matchups(self) -> List[Tuple[int, int, int, bool]]:
        """
        Generate round-robin style matchups.

        Every team plays every other team at least once (if num_games allows).

        Returns:
            List of (game_id, away_team_id, home_team_id, suppress_output) tuples
        """
        matchups = []
        game_id = 0

        # Full round-robin: 32 teams = 32*31/2 = 496 unique matchups
        all_team_ids = list(range(1, 33))

        for i, away_id in enumerate(all_team_ids):
            for home_id in all_team_ids[i+1:]:
                if game_id >= self.num_games:
                    return matchups
                matchups.append((game_id, away_id, home_id, self.suppress_output))
                game_id += 1

        # If we need more games, add random matchups
        while len(matchups) < self.num_games:
            away_id, home_id = random.sample(all_team_ids, 2)
            matchups.append((len(matchups), away_id, home_id, self.suppress_output))

        return matchups

    def run_simulations(
        self,
        progress_callback: Optional[Callable[[int, int, float], None]] = None,
        use_round_robin: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Execute all simulations in parallel.

        Args:
            progress_callback: Optional callback(completed, total, eta_seconds)
            use_round_robin: Use round-robin matchups instead of random

        Returns:
            List of game result dictionaries
        """
        # Generate matchups
        if use_round_robin:
            matchups = self.generate_round_robin_matchups()
        else:
            matchups = self.generate_matchups()

        results = []
        completed = 0
        errors = 0
        start_time = time.time()

        # Use ProcessPoolExecutor for parallel execution
        with ProcessPoolExecutor(max_workers=self.num_workers) as executor:
            # Submit all tasks
            futures = {
                executor.submit(simulate_single_game, m): m
                for m in matchups
            }

            # Collect results as they complete
            for future in as_completed(futures):
                matchup = futures[future]
                try:
                    result = future.result(timeout=300)  # 5 minute timeout per game

                    if 'error' in result:
                        errors += 1
                        print(f"Game {result['game_id']} failed: {result['error']}")
                    else:
                        results.append(result)

                    completed += 1

                    if progress_callback:
                        elapsed = time.time() - start_time
                        if completed > 0:
                            eta = (elapsed / completed) * (self.num_games - completed)
                        else:
                            eta = 0
                        progress_callback(completed, self.num_games, eta)

                except Exception as e:
                    errors += 1
                    completed += 1
                    print(f"Game {matchup[0]} exception: {e}")

        return results

    def run_simulations_sequential(
        self,
        progress_callback: Optional[Callable[[int, int, float], None]] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute simulations sequentially (for debugging).

        Args:
            progress_callback: Optional callback(completed, total, eta_seconds)

        Returns:
            List of game result dictionaries
        """
        matchups = self.generate_matchups()
        results = []
        start_time = time.time()

        for i, matchup in enumerate(matchups):
            result = simulate_single_game(matchup)

            if 'error' not in result:
                results.append(result)
            else:
                print(f"Game {result['game_id']} failed: {result['error']}")

            if progress_callback:
                elapsed = time.time() - start_time
                completed = i + 1
                if completed > 0:
                    eta = (elapsed / completed) * (self.num_games - completed)
                else:
                    eta = 0
                progress_callback(completed, self.num_games, eta)

        return results
