#!/usr/bin/env python3
"""
Phase 4 Comprehensive Demonstration

Complete NFL game simulation with full statistics API access.
Demonstrates all Phase 4 features and API methods.
"""

from src.game_management.full_game_simulator import FullGameSimulator
from src.constants.team_ids import TeamIDs
import time
import json
import random


def get_random_team_matchups():
    """Get 3 random team matchups from the complete NFL database"""
    # Get all available team IDs from our complete database (all 32 teams)
    all_teams = [
        TeamIDs.BUFFALO_BILLS, TeamIDs.MIAMI_DOLPHINS, TeamIDs.NEW_ENGLAND_PATRIOTS, TeamIDs.NEW_YORK_JETS,
        TeamIDs.BALTIMORE_RAVENS, TeamIDs.CINCINNATI_BENGALS, TeamIDs.CLEVELAND_BROWNS, TeamIDs.PITTSBURGH_STEELERS,
        TeamIDs.HOUSTON_TEXANS, TeamIDs.INDIANAPOLIS_COLTS, TeamIDs.JACKSONVILLE_JAGUARS, TeamIDs.TENNESSEE_TITANS,
        TeamIDs.DENVER_BRONCOS, TeamIDs.KANSAS_CITY_CHIEFS, TeamIDs.LAS_VEGAS_RAIDERS, TeamIDs.LOS_ANGELES_CHARGERS,
        TeamIDs.CHICAGO_BEARS, TeamIDs.DETROIT_LIONS, TeamIDs.GREEN_BAY_PACKERS, TeamIDs.MINNESOTA_VIKINGS,
        TeamIDs.DALLAS_COWBOYS, TeamIDs.NEW_YORK_GIANTS, TeamIDs.PHILADELPHIA_EAGLES, TeamIDs.WASHINGTON_COMMANDERS,
        TeamIDs.ATLANTA_FALCONS, TeamIDs.CAROLINA_PANTHERS, TeamIDs.NEW_ORLEANS_SAINTS, TeamIDs.TAMPA_BAY_BUCCANEERS,
        TeamIDs.ARIZONA_CARDINALS, TeamIDs.LOS_ANGELES_RAMS, TeamIDs.SAN_FRANCISCO_49ERS, TeamIDs.SEATTLE_SEAHAWKS
    ]
    
    # Shuffle teams and create 3 random matchups
    random.shuffle(all_teams)
    matchups = []
    for i in range(0, 6, 2):  # Take pairs: (0,1), (2,3), (4,5)
        away_team = all_teams[i]
        home_team = all_teams[i + 1]
        matchups.append((away_team, home_team))
    
    return matchups


def get_team_name(team_id):
    """Get team name from team ID"""
    team_names = {
        TeamIDs.BUFFALO_BILLS: "Buffalo Bills",
        TeamIDs.MIAMI_DOLPHINS: "Miami Dolphins", 
        TeamIDs.NEW_ENGLAND_PATRIOTS: "New England Patriots",
        TeamIDs.NEW_YORK_JETS: "New York Jets",
        TeamIDs.BALTIMORE_RAVENS: "Baltimore Ravens",
        TeamIDs.CINCINNATI_BENGALS: "Cincinnati Bengals",
        TeamIDs.CLEVELAND_BROWNS: "Cleveland Browns",
        TeamIDs.PITTSBURGH_STEELERS: "Pittsburgh Steelers",
        TeamIDs.HOUSTON_TEXANS: "Houston Texans",
        TeamIDs.INDIANAPOLIS_COLTS: "Indianapolis Colts",
        TeamIDs.JACKSONVILLE_JAGUARS: "Jacksonville Jaguars",
        TeamIDs.TENNESSEE_TITANS: "Tennessee Titans",
        TeamIDs.DENVER_BRONCOS: "Denver Broncos",
        TeamIDs.KANSAS_CITY_CHIEFS: "Kansas City Chiefs",
        TeamIDs.LAS_VEGAS_RAIDERS: "Las Vegas Raiders",
        TeamIDs.LOS_ANGELES_CHARGERS: "Los Angeles Chargers",
        TeamIDs.CHICAGO_BEARS: "Chicago Bears",
        TeamIDs.DETROIT_LIONS: "Detroit Lions",
        TeamIDs.GREEN_BAY_PACKERS: "Green Bay Packers",
        TeamIDs.MINNESOTA_VIKINGS: "Minnesota Vikings",
        TeamIDs.DALLAS_COWBOYS: "Dallas Cowboys",
        TeamIDs.NEW_YORK_GIANTS: "New York Giants",
        TeamIDs.PHILADELPHIA_EAGLES: "Philadelphia Eagles",
        TeamIDs.WASHINGTON_COMMANDERS: "Washington Commanders",
        TeamIDs.ATLANTA_FALCONS: "Atlanta Falcons",
        TeamIDs.CAROLINA_PANTHERS: "Carolina Panthers",
        TeamIDs.NEW_ORLEANS_SAINTS: "New Orleans Saints",
        TeamIDs.TAMPA_BAY_BUCCANEERS: "Tampa Bay Buccaneers",
        TeamIDs.ARIZONA_CARDINALS: "Arizona Cardinals",
        TeamIDs.LOS_ANGELES_RAMS: "Los Angeles Rams",
        TeamIDs.SAN_FRANCISCO_49ERS: "San Francisco 49ers",
        TeamIDs.SEATTLE_SEAHAWKS: "Seattle Seahawks"
    }
    return team_names.get(team_id, f"Team {team_id}")


