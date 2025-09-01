#!/usr/bin/env python3
"""
One Game Demo - Complete Game Simulation with Team and Player Stats

Simulates a full game between two teams and displays comprehensive statistics:
- Game summary and final score
- Team-level statistics (offense, defense, special teams)
- Individual player statistics (passing, rushing, receiving, defense)
- Advanced analytics from the enhanced tracking system
"""

import sys
import os
import json
from typing import Dict, Any, Optional

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.game_engine.core.game_orchestrator import SimpleGameEngine, GameResult
from src.game_engine.data.loaders.team_loader import TeamLoader
from src.game_engine.data.loaders.player_loader import PlayerLoader

class OneGameDemo:
    """Comprehensive game simulation demo with detailed statistics"""
    
    def __init__(self):
        """Initialize the demo with game engine and data loaders"""
        print("🏈 Initializing One Game Demo...")
        
        # Initialize game engine
        self.game_engine = SimpleGameEngine(data_source="json")
        
        # Initialize data loaders for statistics
        self.team_loader = TeamLoader("json")
        self.player_loader = PlayerLoader("json")
        
        print("✅ Game engine and data loaders initialized")
    
    def run_demo(self, home_team_id: int = 1, away_team_id: int = 2, show_detailed_stats: bool = True):
        """
        Run a complete game simulation and display all statistics
        
        Args:
            home_team_id: ID of the home team
            away_team_id: ID of the away team  
            show_detailed_stats: Whether to show detailed player stats
        """
        print("\n" + "=" * 80)
        print("🏈 ONE GAME SIMULATION DEMO")
        print("=" * 80)
        
        # Load team information
        home_team = self.team_loader.get_by_id(home_team_id)
        away_team = self.team_loader.get_by_id(away_team_id)
        
        if not home_team or not away_team:
            print("❌ Error: Could not load team data")
            print(f"   Home team (ID {home_team_id}): {'Found' if home_team else 'Not found'}")
            print(f"   Away team (ID {away_team_id}): {'Found' if away_team else 'Not found'}")
            return
        
        print(f"🏠 Home Team: {home_team.city} {home_team.name} (Overall: {home_team.ratings.get('overall_rating', 'N/A')})")
        print(f"✈️  Away Team: {away_team.city} {away_team.name} (Overall: {away_team.ratings.get('overall_rating', 'N/A')})")
        print(f"🎮 Simulating game...")
        
        # Simulate the game
        try:
            game_result = self.game_engine.simulate_game(home_team_id, away_team_id)
            print("✅ Game simulation completed!")
            
        except Exception as e:
            print(f"❌ Game simulation failed: {e}")
            import traceback
            traceback.print_exc()
            return
        
        # Display comprehensive results
        self._display_game_summary(game_result, home_team, away_team)
        self._display_team_statistics(game_result, home_team, away_team)
        
        if show_detailed_stats:
            self._display_advanced_analytics(game_result)
            self._display_player_statistics(home_team_id, away_team_id)
        
        print("\n🎉 One Game Demo completed successfully!")
        return game_result
    
    def _display_game_summary(self, result: GameResult, home_team, away_team):
        """Display basic game summary and final score"""
        print("\n" + "=" * 60)
        print("📊 GAME SUMMARY")
        print("=" * 60)
        
        # Final Score
        print(f"🏆 FINAL SCORE:")
        print(f"   {home_team.city} {home_team.name}: {result.home_score}")
        print(f"   {away_team.city} {away_team.name}: {result.away_score}")
        
        # Winner
        if result.winner_id:
            winner_team = home_team if result.winner_id == result.home_team_id else away_team
            print(f"🥇 Winner: {winner_team.city} {winner_team.name}")
        else:
            print("🤝 Game ended in a tie")
        
        # Basic Stats
        print(f"\n📈 BASIC GAME STATS:")
        print(f"   Total Plays: {result.play_count}")
        print(f"   Play Types: {result.play_type_counts}")
        
        # Clock Management
        if result.clock_stats:
            print(f"   Total Clock Used: {result.clock_stats.get('total_clock_used', 0):.1f} seconds")
            print(f"   Average per Play: {result.clock_stats.get('avg_per_play', 0):.1f} seconds")
    
    def _display_team_statistics(self, result: GameResult, home_team, away_team):
        """Display team-level statistics"""
        print("\n" + "=" * 60)
        print("📊 TEAM STATISTICS")
        print("=" * 60)
        
        # Team Ratings Comparison
        print(f"🏠 {home_team.name} Ratings:")
        home_ratings = home_team.ratings
        print(f"   Offense: {home_ratings.get('offense', {})}")
        print(f"   Defense: {home_ratings.get('defense', {})}")
        print(f"   Special Teams: {home_ratings.get('special_teams', 'N/A')}")
        print(f"   Overall: {home_ratings.get('overall_rating', 'N/A')}")
        
        print(f"\n✈️  {away_team.name} Ratings:")
        away_ratings = away_team.ratings  
        print(f"   Offense: {away_ratings.get('offense', {})}")
        print(f"   Defense: {away_ratings.get('defense', {})}")
        print(f"   Special Teams: {away_ratings.get('special_teams', 'N/A')}")
        print(f"   Overall: {away_ratings.get('overall_rating', 'N/A')}")
        
        # Play Calling Analysis
        print(f"\n🎯 PLAY CALLING BREAKDOWN:")
        play_types = result.play_type_counts
        total_plays = sum(play_types.values()) if play_types else result.play_count
        
        if play_types and total_plays > 0:
            for play_type, count in play_types.items():
                percentage = (count / total_plays) * 100
                print(f"   {play_type.capitalize()}: {count} ({percentage:.1f}%)")
        else:
            print("   Play breakdown not available")
        
        # Coaching Philosophy Analysis
        if hasattr(home_team, 'team_philosophy'):
            print(f"\n🧠 COACHING PHILOSOPHY:")
            print(f"   {home_team.name}: {getattr(home_team, 'team_philosophy', 'Unknown')}")
            print(f"   {away_team.name}: {getattr(away_team, 'team_philosophy', 'Unknown')}")
    
    def _display_advanced_analytics(self, result: GameResult):
        """Display advanced analytics if available"""
        print("\n" + "=" * 60)
        print("🔬 ADVANCED ANALYTICS")
        print("=" * 60)
        
        if result.tracking_summary:
            print("✅ Enhanced tracking data available:")
            tracking = result.tracking_summary
            
            # Statistics Summary
            if 'statistics' in tracking:
                stats = tracking['statistics']
                print(f"\n📊 Enhanced Statistics:")
                for key, value in stats.items():
                    if isinstance(value, dict):
                        print(f"   {key.replace('_', ' ').title()}:")
                        for sub_key, sub_value in value.items():
                            print(f"     • {sub_key}: {sub_value}")
                    else:
                        print(f"   {key.replace('_', ' ').title()}: {value}")
            
            # Performance Analysis
            if 'performance' in tracking:
                perf = tracking['performance']
                print(f"\n⚡ Performance Metrics:")
                for key, value in perf.items():
                    print(f"   {key.replace('_', ' ').title()}: {value}")
            
            # Audit Summary
            if 'audit_summary' in tracking:
                audit = tracking['audit_summary']
                print(f"\n📋 Audit Summary:")
                print(f"   Total Entries: {audit.get('total_entries', 0)}")
                print(f"   Error Count: {audit.get('error_count', 0)}")
                print(f"   Event Types: {audit.get('event_types', [])}")
            
            # Contextual Intelligence
            if 'contextual_decisions' in tracking:
                context = tracking['contextual_decisions']
                print(f"\n🧠 Contextual Intelligence:")
                for archetype, decisions in context.items():
                    success_rate = 0
                    if isinstance(decisions, dict) and decisions.get('total_decisions', 0) > 0:
                        success_rate = decisions.get('successful_decisions', 0) / decisions['total_decisions'] * 100
                    print(f"   {archetype}: {success_rate:.1f}% success rate")
        else:
            print("ℹ️  Using basic tracking (advanced analytics not available)")
            print(f"   This usually means the comprehensive tracking system")
            print(f"   dependencies are not installed. Install 'psutil' for full analytics.")
    
    def _display_player_statistics(self, home_team_id: int, away_team_id: int):
        """Display individual player statistics if available"""
        print("\n" + "=" * 60)
        print("👤 PLAYER STATISTICS")
        print("=" * 60)
        
        try:
            # Check if individual player data is supported
            if not self.player_loader.data_source.supports_entity_type("players"):
                print("ℹ️  Individual player statistics not available with current data source")
                print("   Player statistics require database or enhanced data source")
                return
            
            # Load team rosters
            home_roster = self.player_loader.get_team_roster(home_team_id)
            away_roster = self.player_loader.get_team_roster(away_team_id)
            
            if not home_roster and not away_roster:
                print("ℹ️  No player roster data available")
                return
            
            print("📋 TEAM ROSTERS:")
            
            # Home Team Roster
            if home_roster:
                home_team = self.team_loader.get_by_id(home_team_id)
                print(f"\n🏠 {home_team.name} Roster ({len(home_roster)} players):")
                self._display_roster_stats(home_roster)
            
            # Away Team Roster  
            if away_roster:
                away_team = self.team_loader.get_by_id(away_team_id)
                print(f"\n✈️  {away_team.name} Roster ({len(away_roster)} players):")
                self._display_roster_stats(away_roster)
            
            print("\n💡 Note: Individual game statistics tracking requires")
            print("   integration with the play-by-play system for full")
            print("   in-game performance metrics.")
                
        except Exception as e:
            print(f"ℹ️  Player statistics not available: {e}")
            print("   This is normal if using basic team data without player rosters")
    
    def _display_roster_stats(self, roster):
        """Display roster statistics organized by position"""
        if not roster:
            return
            
        # Organize by position
        position_groups = {}
        for player in roster:
            position = getattr(player, 'position', 'Unknown')
            if position not in position_groups:
                position_groups[position] = []
            position_groups[position].append(player)
        
        # Display by position group
        for position, players in sorted(position_groups.items()):
            print(f"   {position}: {len(players)} players")
            
            # Show key players (limit to prevent overwhelming output)
            key_players = players[:3] if len(players) > 3 else players
            for player in key_players:
                name = getattr(player, 'name', 'Unknown')
                overall = getattr(player, 'overall_rating', 'N/A')
                print(f"     • {name} (Overall: {overall})")
            
            if len(players) > 3:
                print(f"     ... and {len(players) - 3} more")
    
    def export_game_data(self, game_result: GameResult, filename: Optional[str] = None):
        """Export game data to JSON file"""
        if not filename:
            filename = f"game_result_{game_result.home_team_id}_vs_{game_result.away_team_id}.json"
        
        # Convert game result to exportable format
        export_data = {
            "game_summary": {
                "home_team_id": game_result.home_team_id,
                "away_team_id": game_result.away_team_id,
                "home_score": game_result.home_score,
                "away_score": game_result.away_score,
                "winner_id": game_result.winner_id,
                "play_count": game_result.play_count
            },
            "play_type_counts": game_result.play_type_counts,
            "clock_stats": game_result.clock_stats,
            "tracking_summary": game_result.tracking_summary
        }
        
        try:
            with open(filename, 'w') as f:
                json.dump(export_data, f, indent=2, default=str)
            print(f"📁 Game data exported to: {filename}")
            return filename
        except Exception as e:
            print(f"❌ Export failed: {e}")
            return None

