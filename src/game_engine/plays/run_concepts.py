from dataclasses import dataclass
from typing import Dict, List, Optional
from enum import Enum
import random
from ...database.models.players.positions import RunningBack, OffensiveLineman, DefensiveLineman, Linebacker
from ..field.field_state import FieldState


class RunConceptType(Enum):
    ZONE = "zone"           # Zone blocking schemes
    GAP = "gap"             # Gap/power blocking schemes  
    OPTION = "option"       # Option plays
    DRAW = "draw"           # Draw plays


@dataclass
class RunConcept:
    """Represents a specific run concept with its characteristics"""
    name: str
    concept_type: RunConceptType
    target_gap: str         # A, B, C gap or "variable"
    blocking_scheme: str    # "zone", "gap", "combo", "reach"
    rb_technique: str       # "one_cut", "patient", "hit_gap", "bounce"
    success_factors: List[str]  # Key attributes for success
    
    # Situational preferences
    preferred_down: List[int] = None        # [1, 2] = 1st and 2nd down
    preferred_distance: str = "any"         # "short", "medium", "long", "any"
    preferred_field_position: str = "any"   # "goal_line", "red_zone", "midfield", "any"
    
    def is_suitable_for_situation(self, field_state: FieldState) -> bool:
        """Check if this concept is suitable for the current game situation"""
        
        # Check down preference
        if self.preferred_down and field_state.down not in self.preferred_down:
            return False
            
        # Check distance preference
        if self.preferred_distance != "any":
            if self.preferred_distance == "short" and field_state.yards_to_go > 3:
                return False
            elif self.preferred_distance == "medium" and not 4 <= field_state.yards_to_go <= 8:
                return False
            elif self.preferred_distance == "long" and field_state.yards_to_go < 8:
                return False
                
        # Check field position preference
        if self.preferred_field_position != "any":
            if self.preferred_field_position == "goal_line" and not field_state.is_goal_line():
                return False
            elif self.preferred_field_position == "red_zone" and field_state.field_position < 80:
                return False
                
        return True


