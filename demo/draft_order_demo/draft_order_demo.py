#!/usr/bin/env python3
"""
Interactive NFL Draft Order Demo

Demonstrates the draft order calculation system with realistic mock data.
Shows how draft order is determined from regular season standings and playoff results.

Usage:
    python demo/draft_order_demo.py

    Or with PYTHONPATH:
    PYTHONPATH=src python demo/draft_order_demo.py

Features:
- View complete Round 1 draft order (picks 1-32)
- View other rounds (2-7)
- View all picks for a specific team
- Show SOS calculation details
- Explain tiebreaker logic
- Color-coded output for better readability
"""

import sys
from pathlib import Path

# Add src to path if needed
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from offseason.draft_order_service import (
    DraftOrderService,
    TeamRecord,
    DraftPickOrder
)
from team_management.teams.team_loader import get_team_by_id

# ANSI color codes for terminal output
class Colors:
    """ANSI color codes for terminal output"""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def create_mock_standings():
    """
    Create realistic 32-team standings with varied records.

    Returns:
        List of TeamRecord objects representing the final regular season standings
    """
    # Create realistic NFL records (worst to best)
    # Include teams with identical records for tiebreaker demonstration
    records = [
        # Bottom feeders (4-13 to 5-12)
        TeamRecord(team_id=26, wins=4, losses=13, ties=0, win_percentage=0.235),  # Carolina
        TeamRecord(team_id=18, wins=4, losses=13, ties=0, win_percentage=0.235),  # NY Giants
        TeamRecord(team_id=29, wins=5, losses=12, ties=0, win_percentage=0.294),  # Arizona
        TeamRecord(team_id=3, wins=5, losses=12, ties=0, win_percentage=0.294),   # New England

        # Bad teams (6-11 to 7-10)
        TeamRecord(team_id=12, wins=6, losses=11, ties=0, win_percentage=0.353),  # Tennessee
        TeamRecord(team_id=15, wins=6, losses=11, ties=0, win_percentage=0.353),  # Las Vegas
        TeamRecord(team_id=20, wins=7, losses=10, ties=0, win_percentage=0.412),  # Washington
        TeamRecord(team_id=4, wins=7, losses=10, ties=0, win_percentage=0.412),   # NY Jets

        # Below average (8-9)
        TeamRecord(team_id=21, wins=8, losses=9, ties=0, win_percentage=0.471),   # Chicago
        TeamRecord(team_id=25, wins=8, losses=9, ties=0, win_percentage=0.471),   # Atlanta
        TeamRecord(team_id=27, wins=8, losses=9, ties=0, win_percentage=0.471),   # New Orleans
        TeamRecord(team_id=11, wins=8, losses=9, ties=0, win_percentage=0.471),   # Jacksonville

        # Mediocre (9-8)
        TeamRecord(team_id=13, wins=9, losses=8, ties=0, win_percentage=0.529),   # Denver
        TeamRecord(team_id=16, wins=9, losses=8, ties=0, win_percentage=0.529),   # LA Chargers
        TeamRecord(team_id=28, wins=9, losses=8, ties=0, win_percentage=0.529),   # Tampa Bay
        TeamRecord(team_id=2, wins=9, losses=8, ties=0, win_percentage=0.529),    # Miami

        # Non-playoff fringe (10-7)
        TeamRecord(team_id=7, wins=10, losses=7, ties=0, win_percentage=0.588),   # Cleveland
        TeamRecord(team_id=17, wins=10, losses=7, ties=0, win_percentage=0.588),  # Dallas

        # Wild Card Round losers (11-6)
        TeamRecord(team_id=9, wins=11, losses=6, ties=0, win_percentage=0.647),   # Houston (WC loss)
        TeamRecord(team_id=30, wins=11, losses=6, ties=0, win_percentage=0.647),  # LA Rams (WC loss)
        TeamRecord(team_id=8, wins=11, losses=6, ties=0, win_percentage=0.647),   # Pittsburgh (WC loss)
        TeamRecord(team_id=23, wins=11, losses=6, ties=0, win_percentage=0.647),  # Green Bay (WC loss)
        TeamRecord(team_id=24, wins=11, losses=6, ties=0, win_percentage=0.647),  # Minnesota (WC loss)
        TeamRecord(team_id=1, wins=11, losses=6, ties=0, win_percentage=0.647),   # Buffalo (WC loss)

        # Divisional Round losers (12-5)
        TeamRecord(team_id=5, wins=12, losses=5, ties=0, win_percentage=0.706),   # Baltimore (Div loss)
        TeamRecord(team_id=19, wins=12, losses=5, ties=0, win_percentage=0.706),  # Philadelphia (Div loss)
        TeamRecord(team_id=10, wins=12, losses=5, ties=0, win_percentage=0.706),  # Indianapolis (Div loss)
        TeamRecord(team_id=32, wins=12, losses=5, ties=0, win_percentage=0.706),  # Seattle (Div loss)

        # Conference Championship losers (13-4)
        TeamRecord(team_id=6, wins=13, losses=4, ties=0, win_percentage=0.765),   # Cincinnati (Conf loss)
        TeamRecord(team_id=22, wins=13, losses=4, ties=0, win_percentage=0.765),  # Detroit (Conf loss)

        # Super Bowl participants (14-3)
        TeamRecord(team_id=31, wins=14, losses=3, ties=0, win_percentage=0.824),  # San Francisco (SB loss)
        TeamRecord(team_id=14, wins=14, losses=3, ties=0, win_percentage=0.824),  # Kansas City (SB win)
    ]

    return records


