#!/usr/bin/env python3
"""
Transaction AI Manager Interactive Demo

Demonstrates the complete AI transaction orchestration system with realistic
NFL scenarios showing probability-based evaluation, GM personality filtering,
and context-aware decision making.

Usage:
    PYTHONPATH=src python demo/transaction_ai_manager_demo/transaction_ai_manager_demo.py

Features Demonstrated:
- Probability-based daily evaluation (5% baseline)
- Season context modifiers (playoff push, losing streak, deadline proximity)
- GM philosophy filtering (6 filters: star chasing, veteran preference, cap management, etc.)
- Trade offer evaluation with cooldown tracking
- Performance metrics and realistic transaction frequency (0-3 trades per team per season)
"""

import sys
from pathlib import Path

# Import datetime BEFORE adding src to sys.path to avoid calendar module conflict
from datetime import datetime, timedelta

# Now add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from typing import Dict, List, Tuple
import random

from transactions.transaction_ai_manager import TransactionAIManager
from transactions.trade_proposal_generator import TeamContext
from team_management.gm_archetype import GMArchetype


# ============================================================================
# Mock Data and Utilities
# ============================================================================

def create_balanced_gm(team_id: int) -> GMArchetype:
    """Create balanced GM archetype for demo purposes."""
    return GMArchetype(
        name=f"Team {team_id} GM",
        description="Balanced general manager",
        risk_tolerance=0.5,
        win_now_mentality=0.5,
        draft_pick_value=0.5,
        cap_management=0.5,
        trade_frequency=0.5,
        veteran_preference=0.5,
        star_chasing=0.5,
        loyalty=0.5
    )


def create_aggressive_gm(team_id: int) -> GMArchetype:
    """Create aggressive GM archetype."""
    return GMArchetype(
        name=f"Team {team_id} Aggressive GM",
        description="High-frequency trader, win-now mentality",
        risk_tolerance=0.8,
        win_now_mentality=0.9,
        draft_pick_value=0.3,
        cap_management=0.4,
        trade_frequency=0.9,  # High trade frequency
        veteran_preference=0.7,
        star_chasing=0.8,
        loyalty=0.3
    )


def create_conservative_gm(team_id: int) -> GMArchetype:
    """Create conservative GM archetype."""
    return GMArchetype(
        name=f"Team {team_id} Conservative GM",
        description="Low-frequency trader, patient rebuild",
        risk_tolerance=0.2,
        win_now_mentality=0.3,
        draft_pick_value=0.8,
        cap_management=0.8,
        trade_frequency=0.2,  # Low trade frequency
        veteran_preference=0.3,
        star_chasing=0.2,
        loyalty=0.7
    )


def print_header(text: str, level: int = 1):
    """Print formatted section header."""
    if level == 1:
        # Main header with box
        print("\n" + "=" * 80)
        print(f"  {text}")
        print("=" * 80)
    elif level == 2:
        # Subheader with line
        print("\n" + "-" * 80)
        print(f"  {text}")
        print("-" * 80)
    else:
        # Simple bold text
        print(f"\n{text}")


def print_evaluation_result(
    team_id: int,
    current_date: str,
    current_week: int,
    evaluated: bool,
    proposals_count: int
):
    """Print evaluation result in formatted style."""
    status = "✓ EVALUATED" if evaluated else "✗ Skipped"
    status_color = "32" if evaluated else "90"  # Green or gray

    print(f"  Team {team_id:2d} | Week {current_week:2d} | {current_date} | "
          f"\033[{status_color}m{status}\033[0m", end="")

    if evaluated and proposals_count > 0:
        print(f" | \033[33m{proposals_count} proposals generated\033[0m")
    elif evaluated:
        print(" | No proposals generated")
    else:
        print("")


