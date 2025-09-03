"""
Core Team Type System

Provides standardized team identification types that eliminate the type mismatches
causing the scoreboard bug. All team operations throughout the system should use
these types for consistency and type safety.

Key Types:
- TeamSide: Enum for team sides (HOME, AWAY, NEUTRAL)
- TeamID: IntEnum for standardized team identifiers with conversion utilities
- TeamInfo: Dataclass for complete team information

Usage:
    from game_engine.teams.team_types import TeamID, TeamSide, TeamInfo
    
    # Convert various formats to TeamID
    team = TeamID.from_any("home")  # Returns TeamID.HOME
    team = TeamID.from_any(1)       # Returns TeamID.HOME
    team = TeamID.from_any("2")     # Returns TeamID.AWAY
    
    # Get team side
    side = team.to_side()  # Returns TeamSide.HOME
"""

from enum import Enum, IntEnum
from dataclasses import dataclass
from typing import Optional, Dict, Any, Union


class TeamSide(Enum):
    """Team sides in a football game"""
    HOME = "home"
    AWAY = "away"  
    NEUTRAL = "neutral"  # For kickoffs, neutral possessions, special situations


class TeamID(IntEnum):
    """
    Standardized team identifiers
    
    Uses IntEnum for backward compatibility with existing integer-based code
    while providing type safety and conversion utilities.
    """
    NEUTRAL = 0  # For neutral possessions, kickoffs, special situations
    HOME = 1     # Home team (replaces various "1", "home" formats)
    AWAY = 2     # Away team (replaces various "2", "away" formats)
    
    @classmethod
    def from_any(cls, value: Union[int, str, 'TeamID']) -> 'TeamID':
        """
        Convert various formats to TeamID
        
        Handles the multiple formats currently used in the codebase:
        - Integers: 0, 1, 2
        - Strings: "0", "1", "2", "home", "away", "neutral"
        - TeamID instances: pass-through
        
        Args:
            value: Value to convert to TeamID
            
        Returns:
            TeamID: Standardized team identifier
            
        Raises:
            ValueError: If value cannot be converted to valid TeamID
            TypeError: If value type is not supported
        """
        if isinstance(value, cls):
            return value
            
        if isinstance(value, str):
            # Handle string representations
            value_lower = value.lower().strip()
            
            if value_lower == "home":
                return cls.HOME
            elif value_lower == "away":
                return cls.AWAY
            elif value_lower == "neutral":
                return cls.NEUTRAL
            else:
                # Try to convert string number
                try:
                    return cls(int(value_lower))
                except (ValueError, TypeError):
                    raise ValueError(f"Cannot convert string '{value}' to TeamID")
                    
        elif isinstance(value, int):
            # Handle integer values
            try:
                return cls(value)
            except ValueError:
                raise ValueError(f"Invalid TeamID integer: {value}. Valid values: 0 (NEUTRAL), 1 (HOME), 2 (AWAY)")
                
        else:
            raise TypeError(f"Cannot convert {type(value)} to TeamID. Supported types: int, str, TeamID")
    
    def to_side(self) -> TeamSide:
        """
        Convert TeamID to corresponding TeamSide
        
        Returns:
            TeamSide: Corresponding team side
        """
        if self == TeamID.HOME:
            return TeamSide.HOME
        elif self == TeamID.AWAY:
            return TeamSide.AWAY
        else:
            return TeamSide.NEUTRAL
    
    def to_scoreboard_field(self) -> str:
        """
        Convert TeamID to scoreboard field name
        
        This is a convenience method for the common operation of mapping
        team IDs to scoreboard field names.
        
        Returns:
            str: Scoreboard field name ("home" or "away")
            
        Raises:
            ValueError: If team is NEUTRAL (cannot score)
        """
        if self == TeamID.HOME:
            return "home"
        elif self == TeamID.AWAY:
            return "away"
        else:
            raise ValueError(f"Neutral team (TeamID.NEUTRAL) cannot be mapped to scoreboard")
    
    def get_opponent(self) -> 'TeamID':
        """
        Get the opposing team
        
        Returns:
            TeamID: The opposing team
            
        Raises:
            ValueError: If team is NEUTRAL (has no opponent)
        """
        if self == TeamID.HOME:
            return TeamID.AWAY
        elif self == TeamID.AWAY:
            return TeamID.HOME
        else:
            raise ValueError(f"Neutral team (TeamID.NEUTRAL) has no opponent")


@dataclass
class TeamInfo:
    """
    Complete team information for a game
    
    Contains all relevant information about a team participating in a game,
    including identification, display information, and extensible metadata.
    """
    team_id: TeamID
    side: TeamSide
    name: str
    abbreviation: str
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        """Initialize optional fields with defaults"""
        if self.metadata is None:
            self.metadata = {}
    
    def is_home_team(self) -> bool:
        """Check if this is the home team"""
        return self.team_id == TeamID.HOME
    
    def is_away_team(self) -> bool:
        """Check if this is the away team"""
        return self.team_id == TeamID.AWAY
    
    def is_neutral(self) -> bool:
        """Check if this represents a neutral entity"""
        return self.team_id == TeamID.NEUTRAL
    
    def get_opponent_id(self) -> TeamID:
        """Get the opponent's TeamID"""
        return self.team_id.get_opponent()
    
    def get_display_name(self, format_type: str = "full") -> str:
        """
        Get formatted team name for display
        
        Args:
            format_type: Format type ("full", "abbrev", "short")
            
        Returns:
            str: Formatted team name
        """
        if format_type == "abbrev" or format_type == "short":
            return self.abbreviation
        elif format_type == "full":
            return self.name
        else:
            return f"{self.abbreviation} ({self.name})"
    
    def add_metadata(self, key: str, value: Any):
        """Add metadata entry"""
        self.metadata[key] = value
    
    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get metadata entry with optional default"""
        return self.metadata.get(key, default)
    
    def __str__(self) -> str:
        """String representation for debugging"""
        return f"{self.name} ({self.abbreviation}) - {self.side.value.title()} Team (ID: {self.team_id})"
    
    def __repr__(self) -> str:
        """Detailed representation for debugging"""
        return f"TeamInfo(team_id={self.team_id}, side={self.side}, name='{self.name}', abbreviation='{self.abbreviation}')"