#!/usr/bin/env python3
"""
Contextual Decision Making Demo
Showcases how different coaching archetypes make decisions in various game scenarios
"""

import sys
import os
import random
from typing import Dict, List, Tuple

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import game engine components
try:
    from src.game_engine.coaching.clock.context.game_context import GameContext
    from src.game_engine.field.game_state import GameState
    from src.game_engine.field.field_state import FieldState
    from src.game_engine.field.game_clock import GameClock
    from src.game_engine.field.scoreboard import Scoreboard
    from src.game_engine.plays.play_calling import PlayCaller
    from src.game_engine.core.play_executor import PlayExecutor
    from src.game_engine.plays.data_structures import PlayResult
    
    print("✅ Successfully imported game engine components")
    components_available = True
except ImportError as e:
    print(f"⚠️  Could not import game engine components: {e}")
    print("Demo will use simplified mock implementations")
    components_available = False

class DemoScenario:
    """Represents a specific game scenario for testing contextual decisions"""
    
    def __init__(self, name: str, quarter: int, time_remaining: int, 
                 home_score: int, away_score: int, field_position: int,
                 down: int, yards_to_go: int, description: str):
        self.name = name
        self.quarter = quarter
        self.time_remaining = time_remaining
        self.home_score = home_score
        self.away_score = away_score
        self.field_position = field_position
        self.down = down
        self.yards_to_go = yards_to_go
        self.description = description
        
    def create_game_state(self):
        """Create a GameState object for this scenario"""
        if not components_available:
            return None
            
        game_state = GameState()
        
        # Set field state
        game_state.field.down = self.down
        game_state.field.yards_to_go = self.yards_to_go
        game_state.field.field_position = self.field_position
        game_state.field.possession_team_id = 1  # Home team has possession
        
        # Set clock
        game_state.clock.quarter = self.quarter
        game_state.clock.clock = self.time_remaining
        
        # Set scoreboard
        game_state.scoreboard.home_team_id = 1
        game_state.scoreboard.away_team_id = 2
        game_state.scoreboard.home_score = self.home_score
        game_state.scoreboard.away_score = self.away_score
        
        return game_state
    
    def get_context_description(self) -> str:
        """Get a human-readable context description"""
        score_diff = self.home_score - self.away_score
        if score_diff > 0:
            situation = f"Leading by {score_diff}"
        elif score_diff < 0:
            situation = f"Trailing by {abs(score_diff)}"
        else:
            situation = "Tied game"
            
        quarter_desc = f"Q{self.quarter}"
        time_desc = f"{self.time_remaining//60}:{self.time_remaining%60:02d}"
        field_desc = f"Own {self.field_position}" if self.field_position < 50 else f"Opp {100-self.field_position}"
        down_desc = f"{self.down} & {self.yards_to_go}"
        
        return f"{situation} | {quarter_desc} {time_desc} | {field_desc} | {down_desc}"