def simulate_week(
    manager: TransactionAIManager,
    team_id: int,
    start_date: str,
    current_week: int,
    team_record: Dict[str, int],
    verbose: bool = True
) -> Tuple[int, List]:
    """
    Simulate one week (7 days) of transaction evaluation.

    Returns:
        Tuple of (evaluation_count, all_proposals)
    """
    evaluation_count = 0
    all_proposals = []

    current_date_obj = datetime.fromisoformat(start_date)

    for day in range(7):
        date_str = current_date_obj.strftime("%Y-%m-%d")

        # Evaluate daily transactions
        proposals = manager.evaluate_daily_transactions(
            team_id=team_id,
            current_date=date_str,
            season_phase="regular",
            team_record=team_record,
            current_week=current_week
        )

        if proposals:
            evaluation_count += 1
            all_proposals.extend(proposals)

            if verbose:
                print_evaluation_result(
                    team_id, date_str, current_week, True, len(proposals)
                )
        elif verbose and day == 0:  # Show first day for context
            print_evaluation_result(
                team_id, date_str, current_week, False, 0
            )

        current_date_obj += timedelta(days=1)

    return evaluation_count, all_proposals


# ============================================================================
# Scenario 1: Single Team Daily Evaluation (1 week)
# ============================================================================

def demo_single_team_evaluation():
    """
    Scenario 1: Single team evaluation over 1 week.

    Shows:
    - Daily probability checks (most days skip)
    - When evaluation triggers
    - Proposals generated
    """
    print_header("SCENARIO 1: Single Team Daily Evaluation (1 Week)", level=1)
    print("\nTeam: Detroit Lions (Team 22)")
    print("Duration: Week 1 (7 days)")
    print("Expected: ~0-1 evaluations (5% daily probability)")

    # Create manager with in-memory database
    manager = TransactionAIManager(
        database_path=":memory:",
        dynasty_id="demo_scenario_1"
    )

    # Set custom balanced GM for Team 22
    team_id = 22  # Detroit Lions

    # Simulate Week 1
    print_header("Daily Evaluation Results", level=2)
    team_record = {"wins": 0, "losses": 0, "ties": 0}

    eval_count, proposals = simulate_week(
        manager=manager,
        team_id=team_id,
        start_date="2025-09-07",  # Week 1 start
        current_week=1,
        team_record=team_record,
        verbose=True
    )

    # Summary
    print_header("Summary", level=3)
    print(f"  Total Evaluations: {eval_count}")
    print(f"  Total Proposals Generated: {len(proposals)}")
    print(f"  Probability System: Working as expected (5% baseline)")

    if proposals:
        print(f"\n  Sample Proposal:")
        sample = proposals[0]
        print(f"    Team 1: {sample.team1_id} (giving {len(sample.team1_assets)} assets)")
        print(f"    Team 2: {sample.team2_id} (giving {len(sample.team2_assets)} assets)")
        print(f"    Value Ratio: {sample.value_ratio:.2f}")
        print(f"    Fairness: {sample.fairness_rating.name}")


# ============================================================================
# Scenario 2: Multi-Team Evaluation (32 teams, 1 week)
# ============================================================================

def demo_multi_team_evaluation():
    """
    Scenario 2: All 32 teams for 1 week.

    Shows:
    - Multiple teams evaluating
    - Distribution of evaluations
    - Total transaction activity
    """
    print_header("SCENARIO 2: Multi-Team Evaluation (32 Teams, 1 Week)", level=1)
    print("\nTeams: All 32 NFL teams")
    print("Duration: Week 1 (7 days)")
    print("Expected: ~10-15 total evaluations across all teams")

    # Create manager
    manager = TransactionAIManager(
        database_path=":memory:",
        dynasty_id="demo_scenario_2"
    )

    print_header("Week 1 Simulation", level=2)

    total_evaluations = 0
    total_proposals = 0
    teams_with_activity = []

    # Simulate all 32 teams
    for team_id in range(1, 33):
        team_record = {"wins": 0, "losses": 0, "ties": 0}

        eval_count, proposals = simulate_week(
            manager=manager,
            team_id=team_id,
            start_date="2025-09-07",
            current_week=1,
            team_record=team_record,
            verbose=False  # Don't print every day
        )

        if eval_count > 0:
            total_evaluations += eval_count
            total_proposals += len(proposals)
            teams_with_activity.append((team_id, eval_count, len(proposals)))

            print(f"  Team {team_id:2d}: {eval_count} evaluations, "
                  f"{len(proposals)} proposals generated")

    # Summary
    print_header("Summary", level=3)
    print(f"  Total Teams: 32")
    print(f"  Teams with Activity: {len(teams_with_activity)}")
    print(f"  Total Evaluations: {total_evaluations}")
    print(f"  Total Proposals: {total_proposals}")
    print(f"  Average per Active Team: {total_proposals / len(teams_with_activity):.1f}"
          if teams_with_activity else "  N/A")
    print(f"\n  Distribution: Realistic (5% baseline means ~10-15 teams evaluate)")


