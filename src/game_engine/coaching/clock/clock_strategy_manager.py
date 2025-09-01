from typing import Dict, Any, Optional, Protocol
import logging


class ClockStrategy(Protocol):
    """Protocol defining the interface for clock strategies"""
    
    def get_time_elapsed(self, play_type: str, game_context: Dict[str, Any], completion_status: str = None) -> int:
        """
        Calculate time elapsed for a play based on archetype and game context
        
        Args:
            play_type: Type of play ('run', 'pass', 'punt', 'field_goal', etc.)
            game_context: Context including field_state, down, distance, etc.
            completion_status: For pass plays, status like 'complete', 'incomplete', 'touchdown', 'interception'
            
        Returns:
            int: Time elapsed in seconds
        """
        ...


class ClockStrategyManager:
    """
    Main orchestrator for clock timing decisions using Strategy pattern.
    
    This manager coordinates different clock strategies based on offensive archetypes
    and provides a clean interface for the play execution system. Following the 
    established patterns in the codebase for manager classes.
    """
    
    def __init__(self):
        """Initialize the clock strategy manager with archetype mappings"""
        # Dictionary to store archetype -> strategy mappings
        self._strategies: Dict[str, ClockStrategy] = {}
        
        # Set up logging
        self.logger = logging.getLogger(__name__)
        
        # Initialize with placeholder strategies for future implementation
        self._initialize_placeholder_strategies()
    
    def _initialize_placeholder_strategies(self):
        """Initialize placeholder strategy mappings for known archetypes"""
        # These imports will work when the actual strategy classes are implemented
        # For now, we'll use placeholders that log warnings
        
        try:
            # Import actual strategy implementations
            from .strategies import (
                RunHeavyStrategy,
                AirRaidStrategy,  
                WestCoastStrategy,
                BalancedStrategy
            )
            
            # Register actual strategies
            self.register_strategy('run_heavy', RunHeavyStrategy())
            self.register_strategy('air_raid', AirRaidStrategy())
            self.register_strategy('west_coast', WestCoastStrategy())
            self.register_strategy('balanced_attack', BalancedStrategy())
            self.register_strategy('balanced', BalancedStrategy())  # Alias
            
        except ImportError:
            # Placeholder strategies not yet implemented, use fallback approach
            self.logger.info("Clock strategies not yet implemented, using placeholder approach")
            self._register_placeholder_strategies()
    
    def _register_placeholder_strategies(self):
        """Register placeholder strategies until actual implementations are available"""
        placeholder_strategy = _PlaceholderClockStrategy()
        
        # Register for all known archetypes
        known_archetypes = [
            'run_heavy', 'air_raid', 'west_coast', 'balanced_attack', 
            'balanced', 'conservative', 'aggressive'
        ]
        
        for archetype in known_archetypes:
            self._strategies[archetype] = placeholder_strategy
    
    def register_strategy(self, archetype: str, strategy: ClockStrategy):
        """
        Register a clock strategy for a specific archetype
        
        Args:
            archetype: Offensive archetype name (e.g., 'run_heavy', 'air_raid')
            strategy: Strategy implementation conforming to ClockStrategy protocol
        """
        if not hasattr(strategy, 'get_time_elapsed'):
            raise ValueError(f"Strategy for {archetype} must implement ClockStrategy protocol")
        
        self._strategies[archetype] = strategy
        self.logger.debug(f"Registered clock strategy for archetype: {archetype}")
    
    def get_time_elapsed(self, archetype: str, play_type: str, 
                        game_context: Dict[str, Any], completion_status: str = None) -> int:
        """
        Main entry point for calculating time elapsed based on archetype and play
        
        Args:
            archetype: Offensive archetype (e.g., 'run_heavy', 'air_raid', etc.)
            play_type: Type of play ('run', 'pass', 'punt', 'field_goal', etc.)
            game_context: Game context dict containing:
                - field_state: Current field state
                - down: Current down (1-4)
                - distance: Yards to go
                - quarter: Current quarter
                - clock: Time remaining in quarter
                - score_differential: Point difference
                - timeout_situation: If in timeout scenario
            completion_status: For pass plays, status like 'complete', 'incomplete', 'touchdown', 'interception'
                
        Returns:
            int: Time elapsed in seconds
        """
        # Get strategy for archetype, with fallback to balanced
        strategy = self._get_strategy_with_fallback(archetype)
        
        try:
            time_elapsed = strategy.get_time_elapsed(play_type, game_context, completion_status)
            
            # Validate returned time is reasonable
            if not isinstance(time_elapsed, int) or time_elapsed < 0:
                self.logger.warning(f"Invalid time elapsed {time_elapsed} from {archetype} strategy, using fallback")
                return self._get_fallback_time(play_type, game_context)
            
            # Cap maximum time to reasonable limits
            max_time = self._get_maximum_play_time(play_type, game_context)
            if time_elapsed > max_time:
                self.logger.warning(f"Time elapsed {time_elapsed}s exceeds maximum {max_time}s, capping")
                time_elapsed = max_time
            
            return time_elapsed
            
        except Exception as e:
            self.logger.error(f"Error calculating time elapsed for {archetype}: {e}")
            return self._get_fallback_time(play_type, game_context)
    
    def _get_strategy_with_fallback(self, archetype: str) -> ClockStrategy:
        """Get strategy for archetype with fallback to balanced"""
        # Try to get exact archetype match
        if archetype in self._strategies:
            return self._strategies[archetype]
        
        # Try common aliases
        archetype_aliases = {
            'balanced_attack': 'balanced',
            'conservative': 'balanced',
            'aggressive': 'balanced'
        }
        
        alias = archetype_aliases.get(archetype)
        if alias and alias in self._strategies:
            return self._strategies[alias]
        
        # Fallback to balanced strategy
        if 'balanced' in self._strategies:
            self.logger.warning(f"Unknown archetype '{archetype}', falling back to balanced strategy")
            return self._strategies['balanced']
        
        # Ultimate fallback - create placeholder
        self.logger.warning(f"No strategy available for '{archetype}', using placeholder")
        return _PlaceholderClockStrategy()
    
    def _get_fallback_time(self, play_type: str, game_context: Dict[str, Any]) -> int:
        """Calculate fallback time when primary strategy fails"""
        # Simple fallback timing based on play type
        base_times = {
            'run': 25,      # Running plays consume more clock
            'pass': 15,     # Passing plays vary but shorter on average
            'punt': 10,     # Special teams plays
            'field_goal': 10,
            'kneel': 40,    # Kneeling to run clock
            'spike': 2      # Clock stoppers
        }
        
        base_time = base_times.get(play_type, 20)  # Default 20 seconds
        
        # Apply basic context adjustments
        if game_context.get('timeout_situation'):
            return 2  # Minimal time if timeout called
        
        # Slightly less time in hurry-up situations
        quarter = game_context.get('quarter', 1)
        clock = game_context.get('clock', 900)
        
        if quarter in [2, 4] and clock < 120:  # Two minute warning
            return max(base_time - 5, 5)  # 5-second reduction, minimum 5 seconds
        
        return base_time
    
    def _get_maximum_play_time(self, play_type: str, game_context: Dict[str, Any]) -> int:
        """Get maximum reasonable time for a play type"""
        # Maximum times to prevent unrealistic clock usage
        max_times = {
            'run': 45,      # Very slow running play
            'pass': 35,     # Slow developing pass
            'punt': 30,     # Including snap time
            'field_goal': 30,
            'kneel': 45,    # Maximum kneel time
            'spike': 5      # Should be very quick
        }
        
        return max_times.get(play_type, 40)  # Default maximum
    
    def get_registered_archetypes(self) -> list[str]:
        """Get list of all registered archetypes"""
        return list(self._strategies.keys())
    
    def is_archetype_supported(self, archetype: str) -> bool:
        """Check if an archetype has a registered strategy"""
        return archetype in self._strategies


