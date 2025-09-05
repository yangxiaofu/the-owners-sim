"""
Team Data Loader for NFL Teams

Manages loading and access to team data from JSON configuration files.
Provides methods to look up teams by numerical ID, division, conference, etc.
"""

import json
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass


@dataclass
class Team:
    """Represents an NFL team with all metadata"""
    team_id: int
    city: str
    nickname: str
    full_name: str
    abbreviation: str
    conference: str
    division: str
    colors: Dict[str, str]
    
    def __str__(self):
        return self.full_name
    
    def __repr__(self):
        return f"Team(id={self.team_id}, name='{self.full_name}', abbrev='{self.abbreviation}')"


class TeamDataLoader:
    """Loads and manages NFL team data from JSON configuration"""
    
    def __init__(self, teams_file_path: Optional[str] = None):
        """
        Initialize team data loader
        
        Args:
            teams_file_path: Path to teams.json file. If None, uses default location.
        """
        if teams_file_path is None:
            # Default to teams.json in the data directory (go up to src level)
            current_dir = os.path.dirname(os.path.abspath(__file__))
            src_dir = os.path.dirname(os.path.dirname(current_dir))  # Go up from teams/ to team_management/ to src/
            teams_file_path = os.path.join(src_dir, 'data', 'teams.json')
        
        self.teams_file_path = teams_file_path
        self._teams_data = None
        self._teams_by_id = {}
        self._load_teams_data()
    
    def _load_teams_data(self):
        """Load teams data from JSON file"""
        try:
            with open(self.teams_file_path, 'r') as f:
                self._teams_data = json.load(f)
            
            # Create Team objects and index by ID
            teams_dict = self._teams_data.get('teams', {})
            for team_id_str, team_data in teams_dict.items():
                team = Team(
                    team_id=team_data['team_id'],
                    city=team_data['city'],
                    nickname=team_data['nickname'],
                    full_name=team_data['full_name'],
                    abbreviation=team_data['abbreviation'],
                    conference=team_data['conference'],
                    division=team_data['division'],
                    colors=team_data.get('colors', {})
                )
                self._teams_by_id[team.team_id] = team
                
        except FileNotFoundError:
            raise FileNotFoundError(f"Teams data file not found: {self.teams_file_path}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in teams data file: {e}")
        except KeyError as e:
            raise ValueError(f"Missing required field in teams data: {e}")
    
    def get_team_by_id(self, team_id: int) -> Optional[Team]:
        """
        Get team by numerical ID
        
        Args:
            team_id: Numerical team ID (1-32)
            
        Returns:
            Team object or None if not found
        """
        return self._teams_by_id.get(team_id)
    
    def get_team_by_abbreviation(self, abbreviation: str) -> Optional[Team]:
        """
        Get team by abbreviation (e.g., 'DET', 'WAS')
        
        Args:
            abbreviation: Team abbreviation
            
        Returns:
            Team object or None if not found
        """
        for team in self._teams_by_id.values():
            if team.abbreviation.upper() == abbreviation.upper():
                return team
        return None
    
    def get_all_teams(self) -> List[Team]:
        """
        Get all teams
        
        Returns:
            List of all Team objects
        """
        return list(self._teams_by_id.values())
    
    def get_teams_by_conference(self, conference: str) -> List[Team]:
        """
        Get teams by conference
        
        Args:
            conference: 'AFC' or 'NFC'
            
        Returns:
            List of Team objects in the conference
        """
        return [team for team in self._teams_by_id.values() 
                if team.conference.upper() == conference.upper()]
    
    def get_teams_by_division(self, conference: str, division: str) -> List[Team]:
        """
        Get teams by division
        
        Args:
            conference: 'AFC' or 'NFC'
            division: 'East', 'North', 'South', or 'West'
            
        Returns:
            List of Team objects in the division
        """
        return [team for team in self._teams_by_id.values() 
                if (team.conference.upper() == conference.upper() and 
                    team.division.upper() == division.upper())]
    
    def get_division_rivals(self, team_id: int) -> List[Team]:
        """
        Get division rivals for a team
        
        Args:
            team_id: Team ID to find rivals for
            
        Returns:
            List of Team objects in the same division (excluding the input team)
        """
        team = self.get_team_by_id(team_id)
        if not team:
            return []
        
        division_teams = self.get_teams_by_division(team.conference, team.division)
        return [t for t in division_teams if t.team_id != team_id]
    
    def validate_team_id(self, team_id: int) -> bool:
        """
        Validate that a team ID exists
        
        Args:
            team_id: Team ID to validate
            
        Returns:
            True if valid, False otherwise
        """
        return team_id in self._teams_by_id
    
    def get_team_ids(self) -> List[int]:
        """
        Get all valid team IDs
        
        Returns:
            List of all numerical team IDs
        """
        return list(self._teams_by_id.keys())
    
    def get_random_matchup(self) -> tuple[Team, Team]:
        """
        Get a random matchup of two teams
        
        Returns:
            Tuple of (home_team, away_team)
        """
        import random
        all_teams = self.get_all_teams()
        return tuple(random.sample(all_teams, 2))
    
    def search_teams(self, query: str) -> List[Team]:
        """
        Search teams by city, nickname, or full name
        
        Args:
            query: Search query string
            
        Returns:
            List of matching Team objects
        """
        query_lower = query.lower()
        matches = []
        
        for team in self._teams_by_id.values():
            if (query_lower in team.city.lower() or
                query_lower in team.nickname.lower() or
                query_lower in team.full_name.lower() or
                query_lower in team.abbreviation.lower()):
                matches.append(team)
        
        return matches
    
    def get_metadata(self) -> Dict[str, Any]:
        """
        Get metadata about the teams data
        
        Returns:
            Dictionary with metadata information
        """
        return self._teams_data.get('metadata', {})
    
    def __len__(self):
        """Return number of teams"""
        return len(self._teams_by_id)
    
    def __str__(self):
        return f"TeamDataLoader with {len(self._teams_by_id)} NFL teams"


