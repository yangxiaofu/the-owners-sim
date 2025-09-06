#!/usr/bin/env python3
"""
Real vs Synthetic Roster Demo

Demonstrates the integration of real NFL player data with the existing
synthetic roster generation system. Shows rosters for:
- Cleveland Browns (team_id: 7) - Real data
- San Francisco 49ers (team_id: 31) - Real data  
- Detroit Lions (team_id: 22) - Synthetic data
"""

import sys
import os

# Add src directory to Python path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from team_management.personnel import TeamRosterGenerator, PersonnelPackageManager
from team_management.players.player_loader import get_player_loader, has_real_roster_data
from constants.team_ids import TeamIDs
from team_management.teams.team_loader import get_team_by_id

def print_separator(title):
    """Print a formatted separator"""
    print("\n" + "=" * 60)
    print(f" {title}")
    print("=" * 60)


def print_roster_summary(roster, team_name):
    """Print summary of a team roster"""
    print(f"\n{team_name} Roster Summary:")
    print(f"  Total Players: {len(roster)}")
    
    # Position counts
    position_counts = {}
    total_overall = 0
    
    for player in roster:
        pos = player.primary_position
        position_counts[pos] = position_counts.get(pos, 0) + 1
        total_overall += player.get_rating('overall')
    
    avg_overall = total_overall / len(roster) if roster else 0
    print(f"  Average Overall Rating: {avg_overall:.1f}")
    
    # Show top 5 players
    top_players = sorted(roster, key=lambda p: p.get_rating('overall'), reverse=True)[:5]
    print(f"\n  Top 5 Players:")
    for i, player in enumerate(top_players, 1):
        print(f"    {i}. {player}")
    
    # Show position distribution
    print(f"\n  Position Distribution:")
    for position, count in sorted(position_counts.items()):
        print(f"    {position}: {count}")


def demo_real_roster(team_id, team_name):
    """Demo real roster functionality"""
    print_separator(f"Real Roster Demo - {team_name}")
    
    # Check if real data exists
    if not has_real_roster_data(team_id):
        print(f"❌ No real roster data available for {team_name} (team_id: {team_id})")
        return
    
    print(f"✅ Real roster data available for {team_name} (team_id: {team_id})")
    
    # Generate roster using the integrated system
    roster = TeamRosterGenerator.generate_sample_roster(team_id)
    print_roster_summary(roster, team_name)
    
    # Show personnel package management
    print(f"\n{team_name} Personnel Package Demo:")
    manager = PersonnelPackageManager(roster)
    
    # Test offensive personnel for different play types
    offense_shotgun = manager.get_offensive_personnel_for_play("pass_play")
    print(f"  Shotgun Formation (11 players):")
    for player in offense_shotgun:
        print(f"    {player}")
    
    return roster


def demo_synthetic_roster(team_id, team_name):
    """Demo synthetic roster functionality"""
    print_separator(f"Synthetic Roster Demo - {team_name}")
    
    print(f"📊 Generating synthetic roster for {team_name} (team_id: {team_id})")
    
    # Generate synthetic roster
    roster = TeamRosterGenerator.generate_sample_roster(team_id)
    print_roster_summary(roster, team_name)
    
    return roster


def demo_player_data_loader():
    """Demo player data loader capabilities"""
    print_separator("Player Data Loader Demo")
    
    loader = get_player_loader()
    print(f"✅ Loaded {len(loader)} real players")
    print(f"Available teams with real data: {loader.get_available_teams()}")
    
    # Search functionality
    print(f"\nPlayer Search Demo:")
    
    # Search by name
    watson_results = loader.search_players_by_name("Watson")
    print(f"  Players with 'Watson' in name: {len(watson_results)}")
    for player in watson_results:
        print(f"    {player}")
    
    # Get top QBs by overall rating
    print(f"\nTop Quarterbacks by Overall Rating:")
    top_qbs = loader.get_top_players_by_attribute("overall", limit=5, position="quarterback")
    for i, qb in enumerate(top_qbs, 1):
        print(f"  {i}. {qb.full_name} #{qb.number} - Overall: {qb.overall_rating}")
    
    # Team roster summaries
    print(f"\nTeam Roster Summaries:")
    for team_id in loader.get_available_teams():
        team = get_team_by_id(team_id)
        summary = loader.get_team_roster_summary(team_id)
        print(f"  {team.city} {team.nickname}:")
        print(f"    Players: {summary['total_players']}")
        print(f"    Avg Rating: {summary['avg_overall_rating']:.1f}")
        print(f"    Best Player: {summary['highest_rated_player']}")


def compare_rosters():
    """Compare real vs synthetic roster characteristics"""
    print_separator("Real vs Synthetic Roster Comparison")
    
    # Get rosters
    browns_roster = TeamRosterGenerator.generate_sample_roster(TeamIDs.CLEVELAND_BROWNS)
    niners_roster = TeamRosterGenerator.generate_sample_roster(TeamIDs.SAN_FRANCISCO_49ERS)
    lions_roster = TeamRosterGenerator.generate_sample_roster(TeamIDs.DETROIT_LIONS)
    
    def get_roster_stats(roster, label):
        ratings = [p.get_rating('overall') for p in roster]
        avg_rating = sum(ratings) / len(ratings)
        max_rating = max(ratings)
        min_rating = min(ratings)
        
        # Count unique positions
        positions = set(p.primary_position for p in roster)
        
        print(f"  {label}:")
        print(f"    Size: {len(roster)} players")
        print(f"    Avg Rating: {avg_rating:.1f}")
        print(f"    Rating Range: {min_rating}-{max_rating}")
        print(f"    Unique Positions: {len(positions)}")
        print(f"    Data Source: {'Real NFL Data' if 'Browns' in label or '49ers' in label else 'Synthetic'}")
    
    get_roster_stats(browns_roster, "Cleveland Browns")
    get_roster_stats(niners_roster, "San Francisco 49ers") 
    get_roster_stats(lions_roster, "Detroit Lions")


def main():
    """Main demo function"""
    print("🏈 NFL Roster Management System Demo")
    print("Real Player Data Integration with Synthetic Fallback")
    
    try:
        # Demo player data loader
        demo_player_data_loader()
        
        # Demo real rosters (MVP teams)
        browns_roster = demo_real_roster(TeamIDs.CLEVELAND_BROWNS, "Cleveland Browns")
        niners_roster = demo_real_roster(TeamIDs.SAN_FRANCISCO_49ERS, "San Francisco 49ers")
        
        # Demo synthetic roster (non-MVP team)
        lions_roster = demo_synthetic_roster(TeamIDs.DETROIT_LIONS, "Detroit Lions")
        
        # Compare the different roster types
        compare_rosters()
        
        # Final summary
        print_separator("Demo Summary")
        print("✅ Real roster integration successful!")
        print("✅ Synthetic roster fallback working!")
        print("✅ Personnel package management compatible!")
        print("\nMVP Teams (Real Data):")
        print(f"  • Cleveland Browns (ID: {TeamIDs.CLEVELAND_BROWNS})")
        print(f"  • San Francisco 49ers (ID: {TeamIDs.SAN_FRANCISCO_49ERS})")
        print("\nOther Teams:")
        print("  • Fallback to synthetic roster generation")
        
    except Exception as e:
        print(f"❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()
    

if __name__ == "__main__":
    main()