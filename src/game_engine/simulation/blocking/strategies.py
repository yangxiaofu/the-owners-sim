import random
from dataclasses import dataclass
from typing import Dict, List, Optional
from abc import ABC, abstractmethod

@dataclass
class BlockingContext:
    """Context information for blocking simulation"""
    blocking_type: str          # "run_blocking", "pass_protection", "screen_blocking"
    play_details: Dict         # play_type, direction, formation, etc.
    situation: Dict            # down, distance, field_position, clock, etc.
    game_factors: Dict = None  # weather, crowd_noise, etc. (future expansion)
    
    @classmethod
    def for_run_play(cls, play_type: str, direction: str, formation: str, 
                     down: int, yards_to_go: int, field_position: int):
        return cls(
            blocking_type="run_blocking",
            play_details={
                "play_type": play_type,
                "direction": direction, 
                "formation": formation
            },
            situation={
                "down": down,
                "yards_to_go": yards_to_go,
                "field_position": field_position
            }
        )
    
    @classmethod  
    def for_pass_play(cls, pass_type: str, protection_scheme: str, formation: str,
                      down: int, yards_to_go: int, field_position: int):
        return cls(
            blocking_type="pass_protection",
            play_details={
                "pass_type": pass_type,           # "quick", "intermediate", "deep"
                "protection_scheme": protection_scheme,  # "max_protect", "slide", "dual_read"
                "formation": formation
            },
            situation={
                "down": down,
                "yards_to_go": yards_to_go,
                "field_position": field_position
            }
        )

class BlockingStrategy(ABC):
    """Abstract base class for different blocking simulation strategies"""
    
    @abstractmethod
    def calculate_matchup_probability(self, blocker_rating: int, defender_rating: int, 
                                    blocker_position: str, defender_position: str,
                                    context: BlockingContext) -> float:
        """Calculate base probability of successful block for this matchup"""
        pass
    
    @abstractmethod
    def apply_situation_modifiers(self, base_prob: float, blocker_position: str,
                                context: BlockingContext) -> float:
        """Apply situational modifiers to the base probability"""
        pass
    
    def get_impact_factor(self, blocker_position: str, defender_position: str, 
                         success: bool, context: BlockingContext) -> float:
        """Calculate how much this block impacts the overall play"""
        # Default implementation - can be overridden
        base_impact = 0.8 if blocker_position in ["LT", "RT", "C"] else 0.6
        if not success:
            base_impact *= 1.5  # Failed blocks have higher negative impact
        return base_impact

class RunBlockingStrategy(BlockingStrategy):
    """Strategy for run blocking simulation"""
    
    def __init__(self):
        # Position importance multipliers for run blocking
        self.position_importance = {
            "LT": 1.0, "LG": 1.0, "C": 1.0, "RG": 1.0, "RT": 1.0,  # OL
            "TE": 0.85, "FB": 0.9, "WR": 0.6  # Other blockers
        }
        
        # Play type modifiers
        self.play_type_modifiers = {
            "dive": {"power_bonus": 0, "technique_bonus": 0.05},
            "power": {"power_bonus": 0.15, "technique_bonus": 0.1},
            "sweep": {"power_bonus": -0.1, "technique_bonus": -0.05, "athleticism_bonus": 0.1},
            "draw": {"power_bonus": 0, "technique_bonus": 0.05, "timing_bonus": 0.1},
            "counter": {"power_bonus": 0.05, "technique_bonus": 0, "athleticism_bonus": 0.05}
        }
    
    def calculate_matchup_probability(self, blocker_rating: int, defender_rating: int,
                                    blocker_position: str, defender_position: str, 
                                    context: BlockingContext) -> float:
        """Calculate run blocking success probability"""
        
        # Base calculation favors blocker slightly in run game
        base_prob = (blocker_rating * 1.1) / ((blocker_rating * 1.1) + defender_rating)
        
        # Position-specific adjustments
        if blocker_position in ["LG", "RG", "C"] and context.play_details.get("play_type") == "power":
            base_prob *= 1.1  # Guards and center crucial in power runs
        elif blocker_position in ["LT", "RT"] and context.play_details.get("play_type") == "sweep":
            base_prob *= 1.05  # Tackles important for sweep blocking
        
        # Direction-based adjustments
        direction = context.play_details.get("direction", "center")
        if direction == "left" and blocker_position in ["LT", "LG"]:
            base_prob *= 1.05
        elif direction == "right" and blocker_position in ["RT", "RG"]:
            base_prob *= 1.05
        
        return min(0.95, base_prob)  # Cap at 95% success
    
    def apply_situation_modifiers(self, base_prob: float, blocker_position: str,
                                context: BlockingContext) -> float:
        """Apply situational modifiers for run blocking"""
        
        modified_prob = base_prob
        situation = context.situation
        
        # Short yardage situations favor run blocking
        yards_to_go = situation.get("yards_to_go", 10)
        if yards_to_go <= 2:
            modified_prob *= 1.1  # 10% bonus for short yardage
        elif yards_to_go <= 5:
            modified_prob *= 1.05  # 5% bonus for medium short
        
        # Goal line situations (inside 10-yard line)
        field_position = situation.get("field_position", 50)
        if field_position >= 90:  # Inside 10-yard line
            modified_prob *= 1.08  # Condensed field helps blockers
        
        # Down and distance
        down = situation.get("down", 1)
        if down == 3 and yards_to_go <= 3:
            modified_prob *= 1.05  # 3rd and short determination
        elif down == 4:
            modified_prob *= 1.1   # 4th down desperation
        
        return min(0.98, modified_prob)  # Cap at 98%
    
    def get_impact_factor(self, blocker_position: str, defender_position: str,
                         success: bool, context: BlockingContext) -> float:
        """Calculate impact factor for run blocking"""
        
        # Base impact depends on position importance
        base_impact = self.position_importance.get(blocker_position, 0.5)
        
        # Play-specific adjustments
        play_type = context.play_details.get("play_type", "dive")
        direction = context.play_details.get("direction", "center")
        
        # Key positions for specific plays get higher impact
        if play_type == "power" and blocker_position in ["LG", "RG", "C", "FB"]:
            base_impact *= 1.2
        elif play_type == "sweep" and blocker_position in ["LT", "RT"]:
            base_impact *= 1.15
        elif direction == "left" and blocker_position in ["LT", "LG"]:
            base_impact *= 1.1
        elif direction == "right" and blocker_position in ["RT", "RG"]:
            base_impact *= 1.1
        
        # Failed blocks have amplified negative impact
        if not success:
            base_impact *= 1.8
        
        return min(1.0, base_impact)