def simulate_single_game(game_num, away_team_id, home_team_id):
    """Simulate a single game and return results"""
    away_name = get_team_name(away_team_id)
    home_name = get_team_name(home_team_id)
    
    print(f"\n🏈 GAME {game_num}: {away_name} @ {home_name}")
    print("-" * 50)
    
    # Create simulator
    simulator = FullGameSimulator(away_team_id=away_team_id, home_team_id=home_team_id)
    
    # Run simulation
    start_time = time.time()
    game_result = simulator.simulate_game()
    end_time = time.time()
    
    # Get results
    final_score = simulator.get_final_score()
    team_stats = simulator.get_team_stats()
    
    # Get scores by team name
    scores = final_score.get('scores', {})
    away_score = 0
    home_score = 0
    
    # Find scores by matching team names
    for team_name, score in scores.items():
        if away_name.lower() in team_name.lower():
            away_score = score
        elif home_name.lower() in team_name.lower():
            home_score = score
    
    # Display results
    print(f"📊 Final Score: {away_name} {away_score} - {home_score} {home_name}")
    print(f"🏆 Winner: {final_score.get('winner', 'Tie Game')}")
    print(f"⏱️  Simulation Time: {end_time - start_time:.2f} seconds")
    print(f"🏃 Total Plays: {final_score.get('total_plays', 0)}")
    
    # Show key team stats
    for team_name, stats in team_stats.items():
        total_yards = stats.get('total_yards', 0)
        touchdowns = stats.get('touchdowns', 0)
        print(f"   {team_name}: {total_yards} yards, {touchdowns} TDs")
    
    return {
        'game_number': game_num,
        'away_team': away_name,
        'home_team': home_name,
        'away_score': away_score,
        'home_score': home_score,
        'winner': final_score.get('winner', 'Tie Game'),
        'total_plays': final_score.get('total_plays', 0),
        'simulation_time': end_time - start_time,
        'simulator': simulator
    }