class _PlaceholderClockStrategy:
    """
    Placeholder strategy implementation for when actual strategies aren't available yet.
    
    This provides basic clock management functionality that can be used until
    archetype-specific strategies are implemented.
    """
    
    def get_time_elapsed(self, play_type: str, game_context: Dict[str, Any], completion_status: str = None) -> int:
        """Basic placeholder implementation of time calculation"""
        # Simple time calculation based on play type and context
        base_times = {
            'run': 38,      # Running plays typically consume more clock
            'pass_complete': 18,     # Complete passes
            'pass_incomplete': 13,   # Incomplete passes stop clock
            'punt': 12,     # Special teams operations
            'field_goal': 12,
            'kneel': 40,    # Intentional clock burning
            'spike': 3      # Intentional clock stopping
        }
        
        # Handle pass play types with completion status
        if play_type == 'pass' and completion_status:
            if completion_status in ['complete', 'touchdown']:
                effective_play_type = 'pass_complete'
            elif completion_status in ['incomplete', 'interception']:
                effective_play_type = 'pass_incomplete'
            else:
                effective_play_type = 'pass_complete'  # Default to complete
        else:
            effective_play_type = play_type
        
        base_time = base_times.get(effective_play_type, 22)  # Default timing
        
        # Basic context modifications
        context_modifiers = self._get_basic_context_modifiers(game_context)
        adjusted_time = base_time + context_modifiers
        
        # Ensure reasonable bounds
        return max(3, min(adjusted_time, 45))
    
    def _get_basic_context_modifiers(self, game_context: Dict[str, Any]) -> int:
        """Apply basic context modifications to timing"""
        modifier = 0
        
        # Hurry-up situations reduce time
        quarter = game_context.get('quarter', 1)
        clock = game_context.get('clock', 900)
        
        if quarter in [2, 4] and clock < 120:  # Two minute drill
            modifier -= 8  # Faster execution
        elif quarter in [2, 4] and clock < 300:  # End of half/game
            modifier -= 4  # Moderately faster
        
        # Score differential affects tempo
        score_diff = game_context.get('score_differential', 0)
        
        if score_diff < -7:  # Trailing by more than a touchdown
            modifier -= 3  # Slight hurry
        elif score_diff > 7:  # Leading by more than a touchdown
            modifier += 3   # Take more time
        
        return modifier