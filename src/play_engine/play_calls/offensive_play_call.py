"""
Offensive play call with formation and concept support

Represents a complete offensive play call including play type, formation,
and optional concepts/personnel packages for realistic football play calling.
"""

from typing import Optional, Dict, Any
from ..play_types.offensive_types import OffensivePlayType
from formation import OffensiveFormation


class OffensivePlayCall:
    """Complete offensive play call with formation and concepts"""
    
    def __init__(self, play_type: str, formation: str, concept: Optional[str] = None, 
                 personnel_package: Optional[str] = None, **kwargs):
        """
        Initialize offensive play call
        
        Args:
            play_type: OffensivePlayType constant (e.g., OffensivePlayType.RUN)
            formation: OffensiveFormation constant (e.g., OffensiveFormation.I_FORMATION)
            concept: Optional play concept ("power", "sweep", "four_verticals", etc.)
            personnel_package: Optional personnel designation ("21", "11", "12", etc.)
            **kwargs: Additional play-specific parameters
        """
        self.play_type = play_type
        self.formation = formation
        self.concept = concept
        self.personnel_package = personnel_package
        self.additional_params = kwargs
        
        # Validate inputs
        self._validate_play_call()
    
    def _validate_play_call(self):
        """Validate that play call components are compatible"""
        # Validate play type
        if not self._is_valid_offensive_play_type(self.play_type):
            raise ValueError(f"Invalid offensive play type: {self.play_type}")
        
        # Validate formation
        if not self._is_valid_offensive_formation(self.formation):
            raise ValueError(f"Invalid offensive formation: {self.formation}")
        
        # Validate play type + formation compatibility
        if not self._is_compatible_play_formation(self.play_type, self.formation):
            raise ValueError(f"Incompatible play type {self.play_type} with formation {self.formation}")
    
    def _is_valid_offensive_play_type(self, play_type: str) -> bool:
        """Check if play type is valid offensive type"""
        valid_types = [
            OffensivePlayType.RUN, OffensivePlayType.PASS, OffensivePlayType.PLAY_ACTION_PASS,
            OffensivePlayType.SCREEN_PASS, OffensivePlayType.QUICK_SLANT, OffensivePlayType.DEEP_BALL,
            OffensivePlayType.FIELD_GOAL, OffensivePlayType.PUNT, OffensivePlayType.KICKOFF,
            OffensivePlayType.TWO_POINT_CONVERSION, OffensivePlayType.KNEEL_DOWN, OffensivePlayType.SPIKE
        ]
        return play_type in valid_types
    
    def _is_valid_offensive_formation(self, formation: str) -> bool:
        """Check if formation is valid offensive formation"""
        valid_formations = [
            OffensiveFormation.I_FORMATION, OffensiveFormation.SHOTGUN, OffensiveFormation.SINGLEBACK,
            OffensiveFormation.PISTOL, OffensiveFormation.WILDCAT, OffensiveFormation.FOUR_WIDE,
            OffensiveFormation.FIVE_WIDE, OffensiveFormation.TRIPS, OffensiveFormation.BUNCH,
            OffensiveFormation.GOAL_LINE, OffensiveFormation.SHORT_YARDAGE,
            OffensiveFormation.FIELD_GOAL, OffensiveFormation.PUNT, OffensiveFormation.KICKOFF,
            OffensiveFormation.VICTORY
        ]
        return formation in valid_formations
    
    def _is_compatible_play_formation(self, play_type: str, formation: str) -> bool:
        """Check if play type and formation are compatible"""
        # Special teams plays must use special teams formations
        special_teams_plays = {
            OffensivePlayType.FIELD_GOAL: OffensiveFormation.FIELD_GOAL,
            OffensivePlayType.PUNT: OffensiveFormation.PUNT,
            OffensivePlayType.KICKOFF: OffensiveFormation.KICKOFF
        }
        
        if play_type in special_teams_plays:
            return formation == special_teams_plays[play_type]
        
        # Non-special teams plays cannot use special teams formations
        special_formations = [OffensiveFormation.FIELD_GOAL, OffensiveFormation.PUNT, OffensiveFormation.KICKOFF]
        if formation in special_formations:
            return play_type in special_teams_plays
        
        # All other combinations are valid
        return True
    
    def get_play_type(self) -> str:
        """Get the play type"""
        return self.play_type
    
    def get_formation(self) -> str:
        """Get the formation"""
        return self.formation
    
    def get_concept(self) -> Optional[str]:
        """Get the play concept"""
        return self.concept
    
    def get_personnel_package(self) -> Optional[str]:
        """Get the personnel package"""
        return self.personnel_package
    
    def get_additional_params(self) -> Dict[str, Any]:
        """Get additional play parameters"""
        return self.additional_params.copy()
    
    def is_running_play(self) -> bool:
        """Check if this is a running play"""
        running_plays = [OffensivePlayType.RUN, OffensivePlayType.KNEEL_DOWN]
        return self.play_type in running_plays
    
    def is_passing_play(self) -> bool:
        """Check if this is a passing play"""
        passing_plays = [
            OffensivePlayType.PASS, OffensivePlayType.PLAY_ACTION_PASS,
            OffensivePlayType.SCREEN_PASS, OffensivePlayType.QUICK_SLANT,
            OffensivePlayType.DEEP_BALL, OffensivePlayType.SPIKE
        ]
        return self.play_type in passing_plays
    
    def is_special_teams(self) -> bool:
        """Check if this is a special teams play"""
        special_teams = [
            OffensivePlayType.FIELD_GOAL, OffensivePlayType.PUNT, OffensivePlayType.KICKOFF
        ]
        return self.play_type in special_teams
    
    def with_concept(self, concept: str) -> 'OffensivePlayCall':
        """Create new play call with different concept"""
        return OffensivePlayCall(
            play_type=self.play_type,
            formation=self.formation,
            concept=concept,
            personnel_package=self.personnel_package,
            **self.additional_params
        )
    
    def with_formation(self, formation: str) -> 'OffensivePlayCall':
        """Create new play call with different formation"""
        return OffensivePlayCall(
            play_type=self.play_type,
            formation=formation,
            concept=self.concept,
            personnel_package=self.personnel_package,
            **self.additional_params
        )
    
    def __str__(self) -> str:
        concept_str = f", concept='{self.concept}'" if self.concept else ""
        package_str = f", personnel='{self.personnel_package}'" if self.personnel_package else ""
        return f"OffensivePlayCall(play_type='{self.play_type}', formation='{self.formation}'{concept_str}{package_str})"
    
    def __repr__(self) -> str:
        return self.__str__()
    
    def __eq__(self, other) -> bool:
        """Check equality with another play call"""
        if not isinstance(other, OffensivePlayCall):
            return False
        return (self.play_type == other.play_type and 
                self.formation == other.formation and
                self.concept == other.concept and
                self.personnel_package == other.personnel_package and
                self.additional_params == other.additional_params)