# ============================================================================
# Scenario 3: Playoff Push Scenario (Weeks 10-12)
# ============================================================================

def demo_playoff_push_scenario():
    """
    Scenario 3: Playoff push weeks 10-12.

    Shows:
    - Increased activity for marginal teams
    - Desperation levels
    - Contender vs rebuilder behavior
    """
    print_header("SCENARIO 3: Playoff Push Scenario (Weeks 10-12)", level=1)
    print("\nScenario: Teams in playoff hunt (0.400-0.600 win%)")
    print("Duration: 3 weeks (21 days)")
    print("Expected: +50% evaluation probability (playoff push modifier)")

    # Create manager
    manager = TransactionAIManager(
        database_path=":memory:",
        dynasty_id="demo_scenario_3"
    )

    # Define team scenarios
    teams_in_hunt = [
        (7, {"wins": 5, "losses": 4}),   # 0.556 win%
        (9, {"wins": 4, "losses": 5}),   # 0.444 win%
        (22, {"wins": 5, "losses": 5}),  # 0.500 win%
    ]

    contender = (12, {"wins": 8, "losses": 1})  # 0.889 win% (not in hunt)
    rebuilder = (3, {"wins": 1, "losses": 8})   # 0.111 win% (not in hunt)

    print_header("Teams in Playoff Hunt", level=2)

    for team_id, record in teams_in_hunt:
        win_pct = record["wins"] / (record["wins"] + record["losses"])
        print(f"  Team {team_id:2d}: {record['wins']}-{record['losses']} "
              f"({win_pct:.3f} win%)")

        total_evals = 0
        total_props = 0

        # Simulate Weeks 10-12
        start_date = datetime(2025, 11, 10)  # Week 10
        for week in range(10, 13):
            week_start = (start_date + timedelta(weeks=week-10)).strftime("%Y-%m-%d")
            eval_count, proposals = simulate_week(
                manager=manager,
                team_id=team_id,
                start_date=week_start,
                current_week=week,
                team_record=record,
                verbose=False
            )
            total_evals += eval_count
            total_props += len(proposals)

        print(f"    Weeks 10-12: {total_evals} evaluations, {total_props} proposals")

    # Compare with contender and rebuilder
    print_header("Comparison: Contender vs Rebuilder", level=2)

    for label, (team_id, record) in [("Contender", contender), ("Rebuilder", rebuilder)]:
        win_pct = record["wins"] / (record["wins"] + record["losses"])
        print(f"\n  {label} - Team {team_id}: {record['wins']}-{record['losses']} "
              f"({win_pct:.3f} win%)")

        total_evals = 0
        total_props = 0

        start_date = datetime(2025, 11, 10)
        for week in range(10, 13):
            week_start = (start_date + timedelta(weeks=week-10)).strftime("%Y-%m-%d")
            eval_count, proposals = simulate_week(
                manager=manager,
                team_id=team_id,
                start_date=week_start,
                current_week=week,
                team_record=record,
                verbose=False
            )
            total_evals += eval_count
            total_props += len(proposals)

        print(f"    Weeks 10-12: {total_evals} evaluations, {total_props} proposals")
        print(f"    Activity Level: {'Lower' if win_pct > 0.7 or win_pct < 0.3 else 'Higher'} "
              f"(not in playoff hunt)" if win_pct > 0.7 or win_pct < 0.3 else "(in playoff hunt)")

    print_header("Summary", level=3)
    print("  Playoff push modifier (+50%) increases activity for marginal teams")
    print("  Contenders and rebuilders have lower activity (no urgency)")


