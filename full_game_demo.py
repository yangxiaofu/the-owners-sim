#!/usr/bin/env python3
"""
Full Game Simulator Demo

Demonstration script for running the FullGameSimulator with team initialization.
This is intentionally minimal as components will be added incrementally.
"""

from src.game_management.full_game_simulator import FullGameSimulator
from src.constants.team_ids import TeamIDs


def main():
    """Run the full game simulator demo"""
    print("🏈" * 30)
    print("    NFL FULL GAME SIMULATOR")
    print("🏈" * 30)
    print()
    
    try:
        # Create simulator with Detroit Lions @ Green Bay Packers (classic rivalry)
        print("🚀 Initializing Full Game Simulator...")
        simulator = FullGameSimulator(
            away_team_id=TeamIDs.CLEVELAND_BROWNS,
            home_team_id=TeamIDs.SAN_FRANCISCO_49ERS
        )





        print()
        
        # Display matchup information
        team_info = simulator.get_team_info()
        print("📋 MATCHUP DETAILS")
        print("=" * 50)
        print(f"🏟️  AWAY: {team_info['away_team']['name']}")
        print(f"   📍 {team_info['away_team']['city']}")
        print(f"   🏆 {team_info['away_team']['conference']} {team_info['away_team']['division']}")
        print(f"   🎨 {team_info['away_team']['colors']}")
        print()
        print(f"🏠 HOME: {team_info['home_team']['name']}")
        print(f"   📍 {team_info['home_team']['city']}")
        print(f"   🏆 {team_info['home_team']['conference']} {team_info['home_team']['division']}")
        print(f"   🎨 {team_info['home_team']['colors']}")
        print()
        
        # Show loaded player rosters
        print("👥 ROSTER ANALYSIS")
        print("=" * 50)
        
        # Away team roster analysis
        away_roster = simulator.get_away_roster()
        away_qbs = simulator.get_starting_lineup(simulator.away_team_id, "quarterback")
        away_depth_chart = simulator.get_team_depth_chart(simulator.away_team_id)
        
        print(f"🏈 Away Team Roster: {team_info['away_team']['name']} ({len(away_roster)} players)")
        if away_qbs:
            qb = away_qbs[0]
            print(f"   Starting QB: {qb.name} #{qb.number} ({qb.get_rating('overall')} OVR)")
        
        # Show a few key positions
        key_positions = ['running_back', 'wide_receiver', 'tight_end']
        for pos in key_positions:
            if pos in away_depth_chart and away_depth_chart[pos]:
                player = away_depth_chart[pos][0]  # Top player at position
                print(f"   Top {pos.replace('_', ' ').title()}: {player.name} #{player.number} ({player.get_rating('overall')} OVR)")
        print()
        
        # Home team roster analysis  
        home_roster = simulator.get_home_roster()
        home_qbs = simulator.get_starting_lineup(simulator.home_team_id, "quarterback")
        home_depth_chart = simulator.get_team_depth_chart(simulator.home_team_id)
        
        print(f"🏠 Home Team Roster: {team_info['home_team']['name']} ({len(home_roster)} players)")
        if home_qbs:
            qb = home_qbs[0]
            print(f"   Starting QB: {qb.name} #{qb.number} ({qb.get_rating('overall')} OVR)")
            
        # Show a few key positions
        for pos in key_positions:
            if pos in home_depth_chart and home_depth_chart[pos]:
                player = home_depth_chart[pos][0]  # Top player at position
                print(f"   Top {pos.replace('_', ' ').title()}: {player.name} #{player.number} ({player.get_rating('overall')} OVR)")
        print()
        
        # Show position breakdown
        print("📊 Position Breakdown:")
        print(f"Away Team Positions: {', '.join(sorted(away_depth_chart.keys()))}")
        print(f"Home Team Positions: {', '.join(sorted(home_depth_chart.keys()))}")
        print()
        
        # Show game status (clock and scoreboard)
        print("🕐 GAME STATUS")
        print("=" * 50)
        game_status = simulator.get_game_status()
        print(f"⏰ Game Time: {game_status['time_display']} ({game_status['game_phase'].replace('_', ' ').title()})")
        print(f"📊 Score: {game_status['away_team']} {game_status['away_score']} - {game_status['home_team']} {game_status['home_score']}")
        print(f"🎮 Quarter: {game_status['quarter']} | Halftime: {game_status['is_halftime']}")
        if game_status['is_two_minute_warning']:
            print("🚨 Two-Minute Warning Active")
        print()
        
        # Show coin toss results
        print("🪙 COIN TOSS RESULTS")
        print("=" * 50)
        coin_toss = simulator.get_coin_toss_results()
        current_position = simulator.get_current_field_position()
        possession_team = simulator.get_possession_manager().get_possessing_team()
        
        print(f"🎯 Coin Toss Winner: {coin_toss['winner']}")
        print(f"⚡ Opening Kickoff: {coin_toss['opening_kickoff_team']} kicks off")
        print(f"🏈 Receiving Team: {coin_toss['receiving_team']}")
        print(f"📍 Starting Position: {current_position.yard_line}-yard line ({current_position.field_zone.value.replace('_', ' ').title()})")
        print(f"🎯 Current Possession: {possession_team}")
        print()
        
        # Run the simulation (currently minimal)
        print("🎮 STARTING SIMULATION")
        print("=" * 50)
        simulator.simulate_game()
        print()
        
        print("✨ DEMO COMPLETE")
        print("=" * 50)
        print("The simulator is ready for incremental component additions!")
        print("Next steps: Add game clock, drive management, play calling, etc.")
        
    except Exception as e:
        print(f"❌ Error running demo: {e}")
        raise


if __name__ == "__main__":
    main()