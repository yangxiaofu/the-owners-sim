#!/usr/bin/env python3
"""
Playoff Manager and Scheduler Demo

Demonstrates NFL playoff bracket generation and progression through all rounds.

Shows:
1. Wild Card Round - 6 games (3 per conference)
2. Divisional Round - 4 games with re-seeding logic
3. Conference Championships - 2 games
4. Super Bowl - 1 game

Features:
- Color-coded terminal output
- Re-seeding demonstration (how #1 seed plays lowest remaining seed)
- Fake game results to show bracket progression
- Educational explanations of NFL playoff rules

Run: PYTHONPATH=src python demo/playoff_manager_demo/playoff_manager_demo.py
"""

import sys
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from playoff_system.playoff_manager import PlayoffManager
from playoff_system.playoff_seeder import PlayoffSeeder
from playoff_system.seeding_models import PlayoffSeed
from constants.team_ids import TeamIDs
from team_management.teams.team_loader import get_team_by_id, Team
from stores.standings_store import EnhancedTeamStanding
from shared.game_result import GameResult
from calendar.date_models import Date


# ANSI color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    RESET = '\033[0m'


def print_header(title: str):
    """Print formatted header."""
    print(f"\n{Colors.BOLD}{'='*100}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{title.center(100)}{Colors.RESET}")
    print(f"{Colors.BOLD}{'='*100}{Colors.RESET}\n")


