"""
Player Data Loader for Real NFL Players

Manages loading and access to real player data from JSON configuration files.
Provides methods to look up players by ID, team, position, name, etc.
Currently supports Cleveland Browns (team_id: 7) and San Francisco 49ers (team_id: 31).
"""

import json
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass


@dataclass
class RealPlayer:
    """Represents a real NFL player with comprehensive attributes"""
    player_id: int
    first_name: str
    last_name: str
    number: int
    positions: List[str]
    team_id: int
    attributes: Dict[str, Any]
    
    @property
    def full_name(self) -> str:
        """Get player's full name"""
        return f"{self.first_name} {self.last_name}"
    
    @property
    def primary_position(self) -> str:
        """Get player's primary (first listed) position"""
        return self.positions[0] if self.positions else "unknown"
    
    @property
    def jersey_display(self) -> str:
        """Get jersey number display format"""
        return f"#{self.number}"
    
    @property
    def overall_rating(self) -> int:
        """Get overall rating attribute"""
        return self.attributes.get('overall', 75)
    
    def has_position(self, position: str) -> bool:
        """Check if player can play a specific position"""
        return position in self.positions
    
    def get_attribute(self, attribute_name: str, default: Any = 0) -> Any:
        """Get a specific attribute value"""
        return self.attributes.get(attribute_name, default)
    
    def __str__(self):
        return f"{self.full_name} #{self.number} ({self.primary_position})"
    
    def __repr__(self):
        return f"RealPlayer(id={self.player_id}, name='{self.full_name}', pos='{self.primary_position}')"


