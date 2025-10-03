#!/usr/bin/env python3
"""
Playoff Seeder Demo

Demonstrates real-time playoff seeding calculation at different points in the season.

Scenarios:
1. Week 10: Early playoff picture - divisions still up for grabs
2. Week 15: Late season race - playoff spots getting tight
3. Week 18: Final regular season seeding - bracket set

This shows how the PlayoffSeeder can be used throughout the season to track
the current playoff picture, not just at the end of regular season.

Run: PYTHONPATH=src python demo/playoff_seeder_demo/playoff_seeder_demo.py
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from playoff_system.playoff_seeder import PlayoffSeeder
from constants.team_ids import TeamIDs
from team_management.teams.team_loader import get_team_by_id
from stores.standings_store import EnhancedTeamStanding


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


def display_conference_seeding(conf_seeding, week, verbose=True):
    """Display seeding for a conference."""
    print(f"\n{Colors.BOLD}{Colors.GREEN}{conf_seeding.conference} PLAYOFF SEEDING - WEEK {week}{Colors.RESET}")
    print("─" * 100)

    for seed_obj in conf_seeding.seeds:
        team = get_team_by_id(seed_obj.team_id)

        # Status indicator
        if seed_obj.seed == 1:
            status = f"{Colors.YELLOW}★ BYE{Colors.RESET}"
        elif seed_obj.division_winner:
            status = f"{Colors.GREEN}★{Colors.RESET}"
        else:
            status = f"{Colors.CYAN}WC{Colors.RESET}"

        # Seed color based on position
        seed_color = Colors.GREEN if seed_obj.seed <= 2 else (Colors.CYAN if seed_obj.seed <= 4 else Colors.YELLOW)

        print(f"  {seed_color}{seed_obj.seed}.{Colors.RESET} [{status}] "
              f"{Colors.BOLD}{team.full_name:32}{Colors.RESET} "
              f"{seed_obj.record_string:8} "
              f"({seed_obj.win_percentage:.3f})  "
              f"PF: {seed_obj.points_for:3}  PA: {seed_obj.points_against:3}  "
              f"Diff: {seed_obj.point_differential:+4}")

        if verbose:
            print(f"      {Colors.CYAN}Division: {seed_obj.division_record}  "
                  f"Conference: {seed_obj.conference_record}  "
                  f"{seed_obj.division_name}{Colors.RESET}")

    print()
    print(f"  {Colors.GREEN}✓ Clinched:{Colors.RESET} {len(conf_seeding.clinched_teams)} teams")
    print(f"  {Colors.RED}✗ Eliminated:{Colors.RESET} {len(conf_seeding.eliminated_teams)} teams")


def display_wild_card_matchups(seeding):
    """Display potential wild card matchups."""
    print_section("WILD CARD ROUND MATCHUPS")

    matchups = seeding.get_matchups()

    for conf in ['AFC', 'NFC']:
        print(f"\n{Colors.BOLD}{conf} WILD CARD GAMES:{Colors.RESET}")

        for i, (home_id, away_id) in enumerate(matchups[conf], start=1):
            home_team = get_team_by_id(home_id)
            away_team = get_team_by_id(away_id)
            home_seed = seeding.get_seed(home_id)
            away_seed = seeding.get_seed(away_id)

            print(f"  Game {i}: "
                  f"({away_seed.seed}) {away_team.full_name} @ "
                  f"({home_seed.seed}) {home_team.full_name}")


def create_week_10_standings():
    """
    Create realistic week 10 standings.

    Early season - many teams still in contention, divisions not decided.
    """
    standings = {}

    # AFC EAST: Bills leading, competitive division
    standings[TeamIDs.BUFFALO_BILLS] = EnhancedTeamStanding(
        team_id=TeamIDs.BUFFALO_BILLS, wins=7, losses=2, points_for=245, points_against=180,
        division_wins=2, division_losses=0, conference_wins=5, conference_losses=2
    )
    standings[TeamIDs.MIAMI_DOLPHINS] = EnhancedTeamStanding(
        team_id=TeamIDs.MIAMI_DOLPHINS, wins=6, losses=3, points_for=230, points_against=195,
        division_wins=2, division_losses=1, conference_wins=4, conference_losses=3
    )
    standings[TeamIDs.NEW_YORK_JETS] = EnhancedTeamStanding(
        team_id=TeamIDs.NEW_YORK_JETS, wins=5, losses=4, points_for=210, points_against=215,
        division_wins=1, division_losses=2, conference_wins=4, conference_losses=3
    )
    standings[TeamIDs.NEW_ENGLAND_PATRIOTS] = EnhancedTeamStanding(
        team_id=TeamIDs.NEW_ENGLAND_PATRIOTS, wins=2, losses=7, points_for=165, points_against=260,
        division_wins=0, division_losses=3, conference_wins=2, conference_losses=6
    )

    # AFC NORTH: Ravens and Steelers battling
    standings[TeamIDs.BALTIMORE_RAVENS] = EnhancedTeamStanding(
        team_id=TeamIDs.BALTIMORE_RAVENS, wins=7, losses=2, points_for=255, points_against=190,
        division_wins=3, division_losses=0, conference_wins=6, conference_losses=1
    )
    standings[TeamIDs.PITTSBURGH_STEELERS] = EnhancedTeamStanding(
        team_id=TeamIDs.PITTSBURGH_STEELERS, wins=6, losses=3, points_for=220, points_against=200,
        division_wins=2, division_losses=1, conference_wins=5, conference_losses=2
    )
    standings[TeamIDs.CLEVELAND_BROWNS] = EnhancedTeamStanding(
        team_id=TeamIDs.CLEVELAND_BROWNS, wins=5, losses=4, points_for=200, points_against=210,
        division_wins=1, division_losses=2, conference_wins=4, conference_losses=3
    )
    standings[TeamIDs.CINCINNATI_BENGALS] = EnhancedTeamStanding(
        team_id=TeamIDs.CINCINNATI_BENGALS, wins=4, losses=5, points_for=215, points_against=225,
        division_wins=1, division_losses=2, conference_wins=3, conference_losses=4
    )

    # AFC SOUTH: Texans leading weak division
    standings[TeamIDs.HOUSTON_TEXANS] = EnhancedTeamStanding(
        team_id=TeamIDs.HOUSTON_TEXANS, wins=6, losses=3, points_for=215, points_against=195,
        division_wins=3, division_losses=0, conference_wins=5, conference_losses=2
    )
    standings[TeamIDs.JACKSONVILLE_JAGUARS] = EnhancedTeamStanding(
        team_id=TeamIDs.JACKSONVILLE_JAGUARS, wins=5, losses=4, points_for=205, points_against=210,
        division_wins=2, division_losses=1, conference_wins=4, conference_losses=3
    )
    standings[TeamIDs.INDIANAPOLIS_COLTS] = EnhancedTeamStanding(
        team_id=TeamIDs.INDIANAPOLIS_COLTS, wins=4, losses=5, points_for=190, points_against=215,
        division_wins=1, division_losses=2, conference_wins=3, conference_losses=4
    )
    standings[TeamIDs.TENNESSEE_TITANS] = EnhancedTeamStanding(
        team_id=TeamIDs.TENNESSEE_TITANS, wins=3, losses=6, points_for=175, points_against=230,
        division_wins=1, division_losses=2, conference_wins=2, conference_losses=5
    )

    # AFC WEST: Chiefs dominant, Chargers in wildcard hunt
    standings[TeamIDs.KANSAS_CITY_CHIEFS] = EnhancedTeamStanding(
        team_id=TeamIDs.KANSAS_CITY_CHIEFS, wins=8, losses=1, points_for=270, points_against=175,
        division_wins=3, division_losses=0, conference_wins=6, conference_losses=1
    )
    standings[TeamIDs.LOS_ANGELES_CHARGERS] = EnhancedTeamStanding(
        team_id=TeamIDs.LOS_ANGELES_CHARGERS, wins=6, losses=3, points_for=225, points_against=200,
        division_wins=2, division_losses=1, conference_wins=5, conference_losses=2
    )
    standings[TeamIDs.DENVER_BRONCOS] = EnhancedTeamStanding(
        team_id=TeamIDs.DENVER_BRONCOS, wins=4, losses=5, points_for=195, points_against=220,
        division_wins=1, division_losses=2, conference_wins=3, conference_losses=4
    )
    standings[TeamIDs.LAS_VEGAS_RAIDERS] = EnhancedTeamStanding(
        team_id=TeamIDs.LAS_VEGAS_RAIDERS, wins=3, losses=6, points_for=180, points_against=240,
        division_wins=0, division_losses=3, conference_wins=2, conference_losses=5
    )

    # NFC EAST: Eagles leading, Cowboys close
    standings[TeamIDs.PHILADELPHIA_EAGLES] = EnhancedTeamStanding(
        team_id=TeamIDs.PHILADELPHIA_EAGLES, wins=7, losses=2, points_for=250, points_against=190,
        division_wins=3, division_losses=0, conference_wins=6, conference_losses=1
    )
    standings[TeamIDs.DALLAS_COWBOYS] = EnhancedTeamStanding(
        team_id=TeamIDs.DALLAS_COWBOYS, wins=6, losses=3, points_for=235, points_against=205,
        division_wins=2, division_losses=1, conference_wins=5, conference_losses=2
    )
    standings[TeamIDs.WASHINGTON_COMMANDERS] = EnhancedTeamStanding(
        team_id=TeamIDs.WASHINGTON_COMMANDERS, wins=5, losses=4, points_for=210, points_against=215,
        division_wins=1, division_losses=2, conference_wins=4, conference_losses=3
    )
    standings[TeamIDs.NEW_YORK_GIANTS] = EnhancedTeamStanding(
        team_id=TeamIDs.NEW_YORK_GIANTS, wins=3, losses=6, points_for=175, points_against=235,
        division_wins=0, division_losses=3, conference_wins=2, conference_losses=5
    )

    # NFC NORTH: Lions and Vikings battling
    standings[TeamIDs.DETROIT_LIONS] = EnhancedTeamStanding(
        team_id=TeamIDs.DETROIT_LIONS, wins=7, losses=2, points_for=260, points_against=195,
        division_wins=2, division_losses=1, conference_wins=6, conference_losses=1
    )
    standings[TeamIDs.MINNESOTA_VIKINGS] = EnhancedTeamStanding(
        team_id=TeamIDs.MINNESOTA_VIKINGS, wins=6, losses=3, points_for=240, points_against=210,
        division_wins=2, division_losses=1, conference_wins=5, conference_losses=2
    )
    standings[TeamIDs.GREEN_BAY_PACKERS] = EnhancedTeamStanding(
        team_id=TeamIDs.GREEN_BAY_PACKERS, wins=5, losses=4, points_for=220, points_against=220,
        division_wins=1, division_losses=2, conference_wins=4, conference_losses=3
    )
    standings[TeamIDs.CHICAGO_BEARS] = EnhancedTeamStanding(
        team_id=TeamIDs.CHICAGO_BEARS, wins=3, losses=6, points_for=185, points_against=245,
        division_wins=0, division_losses=3, conference_wins=2, conference_losses=5
    )

    # NFC SOUTH: Falcons narrowly leading
    standings[TeamIDs.ATLANTA_FALCONS] = EnhancedTeamStanding(
        team_id=TeamIDs.ATLANTA_FALCONS, wins=6, losses=3, points_for=220, points_against=200,
        division_wins=3, division_losses=0, conference_wins=5, conference_losses=2
    )
    standings[TeamIDs.NEW_ORLEANS_SAINTS] = EnhancedTeamStanding(
        team_id=TeamIDs.NEW_ORLEANS_SAINTS, wins=5, losses=4, points_for=210, points_against=210,
        division_wins=2, division_losses=1, conference_wins=4, conference_losses=3
    )
    standings[TeamIDs.TAMPA_BAY_BUCCANEERS] = EnhancedTeamStanding(
        team_id=TeamIDs.TAMPA_BAY_BUCCANEERS, wins=4, losses=5, points_for=200, points_against=220,
        division_wins=1, division_losses=2, conference_wins=3, conference_losses=4
    )
    standings[TeamIDs.CAROLINA_PANTHERS] = EnhancedTeamStanding(
        team_id=TeamIDs.CAROLINA_PANTHERS, wins=2, losses=7, points_for=170, points_against=250,
        division_wins=0, division_losses=3, conference_wins=2, conference_losses=6
    )

    # NFC WEST: 49ers dominant, Rams competitive
    standings[TeamIDs.SAN_FRANCISCO_49ERS] = EnhancedTeamStanding(
        team_id=TeamIDs.SAN_FRANCISCO_49ERS, wins=8, losses=1, points_for=275, points_against=180,
        division_wins=3, division_losses=0, conference_wins=7, conference_losses=0
    )
    standings[TeamIDs.LOS_ANGELES_RAMS] = EnhancedTeamStanding(
        team_id=TeamIDs.LOS_ANGELES_RAMS, wins=5, losses=4, points_for=215, points_against=210,
        division_wins=2, division_losses=1, conference_wins=4, conference_losses=3
    )
    standings[TeamIDs.SEATTLE_SEAHAWKS] = EnhancedTeamStanding(
        team_id=TeamIDs.SEATTLE_SEAHAWKS, wins=5, losses=4, points_for=210, points_against=215,
        division_wins=1, division_losses=2, conference_wins=4, conference_losses=3
    )
    standings[TeamIDs.ARIZONA_CARDINALS] = EnhancedTeamStanding(
        team_id=TeamIDs.ARIZONA_CARDINALS, wins=3, losses=6, points_for=185, points_against=235,
        division_wins=0, division_losses=3, conference_wins=2, conference_losses=5
    )

    return standings


def create_week_18_standings():
    """
    Create realistic week 18 final standings.

    End of regular season - playoff bracket set, seeding finalized.
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