class PassBlockingStrategy(BlockingStrategy):
    """Strategy for pass protection simulation"""
    
    def __init__(self):
        # Pass protection is harder - defenders have advantage
        self.protection_schemes = {
            "max_protect": {"success_bonus": 0.15, "time_bonus": 0.2},
            "slide": {"success_bonus": 0.05, "time_bonus": 0.1},
            "dual_read": {"success_bonus": -0.05, "time_bonus": -0.1},
            "sprint_out": {"success_bonus": 0.1, "time_bonus": 0.05}
        }
        
        self.pass_types = {
            "quick": {"time_required": 1.5, "difficulty_modifier": 0.15},    # Easier to block
            "intermediate": {"time_required": 3.0, "difficulty_modifier": 0}, # Standard
            "deep": {"time_required": 5.0, "difficulty_modifier": -0.1}      # Harder to block
        }
    
    def calculate_matchup_probability(self, blocker_rating: int, defender_rating: int,
                                    blocker_position: str, defender_position: str,
                                    context: BlockingContext) -> float:
        """Calculate pass protection success probability"""
        
        # Pass blocking favors pass rushers more than run blocking
        base_prob = blocker_rating / (blocker_rating + defender_rating * 1.3)
        
        # Pass type adjustments
        pass_type = context.play_details.get("pass_type", "intermediate")
        if pass_type in self.pass_types:
            base_prob += self.pass_types[pass_type]["difficulty_modifier"]
        
        # Protection scheme adjustments  
        scheme = context.play_details.get("protection_scheme", "slide")
        if scheme in self.protection_schemes:
            base_prob += self.protection_schemes[scheme]["success_bonus"]
        
        # Position-specific adjustments (tackles face edge rushers more)
        if blocker_position in ["LT", "RT"] and defender_position in ["DE", "OLB"]:
            base_prob *= 0.95  # Edge rush is challenging
        elif blocker_position in ["LG", "RG", "C"] and defender_position in ["DT", "NT"]:
            base_prob *= 1.02  # Interior pass pro slight advantage
        
        return max(0.1, min(0.9, base_prob))  # Cap between 10% and 90%
    
    def apply_situation_modifiers(self, base_prob: float, blocker_position: str,
                                context: BlockingContext) -> float:
        """Apply situational modifiers for pass protection"""
        
        modified_prob = base_prob
        situation = context.situation
        
        # Passing situations (3rd and long) are harder to block
        down = situation.get("down", 1)
        yards_to_go = situation.get("yards_to_go", 10)
        
        if down == 3 and yards_to_go >= 8:
            modified_prob *= 0.9   # 3rd and long - defense pins ears back
        elif down == 3 and yards_to_go >= 15:
            modified_prob *= 0.85  # Obvious passing down
        
        # Two-minute drill / hurry-up situations
        # TODO: Add clock-based modifiers when game state includes clock
        
        # Field position (backed up = harder to protect)
        field_position = situation.get("field_position", 50)
        if field_position <= 20:  # Own 20-yard line or closer
            modified_prob *= 0.93  # Less room to step up in pocket
        
        return max(0.05, min(0.95, modified_prob))
    
    def get_impact_factor(self, blocker_position: str, defender_position: str,
                         success: bool, context: BlockingContext) -> float:
        """Calculate impact factor for pass protection"""
        
        # Tackles are most critical in pass pro (protect QB's blind side)
        position_impact = {
            "LT": 1.0,   # Left tackle most important
            "RT": 0.9,   # Right tackle
            "LG": 0.7,   # Guards
            "RG": 0.7,
            "C": 0.8,    # Center important for communication
            "TE": 0.6,   # Tight end
            "RB": 0.5    # Running back in protection
        }
        
        base_impact = position_impact.get(blocker_position, 0.5)
        
        # Pass type affects importance
        pass_type = context.play_details.get("pass_type", "intermediate")
        if pass_type == "deep":
            base_impact *= 1.3  # All blocks more critical on deep passes
        elif pass_type == "quick":
            base_impact *= 0.8  # Less critical on quick passes
        
        # Failed pass protection is devastating
        if not success:
            base_impact *= 2.0  # Sacks/pressures hurt much more than failed run blocks
        
        return min(1.5, base_impact)  # Allow higher impact for pass pro failures