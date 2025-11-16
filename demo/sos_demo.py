#!/usr/bin/env python3
"""
Strength of Schedule (SOS) Calculation Demo

Demonstrates how SOS is calculated for NFL draft order tiebreakers.
Shows team records, opponents, and calculated SOS values.

SOS Formula: Average win percentage of all opponents faced

Usage:
    PYTHONPATH=src python demo/sos_demo.py
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from offseason.draft_order_service import (
    DraftOrderService,
    TeamRecord
)
from typing import List, Dict


def create_mock_team_records() -> List[TeamRecord]:
    """
    Create 32 mock team records with varied records.

    Includes teams with IDENTICAL records to demonstrate SOS tiebreaker.
    Records distributed across realistic NFL win-loss scenarios.
    """
    records = [
        # Bottom tier (4 picks, 2 tied at 4-13)
        TeamRecord(team_id=1, wins=4, losses=13, ties=0, win_percentage=0.235),
        TeamRecord(team_id=2, wins=4, losses=13, ties=0, win_percentage=0.235),  # TIED with 1
        TeamRecord(team_id=3, wins=5, losses=12, ties=0, win_percentage=0.294),
        TeamRecord(team_id=4, wins=5, losses=12, ties=0, win_percentage=0.294),  # TIED with 3

        # Lower tier (6 picks, 3 tied at 6-11)
        TeamRecord(team_id=5, wins=6, losses=11, ties=0, win_percentage=0.353),
        TeamRecord(team_id=6, wins=6, losses=11, ties=0, win_percentage=0.353),  # TIED with 5
        TeamRecord(team_id=7, wins=6, losses=11, ties=0, win_percentage=0.353),  # TIED with 5,6
        TeamRecord(team_id=8, wins=7, losses=10, ties=0, win_percentage=0.412),
        TeamRecord(team_id=9, wins=7, losses=10, ties=0, win_percentage=0.412),  # TIED with 8
        TeamRecord(team_id=10, wins=8, losses=9, ties=0, win_percentage=0.471),

        # Middle tier (bubble playoff teams)
        TeamRecord(team_id=11, wins=8, losses=9, ties=0, win_percentage=0.471),  # TIED with 10
        TeamRecord(team_id=12, wins=9, losses=8, ties=0, win_percentage=0.529),
        TeamRecord(team_id=13, wins=9, losses=8, ties=0, win_percentage=0.529),  # TIED with 12
        TeamRecord(team_id=14, wins=10, losses=7, ties=0, win_percentage=0.588),
        TeamRecord(team_id=15, wins=10, losses=7, ties=0, win_percentage=0.588),  # TIED with 14
        TeamRecord(team_id=16, wins=10, losses=7, ties=0, win_percentage=0.588),  # TIED with 14,15

        # Playoff tier
        TeamRecord(team_id=17, wins=11, losses=6, ties=0, win_percentage=0.647),
        TeamRecord(team_id=18, wins=11, losses=6, ties=0, win_percentage=0.647),  # TIED with 17
        TeamRecord(team_id=19, wins=11, losses=6, ties=0, win_percentage=0.647),  # TIED with 17,18
        TeamRecord(team_id=20, wins=12, losses=5, ties=0, win_percentage=0.706),
        TeamRecord(team_id=21, wins=12, losses=5, ties=0, win_percentage=0.706),  # TIED with 20
        TeamRecord(team_id=22, wins=13, losses=4, ties=0, win_percentage=0.765),

        # Upper tier (division winners)
        TeamRecord(team_id=23, wins=13, losses=4, ties=0, win_percentage=0.765),  # TIED with 22
        TeamRecord(team_id=24, wins=14, losses=3, ties=0, win_percentage=0.824),
        TeamRecord(team_id=25, wins=14, losses=3, ties=0, win_percentage=0.824),  # TIED with 24
        TeamRecord(team_id=26, wins=15, losses=2, ties=0, win_percentage=0.882),
        TeamRecord(team_id=27, wins=15, losses=2, ties=0, win_percentage=0.882),  # TIED with 26
        TeamRecord(team_id=28, wins=16, losses=1, ties=0, win_percentage=0.941),

        # Top tier (championship contenders)
        TeamRecord(team_id=29, wins=16, losses=1, ties=0, win_percentage=0.941),  # TIED with 28
        TeamRecord(team_id=30, wins=17, losses=0, ties=0, win_percentage=1.000),
        TeamRecord(team_id=31, wins=3, losses=14, ties=0, win_percentage=0.176),
        TeamRecord(team_id=32, wins=2, losses=15, ties=0, win_percentage=0.118),
    ]
    return records


def create_mock_schedules() -> Dict[int, List[int]]:
    """
    Create mock 17-game schedules for all teams.

    Schedules designed to create varied SOS values:
    - Bottom teams face easier schedules (lower SOS)
    - Top teams face harder schedules (higher SOS)
    - Tied teams have DIFFERENT opponent sets to demonstrate SOS tiebreaker

    Returns dict mapping team_id -> list of opponent_ids
    """
    schedules = {
        # Team 1 (4-13): Faced weaker schedule (easier opponents)
        1: [31, 32, 3, 4, 5, 8, 10, 11, 12, 14, 17, 19, 20, 22, 24, 26, 28],

        # Team 2 (4-13): Faced harder schedule than Team 1 (stronger opponents)
        2: [20, 22, 23, 24, 25, 26, 27, 28, 29, 30, 17, 18, 19, 14, 15, 16, 13],

        # Team 3 (5-12): Easier schedule
        3: [1, 31, 32, 4, 5, 8, 10, 11, 12, 14, 17, 19, 20, 22, 24, 26, 28],

        # Team 4 (5-12): Harder schedule than Team 3
        4: [20, 22, 23, 24, 25, 26, 27, 28, 29, 17, 18, 19, 14, 15, 16, 13, 12],

        # Team 5 (6-11): Easier schedule (more bad teams)
        5: [1, 2, 31, 32, 3, 4, 8, 10, 11, 12, 14, 17, 19, 20, 22, 24, 26],

        # Team 6 (6-11): Medium schedule
        6: [1, 3, 8, 10, 11, 12, 14, 17, 19, 20, 22, 24, 26, 28, 15, 16, 13],

        # Team 7 (6-11): Harder schedule (more good teams)
        7: [20, 22, 23, 24, 25, 26, 27, 28, 17, 18, 19, 14, 15, 16, 13, 12, 11],

        # Team 8 (7-10): Mixed schedule
        8: [1, 3, 5, 10, 11, 12, 14, 17, 19, 20, 22, 24, 26, 28, 15, 16, 13],

        # Team 9 (7-10): Different schedule from Team 8
        9: [2, 4, 6, 7, 20, 22, 24, 26, 28, 17, 18, 19, 14, 15, 16, 13, 12],

        # Team 10 (8-9): Balanced schedule
        10: [1, 3, 5, 8, 11, 12, 14, 17, 19, 20, 22, 24, 26, 28, 15, 16, 13],

        # Team 11 (8-9): Slightly harder than Team 10
        11: [2, 4, 6, 7, 9, 20, 22, 24, 26, 28, 17, 18, 19, 14, 15, 16, 13],

        # Team 12 (9-8): Mixed schedule
        12: [1, 3, 5, 8, 10, 14, 17, 19, 20, 22, 24, 26, 28, 15, 16, 13, 11],

        # Team 13 (9-8): Harder than Team 12
        13: [2, 4, 6, 7, 9, 11, 20, 22, 24, 26, 28, 17, 18, 19, 14, 15, 16],

        # Team 14 (10-7): Easier playoff schedule
        14: [1, 3, 5, 8, 10, 12, 17, 19, 20, 22, 24, 26, 28, 15, 16, 13, 11],

        # Team 15 (10-7): Medium playoff schedule
        15: [2, 4, 6, 8, 10, 12, 14, 17, 19, 20, 22, 24, 26, 28, 16, 13, 11],

        # Team 16 (10-7): Harder playoff schedule
        16: [4, 6, 7, 9, 11, 13, 20, 22, 24, 26, 28, 17, 18, 19, 14, 15, 12],

        # Team 17 (11-6): Easier among good teams
        17: [1, 3, 5, 8, 10, 12, 14, 19, 20, 22, 24, 26, 28, 15, 16, 13, 11],

        # Team 18 (11-6): Medium schedule
        18: [2, 4, 6, 8, 10, 12, 14, 17, 20, 22, 24, 26, 28, 15, 16, 13, 11],

        # Team 19 (11-6): Harder among good teams
        19: [4, 6, 7, 9, 11, 13, 15, 16, 20, 22, 24, 26, 28, 17, 18, 14, 12],

        # Team 20 (12-5): Easier for top team
        20: [1, 3, 5, 8, 10, 12, 14, 17, 19, 22, 24, 26, 28, 15, 16, 13, 11],

        # Team 21 (12-5): Harder for top team
        21: [2, 4, 6, 7, 9, 11, 13, 15, 16, 17, 18, 19, 22, 24, 26, 28, 14],

        # Team 22 (13-4): Balanced top schedule
        22: [1, 3, 5, 8, 10, 12, 14, 17, 19, 20, 24, 26, 28, 15, 16, 13, 11],

        # Team 23 (13-4): Harder top schedule
        23: [2, 4, 6, 7, 9, 11, 13, 15, 16, 17, 18, 19, 20, 21, 24, 26, 28],

        # Team 24 (14-3): Elite with easier path
        24: [1, 3, 5, 8, 10, 12, 14, 17, 19, 20, 22, 26, 28, 15, 16, 13, 11],

        # Team 25 (14-3): Elite with harder path
        25: [2, 4, 6, 7, 9, 11, 13, 15, 16, 17, 18, 19, 20, 21, 22, 23, 26],

        # Team 26 (15-2): Championship with easier schedule
        26: [1, 3, 5, 8, 10, 12, 14, 17, 19, 20, 22, 24, 28, 15, 16, 13, 11],

        # Team 27 (15-2): Championship with harder schedule
        27: [2, 4, 6, 7, 9, 11, 13, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24],

        # Team 28 (16-1): Best team, easier opponents
        28: [1, 3, 5, 8, 10, 12, 14, 17, 19, 20, 22, 24, 26, 15, 16, 13, 11],

        # Team 29 (16-1): Best team, harder opponents
        29: [2, 4, 6, 7, 9, 11, 13, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24],

        # Team 30 (17-0): Perfect season, balanced schedule
        30: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17],

        # Team 31 (3-14): Terrible team, easier schedule
        31: [1, 2, 3, 4, 5, 32, 8, 10, 11, 12, 14, 17, 19, 20, 22, 24, 26],

        # Team 32 (2-15): Worst team, harder schedule
        32: [20, 22, 23, 24, 25, 26, 27, 28, 29, 17, 18, 19, 14, 15, 16, 13, 31],
    }
    return schedules


def calculate_all_sos(
    records: List[TeamRecord],
    schedules: Dict[int, List[int]]
) -> Dict[int, float]:
    """Calculate SOS for all teams"""
    service = DraftOrderService(dynasty_id="demo", season_year=2025)
    sos_values = {}

    for team in records:
        schedule = schedules.get(team.team_id, [])
        if schedule:
            sos = service.calculate_strength_of_schedule(
                team_id=team.team_id,
                all_standings=records,
                schedule=schedule
            )
            sos_values[team.team_id] = sos
        else:
            sos_values[team.team_id] = 0.500

    return sos_values


def display_sos_table(
    records: List[TeamRecord],
    sos_values: Dict[int, float]
):
    """Display formatted table of teams, records, and SOS"""
    print("\n" + "="*80)
    print("STRENGTH OF SCHEDULE DEMONSTRATION")
    print("="*80)
    print(f"\n{'Team':<6} {'Record':<12} {'Win%':<8} {'SOS':<8} {'Notes'}")
    print("-"*80)

    # Sort by record (worst to best) then by SOS (higher = harder schedule)
    sorted_teams = sorted(
        records,
        key=lambda t: (t.win_percentage, -sos_values.get(t.team_id, 0.500))
    )

    for team in sorted_teams:
        sos = sos_values.get(team.team_id, 0.500)
        record = f"{team.wins}-{team.losses}-{team.ties}"

        # Highlight teams with identical records
        notes = ""
        tied_teams = [t for t in records if t.win_percentage == team.win_percentage and t.team_id != team.team_id]
        if tied_teams:
            notes = f"TIED (SOS breaks tie)"

        print(f"{team.team_id:<6} {record:<12} {team.win_percentage:.3f}   {sos:.3f}   {notes}")


def demonstrate_tiebreaker(
    records: List[TeamRecord],
    schedules: Dict[int, List[int]],
    sos_values: Dict[int, float]
):
    """Demonstrate how SOS breaks ties for draft order"""
    print("\n" + "="*80)
    print("TIEBREAKER DEMONSTRATIONS")
    print("="*80)

    # Find teams with identical records
    record_groups = {}
    for team in records:
        key = team.win_percentage
        if key not in record_groups:
            record_groups[key] = []
        record_groups[key].append(team)

    # Show detailed tiebreaker analysis for groups with 2+ teams
    tied_groups = {k: v for k, v in record_groups.items() if len(v) >= 2}

    for win_pct, teams in sorted(tied_groups.items()):
        if len(teams) < 2:
            continue

        print(f"\n{'─'*80}")
        record = f"{teams[0].wins}-{teams[0].losses}-{teams[0].ties}"
        print(f"SCENARIO: {len(teams)} teams finished {record} ({win_pct:.3f} win%)")
        print(f"{'─'*80}")

        # Sort by SOS (lower SOS = higher draft pick)
        teams_by_sos = sorted(teams, key=lambda t: sos_values.get(t.team_id, 0.500))

        for i, team in enumerate(teams_by_sos, 1):
            sos = sos_values.get(team.team_id, 0.500)
            schedule = schedules.get(team.team_id, [])

            print(f"\nTeam {team.team_id}:")
            print(f"  Record: {team.wins}-{team.losses}-{team.ties}")
            print(f"  Opponents: {schedule[:5]}... (first 5 of 17)")

            # Calculate opponent average win%
            opponent_records = [r for r in records if r.team_id in schedule]
            if opponent_records:
                avg_opp_win_pct = sum(r.win_percentage for r in opponent_records) / len(opponent_records)
                print(f"  Opponent avg win%: {avg_opp_win_pct:.3f}")

            print(f"  SOS: {sos:.3f}")

            if sos < 0.450:
                difficulty = "EASIER schedule"
            elif sos > 0.550:
                difficulty = "HARDER schedule"
            else:
                difficulty = "AVERAGE schedule"
            print(f"  Difficulty: {difficulty}")

        # Show draft order result
        print(f"\n{'─'*40}")
        print("DRAFT ORDER RESULT:")
        print(f"{'─'*40}")
        for i, team in enumerate(teams_by_sos, 1):
            sos = sos_values.get(team.team_id, 0.500)
            if i == 1:
                print(f"  #{i}: Team {team.team_id} picks FIRST (SOS: {sos:.3f} - easiest schedule)")
            elif i == len(teams_by_sos):
                print(f"  #{i}: Team {team.team_id} picks LAST (SOS: {sos:.3f} - hardest schedule)")
            else:
                print(f"  #{i}: Team {team.team_id} picks here (SOS: {sos:.3f})")

        print("\nKey Principle: LOWER SOS = HIGHER DRAFT PICK")
        print("(Teams that faced easier schedules pick before teams with harder schedules)")


def show_sos_formula():
    """Display the SOS calculation formula"""
    print("\n" + "="*80)
    print("STRENGTH OF SCHEDULE (SOS) FORMULA")
    print("="*80)
    print("\nSOS = Average win percentage of all opponents faced")
    print("\nCalculation Steps:")
    print("  1. Get team's 17-game schedule (list of opponent IDs)")
    print("  2. Look up each opponent's win percentage")
    print("  3. Calculate average: sum(opponent_win_pcts) / 17")
    print("  4. Result is team's SOS (range: 0.000 to 1.000)")
    print("\nExample:")
    print("  Team A opponents: 0.500, 0.600, 0.400, 0.550, ... (17 total)")
    print("  SOS = (0.500 + 0.600 + 0.400 + 0.550 + ...) / 17")
    print("  SOS = 0.520 (faced opponents with 52% average win rate)")
    print("\nInterpretation:")
    print("  SOS < 0.450: Easy schedule (opponents had losing records)")
    print("  SOS = 0.500: Average schedule (opponents were .500 teams)")
    print("  SOS > 0.550: Hard schedule (opponents had winning records)")


def show_draft_order_rules():
    """Display NFL draft order tiebreaker rules"""
    print("\n" + "="*80)
    print("NFL DRAFT ORDER TIEBREAKER RULES")
    print("="*80)
    print("\nFor non-playoff teams with identical records:")
    print("\n  1. LOWER win percentage picks HIGHER")
    print("     (4-13 team picks before 5-12 team)")
    print("\n  2. If win% tied, LOWER SOS picks HIGHER")
    print("     (Team with easier schedule gets higher pick)")
    print("\n  3. If SOS tied, division/conference tiebreakers apply")
    print("     (Same division → coin flip or rotation)")
    print("\nWhy SOS matters:")
    print("  - Rewards teams that struggled against weaker competition")
    print("  - Ensures fairness (team that faced 0.400 opponents picks")
    print("    before team that faced 0.600 opponents)")
    print("  - Prevents gaming the system (can't control opponent strength)")


def main():
    """Main demo execution"""
    print("\n" + "="*80)
    print("NFL STRENGTH OF SCHEDULE (SOS) CALCULATION DEMO")
    print("="*80)
    print("\nThis demo calculates SOS for 32 teams with realistic schedules")
    print("and demonstrates how SOS breaks draft order tiebreakers.")

    # Create mock data
    print("\nCreating mock team records and schedules...")
    records = create_mock_team_records()
    schedules = create_mock_schedules()

    # Calculate SOS
    print("Calculating Strength of Schedule for all 32 teams...")
    sos_values = calculate_all_sos(records, schedules)

    # Display results
    show_sos_formula()
    show_draft_order_rules()
    display_sos_table(records, sos_values)
    demonstrate_tiebreaker(records, schedules, sos_values)

    print("\n" + "="*80)
    print("Demo complete!")
    print("="*80)
    print("\nKey Takeaways:")
    print("  - SOS = average win% of all 17 opponents")
    print("  - Lower SOS = easier schedule = higher draft pick")
    print("  - Teams with identical records use SOS to break ties")
    print("  - SOS ranges from 0.000 (easiest) to 1.000 (hardest)")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
