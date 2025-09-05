"""
Defensive play call with formation and coverage support

Represents a complete defensive play call including play type, formation,
and optional coverage/blitz packages for realistic football defensive coordination.
"""

from typing import Optional, Dict, Any, List
from ..play_types.defensive_types import DefensivePlayType
from formation import DefensiveFormation


class DefensivePlayCall:
    """Complete defensive play call with formation and coverage"""
    
    def __init__(self, play_type: str, formation: str, coverage: Optional[str] = None,
                 blitz_package: Optional[str] = None, hot_routes: Optional[List[str]] = None, **kwargs):
        """
        Initialize defensive play call
        
        Args:
            play_type: DefensivePlayType constant (e.g., DefensivePlayType.COVER_2)
            formation: DefensiveFormation constant (e.g., DefensiveFormation.FOUR_THREE)
            coverage: Optional coverage scheme ("man", "zone", "robber", etc.)
            blitz_package: Optional blitz type ("corner_blitz", "safety_blitz", "a_gap", etc.)
            hot_routes: Optional list of hot route adjustments
            **kwargs: Additional defensive-specific parameters
        """
        self.play_type = play_type
        self.formation = formation
        self.coverage = coverage
        self.blitz_package = blitz_package
        self.hot_routes = hot_routes or []
        self.additional_params = kwargs
        
        # Validate inputs
        self._validate_play_call()
    
    def _validate_play_call(self):
        """Validate that defensive play call components are compatible"""
        # Validate play type
        if not self._is_valid_defensive_play_type(self.play_type):
            raise ValueError(f"Invalid defensive play type: {self.play_type}")
        
        # Validate formation
        if not self._is_valid_defensive_formation(self.formation):
            raise ValueError(f"Invalid defensive formation: {self.formation}")
        
        # Validate play type + formation compatibility
        if not self._is_compatible_play_formation(self.play_type, self.formation):
            raise ValueError(f"Incompatible play type {self.play_type} with formation {self.formation}")
    
    def _is_valid_defensive_play_type(self, play_type: str) -> bool:
        """Check if play type is valid defensive type"""
        valid_types = [
            DefensivePlayType.COVER_0, DefensivePlayType.COVER_1, DefensivePlayType.COVER_2,
            DefensivePlayType.COVER_3, DefensivePlayType.MAN_COVERAGE, DefensivePlayType.ZONE_COVERAGE,
            DefensivePlayType.FOUR_MAN_RUSH, DefensivePlayType.BLITZ, DefensivePlayType.CORNER_BLITZ,
            DefensivePlayType.SAFETY_BLITZ, DefensivePlayType.NICKEL_DEFENSE, DefensivePlayType.DIME_DEFENSE,
            DefensivePlayType.GOAL_LINE_DEFENSE, DefensivePlayType.PREVENT_DEFENSE, DefensivePlayType.RUN_STUFF
        ]
        return play_type in valid_types
    
    def _is_valid_defensive_formation(self, formation: str) -> bool:
        """Check if formation is valid defensive formation"""
        valid_formations = [
            DefensiveFormation.FOUR_THREE, DefensiveFormation.THREE_FOUR, DefensiveFormation.FOUR_SIX,
            DefensiveFormation.NICKEL, DefensiveFormation.DIME, DefensiveFormation.QUARTER,
            DefensiveFormation.GOAL_LINE, DefensiveFormation.PREVENT, DefensiveFormation.BLITZ_PACKAGE,
            DefensiveFormation.PUNT_RETURN, DefensiveFormation.KICK_RETURN, DefensiveFormation.FIELD_GOAL_BLOCK
        ]
        return formation in valid_formations
    
    def _is_compatible_play_formation(self, play_type: str, formation: str) -> bool:
        """Check if play type and formation are compatible"""
        # Specific play type + formation requirements
        required_formations = {
            DefensivePlayType.NICKEL_DEFENSE: DefensiveFormation.NICKEL,
            DefensivePlayType.DIME_DEFENSE: DefensiveFormation.DIME,
            DefensivePlayType.GOAL_LINE_DEFENSE: DefensiveFormation.GOAL_LINE,
            DefensivePlayType.PREVENT_DEFENSE: DefensiveFormation.PREVENT
        }
        
        if play_type in required_formations:
            return formation == required_formations[play_type]
        
        # Special teams formations match
        special_teams_formations = [
            DefensiveFormation.PUNT_RETURN, DefensiveFormation.KICK_RETURN, DefensiveFormation.FIELD_GOAL_BLOCK
        ]
        
        # For now, allow all other combinations (could be refined later)
        return True
    
    def get_play_type(self) -> str:
        """Get the play type"""
        return self.play_type
    
    def get_formation(self) -> str:
        """Get the formation"""
        return self.formation
    
    def get_coverage(self) -> Optional[str]:
        """Get the coverage scheme"""
        return self.coverage
    
    def get_blitz_package(self) -> Optional[str]:
        """Get the blitz package"""
        return self.blitz_package
    
    def get_hot_routes(self) -> List[str]:
        """Get hot route adjustments"""
        return self.hot_routes.copy()
    
    def get_additional_params(self) -> Dict[str, Any]:
        """Get additional defensive parameters"""
        return self.additional_params.copy()
    
    def is_man_coverage(self) -> bool:
        """Check if this uses man coverage"""
        man_coverage_plays = [
            DefensivePlayType.COVER_0, DefensivePlayType.COVER_1, DefensivePlayType.MAN_COVERAGE
        ]
        return self.play_type in man_coverage_plays or self.coverage == "man"
    
    def is_zone_coverage(self) -> bool:
        """Check if this uses zone coverage"""
        zone_coverage_plays = [
            DefensivePlayType.COVER_2, DefensivePlayType.COVER_3, DefensivePlayType.ZONE_COVERAGE,
            DefensivePlayType.PREVENT_DEFENSE
        ]
        return self.play_type in zone_coverage_plays or self.coverage == "zone"
    
    def is_blitz(self) -> bool:
        """Check if this is a blitz play"""
        blitz_plays = [
            DefensivePlayType.BLITZ, DefensivePlayType.CORNER_BLITZ, DefensivePlayType.SAFETY_BLITZ
        ]
        return (self.play_type in blitz_plays or 
                self.formation == DefensiveFormation.BLITZ_PACKAGE or
                self.blitz_package is not None)
    
    def is_pass_defense(self) -> bool:
        """Check if this is primarily pass defense"""
        pass_defense_plays = [
            DefensivePlayType.COVER_0, DefensivePlayType.COVER_1, DefensivePlayType.COVER_2,
            DefensivePlayType.COVER_3, DefensivePlayType.MAN_COVERAGE, DefensivePlayType.ZONE_COVERAGE,
            DefensivePlayType.NICKEL_DEFENSE, DefensivePlayType.DIME_DEFENSE, DefensivePlayType.PREVENT_DEFENSE,
            DefensivePlayType.BLITZ, DefensivePlayType.CORNER_BLITZ, DefensivePlayType.SAFETY_BLITZ
        ]
        return self.play_type in pass_defense_plays
    
    def is_run_defense(self) -> bool:
        """Check if this is primarily run defense"""
        run_defense_plays = [DefensivePlayType.RUN_STUFF, DefensivePlayType.GOAL_LINE_DEFENSE]
        return (self.play_type in run_defense_plays or 
                self.formation in [DefensiveFormation.FOUR_SIX, DefensiveFormation.GOAL_LINE])
    
    def with_coverage(self, coverage: str) -> 'DefensivePlayCall':
        """Create new play call with different coverage"""
        return DefensivePlayCall(
            play_type=self.play_type,
            formation=self.formation,
            coverage=coverage,
            blitz_package=self.blitz_package,
            hot_routes=self.hot_routes,
            **self.additional_params
        )
    
    def with_blitz_package(self, blitz_package: str) -> 'DefensivePlayCall':
        """Create new play call with different blitz package"""
        return DefensivePlayCall(
            play_type=self.play_type,
            formation=self.formation,
            coverage=self.coverage,
            blitz_package=blitz_package,
            hot_routes=self.hot_routes,
            **self.additional_params
        )
    
    def with_formation(self, formation: str) -> 'DefensivePlayCall':
        """Create new play call with different formation"""
        return DefensivePlayCall(
            play_type=self.play_type,
            formation=formation,
            coverage=self.coverage,
            blitz_package=self.blitz_package,
            hot_routes=self.hot_routes,
            **self.additional_params
        )
    
    def add_hot_route(self, hot_route: str) -> 'DefensivePlayCall':
        """Create new play call with additional hot route"""
        new_hot_routes = self.hot_routes + [hot_route]
        return DefensivePlayCall(
            play_type=self.play_type,
            formation=self.formation,
            coverage=self.coverage,
            blitz_package=self.blitz_package,
            hot_routes=new_hot_routes,
            **self.additional_params
        )
    
    def __str__(self) -> str:
        coverage_str = f", coverage='{self.coverage}'" if self.coverage else ""
        blitz_str = f", blitz='{self.blitz_package}'" if self.blitz_package else ""
        hot_routes_str = f", hot_routes={self.hot_routes}" if self.hot_routes else ""
        return f"DefensivePlayCall(play_type='{self.play_type}', formation='{self.formation}'{coverage_str}{blitz_str}{hot_routes_str})"
    
    def __repr__(self) -> str:
        return self.__str__()
    
    def __eq__(self, other) -> bool:
        """Check equality with another play call"""
        if not isinstance(other, DefensivePlayCall):
            return False
        return (self.play_type == other.play_type and 
                self.formation == other.formation and
                self.coverage == other.coverage and
                self.blitz_package == other.blitz_package and
                self.hot_routes == other.hot_routes and
                self.additional_params == other.additional_params)