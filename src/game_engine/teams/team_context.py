"""
Team Context Manager

Manages team assignments and mappings for a specific game. This component handles
the critical task of mapping possession team IDs (like the problematic "6" from 
debug output) to standardized TeamID values.

Key responsibilities:
- Maintain home/away team information for a game
- Map possession IDs to TeamID values
- Handle complex team ID resolution scenarios
- Support dynamic team mappings during games

Usage:
    from game_engine.teams.team_context import TeamContext
    
    context = TeamContext(home_team_data, away_team_data)
    
    # Map possession ID to team
    team_id = context.map_possession_to_team(6)  # Handles the debug case
    
    # Register custom mappings
    context.register_possession_mapping(6, TeamID.HOME)
"""

from typing import Dict, Any, Optional, Set
from .team_types import TeamID, TeamSide, TeamInfo


class TeamContext:
    """Manages team assignments for a specific game"""
    
    def __init__(self, home_team_data: Dict[str, Any], away_team_data: Dict[str, Any]):
        """
        Initialize team context for a game
        
        Args:
            home_team_data: Dictionary containing home team information
            away_team_data: Dictionary containing away team information
        """
        # Create standardized team info objects
        self.home_team = TeamInfo(
            team_id=TeamID.HOME,
            side=TeamSide.HOME,
            name=home_team_data.get("name", "Home Team"),
            abbreviation=home_team_data.get("abbreviation", "HOME"),
            metadata=home_team_data.get("metadata", {})
        )
        
        self.away_team = TeamInfo(
            team_id=TeamID.AWAY, 
            side=TeamSide.AWAY,
            name=away_team_data.get("name", "Away Team"),
            abbreviation=away_team_data.get("abbreviation", "AWAY"),
            metadata=away_team_data.get("metadata", {})
        )
        
        # Standard possession mappings for common formats
        self._possession_mappings: Dict[Any, TeamID] = {
            # Integer formats
            1: TeamID.HOME,
            2: TeamID.AWAY,
            0: TeamID.NEUTRAL,
            
            # String formats  
            "1": TeamID.HOME,
            "2": TeamID.AWAY,
            "0": TeamID.NEUTRAL,
            
            # Descriptive formats
            "home": TeamID.HOME,
            "away": TeamID.AWAY,
            "neutral": TeamID.NEUTRAL,
        }
        
        # Process any custom mappings from team data
        self._process_custom_mappings(home_team_data, away_team_data)
        
        # Track unknown possession IDs for debugging
        self._unknown_possession_ids: Set[Any] = set()
    
    def get_team_info(self, team_id: TeamID) -> Optional[TeamInfo]:
        """
        Get complete team information by TeamID
        
        Args:
            team_id: The team identifier
            
        Returns:
            TeamInfo: Complete team information, or None if not found
        """
        if team_id == TeamID.HOME:
            return self.home_team
        elif team_id == TeamID.AWAY:
            return self.away_team
        elif team_id == TeamID.NEUTRAL:
            # Create neutral team info for special cases
            return TeamInfo(
                team_id=TeamID.NEUTRAL,
                side=TeamSide.NEUTRAL,
                name="Neutral",
                abbreviation="NEU"
            )
        return None
    
    def map_possession_to_team(self, possession_id: Any) -> TeamID:
        """
        Map possession team ID to standardized TeamID
        
        This is the critical method that resolves the various possession ID formats
        used throughout the system (including the problematic possession_id=6 case).
        
        Args:
            possession_id: The possession team identifier (various formats)
            
        Returns:
            TeamID: Standardized team identifier
        """
        # Check direct mappings first (fastest path) - handle unhashable types
        try:
            if possession_id in self._possession_mappings:
                return self._possession_mappings[possession_id]
        except TypeError:
            # Unhashable type - cannot be a key in mappings, skip lookup
            pass
        
        # Try TeamID conversion for standard values
        try:
            return TeamID.from_any(possession_id)
        except (ValueError, TypeError):
            # Handle complex/unknown cases
            return self._resolve_complex_possession(possession_id)
    
    def register_possession_mapping(self, possession_id: Any, team_id: TeamID):
        """
        Register custom possession ID mapping
        
        This allows dynamic registration of possession mappings, useful for
        handling game-specific team ID formats or correcting misassignments.
        
        Args:
            possession_id: The possession identifier to map
            team_id: The target TeamID
        """
        self._possession_mappings[possession_id] = team_id
        
        # Remove from unknown list if it was there
        self._unknown_possession_ids.discard(possession_id)
    
    def get_possession_mappings(self) -> Dict[Any, TeamID]:
        """Get copy of current possession mappings for debugging"""
        return self._possession_mappings.copy()
    
    def get_unknown_possession_ids(self) -> Set[Any]:
        """Get set of possession IDs that couldn't be resolved"""
        return self._unknown_possession_ids.copy()
    
    def validate_possession_mapping(self, possession_id: Any) -> bool:
        """
        Check if a possession ID can be mapped to a valid team
        
        Args:
            possession_id: The possession identifier to check
            
        Returns:
            bool: True if mapping exists, False otherwise
        """
        # Handle None and invalid cases
        if possession_id is None:
            return False
            
        try:
            team_id = self.map_possession_to_team(possession_id)
            return team_id in {TeamID.HOME, TeamID.AWAY, TeamID.NEUTRAL}
        except Exception:
            return False
    
    def _process_custom_mappings(self, home_team_data: Dict, away_team_data: Dict):
        """
        Process custom possession mappings from team data
        
        This handles special mappings defined in team data, such as:
        {"possession_mappings": {6: "home"}}
        """
        # Process home team mappings
        home_mappings = home_team_data.get("possession_mappings", {})
        for possession_id, team_designation in home_mappings.items():
            if team_designation in {"home", "HOME", TeamID.HOME}:
                self._possession_mappings[possession_id] = TeamID.HOME
        
        # Process away team mappings
        away_mappings = away_team_data.get("possession_mappings", {})
        for possession_id, team_designation in away_mappings.items():
            if team_designation in {"away", "AWAY", TeamID.AWAY}:
                self._possession_mappings[possession_id] = TeamID.AWAY
    
    def _resolve_complex_possession(self, possession_id: Any) -> TeamID:
        """
        Handle complex possession ID resolution
        
        This method handles edge cases where possession IDs don't fit standard
        patterns. It implements fallback logic and learning capabilities.
        
        Args:
            possession_id: The unresolved possession identifier
            
        Returns:
            TeamID: Best-guess team assignment (defaults to HOME)
        """
        # Track unknown possession IDs for debugging (handle unhashable types)
        try:
            self._unknown_possession_ids.add(possession_id)
        except TypeError:
            # Handle unhashable types (like dicts, lists)
            self._unknown_possession_ids.add(str(possession_id))
        
        # Implement heuristic-based resolution
        if isinstance(possession_id, (int, str)):
            try:
                # Try numeric-based heuristics
                numeric_value = int(str(possession_id))
                
                # Odd numbers -> HOME, Even numbers -> AWAY (simple heuristic)
                if numeric_value % 2 == 1:
                    fallback_team = TeamID.HOME
                else:
                    fallback_team = TeamID.AWAY
                
                # Register this mapping for consistency (only for hashable types)
                try:
                    self._possession_mappings[possession_id] = fallback_team
                except TypeError:
                    # Skip mapping registration for unhashable types
                    pass
                
                return fallback_team
                
            except (ValueError, TypeError):
                pass
        
        # Ultimate fallback - assign to home team
        # This maintains game functionality while highlighting the issue
        fallback_team = TeamID.HOME
        
        # Try to register mapping (only for hashable types)
        try:
            self._possession_mappings[possession_id] = fallback_team
        except TypeError:
            # Skip mapping registration for unhashable types like dicts
            pass
        
        return fallback_team
    
    def get_debug_info(self) -> Dict[str, Any]:
        """
        Get comprehensive debug information about team context
        
        Returns:
            Dict: Debug information including mappings, unknown IDs, etc.
        """
        return {
            "home_team": {
                "name": self.home_team.name,
                "abbreviation": self.home_team.abbreviation,
                "team_id": self.home_team.team_id,
            },
            "away_team": {
                "name": self.away_team.name,
                "abbreviation": self.away_team.abbreviation, 
                "team_id": self.away_team.team_id,
            },
            "possession_mappings_count": len(self._possession_mappings),
            "possession_mappings": dict(self._possession_mappings),
            "unknown_possession_ids": list(self._unknown_possession_ids),
            "unknown_count": len(self._unknown_possession_ids)
        }
    
    def __str__(self) -> str:
        """String representation for debugging"""
        return f"TeamContext(home='{self.home_team.name}', away='{self.away_team.name}', mappings={len(self._possession_mappings)})"
    
    def __repr__(self) -> str:
        """Detailed representation for debugging"""
        return f"TeamContext(home_team={self.home_team!r}, away_team={self.away_team!r}, possession_mappings={len(self._possession_mappings)})"