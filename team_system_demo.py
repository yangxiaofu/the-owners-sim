#!/usr/bin/env python3
"""
Team System Demo

Demonstrates the new JSON-based team import system with numerical team IDs.
Shows multiple ways to use the system for maximum flexibility.
"""

import sys
sys.path.append('src')

from team_data_loader import TeamDataLoader, get_team_by_id, get_all_teams
from constants.team_ids import TeamIDs, PopularTeams
from personnel_package_manager import TeamRosterGenerator, PersonnelPackageManager


def demo_basic_team_loading():
    """Demonstrate basic team data loading"""
    print("=" * 60)
    print("BASIC TEAM DATA LOADING DEMO")
    print("=" * 60)
    
    # Method 1: Direct numerical IDs
    lions = get_team_by_id(22)
    commanders = get_team_by_id(20)
    
    print("Using direct numerical IDs:")
    print(f"  Team 22: {lions}")
    print(f"  Team 20: {commanders}")
    print()
    
    # Method 2: Using constants for readability
    bills = get_team_by_id(TeamIDs.BUFFALO_BILLS)
    chiefs = get_team_by_id(TeamIDs.KANSAS_CITY_CHIEFS)
    
    print("Using TeamIDs constants:")
    print(f"  Bills: {bills}")
    print(f"  Chiefs: {chiefs}")
    print()
    
    # Method 3: Using popular team aliases
    packers = get_team_by_id(PopularTeams.PACKERS)
    cowboys = get_team_by_id(PopularTeams.COWBOYS)
    
    print("Using PopularTeams aliases:")
    print(f"  Packers: {packers}")
    print(f"  Cowboys: {cowboys}")
    print()


def demo_team_data_features():
    """Demonstrate team data features"""
    print("=" * 60)
    print("TEAM DATA FEATURES DEMO")
    print("=" * 60)
    
    loader = TeamDataLoader()
    
    # Get division teams
    nfc_north = loader.get_teams_by_division('NFC', 'North')
    print("NFC North teams:")
    for team in nfc_north:
        print(f"  {team.team_id}: {team.full_name} ({team.abbreviation})")
        print(f"    Colors: {team.colors}")
    print()
    
    # Search functionality
    chicago_teams = loader.search_teams('chicago')
    print(f"Teams matching 'chicago': {[str(t) for t in chicago_teams]}")
    
    giants_teams = loader.search_teams('giants')
    print(f"Teams matching 'giants': {[str(t) for t in giants_teams]}")
    print()
    
    # Division rivals
    lions = get_team_by_id(22)
    if lions:
        rivals = loader.get_division_rivals(22)
        print(f"Detroit Lions division rivals:")
        for rival in rivals:
            print(f"  {rival}")
    print()


def demo_roster_generation_with_team_data():
    """Demonstrate roster generation with team data integration"""
    print("=" * 60)
    print("ROSTER GENERATION WITH TEAM DATA DEMO")
    print("=" * 60)
    
    # Method 1: Direct numerical IDs
    print("Method 1: Direct numerical IDs")
    lions_roster = TeamRosterGenerator.generate_sample_roster(22)
    commanders_roster = TeamRosterGenerator.generate_sample_roster(20)
    
    print(f"Generated roster for team 22:")
    print(f"  Sample players: {lions_roster[0].name}, {lions_roster[1].name}, {lions_roster[2].name}")
    print()
    
    # Method 2: Using constants
    print("Method 2: Using TeamIDs constants")
    bills_roster = TeamRosterGenerator.generate_sample_roster(TeamIDs.BUFFALO_BILLS)
    chiefs_roster = TeamRosterGenerator.generate_sample_roster(TeamIDs.KANSAS_CITY_CHIEFS)
    
    print(f"Generated roster for Buffalo Bills:")
    print(f"  Sample players: {bills_roster[0].name}, {bills_roster[1].name}, {bills_roster[2].name}")
    print()
    
    # Method 3: Using popular aliases
    print("Method 3: Using PopularTeams aliases")
    packers_roster = TeamRosterGenerator.generate_sample_roster(PopularTeams.PACKERS)
    
    print(f"Generated roster for Green Bay Packers:")
    print(f"  Sample players: {packers_roster[0].name}, {packers_roster[1].name}, {packers_roster[2].name}")
    print()


