"""
Special Teams play call with formation and strategy support

Represents a complete special teams play call including play type, formation,
and optional strategies for kicking, punting, and return coverage.
"""

from typing import Optional, Dict, Any, List
from ..play_types.offensive_types import OffensivePlayType, PuntPlayType
from ..play_types.defensive_types import DefensivePlayType
from ..mechanics.formations import OffensiveFormation, DefensiveFormation


class SpecialTeamsPlayCall:
    """Complete special teams play call with formation and strategies"""
    
    def __init__(self, play_type: str, formation: str, strategy: Optional[str] = None,
                 coverage: Optional[str] = None, target_area: Optional[str] = None, **kwargs):
        """
        Initialize special teams play call
        
        Args:
            play_type: Special teams play type (field goal, punt, kickoff, returns, etc.)
            formation: Special teams formation (field goal, punt, kickoff formations)
            strategy: Optional play strategy ("directional_punt", "onside_kick", "block_attempt", etc.)
            coverage: Optional coverage scheme ("contain", "return_left", "return_middle", "return_right")
            target_area: Optional target area ("coffin_corner", "endzone", "sideline", etc.)
            **kwargs: Additional special teams-specific parameters
        """
        self.play_type = play_type
        self.formation = formation
        self.strategy = strategy
        self.coverage = coverage
        self.target_area = target_area
        self.additional_params = kwargs
        
        # Validate inputs
        self._validate_play_call()
    
    def _validate_play_call(self):
        """Validate that special teams play call components are compatible"""
        # Validate play type
        if not self._is_valid_special_teams_play_type(self.play_type):
            raise ValueError(f"Invalid special teams play type: {self.play_type}")
        
        # Validate formation
        if not self._is_valid_special_teams_formation(self.formation):
            raise ValueError(f"Invalid special teams formation: {self.formation}")
        
        # Validate play type + formation compatibility
        if not self._is_compatible_play_formation(self.play_type, self.formation):
            raise ValueError(f"Incompatible play type {self.play_type} with formation {self.formation}")
    
    def _is_valid_special_teams_play_type(self, play_type: str) -> bool:
        """Check if play type is valid special teams type"""
        # Offensive special teams plays
        offensive_special_teams = [
            OffensivePlayType.FIELD_GOAL, OffensivePlayType.PUNT, OffensivePlayType.KICKOFF,
            OffensivePlayType.ONSIDE_KICK, PuntPlayType.REAL_PUNT, PuntPlayType.FAKE_PUNT_PASS,
            PuntPlayType.FAKE_PUNT_RUN
        ]
        
        # Defensive special teams plays
        defensive_special_teams = [
            DefensivePlayType.PUNT_RETURN, DefensivePlayType.PUNT_BLOCK, 
            DefensivePlayType.PUNT_SAFE, DefensivePlayType.SPREAD_RETURN,
            DefensivePlayType.KICKOFF_RETURN
        ]
        
        return play_type in (offensive_special_teams + defensive_special_teams)
    
    def _is_valid_special_teams_formation(self, formation: str) -> bool:
        """Check if formation is valid special teams formation"""
        # Offensive special teams formations (old constants)
        offensive_formations = [
            OffensiveFormation.FIELD_GOAL, OffensiveFormation.PUNT, OffensiveFormation.KICKOFF
        ]
        
        # Defensive special teams formations (old constants)
        defensive_formations = [
            DefensiveFormation.PUNT_RETURN, DefensiveFormation.FIELD_GOAL_BLOCK
        ]
        
        # Unified formation system coordinator names (new system)
        unified_special_teams_formations = [
            # Offensive special teams (unified system uses old formation names)
            "field_goal", "punt", "kickoff",
            # Defensive special teams (unified system coordinator names)
            "punt_return", "punt_block", "punt_safe", "spread_return",
            "field_goal_block", "kick_return"
        ]
        
        return formation in (offensive_formations + defensive_formations + unified_special_teams_formations)
    
    def _is_compatible_play_formation(self, play_type: str, formation: str) -> bool:
        """Check if play type and formation are compatible"""
        # Define compatible combinations (supporting both old and new formation systems)
        compatibility_map = {
            # Offensive special teams (old formation constants)
            OffensivePlayType.FIELD_GOAL: [OffensiveFormation.FIELD_GOAL, "field_goal"],
            OffensivePlayType.PUNT: [OffensiveFormation.PUNT, "punt"],
            PuntPlayType.REAL_PUNT: [OffensiveFormation.PUNT, "punt"],
            PuntPlayType.FAKE_PUNT_PASS: [OffensiveFormation.PUNT, "punt"],
            PuntPlayType.FAKE_PUNT_RUN: [OffensiveFormation.PUNT, "punt"],
            OffensivePlayType.KICKOFF: [OffensiveFormation.KICKOFF, "kickoff"],
            OffensivePlayType.ONSIDE_KICK: [OffensiveFormation.KICKOFF, "kickoff"],
            
            # Defensive special teams (old and new formation names)
            DefensivePlayType.PUNT_RETURN: [DefensiveFormation.PUNT_RETURN, "punt_return", "punt_safe"],
            DefensivePlayType.PUNT_BLOCK: [DefensiveFormation.PUNT_RETURN, "punt_return", "punt_block", "field_goal_block"],
            DefensivePlayType.PUNT_SAFE: [DefensiveFormation.PUNT_RETURN, "punt_return", "punt_safe", "field_goal_block"],
            DefensivePlayType.SPREAD_RETURN: [DefensiveFormation.PUNT_RETURN, "punt_return", "spread_return"],
            DefensivePlayType.KICKOFF_RETURN: [DefensiveFormation.PUNT_RETURN, "punt_return", "kick_return"],
        }
        
        if play_type in compatibility_map:
            return formation in compatibility_map[play_type]
        
        return False
    
    def get_play_type(self) -> str:
        """Get the play type"""
        return self.play_type
    
    def get_formation(self) -> str:
        """Get the formation"""
        return self.formation
    
    def get_strategy(self) -> Optional[str]:
        """Get the play strategy"""
        return self.strategy
    
    def get_coverage(self) -> Optional[str]:
        """Get the coverage scheme"""
        return self.coverage
    
    def get_target_area(self) -> Optional[str]:
        """Get the target area"""
        return self.target_area
    
    def get_additional_params(self) -> Dict[str, Any]:
        """Get additional play parameters"""
        return self.additional_params.copy()
    
    def is_kicking_play(self) -> bool:
        """Check if this is a kicking play (field goal, punt, kickoff)"""
        kicking_plays = [
            OffensivePlayType.FIELD_GOAL, OffensivePlayType.PUNT, OffensivePlayType.KICKOFF,
            OffensivePlayType.ONSIDE_KICK, PuntPlayType.REAL_PUNT
        ]
        return self.play_type in kicking_plays
    
    def is_return_play(self) -> bool:
        """Check if this is a return play"""
        return_plays = [
            DefensivePlayType.PUNT_RETURN, DefensivePlayType.KICKOFF_RETURN,
            DefensivePlayType.SPREAD_RETURN
        ]
        return self.play_type in return_plays
    
    def is_blocking_play(self) -> bool:
        """Check if this is a blocking/disruption play"""
        blocking_plays = [
            DefensivePlayType.PUNT_BLOCK, DefensivePlayType.PUNT_SAFE
        ]
        return self.play_type in blocking_plays
    
    def is_fake_play(self) -> bool:
        """Check if this is a fake special teams play"""
        fake_plays = [
            PuntPlayType.FAKE_PUNT_PASS, PuntPlayType.FAKE_PUNT_RUN
        ]
        return self.play_type in fake_plays
    
    def is_offensive_special_teams(self) -> bool:
        """Check if this is an offensive special teams play"""
        offensive_plays = [
            OffensivePlayType.FIELD_GOAL, OffensivePlayType.PUNT, OffensivePlayType.KICKOFF,
            OffensivePlayType.ONSIDE_KICK, PuntPlayType.REAL_PUNT, 
            PuntPlayType.FAKE_PUNT_PASS, PuntPlayType.FAKE_PUNT_RUN
        ]
        return self.play_type in offensive_plays
    
    def is_defensive_special_teams(self) -> bool:
        """Check if this is a defensive special teams play"""
        defensive_plays = [
            DefensivePlayType.PUNT_RETURN, DefensivePlayType.PUNT_BLOCK,
            DefensivePlayType.PUNT_SAFE, DefensivePlayType.SPREAD_RETURN,
            DefensivePlayType.KICKOFF_RETURN
        ]
        return self.play_type in defensive_plays
    
    def with_strategy(self, strategy: str) -> 'SpecialTeamsPlayCall':
        """Create new play call with different strategy"""
        return SpecialTeamsPlayCall(
            play_type=self.play_type,
            formation=self.formation,
            strategy=strategy,
            coverage=self.coverage,
            target_area=self.target_area,
            **self.additional_params
        )
    
    def with_coverage(self, coverage: str) -> 'SpecialTeamsPlayCall':
        """Create new play call with different coverage"""
        return SpecialTeamsPlayCall(
            play_type=self.play_type,
            formation=self.formation,
            strategy=self.strategy,
            coverage=coverage,
            target_area=self.target_area,
            **self.additional_params
        )
    
    def with_target_area(self, target_area: str) -> 'SpecialTeamsPlayCall':
        """Create new play call with different target area"""
        return SpecialTeamsPlayCall(
            play_type=self.play_type,
            formation=self.formation,
            strategy=self.strategy,
            coverage=self.coverage,
            target_area=target_area,
            **self.additional_params
        )
    
    def __str__(self) -> str:
        strategy_str = f", strategy='{self.strategy}'" if self.strategy else ""
        coverage_str = f", coverage='{self.coverage}'" if self.coverage else ""
        target_str = f", target='{self.target_area}'" if self.target_area else ""
        return f"SpecialTeamsPlayCall(play_type='{self.play_type}', formation='{self.formation}'{strategy_str}{coverage_str}{target_str})"
    
    def __repr__(self) -> str:
        return self.__str__()
    
    def __eq__(self, other) -> bool:
        """Check equality with another play call"""
        if not isinstance(other, SpecialTeamsPlayCall):
            return False
        return (self.play_type == other.play_type and 
                self.formation == other.formation and
                self.strategy == other.strategy and
                self.coverage == other.coverage and
                self.target_area == other.target_area and
                self.additional_params == other.additional_params)