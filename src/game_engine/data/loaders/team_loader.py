from typing import Dict, List, Any, Optional
from ..base.entity_loader import EntityLoader
from ..entities import Team


class TeamLoader(EntityLoader[Team]):
    """
    Loader for Team entities.
    
    Provides team-specific loading functionality including filtering by
    division, conference, and other team attributes.
    """
    
    def get_entity_type(self) -> str:
        """Return entity type for data source queries."""
        return "teams"
    
    def load(self, ids: List[int] = None, **filters) -> Dict[int, Team]:
        """
        Load teams by IDs or filters.
        
        Args:
            ids: Optional list of team IDs to load
            **filters: Additional filters:
                - division: Filter by division name
                - conference: Filter by conference name
                - city: Filter by city name
                
        Returns:
            Dict mapping team ID -> Team object
        """
        # Build cache key for caching
        cache_key = self._build_cache_key(ids, **filters)
        
        def loader_func():
            # Load raw data from data source
            raw_entities = self._load_raw_data(ids, **filters)
            
            # Map to Team objects
            teams = {}
            for raw_data in raw_entities:
                team = self._map_data(raw_data)
                teams[team.id] = team
            
            # Validate loaded teams
            if not self.validate_entities(teams):
                raise ValueError("Team data validation failed")
            
            return teams
        
        return self._apply_cache(cache_key, loader_func)
    
    def _map_data(self, raw_data: Dict[str, Any]) -> Team:
        """
        Convert raw data dictionary to Team object.
        
        Args:
            raw_data: Raw team data from data source
            
        Returns:
            Team object
        """
        return Team(
            id=raw_data["id"],
            name=raw_data["name"],
            city=raw_data["city"],
            founded=raw_data.get("founded"),
            stadium_id=raw_data.get("stadium_id"),
            division=raw_data.get("division"),
            conference=raw_data.get("conference"),
            ratings=raw_data.get("ratings", {}),
            salary_cap=raw_data.get("salary_cap"),
            cap_space=raw_data.get("cap_space")
        )
    
    # Convenience methods for team-specific queries
    
    def get_division_teams(self, division: str) -> List[Team]:
        """
        Get all teams in a specific division.
        
        Args:
            division: Division name (e.g., "NFC North")
            
        Returns:
            List of Team objects in the division
        """
        teams_dict = self.load(division=division)
        return list(teams_dict.values())
    
    def get_conference_teams(self, conference: str) -> List[Team]:
        """
        Get all teams in a specific conference.
        
        Args:
            conference: Conference name (e.g., "NFC")
            
        Returns:
            List of Team objects in the conference
        """
        teams_dict = self.load(conference=conference)
        return list(teams_dict.values())
    
    def find_by_city(self, city: str) -> Optional[Team]:
        """
        Find team by city name.
        
        Args:
            city: City name
            
        Returns:
            Team object or None if not found
        """
        teams_dict = self.load(city=city)
        return next(iter(teams_dict.values())) if teams_dict else None
    
    def find_by_name(self, name: str) -> Optional[Team]:
        """
        Find team by name.
        
        Args:
            name: Team name
            
        Returns:
            Team object or None if not found
        """
        all_teams = self.get_all()
        for team in all_teams.values():
            if team.name.lower() == name.lower():
                return team
        return None
    
    def find_by_full_name(self, full_name: str) -> Optional[Team]:
        """
        Find team by full name (city + name).
        
        Args:
            full_name: Full team name (e.g., "Chicago Bears")
            
        Returns:
            Team object or None if not found
        """
        all_teams = self.get_all()
        for team in all_teams.values():
            if team.full_name.lower() == full_name.lower():
                return team
        return None
    
    def get_teams_by_rating_range(self, min_rating: int, max_rating: int) -> List[Team]:
        """
        Get teams within a specific overall rating range.
        
        Args:
            min_rating: Minimum overall rating
            max_rating: Maximum overall rating
            
        Returns:
            List of teams within rating range
        """
        all_teams = self.get_all()
        filtered_teams = []
        
        for team in all_teams.values():
            overall_rating = team.get_rating("overall_rating")
            if min_rating <= overall_rating <= max_rating:
                filtered_teams.append(team)
        
        return sorted(filtered_teams, key=lambda t: t.get_rating("overall_rating"), reverse=True)
    
    def get_top_teams(self, count: int = 10) -> List[Team]:
        """
        Get top teams by overall rating.
        
        Args:
            count: Number of teams to return
            
        Returns:
            List of top teams sorted by rating
        """
        all_teams = self.get_all()
        sorted_teams = sorted(all_teams.values(), 
                            key=lambda t: t.get_rating("overall_rating"), 
                            reverse=True)
        return sorted_teams[:count]
    
    def validate_entities(self, teams: Dict[int, Team]) -> bool:
        """
        Validate loaded teams for data integrity.
        
        Args:
            teams: Dict of loaded teams
            
        Returns:
            True if all teams are valid
        """
        if not super().validate_entities(teams):
            return False
        
        # Team-specific validation
        for team_id, team in teams.items():
            # Ensure team has required attributes
            if not team.name or not team.city:
                return False
            
            # Ensure ratings are present
            if not team.ratings:
                return False
        
        return True