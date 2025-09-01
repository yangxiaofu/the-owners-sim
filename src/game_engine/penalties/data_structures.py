"""
Penalty Data Structures - Core penalty representation and constants

This module defines the core data structures for representing penalties,
penalty types, and penalty enforcement rules within the football simulation.

Key Components:
- Penalty: Immutable penalty occurrence representation
- PenaltyType: Enum of all supported penalty types
- PenaltyConstants: Centralized penalty rules and yardage
- Penalty phase and enforcement utilities
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, List, Tuple
from enum import Enum


class PenaltyPhase(Enum):
    """When during the play the penalty occurred."""
    PRE_SNAP = "pre_snap"          # Before play starts (false start, offside)
    DURING_PLAY = "during_play"    # During play execution (holding, PI)
    POST_PLAY = "post_play"        # After play completion (unsportsmanlike)


class PenaltyType(Enum):
    """All supported penalty types with their string identifiers."""
    # Pre-snap penalties
    FALSE_START = "false_start"
    OFFSIDE = "offside"
    ENCROACHMENT = "encroachment"
    DELAY_OF_GAME = "delay_of_game"
    TOO_MANY_MEN = "too_many_men"
    
    # During-play penalties
    OFFENSIVE_HOLDING = "offensive_holding"
    DEFENSIVE_HOLDING = "defensive_holding"
    PASS_INTERFERENCE = "pass_interference"
    OFFENSIVE_PASS_INTERFERENCE = "offensive_pass_interference"
    FACE_MASK = "face_mask"
    CLIPPING = "clipping"
    ILLEGAL_BLOCK_IN_BACK = "illegal_block_in_back"
    
    # Post-play penalties
    UNSPORTSMANLIKE_CONDUCT = "unsportsmanlike_conduct"
    TAUNTING = "taunting"
    LATE_HIT = "late_hit"
    EXCESSIVE_CELEBRATION = "excessive_celebration"


@dataclass(frozen=True)
class Penalty:
    """
    Immutable penalty occurrence with complete enforcement information.
    
    This class represents a single penalty that occurred during play execution,
    including the type, responsible player, yardage, and enforcement rules.
    """
    penalty_type: str              # PenaltyType enum value
    penalized_player: str          # Name or ID of player who committed penalty
    penalty_yards: int             # Yardage assessment (positive for offense/defense)
    automatic_first_down: bool     # Whether penalty grants automatic first down
    phase: str                     # PenaltyPhase enum value
    description: str = ""          # Human-readable penalty description
    
    # Additional context
    team_penalized: Optional[str] = None    # "offense" or "defense"
    spot_foul: bool = False                 # Whether penalty is assessed at spot of foul
    loss_of_down: bool = False              # Whether penalty causes loss of down
    
    def __post_init__(self):
        """Validate penalty data integrity."""
        if self.penalty_yards < 0:
            raise ValueError("Penalty yards must be non-negative")
        if self.phase not in [p.value for p in PenaltyPhase]:
            raise ValueError(f"Invalid penalty phase: {self.phase}")
        if self.penalty_type not in [p.value for p in PenaltyType]:
            raise ValueError(f"Invalid penalty type: {self.penalty_type}")
    
    @property
    def penalty_name(self) -> str:
        """Get formatted penalty name for display."""
        return self.penalty_type.replace('_', ' ').title()
    
    def get_enforcement_summary(self) -> str:
        """Generate penalty enforcement description for commentary."""
        player_ref = f"#{self.penalized_player}" if self.penalized_player.isdigit() else self.penalized_player
        summary = f"{self.penalty_name} on {player_ref}"
        
        if self.spot_foul:
            summary += f", {self.penalty_yards} yards from the spot of the foul"
        else:
            summary += f", {self.penalty_yards} yard penalty"
            
        if self.automatic_first_down:
            summary += ", automatic first down"
        elif self.loss_of_down:
            summary += ", loss of down"
            
        return summary
    
    def get_short_description(self) -> str:
        """Get concise penalty description for play-by-play."""
        if self.description:
            return self.description
        return f"{self.penalty_name} - {self.penalty_yards} yards"


@dataclass
class PenaltyResult:
    """
    Result of penalty detection that can be applied to a play.
    
    This class wraps penalty information with additional context needed
    for proper enforcement and play result modification.
    """
    penalty: Penalty
    affects_play_outcome: bool = True      # Whether penalty changes play result
    nullifies_play: bool = False           # Whether penalty cancels play entirely
    enforcement_context: Dict = field(default_factory=dict)  # Additional enforcement data
    
    @property
    def should_retry_play(self) -> bool:
        """Whether this penalty requires replaying the down."""
        # Dead ball fouls typically don't replay the down
        return self.penalty.phase == PenaltyPhase.PRE_SNAP.value and not self.nullifies_play


class PenaltyConstants:
    """
    Centralized penalty rules, yardage, and base occurrence rates.
    
    This class maintains all penalty-specific constants including yardage assessments,
    automatic first down rules, and base probability rates for each penalty type.
    """
    
    # Penalty yardage assessments
    PENALTY_YARDS = {
        # Pre-snap penalties (5 yards)
        PenaltyType.FALSE_START.value: 5,
        PenaltyType.OFFSIDE.value: 5,
        PenaltyType.ENCROACHMENT.value: 5,
        PenaltyType.DELAY_OF_GAME.value: 5,
        PenaltyType.TOO_MANY_MEN.value: 5,
        
        # During-play penalties (varies)
        PenaltyType.OFFENSIVE_HOLDING.value: 10,
        PenaltyType.DEFENSIVE_HOLDING.value: 5,
        PenaltyType.PASS_INTERFERENCE.value: 0,  # Spot foul
        PenaltyType.OFFENSIVE_PASS_INTERFERENCE.value: 10,
        PenaltyType.FACE_MASK.value: 15,
        PenaltyType.CLIPPING.value: 15,
        PenaltyType.ILLEGAL_BLOCK_IN_BACK.value: 10,
        
        # Post-play penalties (15 yards)
        PenaltyType.UNSPORTSMANLIKE_CONDUCT.value: 15,
        PenaltyType.TAUNTING.value: 15,
        PenaltyType.LATE_HIT.value: 15,
        PenaltyType.EXCESSIVE_CELEBRATION.value: 15,
    }
    
    # Automatic first down rules
    AUTOMATIC_FIRST_DOWN = {
        # Defensive penalties that grant automatic first down
        PenaltyType.DEFENSIVE_HOLDING.value: True,
        PenaltyType.PASS_INTERFERENCE.value: True,
        PenaltyType.FACE_MASK.value: True,  # If by defense
        PenaltyType.UNSPORTSMANLIKE_CONDUCT.value: True,  # Context dependent
        PenaltyType.LATE_HIT.value: True,
        
        # Offensive penalties (never automatic first down)
        PenaltyType.FALSE_START.value: False,
        PenaltyType.OFFENSIVE_HOLDING.value: False,
        PenaltyType.OFFENSIVE_PASS_INTERFERENCE.value: False,
        PenaltyType.DELAY_OF_GAME.value: False,
        PenaltyType.CLIPPING.value: False,
        PenaltyType.ILLEGAL_BLOCK_IN_BACK.value: False,
        
        # Neutral penalties (depends on context)
        PenaltyType.OFFSIDE.value: False,
        PenaltyType.ENCROACHMENT.value: False,
        PenaltyType.TOO_MANY_MEN.value: False,
        PenaltyType.TAUNTING.value: False,
        PenaltyType.EXCESSIVE_CELEBRATION.value: False,
    }
    
    # Spot foul penalties (assessed at location of foul)
    SPOT_FOULS = {
        PenaltyType.PASS_INTERFERENCE.value: True,
        PenaltyType.OFFENSIVE_PASS_INTERFERENCE.value: True,
    }
    
    # Base penalty occurrence rates (per play probability)
    BASE_PENALTY_RATES = {
        # Pre-snap penalties (final calibration for NFL 2024 targets)
        PenaltyType.FALSE_START.value: 0.030,      # 3.0% per play  
        PenaltyType.OFFSIDE.value: 0.025,          # 2.5% per play
        PenaltyType.ENCROACHMENT.value: 0.014,     # 1.4% per play
        PenaltyType.DELAY_OF_GAME.value: 0.010,    # 1.0% per play
        PenaltyType.TOO_MANY_MEN.value: 0.007,     # 0.7% per play
        
        # During-play penalties (final calibration for NFL 2024 targets)
        PenaltyType.OFFENSIVE_HOLDING.value: 0.044,     # 4.4% per play (slight increase for yards)
        PenaltyType.DEFENSIVE_HOLDING.value: 0.020,     # 2.0% per play
        PenaltyType.PASS_INTERFERENCE.value: 0.032,     # 3.2% per play (slight increase for yards)
        PenaltyType.OFFENSIVE_PASS_INTERFERENCE.value: 0.005,  # 0.5% per play
        PenaltyType.FACE_MASK.value: 0.014,             # 1.4% per play
        PenaltyType.CLIPPING.value: 0.005,              # 0.5% per play
        PenaltyType.ILLEGAL_BLOCK_IN_BACK.value: 0.009, # 0.9% per play
        
        # Post-play penalties (final calibration for NFL 2024 targets)
        PenaltyType.UNSPORTSMANLIKE_CONDUCT.value: 0.009,  # 0.9% per play
        PenaltyType.TAUNTING.value: 0.005,                 # 0.5% per play
        PenaltyType.LATE_HIT.value: 0.007,                 # 0.7% per play
        PenaltyType.EXCESSIVE_CELEBRATION.value: 0.004,    # 0.4% per play
    }
    
    # Position groups most likely to commit each penalty type
    PENALTY_POSITION_GROUPS = {
        PenaltyType.FALSE_START.value: ['LT', 'LG', 'C', 'RG', 'RT', 'TE'],  # Offensive line
        PenaltyType.OFFSIDE.value: ['DE', 'DT', 'OLB'],                       # Pass rushers
        PenaltyType.OFFENSIVE_HOLDING.value: ['LT', 'LG', 'C', 'RG', 'RT', 'TE'],
        PenaltyType.DEFENSIVE_HOLDING.value: ['CB', 'S'],                     # Secondary
        PenaltyType.PASS_INTERFERENCE.value: ['CB', 'S'],                     # Secondary
        PenaltyType.FACE_MASK.value: ['LB', 'S', 'CB', 'DE'],               # Tacklers
        PenaltyType.UNSPORTSMANLIKE_CONDUCT.value: ['ALL'],                   # Any player
        PenaltyType.TAUNTING.value: ['WR', 'RB', 'LB', 'CB'],               # Skill positions
    }
    
    @classmethod
    def get_penalty_yards(cls, penalty_type: str) -> int:
        """Get yardage assessment for penalty type."""
        return cls.PENALTY_YARDS.get(penalty_type, 0)
    
    @classmethod
    def is_automatic_first_down(cls, penalty_type: str, team_penalized: str = "defense") -> bool:
        """Check if penalty grants automatic first down."""
        base_auto_first = cls.AUTOMATIC_FIRST_DOWN.get(penalty_type, False)
        
        # Some penalties depend on which team committed them
        if penalty_type == PenaltyType.FACE_MASK.value:
            return team_penalized == "defense"
        elif penalty_type == PenaltyType.UNSPORTSMANLIKE_CONDUCT.value:
            return team_penalized == "defense"
            
        return base_auto_first
    
    @classmethod
    def is_spot_foul(cls, penalty_type: str) -> bool:
        """Check if penalty is assessed at spot of foul."""
        return cls.SPOT_FOULS.get(penalty_type, False)
    
    @classmethod
    def get_base_rate(cls, penalty_type: str) -> float:
        """Get base probability rate for penalty type."""
        return cls.BASE_PENALTY_RATES.get(penalty_type, 0.0)
    
    @classmethod
    def get_penalty_positions(cls, penalty_type: str) -> List[str]:
        """Get position groups most likely to commit this penalty."""
        return cls.PENALTY_POSITION_GROUPS.get(penalty_type, ['ALL'])


@dataclass
class SituationalModifiers:
    """
    Contextual modifiers that affect penalty probability rates.
    
    These modifiers are applied to base penalty rates based on game situation,
    field position, score, time remaining, and other contextual factors.
    """
    # Field position modifiers
    red_zone: float = 1.15          # +15% penalty rate in red zone
    goal_line: float = 1.25         # +25% penalty rate on goal line (1-5 yard line)
    
    # Down and distance modifiers
    fourth_down: float = 1.10       # +10% penalty rate on 4th down
    third_and_long: float = 1.12    # +12% penalty rate on 3rd & 7+
    third_and_short: float = 0.95   # -5% penalty rate on 3rd & 1-2 (less desperate)
    
    # Time situation modifiers
    two_minute_drill: float = 1.20  # +20% penalty rate in final 2 minutes
    overtime: float = 0.90          # -10% penalty rate in OT (extra discipline)
    
    # Game context modifiers
    playoff_game: float = 0.95      # -5% penalty rate in playoffs
    rivalry_game: float = 1.12      # +12% penalty rate in rivalry games
    road_game: float = 1.08         # +8% penalty rate on road
    prime_time: float = 0.98        # -2% penalty rate in prime time (more focused)
    
    # Score differential modifiers
    blowout_winning: float = 0.85   # -15% when winning by 21+ (less intense)
    blowout_losing: float = 1.15    # +15% when losing by 21+ (more desperate)
    close_game: float = 1.08        # +8% when within 7 points (more intense)
    
    # Weather modifiers (for applicable penalties)
    bad_weather: float = 1.05       # +5% penalty rate in rain/snow/wind
    
    @classmethod
    def get_modifier_for_situation(cls, situation_name: str) -> float:
        """Get modifier value for a specific situation."""
        return getattr(cls, situation_name, 1.0)
    
    def get_combined_modifier(self, active_situations: List[str]) -> float:
        """Calculate combined modifier for multiple active situations."""
        combined = 1.0
        for situation in active_situations:
            modifier = self.get_modifier_for_situation(situation)
            combined *= modifier
        
        # Cap combined modifiers to prevent extreme values
        return max(0.5, min(2.0, combined))


# Utility functions for penalty creation and validation

def create_penalty(penalty_type: PenaltyType, penalized_player: str, 
                  phase: PenaltyPhase, team_penalized: str = "offense",
                  custom_description: str = "") -> Penalty:
    """
    Create a properly configured Penalty instance.
    
    Args:
        penalty_type: Type of penalty from PenaltyType enum
        penalized_player: Name or ID of penalized player
        phase: When the penalty occurred (PenaltyPhase enum)
        team_penalized: "offense" or "defense"
        custom_description: Optional custom description
    
    Returns:
        Properly configured Penalty instance
    """
    penalty_str = penalty_type.value
    phase_str = phase.value
    
    yards = PenaltyConstants.get_penalty_yards(penalty_str)
    auto_first = PenaltyConstants.is_automatic_first_down(penalty_str, team_penalized)
    spot_foul = PenaltyConstants.is_spot_foul(penalty_str)
    
    description = custom_description or f"{penalty_type.value.replace('_', ' ').title()}"
    
    return Penalty(
        penalty_type=penalty_str,
        penalized_player=penalized_player,
        penalty_yards=yards,
        automatic_first_down=auto_first,
        phase=phase_str,
        description=description,
        team_penalized=team_penalized,
        spot_foul=spot_foul,
        loss_of_down=(penalty_str == PenaltyType.OFFENSIVE_PASS_INTERFERENCE.value)
    )


def get_penalty_summary_stats() -> Dict[str, float]:
    """
    Get summary statistics of expected penalty rates for validation.
    
    Returns:
        Dictionary with expected penalties per game and yards per game
    """
    total_rate = sum(PenaltyConstants.BASE_PENALTY_RATES.values())
    avg_yards = sum(
        rate * PenaltyConstants.get_penalty_yards(penalty_type)
        for penalty_type, rate in PenaltyConstants.BASE_PENALTY_RATES.items()
    ) / len(PenaltyConstants.BASE_PENALTY_RATES)
    
    # Estimate penalties per game (assuming ~65 plays per game per team)
    plays_per_game = 65
    penalties_per_game = total_rate * plays_per_game
    yards_per_game = avg_yards * penalties_per_game
    
    return {
        'expected_penalties_per_game': penalties_per_game,
        'expected_yards_per_game': yards_per_game,
        'total_base_rate': total_rate,
        'average_penalty_yards': avg_yards
    }