# Define the core run concepts
class RunConceptLibrary:
    """Library of all available run concepts"""
    
    @staticmethod
    def get_all_concepts() -> List[RunConcept]:
        """Get all available run concepts"""
        return [
            # Inside Zone - Patient runner, OL combo blocks, RB finds the hole
            RunConcept(
                name="Inside Zone",
                concept_type=RunConceptType.ZONE,
                target_gap="variable",
                blocking_scheme="zone",
                rb_technique="one_cut",
                success_factors=["vision", "agility", "ol_mobility", "dl_gap_discipline"],
                preferred_down=[1, 2],
                preferred_distance="any"
            ),
            
            # Outside Zone - Speed to the edge, reach blocks
            RunConcept(
                name="Outside Zone", 
                concept_type=RunConceptType.ZONE,
                target_gap="C",
                blocking_scheme="reach",
                rb_technique="bounce",
                success_factors=["speed", "agility", "ol_mobility", "lb_pursuit"],
                preferred_down=[1, 2, 3],
                preferred_distance="medium"
            ),
            
            # Power O - Lead blocker, pulling guard, gap scheme
            RunConcept(
                name="Power O",
                concept_type=RunConceptType.GAP,
                target_gap="B",
                blocking_scheme="gap",
                rb_technique="hit_gap",
                success_factors=["power", "strength", "ol_power_blocking", "dl_run_defense"],
                preferred_down=[3, 4],
                preferred_distance="short",
                preferred_field_position="goal_line"
            ),
            
            # Draw Play - QB sells pass, RB delay
            RunConcept(
                name="Draw",
                concept_type=RunConceptType.DRAW,
                target_gap="A",
                blocking_scheme="zone", 
                rb_technique="patient",
                success_factors=["vision", "patience", "dl_pass_rushing", "lb_coverage"],
                preferred_down=[2, 3],
                preferred_distance="long"
            ),
            
            # Dive - Quick hit up the gut
            RunConcept(
                name="Dive",
                concept_type=RunConceptType.GAP,
                target_gap="A",
                blocking_scheme="gap",
                rb_technique="hit_gap",
                success_factors=["power", "acceleration", "ol_drive_blocking", "dl_gap_control"],
                preferred_down=[3, 4],
                preferred_distance="short"
            ),
            
            # Counter - Misdirection, pulling guards
            RunConcept(
                name="Counter",
                concept_type=RunConceptType.GAP,
                target_gap="B",
                blocking_scheme="gap",
                rb_technique="patient",
                success_factors=["vision", "agility", "ol_mobility", "lb_discipline"],
                preferred_down=[1, 2],
                preferred_distance="medium"
            ),
            
            # Sweep - Wide run to sideline
            RunConcept(
                name="Sweep",
                concept_type=RunConceptType.GAP,
                target_gap="outside",
                blocking_scheme="gap",
                rb_technique="bounce",
                success_factors=["speed", "elusiveness", "ol_mobility", "lb_pursuit"],
                preferred_down=[1, 2],
                preferred_distance="any"
            )
        ]
    
    @staticmethod
    def select_concept_for_situation(field_state: FieldState, formation: str, 
                                   rb_style: str = "balanced") -> RunConcept:
        """Select the best run concept for the current situation"""
        
        # Get all concepts that are suitable for this situation
        all_concepts = RunConceptLibrary.get_all_concepts()
        suitable_concepts = [concept for concept in all_concepts 
                           if concept.is_suitable_for_situation(field_state)]
        
        if not suitable_concepts:
            # Fallback to inside zone if no concepts match
            suitable_concepts = [concept for concept in all_concepts 
                               if concept.name == "Inside Zone"]
        
        # Apply formation preferences
        formation_preferences = {
            "goal_line": ["Power O", "Dive"],
            "i_formation": ["Power O", "Inside Zone", "Counter"], 
            "singleback": ["Inside Zone", "Outside Zone", "Draw"],
            "shotgun": ["Draw", "Inside Zone"],
            "shotgun_spread": ["Draw"]
        }
        
        if formation in formation_preferences:
            preferred_names = formation_preferences[formation]
            preferred_concepts = [c for c in suitable_concepts if c.name in preferred_names]
            if preferred_concepts:
                suitable_concepts = preferred_concepts
        
        # Apply RB style preferences
        rb_preferences = {
            "power": ["Power O", "Dive", "Inside Zone"],
            "outside": ["Outside Zone", "Sweep", "Counter"],
            "zone": ["Inside Zone", "Outside Zone", "Draw"],
            "balanced": []  # No specific preference
        }
        
        if rb_style in rb_preferences and rb_preferences[rb_style]:
            style_preferred = [c for c in suitable_concepts if c.name in rb_preferences[rb_style]]
            if style_preferred:
                suitable_concepts = style_preferred
        
        # Select randomly from remaining suitable concepts
        return random.choice(suitable_concepts)


