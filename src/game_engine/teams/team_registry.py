"""
Team Registry - Central Authority for Team Operations

The TeamRegistry serves as the single source of truth for all team-related operations
in the game. It provides authoritative team resolution, validation, and event logging.

This component addresses the core issue causing the scoreboard bug by ensuring
consistent, validated team assignments throughout the system.

Key responsibilities:
- Authoritative possession → team mapping
- Team → scoreboard field resolution  
- Team operation validation
- Event logging and audit trails
- Business rule enforcement

Usage:
    from game_engine.teams.team_registry import TeamRegistry
    from game_engine.teams.team_context import TeamContext
    
    registry = TeamRegistry(team_context)
    
    # Resolve team from possession (the critical operation)
    team_id = registry.resolve_team_from_possession(possession_id)
    
    # Get scoreboard field for score application
    field = registry.resolve_scoreboard_target(team_id)
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from .team_types import TeamID, TeamSide, TeamInfo
from .team_context import TeamContext


class TeamRegistry:
    """Single source of truth for all team operations"""
    
    def __init__(self, team_context: TeamContext):
        """
        Initialize team registry with team context
        
        Args:
            team_context: TeamContext containing game-specific team information
        """
        self.context = team_context
        
        # Event logging for debugging and auditing
        self._event_log: List[Dict[str, Any]] = []
        
        # Operation counters for performance monitoring
        self._operation_counts = {
            'possession_resolutions': 0,
            'scoreboard_resolutions': 0,
            'validations': 0,
            'errors': 0
        }
        
        # Cache for frequent operations (cleared on context changes)
        self._resolution_cache: Dict[Any, TeamID] = {}
        self._scoreboard_cache: Dict[TeamID, str] = {}
    
    def resolve_team_from_possession(self, possession_id: Any) -> TeamID:
        """
        Authoritative possession → team mapping
        
        This is the critical method that fixes the scoreboard bug by providing
        consistent, validated team resolution for all possession scenarios.
        
        Args:
            possession_id: The possession team identifier (various formats)
            
        Returns:
            TeamID: Standardized, validated team identifier
        """
        self._operation_counts['possession_resolutions'] += 1
        
        # Check cache first for performance
        if possession_id in self._resolution_cache:
            return self._resolution_cache[possession_id]
        
        try:
            # Use team context for resolution
            team_id = self.context.map_possession_to_team(possession_id)
            
            # Validate the result
            if not self._validate_team_id(team_id):
                self._log_error(f"Invalid team ID resolved: {team_id} from possession {possession_id}")
                team_id = TeamID.HOME  # Safe fallback
            
            # Cache the result
            self._resolution_cache[possession_id] = team_id
            
            # Log the resolution for debugging
            self._log_event({
                'event_type': 'possession_resolution',
                'possession_id': possession_id,
                'resolved_team_id': team_id,
                'method': 'context_mapping'
            })
            
            return team_id
            
        except Exception as e:
            self._operation_counts['errors'] += 1
            self._log_error(f"Error resolving possession {possession_id}: {e}")
            
            # Fallback to safe default
            fallback_team = TeamID.HOME
            self._resolution_cache[possession_id] = fallback_team
            return fallback_team
    
    def resolve_scoring_team(self, possession_id: Any) -> TeamID:
        """
        Determine which team scores for given possession
        
        In most cases, the possessing team scores. This method allows for
        future enhancement of scoring logic (e.g., defensive scores).
        
        Args:
            possession_id: The possession team identifier
            
        Returns:
            TeamID: The team that should be credited with scoring
        """
        # For now, possessing team scores (standard case)
        scoring_team = self.resolve_team_from_possession(possession_id)
        
        self._log_event({
            'event_type': 'scoring_team_resolution',
            'possession_id': possession_id,
            'scoring_team_id': scoring_team
        })
        
        return scoring_team
    
    def resolve_scoreboard_target(self, team_id: TeamID) -> str:
        """
        Map team ID to scoreboard field name
        
        This is the other critical method for fixing the scoreboard bug.
        It ensures consistent mapping from TeamID to scoreboard fields.
        
        Args:
            team_id: The team identifier
            
        Returns:
            str: Scoreboard field name ("home" or "away")
            
        Raises:
            ValueError: If team cannot be mapped to scoreboard (e.g., NEUTRAL)
        """
        self._operation_counts['scoreboard_resolutions'] += 1
        
        # Check cache first
        if team_id in self._scoreboard_cache:
            return self._scoreboard_cache[team_id]
        
        try:
            # Use TeamID's built-in method for consistency
            scoreboard_field = team_id.to_scoreboard_field()
            
            # Cache the result
            self._scoreboard_cache[team_id] = scoreboard_field
            
            self._log_event({
                'event_type': 'scoreboard_resolution',
                'team_id': team_id,
                'scoreboard_field': scoreboard_field
            })
            
            return scoreboard_field
            
        except ValueError as e:
            self._operation_counts['errors'] += 1
            self._log_error(f"Cannot map team {team_id} to scoreboard: {e}")
            raise
    
    def validate_team_operation(self, team_id: TeamID, operation: str, context: Dict[str, Any] = None) -> bool:
        """
        Validate team-related operations
        
        Provides business rule validation for team operations to prevent
        invalid states and ensure game rule compliance.
        
        Args:
            team_id: The team identifier
            operation: The operation being performed ("score", "possess", etc.)
            context: Optional context information for validation
            
        Returns:
            bool: True if operation is valid, False otherwise
        """
        self._operation_counts['validations'] += 1
        context = context or {}
        
        # Basic team ID validation
        if not self._validate_team_id(team_id):
            self._log_error(f"Invalid team ID for operation '{operation}': {team_id}")
            return False
        
        # Operation-specific validation
        if operation == "score":
            # Only HOME and AWAY teams can score
            if team_id not in {TeamID.HOME, TeamID.AWAY}:
                self._log_error(f"Team {team_id} cannot score")
                return False
            
            # Check if team exists in context
            team_info = self.context.get_team_info(team_id)
            if team_info is None:
                self._log_error(f"No team information found for scoring team {team_id}")
                return False
                
        elif operation == "possess":
            # NEUTRAL can possess in special circumstances (kickoffs)
            if team_id not in {TeamID.HOME, TeamID.AWAY, TeamID.NEUTRAL}:
                self._log_error(f"Invalid team for possession: {team_id}")
                return False
                
        elif operation == "transition":
            # Validate possession changes
            from_team = context.get('from_team')
            to_team = context.get('to_team', team_id)
            
            if from_team == to_team and context.get('reason') not in {'continuation', 'timeout'}:
                # Log warning for unusual same-team transitions
                self._log_warning(f"Same-team transition: {from_team} -> {to_team} ({context.get('reason')})")
        
        # Log successful validation
        self._log_event({
            'event_type': 'operation_validation',
            'team_id': team_id,
            'operation': operation,
            'valid': True,
            'context': context
        })
        
        return True
    
    def get_team_info(self, team_id: TeamID) -> Optional[TeamInfo]:
        """
        Get complete team information
        
        Args:
            team_id: The team identifier
            
        Returns:
            TeamInfo: Complete team information, or None if not found
        """
        return self.context.get_team_info(team_id)
    
    def get_all_teams(self) -> List[TeamInfo]:
        """
        Get information for all teams in the game
        
        Returns:
            List[TeamInfo]: List of all team information
        """
        teams = []
        for team_id in [TeamID.HOME, TeamID.AWAY]:
            team_info = self.get_team_info(team_id)
            if team_info:
                teams.append(team_info)
        return teams
    
    def register_custom_possession_mapping(self, possession_id: Any, team_id: TeamID):
        """
        Register custom possession mapping and clear affected caches
        
        Args:
            possession_id: The possession identifier to map
            team_id: The target TeamID
        """
        self.context.register_possession_mapping(possession_id, team_id)
        
        # Clear cache entries that might be affected
        if possession_id in self._resolution_cache:
            del self._resolution_cache[possession_id]
        
        self._log_event({
            'event_type': 'custom_mapping_registered',
            'possession_id': possession_id,
            'team_id': team_id
        })
    
    def get_event_log(self, event_type: Optional[str] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get team operation event log for debugging
        
        Args:
            event_type: Optional filter by event type
            limit: Optional limit on number of events returned
            
        Returns:
            List[Dict]: Event log entries
        """
        events = self._event_log
        
        # Filter by event type if specified
        if event_type:
            events = [event for event in events if event.get('event_type') == event_type]
        
        # Limit results if specified
        if limit:
            events = events[-limit:]
        
        return events.copy()
    
    def get_operation_stats(self) -> Dict[str, Any]:
        """
        Get operation statistics for performance monitoring
        
        Returns:
            Dict: Operation statistics and cache information
        """
        return {
            'operation_counts': self._operation_counts.copy(),
            'cache_sizes': {
                'resolution_cache': len(self._resolution_cache),
                'scoreboard_cache': len(self._scoreboard_cache)
            },
            'event_log_size': len(self._event_log),
            'unknown_possession_ids': len(self.context.get_unknown_possession_ids())
        }
    
    def clear_caches(self):
        """Clear all caches (useful for testing or context changes)"""
        self._resolution_cache.clear()
        self._scoreboard_cache.clear()
        
        self._log_event({
            'event_type': 'caches_cleared'
        })
    
    def _validate_team_id(self, team_id: TeamID) -> bool:
        """Validate that team_id is a proper TeamID instance"""
        return isinstance(team_id, TeamID) and team_id in {TeamID.HOME, TeamID.AWAY, TeamID.NEUTRAL}
    
    def _log_event(self, event_data: Dict[str, Any]):
        """Log an event with timestamp"""
        event_entry = {
            'timestamp': self._get_timestamp(),
            **event_data
        }
        self._event_log.append(event_entry)
        
        # Limit log size to prevent memory issues
        if len(self._event_log) > 1000:
            self._event_log = self._event_log[-500:]  # Keep last 500 entries
    
    def _log_error(self, message: str, context: Dict[str, Any] = None):
        """Log an error event"""
        self._log_event({
            'event_type': 'error',
            'message': message,
            'context': context or {}
        })
    
    def _log_warning(self, message: str, context: Dict[str, Any] = None):
        """Log a warning event"""
        self._log_event({
            'event_type': 'warning', 
            'message': message,
            'context': context or {}
        })
    
    def _get_timestamp(self) -> str:
        """Get current timestamp for event logging"""
        return datetime.now().isoformat()
    
    def get_debug_info(self) -> Dict[str, Any]:
        """
        Get comprehensive debug information
        
        Returns:
            Dict: Complete debug information including context, stats, and logs
        """
        return {
            'team_context': self.context.get_debug_info(),
            'operation_stats': self.get_operation_stats(),
            'recent_events': self.get_event_log(limit=10),
            'cache_info': {
                'resolution_cache_keys': list(self._resolution_cache.keys())[:10],  # First 10
                'scoreboard_cache': dict(self._scoreboard_cache)
            }
        }
    
    def __str__(self) -> str:
        """String representation for debugging"""
        stats = self.get_operation_stats()
        return f"TeamRegistry(resolutions={stats['operation_counts']['possession_resolutions']}, cached={stats['cache_sizes']['resolution_cache']})"
    
    def __repr__(self) -> str:
        """Detailed representation for debugging"""
        return f"TeamRegistry(context={self.context!r}, operations={self._operation_counts})"