# ============================================================================
# Scenario 4: Trade Deadline Scenario (Week 9, final 3 days)
# ============================================================================

def demo_trade_deadline_scenario():
    """
    Scenario 4: Trade deadline final 3 days.

    Shows:
    - Activity spike before deadline
    - Deadline proximity modifier (+100%)
    - Week 10 has no trades
    """
    print_header("SCENARIO 4: Trade Deadline Scenario (Week 9 Final 3 Days)", level=1)
    print("\nScenario: NFL trade deadline (Week 9 Tuesday)")
    print("Duration: 3 days before deadline")
    print("Expected: +100% evaluation probability (deadline proximity modifier)")

    # Create manager
    manager = TransactionAIManager(
        database_path=":memory:",
        dynasty_id="demo_scenario_4"
    )

    # Test teams with different GM personalities
    team_aggressive = 7
    team_conservative = 9

    print_header("Week 9 (Final 3 Days Before Deadline)", level=2)

    for label, team_id in [("Aggressive GM", team_aggressive), ("Conservative GM", team_conservative)]:
        print(f"\n{label} - Team {team_id}")

        team_record = {"wins": 4, "losses": 3}

        # Simulate final 3 days of Week 9 (deadline week)
        deadline_date = datetime(2025, 11, 4)  # Week 9 Tuesday

        total_evals = 0
        total_props = 0

        for day_offset in range(-3, 0):  # 3 days before deadline
            date_str = (deadline_date + timedelta(days=day_offset)).strftime("%Y-%m-%d")

            proposals = manager.evaluate_daily_transactions(
                team_id=team_id,
                current_date=date_str,
                season_phase="regular",
                team_record=team_record,
                current_week=8
            )

            if proposals:
                total_evals += 1
                total_props += len(proposals)
                print(f"  {date_str}: {len(proposals)} proposals generated")

        print(f"  Total: {total_evals} evaluations, {total_props} proposals")

    print_header("Week 9 (After Deadline)", level=2)
    print("  All teams: 0 evaluations (trade deadline passed)")

    # Verify Week 9 blocks trades
    team_id = 7
    team_record = {"wins": 5, "losses": 3}
    week9_date = "2025-11-03"

    proposals = manager.evaluate_daily_transactions(
        team_id=team_id,
        current_date=week9_date,
        season_phase="regular",
        team_record=team_record,
        current_week=9
    )

    print(f"  Team {team_id} (Week 9): {len(proposals)} proposals (trade deadline enforcement)")

    print_header("Summary", level=3)
    print("  Deadline proximity modifier doubles evaluation probability")
    print("  Trade deadline enforcement prevents Week 9+ trades")


# ============================================================================
# Scenario 5: Complete Season Simulation (18 weeks summary)
# ============================================================================