def create_mock_playoff_results():
    """
    Create realistic playoff results.

    Returns:
        Dict with playoff team categorization
    """
    return {
        'wild_card_losers': [9, 30, 8, 23, 24, 1],  # Houston, Rams, Pittsburgh, GB, Minnesota, Buffalo
        'divisional_losers': [5, 19, 10, 32],  # Baltimore, Philadelphia, Indianapolis, Seattle
        'conference_losers': [6, 22],  # Cincinnati, Detroit
        'super_bowl_loser': 31,  # San Francisco
        'super_bowl_winner': 14  # Kansas City
    }


def create_mock_schedules():
    """
    Create mock schedules for SOS calculation.

    Returns:
        Dict mapping team_id to list of opponent team_ids
    """
    # Simplified mock schedules (17 games each)
    # In reality, these would come from the actual NFL schedule
    schedules = {}

    # For demo purposes, create varied schedules
    # Teams that played harder schedules will have higher SOS
    for team_id in range(1, 33):
        # Create a schedule of 17 random opponents (excluding self)
        import random
        random.seed(team_id)  # Deterministic for demo
        all_teams = list(range(1, 33))
        all_teams.remove(team_id)
        schedules[team_id] = random.sample(all_teams, 17)

    return schedules


def calculate_all_sos(service, standings, schedules):
    """
    Pre-calculate SOS for all teams.

    Args:
        service: DraftOrderService instance
        standings: List of TeamRecord objects
        schedules: Dict of team schedules
    """
    for team_id in range(1, 33):
        if team_id in schedules:
            service.calculate_strength_of_schedule(
                team_id=team_id,
                all_standings=standings,
                schedule=schedules[team_id]
            )


def get_reason_display(reason):
    """
    Convert reason code to human-readable display text.

    Args:
        reason: Reason code (e.g., "non_playoff", "wild_card_loss")

    Returns:
        Formatted display string
    """
    reason_map = {
        "non_playoff": "Non-Playoff Team",
        "wild_card_loss": "Wild Card Loss",
        "divisional_loss": "Divisional Loss",
        "conference_loss": "Conference Loss",
        "super_bowl_loss": "Super Bowl Loss",
        "super_bowl_win": "Super Bowl Winner"
    }
    return reason_map.get(reason, reason)


