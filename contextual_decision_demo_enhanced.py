#!/usr/bin/env python3
"""
Enhanced Contextual Decision Making Demo
Showcases realistic archetype-based decisions using the actual contextual intelligence system
"""

import sys
import os
import random
from typing import Dict, List

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

class MockGameState:
    def __init__(self, field=None, clock=None, scoreboard=None):
        self.field = field or MockFieldState()
        self.clock = clock or MockClock()
        self.scoreboard = scoreboard or MockScoreboard()

class MockFieldState:
    def __init__(self, down=1, yards_to_go=10, field_position=25, possession_team_id=1):
        self.down = down
        self.yards_to_go = yards_to_go
        self.field_position = field_position
        self.possession_team_id = possession_team_id

class MockClock:
    def __init__(self, quarter=1, clock=900):
        self.quarter = quarter
        self.clock = clock

class MockScoreboard:
    def __init__(self, home_score=0, away_score=0, home_team_id=1, away_team_id=2):
        self.home_score = home_score
        self.away_score = away_score
        self.home_team_id = home_team_id
        self.away_team_id = away_team_id
    
    def get_score(self):
        return self.home_score, self.away_score
    
    def get_score_differential(self, team_id):
        if team_id == self.home_team_id:
            return self.home_score - self.away_score
        else:
            return self.away_score - self.home_score

# Import our actual contextual intelligence system
try:
    sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
    from game_engine.coaching.clock.context.game_context import GameContext
    contextual_system_available = True
    print("✅ Successfully imported contextual intelligence system")
except ImportError as e:
    print(f"⚠️  Could not import contextual system: {e}")
    contextual_system_available = False

