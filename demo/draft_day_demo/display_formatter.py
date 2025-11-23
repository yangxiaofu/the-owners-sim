"""
Display Formatter for Draft Day Demo

Handles terminal output formatting with colors and interactive pauses.
"""

import sqlite3
from typing import List, Dict, Any


# ANSI color codes
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'


# NFL team names mapping (1-32)
TEAM_NAMES = {
    1: "Arizona Cardinals",
    2: "Atlanta Falcons",
    3: "Baltimore Ravens",
    4: "Buffalo Bills",
    5: "Carolina Panthers",
    6: "Chicago Bears",
    7: "Cincinnati Bengals",
    8: "Cleveland Browns",
    9: "Dallas Cowboys",
    10: "Denver Broncos",
    11: "Detroit Lions",
    12: "Green Bay Packers",
    13: "Houston Texans",
    14: "Indianapolis Colts",
    15: "Jacksonville Jaguars",
    16: "Kansas City Chiefs",
    17: "Las Vegas Raiders",
    18: "Los Angeles Chargers",
    19: "Los Angeles Rams",
    20: "Miami Dolphins",
    21: "Minnesota Vikings",
    22: "New England Patriots",
    23: "New Orleans Saints",
    24: "New York Giants",
    25: "New York Jets",
    26: "Philadelphia Eagles",
    27: "Pittsburgh Steelers",
    28: "San Francisco 49ers",
    29: "Seattle Seahawks",
    30: "Tampa Bay Buccaneers",
    31: "Tennessee Titans",
    32: "Washington Commanders"
}


def print_header():
    """Print demo header."""
    print(f"\n{Colors.BOLD}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}NFL DRAFT DAY SIMULATION DEMO{Colors.END}")
    print(f"{Colors.BOLD}{'='*80}{Colors.END}\n")


def print_setup_message():
    """Print setup message."""
    print(f"{Colors.YELLOW}Setting up in-memory database...{Colors.END}")


def print_setup_complete(counts: Dict[str, int]):
    """Print setup completion message."""
    print(f"{Colors.GREEN}✅ Mock data generated ({counts['prospects']} prospects, "
          f"{counts['teams']} teams, {counts['picks']} picks){Colors.END}\n")
    print(f"{Colors.YELLOW}Starting draft simulation...{Colors.END}\n")


def print_round_header(round_number: int):
    """Print round header."""
    print(f"\n{Colors.BOLD}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}ROUND {round_number}{Colors.END}")
    print(f"{Colors.BOLD}{'='*80}{Colors.END}\n")


def print_pick(
    pick_data: Dict[str, Any],
    cursor: sqlite3.Cursor,
    dynasty_id: str
):
    """
    Print formatted pick information.

    Args:
        pick_data: Pick result from DraftManager
        cursor: SQLite cursor for data lookup
        dynasty_id: Dynasty identifier
    """
    team_id = pick_data['team_id']
    overall_pick = pick_data['overall_pick']
    round_num = pick_data['round']
    pick_in_round = pick_data['pick_in_round']

    # Get team name
    team_name = TEAM_NAMES.get(team_id, f"Team {team_id}")

    # Get prospect details
    prospect_id = pick_data.get('prospect_id')
    if prospect_id:
        cursor.execute("""
            SELECT first_name, last_name, position, college,
                   overall_rating, potential_rating, age, ceiling, floor, archetype
            FROM draft_prospects
            WHERE prospect_id = ? AND dynasty_id = ?
        """, (prospect_id, dynasty_id))

        prospect = cursor.fetchone()
        if prospect:
            first_name, last_name, position, college, overall, potential, age, ceiling, floor, archetype = prospect

            # Get team needs
            cursor.execute("""
                SELECT position FROM team_needs
                WHERE team_id = ? AND dynasty_id = ?
                ORDER BY priority
                LIMIT 3
            """, (team_id, dynasty_id))
            needs = [row[0] for row in cursor.fetchall()]
            needs_str = ", ".join(needs)

            # Get GM personality
            cursor.execute("""
                SELECT archetype FROM gm_personalities
                WHERE team_id = ? AND dynasty_id = ?
            """, (team_id, dynasty_id))
            gm_row = cursor.fetchone()
            gm_archetype = gm_row[0] if gm_row else "Unknown"

            # Generate GM commentary based on archetype
            commentary = _generate_gm_commentary(gm_archetype, position, needs, overall, archetype)

            # Print pick
            print(f"{Colors.BOLD}Pick {overall_pick}: {team_name}{Colors.END}")
            print(f"  {Colors.CYAN}Needs: {needs_str}{Colors.END}")
            print(f"  {Colors.GREEN}Selects: {first_name} {last_name}{Colors.END}")
            print(f"  {Colors.YELLOW}Position: {position} | College: {college}{Colors.END}")
            print(f"  {Colors.BLUE}Ratings: {overall} OVR, {potential} POT | Age: {age} | "
                  f"Ceiling: {ceiling}, Floor: {floor}{Colors.END}")
            print(f"  {Colors.BOLD}{commentary}{Colors.END}")
            print()


