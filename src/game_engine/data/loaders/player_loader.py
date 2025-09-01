from typing import Dict, List, Any, Optional
from ..base.entity_loader import EntityLoader
try:
    from database.models.players.player import Player
    from database.models.players.positions import (
        RunningBack, OffensiveLineman, DefensiveLineman, Linebacker,
        create_running_back, create_offensive_lineman, create_defensive_lineman, create_linebacker
    )
except ImportError:
    from src.database.models.players.player import Player
    from src.database.models.players.positions import (
        RunningBack, OffensiveLineman, DefensiveLineman, Linebacker,
        create_running_back, create_offensive_lineman, create_defensive_lineman, create_linebacker
    )


class PlayerLoader(EntityLoader[Player]):
    """
    Loader for Player entities.
    
    Provides player-specific loading functionality including filtering by
    team, position, role, and building team rosters.
    """
    
    def get_entity_type(self) -> str:
        """Return entity type for data source queries."""
        return "players"
    
    def load(self, ids: List[str] = None, team_ids: List[int] = None, 
             positions: List[str] = None, roles: List[str] = None, **filters) -> Dict[str, Player]:
        """
        Load players by IDs or filters.
        
        Args:
            ids: Optional list of player IDs to load
            team_ids: Filter by team IDs
            positions: Filter by positions ("RB", "LT", "MLB", etc.)
            roles: Filter by roles ("starter", "backup", "depth")
            **filters: Additional filters
                
        Returns:
            Dict mapping player ID -> Player object
        """
        # Add specific filters to the general filters dict
        if team_ids is not None:
            filters['team_ids'] = team_ids
        if positions is not None:
            filters['positions'] = positions
        if roles is not None:
            filters['roles'] = roles
        
        # Build cache key for caching
        cache_key = self._build_cache_key(ids, **filters)
        
        def loader_func():
            # Load raw data from data source
            raw_entities = self._load_raw_data(ids, **filters)
            
            # Map to Player objects
            players = {}
            for raw_data in raw_entities:
                player = self._map_data(raw_data)
                players[player.id] = player
            
            # Validate loaded players
            if not self.validate_entities(players):
                raise ValueError("Player data validation failed")
            
            return players
        
        return self._apply_cache(cache_key, loader_func)
    
    def _map_data(self, raw_data: Dict[str, Any]) -> Player:
        """
        Convert raw data dictionary to appropriate Player subclass.
        
        Args:
            raw_data: Raw player data from data source
            
        Returns:
            Player object (RunningBack, OffensiveLineman, etc.)
        """
        position = raw_data["position"]
        name = raw_data["name"]
        team_id = raw_data["team_id"]
        attributes = raw_data.get("attributes", {})
        role = raw_data.get("role", "starter")
        
        # Convert role string to PlayerRole enum
        from database.models.players.player import PlayerRole
        player_role = PlayerRole.STARTER
        if role == "backup":
            player_role = PlayerRole.BACKUP
        elif role == "depth":
            player_role = PlayerRole.DEPTH
        elif role == "practice_squad":
            player_role = PlayerRole.PRACTICE_SQUAD
        
        # Create appropriate player subclass based on position using factory functions
        if position in ["RB", "FB"]:
            player = create_running_back(name, team_id, position, attributes, player_role)
        elif position in ["LT", "LG", "C", "RG", "RT", "OL"]:
            player = create_offensive_lineman(name, team_id, position, attributes, player_role)
        elif position in ["LE", "DT", "NT", "RE", "DE", "DL"]:
            player = create_defensive_lineman(name, team_id, position, attributes, player_role)
        elif position in ["LOLB", "MLB", "ROLB", "ILB", "OLB", "LB"]:
            player = create_linebacker(name, team_id, position, attributes, player_role)
        else:
            # Fallback to base Player class for unknown positions
            from database.models.players.player import Player, InjuryStatus
            player = Player(
                id=raw_data["id"],
                name=name,
                position=position,
                team_id=team_id,
                speed=attributes.get("speed", 50),
                strength=attributes.get("strength", 50),
                agility=attributes.get("agility", 50),
                stamina=attributes.get("stamina", 50),
                awareness=attributes.get("awareness", 50),
                technique=attributes.get("technique", 50),
                role=player_role,
                injury_status=InjuryStatus.HEALTHY
            )
        
        # Set the ID from JSON data (factory functions generate their own IDs)
        player.id = raw_data["id"]
        return player
    
    # Convenience methods for player-specific queries
    
    def get_team_roster(self, team_id: int) -> Dict[str, List[Player]]:
        """
        Get organized roster for a specific team.
        
        Args:
            team_id: ID of team to get roster for
            
        Returns:
            Dict mapping position group -> list of players
        """
        players = self.load(team_ids=[team_id])
        
        # Organize players by position groups
        roster = {
            "running_backs": [],
            "offensive_line": [],
            "defensive_line": [], 
            "linebackers": []
        }
        
        for player in players.values():
            position_group = self._get_position_group(player.position)
            if position_group in roster:
                roster[position_group].append(player)
        
        # Sort each position group by role (starters first)
        for position_group in roster.values():
            position_group.sort(key=lambda p: p.role.value)
        
        return roster
    
    def get_starters(self, team_id: int) -> Dict[str, List[Player]]:
        """
        Get starting lineup for a specific team.
        
        Args:
            team_id: ID of team to get starters for
            
        Returns:
            Dict mapping position group -> list of starting players
        """
        players = self.load(team_ids=[team_id], roles=["starter"])
        
        # Organize starters by position groups
        starters = {
            "running_backs": [],
            "offensive_line": [],
            "defensive_line": [],
            "linebackers": []
        }
        
        for player in players.values():
            position_group = self._get_position_group(player.position)
            if position_group in starters:
                starters[position_group].append(player)
        
        return starters
    
    def get_players_by_position(self, position: str, team_id: int = None) -> List[Player]:
        """
        Get all players at a specific position.
        
        Args:
            position: Position code ("RB", "LT", etc.)
            team_id: Optional team filter
            
        Returns:
            List of players at that position
        """
        filters = {"positions": [position]}
        if team_id is not None:
            filters["team_ids"] = [team_id]
            
        players_dict = self.load(**filters)
        return list(players_dict.values())
    
    def find_best_player_at_position(self, position: str, team_id: int = None) -> Optional[Player]:
        """
        Find the highest-rated player at a specific position.
        
        Args:
            position: Position code
            team_id: Optional team filter
            
        Returns:
            Best player at position or None if no players found
        """
        players = self.get_players_by_position(position, team_id)
        if not players:
            return None
            
        return max(players, key=lambda p: p.overall_rating)
    
    def get_depth_chart(self, team_id: int, position: str) -> List[Player]:
        """
        Get depth chart for a specific position on a team.
        
        Args:
            team_id: Team ID
            position: Position code
            
        Returns:
            List of players sorted by depth (starters first)
        """
        players = self.get_players_by_position(position, team_id)
        
        # Sort by role (starter -> backup -> depth -> practice squad)
        role_order = {"starter": 0, "backup": 1, "depth": 2, "practice_squad": 3}
        players.sort(key=lambda p: role_order.get(p.role.value, 4))
        
        return players
    
    def get_free_agents(self) -> List[Player]:
        """
        Get all players without a team (free agents).
        
        Returns:
            List of free agent players
        """
        # In this implementation, we assume team_id = 0 means free agent
        players_dict = self.load(team_ids=[0])
        return list(players_dict.values())
    
    def get_injured_players(self, team_id: int = None) -> List[Player]:
        """
        Get all injured players.
        
        Args:
            team_id: Optional team filter
            
        Returns:
            List of injured players
        """
        filters = {}
        if team_id is not None:
            filters["team_ids"] = [team_id]
            
        all_players = self.load(**filters)
        
        from database.models.players.player import InjuryStatus
        injured_players = []
        for player in all_players.values():
            if player.injury_status != InjuryStatus.HEALTHY:
                injured_players.append(player)
                
        return injured_players
    
    def _get_position_group(self, position: str) -> str:
        """
        Map position code to position group.
        
        Args:
            position: Position code
            
        Returns:
            Position group name
        """
        if position in ["RB", "FB"]:
            return "running_backs"
        elif position in ["LT", "LG", "C", "RG", "RT", "OL"]:
            return "offensive_line"
        elif position in ["LE", "DT", "NT", "RE", "DE", "DL"]:
            return "defensive_line"
        elif position in ["LOLB", "MLB", "ROLB", "ILB", "OLB", "LB"]:
            return "linebackers"
        else:
            return "other"
    
    def validate_entities(self, players: Dict[str, Player]) -> bool:
        """
        Validate loaded players for data integrity.
        
        Args:
            players: Dict of loaded players
            
        Returns:
            True if all players are valid
        """
        if not super().validate_entities(players):
            return False
        
        # Player-specific validation
        for player_id, player in players.items():
            # Ensure player has required attributes
            if not player.name or not player.position:
                return False
            
            # Ensure team_id is valid (not None)
            if player.team_id is None:
                return False
                
            # Ensure ratings are within valid range
            if not (0 <= player.overall_rating <= 100):
                return False
        
        return True