class EnhancedContextualDecisionEngine:
    """Enhanced decision engine that uses real contextual intelligence"""
    
    def __init__(self):
        # Archetype-specific decision patterns based on our implemented system
        self.archetype_patterns = {
            "aggressive": {
                "base_aggression": 0.75,
                "fourth_down_threshold": 0.6,
                "two_point_base_rate": 0.15,
                "risk_tolerance": 0.8,
                "play_preferences": {"pass": 0.6, "run": 0.4}
            },
            "conservative": {
                "base_aggression": 0.25,
                "fourth_down_threshold": 0.3,
                "two_point_base_rate": 0.05,
                "risk_tolerance": 0.3,
                "play_preferences": {"pass": 0.4, "run": 0.6}
            },
            "balanced": {
                "base_aggression": 0.5,
                "fourth_down_threshold": 0.45,
                "two_point_base_rate": 0.08,
                "risk_tolerance": 0.55,
                "play_preferences": {"pass": 0.5, "run": 0.5}
            },
            "innovative": {
                "base_aggression": 0.7,
                "fourth_down_threshold": 0.65,
                "two_point_base_rate": 0.12,
                "risk_tolerance": 0.75,
                "play_preferences": {"pass": 0.65, "run": 0.35}
            },
            "traditional": {
                "base_aggression": 0.3,
                "fourth_down_threshold": 0.35,
                "two_point_base_rate": 0.04,
                "risk_tolerance": 0.35,
                "play_preferences": {"pass": 0.35, "run": 0.65}
            },
            "air_raid": {
                "base_aggression": 0.65,
                "fourth_down_threshold": 0.55,
                "two_point_base_rate": 0.10,
                "risk_tolerance": 0.65,
                "play_preferences": {"pass": 0.85, "run": 0.15}
            },
            "run_heavy": {
                "base_aggression": 0.4,
                "fourth_down_threshold": 0.4,
                "two_point_base_rate": 0.06,
                "risk_tolerance": 0.45,
                "play_preferences": {"pass": 0.25, "run": 0.75}
            },
            "west_coast": {
                "base_aggression": 0.55,
                "fourth_down_threshold": 0.5,
                "two_point_base_rate": 0.09,
                "risk_tolerance": 0.6,
                "play_preferences": {"pass": 0.7, "run": 0.3}
            }
        }
    
    def analyze_contextual_decision(self, scenario, archetype):
        """Analyze what decision an archetype would make in a scenario"""
        
        # Create game state and context
        game_state = self._create_game_state(scenario)
        
        if contextual_system_available:
            context = GameContext.from_game_state(game_state, 1)
        else:
            context = self._create_mock_context(scenario)
        
        archetype_config = self.archetype_patterns[archetype]
        
        decision_analysis = {
            "primary_decision": "",
            "reasoning": [],
            "context_factors": self._get_context_summary(context),
            "confidence": 0.0
        }
        
        # 4th down decisions
        if scenario["down"] == 4:
            decision_analysis.update(
                self._analyze_fourth_down(scenario, archetype, context, archetype_config)
            )
        
        # Two-point conversion scenarios
        elif scenario.get("is_touchdown_scenario", False):
            decision_analysis.update(
                self._analyze_two_point_conversion(scenario, archetype, context, archetype_config)
            )
        
        # Regular play calling
        else:
            decision_analysis.update(
                self._analyze_regular_play_call(scenario, archetype, context, archetype_config)
            )
        
        return decision_analysis
    
    def _create_game_state(self, scenario):
        """Create game state from scenario"""
        field = MockFieldState(
            down=scenario["down"],
            yards_to_go=scenario["yards_to_go"], 
            field_position=scenario["field_position"]
        )
        clock = MockClock(
            quarter=scenario["quarter"],
            clock=scenario["time_remaining"]
        )
        scoreboard = MockScoreboard(
            home_score=scenario["home_score"],
            away_score=scenario["away_score"]
        )
        return MockGameState(field, clock, scoreboard)
    
    def _create_mock_context(self, scenario):
        """Create mock context when real system unavailable"""
        class MockContext:
            def __init__(self, scenario):
                self.score_differential = scenario["home_score"] - scenario["away_score"]
                self.time_remaining = scenario["time_remaining"]
                self.quarter = scenario["quarter"]
                self.is_leading = self.score_differential > 0
                self.is_trailing = self.score_differential < 0
                self.is_tied = self.score_differential == 0
                self.is_two_minute_drill = self.quarter in [2,4] and self.time_remaining <= 120
                self.is_critical_time = self.quarter == 4 and self.time_remaining <= 480
                self.is_late_game = self.quarter >= 4
            
            def get_time_pressure_level(self):
                if self.is_two_minute_drill:
                    return 'critical'
                elif self.is_critical_time:
                    return 'medium'
                elif self.is_late_game:
                    return 'low'
                else:
                    return 'none'
        
        return MockContext(scenario)
    
    def _get_context_summary(self, context):
        """Get context summary"""
        if contextual_system_available:
            return {
                "time_pressure": context.get_time_pressure_level(),
                "score_situation": "leading" if context.is_leading else "trailing" if context.is_trailing else "tied",
                "critical_time": context.is_critical_time,
                "two_minute_drill": context.is_two_minute_drill,
                "score_differential": context.score_differential
            }
        else:
            return {
                "time_pressure": context.get_time_pressure_level(),
                "score_situation": "leading" if context.is_leading else "trailing" if context.is_trailing else "tied",
                "critical_time": context.is_critical_time,
                "two_minute_drill": context.is_two_minute_drill,
                "score_differential": context.score_differential
            }
    
    def _analyze_fourth_down(self, scenario, archetype, context, config):
        """Analyze 4th down decision"""
        field_pos = scenario["field_position"]
        yards_to_go = scenario["yards_to_go"]
        
        # Field goal range check
        field_goal_range = field_pos >= 65
        field_goal_distance = (100 - field_pos) + 17
        
        # Short yardage check
        short_yardage = yards_to_go <= 3
        
        # Context modifiers
        desperation_mode = context.is_two_minute_drill and context.is_trailing
        protect_lead = context.is_leading and context.is_critical_time
        
        reasoning = []
        confidence = config["base_aggression"]
        
        # Desperation mode override
        if desperation_mode:
            decision = "go_for_it"
            reasoning.append("Desperation mode - must be aggressive")
            confidence = 0.9
        
        # Protect lead mode - be conservative
        elif protect_lead and not short_yardage:
            if field_goal_range:
                decision = "field_goal"
                reasoning.append("Protecting lead, take the points")
            else:
                decision = "punt"
                reasoning.append("Protecting lead, pin them deep")
            confidence = 0.8
        
        # Short yardage situations
        elif short_yardage and field_pos >= 50:
            aggression_threshold = config["fourth_down_threshold"]
            if archetype in ["aggressive", "innovative"] or random.random() < aggression_threshold:
                decision = "go_for_it"
                reasoning.append(f"{archetype} archetype favors short yardage attempts")
                confidence = config["fourth_down_threshold"]
            else:
                decision = "field_goal" if field_goal_range else "punt"
                reasoning.append("Short yardage but playing it safe")
                confidence = 0.7
        
        # Field goal situations
        elif field_goal_range:
            # Distance-based success rate estimation
            success_rate = max(0.5, 0.95 - (field_goal_distance - 25) * 0.02)
            
            if success_rate >= 0.75 or archetype in ["conservative", "traditional"]:
                decision = "field_goal"
                reasoning.append(f"High success rate field goal ({success_rate:.1%})")
                confidence = success_rate
            else:
                decision = "go_for_it"
                reasoning.append(f"Low success rate FG, {archetype} goes for it")
                confidence = config["risk_tolerance"]
        
        # Punt situations
        else:
            if archetype in ["aggressive", "innovative"] and yards_to_go <= 5:
                decision = "go_for_it"
                reasoning.append(f"{archetype} archetype takes risks")
                confidence = config["risk_tolerance"] * 0.7
            else:
                decision = "punt"
                reasoning.append("Too far for field goal, punt it away")
                confidence = 0.8
        
        return {
            "primary_decision": decision,
            "reasoning": reasoning,
            "confidence": confidence,
            "field_goal_distance": field_goal_distance if field_goal_range else None
        }
    
    def _analyze_two_point_conversion(self, scenario, archetype, context, config):
        """Analyze two-point conversion decision"""
        score_diff = context.score_differential
        base_rate = config["two_point_base_rate"]
        
        reasoning = []
        
        # Mandatory situations
        if score_diff == -8:  # Down by 8, need 2PT to tie with FG
            decision = "two_point"
            reasoning.append("Must go for 2 to stay alive")
            confidence = 0.95
        elif score_diff == -1 and context.is_critical_time:  # Down by 1, go for lead
            if archetype in ["aggressive", "innovative", "air_raid"]:
                decision = "two_point"  
                reasoning.append(f"{archetype} archetype goes for the lead")
                confidence = 0.8
            else:
                decision = "extra_point"
                reasoning.append("Conservative, take the tie")
                confidence = 0.7
        elif abs(score_diff) >= 21:  # Garbage time
            decision = "extra_point"
            reasoning.append("Garbage time, just take the point")
            confidence = 0.9
        else:
            # Use base archetype rates with context modifiers
            attempt_rate = base_rate
            
            # Time pressure multipliers
            if context.get_time_pressure_level() == 'critical':
                attempt_rate *= 2.0
            elif context.get_time_pressure_level() == 'high':
                attempt_rate *= 1.5
            
            if random.random() < attempt_rate:
                decision = "two_point"
                reasoning.append(f"{archetype} archetype base rate ({base_rate:.1%})")
                confidence = attempt_rate
            else:
                decision = "extra_point"
                reasoning.append("Standard situation, kick the XP")
                confidence = 1.0 - attempt_rate
        
        return {
            "primary_decision": decision,
            "reasoning": reasoning,
            "confidence": confidence,
            "base_attempt_rate": base_rate
        }
    
    def _analyze_regular_play_call(self, scenario, archetype, context, config):
        """Analyze regular down play calling"""
        down = scenario["down"]
        yards_to_go = scenario["yards_to_go"]
        field_pos = scenario["field_position"]
        
        play_prefs = config["play_preferences"]
        reasoning = []
        
        # Context adjustments
        base_pass_rate = play_prefs["pass"]
        
        # Down and distance adjustments
        if down == 3 and yards_to_go >= 7:
            base_pass_rate = 0.8  # 3rd and long = pass
            reasoning.append("3rd and long favors passing")
        elif down <= 2 and yards_to_go <= 3:
            base_pass_rate = 0.3  # Short yardage favors running
            reasoning.append("Short yardage favors running")
        elif context.is_two_minute_drill:
            base_pass_rate = 0.75  # Two minute drill = more passing
            reasoning.append("Two-minute drill increases passing")
        elif context.is_leading and context.is_critical_time:
            base_pass_rate = 0.35  # Protect lead = more running
            reasoning.append("Protecting lead with ground game")
        
        # Red zone adjustments
        if field_pos >= 80:
            if archetype in ["run_heavy", "traditional"]:
                base_pass_rate *= 0.7
                reasoning.append("Ground and pound in red zone")
            else:
                reasoning.append("Red zone situation")
        
        # Make decision
        if random.random() < base_pass_rate:
            decision = "pass"
            confidence = base_pass_rate
        else:
            decision = "run"
            confidence = 1.0 - base_pass_rate
        
        reasoning.append(f"{archetype} base preference: {play_prefs['pass']:.1%} pass")
        
        return {
            "primary_decision": decision,
            "reasoning": reasoning,
            "confidence": confidence,
            "adjusted_pass_rate": base_pass_rate
        }