class RunConceptExecutor:
    """Executes run concepts and calculates results"""
    
    @staticmethod
    def execute_concept(concept: RunConcept, rb: RunningBack, ol_players: List[OffensiveLineman],
                       dl_players: List[DefensiveLineman], lb_players: List[Linebacker],
                       field_state: FieldState) -> Dict:
        """
        Execute a run concept and return detailed results
        
        Returns:
            Dict containing:
            - yards_gained: int
            - outcome: str ("gain", "touchdown", "fumble", "safety") 
            - success_factors: Dict of factor contributions
            - play_description: str
        """
        
        # Calculate concept-specific success probability
        concept_success = RunConceptExecutor._calculate_concept_success(
            concept, rb, ol_players, dl_players, lb_players
        )
        
        # Base yards calculation
        base_yards = RunConceptExecutor._calculate_base_yards(concept, concept_success)
        
        # Apply situational modifiers
        final_yards = RunConceptExecutor._apply_situational_modifiers(
            base_yards, concept, field_state
        )
        
        # Determine outcome
        outcome = RunConceptExecutor._determine_outcome(final_yards, concept, rb, field_state)
        
        # Generate play description
        play_description = RunConceptExecutor._generate_play_description(
            concept, rb, final_yards, outcome
        )
        
        return {
            'yards_gained': final_yards,
            'outcome': outcome,
            'concept_name': concept.name,
            'success_factors': concept_success,
            'play_description': play_description,
            'target_gap': concept.target_gap,
            'rb_technique': concept.rb_technique
        }
    
    @staticmethod
    def _calculate_concept_success(concept: RunConcept, rb: RunningBack, 
                                 ol_players: List[OffensiveLineman],
                                 dl_players: List[DefensiveLineman], 
                                 lb_players: List[Linebacker]) -> Dict:
        """Calculate success factors for this specific concept"""
        
        success_factors = {}
        
        # RB attributes
        if "vision" in concept.success_factors:
            success_factors["rb_vision"] = rb.get_effective_attribute("vision") / 100
        if "power" in concept.success_factors:
            success_factors["rb_power"] = rb.get_effective_attribute("power") / 100
        if "speed" in concept.success_factors:
            success_factors["rb_speed"] = rb.get_effective_attribute("speed") / 100
        if "agility" in concept.success_factors:
            success_factors["rb_agility"] = rb.get_effective_attribute("agility") / 100
        if "elusiveness" in concept.success_factors:
            success_factors["rb_elusiveness"] = rb.get_effective_attribute("elusiveness") / 100
            
        # OL attributes
        if ol_players:
            if "ol_mobility" in concept.success_factors:
                avg_mobility = sum(ol.get_effective_attribute("mobility") for ol in ol_players) / len(ol_players)
                success_factors["ol_mobility"] = avg_mobility / 100
                
            if "ol_power_blocking" in concept.success_factors:
                avg_power = sum(ol.power_blocking_rating for ol in ol_players) / len(ol_players)
                success_factors["ol_power_blocking"] = avg_power / 100
                
            if "ol_drive_blocking" in concept.success_factors:
                avg_run = sum(ol.get_effective_attribute("run_blocking") for ol in ol_players) / len(ol_players)
                success_factors["ol_drive_blocking"] = avg_run / 100
        
        # DL resistance
        if dl_players:
            if "dl_gap_discipline" in concept.success_factors:
                avg_gap = sum(dl.get_effective_attribute("gap_discipline") for dl in dl_players) / len(dl_players)
                success_factors["dl_gap_discipline"] = 1 - (avg_gap / 100)  # Inverse - bad for offense
                
            if "dl_run_defense" in concept.success_factors:
                avg_run_def = sum(dl.run_stopping_rating for dl in dl_players) / len(dl_players)
                success_factors["dl_run_defense"] = 1 - (avg_run_def / 100)
                
            if "dl_pass_rushing" in concept.success_factors:
                avg_rush = sum(dl.get_effective_attribute("pass_rushing") for dl in dl_players) / len(dl_players)
                success_factors["dl_pass_rushing"] = avg_rush / 100  # Good for draw plays
        
        # LB factors
        if lb_players:
            if "lb_pursuit" in concept.success_factors:
                avg_pursuit = sum(lb.get_effective_attribute("pursuit") for lb in lb_players) / len(lb_players)
                success_factors["lb_pursuit"] = 1 - (avg_pursuit / 100)  # Inverse
                
            if "lb_discipline" in concept.success_factors:
                avg_discipline = sum(lb.get_effective_attribute("instincts") for lb in lb_players) / len(lb_players)
                success_factors["lb_discipline"] = 1 - (avg_discipline / 100)  # Inverse
                
            if "lb_coverage" in concept.success_factors:
                avg_coverage = sum(lb.get_effective_attribute("coverage") for lb in lb_players) / len(lb_players)
                success_factors["lb_coverage"] = avg_coverage / 100  # Good for draws (LBs in coverage)
        
        return success_factors
    
    @staticmethod
    def _calculate_base_yards(concept: RunConcept, success_factors: Dict) -> int:
        """Calculate base yards for the concept"""
        
        # Calculate overall success probability
        if success_factors:
            success_prob = sum(success_factors.values()) / len(success_factors)
        else:
            success_prob = 0.5  # Default
            
        # Concept-specific yard ranges
        concept_ranges = {
            "Inside Zone": (1, 8, 15),      # min, typical_max, breakaway_max
            "Outside Zone": (0, 12, 25),    # More variance
            "Power O": (2, 6, 12),          # Consistent but short
            "Draw": (-1, 10, 20),           # Can be negative or big
            "Dive": (1, 4, 8),              # Short but reliable
            "Counter": (0, 8, 18),          # Boom or bust
            "Sweep": (-2, 15, 30)           # High variance
        }
        
        min_yards, typical_max, breakaway_max = concept_ranges.get(concept.name, (0, 5, 15))
        
        if success_prob > 0.7:
            # Very successful - chance for big gain
            if random.random() < 0.15:  # 15% chance of breakaway
                return random.randint(typical_max, breakaway_max)
            else:
                return random.randint((min_yards + typical_max) // 2, typical_max)
        elif success_prob > 0.4:
            # Moderate success
            return random.randint(min_yards, typical_max)
        else:
            # Poor execution
            return random.randint(min_yards - 2, min_yards + 2)
    
    @staticmethod
    def _apply_situational_modifiers(base_yards: int, concept: RunConcept, 
                                   field_state: FieldState) -> int:
        """Apply situational modifiers to the base yards"""
        modified_yards = base_yards
        
        # Goal line modifier (harder to run in tight space)
        if field_state.is_goal_line() and concept.name not in ["Power O", "Dive"]:
            modified_yards = int(modified_yards * 0.7)
        
        # Short yardage modifier (defense expecting run)
        if field_state.is_short_yardage() and concept.concept_type != RunConceptType.DRAW:
            modified_yards = int(modified_yards * 0.8)
        
        # Long yardage modifier (defense not expecting run)
        if field_state.yards_to_go >= 10 and concept.concept_type == RunConceptType.DRAW:
            modified_yards = int(modified_yards * 1.3)
        
        return max(-5, modified_yards)  # Minimum -5 yard loss
    
    @staticmethod
    def _determine_outcome(yards: int, concept: RunConcept, rb: RunningBack, 
                         field_state: FieldState) -> str:
        """Determine the play outcome based on yards gained"""
        
        # Check for touchdown
        if yards >= (100 - field_state.field_position):
            return "touchdown"
        
        # Check for safety  
        if field_state.field_position + yards <= 0:
            return "safety"
        
        # Check for fumble (higher chance on big hits in power concepts)
        fumble_base_chance = 0.01  # 1% base chance
        if concept.concept_type == RunConceptType.GAP and yards < 2:
            fumble_base_chance = 0.025  # Higher chance on stuffed power runs
        
        fumble_chance = fumble_base_chance * (1 - rb.get_effective_attribute("strength") / 200)
        if random.random() < fumble_chance:
            return "fumble"
        
        # Normal gain
        return "gain"
    
    @staticmethod
    def _generate_play_description(concept: RunConcept, rb: RunningBack, 
                                 yards: int, outcome: str) -> str:
        """Generate a descriptive text for the play"""
        
        rb_name = rb.name if rb else "RB"
        
        concept_descriptions = {
            "Inside Zone": f"{rb_name} takes the handoff and finds a seam up the middle",
            "Outside Zone": f"{rb_name} stretches the play to the outside",
            "Power O": f"{rb_name} follows the lead blocker through the gap",
            "Draw": f"{rb_name} takes the delayed handoff after the QB sell",
            "Dive": f"{rb_name} hits the A-gap quickly",
            "Counter": f"{rb_name} takes the counter handoff with misdirection",
            "Sweep": f"{rb_name} takes the sweep toward the sideline"
        }
        
        base_desc = concept_descriptions.get(concept.name, f"{rb_name} carries the ball")
        
        # Add outcome-specific details
        if outcome == "touchdown":
            return f"{base_desc} and breaks free for a touchdown!"
        elif outcome == "fumble":
            return f"{base_desc} but fumbles the ball!"
        elif yards >= 15:
            return f"{base_desc} and breaks away for a big gain!"
        elif yards <= 0:
            return f"{base_desc} but is stopped behind the line."
        else:
            return f"{base_desc} for {yards} yards."