class ContextualDecisionDemo:
    """Main demo class that runs contextual decision scenarios"""
    
    def __init__(self):
        self.archetypes = [
            "aggressive", "conservative", "balanced", "innovative", 
            "traditional", "air_raid", "run_heavy", "west_coast"
        ]
        
        self.scenarios = self._create_demo_scenarios()
        self.play_caller = PlayCaller() if components_available else None
        self.play_executor = PlayExecutor() if components_available else None
        
    def _create_demo_scenarios(self):
        """Create 25 interesting game scenarios to demonstrate contextual decisions"""
        return [
            # Critical game situations
            DemoScenario("Game-winning drive", 4, 120, 14, 17, 75, 3, 8, 
                        "Down by 3 with 2 minutes left, in opponent territory"),
            DemoScenario("Protect the lead", 4, 480, 24, 17, 35, 2, 6,
                        "Leading by 7 with 8 minutes left, own territory"),
            DemoScenario("Two-minute drill", 4, 90, 21, 21, 45, 1, 10,
                        "Tied game with 1:30 left at midfield"),
            DemoScenario("Desperation time", 4, 45, 10, 17, 25, 4, 12,
                        "Down by 7 with 45 seconds, long 4th down in own territory"),
            DemoScenario("Goal line stand", 4, 180, 14, 13, 97, 3, 2,
                        "Leading by 1 with 3 minutes left, opponent's 3-yard line"),
            
            # 4th down scenarios
            DemoScenario("Short yardage gamble", 3, 420, 14, 14, 55, 4, 1,
                        "Tied game, 4th and 1 in opponent territory"),
            DemoScenario("Field goal range", 4, 300, 17, 20, 72, 4, 8,
                        "Down by 3, 4th and 8 in field goal range"),
            DemoScenario("Punt or go", 2, 180, 7, 10, 42, 4, 6,
                        "Down by 3 in 2nd quarter, 4th and 6 at midfield"),
            DemoScenario("Red zone decision", 4, 600, 21, 14, 88, 4, 3,
                        "Leading by 7, 4th and 3 in red zone"),
            DemoScenario("Own territory punt", 3, 720, 10, 7, 28, 4, 5,
                        "Leading by 3, 4th and 5 in own territory"),
            
            # Two-point conversion scenarios
            DemoScenario("Must go for 2", 4, 180, 20, 22, 5, 1, 5,
                        "Down by 2 after touchdown, need 2-point conversion"),
            DemoScenario("Extra point or 2", 4, 420, 21, 20, 3, 1, 3,
                        "Leading by 1 after TD, decision time"),
            DemoScenario("Garbage time TD", 4, 90, 35, 14, 8, 2, 8,
                        "Big lead, late touchdown"),
            DemoScenario("Comeback attempt", 4, 240, 14, 21, 4, 1, 4,
                        "Down by 7 after TD, need to decide on conversion"),
            DemoScenario("Take the lead", 4, 360, 27, 28, 6, 3, 6,
                        "Down by 1 after TD, chance to take lead"),
            
            # Clock management scenarios
            DemoScenario("End of half", 2, 35, 14, 10, 68, 2, 12,
                        "Leading by 4, end of first half in field goal range"),
            DemoScenario("Milk the clock", 4, 240, 28, 21, 45, 1, 10,
                        "Leading by 7 with 4 minutes left"),
            DemoScenario("Hurry up offense", 4, 180, 17, 24, 60, 2, 8,
                        "Down by 7 with 3 minutes, need to score quickly"),
            DemoScenario("Conservative drive", 4, 420, 21, 17, 25, 1, 10,
                        "Leading by 4 with 7 minutes, control the game"),
            DemoScenario("Prevent defense time", 4, 90, 24, 17, 80, 3, 15,
                        "Leading by 7, opponent in red zone with little time"),
            
            # Situational scenarios
            DemoScenario("Weather game", 3, 540, 10, 13, 35, 3, 7,
                        "Down by 3 in bad weather, 3rd and 7"),
            DemoScenario("Rivalry game", 4, 300, 21, 21, 50, 3, 4,
                        "Tied rivalry game with 5 minutes left"),
            DemoScenario("Playoff implications", 4, 600, 14, 17, 30, 2, 12,
                        "Must-win game, down by 3 with 10 minutes left"),
            DemoScenario("Blowout management", 4, 480, 42, 14, 40, 2, 5,
                        "Big lead, manage the game responsibly"),
            DemoScenario("First quarter tone", 1, 720, 0, 0, 25, 3, 8,
                        "Opening drive, set the tone for the game")
        ]
    
    def analyze_scenario_decisions(self, scenario):
        """Analyze how different archetypes would handle a scenario"""
        if not components_available:
            return self._mock_scenario_analysis(scenario)
            
        game_state = scenario.create_game_state()
        context = GameContext.from_game_state(game_state, 1)
        
        archetype_decisions = {}
        
        for archetype in self.archetypes:
            # Create coordinator with archetype
            coordinator = {"archetype": archetype}
            
            # Analyze the decision
            decision_analysis = {
                "play_call": "unknown",
                "reasoning": [],
                "context_factors": {
                    "time_pressure": context.get_time_pressure_level(),
                    "is_critical_time": context.is_critical_time,
                    "is_two_minute_drill": context.is_two_minute_drill,
                    "is_leading": context.is_leading,
                    "is_trailing": context.is_trailing,
                    "score_differential": context.score_differential
                }
            }
            
            try:
                # Determine play type for normal downs
                if scenario.down <= 3:
                    play_type = self.play_caller.determine_play_type(game_state.field, coordinator)
                    decision_analysis["play_call"] = play_type
                    decision_analysis["reasoning"].append(f"Called {play_type} play")
                    
                # Analyze 4th down decisions
                elif scenario.down == 4:
                    fourth_down_decision = self._analyze_fourth_down_decision(
                        scenario, archetype, context
                    )
                    decision_analysis.update(fourth_down_decision)
                    
                # Check for two-point conversion scenarios (touchdown situations)
                if scenario.field_position >= 95 and scenario.down <= 2:
                    conversion_decision = self._analyze_conversion_decision(
                        scenario, archetype, context
                    )
                    decision_analysis["conversion"] = conversion_decision
                    
            except Exception as e:
                decision_analysis["play_call"] = "error"
                decision_analysis["reasoning"].append(f"Analysis error: {str(e)}")
                
            archetype_decisions[archetype] = decision_analysis
            
        return archetype_decisions
    
    def _analyze_fourth_down_decision(self, scenario, archetype, context):
        """Analyze 4th down decision for an archetype"""
        # Simplified 4th down analysis
        field_goal_range = scenario.field_position >= 65
        short_yardage = scenario.yards_to_go <= 3
        desperation_mode = context.is_two_minute_drill and context.is_trailing
        
        reasoning = []
        
        if desperation_mode:
            decision = "go_for_it"
            reasoning.append("Desperation mode - must go for it")
        elif short_yardage and scenario.field_position >= 50:
            if archetype in ["aggressive", "innovative"]:
                decision = "go_for_it"
                reasoning.append(f"{archetype} archetype favors aggressive 4th down")
            else:
                decision = "field_goal" if field_goal_range else "punt"
                reasoning.append(f"{archetype} archetype plays it safe")
        elif field_goal_range:
            decision = "field_goal"
            reasoning.append("In field goal range")
        else:
            decision = "punt"
            reasoning.append("Not in field goal range, punt it away")
            
        return {
            "play_call": decision,
            "reasoning": reasoning
        }
    
    def _analyze_conversion_decision(self, scenario, archetype, context):
        """Analyze two-point conversion decision"""
        score_diff = context.score_differential
        
        # Key scenarios for 2-point attempts
        down_by_8 = score_diff == -8  # Need TD + 2PT to tie
        down_by_1 = score_diff == -1  # 2PT gives lead
        late_game = context.is_two_minute_drill or context.is_critical_time
        
        if down_by_8:
            return {"decision": "two_point", "reason": "Must go for 2 to have chance"}
        elif down_by_1 and late_game:
            if archetype in ["aggressive", "innovative"]:
                return {"decision": "two_point", "reason": "Aggressive archetype goes for lead"}
            else:
                return {"decision": "extra_point", "reason": "Conservative, take the tie"}
        elif abs(score_diff) >= 21:  # Garbage time
            return {"decision": "extra_point", "reason": "Garbage time, take the point"}
        else:
            base_rate = 0.15 if archetype == "aggressive" else 0.05
            return {"decision": "extra_point", "reason": f"Standard situation ({base_rate:.1%} 2PT rate)"}
    
    def _mock_scenario_analysis(self, scenario):
        """Provide mock analysis when components aren't available"""
        mock_decisions = {}
        
        for archetype in self.archetypes:
            if scenario.down == 4:
                if archetype in ["aggressive", "innovative"]:
                    decision = "go_for_it" if scenario.yards_to_go <= 3 else "field_goal"
                else:
                    decision = "punt" if scenario.field_position < 65 else "field_goal"
            else:
                if archetype in ["air_raid", "west_coast"]:
                    decision = "pass"
                elif archetype in ["run_heavy", "traditional"]:
                    decision = "run"
                else:
                    decision = "balanced_mix"
                    
            mock_decisions[archetype] = {
                "play_call": decision,
                "reasoning": [f"Mock {archetype} decision"],
                "context_factors": {
                    "time_pressure": "medium",
                    "is_critical_time": scenario.quarter == 4,
                    "score_differential": scenario.home_score - scenario.away_score
                }
            }
            
        return mock_decisions
    
    def run_demo(self):
        """Run the contextual decision demo"""
        print("=" * 80)
        print("CONTEXTUAL DECISION MAKING DEMO")
        print("=" * 80)
        print("Analyzing how different coaching archetypes make decisions")
        print("across 25 critical game scenarios\n")
        
        print(f"Available Archetypes: {', '.join(self.archetypes)}")
        print(f"Total Scenarios: {len(self.scenarios)}\n")
        
        # Group scenarios for better presentation
        scenario_groups = {
            "Critical Game Situations": self.scenarios[0:5],
            "4th Down Scenarios": self.scenarios[5:10], 
            "Two-Point Conversion Scenarios": self.scenarios[10:15],
            "Clock Management Scenarios": self.scenarios[15:20],
            "Situational Scenarios": self.scenarios[20:25]
        }
        
        for group_name, group_scenarios in scenario_groups.items():
            print("=" * 60)
            print(f"{group_name.upper()}")
            print("=" * 60)
            
            for i, scenario in enumerate(group_scenarios, 1):
                print(f"\n{i}. {scenario.name}")
                print(f"   Situation: {scenario.get_context_description()}")
                print(f"   {scenario.description}")
                
                # Analyze decisions
                decisions = self.analyze_scenario_decisions(scenario)
                
                # Display archetype decisions in a compact format
                decision_summary = {}
                for archetype, analysis in decisions.items():
                    decision_summary[archetype] = analysis["play_call"]
                
                # Group similar decisions
                decision_groups = {}
                for archetype, decision in decision_summary.items():
                    if decision not in decision_groups:
                        decision_groups[decision] = []
                    decision_groups[decision].append(archetype)
                
                print("   Archetype Decisions:")
                for decision, archetypes in decision_groups.items():
                    archetype_list = ", ".join(archetypes)
                    print(f"     • {decision.replace('_', ' ').title()}: {archetype_list}")
                
                # Show context factors for first scenario in each group
                if i == 1 and components_available:
                    context = list(decisions.values())[0]["context_factors"]
                    print(f"   Context: {context['time_pressure']} pressure, "
                          f"{'critical time' if context['is_critical_time'] else 'normal time'}")
        
        # Summary statistics
        print("\n" + "=" * 80)
        print("DEMO SUMMARY")
        print("=" * 80)
        
        # Count decision types across all scenarios
        all_decisions = {}
        archetype_patterns = {archetype: {"aggressive": 0, "conservative": 0} 
                            for archetype in self.archetypes}
        
        for scenario in self.scenarios:
            decisions = self.analyze_scenario_decisions(scenario)
            for archetype, analysis in decisions.items():
                decision = analysis["play_call"]
                
                if decision not in all_decisions:
                    all_decisions[decision] = 0
                all_decisions[decision] += 1
                
                # Classify as aggressive or conservative
                aggressive_decisions = ["go_for_it", "two_point", "pass"]
                if decision in aggressive_decisions:
                    archetype_patterns[archetype]["aggressive"] += 1
                else:
                    archetype_patterns[archetype]["conservative"] += 1
        
        print(f"Total decision points analyzed: {len(self.scenarios) * len(self.archetypes)}")
        print(f"Decision types observed: {', '.join(all_decisions.keys())}")
        
        print("\nArchetype Aggression Patterns:")
        for archetype in self.archetypes:
            aggressive = archetype_patterns[archetype]["aggressive"]
            conservative = archetype_patterns[archetype]["conservative"]
            total = aggressive + conservative
            if total > 0:
                aggression_rate = aggressive / total * 100
                print(f"  {archetype:12}: {aggression_rate:5.1f}% aggressive decisions")
        
        print(f"\n✅ Demo completed successfully!")
        print("This demonstrates the contextual intelligence system adapting")
        print("coaching decisions based on game situation and archetype philosophy.")

def main():
    """Run the contextual decision demo"""
    try:
        demo = ContextualDecisionDemo()
        demo.run_demo()
        return 0
    except Exception as e:
        print(f"❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())