def create_demo_scenarios():
    """Create 25 enhanced demo scenarios with proper context"""
    return [
        # Critical game situations
        {"name": "Game-winning drive", "quarter": 4, "time_remaining": 120, 
         "home_score": 14, "away_score": 17, "field_position": 75, "down": 3, "yards_to_go": 8,
         "description": "Down by 3, 2 mins left, red zone"},
        
        {"name": "Protect the lead", "quarter": 4, "time_remaining": 480,
         "home_score": 24, "away_score": 17, "field_position": 35, "down": 2, "yards_to_go": 6,
         "description": "Leading by 7, 8 mins left, control game"},
         
        {"name": "Two-minute drill", "quarter": 4, "time_remaining": 90,
         "home_score": 21, "away_score": 21, "field_position": 45, "down": 1, "yards_to_go": 10,
         "description": "Tied, 1:30 left, drive for win"},
         
        {"name": "Desperation 4th down", "quarter": 4, "time_remaining": 45,
         "home_score": 10, "away_score": 17, "field_position": 25, "down": 4, "yards_to_go": 12,
         "description": "Down 7, 45 secs, long 4th down"},
         
        {"name": "Goal line stand", "quarter": 4, "time_remaining": 180,
         "home_score": 14, "away_score": 13, "field_position": 97, "down": 3, "yards_to_go": 2,
         "description": "Leading by 1, goal line, 3 mins left"},
        
        # 4th down scenarios
        {"name": "Short yardage gamble", "quarter": 3, "time_remaining": 420,
         "home_score": 14, "away_score": 14, "field_position": 55, "down": 4, "yards_to_go": 1,
         "description": "Tied game, 4th & 1, opponent territory"},
         
        {"name": "Field goal decision", "quarter": 4, "time_remaining": 300,
         "home_score": 17, "away_score": 20, "field_position": 72, "down": 4, "yards_to_go": 8,
         "description": "Down 3, 4th & 8, 35-yard FG"},
         
        {"name": "Midfield punt/go", "quarter": 2, "time_remaining": 180,
         "home_score": 7, "away_score": 10, "field_position": 42, "down": 4, "yards_to_go": 6,
         "description": "Down 3, 2nd quarter, 4th & 6"},
         
        {"name": "Red zone 4th down", "quarter": 4, "time_remaining": 600,
         "home_score": 21, "away_score": 14, "field_position": 88, "down": 4, "yards_to_go": 3,
         "description": "Leading by 7, red zone, 4th & 3"},
         
        {"name": "Own territory risk", "quarter": 3, "time_remaining": 720,
         "home_score": 10, "away_score": 7, "field_position": 28, "down": 4, "yards_to_go": 5,
         "description": "Leading by 3, own territory"},
        
        # Two-point scenarios  
        {"name": "Must go for 2", "quarter": 4, "time_remaining": 180,
         "home_score": 20, "away_score": 22, "field_position": 5, "down": 1, "yards_to_go": 5,
         "description": "Down by 2 after TD", "is_touchdown_scenario": True},
         
        {"name": "Go for lead", "quarter": 4, "time_remaining": 420,
         "home_score": 21, "away_score": 20, "field_position": 3, "down": 1, "yards_to_go": 3,
         "description": "Leading by 1 after TD", "is_touchdown_scenario": True},
         
        {"name": "Garbage time TD", "quarter": 4, "time_remaining": 90,
         "home_score": 35, "away_score": 14, "field_position": 8, "down": 2, "yards_to_go": 8,
         "description": "Big lead, late TD", "is_touchdown_scenario": True},
         
        {"name": "Comeback 2PT", "quarter": 4, "time_remaining": 240,
         "home_score": 14, "away_score": 21, "field_position": 4, "down": 1, "yards_to_go": 4,
         "description": "Down 7 after TD", "is_touchdown_scenario": True},
         
        {"name": "Take the lead 2PT", "quarter": 4, "time_remaining": 360,
         "home_score": 27, "away_score": 28, "field_position": 6, "down": 3, "yards_to_go": 6,
         "description": "Down 1 after TD", "is_touchdown_scenario": True},
        
        # Clock management
        {"name": "End of half FG", "quarter": 2, "time_remaining": 35,
         "home_score": 14, "away_score": 10, "field_position": 68, "down": 2, "yards_to_go": 12,
         "description": "Leading, end of half, FG range"},
         
        {"name": "Milk the clock", "quarter": 4, "time_remaining": 240,
         "home_score": 28, "away_score": 21, "field_position": 45, "down": 1, "yards_to_go": 10,
         "description": "Leading by 7, 4 mins left"},
         
        {"name": "Hurry up offense", "quarter": 4, "time_remaining": 180,
         "home_score": 17, "away_score": 24, "field_position": 60, "down": 2, "yards_to_go": 8,
         "description": "Down 7, need quick score"},
         
        {"name": "Conservative drive", "quarter": 4, "time_remaining": 420,
         "home_score": 21, "away_score": 17, "field_position": 25, "down": 1, "yards_to_go": 10,
         "description": "Leading by 4, control game"},
         
        {"name": "Prevent defense", "quarter": 4, "time_remaining": 90,
         "home_score": 24, "away_score": 17, "field_position": 80, "down": 3, "yards_to_go": 15,
         "description": "Leading, opponent desperation"},
        
        # Situational
        {"name": "Weather game", "quarter": 3, "time_remaining": 540,
         "home_score": 10, "away_score": 13, "field_position": 35, "down": 3, "yards_to_go": 7,
         "description": "Down 3, bad weather, 3rd & 7"},
         
        {"name": "Rivalry game", "quarter": 4, "time_remaining": 300,
         "home_score": 21, "away_score": 21, "field_position": 50, "down": 3, "yards_to_go": 4,
         "description": "Tied rivalry, 5 mins left"},
         
        {"name": "Playoff implications", "quarter": 4, "time_remaining": 600,
         "home_score": 14, "away_score": 17, "field_position": 30, "down": 2, "yards_to_go": 12,
         "description": "Must-win, down 3, 10 mins"},
         
        {"name": "Blowout management", "quarter": 4, "time_remaining": 480,
         "home_score": 42, "away_score": 14, "field_position": 40, "down": 2, "yards_to_go": 5,
         "description": "Big lead, manage responsibly"},
         
        {"name": "Opening drive", "quarter": 1, "time_remaining": 720,
         "home_score": 0, "away_score": 0, "field_position": 25, "down": 3, "yards_to_go": 8,
         "description": "Set the tone, 3rd & 8"}
    ]

