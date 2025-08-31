#!/usr/bin/env python3
"""
Simple Run Test - Non-interactive version for quick testing
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.database.models.players.player import Player, PlayerRole, InjuryStatus
from src.database.models.players.positions import RunningBack, OffensiveLineman, DefensiveLineman, Linebacker
from src.database.generators.mock_generator import MockPlayerGenerator
from src.game_engine.plays.run_concepts import RunConcept, RunConceptLibrary, RunConceptExecutor
import random

def main():
    print("🏈 Simple Run Concept Test")
    print("=" * 30)
    
    # Generate teams
    generator = MockPlayerGenerator()
    
    # Team 1 - Power team
    power_team = generator.generate_team_roster(
        team_id=1, 
        team_data={'offense': {'rb_rating': 90, 'ol_rating': 85}, 'defense': {'dl_rating': 85, 'lb_rating': 80}}
    )
    
    # Team 2 - Speed team  
    speed_team = generator.generate_team_roster(
        team_id=2,
        team_data={'offense': {'rb_rating': 75, 'ol_rating': 70}, 'defense': {'dl_rating': 75, 'lb_rating': 85}}
    )
    
    print(f"✅ Generated team rosters")
    
    # Get players
    power_rb = power_team['running_backs'][0]
    power_ol = power_team['offensive_line'][:5]
    speed_dl = speed_team['defensive_line'][:4]
    speed_lb = speed_team['linebackers'][:3]
    
    print(f"✅ Power RB: {power_rb.name} (OVR: {power_rb.overall_rating}, Style: {power_rb.get_gap_preference()})")
    print(f"✅ Defense: Avg DL {sum(d.overall_rating for d in speed_dl)//4}, Avg LB {sum(l.overall_rating for l in speed_lb)//3}")
    
    # Test multiple concepts
    concepts = RunConceptLibrary.get_all_concepts()
    
    class MockFieldState:
        def __init__(self, down, distance, position):
            self.down = down
            self.yards_to_go = distance
            self.field_position = position
        
        def is_goal_line(self):
            return self.field_position >= 90
        
        def is_short_yardage(self):
            return self.yards_to_go <= 3
    
    # Test scenarios
    scenarios = [
        ("1st & 10 from 30", MockFieldState(1, 10, 30)),
        ("3rd & 2 from 45", MockFieldState(3, 2, 45)),
        ("1st & Goal from 5", MockFieldState(1, 1, 95))
    ]
    
    for scenario_name, field_state in scenarios:
        print(f"\n🎯 Testing {scenario_name}:")
        print("-" * 40)
        
        # Test 3 different concepts
        test_concepts = ['Inside Zone', 'Power O', 'Outside Zone']
        
        for concept_name in test_concepts:
            concept = next(c for c in concepts if c.name == concept_name)
            
            result = RunConceptExecutor.execute_concept(
                concept, power_rb, power_ol, speed_dl, speed_lb, field_state
            )
            
            print(f"{concept_name:12}: {result['yards_gained']:2d} yards - {result['play_description']}")
    
    # Quick statistical test
    print(f"\n📊 Quick Stats (100 Inside Zone plays):")
    print("-" * 45)
    
    inside_zone = next(c for c in concepts if c.name == "Inside Zone")
    field_state = MockFieldState(1, 10, 30)
    
    results = []
    for _ in range(100):
        result = RunConceptExecutor.execute_concept(
            inside_zone, power_rb, power_ol, speed_dl, speed_lb, field_state
        )
        results.append(result['yards_gained'])
    
    avg_yards = sum(results) / len(results)
    positive_plays = sum(1 for y in results if y > 0)
    big_plays = sum(1 for y in results if y >= 10)
    
    print(f"Average yards: {avg_yards:.1f}")
    print(f"Positive plays: {positive_plays}/100 ({positive_plays}%)")
    print(f"Big plays (10+): {big_plays}/100 ({big_plays}%)")
    print(f"Range: {min(results)} to {max(results)} yards")
    
    print(f"\n✅ All tests completed successfully!")

if __name__ == "__main__":
    main()