def print_section(title: str):
    """Print section divider."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'─'*100}{Colors.RESET}")
    print(f"{Colors.BOLD}  {title}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'─'*100}{Colors.RESET}")


def print_subsection(title: str):
    """Print subsection divider."""
    print(f"\n{Colors.CYAN}{'▸ ' + title}{Colors.RESET}")


def create_week_18_standings():
    """
    Create realistic week 18 final standings (same as playoff_seeder_demo).

    This represents the end of the regular season with playoff bracket set.
    """
    standings = {}

    # AFC EAST: Bills win division
    standings[TeamIDs.BUFFALO_BILLS] = EnhancedTeamStanding(
        team_id=TeamIDs.BUFFALO_BILLS, wins=13, losses=4, points_for=452, points_against=310,
        division_wins=5, division_losses=1, conference_wins=10, conference_losses=2
    )
    standings[TeamIDs.MIAMI_DOLPHINS] = EnhancedTeamStanding(
        team_id=TeamIDs.MIAMI_DOLPHINS, wins=11, losses=6, points_for=420, points_against=345,
        division_wins=4, division_losses=2, conference_wins=8, conference_losses=4
    )
    standings[TeamIDs.NEW_YORK_JETS] = EnhancedTeamStanding(
        team_id=TeamIDs.NEW_YORK_JETS, wins=9, losses=8, points_for=385, points_against=390,
        division_wins=3, division_losses=3, conference_wins=7, conference_losses=5
    )
    standings[TeamIDs.NEW_ENGLAND_PATRIOTS] = EnhancedTeamStanding(
        team_id=TeamIDs.NEW_ENGLAND_PATRIOTS, wins=4, losses=13, points_for=295, points_against=475,
        division_wins=1, division_losses=5, conference_wins=3, conference_losses=9
    )

    # AFC NORTH: Ravens win division
    standings[TeamIDs.BALTIMORE_RAVENS] = EnhancedTeamStanding(
        team_id=TeamIDs.BALTIMORE_RAVENS, wins=14, losses=3, points_for=485, points_against=325,
        division_wins=5, division_losses=1, conference_wins=11, conference_losses=1
    )
    standings[TeamIDs.PITTSBURGH_STEELERS] = EnhancedTeamStanding(
        team_id=TeamIDs.PITTSBURGH_STEELERS, wins=10, losses=7, points_for=400, points_against=375,
        division_wins=3, division_losses=3, conference_wins=8, conference_losses=4
    )
    standings[TeamIDs.CLEVELAND_BROWNS] = EnhancedTeamStanding(
        team_id=TeamIDs.CLEVELAND_BROWNS, wins=9, losses=8, points_for=375, points_against=385,
        division_wins=2, division_losses=4, conference_wins=7, conference_losses=5
    )
    standings[TeamIDs.CINCINNATI_BENGALS] = EnhancedTeamStanding(
        team_id=TeamIDs.CINCINNATI_BENGALS, wins=8, losses=9, points_for=390, points_against=400,
        division_wins=2, division_losses=4, conference_wins=6, conference_losses=6
    )

    # AFC SOUTH: Texans win division
    standings[TeamIDs.HOUSTON_TEXANS] = EnhancedTeamStanding(
        team_id=TeamIDs.HOUSTON_TEXANS, wins=10, losses=7, points_for=395, points_against=370,
        division_wins=5, division_losses=1, conference_wins=8, conference_losses=4
    )
    standings[TeamIDs.JACKSONVILLE_JAGUARS] = EnhancedTeamStanding(
        team_id=TeamIDs.JACKSONVILLE_JAGUARS, wins=9, losses=8, points_for=380, points_against=385,
        division_wins=3, division_losses=3, conference_wins=7, conference_losses=5
    )
    standings[TeamIDs.INDIANAPOLIS_COLTS] = EnhancedTeamStanding(
        team_id=TeamIDs.INDIANAPOLIS_COLTS, wins=7, losses=10, points_for=350, points_against=395,
        division_wins=2, division_losses=4, conference_wins=5, conference_losses=7
    )
    standings[TeamIDs.TENNESSEE_TITANS] = EnhancedTeamStanding(
        team_id=TeamIDs.TENNESSEE_TITANS, wins=5, losses=12, points_for=310, points_against=435,
        division_wins=2, division_losses=4, conference_wins=4, conference_losses=8
    )

    # AFC WEST: Chiefs win division
    standings[TeamIDs.KANSAS_CITY_CHIEFS] = EnhancedTeamStanding(
        team_id=TeamIDs.KANSAS_CITY_CHIEFS, wins=15, losses=2, points_for=510, points_against=295,
        division_wins=6, division_losses=0, conference_wins=12, conference_losses=0
    )
    standings[TeamIDs.LOS_ANGELES_CHARGERS] = EnhancedTeamStanding(
        team_id=TeamIDs.LOS_ANGELES_CHARGERS, wins=11, losses=6, points_for=425, points_against=370,
        division_wins=4, division_losses=2, conference_wins=9, conference_losses=3
    )
    standings[TeamIDs.DENVER_BRONCOS] = EnhancedTeamStanding(
        team_id=TeamIDs.DENVER_BRONCOS, wins=8, losses=9, points_for=365, points_against=395,
        division_wins=2, division_losses=4, conference_wins=6, conference_losses=6
    )
    standings[TeamIDs.LAS_VEGAS_RAIDERS] = EnhancedTeamStanding(
        team_id=TeamIDs.LAS_VEGAS_RAIDERS, wins=5, losses=12, points_for=320, points_against=450,
        division_wins=1, division_losses=5, conference_wins=4, conference_losses=8
    )

    # NFC EAST: Eagles win division
    standings[TeamIDs.PHILADELPHIA_EAGLES] = EnhancedTeamStanding(
        team_id=TeamIDs.PHILADELPHIA_EAGLES, wins=14, losses=3, points_for=475, points_against=320,
        division_wins=5, division_losses=1, conference_wins=11, conference_losses=1
    )
    standings[TeamIDs.DALLAS_COWBOYS] = EnhancedTeamStanding(
        team_id=TeamIDs.DALLAS_COWBOYS, wins=12, losses=5, points_for=445, points_against=355,
        division_wins=4, division_losses=2, conference_wins=9, conference_losses=3
    )
    standings[TeamIDs.WASHINGTON_COMMANDERS] = EnhancedTeamStanding(
        team_id=TeamIDs.WASHINGTON_COMMANDERS, wins=9, losses=8, points_for=390, points_against=395,
        division_wins=3, division_losses=3, conference_wins=7, conference_losses=5
    )
    standings[TeamIDs.NEW_YORK_GIANTS] = EnhancedTeamStanding(
        team_id=TeamIDs.NEW_YORK_GIANTS, wins=5, losses=12, points_for=315, points_against=445,
        division_wins=1, division_losses=5, conference_wins=4, conference_losses=8
    )

    # NFC NORTH: Lions win division
    standings[TeamIDs.DETROIT_LIONS] = EnhancedTeamStanding(
        team_id=TeamIDs.DETROIT_LIONS, wins=13, losses=4, points_for=490, points_against=340,
        division_wins=5, division_losses=1, conference_wins=10, conference_losses=2
    )
    standings[TeamIDs.MINNESOTA_VIKINGS] = EnhancedTeamStanding(
        team_id=TeamIDs.MINNESOTA_VIKINGS, wins=11, losses=6, points_for=445, points_against=380,
        division_wins=4, division_losses=2, conference_wins=9, conference_losses=3
    )
    standings[TeamIDs.GREEN_BAY_PACKERS] = EnhancedTeamStanding(
        team_id=TeamIDs.GREEN_BAY_PACKERS, wins=10, losses=7, points_for=415, points_against=395,
        division_wins=3, division_losses=3, conference_wins=8, conference_losses=4
    )
    standings[TeamIDs.CHICAGO_BEARS] = EnhancedTeamStanding(
        team_id=TeamIDs.CHICAGO_BEARS, wins=6, losses=11, points_for=340, points_against=435,
        division_wins=1, division_losses=5, conference_wins=5, conference_losses=7
    )

    # NFC SOUTH: Falcons win division
    standings[TeamIDs.ATLANTA_FALCONS] = EnhancedTeamStanding(
        team_id=TeamIDs.ATLANTA_FALCONS, wins=11, losses=6, points_for=410, points_against=370,
        division_wins=5, division_losses=1, conference_wins=9, conference_losses=3
    )
    standings[TeamIDs.NEW_ORLEANS_SAINTS] = EnhancedTeamStanding(
        team_id=TeamIDs.NEW_ORLEANS_SAINTS, wins=9, losses=8, points_for=385, points_against=390,
        division_wins=3, division_losses=3, conference_wins=7, conference_losses=5
    )
    standings[TeamIDs.TAMPA_BAY_BUCCANEERS] = EnhancedTeamStanding(
        team_id=TeamIDs.TAMPA_BAY_BUCCANEERS, wins=8, losses=9, points_for=370, points_against=395,
        division_wins=2, division_losses=4, conference_wins=6, conference_losses=6
    )
    standings[TeamIDs.CAROLINA_PANTHERS] = EnhancedTeamStanding(
        team_id=TeamIDs.CAROLINA_PANTHERS, wins=4, losses=13, points_for=300, points_against=460,
        division_wins=1, division_losses=5, conference_wins=3, conference_losses=9
    )

    # NFC WEST: 49ers win division
    standings[TeamIDs.SAN_FRANCISCO_49ERS] = EnhancedTeamStanding(
        team_id=TeamIDs.SAN_FRANCISCO_49ERS, wins=15, losses=2, points_for=525, points_against=300,
        division_wins=6, division_losses=0, conference_wins=12, conference_losses=0
    )
    standings[TeamIDs.LOS_ANGELES_RAMS] = EnhancedTeamStanding(
        team_id=TeamIDs.LOS_ANGELES_RAMS, wins=10, losses=7, points_for=410, points_against=385,
        division_wins=3, division_losses=3, conference_wins=8, conference_losses=4
    )
    standings[TeamIDs.SEATTLE_SEAHAWKS] = EnhancedTeamStanding(
        team_id=TeamIDs.SEATTLE_SEAHAWKS, wins=9, losses=8, points_for=390, points_against=400,
        division_wins=2, division_losses=4, conference_wins=7, conference_losses=5
    )
    standings[TeamIDs.ARIZONA_CARDINALS] = EnhancedTeamStanding(
        team_id=TeamIDs.ARIZONA_CARDINALS, wins=6, losses=11, points_for=335, points_against=430,
        division_wins=1, division_losses=5, conference_wins=5, conference_losses=7
    )

    return standings


def display_wild_card_bracket(bracket, seeding):
    """Display wild card bracket with all 6 games."""
    print_section("WILD CARD ROUND - 6 GAMES")

    print(f"\n{Colors.YELLOW}NFL Playoff Structure:{Colors.RESET}")
    print("  • Seeds #1 earn first-round bye (Chiefs, 49ers)")
    print("  • Seeds #2-7 play in Wild Card Round")
    print("  • Higher seed hosts all playoff games")
    print("  • Single elimination - win or go home!\n")

    # AFC Games
    print(f"{Colors.BOLD}{Colors.GREEN}AFC WILD CARD GAMES{Colors.RESET}")
    print("─" * 80)
    afc_games = bracket.get_afc_games()
    for i, game in enumerate(sorted(afc_games, key=lambda g: g.game_number), start=1):
        away_team = get_team_by_id(game.away_team_id)
        home_team = get_team_by_id(game.home_team_id)
        away_seed_obj = seeding.afc.get_seed_by_number(game.away_seed)
        home_seed_obj = seeding.afc.get_seed_by_number(game.home_seed)

        print(f"  Game {game.game_number}: "
              f"{Colors.CYAN}({game.away_seed}){Colors.RESET} {away_team.full_name:32} "
              f"{away_seed_obj.record_string:8} @ "
              f"{Colors.GREEN}({game.home_seed}){Colors.RESET} {home_team.full_name:32} "
              f"{home_seed_obj.record_string:8}")
        print(f"           Date: {game.game_date}  |  {away_team.city} @ {home_team.city}")

    # NFC Games
    print(f"\n{Colors.BOLD}{Colors.GREEN}NFC WILD CARD GAMES{Colors.RESET}")
    print("─" * 80)
    nfc_games = bracket.get_nfc_games()
    for i, game in enumerate(sorted(nfc_games, key=lambda g: g.game_number), start=1):
        away_team = get_team_by_id(game.away_team_id)
        home_team = get_team_by_id(game.home_team_id)
        away_seed_obj = seeding.nfc.get_seed_by_number(game.away_seed)
        home_seed_obj = seeding.nfc.get_seed_by_number(game.home_seed)

        print(f"  Game {game.game_number}: "
              f"{Colors.CYAN}({game.away_seed}){Colors.RESET} {away_team.full_name:32} "
              f"{away_seed_obj.record_string:8} @ "
              f"{Colors.GREEN}({game.home_seed}){Colors.RESET} {home_team.full_name:32} "
              f"{home_seed_obj.record_string:8}")
        print(f"           Date: {game.game_date}  |  {away_team.city} @ {home_team.city}")


def display_divisional_bracket(bracket, seeding):
    """Display divisional bracket with re-seeding explanation."""
    print_section("DIVISIONAL ROUND - 4 GAMES WITH RE-SEEDING")

    print(f"\n{Colors.YELLOW}NFL Re-Seeding Rule:{Colors.RESET}")
    print("  • #1 seed (had bye) plays LOWEST REMAINING seed from wild card winners")
    print("  • Other two wild card winners play each other")
    print("  • Higher seed always hosts")
    print("  • This ensures #1 seed faces weakest opponent as reward for regular season performance\n")

    # AFC Games
    print(f"{Colors.BOLD}{Colors.GREEN}AFC DIVISIONAL GAMES{Colors.RESET}")
    print("─" * 80)
    afc_games = bracket.get_afc_games()
    for game in sorted(afc_games, key=lambda g: g.game_number):
        away_team = get_team_by_id(game.away_team_id)
        home_team = get_team_by_id(game.home_team_id)

        # Show re-seeding logic
        if game.home_seed == 1:
            annotation = f"{Colors.YELLOW}[#1 seed vs LOWEST remaining seed]{Colors.RESET}"
        else:
            annotation = f"{Colors.CYAN}[Other wild card winners]{Colors.RESET}"

        print(f"  Game {game.game_number}: "
              f"{Colors.CYAN}({game.away_seed}){Colors.RESET} {away_team.full_name:32} @ "
              f"{Colors.GREEN}({game.home_seed}){Colors.RESET} {home_team.full_name:32}")
        print(f"           {annotation}")
        print(f"           Date: {game.game_date}  |  {away_team.city} @ {home_team.city}")

    # NFC Games
    print(f"\n{Colors.BOLD}{Colors.GREEN}NFC DIVISIONAL GAMES{Colors.RESET}")
    print("─" * 80)
    nfc_games = bracket.get_nfc_games()
    for game in sorted(nfc_games, key=lambda g: g.game_number):
        away_team = get_team_by_id(game.away_team_id)
        home_team = get_team_by_id(game.home_team_id)

        # Show re-seeding logic
        if game.home_seed == 1:
            annotation = f"{Colors.YELLOW}[#1 seed vs LOWEST remaining seed]{Colors.RESET}"
        else:
            annotation = f"{Colors.CYAN}[Other wild card winners]{Colors.RESET}"

        print(f"  Game {game.game_number}: "
              f"{Colors.CYAN}({game.away_seed}){Colors.RESET} {away_team.full_name:32} @ "
              f"{Colors.GREEN}({game.home_seed}){Colors.RESET} {home_team.full_name:32}")
        print(f"           {annotation}")
        print(f"           Date: {game.game_date}  |  {away_team.city} @ {home_team.city}")


def display_conference_championship_bracket(bracket):
    """Display conference championship bracket."""
    print_section("CONFERENCE CHAMPIONSHIPS - 2 GAMES")

    print(f"\n{Colors.YELLOW}Conference Championship Round:{Colors.RESET}")
    print("  • AFC Champion vs NFC Champion advance to Super Bowl")
    print("  • Higher seed hosts")
    print("  • Winner represents conference in Super Bowl\n")

    # AFC Championship
    afc_games = bracket.get_afc_games()
    if afc_games:
        game = afc_games[0]
        away_team = get_team_by_id(game.away_team_id)
        home_team = get_team_by_id(game.home_team_id)

        print(f"{Colors.BOLD}{Colors.GREEN}AFC CHAMPIONSHIP{Colors.RESET}")
        print("─" * 80)
        print(f"  Game {game.game_number}: "
              f"{Colors.CYAN}({game.away_seed}){Colors.RESET} {away_team.full_name:32} @ "
              f"{Colors.GREEN}({game.home_seed}){Colors.RESET} {home_team.full_name:32}")
        print(f"           Date: {game.game_date}  |  {away_team.city} @ {home_team.city}")
        print(f"           {Colors.YELLOW}Winner advances to Super Bowl{Colors.RESET}")

    # NFC Championship
    nfc_games = bracket.get_nfc_games()
    if nfc_games:
        game = nfc_games[0]
        away_team = get_team_by_id(game.away_team_id)
        home_team = get_team_by_id(game.home_team_id)

        print(f"\n{Colors.BOLD}{Colors.GREEN}NFC CHAMPIONSHIP{Colors.RESET}")
        print("─" * 80)
        print(f"  Game {game.game_number}: "
              f"{Colors.CYAN}({game.away_seed}){Colors.RESET} {away_team.full_name:32} @ "
              f"{Colors.GREEN}({game.home_seed}){Colors.RESET} {home_team.full_name:32}")
        print(f"           Date: {game.game_date}  |  {away_team.city} @ {home_team.city}")
        print(f"           {Colors.YELLOW}Winner advances to Super Bowl{Colors.RESET}")


def display_super_bowl_bracket(bracket):
    """Display Super Bowl bracket."""
    print_section("SUPER BOWL - THE CHAMPIONSHIP")

    print(f"\n{Colors.YELLOW}The Big Game:{Colors.RESET}")
    print("  • AFC Champion vs NFC Champion")
    print("  • Neutral site (predetermined location)")
    print("  • Winner is NFL Champion\n")

    sb_game = bracket.get_super_bowl_game()
    if sb_game:
        away_team = get_team_by_id(sb_game.away_team_id)
        home_team = get_team_by_id(sb_game.home_team_id)

        print(f"{Colors.BOLD}{Colors.GREEN}SUPER BOWL{Colors.RESET}")
        print("─" * 80)
        print(f"  {Colors.CYAN}AFC Champion:{Colors.RESET} {away_team.full_name} ({sb_game.away_seed} seed)")
        print(f"  {Colors.CYAN}NFC Champion:{Colors.RESET} {home_team.full_name} ({sb_game.home_seed} seed)")
        print(f"  {Colors.YELLOW}Date:{Colors.RESET} {sb_game.game_date}")
        print(f"  {Colors.YELLOW}Location:{Colors.RESET} Neutral Site")
        print(f"\n  {Colors.BOLD}{Colors.GREEN}WINNER BECOMES NFL CHAMPION!{Colors.RESET}")


def create_fake_wild_card_results(seeding):
    """
    Create fake wild card results for demonstration.

    Simulates these results:
    AFC: #2 Ravens, #3 Bills, #5 Chargers win (lowest remaining seed is #5)
    NFC: #2 Eagles, #3 Lions, #4 Falcons win (lowest remaining seed is #4)

    Based on actual seeding:
    AFC: #1 Chiefs (bye), #2 Ravens, #3 Bills, #4 Texans, #5 Chargers, #6 Dolphins, #7 Steelers
    NFC: #1 49ers (bye), #2 Eagles, #3 Lions, #4 Falcons, #5 Cowboys, #6 Vikings, #7 Rams
    """
    results = []

    # AFC Game 1: (7) Steelers @ (2) Ravens → Ravens win 31-17
    ravens = get_team_by_id(TeamIDs.BALTIMORE_RAVENS)
    steelers = get_team_by_id(TeamIDs.PITTSBURGH_STEELERS)
    results.append(GameResult(
        home_team=ravens,
        away_team=steelers,
        final_score={TeamIDs.BALTIMORE_RAVENS: 31, TeamIDs.PITTSBURGH_STEELERS: 17}
    ))

    # AFC Game 2: (6) Chargers @ (3) Bills → Bills win 27-24
    bills = get_team_by_id(TeamIDs.BUFFALO_BILLS)
    chargers = get_team_by_id(TeamIDs.LOS_ANGELES_CHARGERS)
    results.append(GameResult(
        home_team=bills,
        away_team=chargers,
        final_score={TeamIDs.BUFFALO_BILLS: 27, TeamIDs.LOS_ANGELES_CHARGERS: 24}
    ))

    # AFC Game 3: (5) Dolphins @ (4) Texans → Dolphins win 28-23 (upset!)
    texans = get_team_by_id(TeamIDs.HOUSTON_TEXANS)
    dolphins = get_team_by_id(TeamIDs.MIAMI_DOLPHINS)
    results.append(GameResult(
        home_team=texans,
        away_team=dolphins,
        final_score={TeamIDs.MIAMI_DOLPHINS: 28, TeamIDs.HOUSTON_TEXANS: 23}
    ))

    # NFC Game 1: (7) Rams @ (2) Eagles → Eagles win 28-14
    eagles = get_team_by_id(TeamIDs.PHILADELPHIA_EAGLES)
    rams = get_team_by_id(TeamIDs.LOS_ANGELES_RAMS)
    results.append(GameResult(
        home_team=eagles,
        away_team=rams,
        final_score={TeamIDs.PHILADELPHIA_EAGLES: 28, TeamIDs.LOS_ANGELES_RAMS: 14}
    ))

    # NFC Game 2: (6) Vikings @ (3) Lions → Lions win 35-31
    lions = get_team_by_id(TeamIDs.DETROIT_LIONS)
    vikings = get_team_by_id(TeamIDs.MINNESOTA_VIKINGS)
    results.append(GameResult(
        home_team=lions,
        away_team=vikings,
        final_score={TeamIDs.DETROIT_LIONS: 35, TeamIDs.MINNESOTA_VIKINGS: 31}
    ))

    # NFC Game 3: (5) Cowboys @ (4) Falcons → Falcons win 24-21
    falcons = get_team_by_id(TeamIDs.ATLANTA_FALCONS)
    cowboys = get_team_by_id(TeamIDs.DALLAS_COWBOYS)
    results.append(GameResult(
        home_team=falcons,
        away_team=cowboys,
        final_score={TeamIDs.ATLANTA_FALCONS: 24, TeamIDs.DALLAS_COWBOYS: 21}
    ))

    return results


def display_wild_card_results(results):
    """Display fake wild card results."""
    print_subsection("WILD CARD RESULTS (Simulated)")

    print(f"\n{Colors.GREEN}AFC Results:{Colors.RESET}")
    for result in results[:3]:
        winner_id = max(result.final_score.keys(), key=lambda k: result.final_score[k])
        winner = get_team_by_id(winner_id)
        loser_id = min(result.final_score.keys(), key=lambda k: result.final_score[k])
        loser = get_team_by_id(loser_id)

        print(f"  {winner.full_name:32} {result.final_score[winner_id]:2} - "
              f"{result.final_score[loser_id]:2}  {loser.full_name}")

    print(f"\n{Colors.GREEN}NFC Results:{Colors.RESET}")
    for result in results[3:]:
        winner_id = max(result.final_score.keys(), key=lambda k: result.final_score[k])
        winner = get_team_by_id(winner_id)
        loser_id = min(result.final_score.keys(), key=lambda k: result.final_score[k])
        loser = get_team_by_id(loser_id)

        print(f"  {winner.full_name:32} {result.final_score[winner_id]:2} - "
              f"{result.final_score[loser_id]:2}  {loser.full_name}")

    print(f"\n{Colors.YELLOW}Advancing to Divisional Round:{Colors.RESET}")
    print(f"  AFC: Ravens (#2), Bills (#3), Dolphins (#5) + Chiefs (#1 bye)")
    print(f"  NFC: Eagles (#2), Lions (#3), Falcons (#4) + 49ers (#1 bye)")


def create_fake_divisional_results():
    """
    Create fake divisional results for demonstration.

    Simulates:
    AFC: Chiefs (#1) beat Dolphins (#5) 34-20, Bills (#3) beat Ravens (#2) 27-24
    NFC: 49ers (#1) beat Falcons (#4) 31-17, Lions (#3) beat Eagles (#2) 28-24
    """
    results = []

    # AFC: Chiefs beat Dolphins (lowest seed)
    chiefs = get_team_by_id(TeamIDs.KANSAS_CITY_CHIEFS)
    dolphins = get_team_by_id(TeamIDs.MIAMI_DOLPHINS)
    results.append(GameResult(
        home_team=chiefs,
        away_team=dolphins,
        final_score={TeamIDs.KANSAS_CITY_CHIEFS: 34, TeamIDs.MIAMI_DOLPHINS: 20}
    ))

    # AFC: Bills beat Ravens (upset!)
    bills = get_team_by_id(TeamIDs.BUFFALO_BILLS)
    ravens = get_team_by_id(TeamIDs.BALTIMORE_RAVENS)
    results.append(GameResult(
        home_team=bills,
        away_team=ravens,
        final_score={TeamIDs.BUFFALO_BILLS: 27, TeamIDs.BALTIMORE_RAVENS: 24}
    ))

    # NFC: 49ers beat Falcons (lowest seed)
    niners = get_team_by_id(TeamIDs.SAN_FRANCISCO_49ERS)
    falcons = get_team_by_id(TeamIDs.ATLANTA_FALCONS)
    results.append(GameResult(
        home_team=niners,
        away_team=falcons,
        final_score={TeamIDs.SAN_FRANCISCO_49ERS: 31, TeamIDs.ATLANTA_FALCONS: 17}
    ))

    # NFC: Lions beat Eagles (upset!)
    lions = get_team_by_id(TeamIDs.DETROIT_LIONS)
    eagles = get_team_by_id(TeamIDs.PHILADELPHIA_EAGLES)
    results.append(GameResult(
        home_team=lions,
        away_team=eagles,
        final_score={TeamIDs.DETROIT_LIONS: 28, TeamIDs.PHILADELPHIA_EAGLES: 24}
    ))

    return results


def display_divisional_results(results):
    """Display fake divisional results."""
    print_subsection("DIVISIONAL ROUND RESULTS (Simulated)")

    print(f"\n{Colors.GREEN}AFC Results:{Colors.RESET}")
    for result in results[:2]:
        winner_id = max(result.final_score.keys(), key=lambda k: result.final_score[k])
        winner = get_team_by_id(winner_id)
        loser_id = min(result.final_score.keys(), key=lambda k: result.final_score[k])
        loser = get_team_by_id(loser_id)

        print(f"  {winner.full_name:32} {result.final_score[winner_id]:2} - "
              f"{result.final_score[loser_id]:2}  {loser.full_name}")

    print(f"\n{Colors.GREEN}NFC Results:{Colors.RESET}")
    for result in results[2:]:
        winner_id = max(result.final_score.keys(), key=lambda k: result.final_score[k])
        winner = get_team_by_id(winner_id)
        loser_id = min(result.final_score.keys(), key=lambda k: result.final_score[k])
        loser = get_team_by_id(loser_id)

        print(f"  {winner.full_name:32} {result.final_score[winner_id]:2} - "
              f"{result.final_score[loser_id]:2}  {loser.full_name}")

    print(f"\n{Colors.YELLOW}Advancing to Conference Championships:{Colors.RESET}")
    print(f"  AFC: Chiefs (#1), Bills (#3)")
    print(f"  NFC: 49ers (#1), Lions (#3)")


def create_fake_conference_championship_results():
    """
    Create fake conference championship results.

    Simulates:
    AFC: Chiefs (#1) beat Bills (#3) 31-28
    NFC: 49ers (#1) beat Lions (#3) 24-21
    """
    results = []

    # AFC Championship: Chiefs beat Bills
    chiefs = get_team_by_id(TeamIDs.KANSAS_CITY_CHIEFS)
    bills = get_team_by_id(TeamIDs.BUFFALO_BILLS)
    results.append(GameResult(
        home_team=chiefs,
        away_team=bills,
        final_score={TeamIDs.KANSAS_CITY_CHIEFS: 31, TeamIDs.BUFFALO_BILLS: 28}
    ))

    # NFC Championship: 49ers beat Lions
    niners = get_team_by_id(TeamIDs.SAN_FRANCISCO_49ERS)
    lions = get_team_by_id(TeamIDs.DETROIT_LIONS)
    results.append(GameResult(
        home_team=niners,
        away_team=lions,
        final_score={TeamIDs.SAN_FRANCISCO_49ERS: 24, TeamIDs.DETROIT_LIONS: 21}
    ))

    return results


def display_conference_championship_results(results):
    """Display fake conference championship results."""
    print_subsection("CONFERENCE CHAMPIONSHIP RESULTS (Simulated)")

    print(f"\n{Colors.GREEN}Results:{Colors.RESET}")
    for result in results:
        winner_id = max(result.final_score.keys(), key=lambda k: result.final_score[k])
        winner = get_team_by_id(winner_id)
        loser_id = min(result.final_score.keys(), key=lambda k: result.final_score[k])
        loser = get_team_by_id(loser_id)

        conf = "AFC" if winner_id <= 16 else "NFC"
        print(f"  {conf} Championship: "
              f"{winner.full_name:32} {result.final_score[winner_id]:2} - "
              f"{result.final_score[loser_id]:2}  {loser.full_name}")

    print(f"\n{Colors.YELLOW}Super Bowl Matchup:{Colors.RESET}")
    print(f"  Kansas City Chiefs (#1 AFC) vs San Francisco 49ers (#1 NFC)")


def main():
    """Main demo execution."""
    print_header("NFL PLAYOFF MANAGER & SCHEDULER DEMO")

    print(f"\n{Colors.BOLD}This demo shows complete playoff bracket generation and progression.{Colors.RESET}")
    print(f"{Colors.CYAN}We'll use Week 18 seeding data and simulate playoff results to show bracket dynamics.{Colors.RESET}\n")

    print("Features demonstrated:")
    print("  ✓ Wild Card bracket generation (6 games)")
    print("  ✓ Divisional bracket with NFL re-seeding logic")
    print("  ✓ Conference championships")
    print("  ✓ Super Bowl generation")
    print("  ✓ Progressive bracket scheduling\n")

    # Step 1: Get playoff seeding from Week 18 standings
    print_section("STEP 1: CALCULATE PLAYOFF SEEDING")
    print("\nUsing Week 18 regular season standings to determine playoff seeds...\n")

    standings = create_week_18_standings()
    seeder = PlayoffSeeder()
    seeding = seeder.calculate_seeding(standings, season=2024, week=18)

    print(f"{Colors.GREEN}Playoff Teams:{Colors.RESET}")
    print(f"  AFC: Chiefs (#1), Bills (#2), Ravens (#3), Texans (#4), Chargers (#5), Dolphins (#6), Steelers (#7)")
    print(f"  NFC: 49ers (#1), Eagles (#2), Lions (#3), Falcons (#4), Cowboys (#5), Vikings (#6), Rams (#7)")

    input(f"\n{Colors.BOLD}Press Enter to generate Wild Card bracket...{Colors.RESET}")

    # Step 2: Generate Wild Card Bracket
    print_section("STEP 2: GENERATE WILD CARD BRACKET")

    playoff_manager = PlayoffManager()
    wild_card_start_date = Date(2025, 1, 11)  # Saturday, January 11, 2025

    wild_card_bracket = playoff_manager.generate_wild_card_bracket(
        seeding=seeding,
        start_date=wild_card_start_date,
        season=2024
    )

    display_wild_card_bracket(wild_card_bracket, seeding)

    input(f"\n{Colors.BOLD}Press Enter to simulate Wild Card results and generate Divisional bracket...{Colors.RESET}")

    # Step 3: Simulate Wild Card Results
    print_section("STEP 3: WILD CARD RESULTS & DIVISIONAL BRACKET")

    wild_card_results = create_fake_wild_card_results(seeding)
    display_wild_card_results(wild_card_results)

    print(f"\n{Colors.CYAN}Generating Divisional Round bracket with re-seeding...{Colors.RESET}\n")

    divisional_start_date = Date(2025, 1, 18)  # Saturday, January 18, 2025

    divisional_bracket = playoff_manager.generate_divisional_bracket(
        wild_card_results=wild_card_results,
        original_seeding=seeding,
        start_date=divisional_start_date,
        season=2024
    )

    display_divisional_bracket(divisional_bracket, seeding)

    print(f"\n{Colors.YELLOW}Re-Seeding Explanation:{Colors.RESET}")
    print("  • AFC: #1 Chiefs play #5 Dolphins (LOWEST remaining seed)")
    print("  • AFC: #2 Ravens play #3 Bills (other two winners)")
    print("  • NFC: #1 49ers play #4 Falcons (LOWEST remaining seed)")
    print("  • NFC: #2 Eagles play #3 Lions (other two winners)")

    input(f"\n{Colors.BOLD}Press Enter to simulate Divisional results and generate Conference Championships...{Colors.RESET}")

    # Step 4: Simulate Divisional Results
    print_section("STEP 4: DIVISIONAL RESULTS & CONFERENCE CHAMPIONSHIPS")

    divisional_results = create_fake_divisional_results()
    display_divisional_results(divisional_results)

    print(f"\n{Colors.CYAN}Generating Conference Championship bracket...{Colors.RESET}\n")

    conference_start_date = Date(2025, 1, 26)  # Sunday, January 26, 2025

    conference_bracket = playoff_manager.generate_conference_championship_bracket(
        divisional_results=divisional_results,
        start_date=conference_start_date,
        season=2024
    )

    display_conference_championship_bracket(conference_bracket)

    input(f"\n{Colors.BOLD}Press Enter to simulate Conference Championship results and generate Super Bowl...{Colors.RESET}")

    # Step 5: Simulate Conference Championship Results
    print_section("STEP 5: CONFERENCE CHAMPIONSHIP RESULTS & SUPER BOWL")

    conference_results = create_fake_conference_championship_results()
    display_conference_championship_results(conference_results)

    print(f"\n{Colors.CYAN}Generating Super Bowl bracket...{Colors.RESET}\n")

    super_bowl_date = Date(2025, 2, 9)  # Sunday, February 9, 2025

    super_bowl_bracket = playoff_manager.generate_super_bowl_bracket(
        conference_results=conference_results,
        start_date=super_bowl_date,
        season=2024
    )

    display_super_bowl_bracket(super_bowl_bracket)

    # Summary
    print(f"\n{Colors.BOLD}{'='*100}{Colors.RESET}")
    print(f"{Colors.GREEN}{Colors.BOLD}{'PLAYOFF BRACKET PROGRESSION COMPLETE!'.center(100)}{Colors.RESET}")
    print(f"{Colors.BOLD}{'='*100}{Colors.RESET}")

    print(f"\n{Colors.YELLOW}Key Takeaways:{Colors.RESET}")
    print("  ✓ PlayoffManager generates brackets using pure business logic")
    print("  ✓ Re-seeding ensures #1 seed plays lowest remaining seed (competitive advantage)")
    print("  ✓ Bracket progression is dynamic based on game results")
    print("  ✓ PlayoffScheduler (not shown) would convert brackets to GameEvent objects")
    print("  ✓ System supports full playoff simulation from Wild Card to Super Bowl")

    print(f"\n{Colors.CYAN}The playoff system is ready for integration with your season simulation!{Colors.RESET}\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}⚠  Demo interrupted by user{Colors.RESET}")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n{Colors.RED}❌ Error: {e}{Colors.RESET}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
