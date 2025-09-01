#!/usr/bin/env python3
"""
Enhanced Play Results Test - Random plays with comprehensive statistics and commentary
"""

import sys
import os
import random
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from game_engine.plays.pass_play import PassPlay
from game_engine.plays.run_play import RunPlay
from game_engine.field.field_state import FieldState
from game_engine.personnel.player_selector import PersonnelPackage


def create_mock_personnel():
    """Create mock personnel package with realistic player data"""
    
    class MockPlayer:
        def __init__(self, name, position, **attributes):
            self.name = name
            self.position = position
            for attr, value in attributes.items():
                setattr(self, attr, value)
        
        def __str__(self):
            return self.name
    
    # Mock team ratings
    offensive_players = {"qb_rating": 85, "wr_rating": 82, "ol_rating": 78, "rb_rating": 80}
    defensive_players = {"dl_rating": 83, "lb_rating": 79, "db_rating": 81}
    
    personnel = PersonnelPackage(
        offensive_players=offensive_players,
        defensive_players=defensive_players, 
        formation="shotgun",
        defensive_call="zone_coverage"
    )
    
    # Add realistic individual player tracking
    personnel.individual_players = True
    
    # Star players
    personnel.qb_on_field = MockPlayer("Josh Allen", "QB",
                                     accuracy=88, release_time=82, decision_making=90, 
                                     arm_strength=95, play_action=75, mobility=85,
                                     effective_rating=88)
    
    personnel.rb_on_field = MockPlayer("Jonathan Taylor", "RB",
                                     power=88, vision=90, speed=92, agility=89, 
                                     elusiveness=87, pass_protection=55,
                                     effective_rating=88)
    
    personnel.primary_wr = MockPlayer("Davante Adams", "WR",
                                    route_running=95, hands=92, speed=85, vision=88,
                                    effective_rating=90)
    
    personnel.te_on_field = MockPlayer("Travis Kelce", "TE",
                                     route_running=88, hands=90, pass_protection=78,
                                     effective_rating=89)
    
    # Offensive line (in proper order: LT, LG, C, RG, RT)
    personnel.ol_on_field = [
        MockPlayer("Dion Dawkins", "LT", effective_rating=78),   # Left Tackle
        MockPlayer("Quenton Nelson", "LG", effective_rating=94), # Elite Left Guard
        MockPlayer("Ryan Kelly", "C", effective_rating=88),      # Center
        MockPlayer("Chris Lindstrom", "RG", effective_rating=82), # Right Guard
        MockPlayer("Braden Smith", "RT", effective_rating=85)    # Right Tackle
    ]
    
    # Defensive line (3-4 defense: LE, DT, RE)
    personnel.dl_on_field = [
        MockPlayer("Khalil Mack", "DE", effective_rating=90),    # Left End (pass rusher)
        MockPlayer("Aaron Donald", "DT", effective_rating=99),   # Defensive Tackle (interior rush)
        MockPlayer("Joey Bosa", "DE", effective_rating=88)       # Right End
    ]
    
    # Linebackers
    personnel.lb_on_field = [
        MockPlayer("Roquan Smith", "MLB", effective_rating=92),  # Middle Linebacker
        MockPlayer("Darius Leonard", "OLB", effective_rating=89) # Outside Linebacker
    ]
    
    # Defensive backs (for statistics)
    personnel.cb_on_field = [MockPlayer("Jaire Alexander", "CB", effective_rating=91)]
    personnel.safety_on_field = [MockPlayer("Derwin James", "S", effective_rating=88)]
    
    # NEW: Set up direct position mapping for realistic player names in commentary
    personnel.set_position_player("LE", MockPlayer("Khalil Mack", "DE", effective_rating=90))
    personnel.set_position_player("DT", MockPlayer("Aaron Donald", "DT", effective_rating=99))  
    personnel.set_position_player("RE", MockPlayer("Joey Bosa", "DE", effective_rating=88))
    personnel.set_position_player("MLB", MockPlayer("Roquan Smith", "MLB", effective_rating=92))
    personnel.set_position_player("OLB", MockPlayer("Darius Leonard", "OLB", effective_rating=89))
    
    personnel.set_position_player("LT", MockPlayer("Dion Dawkins", "LT", effective_rating=78))
    personnel.set_position_player("LG", MockPlayer("Quenton Nelson", "LG", effective_rating=94))
    personnel.set_position_player("C", MockPlayer("Ryan Kelly", "C", effective_rating=88))
    personnel.set_position_player("RG", MockPlayer("Chris Lindstrom", "RG", effective_rating=82))
    personnel.set_position_player("RT", MockPlayer("Braden Smith", "RT", effective_rating=85))
    
    personnel.set_position_player("CB", MockPlayer("Jaire Alexander", "CB", effective_rating=91))
    personnel.set_position_player("S", MockPlayer("Derwin James", "S", effective_rating=88))
    
    return personnel