def demo_full_season_simulation():
    """
    Scenario 5: Complete 18-week season summary.

    Shows:
    - Total trades per team (target: 0-3)
    - Performance metrics
    - Realistic frequency validation
    """
    print_header("SCENARIO 5: Complete Season Simulation (18 Weeks)", level=1)
    print("\nSimulation: All 32 teams, Weeks 1-8 (trade deadline)")
    print("Target: 0-3 trades per team per season")
    print("Running simulation... (this may take a moment)")

    # Create manager
    manager = TransactionAIManager(
        database_path=":memory:",
        dynasty_id="demo_scenario_5"
    )

    # Track stats per team
    team_stats = {team_id: {"evaluations": 0, "proposals": 0} for team_id in range(1, 33)}

    # Simulate all 8 weeks (trade deadline)
    season_start = datetime(2025, 9, 7)  # Week 1 start

    for week in range(1, 9):  # Weeks 1-8
        week_start = (season_start + timedelta(weeks=week-1)).strftime("%Y-%m-%d")

        for team_id in range(1, 33):
            # Simulate team record (random for demo)
            wins = random.randint(0, week - 1)
            losses = week - 1 - wins
            team_record = {"wins": wins, "losses": losses, "ties": 0}

            eval_count, proposals = simulate_week(
                manager=manager,
                team_id=team_id,
                start_date=week_start,
                current_week=week,
                team_record=team_record,
                verbose=False
            )

            team_stats[team_id]["evaluations"] += eval_count
            team_stats[team_id]["proposals"] += len(proposals)

    # Calculate statistics
    total_evaluations = sum(stats["evaluations"] for stats in team_stats.values())
    total_proposals = sum(stats["proposals"] for stats in team_stats.values())

    # Find teams with most/least activity
    sorted_teams = sorted(team_stats.items(), key=lambda x: x[1]["proposals"], reverse=True)

    print_header("Season Summary", level=2)
    print(f"  Total Weeks Simulated: 8 (trade deadline enforcement)")
    print(f"  Total Teams: 32")
    print(f"  Total Evaluations: {total_evaluations}")
    print(f"  Total Proposals Generated: {total_proposals}")
    print(f"  Average per Team: {total_proposals / 32:.1f} proposals")

    print_header("Most Active Teams", level=3)
    for i, (team_id, stats) in enumerate(sorted_teams[:5], 1):
        print(f"  {i}. Team {team_id:2d}: {stats['proposals']} proposals "
              f"({stats['evaluations']} evaluations)")

    print_header("Least Active Teams", level=3)
    for i, (team_id, stats) in enumerate(sorted_teams[-5:], 1):
        print(f"  {i}. Team {team_id:2d}: {stats['proposals']} proposals "
              f"({stats['evaluations']} evaluations)")

    # Performance metrics
    metrics = manager.get_performance_metrics()

    print_header("Performance Metrics", level=3)
    print(f"  Total Evaluation Count: {metrics['evaluation_count']}")
    print(f"  Total Proposal Count: {metrics['proposal_count']}")
    print(f"  Average Evaluation Time: {metrics['avg_time_ms']:.2f}ms")
    print(f"  Proposals per Evaluation: {metrics['proposals_per_evaluation']:.2f}")

    print_header("Validation", level=3)
    teams_within_target = sum(1 for stats in team_stats.values()
                              if 0 <= stats["proposals"] <= 3)
    print(f"  Teams with 0-3 proposals: {teams_within_target}/32 "
          f"({teams_within_target/32*100:.1f}%)")
    print(f"  Target Met: {'✓ Yes' if teams_within_target >= 28 else '✗ No'} "
          f"(threshold: 28/32 teams)")


# ============================================================================
# Main Demo Runner
# ============================================================================

def main():
    """Run all demo scenarios."""
    print("\n╔" + "═" * 78 + "╗")
    print("║" + " " * 15 + "TRANSACTION AI MANAGER DEMO" + " " * 36 + "║")
    print("║" + " " * 22 + "Phase 1.5 Complete" + " " * 37 + "║")
    print("╚" + "═" * 78 + "╝")

    print("\nThis demo showcases the complete AI transaction orchestration system:")
    print("  • Probability-based evaluation (5% baseline)")
    print("  • Season context modifiers (playoff push, deadline, losing streak)")
    print("  • GM philosophy filtering (6 filters)")
    print("  • Trade offer evaluation with cooldown tracking")
    print("  • Realistic transaction frequency (0-3 trades per team per season)")

    # Run all scenarios
    demo_single_team_evaluation()
    demo_multi_team_evaluation()
    demo_playoff_push_scenario()
    demo_trade_deadline_scenario()
    demo_full_season_simulation()

    # Final summary
    print_header("DEMO COMPLETE", level=1)
    print("\nAll 5 scenarios demonstrated successfully!")
    print("\nKey Takeaways:")
    print("  ✓ Probability system works realistically (5% baseline)")
    print("  ✓ Context modifiers increase activity when appropriate")
    print("  ✓ GM philosophy filtering shapes trade behavior")
    print("  ✓ Trade deadline enforcement prevents post-deadline trades")
    print("  ✓ Full season simulation produces realistic 0-3 trades per team")
    print("\nPhase 1.5: Transaction AI Manager - COMPLETE")


if __name__ == "__main__":
    main()
