"""
Team Mapper Service - High-Performance Team ID Translation

The TeamMapper provides a high-performance service layer for team operations,
offering optimized caching and pre-computed lookup tables for frequent operations.

This component serves as the primary interface between game components and the
team system, providing fast, consistent team ID mappings with built-in caching.

Key features:
- High-performance caching for frequent lookups
- Pre-computed lookup tables for standard mappings
- Automatic cache invalidation on context changes
- Performance monitoring and metrics
- Batch operation support

Usage:
    from game_engine.teams.team_mapper import TeamMapper
    from game_engine.teams.team_registry import TeamRegistry
    from game_engine.teams.team_context import TeamContext
    
    context = TeamContext(home_data, away_data)
    registry = TeamRegistry(context)
    mapper = TeamMapper(registry)
    
    # Fast possession → team lookup (with caching)
    team_id = mapper.map_possession_to_team(possession_id)
    
    # Fast team → scoreboard field lookup (with caching)  
    field = mapper.map_team_to_scoreboard_field(team_id)
"""

from typing import Dict, Any, List, Tuple, Optional
from .team_types import TeamID, TeamInfo
from .team_registry import TeamRegistry


class TeamMapper:
    """High-performance team ID translation service with caching"""
    
    def __init__(self, registry: TeamRegistry):
        """
        Initialize team mapper with registry
        
        Args:
            registry: TeamRegistry instance providing authoritative team operations
        """
        self.registry = registry
        
        # Pre-computed lookup tables for performance
        self._possession_to_team_cache: Dict[Any, TeamID] = {}
        self._team_to_scoreboard_cache: Dict[TeamID, str] = {}
        
        # Performance metrics
        self._cache_hits = 0
        self._cache_misses = 0
        self._total_operations = 0
        
        # Build initial caches
        self._build_caches()
    
    def map_possession_to_team(self, possession_id: Any) -> TeamID:
        """
        Fast possession ID → TeamID lookup with caching
        
        This is the primary method for converting possession IDs (like the
        problematic possession_id=6 from debug output) to standardized TeamIDs.
        
        Args:
            possession_id: The possession identifier (various formats)
            
        Returns:
            TeamID: Standardized team identifier
        """
        self._total_operations += 1
        
        # Check cache first (fastest path)
        try:
            if possession_id in self._possession_to_team_cache:
                self._cache_hits += 1
                return self._possession_to_team_cache[possession_id]
        except TypeError:
            # Unhashable type - cannot be cached, use direct resolution
            self._cache_misses += 1
            return self.registry.resolve_team_from_possession(possession_id)
        
        # Cache miss - resolve through registry and cache result
        self._cache_misses += 1
        team_id = self.registry.resolve_team_from_possession(possession_id)
        
        # Cache the result (only for hashable types)
        try:
            self._possession_to_team_cache[possession_id] = team_id
        except TypeError:
            # Skip caching for unhashable types like dicts
            pass
        
        return team_id
    
    def map_team_to_scoreboard_field(self, team_id: TeamID) -> str:
        """
        Fast TeamID → scoreboard field lookup with caching
        
        This is the critical method for converting TeamIDs to scoreboard field
        names for score application, fixing the original scoreboard bug.
        
        Args:
            team_id: The team identifier
            
        Returns:
            str: Scoreboard field name ("home" or "away")
            
        Raises:
            ValueError: If team cannot be mapped to scoreboard (e.g., NEUTRAL)
        """
        self._total_operations += 1
        
        # Check cache first
        if team_id in self._team_to_scoreboard_cache:
            self._cache_hits += 1
            return self._team_to_scoreboard_cache[team_id]
        
        # Cache miss - resolve through registry and cache result
        self._cache_misses += 1
        try:
            field = self.registry.resolve_scoreboard_target(team_id)
            self._team_to_scoreboard_cache[team_id] = field
            return field
        except ValueError:
            # Don't cache invalid mappings - let them fail consistently
            raise
    
    def map_possession_to_scoreboard_field(self, possession_id: Any) -> str:
        """
        Direct possession ID → scoreboard field mapping (convenience method)
        
        This combines the two-step process of possession → team → scoreboard
        into a single optimized operation.
        
        Args:
            possession_id: The possession identifier
            
        Returns:
            str: Scoreboard field name ("home" or "away")
        """
        team_id = self.map_possession_to_team(possession_id)
        return self.map_team_to_scoreboard_field(team_id)
    
    def get_team_info(self, team_id: TeamID) -> Optional[TeamInfo]:
        """
        Get complete team information (delegated to registry)
        
        Args:
            team_id: The team identifier
            
        Returns:
            TeamInfo: Complete team information, or None if not found
        """
        return self.registry.get_team_info(team_id)
    
    def get_team_info_by_possession(self, possession_id: Any) -> Optional[TeamInfo]:
        """
        Get team information by possession ID (convenience method)
        
        Args:
            possession_id: The possession identifier
            
        Returns:
            TeamInfo: Complete team information for the possessing team
        """
        team_id = self.map_possession_to_team(possession_id)
        return self.get_team_info(team_id)
    
    def batch_map_possessions(self, possession_ids: List[Any]) -> List[Tuple[Any, TeamID]]:
        """
        Batch process multiple possession mappings for performance
        
        Args:
            possession_ids: List of possession identifiers to map
            
        Returns:
            List[Tuple]: List of (possession_id, team_id) pairs
        """
        results = []
        for possession_id in possession_ids:
            team_id = self.map_possession_to_team(possession_id)
            results.append((possession_id, team_id))
        return results
    
    def validate_possession_mapping(self, possession_id: Any) -> bool:
        """
        Check if possession ID can be mapped to valid team
        
        Args:
            possession_id: The possession identifier to validate
            
        Returns:
            bool: True if mapping is valid, False otherwise
        """
        try:
            team_id = self.map_possession_to_team(possession_id)
            return team_id in {TeamID.HOME, TeamID.AWAY, TeamID.NEUTRAL}
        except Exception:
            return False
    
    def validate_scoreboard_mapping(self, team_id: TeamID) -> bool:
        """
        Check if team ID can be mapped to scoreboard field
        
        Args:
            team_id: The team identifier to validate
            
        Returns:
            bool: True if mapping is valid, False otherwise
        """
        try:
            self.map_team_to_scoreboard_field(team_id)
            return True
        except ValueError:
            return False
    
    def invalidate_caches(self):
        """
        Clear all caches and rebuild with current registry state
        
        This should be called when team context changes or custom
        mappings are registered.
        """
        self._possession_to_team_cache.clear()
        self._team_to_scoreboard_cache.clear()
        
        # Reset performance counters
        self._cache_hits = 0
        self._cache_misses = 0
        
        # Rebuild caches
        self._build_caches()
    
    def _build_caches(self):
        """
        Pre-populate caches with common lookups for performance
        
        This method pre-caches standard team mappings to minimize
        cache misses for frequent operations.
        """
        # Pre-cache standard team → scoreboard mappings
        for team_id in [TeamID.HOME, TeamID.AWAY]:
            try:
                scoreboard_field = self.registry.resolve_scoreboard_target(team_id)
                self._team_to_scoreboard_cache[team_id] = scoreboard_field
            except ValueError:
                # Skip invalid mappings (like NEUTRAL → scoreboard)
                pass
        
        # Pre-cache standard possession mappings
        standard_possessions = [1, 2, 0, "1", "2", "0", "home", "away", "neutral"]
        for possession_id in standard_possessions:
            try:
                team_id = self.registry.resolve_team_from_possession(possession_id)
                self._possession_to_team_cache[possession_id] = team_id
            except Exception:
                # Skip invalid mappings
                pass
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get performance metrics for monitoring and optimization
        
        Returns:
            Dict: Performance statistics including cache hit rates
        """
        total_ops = self._total_operations
        hit_rate = (self._cache_hits / total_ops * 100) if total_ops > 0 else 0
        
        return {
            'total_operations': total_ops,
            'cache_hits': self._cache_hits,
            'cache_misses': self._cache_misses,
            'cache_hit_rate_percent': round(hit_rate, 2),
            'cache_sizes': {
                'possession_cache': len(self._possession_to_team_cache),
                'scoreboard_cache': len(self._team_to_scoreboard_cache)
            }
        }
    
    def get_debug_info(self) -> Dict[str, Any]:
        """
        Get comprehensive debug information
        
        Returns:
            Dict: Debug information including caches and performance metrics
        """
        return {
            'performance_metrics': self.get_performance_metrics(),
            'cache_contents': {
                'possession_cache': dict(self._possession_to_team_cache),
                'scoreboard_cache': dict(self._team_to_scoreboard_cache)
            },
            'registry_debug': self.registry.get_debug_info()
        }
    
    def __str__(self) -> str:
        """String representation for debugging"""
        metrics = self.get_performance_metrics()
        return f"TeamMapper(operations={metrics['total_operations']}, hit_rate={metrics['cache_hit_rate_percent']}%)"
    
    def __repr__(self) -> str:
        """Detailed representation for debugging"""
        return f"TeamMapper(registry={self.registry!r}, cached_possessions={len(self._possession_to_team_cache)})"