def create_random_field_state():
    """Create a random field state for variety"""
    scenarios = [
        {"field_position": random.randint(20, 80), "down": 1, "yards_to_go": 10},
        {"field_position": random.randint(30, 70), "down": 2, "yards_to_go": random.randint(5, 15)},
        {"field_position": random.randint(25, 75), "down": 3, "yards_to_go": random.randint(3, 20)},
        {"field_position": random.randint(80, 95), "down": 1, "yards_to_go": random.randint(1, 10)},  # Red zone
        {"field_position": random.randint(90, 99), "down": 2, "yards_to_go": random.randint(1, 5)},   # Goal line
    ]
    
    scenario = random.choice(scenarios)
    
    field_state = FieldState()
    field_state.field_position = scenario["field_position"] 
    field_state.down = scenario["down"]
    field_state.yards_to_go = scenario["yards_to_go"]
    field_state.quarter = random.randint(1, 4)
    field_state.game_clock = random.randint(60, 900)  # 1-15 minutes
    
    return field_state


def get_play_situation_description(field_state):
    """Generate human-readable situation description"""
    down_names = {1: "1st", 2: "2nd", 3: "3rd", 4: "4th"}
    down_name = down_names.get(field_state.down, str(field_state.down))
    
    # Field position description
    if field_state.field_position >= 95:
        field_desc = f"Goal line (Own {100 - field_state.field_position})"
    elif field_state.field_position >= 80:
        field_desc = f"Red zone (Own {100 - field_state.field_position})"
    elif field_state.field_position <= 20:
        field_desc = f"Deep territory (Own {field_state.field_position})"
    else:
        field_desc = f"Own {field_state.field_position}"
    
    return f"{down_name} & {field_state.yards_to_go} at {field_desc}"


def display_comprehensive_stats(result, play_number):
    """Display all available statistics from the play result"""
    
    print(f"\n{'='*60}")
    print(f"PLAY {play_number} COMPREHENSIVE STATISTICS")
    print(f"{'='*60}")
    
    # Basic play info
    print(f"Play Type: {result.play_type.upper()}")
    print(f"Outcome: {result.outcome}")
    print(f"Yards Gained: {result.yards_gained}")
    print(f"Points Scored: {result.score_points}")
    print(f"Time Elapsed: {result.time_elapsed}s")
    
    print(f"\n--- PLAY DESCRIPTION ---")
    print(f"Basic: {result.get_summary()}")
    print(f"Enhanced: {result.get_enhanced_summary()}")
    
    # Player tracking
    print(f"\n--- PLAYER TRACKING ---")
    if result.quarterback:
        print(f"Quarterback: {result.quarterback}")
    if result.receiver:
        print(f"Primary Receiver: {result.receiver}")
    if result.rusher:
        print(f"Rusher: {result.rusher}")
    if result.tackler:
        print(f"Primary Tackler: {result.tackler}")
    if result.assist_tackler:
        print(f"Assist Tackler: {result.assist_tackler}")
    
    # Passing statistics
    if result.play_type == "pass":
        print(f"\n--- PASSING STATISTICS ---")
        if result.pass_rusher:
            print(f"Pass Rusher: {result.pass_rusher}")
        if result.coverage_defender:
            print(f"Coverage Defender: {result.coverage_defender}")
        if result.passes_defended_by:
            print(f"Passes Defended By: {', '.join(result.passes_defended_by)}")
        if result.quarterback_hits_by:
            print(f"QB Hits By: {', '.join(result.quarterback_hits_by)}")
        if result.quarterback_hurries_by:
            print(f"QB Hurries By: {', '.join(result.quarterback_hurries_by)}")
        if result.interceptions_by:
            print(f"Intercepted By: {result.interceptions_by}")
        
        print(f"Clean Pocket: {'Yes' if result.clean_pocket else 'No'}")
        print(f"Perfect Protection: {'Yes' if result.perfect_protection else 'No'}")
        print(f"Pressure Applied: {'Yes' if result.pressure_applied else 'No'}")
        print(f"Coverage Beaten: {'Yes' if result.coverage_beaten else 'No'}")
        
        if result.protection_breakdowns:
            print(f"Protection Breakdowns:")
            for breakdown in result.protection_breakdowns:
                print(f"  - {breakdown.get('blocker', 'Unknown')} beaten by {breakdown.get('defender', 'Unknown')}")
    
    # Running statistics  
    if result.play_type == "run":
        print(f"\n--- RUNNING STATISTICS ---")
        if result.pancakes_by:
            print(f"Pancakes By: {', '.join(result.pancakes_by)}")
        if result.key_blocks_by:
            print(f"Key Blocks By: {', '.join(result.key_blocks_by)}")
        if result.missed_tackles_by:
            print(f"Missed Tackles By: {', '.join(result.missed_tackles_by)}")
        if result.tackles_for_loss_by:
            print(f"Tackles For Loss By: {', '.join(result.tackles_for_loss_by)}")
        
        print(f"Broken Tackles: {result.broken_tackles}")
        print(f"Perfect Protection: {'Yes' if result.perfect_protection else 'No'}")
        
        if result.protection_breakdowns:
            print(f"Blocking Failures:")
            for breakdown in result.protection_breakdowns:
                print(f"  - {breakdown.get('blocker', 'Unknown')} beaten by {breakdown.get('defender', 'Unknown')}")
    
    # Advanced context
    print(f"\n--- SITUATIONAL CONTEXT ---") 
    print(f"Down: {result.down}")
    print(f"Distance: {result.distance}")
    print(f"Field Position: {result.field_position}")
    print(f"Quarter: {result.quarter}")
    print(f"Game Clock: {result.game_clock}")
    print(f"Big Play (20+): {'Yes' if result.big_play else 'No'}")
    print(f"Explosive Play (40+): {'Yes' if result.explosive_play else 'No'}")
    print(f"Red Zone Play: {'Yes' if result.red_zone_play else 'No'}")
    print(f"Goal Line Play: {'Yes' if result.goal_line_play else 'No'}")


