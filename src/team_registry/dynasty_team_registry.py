"""
Dynamic Dynasty Team Registry

Provides centralized, dynasty-specific team data management.
Solves team ID/name consistency issues by providing a single source of truth
that gets initialized per dynasty with flexible team mappings.
"""

from typing import Dict, Optional, Any, List
from dataclasses import dataclass
import json
from pathlib import Path


@dataclass
class TeamInfo:
    """Complete team information"""
    team_id: int
    city: str
    nickname: str
    full_name: str
    abbreviation: str
    conference: str
    division: str
    colors: Dict[str, str]
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TeamInfo':
        """Create TeamInfo from dictionary data"""
        return cls(
            team_id=data['team_id'],
            city=data['city'],
            nickname=data['nickname'],
            full_name=data['full_name'],
            abbreviation=data['abbreviation'],
            conference=data['conference'],
            division=data['division'],
            colors=data.get('colors', {})
        )


class DynastyTeamRegistry:
    """
    Dynasty-specific team registry providing centralized team data.
    
    This registry gets initialized once per dynasty with that dynasty's
    team configuration, ensuring consistent team ID/name mappings
    throughout the simulation.
    """
    
    _instance: Optional['DynastyTeamRegistry'] = None
    
    def __init__(self):
        """Private constructor - use get_instance() or initialize_dynasty()"""
        self._teams: Dict[int, TeamInfo] = {}
        self._name_to_id: Dict[str, int] = {}
        self._abbreviation_to_id: Dict[str, int] = {}
        self._initialized = False
        self._dynasty_name = ""
        self._season_year = 0
    
    @classmethod
    def get_instance(cls) -> 'DynastyTeamRegistry':
        """Get the current dynasty team registry instance"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    @classmethod
    def initialize_dynasty(
        cls, 
        dynasty_name: str, 
        season_year: int,
        team_config: str = "standard_nfl"
    ) -> 'DynastyTeamRegistry':
        """
        Initialize the registry for a new dynasty.
        
        Args:
            dynasty_name: Name of the dynasty
            season_year: Season year
            team_config: Team configuration type or custom mapping
                - "standard_nfl": Use standard NFL team mappings
                - dict: Custom team ID mappings
                - "randomize_ids": Randomize team IDs (for testing)
        
        Returns:
            The initialized registry instance
        """
        # Create or reset the singleton
        cls._instance = cls()
        registry = cls._instance
        
        # Store dynasty info
        registry._dynasty_name = dynasty_name
        registry._season_year = season_year
        
        # Load team configuration
        if team_config == "standard_nfl":
            registry._load_standard_nfl_teams()
        elif isinstance(team_config, dict):
            registry._load_custom_team_mapping(team_config)
        elif team_config == "randomize_ids":
            registry._load_randomized_teams()
        else:
            raise ValueError(f"Unknown team_config: {team_config}")
        
        # Build lookup indices
        registry._build_lookup_indices()
        registry._initialized = True
        
        print(f"✅ Dynasty Team Registry initialized: {dynasty_name} ({season_year})")
        print(f"   Loaded {len(registry._teams)} teams")
        
        return registry
    
    def _load_standard_nfl_teams(self) -> None:
        """Load standard NFL team mappings from teams.json"""
        teams_file = Path("src/data/teams.json")
        
        # Handle different execution contexts
        if not teams_file.exists():
            teams_file = Path(__file__).parent.parent / "data" / "teams.json"
        
        if not teams_file.exists():
            raise FileNotFoundError(f"Teams file not found: {teams_file}")
        
        with open(teams_file, 'r') as f:
            data = json.load(f)
        
        # Handle nested structure
        teams_data = data.get("teams", data)
        
        for team_id_str, team_data in teams_data.items():
            team_id = int(team_id_str)
            team_info = TeamInfo.from_dict(team_data)
            self._teams[team_id] = team_info
    
    def _load_custom_team_mapping(self, team_mapping: Dict[str, int]) -> None:
        """Load custom team ID mappings"""
        # First load standard team data
        self._load_standard_nfl_teams()
        
        # Then remap team IDs according to custom mapping
        remapped_teams = {}
        
        for team_name, new_team_id in team_mapping.items():
            # Find team by name in existing data
            old_team = None
            for team in self._teams.values():
                if (team_name.lower() in team.full_name.lower() or
                    team_name.lower() == team.nickname.lower() or
                    team_name.lower() == team.abbreviation.lower()):
                    old_team = team
                    break
            
            if old_team:
                # Create new team with remapped ID
                new_team = TeamInfo(
                    team_id=new_team_id,
                    city=old_team.city,
                    nickname=old_team.nickname,
                    full_name=old_team.full_name,
                    abbreviation=old_team.abbreviation,
                    conference=old_team.conference,
                    division=old_team.division,
                    colors=old_team.colors
                )
                remapped_teams[new_team_id] = new_team
        
        # Replace teams with remapped versions
        self._teams = remapped_teams
    
    def _load_randomized_teams(self) -> None:
        """Load teams with randomized IDs for testing"""
        import random
        
        # Load standard teams first
        self._load_standard_nfl_teams()
        
        # Create randomized ID mapping
        team_list = list(self._teams.values())
        random_ids = random.sample(range(1, 101), len(team_list))
        
        randomized_teams = {}
        for team, new_id in zip(team_list, random_ids):
            new_team = TeamInfo(
                team_id=new_id,
                city=team.city,
                nickname=team.nickname,
                full_name=team.full_name,
                abbreviation=team.abbreviation,
                conference=team.conference,
                division=team.division,
                colors=team.colors
            )
            randomized_teams[new_id] = new_team
        
        self._teams = randomized_teams
    
    def _build_lookup_indices(self) -> None:
        """Build lookup indices for fast team access"""
        self._name_to_id.clear()
        self._abbreviation_to_id.clear()
        
        for team_id, team in self._teams.items():
            # Index by various name formats
            self._name_to_id[team.full_name.lower()] = team_id
            self._name_to_id[team.nickname.lower()] = team_id
            self._name_to_id[team.city.lower()] = team_id
            
            # Index by abbreviation
            self._abbreviation_to_id[team.abbreviation.upper()] = team_id
    
    def is_initialized(self) -> bool:
        """Check if registry is initialized"""
        return self._initialized
    
    def get_team_by_id(self, team_id: int) -> Optional[TeamInfo]:
        """Get team by ID"""
        if not self._initialized:
            raise RuntimeError("Registry not initialized. Call initialize_dynasty() first.")
        return self._teams.get(team_id)
    
    def get_team_by_name(self, team_name: str) -> Optional[TeamInfo]:
        """Get team by name (supports full name, city, or nickname)"""
        if not self._initialized:
            raise RuntimeError("Registry not initialized. Call initialize_dynasty() first.")
        team_id = self._name_to_id.get(team_name.lower())
        return self._teams.get(team_id) if team_id else None
    
    def get_team_by_abbreviation(self, abbreviation: str) -> Optional[TeamInfo]:
        """Get team by abbreviation"""
        if not self._initialized:
            raise RuntimeError("Registry not initialized. Call initialize_dynasty() first.")
        team_id = self._abbreviation_to_id.get(abbreviation.upper())
        return self._teams.get(team_id) if team_id else None
    
    def get_team_id_by_name(self, team_name: str) -> Optional[int]:
        """Get team ID by name"""
        team = self.get_team_by_name(team_name)
        return team.team_id if team else None
    
    def get_team_abbreviation(self, team_id: int) -> str:
        """Get team abbreviation by ID"""
        team = self.get_team_by_id(team_id)
        return team.abbreviation if team else f"T{team_id}"
    
    def get_team_full_name(self, team_id: int) -> str:
        """Get team full name by ID"""
        team = self.get_team_by_id(team_id)
        return team.full_name if team else f"Team {team_id}"
    
    def validate_matchup(self, away_team_id: int, home_team_id: int) -> bool:
        """Validate that a matchup uses valid team IDs"""
        return (self.get_team_by_id(away_team_id) is not None and 
                self.get_team_by_id(home_team_id) is not None and
                away_team_id != home_team_id)
    
    def get_all_team_ids(self) -> List[int]:
        """Get all team IDs"""
        return list(self._teams.keys())
    
    def get_all_teams(self) -> List[TeamInfo]:
        """Get all teams"""
        return list(self._teams.values())
    
    def get_dynasty_info(self) -> Dict[str, Any]:
        """Get dynasty information"""
        return {
            'dynasty_name': self._dynasty_name,
            'season_year': self._season_year,
            'team_count': len(self._teams),
            'initialized': self._initialized
        }
    
    def __len__(self) -> int:
        """Get number of teams"""
        return len(self._teams)


# Convenience functions for global access
def get_registry() -> DynastyTeamRegistry:
    """Get the current dynasty team registry"""
    return DynastyTeamRegistry.get_instance()


def initialize_dynasty_teams(dynasty_name: str, season_year: int, team_config: str = "standard_nfl") -> DynastyTeamRegistry:
    """Initialize dynasty team registry - convenience function"""
    return DynastyTeamRegistry.initialize_dynasty(dynasty_name, season_year, team_config)