def get_reason_color(reason):
    """
    Get color for reason display.

    Args:
        reason: Reason code

    Returns:
        ANSI color code
    """
    color_map = {
        "non_playoff": Colors.FAIL,
        "wild_card_loss": Colors.WARNING,
        "divisional_loss": Colors.OKCYAN,
        "conference_loss": Colors.OKBLUE,
        "super_bowl_loss": Colors.OKGREEN,
        "super_bowl_win": Colors.HEADER
    }
    return color_map.get(reason, Colors.ENDC)


def display_round_order(picks, round_number):
    """
    Display draft order for a specific round.

    Args:
        picks: List of all DraftPickOrder objects
        round_number: Round number to display (1-7)
    """
    print(f"\n{Colors.BOLD}{'='*95}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}2025 NFL DRAFT - ROUND {round_number}{Colors.ENDC}")
    print(f"{Colors.BOLD}{'='*95}{Colors.ENDC}")

    # Header
    print(f"\n{Colors.BOLD}{'Pick':<6} {'Team':<28} {'Record':<12} {'SOS':<8} {'Reason':<25}{Colors.ENDC}")
    print(f"{Colors.BOLD}{'-'*95}{Colors.ENDC}")

    # Filter picks for this round
    round_picks = [p for p in picks if p.round_number == round_number]

    for pick in round_picks:
        # Get team info
        team = get_team_by_id(pick.team_id)
        team_name = team.full_name if team else f"Team {pick.team_id}"

        # Calculate overall pick for display
        overall = f"#{pick.overall_pick}"

        # Format pick display
        pick_num = f"{pick.pick_in_round} ({overall})"

        # Get color for reason
        reason_color = get_reason_color(pick.reason)
        reason_display = get_reason_display(pick.reason)

        # Print row with color
        print(f"{pick_num:<6} {team_name:<28} {pick.team_record:<12} "
              f"{pick.strength_of_schedule:.3f}    {reason_color}{reason_display}{Colors.ENDC}")

    print()


def display_team_picks(picks, team_id):
    """
    Display all picks for a specific team.

    Args:
        picks: List of all DraftPickOrder objects
        team_id: Team ID to filter for
    """
    team = get_team_by_id(team_id)
    team_name = team.full_name if team else f"Team {team_id}"

    print(f"\n{Colors.BOLD}{'='*95}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.OKGREEN}DRAFT PICKS: {team_name}{Colors.ENDC}")
    print(f"{Colors.BOLD}{'='*95}{Colors.ENDC}")

    # Filter picks for this team
    team_picks = [p for p in picks if p.team_id == team_id]

    if not team_picks:
        print(f"\n{Colors.WARNING}No picks found for this team.{Colors.ENDC}\n")
        return

    # Display summary
    print(f"\n{Colors.BOLD}Total Picks: {len(team_picks)}{Colors.ENDC}")
    print(f"{Colors.BOLD}Record: {team_picks[0].team_record}{Colors.ENDC}")
    print(f"{Colors.BOLD}SOS: {team_picks[0].strength_of_schedule:.3f}{Colors.ENDC}")
    print(f"{Colors.BOLD}Reason: {get_reason_display(team_picks[0].reason)}{Colors.ENDC}")

    # Header
    print(f"\n{Colors.BOLD}{'Round':<8} {'Pick':<15} {'Overall':<10}{Colors.ENDC}")
    print(f"{Colors.BOLD}{'-'*35}{Colors.ENDC}")

    for pick in team_picks:
        round_str = f"Round {pick.round_number}"
        pick_str = f"Pick {pick.pick_in_round}"
        overall_str = f"#{pick.overall_pick}"

        print(f"{round_str:<8} {pick_str:<15} {overall_str:<10}")

    print()


