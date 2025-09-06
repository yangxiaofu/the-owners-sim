"""
Offensive Coordinator - Offensive play calling and scheme management

The offensive coordinator is responsible for play selection, formation choices,
personnel packages, and implementing offensive concepts and strategies.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from .coach_archetype import BaseCoachArchetype, CoachType, FormationPreferences, PlayTypeTendencies


@dataclass
class OffensivePhilosophy:
    """Offensive coordinator specific philosophical traits"""
    # Scheme preferences (0.0-1.0)
    west_coast_preference: float = 0.5          # Short, timing-based passing
    air_raid_preference: float = 0.3            # Spread, high-volume passing
    ground_and_pound_preference: float = 0.4     # Run-heavy, physical approach
    rpo_usage: float = 0.5                      # Run-pass option frequency
    
    # Innovation and creativity (0.0-1.0)
    motion_usage: float = 0.6                   # Pre-snap motion frequency
    formation_creativity: float = 0.5            # Unique formation usage
    play_action_mastery: float = 0.6            # Play action effectiveness
    gadget_play_frequency: float = 0.1          # Trick plays and gadgets
    
    # Tempo and rhythm (0.0-1.0)
    no_huddle_usage: float = 0.3                # No-huddle offense frequency
    hurry_up_comfort: float = 0.5               # Comfort with fast tempo
    scripted_opening_reliance: float = 0.7      # Stick to scripted plays early


@dataclass
class PersonnelManagement:
    """How the OC manages personnel packages and player usage"""
    # Personnel package preferences (0.0-1.0)
    eleven_personnel_usage: float = 0.6         # 11 personnel (3 WR, 1 TE, 1 RB)
    twelve_personnel_usage: float = 0.4         # 12 personnel (2 WR, 2 TE, 1 RB)
    twenty_one_personnel_usage: float = 0.2     # 21 personnel (2 WR, 1 TE, 2 RB)
    ten_personnel_usage: float = 0.3            # 10 personnel (4 WR, 1 TE, 1 RB)
    
    # Player utilization philosophy
    feature_back_reliance: float = 0.6          # Rely on one primary RB vs committee
    tight_end_involvement: float = 0.5          # How much TEs are used in passing
    slot_receiver_emphasis: float = 0.6         # Focus on slot receiver usage
    deep_threat_prioritization: float = 0.4     # Emphasis on deep ball receivers


@dataclass
class SituationalCalling:
    """Situational play calling tendencies"""
    # Down and distance preferences
    first_down_pass_rate: float = 0.5           # Pass rate on 1st down
    second_and_long_creativity: float = 0.6     # Creative plays on 2nd & 7+
    third_down_conversion_aggression: float = 0.7  # Risk taking on 3rd down
    
    # Field position adjustments
    red_zone_fade_preference: float = 0.4       # Fade routes in red zone
    red_zone_run_commitment: float = 0.6        # Power runs in red zone
    goal_line_innovation: float = 0.3           # Creative goal line plays
    
    # Game situation responses
    comeback_route_mastery: float = 0.6         # Comeback routes when behind
    clock_killing_run_game: float = 0.7         # Run game when protecting leads
    two_minute_drill_efficiency: float = 0.6    # Two-minute offense execution


@dataclass
class OffensiveCoordinator(BaseCoachArchetype):
    """
    Offensive coordinator focused on play calling and offensive scheme management
    
    Handles formation selection, play concepts, personnel packages, and 
    implements the offensive game plan with situational awareness.
    """
    
    # Specialized traits for offensive coordinators
    philosophy: OffensivePhilosophy = field(default_factory=OffensivePhilosophy)
    personnel: PersonnelManagement = field(default_factory=PersonnelManagement)
    situational_calling: SituationalCalling = field(default_factory=SituationalCalling)
    
    # Playbook preferences - list of preferred playbooks
    preferred_playbooks: List[str] = field(default_factory=lambda: ["balanced"])
    
    def __post_init__(self):
        """Initialize offensive coordinator with proper type and validation"""
        self.coach_type = CoachType.OFFENSIVE_COORDINATOR
        super().__post_init__()
    
    def get_formation_preference(self, situation: str, context: Dict[str, Any] = None) -> Dict[str, float]:
        """
        Get formation preferences for a given situation
        
        Args:
            situation: Game situation ('first_down', 'red_zone', 'two_minute', etc.)
            context: Additional context (down, distance, field position, etc.)
        
        Returns:
            Dictionary of formation preferences with weights
        """
        if not context:
            context = {}
        
        base_formations = {
            'i_formation': self.formations.i_formation_preference,
            'shotgun': self.formations.shotgun_preference,
            'pistol': self.formations.pistol_preference,
            'four_wide': self.formations.four_wide_preference,
        }
        
        # Adjust based on situation
        if situation == 'red_zone':
            # More I-formation and goal line packages in red zone
            base_formations['i_formation'] *= 1.5
            base_formations['shotgun'] *= 0.7
            
        elif situation == 'two_minute':
            # More shotgun and four wide in two-minute drill
            base_formations['shotgun'] *= 1.4
            base_formations['four_wide'] *= 1.3
            base_formations['i_formation'] *= 0.6
            
        elif situation == 'third_and_long':
            # Spread formations for passing
            base_formations['shotgun'] *= 1.3
            base_formations['four_wide'] *= 1.4
            
        elif situation == 'short_yardage':
            # Power formations for short yardage
            base_formations['i_formation'] *= 1.6
            base_formations['shotgun'] *= 0.5
        
        # Normalize weights
        total_weight = sum(base_formations.values())
        if total_weight > 0:
            return {k: v/total_weight for k, v in base_formations.items()}
        
        return base_formations
    
    def get_personnel_package(self, formation: str, situation: str) -> str:
        """
        Select personnel package based on formation and situation
        
        Args:
            formation: Selected formation
            situation: Game situation
        
        Returns:
            Personnel package (e.g., "11", "12", "21", "10")
        """
        # Base personnel preferences
        packages = {
            '11': self.personnel.eleven_personnel_usage,      # 3 WR, 1 TE, 1 RB
            '12': self.personnel.twelve_personnel_usage,      # 2 WR, 2 TE, 1 RB  
            '21': self.personnel.twenty_one_personnel_usage,  # 2 WR, 1 TE, 2 RB
            '10': self.personnel.ten_personnel_usage,         # 4 WR, 1 TE, 1 RB
        }
        
        # Adjust based on formation
        if formation in ['shotgun', 'four_wide']:
            packages['11'] *= 1.3  # More spread personnel in spread formations
            packages['10'] *= 1.5
            packages['21'] *= 0.5  # Less heavy personnel
            
        elif formation == 'i_formation':
            packages['21'] *= 1.4  # More heavy personnel in power formations
            packages['12'] *= 1.2
            packages['10'] *= 0.3  # Much less spread personnel
        
        # Adjust based on situation
        if situation in ['red_zone', 'short_yardage']:
            packages['12'] *= 1.3  # More TEs for blocking
            packages['21'] *= 1.2  # More RBs for power
            
        elif situation in ['two_minute', 'third_and_long']:
            packages['11'] *= 1.2  # More receivers
            packages['10'] *= 1.4
            packages['21'] *= 0.6  # Fewer power packages
        
        # Select highest weighted package
        return max(packages.items(), key=lambda x: x[1])[0]
    
    def get_play_concept_preference(self, situation: str, context: Dict[str, Any] = None) -> Dict[str, float]:
        """
        Get preferred play concepts for the situation
        
        Args:
            situation: Game situation
            context: Additional context (formation, personnel, etc.)
        
        Returns:
            Dictionary of concept preferences with weights
        """
        if not context:
            context = {}
        
        # Start with base concepts for all coordinators - NEVER empty
        concepts = {
            'power': 0.4,
            'slants': 0.4, 
            'quick_out': 0.3,
            'comeback': 0.3,
            'four_verticals': 0.2,
            'sweep': 0.2,
            'off_tackle': 0.3
        }
        
        # Enhance based on philosophy preferences
        if self.philosophy.west_coast_preference > 0.5:
            concepts.update({
                'slants': 0.8,
                'quick_out': 0.7,
                'comeback': 0.6,
                'play_action_short': 0.5
            })
        
        if self.philosophy.air_raid_preference > 0.5:
            concepts.update({
                'four_verticals': 0.8,
                'smash': 0.7,
                'deep_comeback': 0.6,
                'crossing_routes': 0.5
            })
        
        if self.philosophy.ground_and_pound_preference > 0.5:
            concepts.update({
                'power': 0.8,
                'sweep': 0.6,
                'off_tackle': 0.7,
                'play_action_deep': 0.5
            })
        
        # Situational adjustments
        if situation == 'red_zone':
            if self.situational_calling.red_zone_fade_preference > 0.5:
                concepts['fade'] = 0.8
            if self.situational_calling.red_zone_run_commitment > 0.5:
                concepts['power'] = concepts.get('power', 0.5) * 1.5
                concepts['off_tackle'] = concepts.get('off_tackle', 0.5) * 1.3
        
        elif situation == 'third_and_long':
            concepts.update({
                'deep_comeback': 0.8,
                'crossing_routes': 0.7,
                'intermediate_routes': 0.6
            })
        
        elif situation == 'two_minute':
            concepts.update({
                'quick_slant': 0.8,
                'sideline_routes': 0.7,
                'deep_routes': 0.4 if self.situational_calling.two_minute_drill_efficiency > 0.6 else 0.2
            })
        
        # STRICT VALIDATION - never allow empty concept dictionary
        if not concepts:
            raise ValueError(f"Empty concepts dictionary for coordinator {self.name} in situation {situation}")
        
        total_weight = sum(concepts.values())
        if total_weight <= 0:
            raise ValueError(f"All concept weights <= 0 for coordinator {self.name}. Concepts: {concepts}")
        
        return concepts
    
    def evaluate_head_coach_influence(self, hc_influence: float, situation: str) -> float:
        """
        Evaluate how head coach influence affects play calling
        
        Args:
            hc_influence: Head coach influence level (0.0-1.0)
            situation: Current situation
        
        Returns:
            Adjusted influence factor for this coordinator
        """
        # Base resistance to head coach control
        resistance = self.adaptability  # Higher adaptability = less resistance to change
        
        # Some coordinators are more autonomous
        autonomy = 1.0 - self.game_script_adherence  # Less adherence = more autonomous
        
        # In critical situations, accept more head coach input
        critical_situations = ['red_zone', 'fourth_down', 'two_minute', 'overtime']
        if situation in critical_situations:
            acceptance = 0.8  # More willing to take direction in critical moments
        else:
            acceptance = resistance * 0.7 + autonomy * 0.3
        
        # Return effective influence (how much HC influence actually affects decisions)
        return hc_influence * acceptance
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert offensive coordinator to dictionary for JSON serialization"""
        base_dict = super().to_dict()
        
        # Add offensive coordinator specific data
        base_dict['coach_type'] = self.coach_type.value
        base_dict['philosophy'] = {
            'west_coast_preference': self.philosophy.west_coast_preference,
            'air_raid_preference': self.philosophy.air_raid_preference,
            'ground_and_pound_preference': self.philosophy.ground_and_pound_preference,
            'rpo_usage': self.philosophy.rpo_usage,
            'motion_usage': self.philosophy.motion_usage,
            'formation_creativity': self.philosophy.formation_creativity,
            'play_action_mastery': self.philosophy.play_action_mastery,
            'gadget_play_frequency': self.philosophy.gadget_play_frequency,
            'no_huddle_usage': self.philosophy.no_huddle_usage,
            'hurry_up_comfort': self.philosophy.hurry_up_comfort,
            'scripted_opening_reliance': self.philosophy.scripted_opening_reliance,
        }
        base_dict['personnel'] = {
            'eleven_personnel_usage': self.personnel.eleven_personnel_usage,
            'twelve_personnel_usage': self.personnel.twelve_personnel_usage,
            'twenty_one_personnel_usage': self.personnel.twenty_one_personnel_usage,
            'ten_personnel_usage': self.personnel.ten_personnel_usage,
            'feature_back_reliance': self.personnel.feature_back_reliance,
            'tight_end_involvement': self.personnel.tight_end_involvement,
            'slot_receiver_emphasis': self.personnel.slot_receiver_emphasis,
            'deep_threat_prioritization': self.personnel.deep_threat_prioritization,
        }
        base_dict['situational_calling'] = {
            'first_down_pass_rate': self.situational_calling.first_down_pass_rate,
            'second_and_long_creativity': self.situational_calling.second_and_long_creativity,
            'third_down_conversion_aggression': self.situational_calling.third_down_conversion_aggression,
            'red_zone_fade_preference': self.situational_calling.red_zone_fade_preference,
            'red_zone_run_commitment': self.situational_calling.red_zone_run_commitment,
            'goal_line_innovation': self.situational_calling.goal_line_innovation,
            'comeback_route_mastery': self.situational_calling.comeback_route_mastery,
            'clock_killing_run_game': self.situational_calling.clock_killing_run_game,
            'two_minute_drill_efficiency': self.situational_calling.two_minute_drill_efficiency,
        }
        base_dict['preferred_playbooks'] = self.preferred_playbooks.copy()
        
        return base_dict
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'OffensiveCoordinator':
        """Create OffensiveCoordinator from dictionary (JSON loading)"""
        # Extract specialized data
        philosophy_data = data.get('philosophy', {})
        personnel_data = data.get('personnel', {})
        situational_calling_data = data.get('situational_calling', {})
        preferred_playbooks = data.get('preferred_playbooks', ['balanced'])
        
        # Use base class method for common traits
        base_coach = BaseCoachArchetype.from_dict(data)
        
        # Create offensive coordinator with specialized traits
        return cls(
            name=base_coach.name,
            description=base_coach.description,
            coach_type=CoachType.OFFENSIVE_COORDINATOR,
            aggression=base_coach.aggression,
            risk_tolerance=base_coach.risk_tolerance,
            adaptability=base_coach.adaptability,
            conservatism=base_coach.conservatism,
            run_preference=base_coach.run_preference,
            fourth_down_aggression=base_coach.fourth_down_aggression,
            red_zone_aggression=base_coach.red_zone_aggression,
            game_script_adherence=base_coach.game_script_adherence,
            momentum_responsiveness=base_coach.momentum_responsiveness,
            pressure_handling=base_coach.pressure_handling,
            situational=base_coach.situational,
            formations=base_coach.formations,
            play_types=base_coach.play_types,
            philosophy=OffensivePhilosophy(**philosophy_data),
            personnel=PersonnelManagement(**personnel_data),
            situational_calling=SituationalCalling(**situational_calling_data),
            preferred_playbooks=preferred_playbooks,
        )