def demo_error_handling():
    """Demonstrate error handling for invalid team IDs"""
    print("=" * 60)
    print("ERROR HANDLING DEMO")
    print("=" * 60)
    
    # Valid team ID
    valid_team = get_team_by_id(22)
    print(f"Valid team ID 22: {valid_team}")
    
    # Invalid team ID
    invalid_team = get_team_by_id(99)
    print(f"Invalid team ID 99: {invalid_team}")
    
    # Error handling in roster generation
    try:
        invalid_roster = TeamRosterGenerator.generate_sample_roster(99)
        print("This should not print")
    except ValueError as e:
        print(f"Roster generation error: {e}")
    
    print()


def demo_practical_usage():
    """Demonstrate practical usage patterns"""
    print("=" * 60)
    print("PRACTICAL USAGE PATTERNS DEMO")
    print("=" * 60)
    
    # Pattern 1: Random matchup
    loader = TeamDataLoader()
    home_team, away_team = loader.get_random_matchup()
    
    print(f"Random matchup: {away_team} @ {home_team}")
    
    # Generate rosters for the matchup
    home_roster = TeamRosterGenerator.generate_sample_roster(home_team.team_id)
    away_roster = TeamRosterGenerator.generate_sample_roster(away_team.team_id)
    
    print(f"Home roster size: {len(home_roster)} players")
    print(f"Away roster size: {len(away_roster)} players")
    print()
    
    # Pattern 2: Division matchup
    nfc_north_teams = loader.get_teams_by_division('NFC', 'North')
    
    print("NFC North division matchups possible:")
    for i, team1 in enumerate(nfc_north_teams):
        for team2 in nfc_north_teams[i+1:]:
            print(f"  {team1.abbreviation} vs {team2.abbreviation}")
    print()
    
    # Pattern 3: Conference championship
    afc_teams = loader.get_teams_by_conference('AFC')
    nfc_teams = loader.get_teams_by_conference('NFC')
    
    print(f"AFC has {len(afc_teams)} teams")
    print(f"NFC has {len(nfc_teams)} teams")
    print(f"Total: {len(afc_teams) + len(nfc_teams)} teams")
    print()


def demo_integration_with_personnel_manager():
    """Show integration with PersonnelPackageManager"""
    print("=" * 60)
    print("PERSONNEL MANAGER INTEGRATION DEMO")
    print("=" * 60)
    
    # Create team rosters using new system
    lions_roster = TeamRosterGenerator.generate_sample_roster(TeamIDs.DETROIT_LIONS)
    commanders_roster = TeamRosterGenerator.generate_sample_roster(TeamIDs.WASHINGTON_COMMANDERS)
    
    # Create personnel managers
    lions_personnel = PersonnelPackageManager(lions_roster)
    commanders_personnel = PersonnelPackageManager(commanders_roster)
    
    print(f"Detroit Lions roster: {len(lions_roster)} players")
    print(f"Washington Commanders roster: {len(commanders_roster)} players")
    print()
    
    # Show that player names now include team city
    print("Sample player names with team integration:")
    for i in range(5):
        print(f"  Lions: {lions_roster[i].name}")
        print(f"  Commanders: {commanders_roster[i].name}")
    print()


def main():
    """Run all demonstrations"""
    print("🏈 NFL TEAM SYSTEM INTEGRATION DEMONSTRATION 🏈")
    print("Showcasing JSON-based team import with numerical IDs")
    print()
    
    demo_basic_team_loading()
    demo_team_data_features()
    demo_roster_generation_with_team_data()
    demo_error_handling()
    demo_practical_usage()
    demo_integration_with_personnel_manager()
    
    print("=" * 60)
    print("TEAM SYSTEM DEMONSTRATION COMPLETE")
    print("=" * 60)
    print()
    print("Key Features Demonstrated:")
    print("✅ JSON-based team data loading with all 32 NFL teams")
    print("✅ Numerical team IDs (1-32) for database-friendly usage")
    print("✅ Readable constants (TeamIDs.DETROIT_LIONS) for better code")
    print("✅ Popular team aliases (PopularTeams.LIONS) for convenience")
    print("✅ Rich team metadata (colors, divisions, conferences)")
    print("✅ Advanced search and filtering capabilities")
    print("✅ Integration with existing roster generation system")
    print("✅ Error handling for invalid team IDs")
    print("✅ Team-aware player names in generated rosters")
    print()
    print("The team system is production-ready and replaces hardcoded team names!")


if __name__ == "__main__":
    main()