def display_sos_details(service, standings, schedules, team_id):
    """
    Display detailed SOS calculation for a team.

    Args:
        service: DraftOrderService instance
        standings: List of TeamRecord objects
        schedules: Dict of team schedules
        team_id: Team ID to show details for
    """
    team = get_team_by_id(team_id)
    team_name = team.full_name if team else f"Team {team_id}"

    print(f"\n{Colors.BOLD}{'='*95}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.OKCYAN}STRENGTH OF SCHEDULE DETAILS: {team_name}{Colors.ENDC}")
    print(f"{Colors.BOLD}{'='*95}{Colors.ENDC}")

    if team_id not in schedules:
        print(f"\n{Colors.WARNING}No schedule data available for this team.{Colors.ENDC}\n")
        return

    # Get team's schedule
    schedule = schedules[team_id]

    # Build lookup for records
    records_map = {rec.team_id: rec for rec in standings}

    print(f"\n{Colors.BOLD}Opponents (17 games):{Colors.ENDC}")
    print(f"{Colors.BOLD}{'Opponent':<28} {'Record':<12} {'Win %':<10}{Colors.ENDC}")
    print(f"{Colors.BOLD}{'-'*50}{Colors.ENDC}")

    total_win_pct = 0.0
    for opp_id in schedule:
        opp_team = get_team_by_id(opp_id)
        opp_name = opp_team.full_name if opp_team else f"Team {opp_id}"

        if opp_id in records_map:
            opp_record = records_map[opp_id]
            print(f"{opp_name:<28} {str(opp_record):<12} {opp_record.win_percentage:.3f}")
            total_win_pct += opp_record.win_percentage

    # Calculate SOS
    sos = total_win_pct / len(schedule)

    print(f"\n{Colors.BOLD}SOS Calculation:{Colors.ENDC}")
    print(f"  Total opponent win percentage: {total_win_pct:.3f}")
    print(f"  Number of games: {len(schedule)}")
    print(f"  {Colors.OKGREEN}Strength of Schedule: {sos:.3f}{Colors.ENDC}")

    # Explain what this means
    print(f"\n{Colors.BOLD}What does this mean?{Colors.ENDC}")
    if sos < 0.450:
        print(f"  {Colors.OKGREEN}Easy schedule{Colors.ENDC} - Opponents had below-average records")
        print(f"  In draft tiebreakers, easier schedule = higher pick")
    elif sos > 0.550:
        print(f"  {Colors.FAIL}Hard schedule{Colors.ENDC} - Opponents had above-average records")
        print(f"  In draft tiebreakers, harder schedule = lower pick")
    else:
        print(f"  {Colors.OKCYAN}Average schedule{Colors.ENDC} - Opponents had average records")

    print()


def display_tiebreaker_explanation():
    """Display explanation of draft order tiebreaker rules."""
    print(f"\n{Colors.BOLD}{'='*95}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}NFL DRAFT ORDER TIEBREAKER RULES{Colors.ENDC}")
    print(f"{Colors.BOLD}{'='*95}{Colors.ENDC}")

    print(f"\n{Colors.BOLD}Round 1 Draft Order (Picks 1-32):{Colors.ENDC}")
    print(f"\n  {Colors.FAIL}1. Picks 1-18: Non-playoff teams{Colors.ENDC}")
    print(f"     • Sorted worst → best by record")
    print(f"     • Tiebreaker: Strength of Schedule (easier schedule picks first)")

    print(f"\n  {Colors.WARNING}2. Picks 19-24: Wild Card Round losers{Colors.ENDC}")
    print(f"     • Sorted worst → best by record")
    print(f"     • Tiebreaker: Strength of Schedule")

    print(f"\n  {Colors.OKCYAN}3. Picks 25-28: Divisional Round losers{Colors.ENDC}")
    print(f"     • Sorted worst → best by record")
    print(f"     • Tiebreaker: Strength of Schedule")

    print(f"\n  {Colors.OKBLUE}4. Picks 29-30: Conference Championship losers{Colors.ENDC}")
    print(f"     • Sorted worst → best by record")
    print(f"     • Tiebreaker: Strength of Schedule")

    print(f"\n  {Colors.OKGREEN}5. Pick 31: Super Bowl loser{Colors.ENDC}")

    print(f"\n  {Colors.HEADER}6. Pick 32: Super Bowl winner{Colors.ENDC}")

    print(f"\n{Colors.BOLD}Rounds 2-7:{Colors.ENDC}")
    print(f"     • Same order as Round 1 (262 total picks)")

    print(f"\n{Colors.BOLD}Strength of Schedule (SOS):{Colors.ENDC}")
    print(f"     • SOS = Average win percentage of all opponents faced")
    print(f"     • Formula: (Sum of opponent win %) / 17 games")
    print(f"     • Used ONLY for breaking ties between teams with identical records")
    print(f"     • {Colors.OKGREEN}Lower SOS (easier schedule) = Higher draft pick{Colors.ENDC}")

    print(f"\n{Colors.BOLD}Example Tiebreaker:{Colors.ENDC}")
    print(f"     • Team A: 4-13 record, SOS = 0.520 (harder schedule)")
    print(f"     • Team B: 4-13 record, SOS = 0.480 (easier schedule)")
    print(f"     • {Colors.OKGREEN}Team B picks first{Colors.ENDC} (easier schedule)")

    print()