def demo_week_10_scenario():
    """Demo: Week 10 early playoff picture."""
    print_header("WEEK 10: EARLY PLAYOFF PICTURE")

    print(f"{Colors.CYAN}📅 Early November - Divisions Still Wide Open{Colors.RESET}")
    print("   Many teams within 1-2 games of playoff position")
    print("   Seeding will shift significantly over next 8 weeks\n")

    # Create realistic week 10 standings
    standings = create_week_10_standings()

    # Calculate seeding
    seeder = PlayoffSeeder()
    seeding = seeder.calculate_seeding(standings, season=2024, week=10)

    # Display results
    display_conference_seeding(seeding.afc, week=10)
    display_conference_seeding(seeding.nfc, week=10)

    print(f"\n{Colors.YELLOW}💡 Week 10 Analysis:{Colors.RESET}")
    print("   • Division races extremely competitive in AFC North, NFC East, NFC North")
    print("   • Wildcard spots up for grabs - 8-10 teams in hunt per conference")
    print("   • Strong teams (Chiefs, 49ers) establishing dominance")
    print("   • Several teams (Dolphins, Chargers, Vikings) in wildcard position")


def demo_week_18_scenario():
    """Demo: Week 18 final seeding."""
    print_header("WEEK 18: FINAL REGULAR SEASON SEEDING")

    print(f"{Colors.GREEN}🏁 Regular Season Complete - Playoff Bracket Set{Colors.RESET}")
    print("   All division winners determined")
    print("   Wildcard teams locked in")
    print("   Seeding official for playoff matchups\n")

    # Create realistic week 18 standings
    standings = create_week_18_standings()

    # Calculate seeding
    seeder = PlayoffSeeder()
    seeding = seeder.calculate_seeding(standings, season=2024, week=18)

    # Display results
    display_conference_seeding(seeding.afc, week=18, verbose=True)
    display_conference_seeding(seeding.nfc, week=18, verbose=True)

    # Display matchups
    display_wild_card_matchups(seeding)

    print(f"\n{Colors.GREEN}🏈 Playoff Bracket Locked In!{Colors.RESET}")
    print("   • #1 seeds (Chiefs, 49ers) earn first-round bye")
    print("   • Wild Card Round features 6 games (3 per conference)")
    print("   • Higher seeds host all playoff games")
    print("   • Road to Super Bowl begins next weekend!")


