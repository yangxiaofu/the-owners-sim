"""
Coach Archetype System - Defines coaching personalities and decision-making traits

Models real NFL coaching philosophies through quantified traits that influence
play calling decisions in different game situations.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from enum import Enum
import json
from pathlib import Path


class CoachType(Enum):
    """Enumeration of different coach types in the coaching staff"""
    HEAD_COACH = "head_coach"
    OFFENSIVE_COORDINATOR = "offensive_coordinator" 
    DEFENSIVE_COORDINATOR = "defensive_coordinator"
    SPECIAL_TEAMS_COORDINATOR = "special_teams_coordinator"


@dataclass
class SituationalTendencies:
    """Situation-specific coaching tendencies"""
    # Down and distance preferences (0.0-1.0)
    first_down_aggression: float = 0.5      # How aggressive on 1st down
    second_down_creativity: float = 0.5      # Likelihood of trick plays on 2nd down
    third_down_aggression: float = 0.6       # Aggressive vs conservative on 3rd down
    fourth_down_aggression: float = 0.3      # Likelihood to go for it vs punt/kick
    
    # Field position preferences
    red_zone_aggression: float = 0.6         # Aggression inside red zone
    goal_line_creativity: float = 0.4        # Creative plays at goal line
    midfield_risk_tolerance: float = 0.5     # Risk-taking in midfield
    
    # Clock management
    two_minute_aggression: float = 0.7       # End-of-half aggression
    clock_management_conservatism: float = 0.5  # Late-game clock control


@dataclass
class FormationPreferences:
    """Coach-specific formation tendencies"""
    # Offensive formation preferences (weights 0.0-1.0)
    i_formation_preference: float = 0.5       # Traditional power formations
    shotgun_preference: float = 0.5           # Spread/shotgun formations  
    pistol_preference: float = 0.3            # Pistol formations
    wildcat_preference: float = 0.1           # Trick/wildcat formations
    four_wide_preference: float = 0.4         # Four receiver sets
    
    # Personnel package preferences
    heavy_personnel_preference: float = 0.4   # 2+ RB/TE sets (21, 22, 12)
    spread_personnel_preference: float = 0.5  # 3+ WR sets (11, 10)
    balanced_personnel_preference: float = 0.6 # Standard sets


@dataclass
class PlayTypeTendencies:
    """Preferences for different play types"""
    # Basic play type preferences (0.0-1.0)
    run_preference: float = 0.5              # Overall run vs pass preference
    play_action_frequency: float = 0.3       # How often to use play action
    screen_frequency: float = 0.15           # Screen pass frequency
    draw_frequency: float = 0.1              # Draw play frequency
    
    # Passing concepts
    short_pass_preference: float = 0.6       # Quick game preference  
    intermediate_pass_preference: float = 0.4 # 10-20 yard routes
    deep_pass_preference: float = 0.2        # 20+ yard attempts
    
    # Special situation plays
    trick_play_frequency: float = 0.05       # Frequency of trick plays
    fake_punt_aggression: float = 0.1        # Likelihood of fake punts
    fake_field_goal_aggression: float = 0.05 # Fake field goal frequency


@dataclass
class BaseCoachArchetype:
    """
    Base coaching archetype class for all coach types
    
    This class provides common personality traits and behaviors that all
    coach types (Head Coach, OC, DC) inherit and extend.
    """
    # Basic identity
    name: str
    description: str = ""
    coach_type: CoachType = CoachType.HEAD_COACH  # Default for backward compatibility
    
    # Core personality traits (0.0-1.0 scale)
    aggression: float = 0.5                  # Overall aggressiveness
    risk_tolerance: float = 0.5              # Willingness to take risks
    adaptability: float = 0.5                # How quickly they adjust to game flow
    conservatism: float = 0.5                # Conservative vs aggressive baseline
    
    # Legacy simple traits for backward compatibility
    run_preference: float = 0.5
    fourth_down_aggression: float = 0.3
    red_zone_aggression: float = 0.6
    
    # Detailed preference systems
    situational: SituationalTendencies = field(default_factory=SituationalTendencies)
    formations: FormationPreferences = field(default_factory=FormationPreferences)
    play_types: PlayTypeTendencies = field(default_factory=PlayTypeTendencies)
    
    # Meta-coaching traits
    game_script_adherence: float = 0.5       # Stick to game plan vs adapt
    momentum_responsiveness: float = 0.6     # React to momentum swings
    pressure_handling: float = 0.7           # Performance under pressure
    
    def __post_init__(self):
        """Validate archetype values and ensure consistency"""
        self._validate_ranges()
        self._ensure_consistency()
    
    def _validate_ranges(self):
        """Ensure all values are in valid 0.0-1.0 range"""
        traits_to_check = [
            'aggression', 'risk_tolerance', 'adaptability', 'conservatism',
            'run_preference', 'fourth_down_aggression', 'red_zone_aggression',
            'game_script_adherence', 'momentum_responsiveness', 'pressure_handling'
        ]
        
        for trait in traits_to_check:
            value = getattr(self, trait)
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"CoachArchetype.{trait} must be between 0.0 and 1.0, got {value}")
    
    def _ensure_consistency(self):
        """Ensure trait consistency (e.g., high aggression matches other traits)"""
        # Conservative coaches should have lower aggression
        if self.conservatism > 0.7 and self.aggression > 0.6:
            self.aggression = min(self.aggression, 0.6)
        
        # Sync legacy traits with detailed preferences
        self.play_types.run_preference = self.run_preference
        self.situational.fourth_down_aggression = self.fourth_down_aggression
        self.situational.red_zone_aggression = self.red_zone_aggression
    
    def get_situational_aggression(self, situation_type: str, base_aggression: float = None) -> float:
        """
        Get situation-specific aggression level
        
        Args:
            situation_type: Type of situation ('red_zone', 'fourth_down', etc.)
            base_aggression: Override base aggression if provided
            
        Returns:
            Adjusted aggression level for the situation
        """
        base = base_aggression or self.aggression
        
        situation_modifiers = {
            'red_zone': self.situational.red_zone_aggression,
            'fourth_down': self.situational.fourth_down_aggression,
            'two_minute': self.situational.two_minute_aggression,
            'goal_line': self.situational.goal_line_creativity,
        }
        
        modifier = situation_modifiers.get(situation_type, 1.0)
        # Use the maximum of base aggression and situational preference
        return min(1.0, max(base, modifier))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert archetype to dictionary for JSON serialization"""
        return {
            'name': self.name,
            'description': self.description,
            'aggression': self.aggression,
            'risk_tolerance': self.risk_tolerance,
            'adaptability': self.adaptability,
            'conservatism': self.conservatism,
            'run_preference': self.run_preference,
            'fourth_down_aggression': self.fourth_down_aggression,
            'red_zone_aggression': self.red_zone_aggression,
            'game_script_adherence': self.game_script_adherence,
            'momentum_responsiveness': self.momentum_responsiveness,
            'pressure_handling': self.pressure_handling,
            'situational': {
                'first_down_aggression': self.situational.first_down_aggression,
                'second_down_creativity': self.situational.second_down_creativity,
                'third_down_aggression': self.situational.third_down_aggression,
                'fourth_down_aggression': self.situational.fourth_down_aggression,
                'red_zone_aggression': self.situational.red_zone_aggression,
                'goal_line_creativity': self.situational.goal_line_creativity,
                'midfield_risk_tolerance': self.situational.midfield_risk_tolerance,
                'two_minute_aggression': self.situational.two_minute_aggression,
                'clock_management_conservatism': self.situational.clock_management_conservatism,
            },
            'formations': {
                'i_formation_preference': self.formations.i_formation_preference,
                'shotgun_preference': self.formations.shotgun_preference,
                'pistol_preference': self.formations.pistol_preference,
                'wildcat_preference': self.formations.wildcat_preference,
                'four_wide_preference': self.formations.four_wide_preference,
                'heavy_personnel_preference': self.formations.heavy_personnel_preference,
                'spread_personnel_preference': self.formations.spread_personnel_preference,
                'balanced_personnel_preference': self.formations.balanced_personnel_preference,
            },
            'play_types': {
                'run_preference': self.play_types.run_preference,
                'play_action_frequency': self.play_types.play_action_frequency,
                'screen_frequency': self.play_types.screen_frequency,
                'draw_frequency': self.play_types.draw_frequency,
                'short_pass_preference': self.play_types.short_pass_preference,
                'intermediate_pass_preference': self.play_types.intermediate_pass_preference,
                'deep_pass_preference': self.play_types.deep_pass_preference,
                'trick_play_frequency': self.play_types.trick_play_frequency,
                'fake_punt_aggression': self.play_types.fake_punt_aggression,
                'fake_field_goal_aggression': self.play_types.fake_field_goal_aggression,
            }
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CoachArchetype':
        """Create CoachArchetype from dictionary (JSON loading)"""
        # Extract nested structures
        situational_data = data.get('situational', {})
        formations_data = data.get('formations', {})
        play_types_data = data.get('play_types', {})
        
        return cls(
            name=data['name'],
            description=data.get('description', ''),
            aggression=data.get('aggression', 0.5),
            risk_tolerance=data.get('risk_tolerance', 0.5),
            adaptability=data.get('adaptability', 0.5),
            conservatism=data.get('conservatism', 0.5),
            run_preference=data.get('run_preference', 0.5),
            fourth_down_aggression=data.get('fourth_down_aggression', 0.3),
            red_zone_aggression=data.get('red_zone_aggression', 0.6),
            game_script_adherence=data.get('game_script_adherence', 0.5),
            momentum_responsiveness=data.get('momentum_responsiveness', 0.6),
            pressure_handling=data.get('pressure_handling', 0.7),
            situational=SituationalTendencies(**situational_data),
            formations=FormationPreferences(**formations_data),
            play_types=PlayTypeTendencies(**play_types_data),
        )


# Legacy alias for backward compatibility - existing code expects CoachArchetype
CoachArchetype = BaseCoachArchetype