def main():
    """Demonstrate complete Phase 4 functionality with 3 random games"""
    print("🏈 PHASE 4: COMPLETE NFL SIMULATION - 3 RANDOM GAMES")
    print("=" * 60)
    
    # Step 1: Generate Random Matchups
    print("\n📋 Step 1: Generating Random NFL Matchups")
    print("   Using complete 32-team NFL database with current 2024-2025 rosters")
    matchups = get_random_team_matchups()
    
    print(f"\n🎲 Today's Random Games:")
    for i, (away_team, home_team) in enumerate(matchups, 1):
        away_name = get_team_name(away_team)
        home_name = get_team_name(home_team)
        print(f"   Game {i}: {away_name} @ {home_name}")
    print()
    
    # Step 2: Simulate All Games
    print("\n🎮 Step 2: Simulating All Games")
    game_results = []
    total_start_time = time.time()
    
    for i, (away_team, home_team) in enumerate(matchups, 1):
        result = simulate_single_game(i, away_team, home_team)
        game_results.append(result)
    
    total_end_time = time.time()
    
    # Step 3: Overall Summary
    print(f"\n📊 Step 3: Games Summary")
    print("=" * 60)
    
    total_simulation_time = total_end_time - total_start_time
    total_plays = sum(result['total_plays'] for result in game_results)
    
    print(f"🏈 Games Completed: {len(game_results)}")
    print(f"⏱️  Total Simulation Time: {total_simulation_time:.2f} seconds")
    print(f"🏃 Total Plays Across All Games: {total_plays}")
    print(f"⚡ Average Plays per Second: {total_plays / total_simulation_time:.1f}")
    
    print(f"\n🏆 Game Results:")
    for result in game_results:
        print(f"   Game {result['game_number']}: {result['away_team']} {result['away_score']} - {result['home_score']} {result['home_team']} ({result['winner']})")
    
    # Step 4: Detailed Analysis of Last Game
    print(f"\n🔍 Step 4: Detailed Analysis - Game {len(game_results)}")
    last_game = game_results[-1]
    simulator = last_game['simulator']
    
    print(f"   Analyzing: {last_game['away_team']} vs {last_game['home_team']}")
    
    # Team Statistics
    team_stats = simulator.get_team_stats()
    print(f"\n📈 Team Statistics:")
    for team_name, stats in team_stats.items():
        print(f"   {team_name}:")
        print(f"     - Total Yards: {stats.get('total_yards', 0)}")
        print(f"     - Passing Yards: {stats.get('passing_yards', 0)}")
        print(f"     - Rushing Yards: {stats.get('rushing_yards', 0)}")
        print(f"     - Touchdowns: {stats.get('touchdowns', 0)}")
        print(f"     - First Downs: {stats.get('first_downs', 0)}")
    
    # Drive Analysis
    drive_summaries = simulator.get_drive_summaries()
    print(f"\n🚗 Drive Analysis ({len(drive_summaries)} total drives):")
    for drive in drive_summaries[:3]:  # Show first 3 drives
        print(f"   Drive #{drive['drive_number']} ({drive['possessing_team']}):")
        print(f"     - Outcome: {drive['drive_outcome']}, Plays: {drive['total_plays']}, Yards: {drive['total_yards']}")
    
    # Performance Metrics
    performance = simulator.get_performance_metrics()
    print(f"\n⚡ Performance Metrics:")
    print(f"   Simulation Duration: {performance['simulation_duration_seconds']:.3f} seconds")
    print(f"   Performance Target Met: {'✅ YES' if performance['performance_target_met'] else '❌ NO'} (< 5.0s)")
    print(f"   Plays per Second: {performance['plays_per_second']:.1f}")
    
    # Step 5: API Summary & Conclusion
    print(f"\n📋 Step 5: Public API Summary")
    api_methods = [
        "simulate_game()", "get_game_result()", "get_final_score()",
        "get_team_stats()", "get_player_stats()", "get_drive_summaries()",
        "get_play_by_play()", "get_penalty_summary()", "get_performance_metrics()"
    ]
    
    print(f"   Available API Methods: {len(api_methods)}")
    for method in api_methods:
        print(f"     - simulator.{method}")
    
    # Conclusion
    print("\n" + "=" * 60)
    print("🎯 PHASE 4 DEMONSTRATION COMPLETE!")
    print(f"   ✅ Complete 32-team NFL database with 2024-2025 rosters (369 players)")
    print(f"   ✅ {len(game_results)} random games simulated with full statistics")
    print(f"   ✅ Multi-level statistics access (game, team, player, drive, play)")
    print(f"   ✅ High performance simulation engine (avg {total_plays / total_simulation_time:.1f} plays/sec)")
    print(f"   ✅ Production-ready public API with complete NFL team coverage")
    print(f"   🎲 Demonstrated randomized matchups from complete league database")
    
    return game_results


if __name__ == "__main__":
    game_results = main()
    
    # Additional interactive features
    print(f"\n🔍 Interactive Features:")
    print(f"   # Example: Any two teams from complete NFL database")
    print(f"   simulator = FullGameSimulator(away_team_id=TeamIDs.KANSAS_CITY_CHIEFS, home_team_id=TeamIDs.BUFFALO_BILLS)")
    print(f"   game_result = simulator.simulate_game()")
    print(f"   final_score = simulator.get_final_score()")
    print(f"   team_stats = simulator.get_team_stats()")
    print(f"   performance = simulator.get_performance_metrics()")
    print(f"   # All 32 NFL teams available with current 2024-2025 rosters!")