# Global instance for easy access throughout the codebase
_global_team_loader = None

def get_team_loader() -> TeamDataLoader:
    """
    Get global team data loader instance
    
    Returns:
        Singleton TeamDataLoader instance
    """
    global _global_team_loader
    if _global_team_loader is None:
        _global_team_loader = TeamDataLoader()
    return _global_team_loader


def get_team_by_id(team_id: int) -> Optional[Team]:
    """
    Convenience function to get team by ID using global loader
    
    Args:
        team_id: Numerical team ID
        
    Returns:
        Team object or None if not found
    """
    return get_team_loader().get_team_by_id(team_id)


def get_all_teams() -> List[Team]:
    """
    Convenience function to get all teams using global loader
    
    Returns:
        List of all Team objects
    """
    return get_team_loader().get_all_teams()


# Example usage and testing
if __name__ == "__main__":
    # Test the team data loader
    loader = TeamDataLoader()
    
    print(f"Loaded {len(loader)} teams")
    print()
    
    # Test team lookup by ID
    lions = loader.get_team_by_id(22)
    print(f"Team ID 22: {lions}")
    
    commanders = loader.get_team_by_id(20)  
    print(f"Team ID 20: {commanders}")
    print()
    
    # Test division lookup
    nfc_north = loader.get_teams_by_division('NFC', 'North')
    print("NFC North teams:")
    for team in nfc_north:
        print(f"  {team.team_id}: {team}")
    print()
    
    # Test search
    chicago_teams = loader.search_teams('chicago')
    print(f"Teams matching 'chicago': {chicago_teams}")
    
    # Test rivals
    if lions:
        rivals = loader.get_division_rivals(lions.team_id)
        print(f"Detroit Lions division rivals:")
        for rival in rivals:
            print(f"  {rival}")