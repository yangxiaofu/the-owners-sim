#!/usr/bin/env python3
"""
Game State Management System Demo

Demonstrates the field tracker and down tracker working together to manage
complete game state progression through realistic NFL scenarios.
"""

from src.play_engine.game_state import (
    GameStateManager, 
    GameState,
    FieldPosition, 
    DownState,
    FieldZone
)
from src.play_engine.simulation.stats import PlayStatsSummary


def create_play_summary(play_type: str, yards_gained: int) -> PlayStatsSummary:
    """Helper to create PlayStatsSummary for demo"""
    return PlayStatsSummary(
        play_type=play_type,
        yards_gained=yards_gained,
        time_elapsed=4.2
    )


def print_game_state(state: GameState, description: str):
    """Print current game state in a readable format"""
    print(f"\n{description}")
    print(f"  Position: {state.possessing_team} ball at {state.field_position.yard_line}-yard line")
    print(f"  Situation: {state.down_state.current_down}{ordinal(state.down_state.current_down)} & {state.down_state.yards_to_go}")
    print(f"  Field Zone: {state.field_position.field_zone.value.replace('_', ' ').title()}")


def print_play_result(result, play_description: str):
    """Print play result in a readable format"""
    print(f"\n🏈 {play_description}")
    print(f"  Raw yards: {result.field_result.raw_yards_gained}")
    print(f"  Actual yards: {result.field_result.actual_yards_gained}")
    
    if result.scoring_occurred:
        print(f"  🎯 SCORE! {result.field_result.scoring_type.upper()} - {result.get_points_scored()} points")
    
    if result.is_first_down():
        print(f"  ✅ FIRST DOWN!")
    elif result.is_turnover_on_downs():
        print(f"  ❌ TURNOVER ON DOWNS")
    
    if result.drive_ended:
        print(f"  📍 Drive ended")
    
    print(f"  Events: {', '.join(result.all_game_events)}")


def ordinal(n):
    """Convert number to ordinal string"""
    return {1: "1st", 2: "2nd", 3: "3rd", 4: "4th"}.get(n, f"{n}th")


def main():
    """Run game state management demonstration"""
    print("🏟️  NFL Game State Management System Demo")
    print("=" * 50)
    
    # Initialize game state manager
    manager = GameStateManager()
    
    # Start a drive at own 25-yard line
    game_state = manager.create_new_drive(25, "Detroit Lions")
    print_game_state(game_state, "🚀 Starting new drive")
    
    # Play 1: 8-yard run
    play1 = create_play_summary("run", 8)
    result1 = manager.process_play(game_state, play1)
    print_play_result(result1, "8-yard run up the middle")
    print_game_state(result1.new_game_state, "After Play 1")
    
    # Play 2: 15-yard pass (first down)
    play2 = create_play_summary("pass", 15)
    result2 = manager.process_play(result1.new_game_state, play2)
    print_play_result(result2, "15-yard pass to the sideline")
    print_game_state(result2.new_game_state, "After Play 2")
    
    # Fast forward to red zone
    red_zone_state = GameState(
        FieldPosition(92, "Detroit Lions", FieldZone.RED_ZONE),
        DownState(2, 8, 100),
        "Detroit Lions"
    )
    print_game_state(red_zone_state, "⚡ Fast forward to RED ZONE")
    
    # Play 3: The famous "5-yard line + 10-yard pass = touchdown" scenario
    td_play = create_play_summary("pass", 15)  # 15-yard pass but only 8 yards to goal
    td_result = manager.process_play(red_zone_state, td_play)
    print_play_result(td_result, "15-yard pass attempt to the corner")
    
    print("\n" + "=" * 50)
    print("🎯 TOUCHDOWN DEMONSTRATION")
    print(f"Raw play mechanics: {td_result.field_result.raw_yards_gained} yards")
    print(f"Field-constrained reality: {td_result.field_result.actual_yards_gained} yards")
    print(f"Result: {td_result.field_result.scoring_type.upper()} for {td_result.get_points_scored()} points!")
    
    # Demonstrate 4th down scenarios
    print("\n" + "=" * 50)
    print("⚡ 4TH DOWN SCENARIOS")
    
    # Successful 4th down conversion
    fourth_down_state = GameState(
        FieldPosition(45, "Green Bay Packers", FieldZone.OWN_TERRITORY),
        DownState(4, 2, 47),
        "Green Bay Packers"
    )
    print_game_state(fourth_down_state, "4th & 2 conversion attempt")
    
    conversion_play = create_play_summary("run", 3)
    conversion_result = manager.process_play(fourth_down_state, conversion_play)
    print_play_result(conversion_result, "QB sneak for 3 yards")
    print_game_state(conversion_result.new_game_state, "After successful conversion")
    
    # Failed 4th down conversion
    failed_fourth_state = GameState(
        FieldPosition(55, "Green Bay Packers", FieldZone.OPPONENT_TERRITORY),
        DownState(4, 5, 60),
        "Green Bay Packers"  
    )
    print_game_state(failed_fourth_state, "4th & 5 conversion attempt")
    
    failed_play = create_play_summary("pass", 3)
    failed_result = manager.process_play(failed_fourth_state, failed_play)
    print_play_result(failed_result, "Incomplete pass, short of first down marker")
    
    # Demonstrate turnover handling
    print("\n" + "=" * 50)
    print("🔄 TURNOVER DEMONSTRATION")
    
    fumble_state = GameState(
        FieldPosition(35, "Chicago Bears", FieldZone.OWN_TERRITORY),
        DownState(2, 6, 41),
        "Chicago Bears"
    )
    print_game_state(fumble_state, "Before fumble")
    
    fumble_result = manager.process_turnover(fumble_state, "fumble", "Minnesota Vikings")
    print_play_result(fumble_result, "FUMBLE recovered by opposing team")
    print_game_state(fumble_result.new_game_state, "After turnover - New possession")
    
    print("\n" + "=" * 50)
    print("✅ Demo complete! Game state management system working perfectly.")
    print(f"📊 Key features demonstrated:")
    print(f"  • Field position tracking with boundary detection")
    print(f"  • Down progression and first down detection")
    print(f"  • Touchdown scoring with field constraints")
    print(f"  • 4th down conversions and turnovers on downs")
    print(f"  • Turnover handling with field position flip")
    print(f"  • Unified game state coordination")


if __name__ == "__main__":
    main()