def main():
    """Main demo function"""
    print("🏈 Welcome to the One Game Demo!")
    print("This demo simulates a complete football game between two teams")
    print("and shows comprehensive team and player statistics.\n")
    
    # Create demo instance
    demo = OneGameDemo()
    
    # Default matchup - you can change these team IDs
    home_team_id = 1  # Change this to any valid team ID
    away_team_id = 2  # Change this to any valid team ID
    
    print(f"🎯 Simulating game between Team {home_team_id} (Home) vs Team {away_team_id} (Away)")
    print("   (You can modify team IDs in the script to test different matchups)\n")
    
    try:
        # Run the demo
        game_result = demo.run_demo(
            home_team_id=home_team_id, 
            away_team_id=away_team_id,
            show_detailed_stats=True
        )
        
        if game_result:
            # Offer to export data
            export_choice = input("\n💾 Would you like to export the game data to JSON? (y/N): ").lower()
            if export_choice in ['y', 'yes']:
                filename = demo.export_game_data(game_result)
                if filename:
                    print(f"✅ Game data saved successfully!")
        
        print("\n" + "=" * 80)
        print("🎉 Demo completed! Key insights:")
        print("• This demonstrates the complete game engine with enhanced tracking")
        print("• Team archetypes and coaching philosophies affect play calling")  
        print("• Advanced analytics show contextual decision-making intelligence")
        print("• Individual player stats require database integration")
        print("=" * 80)
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()