def main():
    """Main demo execution."""
    print_header("NFL PLAYOFF SEEDER DEMO")
    print(f"\n{Colors.BOLD}This demo shows playoff seeding calculation at different points in the season.{Colors.RESET}")
    print(f"{Colors.CYAN}The PlayoffSeeder can calculate current playoff picture from any week's standings.{Colors.RESET}\n")

    print("Use cases:")
    print("  ✓ Real-time playoff tracking during season (weeks 10-18)")
    print("  ✓ Final seeding at end of regular season")
    print("  ✓ Testing with mock data")
    print("  ✓ Integration with live StandingsStore\n")

    # Run scenarios
    demo_week_10_scenario()

    input(f"\n{Colors.BOLD}Press Enter to see Week 18 final seeding...{Colors.RESET}")

    demo_week_18_scenario()

    print(f"\n{Colors.BOLD}{'='*100}{Colors.RESET}")
    print(f"{Colors.GREEN}{Colors.BOLD}{'Demo Complete!'.center(100)}{Colors.RESET}")
    print(f"{Colors.BOLD}{'='*100}{Colors.RESET}")
    print(f"\n{Colors.CYAN}The PlayoffSeeder is ready to use in your season simulations!{Colors.RESET}\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}⚠️  Demo interrupted by user{Colors.RESET}")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n{Colors.RED}❌ Error: {e}{Colors.RESET}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
