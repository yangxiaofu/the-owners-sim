#!/usr/bin/env python3
"""
Test Script for Run Concepts and Individual Player System

This script tests the new run concept system with individual players
to verify that all components work correctly together.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# Import directly to avoid relative import issues
from src.database.models.players.player import Player, PlayerRole, InjuryStatus
from src.database.models.players.positions import RunningBack, OffensiveLineman, DefensiveLineman, Linebacker
from src.database.generators.mock_generator import MockPlayerGenerator
from src.game_engine.plays.run_concepts import RunConcept, RunConceptLibrary, RunConceptExecutor
import random


class RunConceptTester:
    """Interactive tester for the run concept system"""
    
    def __init__(self):
        print("🏈 Run Concept & Individual Player Test System")
        print("=" * 55)
        
        # Generate team rosters
        self.generator = MockPlayerGenerator()
        self.team_rosters = self._generate_test_rosters()
        
        # Get all run concepts
        self.run_concepts = RunConceptLibrary.get_all_concepts()
        
        print(f"✅ Generated {len(self.team_rosters)} team rosters")
        print(f"✅ Loaded {len(self.run_concepts)} run concepts")
    
    def _generate_test_rosters(self):
        """Generate test team rosters with varying strengths"""
        team_configs = [
            # Team 1 - Balanced team
            {'offense': {'rb_rating': 80, 'ol_rating': 75}, 'defense': {'dl_rating': 78, 'lb_rating': 82}},
            # Team 2 - Power running team  
            {'offense': {'rb_rating': 90, 'ol_rating': 85}, 'defense': {'dl_rating': 85, 'lb_rating': 80}},
            # Team 3 - Speed team
            {'offense': {'rb_rating': 75, 'ol_rating': 70}, 'defense': {'dl_rating': 75, 'lb_rating': 85}},
            # Team 4 - Defensive team
            {'offense': {'rb_rating': 65, 'ol_rating': 68}, 'defense': {'dl_rating': 92, 'lb_rating': 88}}
        ]
        
        rosters = {}
        for i, config in enumerate(team_configs, 1):
            rosters[i] = self.generator.generate_team_roster(team_id=i, team_data=config)
        
        return rosters
    
    def display_team_rosters(self):
        """Display information about all team rosters"""
        print("\n📋 Team Rosters:")
        print("-" * 40)
        
        for team_id, roster in self.team_rosters.items():
            print(f"\nTeam {team_id}:")
            
            # Running backs
            rbs = roster['running_backs']
            starter_rb = next((rb for rb in rbs if rb.role == PlayerRole.STARTER), rbs[0])
            print(f"  RB: {starter_rb.name} (OVR: {starter_rb.overall_rating}, Speed: {starter_rb.speed}, Vision: {starter_rb.vision}, Style: {starter_rb.get_gap_preference()})")
            
            # Offensive line average
            ol_players = roster['offensive_line']
            avg_ol_rating = sum(ol.overall_rating for ol in ol_players) // len(ol_players)
            avg_run_block = sum(ol.run_blocking for ol in ol_players) // len(ol_players)
            print(f"  OL: Avg OVR {avg_ol_rating}, Run Block {avg_run_block}")
            
            # Defensive line average  
            dl_players = roster['defensive_line']
            avg_dl_rating = sum(dl.overall_rating for dl in dl_players) // len(dl_players)
            avg_run_def = sum(dl.run_defense for dl in dl_players) // len(dl_players)
            print(f"  DL: Avg OVR {avg_dl_rating}, Run Def {avg_run_def}")
            
            # Linebackers average
            lb_players = roster['linebackers']
            avg_lb_rating = sum(lb.overall_rating for lb in lb_players) // len(lb_players)
            avg_run_stop = sum(lb.run_stopping_rating for lb in lb_players) // len(lb_players)
            print(f"  LB: Avg OVR {avg_lb_rating}, Run Stop {avg_run_stop}")
    
    def display_run_concepts(self):
        """Display all available run concepts"""
        print("\n🏃 Available Run Concepts:")
        print("-" * 35)
        
        for i, concept in enumerate(self.run_concepts, 1):
            print(f"{i}. {concept.name} ({concept.concept_type.value})")
            print(f"   Target: {concept.target_gap} gap, Blocking: {concept.blocking_scheme}")
            print(f"   RB Technique: {concept.rb_technique}")
            print(f"   Success Factors: {', '.join(concept.success_factors)}")
            if concept.preferred_down:
                print(f"   Best Downs: {concept.preferred_down}")
            print()
    
    def test_single_concept(self, concept_index=None):
        """Test a single run concept execution"""
        if concept_index is None:
            print("\n🎯 Testing Random Run Concept")
            concept = random.choice(self.run_concepts)
        else:
            concept = self.run_concepts[concept_index - 1]
            print(f"\n🎯 Testing {concept.name}")
        
        print("-" * 40)
        
        # Select random teams
        offense_team_id = random.randint(1, 4)
        defense_team_id = random.randint(1, 4)
        while defense_team_id == offense_team_id:
            defense_team_id = random.randint(1, 4)
        
        print(f"Offense: Team {offense_team_id} vs Defense: Team {defense_team_id}")
        
        # Get players
        offense_roster = self.team_rosters[offense_team_id]
        defense_roster = self.team_rosters[defense_team_id]
        
        rb = offense_roster['running_backs'][0]
        ol_players = offense_roster['offensive_line'][:5]
        dl_players = defense_roster['defensive_line'][:4] 
        lb_players = defense_roster['linebackers'][:3]
        
        # Create mock field state
        class MockFieldState:
            def __init__(self):
                self.down = random.randint(1, 3)
                self.yards_to_go = random.randint(1, 15)
                self.field_position = random.randint(15, 85)
            
            def is_goal_line(self):
                return self.field_position >= 90
            
            def is_short_yardage(self):
                return self.yards_to_go <= 3
        
        field_state = MockFieldState()
        
        # Execute the concept
        result = RunConceptExecutor.execute_concept(
            concept, rb, ol_players, dl_players, lb_players, field_state
        )
        
        # Display detailed results
        print(f"\nPlay: {concept.name}")
        print(f"Situation: {field_state.down} & {field_state.yards_to_go} at {field_state.field_position}")
        print(f"RB: {rb.name} (OVR: {rb.overall_rating}, {rb.get_gap_preference()} style)")
        print(f"\n🏈 RESULT: {result['play_description']}")
        print(f"📊 Outcome: {result['outcome']} for {result['yards_gained']} yards")
        print(f"🎯 Target: {result['target_gap']} gap using {result['rb_technique']}")
        
        # Show success factors
        print(f"\n📈 Success Factors:")
        for factor, value in result['success_factors'].items():
            percentage = f"{value*100:.1f}%"
            print(f"  {factor}: {percentage}")
        
        return result
    
    def test_concept_comparison(self):
        """Compare different concepts in the same situation"""
        print("\n⚖️ Concept Comparison Test")
        print("-" * 35)
        
        # Fixed situation
        offense_team_id = 2  # Power team
        defense_team_id = 4  # Defensive team
        
        offense_roster = self.team_rosters[offense_team_id]
        defense_roster = self.team_rosters[defense_team_id]
        
        rb = offense_roster['running_backs'][0]
        ol_players = offense_roster['offensive_line'][:5]
        dl_players = defense_roster['defensive_line'][:4]
        lb_players = defense_roster['linebackers'][:3]
        
        # Fixed field state - short yardage
        class MockFieldState:
            def __init__(self):
                self.down = 3
                self.yards_to_go = 2
                self.field_position = 45
            
            def is_goal_line(self):
                return False
            
            def is_short_yardage(self):
                return True
        
        field_state = MockFieldState()
        
        print(f"Situation: 3rd & 2 at the 45")
        print(f"Power Team vs Elite Defense")
        print(f"RB: {rb.name} ({rb.get_gap_preference()} runner)")
        
        # Test multiple concepts
        concepts_to_test = ['Power O', 'Inside Zone', 'Dive', 'Draw']
        results = []
        
        for concept_name in concepts_to_test:
            concept = next(c for c in self.run_concepts if c.name == concept_name)
            
            # Run multiple times for average
            yards_gained = []
            successes = 0
            
            for _ in range(10):
                result = RunConceptExecutor.execute_concept(
                    concept, rb, ol_players, dl_players, lb_players, field_state
                )
                yards_gained.append(result['yards_gained'])
                if result['yards_gained'] >= 2:  # Success if gets first down
                    successes += 1
            
            avg_yards = sum(yards_gained) / len(yards_gained)
            success_rate = successes / 10
            
            results.append({
                'name': concept_name,
                'avg_yards': avg_yards,
                'success_rate': success_rate,
                'yards_range': f"{min(yards_gained)} to {max(yards_gained)}"
            })
        
        # Display comparison
        print(f"\n📊 Results (10 runs each):")
        results.sort(key=lambda x: x['avg_yards'], reverse=True)
        
        for i, result in enumerate(results, 1):
            success_pct = f"{result['success_rate']*100:.0f}%"
            print(f"{i}. {result['name']}: {result['avg_yards']:.1f} avg yards, {success_pct} success rate")
            print(f"   Range: {result['yards_range']} yards")
    
    def test_player_matchups(self):
        """Test how different player matchups affect results"""
        print("\n👥 Player Matchup Test")
        print("-" * 25)
        
        # Test same concept with different player matchups
        concept = next(c for c in self.run_concepts if c.name == "Inside Zone")
        
        matchups = [
            ("Elite RB vs Weak Defense", 2, 3),
            ("Weak RB vs Elite Defense", 3, 4), 
            ("Elite vs Elite", 2, 4),
            ("Balanced vs Balanced", 1, 1)
        ]
        
        class MockFieldState:
            def __init__(self):
                self.down = 1
                self.yards_to_go = 10
                self.field_position = 30
            
            def is_goal_line(self):
                return False
            
            def is_short_yardage(self):
                return False
        
        field_state = MockFieldState()
        
        for matchup_name, off_team_id, def_team_id in matchups:
            offense_roster = self.team_rosters[off_team_id]
            defense_roster = self.team_rosters[def_team_id]
            
            rb = offense_roster['running_backs'][0]
            ol_players = offense_roster['offensive_line'][:5]
            dl_players = defense_roster['defensive_line'][:4]
            lb_players = defense_roster['linebackers'][:3]
            
            # Run multiple simulations
            yards_gained = []
            for _ in range(20):
                result = RunConceptExecutor.execute_concept(
                    concept, rb, ol_players, dl_players, lb_players, field_state
                )
                yards_gained.append(result['yards_gained'])
            
            avg_yards = sum(yards_gained) / len(yards_gained)
            big_plays = sum(1 for y in yards_gained if y >= 10)
            
            print(f"\n{matchup_name}:")
            print(f"  Average: {avg_yards:.1f} yards")
            print(f"  Range: {min(yards_gained)} to {max(yards_gained)}")
            print(f"  Big plays (10+): {big_plays}/20")
    
    def run_statistical_analysis(self):
        """Run statistical analysis over many plays"""
        print("\n📊 Statistical Analysis (1000 plays)")
        print("-" * 40)
        
        all_results = []
        concept_stats = {concept.name: [] for concept in self.run_concepts}
        
        # Mock field state
        class MockFieldState:
            def __init__(self):
                self.down = random.randint(1, 3)
                self.yards_to_go = random.randint(1, 15)
                self.field_position = random.randint(20, 80)
            
            def is_goal_line(self):
                return self.field_position >= 90
            
            def is_short_yardage(self):
                return self.yards_to_go <= 3
        
        # Run 1000 random plays
        for _ in range(1000):
            # Random matchup
            offense_team_id = random.randint(1, 4)
            defense_team_id = random.randint(1, 4)
            while defense_team_id == offense_team_id:
                defense_team_id = random.randint(1, 4)
            
            offense_roster = self.team_rosters[offense_team_id]
            defense_roster = self.team_rosters[defense_team_id]
            
            rb = offense_roster['running_backs'][0]
            ol_players = offense_roster['offensive_line'][:5]
            dl_players = defense_roster['defensive_line'][:4]
            lb_players = defense_roster['linebackers'][:3]
            
            # Random concept
            concept = random.choice(self.run_concepts)
            field_state = MockFieldState()
            
            result = RunConceptExecutor.execute_concept(
                concept, rb, ol_players, dl_players, lb_players, field_state
            )
            
            all_results.append(result['yards_gained'])
            concept_stats[concept.name].append(result['yards_gained'])
        
        # Calculate overall stats
        avg_yards = sum(all_results) / len(all_results)
        positive_plays = sum(1 for y in all_results if y > 0)
        big_plays = sum(1 for y in all_results if y >= 10)
        losses = sum(1 for y in all_results if y < 0)
        
        print(f"Overall Results:")
        print(f"  Average Yards: {avg_yards:.2f}")
        print(f"  Positive Plays: {positive_plays}/1000 ({positive_plays/10:.1f}%)")
        print(f"  Big Plays (10+): {big_plays}/1000 ({big_plays/10:.1f}%)")
        print(f"  Losses: {losses}/1000 ({losses/10:.1f}%)")
        
        # Concept breakdown
        print(f"\nBy Concept:")
        for concept_name, yards in concept_stats.items():
            if yards:  # Only show concepts that were used
                avg = sum(yards) / len(yards)
                print(f"  {concept_name}: {avg:.1f} avg ({len(yards)} plays)")
    
    def run_interactive_menu(self):
        """Main interactive menu"""
        while True:
            print("\n" + "="*55)
            print("🏈 RUN CONCEPT TEST MENU")
            print("="*55)
            print("1. View Team Rosters")
            print("2. View Run Concepts")
            print("3. Test Random Run Concept")
            print("4. Test Specific Run Concept")
            print("5. Concept Comparison (Short Yardage)")
            print("6. Player Matchup Analysis")
            print("7. Statistical Analysis (1000 plays)")
            print("0. Exit")
            
            choice = input("\nEnter your choice (0-7): ").strip()
            
            if choice == "0":
                print("👋 Thanks for testing! Goodbye!")
                break
            elif choice == "1":
                self.display_team_rosters()
            elif choice == "2":
                self.display_run_concepts()
            elif choice == "3":
                self.test_single_concept()
            elif choice == "4":
                self.display_run_concepts()
                try:
                    concept_num = int(input("\nSelect concept number: "))
                    if 1 <= concept_num <= len(self.run_concepts):
                        self.test_single_concept(concept_num)
                    else:
                        print("❌ Invalid concept number")
                except ValueError:
                    print("❌ Invalid input")
            elif choice == "5":
                self.test_concept_comparison()
            elif choice == "6":
                self.test_player_matchups()
            elif choice == "7":
                self.run_statistical_analysis()
            else:
                print("❌ Invalid choice. Please try again.")
            
            if choice != "0":
                input("\nPress Enter to continue...")


def main():
    """Main function to run the test script"""
    try:
        tester = RunConceptTester()
        tester.run_interactive_menu()
    except KeyboardInterrupt:
        print("\n\n👋 Test interrupted by user. Goodbye!")
    except Exception as e:
        print(f"\n❌ Error occurred: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()