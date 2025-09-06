#!/usr/bin/env python3
"""
Interactive testing interface for TeamStatsAccumulator.

Provides a menu-driven interface to create custom test scenarios,
input various player stats combinations, and examine team-level output.
"""

import sys
import os

# Add src directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from play_engine.simulation.stats import (
    PlayStatsSummary, PlayerStats, TeamStatsAccumulator, TeamStats
)
from typing import List, Dict, Optional


class InteractiveTeamStatsTest:
    """Interactive testing interface for team stats accumulation"""
    
    def __init__(self):
        self.accumulator = TeamStatsAccumulator("interactive_test")
        self.play_count = 0
    
    def display_menu(self):
        """Display main menu options"""
        print("\n" + "="*70)
        print("🏈 TEAM STATS ACCUMULATOR - INTERACTIVE TEST INTERFACE 🏈")
        print("="*70)
        print("1. Add Rushing Play")
        print("2. Add Passing Play")
        print("3. Add Defensive Play")
        print("4. Add Field Goal Attempt")
        print("5. Add Custom Multi-Player Play")
        print("6. View Team Stats")
        print("7. View All Teams Summary") 
        print("8. Run Automated Test Scenarios")
        print("9. Reset Accumulator")
        print("0. Exit")
        print("-"*70)
    
    def get_team_ids(self) -> tuple[int, int]:
        """Get offensive and defensive team IDs from user"""
        while True:
            try:
                off_team = int(input("Enter offensive team ID: "))
                def_team = int(input("Enter defensive team ID: "))
                return off_team, def_team
            except ValueError:
                print("Please enter valid integer team IDs")
    
    def add_rushing_play(self):
        """Add a rushing play with user inputs"""
        print("\n📊 ADD RUSHING PLAY")
        print("-"*30)
        
        off_team, def_team = self.get_team_ids()
        
        try:
            yards = int(input("Enter rushing yards gained: "))
            carries = int(input("Enter number of carries (default 1): ") or "1")
            player_name = input("Enter player name (default 'RB'): ") or "RB"
            touchdowns = int(input("Enter rushing touchdowns (default 0): ") or "0")
        except ValueError:
            print("Invalid input, using defaults")
            yards, carries, touchdowns = 5, 1, 0
            player_name = "RB"
        
        # Create player stats
        rb_stats = PlayerStats(
            player_name=player_name,
            position="RB",
            carries=carries,
            rushing_yards=yards,
            rushing_touchdowns=touchdowns
        )
        
        # Create play summary
        play = PlayStatsSummary(
            play_type="RUN",
            yards_gained=yards,
            time_elapsed=5.0,
            player_stats=[rb_stats]
        )
        
        # Add to accumulator
        self.accumulator.add_play_stats(play, off_team, def_team)
        self.play_count += 1
        
        print(f"✅ Rushing play added: {player_name} {yards} yards, {carries} carries")
        self._show_play_impact(off_team, def_team)
    
    def add_passing_play(self):
        """Add a passing play with user inputs"""
        print("\n📊 ADD PASSING PLAY")
        print("-"*30)
        
        off_team, def_team = self.get_team_ids()
        
        try:
            yards = int(input("Enter passing yards gained: "))
            attempts = int(input("Enter pass attempts (default 1): ") or "1")
            completions = int(input("Enter completions (default 1): ") or "1")
            touchdowns = int(input("Enter passing touchdowns (default 0): ") or "0")
            qb_name = input("Enter QB name (default 'QB'): ") or "QB"
        except ValueError:
            print("Invalid input, using defaults")
            yards, attempts, completions, touchdowns = 10, 1, 1, 0
            qb_name = "QB"
        
        # Create QB stats
        qb_stats = PlayerStats(
            player_name=qb_name,
            position="QB",
            pass_attempts=attempts,
            completions=completions,
            passing_yards=yards,
            passing_tds=touchdowns
        )
        
        # Create play summary
        play = PlayStatsSummary(
            play_type="PASS",
            yards_gained=yards,
            time_elapsed=6.0,
            player_stats=[qb_stats]
        )
        
        # Add to accumulator
        self.accumulator.add_play_stats(play, off_team, def_team)
        self.play_count += 1
        
        print(f"✅ Passing play added: {qb_name} {yards} yards, {completions}/{attempts}")
        self._show_play_impact(off_team, def_team)
    
    def add_defensive_play(self):
        """Add a defensive play with user inputs"""
        print("\n📊 ADD DEFENSIVE PLAY")
        print("-"*30)
        
        off_team, def_team = self.get_team_ids()
        
        try:
            sacks = int(input("Enter sacks (default 0): ") or "0")
            tfl = int(input("Enter tackles for loss (default 0): ") or "0") 
            interceptions = int(input("Enter interceptions (default 0): ") or "0")
            forced_fumbles = int(input("Enter forced fumbles (default 0): ") or "0")
            passes_defended = int(input("Enter passes defended (default 0): ") or "0")
            player_name = input("Enter defender name (default 'DEF'): ") or "DEF"
            yards_lost = int(input("Enter yards lost on play (default 0): ") or "0")
        except ValueError:
            print("Invalid input, using defaults")
            sacks, tfl, interceptions, forced_fumbles, passes_defended = 1, 0, 0, 0, 0
            player_name = "DEF"
            yards_lost = -5
        
        # Create defensive player stats
        def_stats = PlayerStats(
            player_name=player_name,
            position="DE",
            sacks=sacks,
            tackles_for_loss=tfl,
            interceptions=interceptions,
            forced_fumbles=forced_fumbles,
            passes_defended=passes_defended
        )
        
        # Create play summary
        play = PlayStatsSummary(
            play_type="PASS",
            yards_gained=-abs(yards_lost),  # Negative yards for defensive plays
            time_elapsed=5.0,
            player_stats=[def_stats]
        )
        
        # Add to accumulator
        self.accumulator.add_play_stats(play, off_team, def_team)
        self.play_count += 1
        
        print(f"✅ Defensive play added: {player_name} - S:{sacks}, TFL:{tfl}, INT:{interceptions}")
        self._show_play_impact(off_team, def_team)
    
    def add_field_goal_attempt(self):
        """Add a field goal attempt"""
        print("\n📊 ADD FIELD GOAL ATTEMPT")
        print("-"*30)
        
        off_team, def_team = self.get_team_ids()
        
        try:
            made = input("Field goal made? (y/n, default y): ").lower().startswith('y')
            kicker_name = input("Enter kicker name (default 'K'): ") or "K"
        except:
            made = True
            kicker_name = "K"
        
        # Create kicker stats
        kicker_stats = PlayerStats(
            player_name=kicker_name,
            position="K",
            field_goal_attempts=1,
            field_goals_made=1 if made else 0
        )
        
        # Create play summary
        play = PlayStatsSummary(
            play_type="FIELD_GOAL",
            yards_gained=0,  # No net yardage change
            time_elapsed=4.0,
            player_stats=[kicker_stats]
        )
        
        # Add to accumulator
        self.accumulator.add_play_stats(play, off_team, def_team)
        self.play_count += 1
        
        result = "GOOD" if made else "MISSED"
        print(f"✅ Field goal added: {kicker_name} - {result}")
        self._show_play_impact(off_team, def_team)
    
    def add_custom_multi_player_play(self):
        """Add a play with multiple players contributing stats"""
        print("\n📊 ADD CUSTOM MULTI-PLAYER PLAY")
        print("-"*40)
        
        off_team, def_team = self.get_team_ids()
        
        players = []
        total_yards = 0
        
        print("Enter stats for multiple players (press Enter with empty name to finish):")
        
        while True:
            name = input("\nPlayer name (or Enter to finish): ").strip()
            if not name:
                break
            
            try:
                position = input("Position: ") or "MISC"
                rush_yards = int(input("Rushing yards (default 0): ") or "0")
                pass_attempts = int(input("Pass attempts (default 0): ") or "0")
                completions = int(input("Completions (default 0): ") or "0")
                pass_yards = int(input("Passing yards (default 0): ") or "0")
                sacks = int(input("Sacks (default 0): ") or "0")
                tackles = int(input("Tackles for loss (default 0): ") or "0")
                
                player = PlayerStats(
                    player_name=name,
                    position=position,
                    rushing_yards=rush_yards,
                    pass_attempts=pass_attempts,
                    completions=completions,
                    passing_yards=pass_yards,
                    sacks=sacks,
                    tackles_for_loss=tackles
                )
                
                players.append(player)
                total_yards += rush_yards + pass_yards
                
                print(f"Added {name} ({position})")
                
            except ValueError:
                print("Invalid input, skipping player")
        
        if not players:
            print("No players added, cancelling play")
            return
        
        # Get total yards for the play
        try:
            play_yards = int(input(f"\nTotal play yards (calculated: {total_yards}): ") or str(total_yards))
        except ValueError:
            play_yards = total_yards
        
        # Create play summary
        play = PlayStatsSummary(
            play_type="CUSTOM",
            yards_gained=play_yards,
            time_elapsed=6.0,
            player_stats=players
        )
        
        # Add to accumulator
        self.accumulator.add_play_stats(play, off_team, def_team)
        self.play_count += 1
        
        print(f"✅ Custom multi-player play added: {len(players)} players, {play_yards} yards")
        self._show_play_impact(off_team, def_team)
    
    def view_team_stats(self):
        """View stats for a specific team"""
        print("\n📈 VIEW TEAM STATS")
        print("-"*25)
        
        try:
            team_id = int(input("Enter team ID to view: "))
        except ValueError:
            print("Invalid team ID")
            return
        
        team_stats = self.accumulator.get_team_stats(team_id)
        if not team_stats:
            print(f"No stats found for team {team_id}")
            return
        
        print(f"\n🏈 TEAM {team_id} STATISTICS")
        print("="*40)
        
        # Offensive stats
        off_stats = team_stats.get_total_offensive_stats()
        if off_stats:
            print("OFFENSIVE STATS:")
            for stat, value in off_stats.items():
                print(f"  {stat}: {value}")
        else:
            print("OFFENSIVE STATS: None")
        
        # Defensive stats  
        def_stats = team_stats.get_total_defensive_stats()
        if def_stats:
            print("\nDEFENSIVE STATS:")
            for stat, value in def_stats.items():
                print(f"  {stat}: {value}")
        else:
            print("\nDEFENSIVE STATS: None")
        
        # Special teams and penalties
        special_stats = {}
        if team_stats.field_goals_attempted > 0:
            special_stats['field_goals_attempted'] = team_stats.field_goals_attempted
            special_stats['field_goals_made'] = team_stats.field_goals_made
        if team_stats.penalties > 0:
            special_stats['penalties'] = team_stats.penalties
            special_stats['penalty_yards'] = team_stats.penalty_yards
        
        if special_stats:
            print("\nSPECIAL TEAMS & PENALTIES:")
            for stat, value in special_stats.items():
                print(f"  {stat}: {value}")
    
    def view_all_teams_summary(self):
        """View summary of all teams with stats"""
        print("\n📊 ALL TEAMS SUMMARY")
        print("="*50)
        
        teams = self.accumulator.get_teams_with_stats()
        if not teams:
            print("No teams have recorded stats yet")
            return
        
        print(f"Teams with stats: {len(teams)}")
        print(f"Total plays processed: {self.accumulator.get_plays_processed()}")
        print()
        
        for team in sorted(teams, key=lambda t: t.team_id):
            print(f"TEAM {team.team_id}:")
            
            # Show key offensive stats
            off_highlights = []
            if team.total_yards > 0:
                off_highlights.append(f"Total Yds: {team.total_yards}")
            if team.rushing_yards > 0:
                off_highlights.append(f"Rush Yds: {team.rushing_yards}")  
            if team.passing_yards > 0:
                off_highlights.append(f"Pass Yds: {team.passing_yards}")
            if team.touchdowns > 0:
                off_highlights.append(f"TDs: {team.touchdowns}")
                
            if off_highlights:
                print(f"  Offense: {', '.join(off_highlights)}")
            
            # Show key defensive stats
            def_highlights = []
            if team.sacks > 0:
                def_highlights.append(f"Sacks: {team.sacks}")
            if team.interceptions > 0:
                def_highlights.append(f"INTs: {team.interceptions}")
            if team.tackles_for_loss > 0:
                def_highlights.append(f"TFL: {team.tackles_for_loss}")
                
            if def_highlights:
                print(f"  Defense: {', '.join(def_highlights)}")
            
            # Show other stats
            other = []
            if team.field_goals_made > 0:
                other.append(f"FGs: {team.field_goals_made}/{team.field_goals_attempted}")
            if team.penalties > 0:
                other.append(f"Penalties: {team.penalties} for {team.penalty_yards} yds")
                
            if other:
                print(f"  Other: {', '.join(other)}")
            print()
    
    def run_automated_scenarios(self):
        """Run some automated test scenarios"""
        print("\n🤖 RUNNING AUTOMATED TEST SCENARIOS")
        print("="*50)
        
        # Save current state
        original_accumulator = self.accumulator
        original_count = self.play_count
        
        # Create fresh accumulator for testing
        test_accumulator = TeamStatsAccumulator("automated_test")
        self.accumulator = test_accumulator
        
        scenarios = [
            ("High-scoring passing game", self._scenario_passing_game),
            ("Defensive domination", self._scenario_defensive_game),
            ("Special teams showcase", self._scenario_special_teams),
            ("Mixed offensive attack", self._scenario_mixed_offense)
        ]
        
        for scenario_name, scenario_func in scenarios:
            print(f"\n🎬 {scenario_name}")
            print("-" * len(scenario_name))
            scenario_func()
        
        print(f"\n📋 Automated scenarios complete")
        self.view_all_teams_summary()
        
        # Restore original state
        self.accumulator = original_accumulator
        self.play_count = original_count
        print("\n↩️  Restored to previous state")
    
    def _scenario_passing_game(self):
        """Simulate a high-scoring passing game"""
        plays = [
            # Team 50 passing attack
            ({"passing_yards": 25, "pass_attempts": 1, "completions": 1, "passing_tds": 1}, 25),
            ({"passing_yards": 18, "pass_attempts": 1, "completions": 1}, 18),
            ({"passing_yards": 12, "pass_attempts": 1, "completions": 1}, 12),
            # Team 51 response
            ({"passing_yards": 22, "pass_attempts": 1, "completions": 1}, 22),
            ({"passing_yards": 15, "pass_attempts": 1, "completions": 1, "passing_tds": 1}, 15)
        ]
        
        teams = [(50, 51), (50, 51), (50, 51), (51, 50), (51, 50)]
        
        for i, (stats, yards) in enumerate(plays):
            off_team, def_team = teams[i]
            qb = PlayerStats(player_name="QB", player_number=12, position="QB", **stats)
            play = PlayStatsSummary("PASS", yards, 5.0, [qb])
            self.accumulator.add_play_stats(play, off_team, def_team)
        
        print("5 passing plays added - Teams 50 and 51")
    
    def _scenario_defensive_game(self):
        """Simulate a defensive battle"""
        # Team 60 defense dominates Team 61 offense
        def_plays = [
            {"sacks": 2, "tackles_for_loss": 1},
            {"interceptions": 1, "passes_defended": 2},
            {"forced_fumbles": 1, "tackles_for_loss": 1},
            {"sacks": 1, "passes_defended": 1}
        ]
        
        for i, stats in enumerate(def_plays):
            defender = PlayerStats(player_name=f"DEF{i+1}", player_number=50+i, position="LB", **stats)
            play = PlayStatsSummary("DEF", -3, 4.0, [defender])
            self.accumulator.add_play_stats(play, 61, 60)  # Team 60 defense vs Team 61 offense
        
        print("4 defensive plays added - Team 60 defense dominates")
    
    def _scenario_special_teams(self):
        """Simulate special teams plays"""
        # Field goals and extra points
        kicker_plays = [
            (1, 1),  # Made FG
            (1, 0),  # Missed FG
            (1, 1),  # Made FG
            (1, 1)   # Made FG
        ]
        
        for i, (attempts, made) in enumerate(kicker_plays):
            kicker = PlayerStats(
                player_name="K", player_number=3, position="K",
                field_goal_attempts=attempts,
                field_goals_made=made
            )
            play = PlayStatsSummary("FIELD_GOAL", 0, 3.0, [kicker])
            team_id = 70 + (i % 2)  # Alternate between teams 70 and 71
            self.accumulator.add_play_stats(play, team_id, team_id + 10)
        
        print("4 field goal attempts added - Teams 70 and 71")
    
    def _scenario_mixed_offense(self):
        """Simulate a balanced offensive attack"""
        mixed_plays = [
            # Running plays
            ({"rushing_yards": 8, "carries": 1}, 8, "RUN"),
            ({"rushing_yards": 15, "carries": 1, "rushing_touchdowns": 1}, 15, "RUN"),
            # Passing plays  
            ({"passing_yards": 20, "pass_attempts": 1, "completions": 1}, 20, "PASS"),
            ({"passing_yards": 35, "pass_attempts": 1, "completions": 1, "passing_tds": 1}, 35, "PASS")
        ]
        
        for i, (stats, yards, play_type) in enumerate(mixed_plays):
            position = "RB" if play_type == "RUN" else "QB"
            number = 28 if position == "RB" else 12
            player = PlayerStats(player_name=position, player_number=number, position=position, **stats)
            play = PlayStatsSummary(play_type, yards, 5.0, [player])
            self.accumulator.add_play_stats(play, 80, 81)
        
        print("4 mixed offensive plays added - Team 80 offense")
    
    def reset_accumulator(self):
        """Reset the accumulator to start fresh"""
        self.accumulator.reset()
        self.play_count = 0
        print("✅ Accumulator reset - all data cleared")
    
    def _show_play_impact(self, off_team: int, def_team: int):
        """Show the impact of the last play on both teams"""
        print(f"\n📊 Play Impact:")
        
        off_stats = self.accumulator.get_team_stats(off_team)
        def_stats = self.accumulator.get_team_stats(def_team)
        
        if off_stats:
            off_highlights = off_stats.get_total_offensive_stats()
            if off_highlights:
                print(f"Team {off_team} offense: {off_highlights}")
        
        if def_stats:
            def_highlights = def_stats.get_total_defensive_stats()
            if def_highlights:
                print(f"Team {def_team} defense: {def_highlights}")
        
        print(f"Total plays processed: {self.accumulator.get_plays_processed()}")
    
    def run(self):
        """Main interactive loop"""
        print("Welcome to the Team Stats Accumulator Interactive Test!")
        
        while True:
            self.display_menu()
            
            try:
                choice = input("Enter your choice (0-9): ").strip()
                
                if choice == '0':
                    print("👋 Goodbye!")
                    break
                elif choice == '1':
                    self.add_rushing_play()
                elif choice == '2':
                    self.add_passing_play()
                elif choice == '3':
                    self.add_defensive_play()
                elif choice == '4':
                    self.add_field_goal_attempt()
                elif choice == '5':
                    self.add_custom_multi_player_play()
                elif choice == '6':
                    self.view_team_stats()
                elif choice == '7':
                    self.view_all_teams_summary()
                elif choice == '8':
                    self.run_automated_scenarios()
                elif choice == '9':
                    self.reset_accumulator()
                else:
                    print("Invalid choice, please try again")
                    
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")


def main():
    """Run the interactive test interface"""
    tester = InteractiveTeamStatsTest()
    tester.run()


if __name__ == "__main__":
    main()