def display_draft_summary(picks):
    """
    Display summary statistics about the draft.

    Args:
        picks: List of all DraftPickOrder objects
    """
    print(f"\n{Colors.BOLD}{'='*95}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}2025 NFL DRAFT SUMMARY{Colors.ENDC}")
    print(f"{Colors.BOLD}{'='*95}{Colors.ENDC}")

    # Count picks by reason
    reason_counts = {}
    for pick in picks:
        if pick.round_number == 1:  # Only count Round 1 for summary
            reason_counts[pick.reason] = reason_counts.get(pick.reason, 0) + 1

    print(f"\n{Colors.BOLD}Total Draft Picks: {len(picks)} (7 rounds × 32 teams){Colors.ENDC}")

    print(f"\n{Colors.BOLD}Round 1 Breakdown:{Colors.ENDC}")
    print(f"  {Colors.FAIL}Non-playoff teams:{Colors.ENDC} {reason_counts.get('non_playoff', 0)} picks (1-18)")
    print(f"  {Colors.WARNING}Wild Card losses:{Colors.ENDC} {reason_counts.get('wild_card_loss', 0)} picks (19-24)")
    print(f"  {Colors.OKCYAN}Divisional losses:{Colors.ENDC} {reason_counts.get('divisional_loss', 0)} picks (25-28)")
    print(f"  {Colors.OKBLUE}Conference losses:{Colors.ENDC} {reason_counts.get('conference_loss', 0)} picks (29-30)")
    print(f"  {Colors.OKGREEN}Super Bowl loser:{Colors.ENDC} {reason_counts.get('super_bowl_loss', 0)} pick (31)")
    print(f"  {Colors.HEADER}Super Bowl winner:{Colors.ENDC} {reason_counts.get('super_bowl_win', 0)} pick (32)")

    # Show teams with multiple first-round picks (trades would show here)
    print(f"\n{Colors.BOLD}Notes:{Colors.ENDC}")
    print(f"  • Draft order determined by regular season record + playoff results")
    print(f"  • Strength of Schedule used for tiebreakers")
    print(f"  • Trade picks not shown in this demo (all teams have original picks)")

    print()


def main_menu():
    """
    Display interactive menu.

    Returns:
        User's menu choice
    """
    print(f"\n{Colors.BOLD}{'='*95}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}NFL DRAFT ORDER DEMO - MAIN MENU{Colors.ENDC}")
    print(f"{Colors.BOLD}{'='*95}{Colors.ENDC}")
    print(f"\n{Colors.BOLD}Options:{Colors.ENDC}")
    print(f"  {Colors.OKGREEN}1.{Colors.ENDC} View Round 1 (Picks 1-32)")
    print(f"  {Colors.OKGREEN}2.{Colors.ENDC} View Other Rounds (2-7)")
    print(f"  {Colors.OKGREEN}3.{Colors.ENDC} View All Picks for a Team")
    print(f"  {Colors.OKGREEN}4.{Colors.ENDC} Show SOS Calculation Details")
    print(f"  {Colors.OKGREEN}5.{Colors.ENDC} Explain Tiebreaker Rules")
    print(f"  {Colors.OKGREEN}6.{Colors.ENDC} Draft Summary")
    print(f"  {Colors.OKGREEN}7.{Colors.ENDC} Exit")
    print()
    return input(f"{Colors.BOLD}Select option (1-7): {Colors.ENDC}").strip()


