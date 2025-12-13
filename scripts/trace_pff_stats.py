#!/usr/bin/env python3
"""
Trace PFF-critical stats through the pipeline.
Temporarily enables tracing in all relevant modules and runs a single game.
"""
import sys
import os
import uuid

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Enable tracing BEFORE importing modules
import play_engine.simulation.stats as stats_module
import game_cycle.services.game_simulator_service as sim_service_module

# Enable tracing flags
stats_module.PlayerStatsAccumulator._TRACE_PFF_STATS = True
sim_service_module.GameSimulatorService._TRACE_PFF_STATS = True

# Now import the rest
from game_cycle.services.game_simulator_service import GameSimulatorService, SimulationMode
from constants.team_ids import TeamIDs

DB_PATH = "data/database/game_cycle/game_cycle.db"

def get_dynasty_id():
    """Get the first dynasty from the database."""
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute("SELECT dynasty_id FROM dynasties LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    if row:
        return row[0]
    return None


def run_trace_game():
    """Run a single game with PFF stats tracing enabled."""
    print("=" * 80)
    print("PFF STATS TRACING - Running single game in FULL mode")
    print("=" * 80)

    dynasty_id = get_dynasty_id()
    if not dynasty_id:
        print("ERROR: No dynasty found in database. Please create one first via main2.py")
        return

    print(f"Dynasty ID: {dynasty_id}")

    # Initialize game simulator service
    service = GameSimulatorService(DB_PATH, dynasty_id)

    # Generate unique game ID
    game_id = f"TRACE_{uuid.uuid4().hex[:8]}"

    # Use Lions vs Bears
    home_team_id = TeamIDs.DETROIT_LIONS  # 22
    away_team_id = TeamIDs.CHICAGO_BEARS  # 5

    print(f"\nMatchup: Team {away_team_id} @ Team {home_team_id}")
    print(f"Game ID: {game_id}")

    print("\n" + "=" * 80)
    print("STARTING FULL GAME SIMULATION - Watch for [PFF_TRACE:*] messages")
    print("=" * 80 + "\n")

    # Run FULL simulation (this generates actual stats through the pipeline)
    result = service.simulate_game(
        game_id=game_id,
        home_team_id=home_team_id,
        away_team_id=away_team_id,
        mode=SimulationMode.FULL,
        season=2024,
        week=1,
        is_playoff=False
    )

    print("\n" + "=" * 80)
    print("GAME COMPLETE")
    print("=" * 80)
    print(f"Final Score: Away {result.away_score} - Home {result.home_score}")
    print(f"Total Plays: {result.total_plays}")

    # Analyze the accumulated stats for PFF-critical fields
    print("\n" + "=" * 80)
    print("ANALYZING OUTPUT STATS FOR PFF-CRITICAL FIELDS")
    print("=" * 80)

    pff_critical = {
        'coverage_targets', 'coverage_completions', 'coverage_yards_allowed',
        'pass_rush_wins', 'pass_rush_attempts', 'times_double_teamed', 'blocking_encounters',
        'broken_tackles', 'tackles_faced', 'yards_after_contact',
        'time_to_throw_total', 'throw_count', 'air_yards', 'pressures_faced',
        'sacks_allowed', 'pressures_allowed', 'hurries_allowed',
        'missed_tackles',
    }

    # Check returned player stats
    print(f"\n--- Player Stats Output ({len(result.player_stats)} players) ---")
    found_count = 0
    missing_count = 0

    for stats in result.player_stats[:30]:  # First 30 players
        player_name = stats.get('player_name', 'Unknown')
        position = stats.get('position', '?')
        pff_found = []
        for stat_name in pff_critical:
            value = stats.get(stat_name, 0)
            if value:
                pff_found.append(f"{stat_name}={value}")
        if pff_found:
            found_count += 1
            print(f"  {player_name} ({position}): {', '.join(pff_found)}")

    # Count stats by field
    print(f"\n--- PFF Stats Population Summary ---")
    for stat_name in sorted(pff_critical):
        count = sum(1 for s in result.player_stats if s.get(stat_name, 0) > 0)
        if count > 0:
            print(f"  {stat_name}: {count} players have non-zero values")
        else:
            missing_count += 1
            print(f"  {stat_name}: MISSING (all zeros)")

    print(f"\n--- Summary ---")
    print(f"Players with PFF stats: {found_count}")
    print(f"PFF stat fields completely missing: {missing_count}")

    print("\n" + "=" * 80)
    print("TRACE COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    run_trace_game()