class PlayerDataLoader:
    """Loads and manages real NFL player data from JSON configuration"""
    
    def __init__(self, players_file_path: Optional[str] = None):
        """
        Initialize player data loader
        
        Args:
            players_file_path: Path to players.json file. If None, uses default location.
        """
        if players_file_path is None:
            # Default to players.json in the data directory (go up to src level)
            current_dir = os.path.dirname(os.path.abspath(__file__))
            src_dir = os.path.dirname(os.path.dirname(current_dir))  # Go up from players/ to team_management/ to src/
            players_file_path = os.path.join(src_dir, 'data', 'players.json')
        
        self.players_file_path = players_file_path
        self._players_data = None
        self._players_by_id = {}
        self._players_by_team = {}
        self._players_by_position = {}
        self._load_players_data()
    
    def _load_players_data(self):
        """Load players data from JSON file"""
        try:
            with open(self.players_file_path, 'r') as f:
                self._players_data = json.load(f)
            
            # Create RealPlayer objects and index them
            players_dict = self._players_data.get('players', {})
            for player_id_str, player_data in players_dict.items():
                player = RealPlayer(
                    player_id=player_data['player_id'],
                    first_name=player_data['first_name'],
                    last_name=player_data['last_name'],
                    number=player_data['number'],
                    positions=player_data['positions'],
                    team_id=player_data['team_id'],
                    attributes=player_data['attributes']
                )
                
                # Index by ID
                self._players_by_id[player.player_id] = player
                
                # Index by team
                if player.team_id not in self._players_by_team:
                    self._players_by_team[player.team_id] = []
                self._players_by_team[player.team_id].append(player)
                
                # Index by position
                for position in player.positions:
                    if position not in self._players_by_position:
                        self._players_by_position[position] = []
                    self._players_by_position[position].append(player)
                    
        except FileNotFoundError:
            raise FileNotFoundError(f"Players data file not found: {self.players_file_path}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in players data file: {e}")
        except KeyError as e:
            raise ValueError(f"Missing required field in players data: {e}")
    
    def get_player_by_id(self, player_id: int) -> Optional[RealPlayer]:
        """
        Get player by numerical ID
        
        Args:
            player_id: Numerical player ID
            
        Returns:
            RealPlayer object or None if not found
        """
        return self._players_by_id.get(player_id)
    
    def get_players_by_team(self, team_id: int) -> List[RealPlayer]:
        """
        Get all players for a specific team
        
        Args:
            team_id: Team ID (7 for Browns, 31 for 49ers)
            
        Returns:
            List of RealPlayer objects for the team
        """
        return self._players_by_team.get(team_id, [])
    
    def get_players_by_position(self, position: str) -> List[RealPlayer]:
        """
        Get all players who can play a specific position
        
        Args:
            position: Position string (e.g., "quarterback", "running_back")
            
        Returns:
            List of RealPlayer objects who can play that position
        """
        return self._players_by_position.get(position, [])
    
    def get_team_players_by_position(self, team_id: int, position: str) -> List[RealPlayer]:
        """
        Get players from a specific team who can play a specific position
        
        Args:
            team_id: Team ID
            position: Position string
            
        Returns:
            List of RealPlayer objects
        """
        team_players = self.get_players_by_team(team_id)
        return [player for player in team_players if player.has_position(position)]
    
    def search_players_by_name(self, query: str) -> List[RealPlayer]:
        """
        Search players by first name, last name, or full name
        
        Args:
            query: Search query string
            
        Returns:
            List of matching RealPlayer objects
        """
        query_lower = query.lower()
        matches = []
        
        for player in self._players_by_id.values():
            if (query_lower in player.first_name.lower() or
                query_lower in player.last_name.lower() or
                query_lower in player.full_name.lower()):
                matches.append(player)
        
        return matches
    
    def get_players_by_jersey_number(self, number: int, team_id: Optional[int] = None) -> List[RealPlayer]:
        """
        Get players by jersey number, optionally filtered by team
        
        Args:
            number: Jersey number
            team_id: Optional team ID to filter by
            
        Returns:
            List of RealPlayer objects with that number
        """
        matches = []
        players_to_search = (self.get_players_by_team(team_id) if team_id 
                           else self._players_by_id.values())
        
        for player in players_to_search:
            if player.number == number:
                matches.append(player)
        
        return matches
    
    def get_top_players_by_attribute(self, attribute: str, limit: int = 10, 
                                   team_id: Optional[int] = None, 
                                   position: Optional[str] = None) -> List[RealPlayer]:
        """
        Get top players by a specific attribute rating
        
        Args:
            attribute: Attribute name (e.g., 'overall', 'speed', 'strength')
            limit: Maximum number of players to return
            team_id: Optional team ID filter
            position: Optional position filter
            
        Returns:
            List of top RealPlayer objects sorted by attribute (highest first)
        """
        # Get player pool based on filters
        if team_id and position:
            players = self.get_team_players_by_position(team_id, position)
        elif team_id:
            players = self.get_players_by_team(team_id)
        elif position:
            players = self.get_players_by_position(position)
        else:
            players = list(self._players_by_id.values())
        
        # Sort by attribute (highest first)
        sorted_players = sorted(players, 
                              key=lambda p: p.get_attribute(attribute, 0), 
                              reverse=True)
        
        return sorted_players[:limit]
    
    def get_available_teams(self) -> List[int]:
        """
        Get list of team IDs that have real player data
        
        Returns:
            List of team IDs with player data
        """
        return list(self._players_by_team.keys())
    
    def get_available_positions(self) -> List[str]:
        """
        Get list of all positions that have real player data
        
        Returns:
            List of position strings
        """
        return list(self._players_by_position.keys())
    
    def has_real_data_for_team(self, team_id: int) -> bool:
        """
        Check if real player data exists for a team
        
        Args:
            team_id: Team ID to check
            
        Returns:
            True if real data exists, False otherwise
        """
        return team_id in self._players_by_team and len(self._players_by_team[team_id]) > 0
    
    def get_team_roster_summary(self, team_id: int) -> Dict[str, Any]:
        """
        Get summary information about a team's roster
        
        Args:
            team_id: Team ID
            
        Returns:
            Dictionary with roster summary information
        """
        players = self.get_players_by_team(team_id)
        
        if not players:
            return {"error": f"No real player data for team {team_id}"}
        
        # Position counts
        position_counts = {}
        for player in players:
            for position in player.positions:
                position_counts[position] = position_counts.get(position, 0) + 1
        
        # Overall rating distribution
        ratings = [player.overall_rating for player in players]
        
        return {
            "team_id": team_id,
            "total_players": len(players),
            "position_counts": position_counts,
            "avg_overall_rating": sum(ratings) / len(ratings) if ratings else 0,
            "highest_rated_player": max(players, key=lambda p: p.overall_rating) if players else None,
            "lowest_rated_player": min(players, key=lambda p: p.overall_rating) if players else None
        }
    
    def get_metadata(self) -> Dict[str, Any]:
        """
        Get metadata about the player data
        
        Returns:
            Dictionary with metadata information
        """
        return self._players_data.get('metadata', {})
    
    def __len__(self):
        """Return total number of players"""
        return len(self._players_by_id)
    
    def __str__(self):
        return f"PlayerDataLoader with {len(self._players_by_id)} real players"