def main():
    """Main demo execution."""
    print(f"\n{Colors.BOLD}{Colors.HEADER}{'='*95}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}NFL DRAFT ORDER CALCULATION DEMO{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}{'='*95}{Colors.ENDC}")
    print(f"\n{Colors.OKCYAN}Initializing draft order calculation system...{Colors.ENDC}")

    # Create service
    service = DraftOrderService(dynasty_id="demo_dynasty", season_year=2025)

    # Create mock data
    print(f"{Colors.OKCYAN}Generating mock regular season standings...{Colors.ENDC}")
    standings = create_mock_standings()

    print(f"{Colors.OKCYAN}Loading playoff results...{Colors.ENDC}")
    playoff_results = create_mock_playoff_results()

    print(f"{Colors.OKCYAN}Calculating strength of schedule for all teams...{Colors.ENDC}")
    schedules = create_mock_schedules()
    calculate_all_sos(service, standings, schedules)

    # Calculate draft order
    print(f"{Colors.OKCYAN}Calculating complete 7-round draft order...{Colors.ENDC}")
    draft_picks = service.calculate_draft_order(standings, playoff_results)

    print(f"{Colors.OKGREEN}✓ Draft order calculated successfully ({len(draft_picks)} picks){Colors.ENDC}")

    # Interactive menu loop
    while True:
        choice = main_menu()

        if choice == "1":
            display_round_order(draft_picks, 1)
            input(f"\n{Colors.BOLD}Press Enter to continue...{Colors.ENDC}")

        elif choice == "2":
            round_input = input(f"{Colors.BOLD}Enter round number (2-7): {Colors.ENDC}").strip()
            try:
                round_num = int(round_input)
                if 2 <= round_num <= 7:
                    display_round_order(draft_picks, round_num)
                    input(f"\n{Colors.BOLD}Press Enter to continue...{Colors.ENDC}")
                else:
                    print(f"{Colors.FAIL}Invalid round number. Must be 2-7.{Colors.ENDC}")
            except ValueError:
                print(f"{Colors.FAIL}Invalid input. Please enter a number.{Colors.ENDC}")

        elif choice == "3":
            team_input = input(f"{Colors.BOLD}Enter team ID (1-32): {Colors.ENDC}").strip()
            try:
                team_id = int(team_input)
                if 1 <= team_id <= 32:
                    display_team_picks(draft_picks, team_id)
                    input(f"\n{Colors.BOLD}Press Enter to continue...{Colors.ENDC}")
                else:
                    print(f"{Colors.FAIL}Invalid team ID. Must be 1-32.{Colors.ENDC}")
            except ValueError:
                print(f"{Colors.FAIL}Invalid input. Please enter a number.{Colors.ENDC}")

        elif choice == "4":
            team_input = input(f"{Colors.BOLD}Enter team ID (1-32): {Colors.ENDC}").strip()
            try:
                team_id = int(team_input)
                if 1 <= team_id <= 32:
                    display_sos_details(service, standings, schedules, team_id)
                    input(f"\n{Colors.BOLD}Press Enter to continue...{Colors.ENDC}")
                else:
                    print(f"{Colors.FAIL}Invalid team ID. Must be 1-32.{Colors.ENDC}")
            except ValueError:
                print(f"{Colors.FAIL}Invalid input. Please enter a number.{Colors.ENDC}")

        elif choice == "5":
            display_tiebreaker_explanation()
            input(f"\n{Colors.BOLD}Press Enter to continue...{Colors.ENDC}")

        elif choice == "6":
            display_draft_summary(draft_picks)
            input(f"\n{Colors.BOLD}Press Enter to continue...{Colors.ENDC}")

        elif choice == "7":
            print(f"\n{Colors.OKGREEN}Exiting demo. Thanks for viewing!{Colors.ENDC}\n")
            break

        else:
            print(f"{Colors.FAIL}Invalid choice. Please select 1-7.{Colors.ENDC}")


if __name__ == "__main__":
    main()
