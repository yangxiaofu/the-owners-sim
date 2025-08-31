import random
from typing import Dict, List, Tuple
from .strategies import BlockingStrategy, BlockingContext
from .data_structures import BlockingResult

class BlockingSimulator:
    """Unified blocking simulator that uses strategy pattern for different blocking types"""
    
    def __init__(self, strategy: BlockingStrategy):
        self.strategy = strategy
    
    def simulate_matchups(self, blockers: Dict[str, int], defenders: Dict[str, int], 
                         context: BlockingContext) -> List[BlockingResult]:
        """
        Simulate blocking matchups using the configured strategy
        
        Args:
            blockers: Dict mapping position -> rating (e.g., {"LT": 80, "LG": 75})
            defenders: Dict mapping position -> rating (e.g., {"DE": 85, "DT": 70})
            context: BlockingContext with play and situation details
            
        Returns:
            List of BlockingResult objects for each matchup
        """
        results = []
        
        # Pair up blockers with defenders
        blocker_assignments = self._assign_blockers_to_defenders(blockers, defenders, context)
        
        for assignment in blocker_assignments:
            blocker_pos = assignment["blocker_position"]
            blocker_rating = assignment["blocker_rating"]
            defender_pos = assignment["defender_position"]  
            defender_rating = assignment["defender_rating"]
            
            # Calculate base probability using strategy
            base_prob = self.strategy.calculate_matchup_probability(
                blocker_rating, defender_rating, blocker_pos, defender_pos, context
            )
            
            # Apply situational modifiers
            final_prob = self.strategy.apply_situation_modifiers(base_prob, blocker_pos, context)
            
            # Add small random variance
            variance = random.uniform(-0.02, 0.02)
            final_prob = max(0.01, min(0.99, final_prob + variance))
            
            # Determine success
            success = random.random() < final_prob
            
            # Calculate impact factor
            impact = self.strategy.get_impact_factor(blocker_pos, defender_pos, success, context)
            
            results.append(BlockingResult(
                blocker_position=blocker_pos,
                blocker_rating=blocker_rating,
                defender_position=defender_pos,
                defender_rating=defender_rating,
                success=success,
                impact_factor=impact
            ))
        
        return results
    
    def _assign_blockers_to_defenders(self, blockers: Dict[str, int], defenders: Dict[str, int],
                                    context: BlockingContext) -> List[Dict]:
        """
        Assign blockers to defenders based on blocking scheme and play type
        
        This is a simplified assignment - in reality, blocking schemes are very complex
        """
        assignments = []
        
        blocker_list = list(blockers.items())
        defender_list = list(defenders.items())
        
        blocking_type = context.blocking_type
        
        if blocking_type == "run_blocking":
            assignments = self._assign_run_blocking(blocker_list, defender_list, context)
        elif blocking_type == "pass_protection":
            assignments = self._assign_pass_protection(blocker_list, defender_list, context)
        else:
            # Default 1-on-1 assignment
            assignments = self._assign_default(blocker_list, defender_list)
        
        return assignments
    
    def _assign_run_blocking(self, blockers: List[Tuple], defenders: List[Tuple], 
                           context: BlockingContext) -> List[Dict]:
        """Assign blockers for run plays based on direction and play type"""
        assignments = []
        
        play_type = context.play_details.get("play_type", "dive")
        direction = context.play_details.get("direction", "center")
        
        # Simplified assignment logic - can be expanded
        for i, (blocker_pos, blocker_rating) in enumerate(blockers):
            if i < len(defenders):
                defender_pos, defender_rating = defenders[i]
                
                # TODO: Implement more sophisticated assignment based on:
                # - Gap responsibilities
                # - Combo blocks (double teams)
                # - Pull blocks for sweeps
                # For now, simple 1-on-1 assignment
                
                assignments.append({
                    "blocker_position": blocker_pos,
                    "blocker_rating": blocker_rating,
                    "defender_position": defender_pos,
                    "defender_rating": defender_rating,
                    "assignment_type": "drive_block"  # Could be "combo", "pull", "cut", etc.
                })
        
        return assignments
    
    def _assign_pass_protection(self, blockers: List[Tuple], defenders: List[Tuple],
                              context: BlockingContext) -> List[Dict]:
        """Assign blockers for pass protection based on protection scheme"""
        assignments = []
        
        protection_scheme = context.play_details.get("protection_scheme", "slide")
        
        # Different protection schemes assign differently
        if protection_scheme == "max_protect":
            # More blockers, RB and TE stay in to block
            assignments = self._assign_max_protect(blockers, defenders)
        elif protection_scheme == "slide":
            # Offensive line slides protection one way
            assignments = self._assign_slide_protection(blockers, defenders, context)
        else:
            # Default protection
            assignments = self._assign_default(blockers, defenders)
        
        return assignments
    
    def _assign_max_protect(self, blockers: List[Tuple], defenders: List[Tuple]) -> List[Dict]:
        """Max protection - keep extra blockers in"""
        assignments = []
        
        # In max protect, we might have 7-8 blockers vs 4-5 rushers
        # Some blockers might not have an assignment (help/hot)
        for i, (blocker_pos, blocker_rating) in enumerate(blockers):
            if i < len(defenders):
                defender_pos, defender_rating = defenders[i]
                assignments.append({
                    "blocker_position": blocker_pos,
                    "blocker_rating": blocker_rating,
                    "defender_position": defender_pos,
                    "defender_rating": defender_rating,
                    "assignment_type": "man_protection"
                })
            else:
                # Extra blocker - assign to help or hot route
                assignments.append({
                    "blocker_position": blocker_pos,
                    "blocker_rating": blocker_rating,
                    "defender_position": "HELP",  # Helping another blocker
                    "defender_rating": 0,  # No direct matchup
                    "assignment_type": "help_protection"
                })
        
        return assignments
    
    def _assign_slide_protection(self, blockers: List[Tuple], defenders: List[Tuple],
                               context: BlockingContext) -> List[Dict]:
        """Slide protection - OL slides one direction"""
        # Simplified slide protection
        return self._assign_default(blockers, defenders)
    
    def _assign_default(self, blockers: List[Tuple], defenders: List[Tuple]) -> List[Dict]:
        """Default 1-on-1 assignment"""
        assignments = []
        
        for i, (blocker_pos, blocker_rating) in enumerate(blockers):
            if i < len(defenders):
                defender_pos, defender_rating = defenders[i]
                assignments.append({
                    "blocker_position": blocker_pos,
                    "blocker_rating": blocker_rating,
                    "defender_position": defender_pos,
                    "defender_rating": defender_rating,
                    "assignment_type": "standard"
                })
        
        return assignments
    
    def calculate_overall_blocking_grade(self, results: List[BlockingResult]) -> float:
        """Calculate an overall blocking performance grade from individual results"""
        if not results:
            return 0.0
        
        total_weighted_success = 0.0
        total_weight = 0.0
        
        for result in results:
            weight = result.impact_factor
            success_value = 1.0 if result.success else 0.0
            
            total_weighted_success += success_value * weight
            total_weight += weight
        
        return total_weighted_success / total_weight if total_weight > 0 else 0.0
    
    def get_unblocked_defenders(self, results: List[BlockingResult]) -> List[Dict]:
        """Get list of defenders who won their matchups (broke free)"""
        unblocked = []
        
        for result in results:
            if not result.success and result.defender_position != "HELP":
                unblocked.append({
                    "position": result.defender_position,
                    "rating": result.defender_rating,
                    "impact": result.impact_factor
                })
        
        return unblocked