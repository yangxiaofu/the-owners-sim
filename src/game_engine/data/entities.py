from dataclasses import dataclass
from typing import Dict, Any, Optional


@dataclass
class Team:
    """
    Team entity representing a football team.
    
    Contains team metadata, ratings, organizational information, and coaching philosophy.
    """
    id: int
    name: str
    city: str
    founded: Optional[int] = None
    stadium_id: Optional[int] = None
    division: Optional[str] = None
    conference: Optional[str] = None
    
    # Team ratings and coaching
    ratings: Dict[str, Any] = None
    team_philosophy: Optional[str] = None
    
    # Financial information
    salary_cap: Optional[int] = None
    cap_space: Optional[int] = None
    
    def __post_init__(self):
        """Initialize default ratings if not provided."""
        if self.ratings is None:
            self.ratings = {
                "offense": {"rb_rating": 50, "ol_rating": 50, "qb_rating": 50, "wr_rating": 50, "te_rating": 50},
                "defense": {"dl_rating": 50, "lb_rating": 50, "db_rating": 50},
                "special_teams": 50,
                "coaching": {
                    "offensive": 50, 
                    "defensive": 50,
                    "offensive_coordinator": {
                        "archetype": "balanced_attack",
                        "personality": "balanced",
                        "custom_modifiers": {}
                    },
                    "defensive_coordinator": {
                        "archetype": "multiple_defense",
                        "personality": "balanced",
                        "custom_modifiers": {}
                    }
                },
                "overall_rating": 50
            }
        
        # Set default team philosophy if not provided
        if self.team_philosophy is None:
            self.team_philosophy = "balanced_approach"
    
    @property
    def full_name(self) -> str:
        """Get full team name (city + name)."""
        return f"{self.city} {self.name}"
    
    def get_rating(self, category: str, subcategory: str = None) -> int:
        """
        Get a specific rating value.
        
        Args:
            category: Main category ("offense", "defense", etc.)
            subcategory: Optional subcategory ("rb_rating", "qb_rating", etc.)
            
        Returns:
            Rating value or 50 if not found
        """
        if category not in self.ratings:
            return 50
            
        rating_data = self.ratings[category]
        
        if subcategory is None:
            return rating_data if isinstance(rating_data, int) else 50
        
        return rating_data.get(subcategory, 50) if isinstance(rating_data, dict) else 50
    
    def get_coaching_archetype(self, coordinator_type: str) -> str:
        """
        Get coaching archetype for offensive or defensive coordinator.
        
        Args:
            coordinator_type: "offensive" or "defensive"
            
        Returns:
            Archetype string or "balanced_attack"/"multiple_defense" as default
        """
        coaching = self.ratings.get("coaching", {})
        coordinator_key = f"{coordinator_type}_coordinator"
        coordinator_data = coaching.get(coordinator_key, {})
        
        if coordinator_type == "offensive":
            return coordinator_data.get("archetype", "balanced_attack")
        else:
            return coordinator_data.get("archetype", "multiple_defense")
    
    def get_custom_modifiers(self, coordinator_type: str) -> Dict[str, float]:
        """
        Get custom modifiers for offensive or defensive coordinator.
        
        Args:
            coordinator_type: "offensive" or "defensive"
            
        Returns:
            Dictionary of custom modifiers
        """
        coaching = self.ratings.get("coaching", {})
        coordinator_key = f"{coordinator_type}_coordinator"
        coordinator_data = coaching.get(coordinator_key, {})
        return coordinator_data.get("custom_modifiers", {})
    
    def get_coordinator_personality(self, coordinator_type: str) -> str:
        """
        Get coordinator personality.
        
        Args:
            coordinator_type: "offensive" or "defensive"
            
        Returns:
            Personality string or "balanced" as default
        """
        coaching = self.ratings.get("coaching", {})
        coordinator_key = f"{coordinator_type}_coordinator"
        coordinator_data = coaching.get(coordinator_key, {})
        return coordinator_data.get("personality", "balanced")
    
    def __str__(self) -> str:
        return self.full_name
    
    def __repr__(self) -> str:
        return f"Team(id={self.id}, name='{self.full_name}', overall={self.get_rating('overall_rating')})"


@dataclass
class Stadium:
    """
    Stadium entity representing a football stadium.
    """
    id: int
    name: str
    city: str
    capacity: int
    surface: str = "grass"  # grass, turf, dome, etc.
    opened: Optional[int] = None
    
    def __str__(self) -> str:
        return f"{self.name} ({self.city})"
    
    def __repr__(self) -> str:
        return f"Stadium(id={self.id}, name='{self.name}', capacity={self.capacity})"


@dataclass 
class MediaAsset:
    """
    Media asset entity for logos, photos, etc.
    """
    id: str
    entity_type: str  # "team", "player", "stadium"
    entity_id: Any    # ID of associated entity
    asset_type: str   # "logo", "photo", "video"
    url: str
    alt_text: Optional[str] = None
    
    def __str__(self) -> str:
        return f"{self.asset_type} for {self.entity_type} {self.entity_id}"
    
    def __repr__(self) -> str:
        return f"MediaAsset(id='{self.id}', type='{self.asset_type}', url='{self.url}')"