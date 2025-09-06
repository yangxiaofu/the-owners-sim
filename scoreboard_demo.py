#!/usr/bin/env python3
"""
Scoreboard System Demonstration

Simple demonstration of the scoreboard and scoring mapper functionality.
Shows how to track scores for an NFL game between two teams.
"""

from src.game_management.scoreboard import Scoreboard, ScoringType, ScoringEvent
from src.game_management.scoring_mapper import ScoringTypeMapper
from src.constants.team_ids import TeamIDs


def main():
    """Demonstrate scoreboard functionality"""
    print("🏈 NFL Scoreboard System Demo")
    print("=" * 50)
    
    # Initialize scoreboard for Lions vs Packers
    print(f"Initializing game: Lions (Team {TeamIDs.DETROIT_LIONS}) vs Packers (Team {TeamIDs.GREEN_BAY_PACKERS})")
    scoreboard = Scoreboard(TeamIDs.DETROIT_LIONS, TeamIDs.GREEN_BAY_PACKERS)
    print(f"Initial score: {scoreboard}")
    print()
    
    # Simulate scoring plays throughout the game
    print("🎮 Simulating scoring plays...")
    print("-" * 30)
    
    # Quarter 1: Packers field goal
    print("Q1: Packers 42-yard field goal attempt...")
    scoreboard.add_score(
        TeamIDs.GREEN_BAY_PACKERS,
        ScoringType.FIELD_GOAL,
        "42-yard FG by Mason Crosby",
        quarter=1,
        game_time="6:23"
    )
    print(f"Score update: {scoreboard}")
    print()
    
    # Quarter 2: Lions touchdown and extra point
    print("Q2: Lions scoring drive...")
    scoreboard.add_score(
        TeamIDs.DETROIT_LIONS,
        ScoringType.TOUCHDOWN,
        "15-yard TD pass to Amon-Ra St. Brown",
        quarter=2,
        game_time="9:45"
    )
    print(f"Touchdown! {scoreboard}")
    
    scoreboard.add_score(
        TeamIDs.DETROIT_LIONS,
        ScoringType.EXTRA_POINT,
        "Extra point good",
        quarter=2,
        game_time="9:44"
    )
    print(f"Extra point good! {scoreboard}")
    print()
    
    # Quarter 3: Safety for Lions
    print("Q3: Safety for Lions...")
    scoreboard.add_score(
        TeamIDs.DETROIT_LIONS,
        ScoringType.SAFETY,
        "Aaron Rodgers tackled in end zone",
        quarter=3,
        game_time="4:12"
    )
    print(f"Safety! {scoreboard}")
    print()
    
    # Quarter 4: Packers touchdown and failed 2-point conversion
    print("Q4: Packers touchdown...")
    scoreboard.add_score(
        TeamIDs.GREEN_BAY_PACKERS,
        ScoringType.TOUCHDOWN,
        "8-yard TD run by Aaron Jones",
        quarter=4,
        game_time="3:15"
    )
    print(f"Touchdown! {scoreboard}")
    
    print("Q4: Packers attempting 2-point conversion...")
    scoreboard.add_score(
        TeamIDs.GREEN_BAY_PACKERS,
        ScoringType.TWO_POINT_CONVERSION,
        "2-point conversion pass to Davante Adams",
        quarter=4,
        game_time="3:14"
    )
    print(f"2-point conversion good! {scoreboard}")
    print()
    
    # Final score analysis
    print("📊 Final Game Analysis")
    print("-" * 30)
    print(f"Final Score: {scoreboard}")
    
    if scoreboard.is_tied():
        print("🤝 Game ended in a tie!")
    else:
        leading_team = scoreboard.get_leading_team()
        score_diff = scoreboard.get_score_difference()
        team_name = "Lions" if leading_team == TeamIDs.DETROIT_LIONS else "Packers"
        print(f"🏆 {team_name} win by {score_diff} points!")
    
    print()
    
    # Scoring history
    print("📝 Complete Scoring History")
    print("-" * 30)
    history = scoreboard.get_scoring_history()
    for i, event in enumerate(history, 1):
        team_name = "Lions" if event.team_id == TeamIDs.DETROIT_LIONS else "Packers"
        print(f"{i}. Q{event.quarter} {event.game_time} - {team_name} {event.scoring_type.name} ({event.points} pts)")
        if event.description:
            print(f"   {event.description}")
    
    print()
    
    # Team-specific scoring breakdown
    print("📈 Team Scoring Breakdown")
    print("-" * 30)
    
    for team_id, team_name in [(TeamIDs.DETROIT_LIONS, "Lions"), (TeamIDs.GREEN_BAY_PACKERS, "Packers")]:
        print(f"{team_name} (Team {team_id}):")
        print(f"  Total Points: {scoreboard.get_team_score(team_id)}")
        
        team_history = scoreboard.get_team_scoring_history(team_id)
        scoring_breakdown = {}
        for event in team_history:
            scoring_type = event.scoring_type.name
            if scoring_type in scoring_breakdown:
                scoring_breakdown[scoring_type] += 1
            else:
                scoring_breakdown[scoring_type] = 1
        
        print("  Scoring Breakdown:")
        for scoring_type, count in scoring_breakdown.items():
            points_each = ScoringType[scoring_type].value
            total_points = count * points_each
            print(f"    {scoring_type}: {count}x ({total_points} pts)")
        print()
    
    # Demonstrate scoring mapper functionality
    print("🔄 Scoring Mapper Demonstration")
    print("-" * 30)
    
    # Simulate FieldResult scoring_type strings
    field_result_examples = [
        "touchdown",
        "field_goal", 
        "safety",
        "extra_point",
        "two_point_conversion",
        "fg",          # Alternative spelling
        "td",          # Alternative spelling
        "invalid_type" # Invalid type
    ]
    
    print("Converting FieldResult scoring_type strings to ScoringType enums:")
    for field_string in field_result_examples:
        scoring_type = ScoringTypeMapper.from_field_result(field_string)
        if scoring_type:
            points = scoring_type.value
            print(f"  '{field_string}' → {scoring_type.name} ({points} pts)")
        else:
            print(f"  '{field_string}' → Invalid scoring type")
    
    print()
    print("✅ Scoreboard demonstration complete!")


if __name__ == "__main__":
    main()