def print_round_complete(round_number: int, total_rounds: int, interactive: bool = True):
    """Print round completion message."""
    print(f"\n{Colors.GREEN}✅ Round {round_number} complete!{Colors.END}")

    if round_number < total_rounds:
        if interactive:
            print(f"{Colors.YELLOW}Press Enter to continue to next round...{Colors.END}")
            try:
                input()
            except EOFError:
                # Non-interactive mode
                pass


def print_draft_complete(total_picks: int):
    """Print draft completion message."""
    print(f"\n{Colors.BOLD}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.GREEN}DRAFT COMPLETE!{Colors.END}")
    print(f"{Colors.BOLD}{'='*80}{Colors.END}\n")
    print(f"{Colors.CYAN}Total picks made: {total_picks}{Colors.END}")
    print(f"{Colors.GREEN}✅ All 32 teams have completed their draft classes{Colors.END}\n")


def _generate_gm_commentary(
    gm_archetype: str,
    position: str,
    needs: List[str],
    overall_rating: int,
    player_archetype: str
) -> str:
    """
    Generate GM commentary based on personality and pick context.

    Args:
        gm_archetype: GM personality type
        position: Player position
        needs: Team's top needs
        overall_rating: Player's overall rating
        player_archetype: Player's archetype

    Returns:
        Commentary string
    """
    is_need = position in needs
    is_elite = overall_rating >= 85
    is_high = overall_rating >= 75

    if gm_archetype == 'BPA':
        if is_elite:
            return f"GM Style: {Colors.BOLD}BPA GM selects elite talent regardless of fit{Colors.END}"
        else:
            return f"GM Style: BPA GM takes best available {player_archetype}"

    elif gm_archetype == 'Win-Now':
        if is_need:
            return f"GM Style: {Colors.BOLD}Win-Now GM targets immediate-impact {position}{Colors.END}"
        else:
            return f"GM Style: Win-Now GM adds {position} depth for playoff push"

    elif gm_archetype == 'Conservative':
        if is_high:
            return f"GM Style: Conservative GM takes safe, NFL-ready prospect"
        else:
            return f"GM Style: Conservative GM values consistency over upside"

    elif gm_archetype == 'Rebuilder':
        if overall_rating < 70:
            return f"GM Style: {Colors.BOLD}Rebuilder GM swings for high-ceiling {player_archetype}{Colors.END}"
        else:
            return f"GM Style: Rebuilder GM adds young talent to foundation"

    elif gm_archetype == 'Risk-Tolerant':
        return f"GM Style: Risk-Tolerant GM bets on {player_archetype} upside"

    elif gm_archetype == 'Aggressive Trader':
        if is_need:
            return f"GM Style: {Colors.BOLD}Aggressive Trader GM targets specific need{Colors.END}"
        else:
            return f"GM Style: Aggressive Trader GM makes bold BPA pick"

    else:
        return f"GM Style: Team selects {player_archetype}"


def print_summary_stats(result_data: Dict[str, Any]):
    """
    Print draft summary statistics.

    Args:
        result_data: Draft result data from DraftDayEvent
    """
    print(f"\n{Colors.BOLD}DRAFT SUMMARY{Colors.END}")
    print(f"{Colors.BOLD}{'-'*80}{Colors.END}")

    picks_by_round = result_data.get('picks_by_round', {})
    for round_num in sorted(picks_by_round.keys()):
        count = picks_by_round[round_num]
        print(f"  Round {round_num}: {count} picks")

    print(f"\n{Colors.CYAN}Total picks: {result_data.get('total_picks', 0)}{Colors.END}")
    print()
