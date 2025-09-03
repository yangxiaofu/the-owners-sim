"""
Base Clock Strategy

Shared functionality and logic for all coaching clock strategies.
Eliminates code duplication and provides consistent timing calculation methods.
"""

from typing import Dict, Any
from abc import ABC, abstractmethod

from ..config import (
    BasePlayTimes,
    ArchetypeModifiers, 
    SituationalAdjustments,
    TimingBounds,
    DesignerConfig,
    get_effective_play_type,
    calculate_situational_adjustment
)


class BaseClockStrategy(ABC):
    """
    Abstract base class for all clock management strategies.
    
    Provides shared timing calculation logic while allowing each strategy
    to define its own archetype-specific adjustments.
    """
    
    def __init__(self, archetype_name: str):
        """
        Initialize the base strategy.
        
        Args:
            archetype_name: Name of the coaching archetype ('balanced', 'air_raid', etc.)
        """
        self.archetype_name = archetype_name.lower()
    
    def get_time_elapsed(self, play_type: str, game_context: Dict[str, Any], completion_status: str = None) -> int:
        """
        Calculate time elapsed with archetype-specific modifications.
        
        This is the main entry point that all strategies use. It combines:
        1. Base play timing
        2. Archetype-specific adjustments  
        3. Situational modifications
        4. Global designer settings
        
        Args:
            play_type: Type of play ('run', 'pass', 'kick', 'punt')
            game_context: Dict containing game situation (quarter, clock, score_differential, etc.)
            completion_status: For pass plays, status ('complete', 'incomplete', 'touchdown', 'interception')
            
        Returns:
            Time elapsed in seconds with all adjustments applied
        """
        # Step 1: Get base time for the play type
        effective_play_type = get_effective_play_type(play_type, completion_status)
        base_time = self._get_base_time(effective_play_type)
        
        # Step 2: Apply archetype-specific base adjustment
        archetype_adjustment = self._get_archetype_base_adjustment()
        
        # Step 3: Apply archetype-specific play modifiers
        play_modifier = self._get_play_type_modifier(effective_play_type)
        
        # Step 4: Apply standard situational adjustments
        situational_adjustment = calculate_situational_adjustment(game_context, self.archetype_name)
        
        # Step 5: Apply any strategy-specific situational logic
        strategy_specific_adjustment = self._get_strategy_specific_adjustments(
            play_type, game_context, completion_status, effective_play_type
        )
        
        # Combine all adjustments
        total_time = (base_time + 
                     archetype_adjustment + 
                     play_modifier + 
                     situational_adjustment + 
                     strategy_specific_adjustment)
        
        # Step 6: Apply global designer settings
        total_time = DesignerConfig.apply_global_adjustments(total_time)
        
        # Step 7: Enforce bounds
        return TimingBounds.enforce_bounds(total_time)
    
    def _get_base_time(self, effective_play_type: str) -> int:
        """Get base time for the effective play type."""
        base_times = BasePlayTimes.get_base_times_dict()
        return base_times.get(effective_play_type, BasePlayTimes.DEFAULT)
    
    def _get_archetype_base_adjustment(self) -> int:
        """Get the base tempo adjustment for this archetype."""
        adjustments = {
            'balanced': ArchetypeModifiers.BALANCED,
            'air_raid': ArchetypeModifiers.AIR_RAID,
            'run_heavy': ArchetypeModifiers.RUN_HEAVY,
            'west_coast': ArchetypeModifiers.WEST_COAST
        }
        return adjustments.get(self.archetype_name, ArchetypeModifiers.BALANCED)
    
    def _get_play_type_modifier(self, effective_play_type: str) -> int:
        """Get play-type specific modifier for this archetype."""
        if self.archetype_name in ArchetypeModifiers.PLAY_MODIFIERS:
            modifiers = ArchetypeModifiers.PLAY_MODIFIERS[self.archetype_name]
            
            # Handle the effective play types (pass_complete/pass_incomplete)
            if effective_play_type in ['pass_complete', 'pass_incomplete']:
                return modifiers.get(effective_play_type, modifiers.get('pass', 0))
            else:
                return modifiers.get(effective_play_type, 0)
        
        return 0
    
    @abstractmethod
    def _get_strategy_specific_adjustments(self, play_type: str, game_context: Dict[str, Any], 
                                         completion_status: str, effective_play_type: str) -> int:
        """
        Get strategy-specific situational adjustments.
        
        This method must be implemented by each concrete strategy to provide
        any unique timing logic that goes beyond the standard situational adjustments.
        
        Args:
            play_type: Original play type
            game_context: Game situation data
            completion_status: Pass completion status if applicable
            effective_play_type: Processed play type for timing lookup
            
        Returns:
            Additional adjustment in seconds (positive = slower, negative = faster)
        """
        pass
    
    def _extract_game_context(self, game_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract and validate game context variables with defaults.
        
        Args:
            game_context: Raw game context dictionary
            
        Returns:
            Validated game context with all required fields
        """
        return {
            'quarter': game_context.get('quarter', 1),
            'clock': game_context.get('clock', 900),
            'score_differential': game_context.get('score_differential', 0),
            'down': game_context.get('down', 1),
            'distance': game_context.get('distance', 10),
            'field_position': game_context.get('field_position', 20),
            'timeouts_remaining': game_context.get('timeouts_remaining', 3)
        }
    
    def _is_two_minute_situation(self, quarter: int, clock: int) -> bool:
        """Check if this is a two-minute warning situation."""
        return quarter in [2, 4] and clock <= SituationalAdjustments.TWO_MINUTE_WARNING
    
    def _is_fourth_quarter_crunch_time(self, quarter: int, clock: int) -> bool:
        """Check if this is fourth quarter crunch time."""
        return quarter == 4 and clock < SituationalAdjustments.FINAL_FIVE_MINUTES
    
    def _is_red_zone(self, field_position: int) -> bool:
        """Check if team is in red zone."""
        return field_position >= SituationalAdjustments.RED_ZONE
    
    def _is_goal_line(self, field_position: int) -> bool:
        """Check if team is at goal line."""
        return field_position >= SituationalAdjustments.GOAL_LINE
    
    def _calculate_score_based_adjustment(self, score_differential: int, quarter: int = 1) -> int:
        """
        Calculate timing adjustment based on score differential.
        
        Args:
            score_differential: Points ahead (positive) or behind (negative)
            quarter: Current quarter for context
            
        Returns:
            Timing adjustment in seconds
        """
        if score_differential > SituationalAdjustments.LARGE_LEAD:
            return SituationalAdjustments.LEADING_LARGE_ADJUSTMENT
        elif score_differential > SituationalAdjustments.SMALL_LEAD:
            return SituationalAdjustments.LEADING_SMALL_ADJUSTMENT
        elif score_differential < -SituationalAdjustments.LARGE_LEAD:
            return SituationalAdjustments.TRAILING_LARGE_ADJUSTMENT
        elif score_differential < -SituationalAdjustments.SMALL_LEAD:
            return SituationalAdjustments.TRAILING_SMALL_ADJUSTMENT
        
        return 0  # Close game, no adjustment
    
    def get_strategy_info(self) -> Dict[str, Any]:
        """
        Get information about this strategy for debugging/analysis.
        
        Returns:
            Dictionary with strategy metadata
        """
        return {
            'archetype_name': self.archetype_name,
            'base_adjustment': self._get_archetype_base_adjustment(),
            'play_modifiers': ArchetypeModifiers.PLAY_MODIFIERS.get(self.archetype_name, {}),
            'strategy_class': self.__class__.__name__
        }