def run_enhanced_demo():
    """Run the enhanced contextual decision demo"""
    print("=" * 80)
    print("ENHANCED CONTEXTUAL DECISION MAKING DEMO")
    print("=" * 80)
    print("Realistic archetype-based decisions using contextual intelligence")
    print()
    
    engine = EnhancedContextualDecisionEngine()
    scenarios = create_demo_scenarios()
    archetypes = ["aggressive", "conservative", "balanced", "innovative", 
                  "traditional", "air_raid", "run_heavy", "west_coast"]
    
    # Sample 10 interesting scenarios for the demo
    demo_scenarios = scenarios[:10]
    
    for i, scenario in enumerate(demo_scenarios, 1):
        print(f"\n{'='*60}")
        print(f"SCENARIO {i}: {scenario['name'].upper()}")
        print(f"{'='*60}")
        
        # Scenario description
        score_diff = scenario["home_score"] - scenario["away_score"]
        situation = f"Leading by {score_diff}" if score_diff > 0 else f"Trailing by {abs(score_diff)}" if score_diff < 0 else "Tied"
        time_desc = f"Q{scenario['quarter']} {scenario['time_remaining']//60}:{scenario['time_remaining']%60:02d}"
        field_desc = f"Own {scenario['field_position']}" if scenario['field_position'] < 50 else f"Opp {100-scenario['field_position']}"
        down_desc = f"{scenario['down']} & {scenario['yards_to_go']}"
        
        print(f"Situation: {situation} | {time_desc} | {field_desc} | {down_desc}")
        print(f"Context: {scenario['description']}")
        
        # Analyze each archetype's decision
        archetype_decisions = {}
        for archetype in archetypes:
            analysis = engine.analyze_contextual_decision(scenario, archetype)
            archetype_decisions[archetype] = analysis
        
        # Display decisions grouped by choice
        decision_groups = {}
        for archetype, analysis in archetype_decisions.items():
            decision = analysis["primary_decision"]
            if decision not in decision_groups:
                decision_groups[decision] = []
            decision_groups[decision].append({
                "archetype": archetype,
                "confidence": analysis["confidence"],
                "reasoning": analysis.get("reasoning", [])[:2]  # First 2 reasons
            })
        
        print("\nArchetype Decisions:")
        for decision, group in decision_groups.items():
            archetypes_str = ", ".join([item["archetype"] for item in group])
            avg_confidence = sum(item["confidence"] for item in group) / len(group)
            print(f"  • {decision.replace('_', ' ').title()}: {archetypes_str} (avg confidence: {avg_confidence:.1%})")
            
            # Show reasoning for one archetype
            if group:
                example = group[0]
                if example["reasoning"]:
                    print(f"    Reasoning: {example['reasoning'][0]}")
        
        # Show context factors
        context_sample = list(archetype_decisions.values())[0]["context_factors"]
        print(f"\nContext: {context_sample['time_pressure']} pressure, {context_sample['score_situation']}, "
              f"{'critical time' if context_sample['critical_time'] else 'normal time'}")
    
    print(f"\n{'='*80}")
    print("ENHANCED DEMO COMPLETED")
    print("=" * 80)
    print("✅ This demonstrates sophisticated contextual decision making with:")
    print("  • Realistic archetype-specific tendencies")
    print("  • Context-aware decision modifiers")
    print("  • NFL-accurate situational responses")
    print("  • Confidence-based decision quality")

if __name__ == "__main__":
    run_enhanced_demo()