# Global instance for easy access throughout the codebase
_global_player_loader = None

def get_player_loader() -> PlayerDataLoader:
    """
    Get global player data loader instance
    
    Returns:
        Singleton PlayerDataLoader instance
    """
    global _global_player_loader
    if _global_player_loader is None:
        _global_player_loader = PlayerDataLoader()
    return _global_player_loader


def get_real_player_by_id(player_id: int) -> Optional[RealPlayer]:
    """
    Convenience function to get player by ID using global loader
    
    Args:
        player_id: Numerical player ID
        
    Returns:
        RealPlayer object or None if not found
    """
    return get_player_loader().get_player_by_id(player_id)


def get_real_roster_for_team(team_id: int) -> List[RealPlayer]:
    """
    Convenience function to get real roster for a team using global loader
    
    Args:
        team_id: Team ID (7 for Browns, 31 for 49ers)
        
    Returns:
        List of RealPlayer objects or empty list if no data
    """
    return get_player_loader().get_players_by_team(team_id)


def has_real_roster_data(team_id: int) -> bool:
    """
    Convenience function to check if real roster data exists for a team
    
    Args:
        team_id: Team ID to check
        
    Returns:
        True if real data exists, False otherwise
    """
    return get_player_loader().has_real_data_for_team(team_id)


# Example usage and testing
if __name__ == "__main__":
    # Test the player data loader
    loader = PlayerDataLoader()
    
    print(f"Loaded {len(loader)} real players")
    print(f"Available teams: {loader.get_available_teams()}")
    print()
    
    # Test player lookup by ID
    player = loader.get_player_by_id(1001)
    if player:
        print(f"Player ID 1001: {player}")
        print(f"  Positions: {player.positions}")
        print(f"  Overall Rating: {player.overall_rating}")
        print(f"  Speed: {player.get_attribute('speed')}")
        print()
    
    # Test team roster
    browns_players = loader.get_players_by_team(7)
    print(f"Cleveland Browns roster ({len(browns_players)} players):")
    for player in browns_players[:5]:  # Show first 5
        print(f"  {player}")
    print()
    
    # Test position lookup
    qbs = loader.get_players_by_position('quarterback')
    print(f"Quarterbacks ({len(qbs)} total):")
    for qb in qbs:
        print(f"  {qb} - Overall: {qb.overall_rating}")
    print()
    
    # Test search
    search_results = loader.search_players_by_name('Brock')
    print(f"Players matching 'Brock': {search_results}")
    print()
    
    # Test team summary
    browns_summary = loader.get_team_roster_summary(7)
    print("Cleveland Browns roster summary:")
    print(f"  Total players: {browns_summary['total_players']}")
    print(f"  Average rating: {browns_summary['avg_overall_rating']:.1f}")
    print(f"  Highest rated: {browns_summary['highest_rated_player']}")
    print(f"  Position counts: {browns_summary['position_counts']}")