def run_enhanced_play_test():
    """Run 10 random plays and display comprehensive statistics"""
    
    print("ENHANCED PLAY RESULTS TEST")
    print("Testing comprehensive player statistics and commentary")
    print("Running 10 random plays with detailed analysis...")
    
    pass_play = PassPlay()
    run_play = RunPlay()
    personnel = create_mock_personnel()
    
    for play_num in range(1, 11):
        # Randomly choose play type
        play_type = random.choice(["pass", "run"])
        
        # Create random field situation
        field_state = create_random_field_state()
        situation_desc = get_play_situation_description(field_state)
        
        # Adjust formation based on situation
        if field_state.field_position >= 95:  # Goal line
            personnel.formation = "goal_line" if play_type == "run" else "shotgun"
            personnel.defensive_call = "goal_line_defense"
        elif field_state.down == 3 and field_state.yards_to_go > 7:  # 3rd and long
            personnel.formation = "shotgun_spread"
            personnel.defensive_call = "nickel_pass"
        elif field_state.down <= 2 and field_state.yards_to_go <= 3:  # Short yardage
            personnel.formation = "I_formation" if play_type == "run" else "shotgun"
            personnel.defensive_call = "base_defense"
        else:  # Normal down
            formations = ["shotgun", "singleback", "pistol"]
            personnel.formation = random.choice(formations)
            personnel.defensive_call = random.choice(["zone_coverage", "man_coverage", "base_defense"])
        
        print(f"\n{'*'*80}")
        print(f"PLAY {play_num}: {play_type.upper()} PLAY")
        print(f"Situation: {situation_desc}")
        print(f"Formation: {personnel.formation} vs {personnel.defensive_call}")
        print(f"{'*'*80}")
        
        # Execute the play
        if play_type == "pass":
            result = pass_play.simulate(personnel, field_state)
        else:
            result = run_play.simulate(personnel, field_state)
        
        # Display comprehensive statistics
        display_comprehensive_stats(result, play_num)
    
    print(f"\n{'='*80}")
    print("✅ ENHANCED PLAY RESULTS TEST COMPLETED")
    print("All 10 plays executed with comprehensive statistics!")
    print(f"{'='*80}")


if __name__ == "__main__":
    try:
        run_enhanced_play_test()
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()