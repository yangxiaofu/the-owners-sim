import random
from typing import List, Dict, Tuple
from game_engine.simulation.blocking.strategies import RunBlockingStrategy, BlockingContext
from game_engine.simulation.blocking.simulator import BlockingSimulator
from game_engine.simulation.blocking.data_structures import BlockingResult, RunPlayCall, RunResult

class DetailedRunSimulator:
    """Detailed position-by-position run play simulation"""
    
    def __init__(self):
        # Use the new blocking simulator with run blocking strategy
        self.blocking_simulator = BlockingSimulator(RunBlockingStrategy())
        
        # Position strength multipliers for different play types (for RB calculations)
        self.play_type_modifiers = {
            "dive": {"power_bonus": 0, "speed_penalty": 0, "blocking_bonus": 0},
            "power": {"power_bonus": 0.15, "speed_penalty": -0.05, "blocking_bonus": 0.1},
            "sweep": {"power_bonus": -0.1, "speed_penalty": 0.1, "blocking_bonus": -0.05},
            "draw": {"power_bonus": 0, "speed_penalty": 0.05, "blocking_bonus": 0.05},
            "counter": {"power_bonus": 0.05, "speed_penalty": 0, "blocking_bonus": -0.02}
        }
    
    def simulate_run(self, offense: Dict, defense: Dict, play_call: RunPlayCall = None) -> RunResult:
        """Main simulation entry point"""
        
        if play_call is None:
            play_call = RunPlayCall.default_inside_run()
        
        # Step 1: Get relevant players for this play
        blockers, defenders = self._get_run_participants(offense, defense, play_call)
        
        # Step 2: Simulate individual blocking matchups using new blocking system
        blocking_context = BlockingContext.for_run_play(
            play_type=play_call.play_type,
            direction=play_call.direction,
            formation=play_call.formation,
            down=1,  # TODO: Get from game_state when integrated
            yards_to_go=10,  # TODO: Get from game_state when integrated  
            field_position=50  # TODO: Get from game_state when integrated
        )
        
        blocking_results = self.blocking_simulator.simulate_matchups(blockers, defenders, blocking_context)
        
        # Step 3: Calculate RB success vs unblocked defenders
        # TODO: For the running back rating, there will be differnet types of ratings that will impact the running back rating
        """
        The running back could be a power back or a back that is evasive.  
        """
        rb_rating = offense["offense"]["rb_rating"]
        rb_performance = self._simulate_rb_vs_defenders(
            rb_rating, blocking_results, defense, play_call
        )
        
        # Step 4: Calculate final yards and outcome
        yards, outcome = self._calculate_final_result(
            blocking_results, rb_performance, play_call, rb_rating
        )
        
        # Step 5: Generate play breakdown
        breakdown = self._generate_play_breakdown(blocking_results, rb_performance, outcome, yards)
        
        return RunResult(
            outcome=outcome,
            yards_gained=yards,
            blocking_results=blocking_results,
            rb_vs_defenders=rb_performance,
            play_breakdown=breakdown
        )
    
    def _get_run_participants(self, offense: Dict, defense: Dict, play_call: RunPlayCall) -> Tuple[Dict, Dict]:
        """Identify which players are involved in this specific run play"""
        
        # Map offense positions based on your team data structure
        # For now, using aggregate ratings but structured for future expansion
        blockers = {}
        defenders = {}
        # TODO: later we need to be more specific with the ratings. Rush as run block rating, and pass block rating, and not just the overall player rating.

        if play_call.direction == "left":
            blockers = {
                "LT": offense["offense"]["ol_rating"],  # Left tackle crucial
                "LG": offense["offense"]["ol_rating"],  # Left guard 
                "C": offense["offense"]["ol_rating"] * 0.8,  # Center helps
                "TE": offense["offense"]["te_rating"] if "te_rating" in offense["offense"] else 65
            }
            defenders = {
                "LE": defense["defense"]["dl_rating"],
                "DT": defense["defense"]["dl_rating"] * 0.9,
                "LOLB": defense["defense"]["lb_rating"],
                "MLB": defense["defense"]["lb_rating"] * 0.8
            }
            
        elif play_call.direction == "right":
            blockers = {
                "RT": offense["offense"]["ol_rating"],
                "RG": offense["offense"]["ol_rating"], 
                "C": offense["offense"]["ol_rating"] * 0.8,
                "TE": offense["offense"]["te_rating"] if "te_rating" in offense["offense"] else 65
            }
            defenders = {
                "RE": defense["defense"]["dl_rating"],
                "DT": defense["defense"]["dl_rating"] * 0.9,
                "ROLB": defense["defense"]["lb_rating"],
                "MLB": defense["defense"]["lb_rating"] * 0.8
            }
            
        else:  # center
            blockers = {
                "LG": offense["offense"]["ol_rating"],
                "C": offense["offense"]["ol_rating"],
                "RG": offense["offense"]["ol_rating"],
                "FB": 70  # Default fullback rating for lead blocking
            }
            defenders = {
                "NT": defense["defense"]["dl_rating"],
                "DT": defense["defense"]["dl_rating"] * 0.9,
                "MLB": defense["defense"]["lb_rating"],
                "ILB": defense["defense"]["lb_rating"] * 0.9
            }
        
        return blockers, defenders
    
    # Removed _simulate_blocking_matchups - now handled by BlockingSimulator
    
    def _simulate_rb_vs_defenders(self, rb_rating: int, blocking_results: List[BlockingResult], 
                                  defense: Dict, play_call: RunPlayCall) -> Dict:
        """Calculate RB performance against unblocked defenders"""
        
        # Use blocking simulator to get unblocked defenders
        unblocked_defenders = self.blocking_simulator.get_unblocked_defenders(blocking_results)
        
        # Add secondary defenders (safeties, other LBs)
        secondary_threat = defense["defense"]["db_rating"] * 0.7  # Safety run support
        unblocked_defenders.append({
            "position": "SS",
            "rating": secondary_threat,
            "impact": 0.4
        })
        
        # Calculate RB's ability to beat each defender
        rb_modifiers = self.play_type_modifiers.get(play_call.play_type, {})
        adjusted_rb = rb_rating * (1 + rb_modifiers.get("speed_penalty", 0) + rb_modifiers.get("power_bonus", 0))
        
        defender_impacts = []
        total_resistance = 0
        
        for defender in unblocked_defenders:
            # RB vs individual defender
            beat_prob = adjusted_rb / (adjusted_rb + defender["rating"])
            beats_defender = random.random() < beat_prob
            
            if not beats_defender:
                resistance = defender["impact"] * (defender["rating"] / 100)
                total_resistance += resistance
            
            defender_impacts.append({
                "defender": defender["position"],
                "beats_defender": beats_defender,
                "resistance": resistance if not beats_defender else 0
            })
        
        rb_success_rate = max(0, 1 - total_resistance)
        
        return {
            "rb_rating": int(adjusted_rb),
            "unblocked_count": len(unblocked_defenders),
            "success_rate": rb_success_rate,
            "defender_impacts": defender_impacts
        }
    
    def _calculate_final_result(self, blocking_results: List[BlockingResult], 
                               rb_performance: Dict, play_call: RunPlayCall, rb_rating: int) -> Tuple[int, str]:
        """Calculate final yards and outcome"""
        
        # Base yards from blocking
        successful_blocks = sum(1 for r in blocking_results if r.success)
        total_blocks = len(blocking_results)
        blocking_grade = successful_blocks / max(total_blocks, 1)
        
        base_yards = blocking_grade * 4  # Perfect blocking = 4 base yards
        
        # RB contribution
        rb_success = rb_performance["success_rate"]
        rb_yards = rb_success * 6  # RB can add up to 6 yards if beats all defenders
        
        # Play type base values
        play_base = {
            "dive": 2,
            "power": 3,
            "sweep": 1,
            "draw": 2,
            "counter": 2
        }
        
        # Calculate total
        total_yards = (base_yards + rb_yards + play_base.get(play_call.play_type, 2) + 
                      random.randint(-2, 4))  # Random variance
        
        final_yards = max(int(total_yards), -3)  # Minimum -3 yard loss
        
        # Determine special outcomes
        outcome = "gain"
        
        # Touchdown check
        if final_yards >= 20 and rb_rating > 70:
            if random.random() < 0.08:  # 8% chance on big run
                outcome = "touchdown"
        
        # Fumble check (more likely on big losses or hits)
        elif final_yards <= -1:
            fumble_prob = 0.005 + (abs(final_yards) * 0.002)  # Higher chance on bigger loss
            if random.random() < fumble_prob:
                outcome = "fumble"
        
        # Big run check (15+ yards)
        elif final_yards >= 15:
            if blocking_grade > 0.8 and rb_success > 0.7:
                final_yards += random.randint(5, 25)  # Breakaway potential
        
        return final_yards, outcome
    
    def _generate_play_breakdown(self, blocking_results: List[BlockingResult], 
                                rb_performance: Dict, outcome: str, yards: int) -> str:
        """Generate a text description of what happened on the play"""
        
        successful_blocks = sum(1 for r in blocking_results if r.success)
        total_blocks = len(blocking_results)
        
        breakdown_parts = []
        
        # Blocking assessment
        if successful_blocks == total_blocks:
            breakdown_parts.append("Perfect blocking creates a clean hole")
        elif successful_blocks >= total_blocks * 0.7:
            breakdown_parts.append("Good blocking opens up the running lane")
        elif successful_blocks >= total_blocks * 0.4:
            breakdown_parts.append("Mixed blocking results, some defenders break through")
        else:
            breakdown_parts.append("Poor blocking, defenders quickly penetrate")
        
        # RB performance
        rb_success = rb_performance["success_rate"]
        unblocked = rb_performance["unblocked_count"]
        
        if rb_success > 0.8:
            breakdown_parts.append(f"RB shows excellent vision/power, beats {unblocked} defenders")
        elif rb_success > 0.5:
            breakdown_parts.append(f"RB makes a solid effort against {unblocked} defenders")
        else:
            breakdown_parts.append(f"RB struggles against {unblocked} unblocked defenders")
        
        # Final result
        if outcome == "touchdown":
            breakdown_parts.append("BREAKS FREE for the touchdown!")
        elif yards >= 10:
            breakdown_parts.append(f"Good gain of {yards} yards")
        elif yards >= 3:
            breakdown_parts.append(f"Decent gain of {yards} yards")
        elif yards > 0:
            breakdown_parts.append(f"Short gain of {yards} yard{'s' if yards != 1 else ''}")
        elif yards == 0:
            breakdown_parts.append("Stuffed at the line of scrimmage")
        else:
            breakdown_parts.append(f"Tackled for a {abs(yards)} yard loss")
        
        return ". ".join(breakdown_parts) + "."